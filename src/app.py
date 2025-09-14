import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from data.loader import load_data
from components.filters import sidebar_filters
from utils.filters_apply import apply_filters
from pages.market_overview import page_market_overview
from pages.property_explorer import page_property_explorer

load_dotenv()

st.set_page_config(page_title="Real Estate Dashboard", layout="wide")

st.title("Real Estate Market Dashboard (Mini)")

# Data load + refresh button
refresh = st.sidebar.button("🔄 Refresh Data")
if refresh:
    load_data.clear()  # type: ignore

df = load_data()

filters = sidebar_filters(df)
filtered = apply_filters(df, filters)

# Export section remains in sidebar (filters area)
with st.sidebar.expander("Export", expanded=False):
    if not filtered.empty:
        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("Download Filtered CSV", data=csv_bytes, file_name="filtered_properties.csv", mime="text/csv")
    else:
        st.caption("No data to export")

# Top navigation tabs
TABS = [
    "Market Overview",
    "Pricing Trends",
    "Supply & Demand",
    "Company Insights",
    "KPI Dashboard",
    "Property Explorer",
    "Data Quality",
]

(tab_market, tab_pricing, tab_supply, tab_company, tab_kpi, tab_explorer, tab_quality) = st.tabs(TABS)

with tab_market:
    page_market_overview(filtered)
with tab_pricing:
    from pages.pricing_trends import page_pricing_trends
    page_pricing_trends(filtered)
with tab_supply:
    from pages.supply_demand import page_supply_demand
    page_supply_demand(filtered)
with tab_company:
    from pages.company_insights import page_company_insights
    page_company_insights(filtered)
with tab_kpi:
    from pages.kpi_dashboard import page_kpi_dashboard
    page_kpi_dashboard(filtered)
with tab_explorer:
    page_property_explorer(filtered)
with tab_quality:
    from pages.data_quality import page_data_quality
    page_data_quality(df)

st.sidebar.caption("Extended version with additional pages.")
