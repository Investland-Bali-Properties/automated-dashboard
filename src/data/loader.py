import os
import json
import re
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from typing import Set, List, Tuple

# Ensure .env loaded for local dev (non-override)
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

SENTINELS: Set[str] = {"", "None", "none", "N/A", "n/a", "NA", "na", "null", "Null", "-", "—"}
SCRAPED_AT_PATTERNS: List[str] = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",  # minute resolution
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]


def _normalize_sentinels(df: pd.DataFrame) -> pd.DataFrame:
    """Replace sentinel string tokens with None (in-place) and record counts in df.attrs.

    Adds / updates:
        df.attrs['sentinel_replacements'] = {column: count_replaced, ...}
    """
    replacements = {}
    for col in df.columns:
        if df[col].dtype == object:
            # Identify sentinel strings (strip then in SENTINELS)
            mask = df[col].apply(lambda v: isinstance(v, str) and v.strip() in SENTINELS)
            count = int(mask.sum())
            if count:
                replacements[col] = count
                df.loc[mask, col] = None
    if replacements:
        existing = df.attrs.get('sentinel_replacements', {})
        existing.update(replacements)
        df.attrs['sentinel_replacements'] = existing
    return df


def _multi_parse_datetime(series: pd.Series, patterns: List[str]):
    raw = series.copy()
    parsed = pd.to_datetime(raw, errors="coerce", utc=True)
    remaining_mask = parsed.isna() & raw.notna()
    reasons = pd.Series([None]*len(raw), index=raw.index, dtype=object)

    # pattern attempts for remaining
    for fmt in patterns:
        if not remaining_mask.any():
            break
        try:
            attempt = pd.to_datetime(raw[remaining_mask], format=fmt, errors="coerce", utc=True)
        except Exception:
            continue
        success_mask = attempt.notna()
        parsed.loc[success_mask.index[success_mask]] = attempt[success_mask]
        remaining_mask = parsed.isna() & raw.notna()

    # classify failures
    failed_raw = raw[remaining_mask]
    for idx, val in failed_raw.items():
        if isinstance(val, str) and val.strip() in SENTINELS:
            reasons.at[idx] = "sentinel"
        elif isinstance(val, str) and not val.strip():
            reasons.at[idx] = "blank"
        else:
            reasons.at[idx] = "unparsed_format"

    return parsed, reasons

def _get_secret(name: str, default: str | None = None) -> str | None:
    """Try env first, then st.secrets (if available)."""
    val = os.getenv(name)
    if val:
        return val
    try:
        sec = getattr(st, "secrets", None)
        if sec:
            v = sec.get(name)  # type: ignore[index]
            return str(v) if v is not None else default
    except Exception:
        pass
    return default


def _get_list_secret(name: str, fallback_name: str | None = None, default: List[str] | None = None) -> List[str] | None:
    """Get list-like secret from env or st.secrets.
    Accepts TOML array, JSON array string, or comma-separated string.
    If not found, will check fallback_name, then return default.
    """
    def parse_list(raw) -> List[str] | None:
        if raw is None:
            return None
        # Already list (from TOML secrets)
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
        s = str(raw).strip()
        if not s:
            return None
        # JSON array
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("\n[") and s.strip().endswith("]")):
            try:
                arr = json.loads(s)
                return [str(x).strip() for x in arr if str(x).strip()]
            except Exception:
                pass
        # comma-separated
        if "," in s:
            return [item.strip() for item in s.split(",") if item.strip()]
        # single value
        return [s]

    # Env first
    env_val = os.getenv(name)
    lst = parse_list(env_val)
    if lst:
        return lst
    # st.secrets
    try:
        sec = getattr(st, "secrets", None)
        if sec:
            raw = sec.get(name)  # type: ignore[index]
            lst = parse_list(raw)
            if lst:
                return lst
    except Exception:
        pass
    # Fallback var
    if fallback_name:
        env_val = os.getenv(fallback_name)
        lst = parse_list(env_val)
        if lst:
            return lst
        try:
            sec = getattr(st, "secrets", None)
            if sec:
                raw = sec.get(fallback_name)  # type: ignore[index]
                lst = parse_list(raw)
                if lst:
                    return lst
        except Exception:
            pass
    return default


def _repair_json_private_key(text: str) -> str:
    """If JSON text contains an unescaped multi-line private_key, escape newlines.
    This fixes the common case when TOML triple-quoted strings preserve newlines.
    """
    pattern = r'"private_key"\s*:\s*"(.*?)"'
    def _repl(m: re.Match[str]) -> str:
        val = m.group(1)
        val = val.replace("\r\n", "\\n").replace("\n", "\\n")
        return f'"private_key": "{val}"'
    return re.sub(pattern, _repl, text, flags=re.DOTALL)


