import streamlit as st
import pandas as pd
from components.kpi_cards import kpi_row
from components.charts import price_trend_chart, price_distribution_chart


def page_market_overview(df: pd.DataFrame):
    st.subheader("Market Overview")
    kpi_row(df)

    col1, col2 = st.columns(2)
    with col1:
        fig_trend = price_trend_chart(df)
        if fig_trend:
            st.plotly_chart(fig_trend, use_container_width=True)
    with col2:
        fig_dist = price_distribution_chart(df)
        if fig_dist:
            st.plotly_chart(fig_dist, use_container_width=True)
