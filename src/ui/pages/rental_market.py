from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.ui.components.charts import (
    bar_chart,
    histogram,
    line_chart,
    render_plotly,
)
from src.ui.components.kpi import KpiCard, render_kpi_cards
from src.ui.components.tables import render_table
from src.ui.pages.context import PageContext
from src.ui.pages.helpers import resample_median, safe_median
from src.ui.utils.currency import series_to_currency, scalar_to_currency


BEDROOM_BUCKETS = ["Studio", "1", "2", "3-4", "5+"]


def _bedroom_bucket(series: pd.Series) -> pd.Series:
    bins = [-np.inf, 0.5, 1.5, 2.5, 4.5, np.inf]
    return pd.cut(series.fillna(0), bins=bins, labels=BEDROOM_BUCKETS, include_lowest=True)


def _split_by_seller(df: pd.DataFrame) -> str:
    seller_cols = ["seller_type", "source_category"]
    for col in seller_cols:
        if col in df:
            return col
    return "source_category"


@st.cache_data(show_spinner=False)
def _adr_grouped(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    working = df.dropna(subset=["area", "bedrooms", "adr_idr"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Area", "Bedroom Bucket", "ADR"])
    working["Bedroom Bucket"] = _bedroom_bucket(working["bedrooms"])
    working = working[working["Bedroom Bucket"].notna()]
    working["ADR"] = series_to_currency(working["adr_idr"], currency, None)
    agg = (
        working.groupby(["Bedroom Bucket", "area"], as_index=False)["ADR"]
        .median()
        .rename(columns={"area": "Area"})
    )
    return agg.sort_values(["Area", "Bedroom Bucket"])


@st.cache_data(show_spinner=False)
def _adr_by_bedrooms(df: pd.DataFrame, currency: str, seller_col: str) -> pd.DataFrame:
    if df.empty or seller_col not in df:
        return pd.DataFrame(columns=["Bedrooms", "Seller", "ADR"])
    working = df.dropna(subset=[seller_col, "bedrooms", "adr_idr"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Bedrooms", "Seller", "ADR"])
    working["Bedrooms"] = _bedroom_bucket(working["bedrooms"])
    working = working[working["Bedrooms"].notna()]
    working["ADR"] = series_to_currency(working["adr_idr"], currency, None)
    grouped = (
        working.groupby(["Bedrooms", seller_col], as_index=False)["ADR"]
        .median()
        .rename(columns={seller_col: "Seller"})
    )
    return grouped


@st.cache_data(show_spinner=False)
def _adr_trend(df: pd.DataFrame, currency: str, freq: str) -> pd.DataFrame:
    working = df.dropna(subset=["listing_date_effective", "adr_idr"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "Median ADR"])
    working["Median ADR"] = series_to_currency(working["adr_idr"], currency, None)
    trend = resample_median(working, "listing_date_effective", "Median ADR", freq=freq)
    trend.rename(columns={"listing_date_effective": "period"}, inplace=True)
    return trend


@st.cache_data(show_spinner=False)
def _occupancy_trend(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if "occupancy" not in df.columns:
        return pd.DataFrame(columns=["period", "Median Occupancy"])
    working = df.dropna(subset=["listing_date_effective", "occupancy"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "Median Occupancy"])
    trend = resample_median(working, "listing_date_effective", "occupancy", freq=freq)
    trend.rename(columns={"listing_date_effective": "period", "occupancy": "Median Occupancy"}, inplace=True)
    return trend


@st.cache_data(show_spinner=False)
def _occupancy_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "occupancy" not in df.columns:
        empty = pd.DataFrame(columns=["Title", "Area", "Occupancy %"])
        return empty, empty
    working = df.dropna(subset=["occupancy"]).copy()
    if working.empty:
        empty = pd.DataFrame(columns=["Title", "Area", "Occupancy %"])
        return empty, empty
    base_cols = [col for col in ["title", "area", "occupancy", "url"] if col in working.columns]
    table = working[base_cols].rename(columns={"title": "Title", "area": "Area", "occupancy": "Occupancy %", "url": "URL"})
    best = table.sort_values("Occupancy %", ascending=False).head(10)
    worst = table.sort_values("Occupancy %", ascending=True).head(10)
    return best, worst


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Rental Market (ADR & Occupancy)")
    rent_df = df[df["rent_price_month_idr_norm"].notna()].copy()
    if rent_df.empty:
        st.info("No rental listings available for the current filter selection.")
        return

    currency = context.filters.currency
    freq = context.filters.date_granularity or "M"
    seller_col = _split_by_seller(rent_df)

    median_adr = safe_median(rent_df.get("adr_idr", pd.Series(dtype=float)))
    median_adr_currency = scalar_to_currency(median_adr, currency)
    median_monthly_rent = scalar_to_currency(safe_median(rent_df.get("rent_price_month_idr_norm")), currency)
    occupancy_median = safe_median(rent_df.get("occupancy", pd.Series(dtype=float)))
    revenue_proxy = None
    if median_adr_currency is not None and occupancy_median is not None:
        revenue_proxy = median_adr_currency * (occupancy_median / 100) * 30

    cards = [
        KpiCard("Median ADR", value=median_adr_currency, currency=currency, decimals=0),
        KpiCard("Median Monthly Rent", value=median_monthly_rent, currency=currency, decimals=0),
        KpiCard("Median Occupancy", value=occupancy_median, value_display=f"{occupancy_median:.1f}%" if occupancy_median is not None else "–"),
        KpiCard("Revenue Proxy (30d)", value=revenue_proxy, currency=currency, decimals=0, help_text="Median ADR * Occupancy * 30"),
    ]
    render_kpi_cards(cards, columns=4)

    st.markdown("#### ADR by Bedrooms & Seller Type")
    seller_split = _adr_by_bedrooms(rent_df, currency, seller_col)
    if seller_split.empty:
        st.info("ADR breakdown unavailable.")
    else:
        fig = line_chart(
            seller_split,
            x="Bedrooms",
            y="ADR",
            color="Seller",
            markers=True,
            title="ADR by Bedrooms (Professional vs Individual)",
            yaxis_title=f"ADR ({currency})",
            yaxis_tickformat=",.0f",
        )
        render_plotly(fig)
        st.caption("Compare median ADR between professional and individual operators for each bedroom type.")

    st.markdown("#### ADR by Area & Bedrooms")
    heat_df = _adr_grouped(rent_df, currency)
    if heat_df.empty:
        st.info("ADR breakdown unavailable.")
    else:
        fig = bar_chart(
            heat_df,
            x="Area",
            y="ADR",
            color="Bedroom Bucket",
            barmode="group",
            title="Median ADR by Area (Grouped by Bedrooms)",
            yaxis_title=f"ADR ({currency})",
            yaxis_tickformat=",.0f",
        )
        render_plotly(fig)
        st.caption("See which areas lead ADR for each bedroom configuration.")

    st.markdown("#### ADR & Occupancy Trends")
    col_adr, col_occ = st.columns(2)
    adr_trend = _adr_trend(rent_df, currency, freq)
    with col_adr:
        if adr_trend.empty:
            st.info("ADR trend unavailable.")
        else:
            fig = line_chart(
                adr_trend,
                x="period",
                y="Median ADR",
                title="Median ADR",
                yaxis_title=f"ADR ({currency})",
                yaxis_tickformat=",.0f",
            )
            render_plotly(fig)
            st.caption("The ADR line helps you track rental momentum after filters are applied.")

    occupancy_trend = _occupancy_trend(rent_df, freq)
    with col_occ:
        if occupancy_trend.empty:
            st.info("Occupancy trend unavailable.")
        else:
            fig = line_chart(
                occupancy_trend,
                x="period",
                y="Median Occupancy",
                title="Median Occupancy",
                yaxis_title="Occupancy (%)",
                yaxis_tickformat=".1f",
            )
            render_plotly(fig)
            st.caption("Monitor how occupancy evolves—ideally it moves in the same direction as ADR.")

    st.markdown("#### ADR Distribution")
    hist_df = rent_df[rent_df["adr_idr"].notna()].copy()
    if hist_df.empty:
        st.info("Not enough ADR data for histogram.")
    else:
        hist_df["ADR"] = series_to_currency(hist_df["adr_idr"], currency, None)
        fig = histogram(
            hist_df,
            x="ADR",
            nbins=30,
            title="ADR Distribution",
            yaxis_title="Listings",
        )
        if not hist_df["ADR"].dropna().empty:
            median_adr_value = float(hist_df["ADR"].median())
            fig.add_vline(
                x=median_adr_value,
                line_dash="dash",
                line_color="#d62728",
                annotation_text=f"Median ({median_adr_value:,.0f})",
                annotation_position="top",
            )
        render_plotly(fig)
        st.caption("The distribution highlights dominant ADR ranges; check the right tail for premium listings.")

    st.markdown("#### Occupancy Leaders & Laggards")
    top_occ, low_occ = _occupancy_tables(rent_df)
    if top_occ.empty:
        st.info("Occupancy details unavailable for listings.")
    else:
        col_top, col_low = st.columns(2)
        with col_top:
            st.caption("Highest Occupancy")
            render_table(top_occ, column_config={"Occupancy %": {"type": "percent", "decimals": 1}}, height=300, export_file_name="occupancy_high.csv")
            st.caption("These listings maintain high occupancy—use them as benchmarks for rental strategy.")
        with col_low:
            st.caption("Lowest Occupancy")
            render_table(low_occ, column_config={"Occupancy %": {"type": "percent", "decimals": 1}}, height=300, export_file_name="occupancy_low.csv")
            st.caption("Review low-occupancy listings for pricing or promotional adjustments.")
