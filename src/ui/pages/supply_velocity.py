from __future__ import annotations

from typing import List

import pandas as pd
import streamlit as st

from src.ui.components.charts import area_chart, bar_chart, render_plotly
from src.ui.components.kpi import KpiCard, render_kpi_cards
from src.ui.components.tables import render_table
from src.ui.pages.context import PageContext
from src.ui.pages.helpers import pct_change, resample_median, safe_median


@st.cache_data(show_spinner=False)
def _new_listings_ts(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if df.empty or "listing_date_effective" not in df:
        return pd.DataFrame(columns=["period", "Listings"])
    working = df.dropna(subset=["listing_date_effective"]).copy()
    if "property_id" in working:
        ts = (
            working.set_index("listing_date_effective")
            .groupby(pd.Grouper(freq=freq))["property_id"]
            .nunique()
            .reset_index(name="Listings")
        )
    else:
        ts = (
            working.set_index("listing_date_effective")
            .groupby(pd.Grouper(freq=freq))
            .size()
            .reset_index(name="Listings")
        )
    ts.rename(columns={"listing_date_effective": "period"}, inplace=True)
    return ts


@st.cache_data(show_spinner=False)
def _sales_volume_ts(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    status = df.get("listing_status_labels")
    if status is None or "listing_date_effective" not in df:
        return pd.DataFrame(columns=["period", "Sales Volume"])
    working = df.dropna(subset=["listing_date_effective"]).copy()
    mask = working["listing_status_labels"].astype(str).str.contains("sold|under offer", regex=True, case=False)
    sold = working[mask]
    if sold.empty:
        return pd.DataFrame(columns=["period", "Sales Volume"])
    if "property_id" in sold:
        ts = (
            sold.set_index("listing_date_effective")
            .groupby(pd.Grouper(freq=freq))["property_id"]
            .nunique()
            .reset_index(name="Sales Volume")
        )
    else:
        ts = (
            sold.set_index("listing_date_effective")
            .groupby(pd.Grouper(freq=freq))
            .size()
            .reset_index(name="Sales Volume")
        )
    ts.rename(columns={"listing_date_effective": "period"}, inplace=True)
    return ts


def _velocity_kpis(df: pd.DataFrame, freq: str) -> List[KpiCard]:
    listings_ts = _new_listings_ts(df, freq)
    latest_listings = listings_ts.iloc[-1]["Listings"] if not listings_ts.empty else None
    previous_listings = listings_ts.iloc[-2]["Listings"] if len(listings_ts) > 1 else None
    growth = pct_change(latest_listings, previous_listings)

    days_median = safe_median(df.get("days_listed", pd.Series(dtype=float)))

    status = df.get("listing_status_labels")
    sales_volume = 0.0
    if status is not None:
        sales_volume = float(status.astype(str).str.contains("sold|under offer", regex=True, case=False).sum())

    cards = [
        KpiCard("New Listings", value=latest_listings, decimals=0),
        KpiCard("Supply Growth", value=growth, value_display=f"{growth:.1f}%" if growth is not None else "–"),
        KpiCard("Median Days Listed", value=days_median, decimals=0),
        KpiCard("Sales Volume", value=sales_volume, decimals=0),
    ]
    return cards


@st.cache_data(show_spinner=False)
def _stacked_supply(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if df.empty or "listing_date_effective" not in df:
        return pd.DataFrame(columns=["period", "Category", "Listings"])
    category_col = "area" if "area" in df.columns else "property_type"
    if category_col not in df.columns:
        return pd.DataFrame(columns=["period", "Category", "Listings"])
    working = df.dropna(subset=["listing_date_effective", category_col]).copy()
    grouped = (
        working.set_index("listing_date_effective")
        .groupby([pd.Grouper(freq=freq), category_col])
        .size()
        .reset_index(name="Listings")
        .rename(columns={"listing_date_effective": "period", category_col: "Category"})
    )
    return grouped


@st.cache_data(show_spinner=False)
def _days_listed_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "days_listed" not in df or "area" not in df:
        return pd.DataFrame(columns=["Area", "Median Days"])
    working = df.dropna(subset=["days_listed", "area"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Area", "Median Days"])
    summary = (
        working.groupby("area")["days_listed"]
        .median()
        .reset_index(name="Median Days")
        .rename(columns={"area": "Area"})
        .sort_values("Median Days")
    )
    return summary.head(15)


@st.cache_data(show_spinner=False)
def _region_leaderboard(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if df.empty or "area" not in df or "listing_date_effective" not in df:
        return pd.DataFrame(columns=["Area", "Listings", "Growth %", "Median Days", "Conversion %"])
    working = df.dropna(subset=["area", "listing_date_effective"]).copy()
    counts = (
        working.set_index("listing_date_effective")
        .groupby(["area", pd.Grouper(freq=freq)])
        .size()
        .reset_index(name="Listings")
        .rename(columns={"listing_date_effective": "period"})
    )
    records = []
    sold_mask = working.get("listing_status_labels", pd.Series(dtype=str)).astype(str).str.contains("sold|under offer", regex=True, case=False) if "listing_status_labels" in working else pd.Series(False, index=working.index)
    for area, area_df in counts.groupby("area"):
        area_df = area_df.sort_values("period")
        latest = area_df.iloc[-1]
        previous = area_df.iloc[-2] if len(area_df) > 1 else None
        growth = pct_change(latest["Listings"], previous["Listings"] if previous is not None else None)
        subset = working[working["area"] == area]
        median_days = safe_median(subset.get("days_listed", pd.Series(dtype=float)))
        conversion = None
        if "listing_status_labels" in working:
            sold_count = subset[sold_mask.loc[subset.index]].shape[0]
            total = subset.shape[0]
            conversion = (sold_count / total * 100) if total else None
        records.append(
            {
                "Area": area,
                "Listings": latest["Listings"],
                "Growth %": growth,
                "Median Days": median_days,
                "Conversion %": conversion,
            }
        )
    leaderboard = pd.DataFrame(records)
    if leaderboard.empty:
        return leaderboard
    leaderboard.sort_values("Listings", ascending=False, inplace=True)
    return leaderboard.head(15)


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Supply & Velocity")
    if df.empty:
        st.info("No listings available to analyse supply dynamics.")
        return

    freq = context.filters.date_granularity or "M"

    cards = _velocity_kpis(df, freq)
    render_kpi_cards(cards, columns=4)

    st.markdown("#### New Listings Trend")
    stacked = _stacked_supply(df, freq)
    if stacked.empty:
        st.info("Supply trend unavailable.")
    else:
        fig = area_chart(
            stacked,
            x="period",
            y="Listings",
            color="Category",
            title="New Listings by Segment",
            yaxis_title="Listings",
        )
        render_plotly(fig)
        st.caption("Use the area chart to spot surges in new listings and how each segment contributes.")

    st.markdown("#### Sales Volume by Period")
    sales_ts = _sales_volume_ts(df, freq)
    if sales_ts.empty:
        st.info("Sales volume data unavailable.")
    else:
        fig = bar_chart(
            sales_ts,
            x="period",
            y="Sales Volume",
            title="Sales Volume",
            yaxis_title="Listings",
        )
        render_plotly(fig)
        st.caption("Watch for peaks in sales volume to gauge market momentum.")

    st.markdown("#### Median Days Listed by Region")
    days_df = _days_listed_summary(df)
    if days_df.empty:
        st.info("Days listed distribution unavailable.")
    else:
        fig = bar_chart(
            days_df,
            x="Area",
            y="Median Days",
            title="Median Days Listed",
            yaxis_title="Days",
            text_auto=True,
        )
        fig.update_layout(xaxis={'categoryorder': 'total descending'})
        render_plotly(fig)
        st.caption("Shorter median days mean listings turn over faster in that area.")

    st.markdown("#### Region Leaderboard")
    leaderboard = _region_leaderboard(df, freq)
    if leaderboard.empty:
        st.info("Insufficient data for regional leaderboard.")
    else:
        column_config = {
            "Growth %": {"type": "percent", "decimals": 1},
            "Median Days": {"type": "number", "decimals": 0},
            "Conversion %": {"type": "percent", "decimals": 1},
        }
        render_table(leaderboard, column_config=column_config, height=380, export_file_name="supply_leaderboard.csv")
        st.caption("Use the leaderboard to pinpoint regions with the best mix of supply growth, speed, and conversion.")
