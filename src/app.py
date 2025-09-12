import os
import streamlit as st
import pandas as pd
from data.loader import load_data
from components.filters import sidebar_filters
from pages.market_overview import page_market_overview
from pages.property_explorer import page_property_explorer

st.set_page_config(page_title="Real Estate Dashboard", layout="wide")

st.title("Real Estate Market Dashboard (Mini)")

# Data load + refresh button
refresh = st.sidebar.button("🔄 Refresh Data")
if refresh:
    load_data.clear()  # type: ignore

df = load_data()

filters = sidebar_filters(df)

# Simple filter application
filtered = df.copy()
if filters.get("property_type"):
    filtered = filtered[filtered["property_type"].isin(filters["property_type"]) ]
if filters.get("area"):
    filtered = filtered[filtered["area"].isin(filters["area"]) ]
if filters.get("price_idr") and "price_idr" in filtered:
    lo, hi = filters["price_idr"]
    filtered = filtered[(filtered["price_idr"]>=lo) & (filtered["price_idr"]<=hi)]
if filters.get("bedrooms") and "bedrooms" in filtered:
    blo, bhi = filters["bedrooms"]
    filtered = filtered[(filtered["bedrooms"]>=blo) & (filtered["bedrooms"]<=bhi)]

page = st.sidebar.radio("Page", ["Market Overview", "Property Explorer"])

if page == "Market Overview":
    page_market_overview(filtered)
elif page == "Property Explorer":
    page_property_explorer(filtered)

st.sidebar.caption("Mini version. More pages coming soon.")
