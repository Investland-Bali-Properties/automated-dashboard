import streamlit as st
import pandas as pd
import plotly.express as px

import common as cm

st.set_page_config(page_title="Overview • Automated Dashboard", page_icon="📊", layout="wide")

st.title("Overview")

# Load data and render global filters
with st.sidebar:
    st.header("Filters")

df = cm.get_data()
filtered, f = cm.render_global_filters(df)

# Headline KPIs
sale_df = filtered[filtered["status"] == "success"].copy()

col1, col2, col3, col4 = st.columns(4)
with col1:
    cm.kpi_metric("Inventory (Listings)", sale_df["listing_id"].nunique())
with col2:
    cm.kpi_metric("Median Sale Price", cm.safe_median(sale_df["price_sale"]), fmt="currency")
with col3:
    cm.kpi_metric("Median ADR", cm.safe_median(sale_df["adr"]), fmt="currency")
with col4:
    cm.kpi_metric("Data Freshness", cm.freshness_label(sale_df["scrape_time"]))

st.divider()

# Sparkline trends
left, right = st.columns(2)

with left:
    st.subheader("Median Sale Price • Trend")
    ts = (sale_df
           .groupby("date", as_index=False)["price_sale"].median())
    if not ts.empty:
        fig = px.area(ts, x="date", y="price_sale")
        fig.update_traces(line_color="#565B38")
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data for current filters.")

with right:
    st.subheader("Median ADR • Trend")
    ts = (sale_df
           .groupby("date", as_index=False)["adr"].median())
    if not ts.empty:
        fig = px.area(ts, x="date", y="adr")
        fig.update_traces(line_color="#565B38")
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data for current filters.")

st.divider()

# Cards per competitor
st.subheader("Inventory by Competitor")
comp = (sale_df.groupby("competitor", as_index=False)["listing_id"].nunique()
                 .rename(columns={"listing_id": "count"}).sort_values("count", ascending=False))
if not comp.empty:
    fig = px.bar(comp, x="competitor", y="count", text_auto=True)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for current filters.")

st.divider()

# Data freshness indicator per source
st.subheader("Data Freshness by Source")
by_src = (sale_df.groupby("source", as_index=False)
                .agg(last_scrape=("scrape_time", "max")))
if not by_src.empty:
    by_src["age_hours"] = (pd.Timestamp.now(tz=by_src["last_scrape"].dt.tz)
                             - by_src["last_scrape"]).dt.total_seconds() / 3600
    fig = px.bar(by_src, x="source", y="age_hours", text_auto=".1f",
                 labels={"age_hours": "Hours since last scrape"})
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for current filters.")

st.caption("Theme from .streamlit/config.toml is applied automatically.")
