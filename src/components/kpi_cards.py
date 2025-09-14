import streamlit as st
import pandas as pd
from utils.formatting import format_currency


def kpi_row(df: pd.DataFrame):
    col1, col2, col3, col4 = st.columns(4)

    total_listings = len(df)
    median_price_idr = df["price_idr"].median() if "price_idr" in df else None
    median_price_usd = df["price_usd"].median() if "price_usd" in df else None
    median_ppsqm_idr = df["price_per_sqm_idr"].median() if "price_per_sqm_idr" in df else None

    with col1:
        st.metric("Total Listings", f"{total_listings:,}")
    with col2:
        st.metric("Median Price (IDR)", format_currency(median_price_idr, suffix=" IDR"))
    with col3:
        st.metric("Median Price (USD)", format_currency(median_price_usd, prefix="$"))
    with col4:
        st.metric("Median Price / sqm (IDR)", format_currency(median_ppsqm_idr, suffix=" IDR"))
