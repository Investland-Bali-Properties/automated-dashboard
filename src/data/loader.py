import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from typing import Set, List

load_dotenv()

SHEET_NAME = os.getenv("SHEET_NAME", "[Silver]Unified_Clean_Data")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

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

@st.cache_data(show_spinner=False, ttl=600)
def load_data() -> pd.DataFrame:
    """Load data from Google Sheets and return DataFrame with normalization + diagnostics."""
    if not SPREADSHEET_ID:
        raise RuntimeError("SPREADSHEET_ID env var missing")

    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "google-credentials.json")
    if not os.path.exists(service_account_file):
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

    credentials = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    ws = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    # Pull raw values first for raw row count (includes header row at index 0)
    raw_values = ws.get_all_values()
    raw_row_count = max(len(raw_values) - 1, 0)  # minus header

    rows = ws.get_all_records()
    df = pd.DataFrame(rows)
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
        "raw_row_count": raw_row_count,
        "dataframe_row_count": int(len(df)),
        "unique_property_id": int(df["property_id"].nunique()) if "property_id" in df.columns else None,
        "duplicate_property_id_rows": int(len(df) - df["property_id"].nunique()) if "property_id" in df.columns else None,
        "sentinel_replacements": df.attrs.get("sentinel_replacements", {}),
        "listing_date_non_null": int(df["listing_date"].notna().sum()) if "listing_date" in df.columns else None,
        "scraped_at_non_null": int(df["scraped_at"].notna().sum()) if "scraped_at" in df.columns else None,
    }
    df.attrs['diagnostics'] = diagnostics
    # Store into session state for pages to optionally display
    try:
        st.session_state['data_diagnostics'] = diagnostics
    except Exception:
        pass

    return df
