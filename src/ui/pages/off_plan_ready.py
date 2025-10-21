from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.charts import bar_chart, line_chart, render_plotly
from src.ui.pages.context import PageContext
from src.ui.utils.currency import series_to_currency


@st.cache_data(show_spinner=False)
def _ppsy_by_status(df: pd.DataFrame, currency: str, dimension: str) -> pd.DataFrame:
    if df.empty or "property_status" not in df or dimension not in df or "price_per_sqm_per_year" not in df:
        return pd.DataFrame(columns=[dimension, "property_status", "PPSY"])
    working = df.dropna(subset=["property_status", dimension, "price_per_sqm_per_year"]).copy()
    if working.empty:
        return pd.DataFrame(columns=[dimension, "property_status", "PPSY"])
    working["PPSY"] = series_to_currency(working["price_per_sqm_per_year"], currency, None)
    grouped = (
        working.groupby([dimension, "property_status"], as_index=False)["PPSY"]
        .median()
        .rename(columns={dimension: "Dimension", "property_status": "Status"})
    )
    return grouped


@st.cache_data(show_spinner=False)
def _status_share_trend(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if df.empty or "listing_date_effective" not in df or "property_status" not in df:
        return pd.DataFrame(columns=["period", "Status", "Listings"])
    working = df.dropna(subset=["listing_date_effective", "property_status"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "Status", "Listings"])
    grouped = (
        working.set_index("listing_date_effective")
        .groupby([pd.Grouper(freq=freq), "property_status"])
        .size()
        .reset_index(name="Listings")
        .rename(columns={"listing_date_effective": "period", "property_status": "Status"})
    )
    totals = grouped.groupby("period")["Listings"].transform("sum")
    grouped["Share"] = grouped["Listings"] / totals * 100
    return grouped


@st.cache_data(show_spinner=False)
def _days_listed_status(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "property_status" not in df or "days_listed" not in df:
        return pd.DataFrame(columns=["Status", "Median Days"])
    working = df.dropna(subset=["property_status", "days_listed"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Status", "Median Days"])
    summary = (
        working.groupby("property_status")["days_listed"]
        .median()
        .reset_index(name="Median Days")
        .rename(columns={"property_status": "Status"})
    )
    return summary.sort_values("Median Days")


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Off-plan vs Ready")
    if df.empty:
        st.info("No listings available to compare project readiness.")
        return

    currency = context.filters.currency
    freq = context.filters.date_granularity or "M"

    st.markdown("#### Leasehold PPSY Comparison")
    dimension_options = [col for col in ["area", "bedrooms"] if col in df.columns]
    if not dimension_options:
        st.info("No categorical fields available for comparison.")
    else:
        default_index = 0
        dimension = st.selectbox(
            "Breakdown by",
            options=dimension_options,
            index=default_index,
            key="sa_offplan_dimension",
        )
        ppsy_df = _ppsy_by_status(df, currency, dimension)
        if ppsy_df.empty:
            st.info("PPSY comparison unavailable for the selected dimension.")
        else:
            title_dim = "Area" if dimension == "area" else "Bedrooms"
            fig = bar_chart(
                ppsy_df,
                x="Dimension",
                y="PPSY",
                color="Status",
                barmode="group",
                title=f"Median PPSY by {title_dim}",
                yaxis_title=f"PPSY ({currency})",
                yaxis_tickformat=",.0f",
            )
            render_plotly(fig)
            st.caption("Compare leasehold PPSY between off-plan and ready stock for the selected dimension.")

    st.markdown("#### Off-plan Share Trend")
    trend = _status_share_trend(df, freq)
    if trend.empty:
        st.info("Off-plan trend unavailable.")
    else:
        fig = line_chart(
            trend,
            x="period",
            y="Share",
            color="Status",
            title="Project Status Share Over Time",
            yaxis_title="Share (%)",
            yaxis_tickformat=".1f",
        )
        render_plotly(fig)
        st.caption("Track how the off-plan versus ready mix shifts over time.")

    st.markdown("#### Days Listed by Status")
    days_df = _days_listed_status(df)
    if days_df.empty:
        st.info("No days listed data available by status.")
    else:
        fig = bar_chart(
            days_df,
            x="Status",
            y="Median Days",
            title="Median Days Listed by Status",
            yaxis_title="Days",
            text_auto=True,
        )
        render_plotly(fig)
        st.caption("See which status type clears faster based on median days listed.")
