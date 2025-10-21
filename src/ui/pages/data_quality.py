from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.kpi import KpiCard, render_kpi_cards
from src.ui.pages.context import PageContext


def _percentage_missing(series: pd.Series) -> float:
    total = len(series)
    if total == 0:
        return 0.0
    return float(series.isna().sum() / total * 100)


def _compute_quality_metrics(df: pd.DataFrame) -> list[KpiCard]:
    metrics = []
    missing_building = _percentage_missing(df.get("building_size_sqm", pd.Series(dtype=float)))
    metrics.append(
        KpiCard(
            label="Missing Building Size",
            value=missing_building,
            value_display=f"{missing_building:.1f}%",
        )
    )

    price_ok = df.get("price_parsed_ok")
    if price_ok is not None:
        price_bool = (
            price_ok.replace({"TRUE": True, "FALSE": False, "true": True, "false": False})
            .astype(str)
            .str.lower()
            .map({"true": True, "false": False})
        )
        fail_pct = float((~price_bool.fillna(False)).mean() * 100)
    else:
        fail_pct = 0.0
    metrics.append(KpiCard(label="Price Parse Failures", value=fail_pct, value_display=f"{fail_pct:.1f}%"))

    leasehold = df[df.get("ownership_type", "").astype(str).str.lower() == "leasehold"]
    lease_missing = _percentage_missing(leasehold.get("lease_years_remaining", pd.Series(dtype=float)))
    metrics.append(KpiCard(label="Leasehold Missing Years", value=lease_missing, value_display=f"{lease_missing:.1f}%"))

    outlier_pct = float(df.get("is_outlier_any", pd.Series(dtype=bool)).fillna(False).mean() * 100)
    metrics.append(KpiCard(label="PPSY Outliers", value=outlier_pct, value_display=f"{outlier_pct:.1f}%"))
    return metrics


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Data Quality & Definitions")
    if df.empty:
        st.info("No diagnostics available yet.")
        return

    metrics = _compute_quality_metrics(context.enriched_df)
    render_kpi_cards(metrics, columns=4)

    st.markdown("#### Diagnostics Summary")
    diagnostics = context.enriched_df.attrs.get("diagnostics", {})
    if diagnostics:
        for key, value in diagnostics.items():
            st.write(f"- **{key.replace('_', ' ').title()}**: {value}")
    else:
        st.info("No diagnostics metadata available.")

    st.markdown("#### Metric Definitions")
    st.write(
        """
        - **PPSY (Price per SQM per Year)**: Leasehold price per sqm divided by remaining lease years.
        - **ADR (Average Daily Rate)**: Normalised monthly rent divided by 30.
        - **Yield Proxy**: Annual rent per sqm divided by price per sqm (median at segment level).
        - **Days Listed**: Days between listing date (or scraped date fallback) and latest scrape.
        - **Freehold PPSY (Assumed)**: Price per sqm divided by configurable horizon (default 30 years).
        """
    )

    st.markdown("#### Current Assumptions")
    st.write(
        """
        - FX rate for USD display defaults to 15,000 IDR (used when USD values are missing).
        - Rent normalisation converts daily ×30, weekly ×4.3, yearly ÷12.
        - Outlier flagging trims metrics outside P1–P99 for price and PPSY measures.
        - Lease years parsed from `lease_duration`, `lease_expiry_year`, or description regex.
        """
    )
