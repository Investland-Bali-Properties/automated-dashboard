from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
import streamlit as st

from src.ui.components.charts import bar_chart, line_chart, render_plotly
from src.ui.components.kpi import KpiCard, render_kpi_cards
from src.ui.components.tables import render_table
from src.ui.pages.context import PageContext
from src.ui.pages.helpers import (
    pct_change,
    resample_median,
    safe_median,
)
from src.ui.utils.currency import scalar_to_currency, series_to_currency


def _median_for_currency(
    df: pd.DataFrame,
    value_col: str,
    currency: str,
    fallback_col: str | None = None,
) -> float | None:
    median_idr = safe_median(df[value_col]) if value_col in df else None
    fallback_series = df.get(fallback_col) if fallback_col else None
    median_usd = safe_median(fallback_series) if fallback_series is not None else None
    return scalar_to_currency(median_idr, target_currency=currency, fallback_value=median_usd)


def _prepare_trend(
    df: pd.DataFrame,
    value_col: str,
    currency: str,
    fallback_col: str | None,
    label: str,
    freq: str,
) -> pd.DataFrame:
    if df.empty or "listing_date_effective" not in df:
        return pd.DataFrame(columns=["period", label])

    working = df.dropna(subset=["listing_date_effective", value_col]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", label])

    fallback_series = working.get(fallback_col) if fallback_col else None
    working[label] = series_to_currency(working[value_col], currency, fallback_series)
    ts = resample_median(working, "listing_date_effective", label, freq=freq)
    ts.rename(columns={"listing_date_effective": "period"}, inplace=True)
    return ts.dropna()


def _ownership_mix(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "ownership_type" not in df:
        return pd.DataFrame(columns=["Ownership", "Listings"])
    working = df[df["ownership_type"].notna()].copy()
    if working.empty:
        return pd.DataFrame(columns=["Ownership", "Listings"])

    if "property_id" in working:
        grouped = (
            working.groupby("ownership_type")["property_id"]
            .nunique()
            .reset_index(name="Listings")
        )
    else:
        grouped = (
            working.groupby("ownership_type")
            .size()
            .reset_index(name="Listings")
        )
    total = grouped["Listings"].sum()
    if total > 0:
        grouped["Share"] = grouped["Listings"] / total * 100
    grouped.rename(columns={"ownership_type": "Ownership"}, inplace=True)
    return grouped.sort_values("Listings", ascending=False)


def _supply_by_region(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "area" not in df:
        return pd.DataFrame(columns=["Area", "Listings"])
    working = df[df["area"].notna()].copy()
    if working.empty:
        return pd.DataFrame(columns=["Area", "Listings"])
    if "property_id" in working:
        grouped = (
            working.groupby("area")["property_id"]
            .nunique()
            .reset_index(name="Listings")
        )
    else:
        grouped = (
            working.groupby("area")
            .size()
            .reset_index(name="Listings")
        )
    grouped.rename(columns={"area": "Area"}, inplace=True)
    return grouped.sort_values("Listings", ascending=False).head(10)


def _regional_movers(
    df: pd.DataFrame,
    freq: str,
) -> pd.DataFrame:
    if df.empty or "area" not in df or "listing_date_effective" not in df:
        return pd.DataFrame(columns=["Area", "Supply Growth %", "PPSQM Change %"])

    working = df.dropna(subset=["area", "listing_date_effective"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Area", "Supply Growth %", "PPSQM Change %"])

    grouped = working.set_index("listing_date_effective").groupby(
        ["area", pd.Grouper(freq=freq)]
    )

    supply = grouped.size().reset_index(name="supply")
    price = grouped["price_per_sqm_idr_calc"].median().reset_index(name="price_per_sqm")
    merged = supply.merge(price, on=["area", "listing_date_effective"], how="left")
    merged.rename(columns={"listing_date_effective": "period"}, inplace=True)
    merged.sort_values(["area", "period"], inplace=True)

    if merged.empty:
        return pd.DataFrame(columns=["Area", "Supply Growth %", "PPSQM Change %"])

    records: List[dict] = []
    for area, area_df in merged.groupby("area"):
        if len(area_df) < 2:
            continue
        latest = area_df.iloc[-1]
        previous = area_df.iloc[-2]
        supply_growth = pct_change(latest["supply"], previous["supply"])
        price_change = pct_change(latest["price_per_sqm"], previous["price_per_sqm"])
        if supply_growth is None and price_change is None:
            continue
        records.append(
            {
                "Area": area,
                "Latest Period": latest["period"].date() if hasattr(latest["period"], "date") else latest["period"],
                "Supply Growth %": supply_growth,
                "PPSQM Change %": price_change,
            }
        )

    movers = pd.DataFrame(records)
    if movers.empty:
        return movers
    movers.sort_values(
        by=["Supply Growth %", "PPSQM Change %"],
        key=lambda col: col.abs().fillna(0),
        ascending=False,
        inplace=True,
    )
    return movers.head(10)


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Overview")
    if df.empty:
        st.info("No listings available for the current filter selection.")
        return

    currency = context.filters.currency
    freq = context.filters.date_granularity or "M"

    listing_type_series = df.get("listing_type", pd.Series(dtype=str)).astype(str).str.lower()
    sales_df = df[listing_type_series == "for sale"]
    rent_df = df[df["rent_price_month_idr_norm"].notna()]
    leasehold_df = df[df.get("ownership_type", "").astype(str).str.lower() == "leasehold"]

    median_sales_price = _median_for_currency(sales_df, "price_sale_idr", currency, "price_usd")
    median_rent_price = _median_for_currency(rent_df, "rent_price_month_idr_norm", currency, None)
    median_ppsqm = _median_for_currency(df, "price_per_sqm_idr_calc", currency, None)
    median_days_listed = safe_median(df.get("days_listed", pd.Series(dtype=float)))
    supply = float(df["property_id"].nunique()) if "property_id" in df else float(len(df))
    status_labels = df.get("listing_status_labels")
    sales_volume = 0.0
    if status_labels is not None:
        status_series = status_labels.astype(str).str.lower()
        sales_volume = float(status_series.str.contains("sold|under offer", regex=True).sum())
    median_ppsy = _median_for_currency(leasehold_df, "price_per_sqm_per_year", currency, None)

    cards: List[KpiCard] = [
        KpiCard(
            label="Median Sales Price",
            value=median_sales_price,
            currency=currency,
            decimals=0,
        ),
        KpiCard(
            label="Median Monthly Rent",
            value=median_rent_price,
            currency=currency,
            decimals=0,
        ),
        KpiCard(
            label="Median Price per SQM",
            value=median_ppsqm,
            currency=currency,
            decimals=0,
        ),
        KpiCard(
            label="Median Days Listed",
            value=median_days_listed,
            decimals=0,
        ),
        KpiCard(
            label="Active Supply",
            value=supply,
            decimals=0,
        ),
        KpiCard(
            label="Sales Volume (Sold / Under Offer)",
            value=sales_volume,
            decimals=0,
        ),
        KpiCard(
            label="Median Leasehold PPSY",
            value=median_ppsy,
            currency=currency,
            decimals=0,
        ),
    ]

    render_kpi_cards(cards, columns=3)

    st.markdown("### Market Trends")

    sales_trend = _prepare_trend(sales_df, "price_sale_idr", currency, "price_usd", "Median Sales Price", freq)
    rent_trend = _prepare_trend(rent_df, "rent_price_month_idr_norm", currency, None, "Median Monthly Rent", freq)
    ppsy_trend = _prepare_trend(leasehold_df, "price_per_sqm_per_year", currency, None, "Median PPSY", freq)

    trend_cols = st.columns(3)
    caption_map = {
        "Median Sales Price": "Track sale price momentum across the selected period.",
        "Median Monthly Rent": "See how normalized monthly rents evolve over time.",
        "Median PPSY": "Monitor leasehold PPSY to gauge long-term value shifts.",
    }
    trend_data = [
        (trend_cols[0], sales_trend, "Median Sales Price", "Period", "currency"),
        (trend_cols[1], rent_trend, "Median Monthly Rent", "Period", "currency"),
        (trend_cols[2], ppsy_trend, "Median PPSY", "Period", "currency"),
    ]

    for col, data_frame, metric, x_label, axis_type in trend_data:
        with col:
            if data_frame.empty:
                st.info(f"No {metric.lower()} trend available.")
            else:
                fig = line_chart(
                    data_frame,
                    x="period",
                    y=metric,
                    title=metric,
                    yaxis_title=metric,
                    yaxis_tickformat=",.0f" if axis_type == "currency" else None,
                )
                render_plotly(fig)
                st.caption(caption_map.get(metric, ""))

    st.markdown("### Ownership Mix & Supply")
    mix = _ownership_mix(df)
    supply_by_region = _supply_by_region(df)

    mix_col, supply_col = st.columns(2)
    with mix_col:
        if mix.empty:
            st.info("Ownership mix not available.")
        else:
            fig = bar_chart(
                mix,
                x="Ownership",
                y="Share",
                title="Ownership Mix",
                yaxis_title="Share (%)",
                yaxis_tickformat=".1f",
                text_auto=True,
            )
            render_plotly(fig)
            st.caption("Check the leasehold versus freehold split to understand tenure mix in the selected areas.")

    with supply_col:
        if supply_by_region.empty:
            st.info("Regional supply not available.")
        else:
            fig = bar_chart(
                supply_by_region,
                x="Listings",
                y="Area",
                orientation="h",
                title="Supply by Region (Top 10)",
                yaxis_title="Area",
                text_auto=True,
            )
            fig.update_layout(yaxis=dict(categoryorder="total ascending"))
            render_plotly(fig)
            st.caption("Focus on these areas first—they carry the highest number of active listings.")

    st.markdown("### Regional Movers")
    movers = _regional_movers(df, freq=freq)
    if movers.empty:
        st.info("Not enough data to compute regional movers.")
    else:
        table_config = {
            "Supply Growth %": {"type": "percent", "decimals": 1},
            "PPSQM Change %": {"type": "percent", "decimals": 1},
        }
        render_table(
            movers,
            column_config=table_config,
            height=320,
            export_file_name="regional_movers.csv",
            highlight_cols=["Supply Growth %", "PPSQM Change %"],
        )
        st.caption("This leaderboard surfaces regions with the strongest supply and price-per-sqm movements.")
