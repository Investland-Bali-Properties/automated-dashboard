from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.charts import area_chart, bar_chart, render_plotly
from src.ui.components.tables import render_table
from src.ui.pages.context import PageContext
from src.ui.pages.helpers import resample_median
from src.ui.utils.currency import series_to_currency


def _ownership_by_region(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "area" not in df or "ownership_type" not in df:
        return pd.DataFrame(columns=["Area", "Ownership", "Listings"])
    working = df.dropna(subset=["area", "ownership_type"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Area", "Ownership", "Listings"])
    if "property_id" in working:
        grouped = (
            working.groupby(["area", "ownership_type"])["property_id"]
            .nunique()
            .reset_index(name="Listings")
        )
    else:
        grouped = (
            working.groupby(["area", "ownership_type"])
            .size()
            .reset_index(name="Listings")
        )
    total = grouped.groupby("area")["Listings"].transform("sum")
    grouped["Share"] = (grouped["Listings"] / total) * 100
    grouped.rename(columns={"area": "Area", "ownership_type": "Ownership"}, inplace=True)
    grouped.sort_values(["Area", "Share"], ascending=[True, False], inplace=True)
    top_areas = grouped["Area"].unique()[:10]
    return grouped[grouped["Area"].isin(top_areas)]


def _price_per_sqm_by_ownership(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    if df.empty or "ownership_type" not in df or "price_per_sqm_idr_calc" not in df:
        return pd.DataFrame(columns=["Ownership", "Median Price per SQM"])
    working = df.dropna(subset=["ownership_type", "price_per_sqm_idr_calc"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Ownership", "Median Price per SQM"])
    working["Price"] = series_to_currency(
        working["price_per_sqm_idr_calc"],
        target_currency=currency,
        fallback_series=None,
    )
    agg = (
        working.groupby("ownership_type")["Price"]
        .median()
        .reset_index(name="Median Price per SQM")
        .rename(columns={"ownership_type": "Ownership"})
    )
    return agg


def _ppsy_comparison(df: pd.DataFrame, currency: str, include_freehold: bool) -> pd.DataFrame:
    if df.empty or "price_per_sqm_per_year" not in df:
        return pd.DataFrame(columns=["Ownership", "PPSY"])
    working = df.copy()
    records = []
    lease = working.dropna(subset=["price_per_sqm_per_year"]) if "price_per_sqm_per_year" in working else pd.DataFrame()
    if not lease.empty:
        lease_ppsy = series_to_currency(lease["price_per_sqm_per_year"], currency, None)
        records.append({
            "Ownership": "Leasehold",
            "PPSY": lease_ppsy.median(),
        })
    if include_freehold and "price_per_sqm_per_year_freehold_assumed" in working:
        freehold = working.dropna(subset=["price_per_sqm_per_year_freehold_assumed"])
        if not freehold.empty:
            freehold_ppsy = series_to_currency(
                freehold["price_per_sqm_per_year_freehold_assumed"],
                currency,
                None,
            )
            records.append({
                "Ownership": "Freehold (Assumed)",
                "PPSY": freehold_ppsy.median(),
            })
    return pd.DataFrame(records)


def _ownership_trend(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if df.empty or "listing_date_effective" not in df or "ownership_type" not in df:
        return pd.DataFrame(columns=["period", "Ownership", "Listings"])
    working = df.dropna(subset=["listing_date_effective", "ownership_type"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "Ownership", "Listings"])
    grouped = (
        working.set_index("listing_date_effective")
        .groupby([pd.Grouper(freq=freq), "ownership_type"])
        .size()
        .reset_index(name="Listings")
        .rename(columns={"listing_date_effective": "period", "ownership_type": "Ownership"})
    )
    totals = grouped.groupby("period")["Listings"].transform("sum")
    grouped["Share"] = grouped["Listings"] / totals * 100
    return grouped


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Ownership Mix")
    if df.empty:
        st.info("No listings to display ownership information.")
        return

    currency = context.filters.currency
    freq = context.filters.date_granularity or "M"

    st.markdown("#### Ownership Share by Region")
    ownership_region = _ownership_by_region(df)
    if ownership_region.empty:
        st.info("Ownership breakdown by region unavailable.")
    else:
        fig = bar_chart(
            ownership_region,
            x="Area",
            y="Share",
            color="Ownership",
            barmode="stack",
            title="Leasehold vs Freehold Share (Top Areas)",
            yaxis_title="Share (%)",
            yaxis_tickformat=".1f",
        )
        render_plotly(fig)

    st.markdown("#### Price per SQM by Tenure")
    price_sq = _price_per_sqm_by_ownership(df, currency)
    if price_sq.empty:
        st.info("Price per SQM comparison unavailable.")
    else:
        fig = bar_chart(
            price_sq,
            x="Ownership",
            y="Median Price per SQM",
            title="Median Price per SQM by Ownership",
            yaxis_title=f"Price per SQM ({currency})",
            yaxis_tickformat=",.0f",
            barmode="group",
        )
        render_plotly(fig)

    if context.filters.ppsy_toggle_freehold:
        st.markdown("#### PPSY Comparison")
        ppsy_df = _ppsy_comparison(df, currency, include_freehold=True)
        if ppsy_df.empty:
            st.info("PPSY comparison unavailable.")
        else:
            fig = bar_chart(
                ppsy_df,
                x="Ownership",
                y="PPSY",
                title="Leasehold vs Freehold PPSY",
                yaxis_title=f"PPSY ({currency})",
                yaxis_tickformat=",.0f",
            )
            render_plotly(fig)

    st.markdown("#### Ownership Share Trend")
    trend = _ownership_trend(df, freq)
    if trend.empty:
        st.info("Ownership trend unavailable.")
    else:
        fig = area_chart(
            trend,
            x="period",
            y="Share",
            color="Ownership",
            title="Ownership Share Over Time",
            yaxis_title="Share (%)",
        )
        render_plotly(fig)

    leaderboard = _ownership_by_region(df)
    if not leaderboard.empty:
        st.markdown("#### Ownership Share Table")
        render_table(
            leaderboard.rename(columns={"Listings": "Listings (count)"}),
            column_config={"Share": {"type": "percent", "decimals": 1}},
            height=360,
            export_file_name="ownership_by_region.csv",
        )
