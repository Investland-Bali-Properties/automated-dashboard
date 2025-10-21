"""
Bootstrap environment for Streamlit Cloud & local dev:
- Flatten st.secrets into uppercase os.environ keys (nested -> PREFIX_CHILD)
- If GOOGLE_CREDENTIALS_JSON is provided in secrets (dict or JSON string),
  write it to /tmp/google-credentials.json and set GOOGLE_APPLICATION_CREDENTIALS
- Finally, load .env (without overriding existing env vars)
"""

from __future__ import annotations

import json
import os
import re
from typing import Iterator, Tuple

import streamlit as st
from dotenv import load_dotenv


def _sanitize_key(key: str) -> str:
    # Uppercase and replace non-alphanumeric with underscores
    return re.sub(r"[^A-Za-z0-9_]", "_", key.upper())


def _flatten_secrets(prefix: str, val) -> Iterator[Tuple[str, str]]:
    if isinstance(val, dict):
        for k, v in val.items():
            yield from _flatten_secrets(f"{prefix}_{k}", v)
    else:
        yield _sanitize_key(prefix), str(val)


def _bridge_secrets_to_env() -> None:
    try:
        # st.secrets may not exist locally outside Streamlit runtime
        items = getattr(st, "secrets", None)
        if not items:
            return
        # Prefer dict-like access
        try:
            secrets_dict = items.to_dict()  # type: ignore[attr-defined]
        except Exception:
            secrets_dict = dict(items)  # fall back for mapping-like

        for key, value in secrets_dict.items():
            if isinstance(value, dict):
                for flat_k, flat_v in _flatten_secrets(key, value):
                    os.environ.setdefault(flat_k, flat_v)
            else:
                os.environ.setdefault(_sanitize_key(key), str(value))
    except Exception:
        # Ignore in non-Streamlit or if secrets unavailable
        return


def _materialize_google_credentials() -> None:
    """Create a temp service account file from secrets if needed.

    Priority:
    1) If GOOGLE_APPLICATION_CREDENTIALS already set and exists -> keep
    2) Else if GOOGLE_CREDENTIALS_JSON provided in secrets -> write to /tmp and set env
    3) Else do nothing (loader may use default path or fail clearly)
    """
    existing_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if existing_path and os.path.exists(existing_path):
        return

    try:
        secrets = getattr(st, "secrets", None)
        if not secrets:
            return
        json_text = None
        # Case A: GOOGLE_APPLICATION_CREDENTIALS provided but points to non-existent path; try if it's JSON content
        if existing_path and not os.path.exists(existing_path):
            try:
                json.loads(existing_path)
                json_text = existing_path
            except Exception:
                json_text = None
        # Case B: Dedicated GOOGLE_CREDENTIALS_JSON key
        if not json_text:
            creds = secrets.get("GOOGLE_CREDENTIALS_JSON")  # type: ignore[index]
            if not creds:
                return
            if isinstance(creds, dict):
                json_text = json.dumps(creds)
            else:
                try:
                    json.loads(str(creds))
                    json_text = str(creds)
                except Exception:
                    return
        tmp_path = "/tmp/google-credentials.json"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(json_text)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_path
    except Exception:
        # Silent fail; loader will surface a clear error if creds missing
        return


def _load_dotenv_non_override() -> None:
    # load_dotenv will not override existing env vars by default
    load_dotenv()



def ensure_env() -> None:
    """Idempotent: make sure env vars and creds are available.
    Safe to call multiple times, both inside and outside Streamlit runtime.
    """
    _bridge_secrets_to_env()
    _materialize_google_credentials()
    _load_dotenv_non_override()

# Execute on import for Streamlit main process, but also allow explicit calls elsewhere.
ensure_env()
