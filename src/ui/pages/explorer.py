from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.pages.context import PageContext
from src.ui.utils.currency import series_to_currency


DEFAULT_COLUMNS = [
    "title",
    "area",
    "listing_type",
    "price_sale_idr",
    "rent_price_month_idr_norm",
    "price_per_sqm_idr_calc",
    "price_per_sqm_per_year",
    "lease_years_remaining",
    "annual_rent_per_sqm",
    "days_listed",
    "ownership_type",
    "property_status",
    "url",
]


def _prepare_display(df: pd.DataFrame, currency: str) -> pd.DataFrame:
    display = df.copy()
    if "price_sale_idr" in display:
        display["price_sale_idr"] = series_to_currency(display["price_sale_idr"], currency, display.get("price_usd"))
    if "rent_price_month_idr_norm" in display:
        display["rent_price_month_idr_norm"] = series_to_currency(display["rent_price_month_idr_norm"], currency, None)
    if "price_per_sqm_idr_calc" in display:
        display["price_per_sqm_idr_calc"] = series_to_currency(display["price_per_sqm_idr_calc"], currency, None)
    if "price_per_sqm_per_year" in display:
        display["price_per_sqm_per_year"] = series_to_currency(display["price_per_sqm_per_year"], currency, None)
    if "annual_rent_per_sqm" in display:
        display["annual_rent_per_sqm"] = series_to_currency(display["annual_rent_per_sqm"], currency, None)
    return display


def render(df: pd.DataFrame, context: PageContext) -> None:
    st.subheader("Explorer")
    if df.empty:
        st.info("No listings to explore.")
        return

    currency = context.filters.currency

    search = st.text_input("Search by title or area", key="sa_explorer_search").strip().lower()
    filtered = df
    if search:
        mask = pd.Series([False] * len(df))
        if "title" in df:
            mask |= df["title"].astype(str).str.lower().str.contains(search, na=False)
        if "area" in df:
            mask |= df["area"].astype(str).str.lower().str.contains(search, na=False)
        filtered = df[mask]

    if "listing_type" in filtered.columns:
        col_sale, col_rent = st.columns(2)
        with col_sale:
            show_sale = st.checkbox("Show sale listings", value=True, key="sa_explorer_sale")
        with col_rent:
            show_rent = st.checkbox("Show rent listings", value=True, key="sa_explorer_rent")
        if not (show_sale and show_rent):
            types = []
            if show_sale:
                types.append("for sale")
            if show_rent:
                types.append("for rent")
            if types:
                filtered = filtered[filtered["listing_type"].astype(str).str.lower().isin(types)]
            else:
                st.info("Toggle minimal satu jenis listing untuk ditampilkan.")
                return

    if "occupancy" in filtered.columns:
        occ_series = pd.to_numeric(filtered["occupancy"], errors="coerce")
        if occ_series.notna().any():
            min_occ = float(occ_series.min())
            max_occ = float(occ_series.max())
        else:
            min_occ, max_occ = 0.0, 100.0
        if min_occ != max_occ:
            occ_range = st.slider(
                "Occupancy range (%)",
                min_value=0.0,
                max_value=100.0,
                value=(max(min_occ, 0.0), min(max_occ, 100.0)),
                step=1.0,
                key="sa_explorer_occ",
            )
            filtered = filtered[occ_series.between(occ_range[0], occ_range[1], inclusive="both") | occ_series.isna()]

    if filtered.empty:
        st.info("No records match the search term.")
        return

    available_columns = [col for col in DEFAULT_COLUMNS if col in filtered.columns]
    selected_columns = st.multiselect(
        "Columns to display",
        options=available_columns,
        default=available_columns,
        key="sa_explorer_columns",
    )

    display_df = _prepare_display(filtered[selected_columns], currency) if selected_columns else pd.DataFrame()

    column_config = {
        "price_sale_idr": st.column_config.TextColumn("Sale Price"),
        "rent_price_month_idr_norm": st.column_config.TextColumn("Monthly Rent"),
        "price_per_sqm_idr_calc": st.column_config.TextColumn("Price/SQM"),
        "price_per_sqm_per_year": st.column_config.TextColumn("PPSY"),
        "annual_rent_per_sqm": st.column_config.TextColumn("Annual Rent/SQM"),
        "days_listed": st.column_config.NumberColumn("Days Listed", format="%d"),
        "lease_years_remaining": st.column_config.NumberColumn("Lease Years", format="%.1f"),
        "url": st.column_config.LinkColumn("Listing URL", display_text="Open"),
    }

    st.dataframe(
        display_df,
        use_container_width=True,
        height=500,
        column_config={k: v for k, v in column_config.items() if k in display_df.columns},
    )
    st.caption("Use the filters above to narrow the list, then follow the URL for full property details.")

    csv_bytes = filtered[selected_columns].to_csv(index=False).encode("utf-8") if selected_columns else b""
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="listings_filtered.csv",
        mime="text/csv",
    )
