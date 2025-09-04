import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# ---------- Dummy data generator ----------
@st.cache_data(show_spinner=False)
def get_data(n_rows: int = 2500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Dates over ~18 months
    start = pd.Timestamp.today().normalize() - pd.offsets.MonthBegin(18)
    dates = pd.date_range(start, periods=540, freq='D')

    regions = [
        "Canggu", "Seminyak", "Ubud", "Uluwatu", "Denpasar", "Sanur",
        "Jimbaran", "Kuta", "Nusa Dua", "Berawa"
    ]
    bedrooms = [1, 2, 3, 4, 5]
    competitors = ["AlphaHomes", "BaliStay", "IslandNest", "TropicVilla"]
    sources = ["scraperA", "scraperB", "scraperC"]

    # Base frame
    df = pd.DataFrame({
        'listing_id': np.arange(1, n_rows + 1),
        'region': rng.choice(regions, n_rows),
        'bedrooms': rng.choice(bedrooms, n_rows),
        'competitor': rng.choice(competitors, n_rows),
        'source': rng.choice(sources, n_rows),
        'date': rng.choice(dates, n_rows),
    })

    # Dummy measures
    base_price = rng.normal(300000, 80000, n_rows).clip(50000, None)
    price_multiplier = (1 + 0.15 * (df['bedrooms'] - 2)) * (1 + 0.08 * rng.normal(0, 1, n_rows))
    df['price_sale'] = (base_price * price_multiplier).round(-2)

    base_adr = rng.normal(150, 40, n_rows).clip(30, None)
    seasonality = 1 + 0.25 * np.sin(df['date'].view('int64') / 8.64e15 * 2 * np.pi)
    df['adr'] = (base_adr * seasonality * (1 + 0.05 * (df['bedrooms'] - 2))).round(2)

    df['sqm'] = rng.normal(120, 40, n_rows).clip(40, 600)
    df['price_per_sqm'] = (df['price_sale'] / df['sqm']).round(2)

    # Inventory flags
    df['is_offplan'] = rng.choice([True, False], n_rows, p=[0.2, 0.8])
    df['owner_type'] = rng.choice(["Developer", "Individual", "Agency"], n_rows, p=[0.25, 0.55, 0.2])

    # Data quality
    df['status'] = rng.choice(['success', 'failed'], n_rows, p=[0.92, 0.08])
    # Random missingness
    df.loc[rng.choice(df.index, int(0.05 * n_rows), replace=False), 'sqm'] = np.nan

    # Scrape time per row around the row date
    tz = 'Asia/Singapore'
    offsets = rng.integers(low=0, high=7 * 24, size=n_rows)  # hours
    df['scrape_time'] = pd.to_datetime(df['date']) + pd.to_timedelta(offsets, unit='h')
    df['scrape_time'] = df['scrape_time'].dt.tz_localize(tz)

    return df

# ---------- Helpers ----------

def safe_median(series: pd.Series):
    s = series.dropna()
    return float(s.median()) if not s.empty else np.nan


def kpi_metric(label: str, value, fmt: str | None = None):
    if fmt == 'currency' and pd.notna(value):
        st.metric(label, f"${value:,.0f}")
    elif isinstance(value, (float, int)) and pd.notna(value):
        st.metric(label, f"{value:,.2f}")
    elif isinstance(value, (str,)):
        st.metric(label, value)
    else:
        st.metric(label, "-")


def freshness_label(scrape_series: pd.Series) -> str:
    if scrape_series.empty:
        return "Unknown"
    last = scrape_series.max()
    if pd.isna(last):
        return "Unknown"
    age = (pd.Timestamp.now(tz=last.tz) - last).total_seconds() / 3600
    if age < 12:
        return "Fresh (<12h)"
    if age < 24:
        return "OK (<24h)"
    if age < 72:
        return "Stale (<3d)"
    return ">=3d old"


# ---------- Global filters ----------

def render_global_filters(df: pd.DataFrame):
    # Default ranges
    min_date, max_date = df['date'].min(), df['date'].max()
    default_start = max(min_date, max_date - pd.Timedelta(days=90))

    with st.sidebar:
        st.markdown("### Global Filters")
        date_range = st.date_input(
            "Date range",
            value=(default_start.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = map(pd.to_datetime, date_range)
        else:
            start_date, end_date = default_start, max_date

        regions = sorted(df['region'].dropna().unique())
        sel_regions = st.multiselect("Region", regions, default=regions[:5])

        beds = sorted(df['bedrooms'].dropna().unique().tolist())
        sel_beds = st.multiselect("Bedrooms", beds, default=beds)

        comps = sorted(df['competitor'].dropna().unique())
        sel_comps = st.multiselect("Competitors", comps, default=comps)

        sources = sorted(df['source'].dropna().unique())
        sel_sources = st.multiselect("Sources", sources, default=sources)

        st.toggle("Enable cache", value=True, key="cache_toggle")

    mask = (
        (df['date'] >= start_date) & (df['date'] <= end_date) &
        (df['region'].isin(sel_regions) if sel_regions else True) &
        (df['bedrooms'].isin(sel_beds) if sel_beds else True) &
        (df['competitor'].isin(sel_comps) if sel_comps else True) &
        (df['source'].isin(sel_sources) if sel_sources else True)
    )

    filtered = df[mask].copy()
    filters = dict(
        start_date=start_date,
        end_date=end_date,
        regions=sel_regions,
        bedrooms=sel_beds,
        competitors=sel_comps,
        sources=sel_sources,
    )
    return filtered, filters


# ---------- Reusable charts ----------

def box_by(df: pd.DataFrame, x: str, y: str, title: str):
    if df.empty:
        st.info("No data for current filters.")
        return
    fig = px.box(df, x=x, y=y, points="outliers")
    fig.update_layout(title=title, height=360, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)


def hist(df: pd.DataFrame, x: str, title: str):
    if df.empty:
        st.info("No data for current filters.")
        return
    fig = px.histogram(df, x=x, nbins=40)
    fig.update_layout(title=title, height=360, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)


def time_series(df: pd.DataFrame, y: str, title: str):
    if df.empty:
        st.info("No data for current filters.")
        return
    ts = df.groupby('date', as_index=False)[y].median()
    fig = px.line(ts, x='date', y=y)
    fig.update_layout(title=title, height=300, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)


def pivot_heat(df: pd.DataFrame, rows: str, cols: str, value: str, title: str):
    if df.empty:
        st.info("No data for current filters.")
        return
    pv = df.pivot_table(index=rows, columns=cols, values=value, aggfunc='median')
    pv = pv.sort_index().sort_index(axis=1)
    fig = px.imshow(pv, text_auto=True, aspect='auto', color_continuous_scale='Viridis')
    fig.update_layout(title=title, height=400, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
