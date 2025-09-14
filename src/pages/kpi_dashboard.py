import streamlit as st
import pandas as pd
import plotly.express as px
from components.kpis_extended import (
    median_sales_price,
    median_available_price,
    price_per_sqm_region,
    supply_growth,
    leasehold_freehold_share,
    days_listed_stats,
)


def page_kpi_dashboard(df: pd.DataFrame):
    st.subheader("Core KPIs")
    if df.empty:
        st.info("No data for current filters.")
        return

    with st.expander("Controls", expanded=False):
        agg_growth = st.selectbox("Supply Growth Aggregation", ["property_type","listing_type","property_status"], index=0)

    # Row 1: Median Sales & Median Available
    sale_df = median_sales_price(df)
    avail_df = median_available_price(df)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Median Sales Price")
        if sale_df.empty:
            st.caption("Insufficient data or columns for sales segmentation.")
        else:
            st.dataframe(sale_df.head(100), width="stretch")
    with col2:
        st.markdown("### Median Available Price")
        if avail_df.empty:
            st.caption("Insufficient data or columns for available segmentation.")
        else:
            st.dataframe(avail_df.head(100), width="stretch")

    # Row 2: Price per SQM Region
    st.markdown("### Price per SQM by Region")
    region_pps = price_per_sqm_region(df)
    if not region_pps:
        st.caption("Cannot compute price per sqm by region (missing columns).")
    else:
        region_table, overall = region_pps
        colr1, colr2 = st.columns([3,1])
        with colr1:
            st.dataframe(region_table.head(100), width="stretch")
        with colr2:
            st.write("**Overall Median**")
            st.metric("Median PPS (IDR)", f"{overall['overall_median_pps_idr'].iloc[0]:,.0f}")
            st.caption(f"Listings used: {overall['overall_listings'].iloc[0]:,}")

    # Row 3: Supply Growth
    st.markdown("### Supply Growth (MoM %)")
    growth_df = supply_growth(df, segment_col=agg_growth)
    if growth_df.empty:
        st.caption("Insufficient time or region data for supply growth.")
    else:
        latest_months = growth_df['month'].drop_duplicates().sort_values().tail(3)
        filt_growth = growth_df[growth_df['month'].isin(latest_months)]
        st.dataframe(filt_growth.head(300), width="stretch")
        # Optional chart focus on overall region aggregated
        pivot = (growth_df.dropna(subset=['mom_growth_pct'])
                 .groupby('month')['mom_growth_pct'].mean().reset_index())
        if not pivot.empty:
            fig = px.bar(pivot, x='month', y='mom_growth_pct', title='Average MoM Supply Growth (%)')
            st.plotly_chart(fig, width="stretch")

    # Row 4: Leasehold vs Freehold
    st.markdown("### Leasehold vs Freehold Share")
    tenure_share = leasehold_freehold_share(df)
    if tenure_share.empty:
        st.caption("Tenure data not available.")
    else:
        st.dataframe(tenure_share, width="stretch")
        fig_tenure = px.pie(tenure_share, names='tenure_bucket', values='pct_share', title='Tenure Share (%)')
        st.plotly_chart(fig_tenure, width="stretch")

    # Row 5: Days Listed Stats
    st.markdown("### Days Listed Stats")
    days_stats = days_listed_stats(df)
    if days_stats.empty:
        st.caption("Cannot compute days listed (missing first/last seen columns).")
    else:
        st.dataframe(days_stats, width="stretch")

    st.caption("Phase 1 KPIs complete. Further metrics (sales volume, ADR, off-plan, regional heatmap) will appear in next phase.")
