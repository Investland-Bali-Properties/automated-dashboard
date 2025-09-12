import os
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SHEET_NAME = os.getenv("SHEET_NAME", "[Silver]Unified_Clean_Data")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")  # put in .env

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

@st.cache_data(show_spinner=False, ttl=600)
def load_data() -> pd.DataFrame:
    """Load data from Google Sheets and return DataFrame."""
    if not GOOGLE_SHEET_ID:
        raise RuntimeError("GOOGLE_SHEET_ID env var missing")

    # Credentials from service account json file path provided via env var or default
    service_account_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google-credentials.json")
    if not os.path.exists(service_account_file):
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

    credentials = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    ws = client.open_by_key(GOOGLE_SHEET_ID).worksheet(SHEET_NAME)
    rows = ws.get_all_records()
    df = pd.DataFrame(rows)

    # Basic type coercions / safe conversions (presentation only)
    date_cols = [c for c in ["listing_date", "scraped_at"] if c in df.columns]
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors="coerce")

    numeric_cols = [
        "price_idr","price_usd","bedrooms","bathrooms","land_size_sqm","building_size_sqm",
        "price_per_sqm_idr","price_per_sqm_usd"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df