def _materialize_creds_if_inline(path_or_json: str) -> str:
    """If GOOGLE_APPLICATION_CREDENTIALS is JSON content, write to /tmp and return the path.
    Accepts both valid JSON and TOML multi-line string variants; attempts auto-repair.
    """
    if os.path.exists(path_or_json):
        return path_or_json
    text = path_or_json.strip()
    if text.startswith("{") and text.endswith("}"):
        # Try parse; if fails, attempt to repair private_key newlines
        content = text
        try:
            json.loads(content)
        except Exception:
            repaired = _repair_json_private_key(content)
            try:
                json.loads(repaired)
                content = repaired
            except Exception:
                # As a last resort, still write content; downstream may still parse
                pass
        tmp_path = "/tmp/google-credentials.json"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        return tmp_path
    # Not JSON-like, treat as file path
    return path_or_json


def _available_secret_keys() -> list[str]:
    keys: list[str] = []
    try:
        sec = getattr(st, "secrets", None)
        if isinstance(sec, dict):
            keys = list(sec.keys())
        else:
            try:
                keys = list(sec.to_dict().keys())  # type: ignore[attr-defined]
            except Exception:
                pass
    except Exception:
        pass
    return sorted(set(str(k) for k in keys))


def load_data() -> pd.DataFrame:
    """Wrapper that resolves config and calls the cached implementation."""
    # Late import to avoid circular if used elsewhere
    try:
        from src.bootstrap_env import ensure_env
        ensure_env()
    except Exception:
        pass

    spreadsheet_id = _get_secret("SPREADSHEET_ID")
    # Prefer explicit list in SHEET_NAMES; else fall back to SHEET_NAME (supports comma-separated)
    sheet_names = _get_list_secret("SHEET_NAMES", fallback_name="SHEET_NAME", default=["[Silver]Unified_Clean_Data"]) or ["[Silver]Unified_Clean_Data"]

    if not spreadsheet_id:
        # Add helpful diagnostics for Cloud
        keys = _available_secret_keys()
        env_flag = bool(os.getenv("SPREADSHEET_ID"))
        raise RuntimeError(
            "SPREADSHEET_ID env var missing (env or secrets). "
            f"Env present? {env_flag}. Secrets keys: {keys}"
        )

    service_account_raw = _get_secret("GOOGLE_APPLICATION_CREDENTIALS", "google-credentials.json")
    service_account_file = _materialize_creds_if_inline(service_account_raw)
    if not os.path.exists(service_account_file):
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

    # Call cached impl with explicit params for proper cache keying
    return _load_data_impl(spreadsheet_id, tuple(sheet_names), service_account_file)


@st.cache_data(show_spinner=False, ttl=600)
def _load_data_impl(spreadsheet_id: str, sheet_names: Tuple[str, ...], service_account_file: str) -> pd.DataFrame:
    """Load data from one or more sheet tabs and return normalized DataFrame.
    Cached by spreadsheet_id, sheet_names, and service_account_file.
    """
    credentials = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    ss = client.open_by_key(spreadsheet_id)

    frames: List[pd.DataFrame] = []
    total_raw_rows = 0
    for name in sheet_names:
        ws = ss.worksheet(name)
        raw_values = ws.get_all_values()
        total_raw_rows += max(len(raw_values) - 1, 0)
        rows = ws.get_all_records()
        df_i = pd.DataFrame(rows)
        if df_i.empty:
            continue
        df_i["data_source"] = name
        frames.append(df_i)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True, sort=True)

    if df.empty:
        return df

    df = _normalize_sentinels(df)

    if "scraped_at" in df.columns:
        df["scraped_at_raw"] = df["scraped_at"]
        parsed, reasons = _multi_parse_datetime(df["scraped_at"], SCRAPED_AT_PATTERNS)
        df["scraped_at"] = parsed
        df["scraped_at_parse_ok"] = df["scraped_at"].notna()
        df["scraped_at_parse_fail_reason"] = reasons

    # listing_date simple parse
    if "listing_date" in df.columns:
        df["listing_date"] = pd.to_datetime(df["listing_date"], errors="coerce", utc=True)

    numeric_cols = [
        "price_idr","price_usd","bedrooms","bathrooms","land_size_sqm","building_size_sqm",
        "price_per_sqm_idr","price_per_sqm_usd"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Basic diagnostics
    diagnostics = {
        "raw_row_count": total_raw_rows,
        "dataframe_row_count": int(len(df)),
        "unique_property_id": int(df["property_id"].nunique()) if "property_id" in df.columns else None,
        "duplicate_property_id_rows": int(len(df) - df["property_id"].nunique()) if "property_id" in df.columns else None,
        "sentinel_replacements": df.attrs.get("sentinel_replacements", {}),
        "listing_date_non_null": int(df["listing_date"].notna().sum()) if "listing_date" in df.columns else None,
        "scraped_at_non_null": int(df["scraped_at"].notna().sum()) if "scraped_at" in df.columns else None,
        "sheet_names": list(sheet_names),
    }
    df.attrs['diagnostics'] = diagnostics
    # Store into session state for pages to optionally display
    try:
        st.session_state['data_diagnostics'] = diagnostics
    except Exception:
        pass

    return df
