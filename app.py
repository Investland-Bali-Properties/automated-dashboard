import src.bootstrap_env  # must be first to set env/secrets
import streamlit as st

from src.config import TABS
from src.data.enrichment import enrich_listings
from src.data.filters import apply_global_filters, serialize_filters
from src.data.loader import load_data
from src.ui.layout import setup_page, sidebar_filters_ui
from src.ui.pages import (
    overview,
    sales_market,
    rental_market,
    supply_velocity,
    ownership_mix,
    off_plan_ready,
    regional_insights,
    data_source,
    explorer,
    data_quality,
)
from src.ui.components.formatting import format_currency, format_number
from src.ui.utils.currency import scalar_to_currency
from src.ui.pages.context import PageContext


PAGE_RENDERERS = {
    "overview": overview.render,
    "sales_market": sales_market.render,
    "rental_market": rental_market.render,
    "supply_velocity": supply_velocity.render,
    "ownership_mix": ownership_mix.render,
    "off_plan_ready": off_plan_ready.render,
    "regional_insights": regional_insights.render,
    "data_source": data_source.render,
    "explorer": explorer.render,
    "data_quality": data_quality.render,
}


def _active_filter_summary(filters, total_rows: int) -> None:
    badges = []
    if filters.listing_type:
        badges.append(f"Listing: {filters.listing_type.title()}")
    if filters.property_types:
        badges.append("Types: " + ", ".join(filters.property_types))
    if filters.areas:
        badges.append("Areas: " + ", ".join(filters.areas[:5]) + ("…" if len(filters.areas) > 5 else ""))
    if filters.price_range:
        min_val, max_val = filters.price_range
        min_display = format_currency(
            scalar_to_currency(min_val, filters.currency),
            currency=filters.currency,
            compact=True,
        )
        max_display = format_currency(
            scalar_to_currency(max_val, filters.currency),
            currency=filters.currency,
            compact=True,
        )
        badges.append(f"Sale Price: {min_display} – {max_display}")
    if filters.rent_range:
        min_val, max_val = filters.rent_range
        min_display = format_currency(
            scalar_to_currency(min_val, filters.currency),
            currency=filters.currency,
            compact=True,
        )
        max_display = format_currency(
            scalar_to_currency(max_val, filters.currency),
            currency=filters.currency,
            compact=True,
        )
        badges.append(f"Rent: {min_display} – {max_display}")
    if filters.building_size_range:
        min_val, max_val = filters.building_size_range
        badges.append(f"Building Size: {format_number(min_val, 0)}–{format_number(max_val, 0)} sqm")
    if filters.land_size_range:
        min_val, max_val = filters.land_size_range
        badges.append(f"Land Size: {format_number(min_val, 0)}–{format_number(max_val, 0)} sqm")
    if filters.bedrooms_bucket:
        badges.append("Bedrooms: " + ", ".join(filters.bedrooms_bucket))

    summary_text = "Active Filters: " + " | ".join(badges) if badges else "Active Filters: All data"
    st.markdown(f"**{summary_text}**")
    st.caption(f"Showing {format_number(total_rows, 0)} listings after filters.")


# Removed scroll-to-top injection to avoid layout shift after filter changes.


def main() -> None:
    setup_page()
    st.title("Bali Real Estate Intelligence Dashboard")

    if st.sidebar.button("🔄 Refresh Data"):
        load_data.clear()  # type: ignore[attr-defined]

    raw_df = load_data()
    enriched_df = enrich_listings(raw_df)

    filters = sidebar_filters_ui(enriched_df)
    filtered_df = apply_global_filters(enriched_df, filters)
    st.session_state["sa_active_filters"] = serialize_filters(filters)

    prev_count = st.session_state.get("sa_prev_filtered_count")
    current_count = len(filtered_df)
    if prev_count is not None and prev_count != current_count:
        st.toast(f"Filters applied to {current_count:,} listings", icon="🔎")
    st.session_state["sa_prev_filtered_count"] = current_count

    if raw_df.empty:
        st.warning("Dataset kosong. Mohon pastikan Google Sheet tersedia atau kredensial valid.")
        return

    _active_filter_summary(filters, current_count)

    context = PageContext(
        raw_df=raw_df,
        enriched_df=enriched_df,
        filters=filters,
    )

    tab_labels = [tab.label for tab in TABS]
    streamlit_tabs = st.tabs(tab_labels)

    for streamlit_tab, tab_config in zip(streamlit_tabs, TABS):
        renderer = PAGE_RENDERERS.get(tab_config.key)
        if renderer is None:
            continue
        with streamlit_tab:
            renderer(filtered_df, context)


if __name__ == "__main__":
    main()
