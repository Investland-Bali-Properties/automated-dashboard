import streamlit as st
import pandas as pd
from components.charts import (
    price_per_sqm_by_area,
    boxplot_price_per_sqm,
    rent_vs_sale_distribution,
)


def page_pricing_trends(df: pd.DataFrame):
    st.subheader("Pricing Trends")
    if df.empty:
        st.info("No data for current filters.")
        return

    with st.expander("Controls", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            top_n = st.slider("Top N Areas", 5, 30, 15)
        with col2:
            show_box = st.checkbox("Show Boxplot", value=True)
        with col3:
            show_violin = st.checkbox("Show Rent vs Sale", value=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_area = price_per_sqm_by_area(df, top_n=top_n)
        if fig_area:
            st.plotly_chart(fig_area, width="stretch")
    with col2:
        if show_box:
            fig_box = boxplot_price_per_sqm(df)
            if fig_box:
                st.plotly_chart(fig_box, width="stretch")

    if show_violin:
        fig_violin = rent_vs_sale_distribution(df)
        if fig_violin:
            st.plotly_chart(fig_violin, width="stretch")