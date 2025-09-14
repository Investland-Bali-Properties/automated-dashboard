import streamlit as st
import pandas as pd
from components.kpi_cards import kpi_row
from components.charts import price_trend_chart, price_distribution_chart


def page_market_overview(df: pd.DataFrame):
    st.subheader("Market Overview")
    kpi_row(df)

    with st.expander("Trend Controls", expanded=False):
        colc1, colc2, colc3, colc4 = st.columns(4)
        with colc1:
            agg = st.selectbox("Aggregation", ["D", "W", "M"], format_func=lambda x: {"D":"Daily","W":"Weekly","M":"Monthly"}[x])
        with colc2:
            group_lt = st.checkbox("Group by listing type")
        with colc3:
            rolling = st.selectbox("Price Rolling", [1,3,7,14], index=0)
        with colc4:
            listings_roll = st.selectbox("Listings Rolling", [1,3,7,14], index=0)
        colc5, colc6 = st.columns(2)
        with colc5:
            metric = st.radio("Price Metric", ["median","mean"], horizontal=True, index=0)
        with colc6:
            show_dist = st.checkbox("Show Distribution Chart", value=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_trend = price_trend_chart(
            df,
            agg=agg,
            group_by_listing_type=group_lt,
            rolling=rolling if rolling>1 else None,
            metric=metric,
            listings_rolling=listings_roll if listings_roll>1 else None,
        )
        if fig_trend:
            st.plotly_chart(fig_trend, width="stretch")
            # Data density note
            if {"scraped_at"}.issubset(df.columns):
                periods = df['scraped_at'].dt.to_period(agg).nunique()
                if periods < 3:
                    st.caption("⚠️ Limited historical depth ("+str(periods)+" periods). Trend interpretation may be unreliable.")
    with col2:
        if show_dist:
            fig_dist = price_distribution_chart(df)
            if fig_dist:
                st.plotly_chart(fig_dist, width="stretch")