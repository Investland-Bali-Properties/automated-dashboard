from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.ui.components.charts import bar_chart, render_plotly, strip_plot, trend_with_ma
from src.ui.components.tables import render_table
from src.ui.pages.context import PageContext
from src.ui.pages.helpers import resample_median
from src.ui.utils.currency import series_to_currency


BEDROOM_BUCKETS = ["1", "2", "3-4", "5+"]


def _create_bedroom_bucket(series: pd.Series) -> pd.Series:
    bins = [0, 1, 2, 4, np.inf]
    return pd.cut(series, bins=bins, labels=BEDROOM_BUCKETS, right=True, include_lowest=True)


@st.cache_data(show_spinner=False)
def _pps_by_area_bedroom(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Area", "Bedroom Bucket", "Median PPSY"])
    working = df.dropna(subset=["area", "bedrooms", "price_per_sqm_per_year"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Area", "Bedroom Bucket", "Median PPSY"])
    working["Bedroom Bucket"] = _create_bedroom_bucket(working["bedrooms"])
    working = working[working["Bedroom Bucket"].notna()]
    working["Median PPSY"] = series_to_currency(
        working["price_per_sqm_per_year"],
        target_currency=currency,
        fallback_series=None,
    )
    agg = (
        working.groupby(["area", "Bedroom Bucket"], as_index=False)["Median PPSY"]
        .median()
        .rename(columns={"area": "Area"})
    )
    return agg.sort_values(["Area", "Bedroom Bucket"])


@st.cache_data(show_spinner=False)
def _ppsy_strip_data(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Area", "PPSY"])
    working = df.dropna(subset=["area", "price_per_sqm_per_year"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Area", "PPSY"])
    working["Area"] = working["area"]
    working["PPSY"] = series_to_currency(
        working["price_per_sqm_per_year"],
        target_currency=currency,
        fallback_series=None,
    )
    return working[["Area", "PPSY", "title", "bedrooms", "url"]].dropna(subset=["PPSY"]) if "title" in working else working[["Area", "PPSY"]]


@st.cache_data(show_spinner=False)
def _ppsy_trend(df: pd.DataFrame, currency: str, freq: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["period", "Median PPSY"])
    working = df.dropna(subset=["listing_date_effective", "price_per_sqm_per_year"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "Median PPSY"])
    working["Median PPSY"] = series_to_currency(
        working["price_per_sqm_per_year"],
        target_currency=currency,
        fallback_series=None,
    )
    trend = resample_median(working, "listing_date_effective", "Median PPSY", freq=freq)
    trend.rename(columns={"listing_date_effective": "period"}, inplace=True)
    return trend


@st.cache_data(show_spinner=False)
def _lease_bucket_ppsy(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Lease Bucket", "Median PPSY"])
    working = df.dropna(subset=["lease_years_remaining", "price_per_sqm_per_year"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Lease Bucket", "Median PPSY"])
    bins = [0, 5, 10, 20, 30, 40, 50, np.inf]
    labels = ["≤5", "6-10", "11-20", "21-30", "31-40", "41-50", "50+"]
    working["Lease Bucket"] = pd.cut(working["lease_years_remaining"], bins=bins, labels=labels, include_lowest=True)
    working["Median PPSY"] = series_to_currency(
        working["price_per_sqm_per_year"],
        target_currency=currency,
        fallback_series=None,
    )
    agg = working.groupby("Lease Bucket", as_index=False)["Median PPSY"].median()
    return agg.dropna()


@st.cache_data(show_spinner=False)
def _price_by_size_bucket(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    sales_df = df[df.get("listing_type", "").astype(str).str.lower() == "for sale"]
    if sales_df.empty:
        return pd.DataFrame(columns=["Size Bucket", "Median Price"])
    working = sales_df.dropna(subset=["building_size_sqm", "price_sale_idr"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Size Bucket", "Median Price"])
    bins = [0, 100, 200, 300, 400, 500, np.inf]
    labels = ["<100", "100-199", "200-299", "300-399", "400-499", "500+"]
    working["Size Bucket"] = pd.cut(working["building_size_sqm"], bins=bins, labels=labels, include_lowest=True)
    working["Median Price"] = series_to_currency(
        working["price_sale_idr"],
        target_currency=currency,
        fallback_series=working.get("price_usd"),
    )
    agg = working.groupby("Size Bucket", as_index=False)["Median Price"].median()
    return agg.dropna()


@st.cache_data(show_spinner=False)
def _value_opportunities(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    working = df.dropna(subset=["price_per_sqm_idr_calc", "building_size_sqm"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["title", "area", "price_per_sqm_idr_calc"])
    working = working.assign(
        PPSY=lambda d: d["price_per_sqm_per_year"],
        PricePerSqm=lambda d: d["price_per_sqm_idr_calc"],
    )
    working["PPSY"] = series_to_currency(working["PPSY"], currency, None)
    working["PricePerSqm"] = series_to_currency(working["PricePerSqm"], currency, None)

    working = working[working["building_size_sqm"] >= 50]
    if working.empty:
        return pd.DataFrame(columns=["Title", "Area", "Price per SQM", "PPSY", "Building Size (sqm)"])

    working["score"] = (
        working["PPSY"].rank(method="min") + working["PricePerSqm"].rank(method="min")
    )
    cols = {
        "title": "Title",
        "area": "Area",
        "PricePerSqm": "Price per SQM",
        "PPSY": "PPSY",
        "building_size_sqm": "Building Size (sqm)",
        "url": "URL",
    }
    result = working.sort_values("score").head(15)
    result = result[list(cols.keys())]
    return result.rename(columns=cols)


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Sales Market")
    if df.empty:
        st.info("No sales listings available for the current filter selection.")
        return

    currency = context.filters.currency
    freq = context.filters.date_granularity or "M"

    leasehold_df = df[df.get("ownership_type", "").astype(str).str.lower() == "leasehold"].copy()

    col_heatmap, col_boxplot = st.columns(2)
    with col_heatmap:
        st.markdown("#### Leasehold PPSY by Area & Bedrooms")
        grouped_df = _pps_by_area_bedroom(leasehold_df, currency)
        if grouped_df.empty:
            st.info("Leasehold PPSY breakdown unavailable.")
        else:
            fig = bar_chart(
                grouped_df,
                x="Area",
                y="Median PPSY",
                color="Bedroom Bucket",
                barmode="group",
                title="Median PPSY (Grouped by Bedrooms)",
                yaxis_title=f"PPSY ({currency})",
                yaxis_tickformat=",.0f",
            )
            render_plotly(fig)
            st.caption("Use this chart to compare leasehold PPSY across areas and bedroom sizes at a glance.")

    with col_boxplot:
        st.markdown("#### PPSY Distribution by Area")
        strip_df = _ppsy_strip_data(leasehold_df, currency)
        if strip_df.empty:
            st.info("PPSY distribution unavailable.")
        else:
            hover_cols = [col for col in ["title", "bedrooms", "url"] if col in strip_df.columns]
            fig = strip_plot(
                strip_df,
                x="Area",
                y="PPSY",
                color=None,
                title="Leasehold PPSY Spread",
                yaxis_title=f"PPSY ({currency})",
                yaxis_tickformat=",.0f",
                hover_data=hover_cols if hover_cols else None,
            )
            render_plotly(fig)
            st.caption("Each dot represents a listing; tighter clusters at lower PPSY highlight more attractive opportunities.")

    st.markdown("#### PPSY Trend (Median & MA)")
    trend_df = _ppsy_trend(leasehold_df, currency, freq)
    if trend_df.empty:
        st.info("PPSY trend unavailable.")
    else:
        fig = trend_with_ma(
            trend_df,
            x="period",
            y="Median PPSY",
            window=3,
            title="Median PPSY",
            yaxis_title="PPSY",
            yaxis_tickformat=",.0f",
        )
        render_plotly(fig)
        st.caption("Track the direction of leasehold PPSY; the dashed line shows the moving average for context.")

    st.markdown("#### Leasehold Tenure vs PPSY")
    lease_bucket_df = _lease_bucket_ppsy(leasehold_df, currency)
    if lease_bucket_df.empty:
        st.info("No leasehold tenure data available.")
    else:
        fig = bar_chart(
            lease_bucket_df,
            x="Lease Bucket",
            y="Median PPSY",
            title="Median PPSY by Lease Bucket",
            yaxis_title=f"PPSY ({currency})",
            yaxis_tickformat=",.0f",
        )
        render_plotly(fig)
        st.caption("Compare PPSY by remaining lease buckets to see which horizons offer better value.")

    st.markdown("#### Price vs Building Size")
    size_bucket_df = _price_by_size_bucket(df, currency)
    if size_bucket_df.empty:
        st.info("Not enough data to summarise price by size bucket.")
    else:
        fig = bar_chart(
            size_bucket_df,
            x="Size Bucket",
            y="Median Price",
            title="Median Sale Price by Building Size",
            yaxis_title=f"Sale Price ({currency})",
            yaxis_tickformat=",.0f",
            text_auto=True,
        )
        render_plotly(fig)
        st.caption("Review median sale price by building-size bucket to spot ranges that may be undervalued.")

    st.markdown("#### Value Opportunities")
    opportunities = _value_opportunities(df, currency)
    if opportunities.empty:
        st.info("No listings match the opportunity filters (>= 50 sqm).")
    else:
        column_config = {
            "Price per SQM": {"type": "currency", "currency": currency, "decimals": 0},
            "PPSY": {"type": "currency", "currency": currency, "decimals": 0},
            "Building Size (sqm)": {"type": "number", "decimals": 0},
        }
        render_table(opportunities, column_config=column_config, height=400, export_file_name="sales_opportunities.csv")
        st.caption("The table is sorted by lowest PPSY and price per sqm—prioritize these listings for deeper analysis.")
