from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.charts import bar_chart, line_chart, render_plotly, scatter_plot
from src.ui.components.tables import render_table
from src.ui.pages.context import PageContext
from src.ui.pages.helpers import pct_change, compute_sold_mask
from src.ui.utils.currency import series_to_currency


def _regional_summary(df: pd.DataFrame, currency: str, freq: str) -> pd.DataFrame:
    if df.empty or "area" not in df:
        return pd.DataFrame(columns=["Area", "Median PPSY"])
    working = df.copy()

    summary = (
        working.groupby("area")
        .agg(
            listings=("property_id", "nunique") if "property_id" in working.columns else ("area", "size"),
            median_price=("price_sale_idr", "median"),
            median_ppsqm=("price_per_sqm_idr_calc", "median"),
            median_ppsy=("price_per_sqm_per_year", "median"),
            median_adr=("adr_idr", "median"),
        )
        .reset_index()
        .rename(columns={"area": "Area"})
    )
    summary["Median PPSY"] = series_to_currency(summary["median_ppsy"], currency, None)
    summary["Median Price"] = series_to_currency(summary["median_price"], currency, summary.get("median_price_usd")) if "median_price" in summary else None
    summary["Median Price per SQM"] = series_to_currency(summary["median_ppsqm"], currency, None)
    summary["Median ADR"] = series_to_currency(summary["median_adr"], currency, None)

    summary.drop(columns=[col for col in ["median_ppsy", "median_price", "median_ppsqm", "median_adr"] if col in summary], inplace=True)
    summary.rename(columns={"listings": "Listings"}, inplace=True)
    return summary


