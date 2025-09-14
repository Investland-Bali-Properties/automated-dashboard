import streamlit as st
import pandas as pd
import plotly.express as px


def page_supply_demand(df: pd.DataFrame):
    st.subheader("Supply & Demand")
    if df.empty:
        st.info("No data for current filters.")
        return

    # Availability breakdown
    if "availability" in df.columns:
        avail_counts = df["availability"].value_counts(dropna=False).reset_index()
        avail_counts.columns = ["availability", "count"]
        fig_avail = px.bar(avail_counts, x="availability", y="count", title="Availability Breakdown")
        st.plotly_chart(fig_avail, width="stretch")

    # New listings over time
    if "scraped_at" in df.columns:
        temp = df.dropna(subset=["scraped_at"]).copy()
        temp["date"] = temp["scraped_at"].dt.floor('D')
        new_listings = temp.groupby("date").agg(new_listings=("property_id", "nunique")).reset_index()
        fig_new = px.bar(new_listings, x="date", y="new_listings", title="New Listings Over Time")
        st.plotly_chart(fig_new, width="stretch")

    # Property status vs type pivot
    if {"property_status", "property_type"}.issubset(df.columns):
        pivot = df.pivot_table(index="property_type", columns="property_status", values="property_id", aggfunc="count", fill_value=0)
        st.write("### Status by Property Type")
        st.dataframe(pivot)
