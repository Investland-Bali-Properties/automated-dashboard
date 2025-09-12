import streamlit as st
import pandas as pd


def kpi_row(df: pd.DataFrame):
    col1, col2, col3, col4 = st.columns(4)

    total_listings = len(df)
    median_price_idr = df["price_idr"].median() if "price_idr" in df else None
    median_price_usd = df["price_usd"].median() if "price_usd" in df else None
    median_ppsqm_idr = df["price_per_sqm_idr"].median() if "price_per_sqm_idr" in df else None

    with col1:
        st.metric("Total Listings", f"{total_listings:,}")
    with col2:
        st.metric("Median Price (IDR)", _fmt_currency(median_price_idr, suffix=" IDR"))
    with col3:
        st.metric("Median Price (USD)", _fmt_currency(median_price_usd, prefix="$"))
    with col4:
        st.metric("Median Price / sqm (IDR)", _fmt_currency(median_ppsqm_idr, suffix=" IDR"))


def _fmt_currency(v, prefix="", suffix=""):
    if v is None or pd.isna(v):
        return "N/A"
    if v > 1_000_000_000:
        return f"{prefix}{v/1_000_000_000:.2f}B{suffix}"
    if v > 1_000_000:
        return f"{prefix}{v/1_000_000:.2f}M{suffix}"
    if v > 1_000:
        return f"{prefix}{v/1_000:.1f}K{suffix}"
    return f"{prefix}{v:,.0f}{suffix}"