def _supply_growth(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if df.empty or "listing_date_effective" not in df or "area" not in df:
        return pd.DataFrame(columns=["Area", "Supply Growth %"])
    working = df.dropna(subset=["listing_date_effective", "area"]).copy()
    counts = (
        working.set_index("listing_date_effective")
        .groupby(["area", pd.Grouper(freq=freq)])
        .size()
        .reset_index(name="Listings")
        .rename(columns={"listing_date_effective": "period"})
    )
    records = []
    for area, area_df in counts.groupby("area"):
        area_df = area_df.sort_values("period")
        if len(area_df) < 2:
            continue
        latest = area_df.iloc[-1]
        previous = area_df.iloc[-2]
        growth = pct_change(latest["Listings"], previous["Listings"])
        records.append({"Area": area, "Supply Growth %": growth})
    return pd.DataFrame(records)


def _sales_volume(df: pd.DataFrame) -> pd.DataFrame:
    if "area" not in df:
        return pd.DataFrame(columns=["Area", "Sales Volume"])
    mask = compute_sold_mask(df)
    sold = df[mask]
    if sold.empty:
        return pd.DataFrame(columns=["Area", "Sales Volume"])
    if "property_id" in sold:
        grouped = sold.groupby("area")["property_id"].nunique().reset_index(name="Sales Volume")
    else:
        grouped = sold.groupby("area").size().reset_index(name="Sales Volume")
    return grouped.rename(columns={"area": "Area"})


def _top_regions(summary: pd.DataFrame, metric: str, top_n: int = 10) -> pd.DataFrame:
    if summary.empty or metric not in summary:
        return pd.DataFrame(columns=["Area", metric])
    return summary[["Area", metric]].dropna().sort_values(metric, ascending=False).head(top_n)


def _trend_by_region(df: pd.DataFrame, currency: str, freq: str, metric: str) -> pd.DataFrame:
    if df.empty or "listing_date_effective" not in df or "area" not in df:
        return pd.DataFrame(columns=["period", "Area", metric])
    metric_map = {
        "Median PPSY": "price_per_sqm_per_year",
        "Median Price": "price_sale_idr",
        "Median ADR": "adr_idr",
    }
    if metric not in metric_map:
        return pd.DataFrame(columns=["period", "Area", metric])
    col = metric_map[metric]
    working = df.dropna(subset=["listing_date_effective", "area", col]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period", "Area", metric])
    working[metric] = series_to_currency(working[col], currency, working.get("price_usd") if col == "price_sale_idr" else None)
    grouped = (
        working.set_index("listing_date_effective")
        .groupby(["area", pd.Grouper(freq=freq)])
        [metric]
        .median()
        .reset_index()
        .rename(columns={"listing_date_effective": "period", "area": "Area"})
    )
    return grouped


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Regional Insights")
    if df.empty:
        st.info("No regional data available for mapping and rankings.")
        return

    currency = context.filters.currency
    freq = context.filters.date_granularity or "M"

    summary = _regional_summary(df, currency, freq)
    growth = _supply_growth(df, freq)
    volume = _sales_volume(df)
    regional_metrics = summary.merge(growth, on="Area", how="left").merge(volume, on="Area", how="left")

    st.markdown("#### Regional Metric View")
    metric_options = ["Median PPSY", "Median Price", "Median ADR", "Supply Growth %", "Sales Volume"]
    metric_choice = st.selectbox("Map Metric", metric_options, index=0, key="sa_region_metric")
    has_coordinates = {"latitude", "longitude"}.issubset(df.columns)
    view_options = ["Ranking"] + (["Map (advanced)"] if has_coordinates else [])
    view_choice = st.radio("View mode", view_options, index=0, horizontal=True, key="sa_region_view")

    top_df = _top_regions(regional_metrics, metric_choice)
    if top_df.empty:
        st.info("Metric data unavailable.")
    else:
        fig = bar_chart(
            top_df,
            x="Area",
            y=metric_choice,
            title=f"Top Regions by {metric_choice}",
            yaxis_tickformat=",.0f" if "Median" in metric_choice else None,
        )
        render_plotly(fig)
        st.caption("The ranking makes it easy to compare area performance without reading a map.")

    if view_choice == "Map (advanced)" and has_coordinates:
        map_df = df.dropna(subset=["latitude", "longitude"]).copy()
        map_df["Area"] = map_df.get("area")
        if metric_choice == "Median PPSY":
            map_df["metric"] = series_to_currency(map_df["price_per_sqm_per_year"], currency, None)
        elif metric_choice == "Median Price":
            map_df["metric"] = series_to_currency(map_df["price_sale_idr"], currency, map_df.get("price_usd"))
        elif metric_choice == "Median ADR":
            map_df["metric"] = series_to_currency(map_df["adr_idr"], currency, None)
        elif metric_choice == "Supply Growth %":
            map_df = map_df.merge(growth, on="Area", how="left")
            map_df["metric"] = map_df["Supply Growth %"]
        else:
            map_df = map_df.merge(volume, on="Area", how="left")
            map_df["metric"] = map_df["Sales Volume"]

        if map_df.empty or map_df["metric"].dropna().empty:
            st.info("Map metric unavailable.")
        else:
            st.caption("The map view helps spatial users see where high-performing locations cluster.")
            fig = scatter_plot(
                map_df,
                x="longitude",
                y="latitude",
                color="metric",
                hover_data=["Area", "metric"],
                title=f"{metric_choice} by Location",
            )
            render_plotly(fig)
            st.caption("Warmer colors indicate higher values for the selected metric.")

    st.markdown("#### Top Regions")
    top_metric = st.selectbox("Metric", ["Median Price per SQM", "Median ADR", "Listings"], index=0, key="sa_region_top_metric")
    top_table = _top_regions(summary, top_metric)
    if top_table.empty:
        st.info("No regional ranking data for the selected metric.")
    else:
        render_plotly(
            bar_chart(
                top_table,
                x="Area",
                y=top_metric,
                title=f"Top Regions by {top_metric}",
                yaxis_tickformat=",.0f",
            )
        )

    st.markdown("#### Regional Trends")
    trend_metric = st.selectbox("Trend Metric", ["Median PPSY", "Median Price", "Median ADR"], index=0, key="sa_region_trend_metric")
    trend_df = _trend_by_region(df, currency, freq, trend_metric)
    if trend_df.empty:
        st.info("Regional trend data unavailable.")
    else:
        view_mode = st.radio(
            "Trend view",
            ["Top performers", "Select area"],
            index=0,
            horizontal=True,
            key="sa_region_trend_view",
        )
        if view_mode == "Top performers":
            top_areas = (
                trend_df.groupby("Area")[trend_metric]
                .median()
                .dropna()
                .sort_values(ascending=False)
                .head(3)
                .index
            )
            filtered = trend_df[trend_df["Area"].isin(top_areas)]
            fig = line_chart(
                filtered,
                x="period",
                y=trend_metric,
                color="Area",
                title=f"{trend_metric} Trend (Top 3 Regions)",
                yaxis_tickformat=",.0f",
            )
            render_plotly(fig)
            st.caption("The trend highlights the top three areas with the highest median for the chosen metric.")
        else:
            area_options = sorted(trend_df["Area"].dropna().unique().tolist())
            selected_area = st.selectbox("Choose area", area_options, key="sa_region_trend_area")
            area_data = trend_df[trend_df["Area"] == selected_area]
            fig = line_chart(
                area_data,
                x="period",
                y=trend_metric,
                color=None,
                title=f"{trend_metric} Trend - {selected_area}",
                yaxis_tickformat=",.0f",
            )
            render_plotly(fig)
            st.caption(f"{trend_metric} trend for {selected_area} under the current filters.")

    if not regional_metrics.empty:
        st.markdown("#### Regional Summary Table")
        column_config = {
            "Median PPSY": {"type": "currency", "currency": currency, "decimals": 0},
            "Median Price per SQM": {"type": "currency", "currency": currency, "decimals": 0},
            "Median ADR": {"type": "currency", "currency": currency, "decimals": 0},
            "Supply Growth %": {"type": "percent", "decimals": 1},
        }
        render_table(regional_metrics, column_config=column_config, height=400, export_file_name="regional_summary.csv")
