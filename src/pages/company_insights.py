import streamlit as st
import pandas as pd
import plotly.express as px

ASSUMED_FX = 15500  # adjustable


def page_company_insights(df: pd.DataFrame):
    st.subheader("Company Insights")
    if df.empty:
        st.info("No data for current filters.")
        return

    if "company" not in df.columns:
        st.warning("'company' column not available.")
        return

    grp_cols = [c for c in ["company","price_idr","price_usd","price_per_sqm_idr"] if c in df.columns]
    summary = df.groupby("company").agg(
        listings=("property_id", "nunique") if "property_id" in df.columns else ("company", "count"),
        median_price_idr=("price_idr", "median") if "price_idr" in df.columns else ("company","count"),
        median_price_usd=("price_usd", "median") if "price_usd" in df.columns else ("company","count"),
        median_ppsqm_idr=("price_per_sqm_idr", "median") if "price_per_sqm_idr" in df.columns else ("company","count"),
    ).reset_index()

    fig_listings = px.bar(summary.sort_values("listings", ascending=False).head(25), x="company", y="listings", title="Top Companies by Listings")
    st.plotly_chart(fig_listings, width="stretch")

    if {"median_price_idr","median_price_usd"}.issubset(summary.columns):
        fig_prices = px.scatter(summary, x="median_price_usd", y="median_price_idr", hover_name="company", title="Median USD vs IDR Price by Company")
        st.plotly_chart(fig_prices, width="stretch")

    # Anomaly detection: derive implied FX from each row if both prices exist
    if {"price_idr","price_usd"}.issubset(df.columns):
        fx_df = df.dropna(subset=["price_idr","price_usd"]).copy()
        fx_df = fx_df[fx_df["price_usd"]>0]
        fx_df["implied_fx"] = fx_df["price_idr"] / fx_df["price_usd"]
        fx_df["fx_deviation_pct"] = (fx_df["implied_fx"] - ASSUMED_FX)/ASSUMED_FX * 100
        anomalies = fx_df[fx_df["fx_deviation_pct"].abs() > 20].head(200)  # >20% deviation
        st.write("### Exchange Rate Anomalies (>20% deviation)")
        if anomalies.empty:
            st.caption("No significant anomalies detected.")
        else:
            show_cols = [c for c in ["property_id","company","price_idr","price_usd","implied_fx","fx_deviation_pct","url"] if c in anomalies.columns]
            st.dataframe(anomalies[show_cols])
