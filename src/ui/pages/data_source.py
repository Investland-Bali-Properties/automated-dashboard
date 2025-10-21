from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.components.charts import bar_chart, render_plotly
from src.ui.components.tables import render_table
from src.ui.pages.context import PageContext
from src.ui.utils.currency import series_to_currency


def _company_column(df: pd.DataFrame) -> str | None:
    for col in ["Company", "listing_agency", "listing_agent"]:
        if col in df.columns:
            return col
    return None


def _company_summary(df: pd.DataFrame, company_col: str, currency: str) -> pd.DataFrame:
    working = df.dropna(subset=[company_col]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Company", "Listings"])
    grouped = (
        working.groupby(company_col)
        .agg(
            Listings=("property_id", "nunique") if "property_id" in working.columns else (company_col, "size"),
            MedianPrice=("price_sale_idr", "median"),
            MedianRent=("rent_price_month_idr_norm", "median"),
            MedianPPSY=("price_per_sqm_per_year", "median"),
            MedianADR=("adr_idr", "median"),
        )
        .reset_index()
        .rename(columns={company_col: "Company"})
    )
    grouped["MedianPrice"] = series_to_currency(grouped["MedianPrice"], currency, None)
    grouped["MedianRent"] = series_to_currency(grouped["MedianRent"], currency, None)
    grouped["MedianPPSY"] = series_to_currency(grouped["MedianPPSY"], currency, None)
    grouped["MedianADR"] = series_to_currency(grouped["MedianADR"], currency, None)
    return grouped.sort_values("Listings", ascending=False)


def _agent_summary(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    if "listing_agent" not in df.columns:
        return pd.DataFrame(columns=["Agent", "Listings"])
    working = df.dropna(subset=["listing_agent"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["Agent", "Listings"])
    listings_agg = ("property_id", "nunique") if "property_id" in working.columns else ("listing_agent", "size")
    grouped = (
        working.groupby("listing_agent")
        .agg(
            Listings=listings_agg,
            MedianPrice=("price_sale_idr", "median"),
            MedianPPSY=("price_per_sqm_per_year", "median"),
            MedianADR=("adr_idr", "median"),
        )
        .reset_index()
        .rename(columns={"listing_agent": "Agent"})
    )
    grouped["MedianPrice"] = series_to_currency(grouped["MedianPrice"], currency, None)
    grouped["MedianPPSY"] = series_to_currency(grouped["MedianPPSY"], currency, None)
    grouped["MedianADR"] = series_to_currency(grouped["MedianADR"], currency, None)
    return grouped.sort_values("Listings", ascending=False)


def _seller_recommendations(summary: pd.DataFrame) -> list[str]:
    recs: list[str] = []
    if summary.empty:
        return recs
    top_supply = summary.nlargest(1, "Listings")
    if not top_supply.empty:
        company = top_supply.iloc[0]["Company"]
        listings = int(top_supply.iloc[0]["Listings"])
        recs.append(f"{company} leads in active supply with {listings:,} listings — maintain close partnership for inventory pipeline.")
    premium = summary.nlargest(1, "MedianPrice")
    if not premium.empty:
        company = premium.iloc[0]["Company"]
        price = premium.iloc[0]["MedianPrice"]
        recs.append(f"{company} captures the highest median sales price ({price}), suggesting strong premium positioning.")
    value = summary.nsmallest(1, "MedianPPSY")
    if not value.empty:
        company = value.iloc[0]["Company"]
        ppsy = value.iloc[0]["MedianPPSY"]
        recs.append(f"{company} offers the lowest leasehold PPSY ({ppsy}), ideal for investors seeking long-term value.")
    return recs


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Data Source Insight")
    company_col = _company_column(df)
    if not company_col:
        st.info("Company metadata unavailable.")
        return

    currency = context.filters.currency
    summary = _company_summary(df, company_col, currency)
    if summary.empty:
        st.info("No listings to summarise by data source.")
        return

    top_n = st.slider("Top companies", min_value=5, max_value=20, value=10, step=1, key="sa_company_topn")
    top_summary = summary.head(top_n)

    fig = bar_chart(
        top_summary,
        x="Company",
        y="Listings",
        title="Listings by Company",
        yaxis_title="Listings",
    )
    render_plotly(fig)
    st.caption("See which companies contribute the most listings to your current selection.")

    st.markdown("#### Company Benchmarks")
    column_config = {
        "MedianPrice": {"type": "currency", "currency": currency, "decimals": 0},
        "MedianRent": {"type": "currency", "currency": currency, "decimals": 0},
        "MedianPPSY": {"type": "currency", "currency": currency, "decimals": 0},
        "MedianADR": {"type": "currency", "currency": currency, "decimals": 0},
    }
    render_table(top_summary, column_config=column_config, height=400, export_file_name="company_insights.csv")
    st.caption("Use the benchmark table to compare pricing and ADR performance by company.")

    st.markdown("#### Recommendations")
    recommendations = _seller_recommendations(summary)
    if not recommendations:
        st.info("Not enough variance to generate recommendations.")
    else:
        for rec in recommendations:
            st.write(f"- {rec}")

    st.markdown("#### Top Listing Agents")
    agent_summary = _agent_summary(df, currency)
    if agent_summary.empty:
        st.info("Listing agent information unavailable.")
        return

    max_agents = max(1, min(20, int(agent_summary.shape[0])))
    top_agents_count = st.slider(
        "Top agents",
        min_value=1,
        max_value=max_agents,
        value=min(10, max_agents),
        step=1,
        key="sa_agent_topn",
    )
    top_agents = agent_summary.head(top_agents_count)

    fig_agents = bar_chart(
        top_agents,
        x="Agent",
        y="Listings",
        title="Listings by Agent",
        yaxis_title="Listings",
    )
    render_plotly(fig_agents)
    st.caption("Highlight the agents driving the most inventory on the platform.")

    agent_columns = {
        "MedianPrice": {"type": "currency", "currency": currency, "decimals": 0},
        "MedianPPSY": {"type": "currency", "currency": currency, "decimals": 0},
        "MedianADR": {"type": "currency", "currency": currency, "decimals": 0},
    }
    render_table(top_agents, column_config=agent_columns, height=360, export_file_name="agent_insights.csv")
    st.caption("Review agent-level metrics to identify premium or value-focused partners.")
