"""
Layout helpers for the Streamlit application (sidebar, header, footer).
"""

from __future__ import annotations

import math
import datetime as dt
import streamlit as st
import pandas as pd

from typing import Optional, List, Tuple

from src.data.filters import GlobalFilters, DEFAULT_FILTERS
from src.ui.utils.currency import FX_RATE_DEFAULT, series_to_currency, scalar_to_currency

BEDROOM_BUCKETS = ["1", "2", "3-4", "5+"]
DATE_PRESETS = ["All", "5Y", "3Y", "1Y", "6M", "YTD", "QTD", "Custom"]
GRANULARITY_OPTIONS = {
    "Daily": "D",
    "Weekly": "W",
    "Monthly": "M",
    "Quarterly": "Q",
}


def setup_page() -> None:
    """Set Streamlit page configuration and top-level styling."""
    st.set_page_config(
        page_title="Bali Real Estate Intelligence",
        layout="wide",
        page_icon=":bar_chart:",
    )
    # Inject a small CSS override for PRIMARY buttons in the sidebar to appear as "danger" (red)
    _inject_sidebar_primary_button_red()


def _multiselect_with_counts(
    label: str,
    key: str,
    options: List[str],
    series: pd.Series,
) -> List[str]:
    if not options:
        return []
    counts = series.value_counts(dropna=False).to_dict()
    return st.sidebar.multiselect(
        label=label,
        options=options,
        default=options,
        key=key,
        format_func=lambda v: f"{v} ({int(counts.get(v, 0))})",
    )


def _suggest_step(min_val: float, max_val: float) -> float:
    span = max_val - min_val
    if span <= 0:
        return 1.0
    exponent = math.floor(math.log10(span)) - 2
    return float(10 ** max(0, exponent))


def _as_date(value, fallback_ts: pd.Timestamp) -> dt.date:
    """Return a datetime.date from various input types, with a Timestamp fallback.

    Handles pd.Timestamp, datetime.datetime, datetime.date, strings, and None.
    """
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return fallback_ts.date()
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return fallback_ts.date()


def _currency_range_input(
        label: str,
        key: str,
        series_idr: pd.Series,
        currency: str,
        fallback_series: Optional[pd.Series] = None,
        currency_changed: bool = False,
) -> Optional[Tuple[float, float]]:
    series_idr = pd.to_numeric(series_idr, errors="coerce")
    if series_idr.dropna().empty:
        return None
    base_min = float(series_idr.min())
    base_max = float(series_idr.max())

    fallback_series = pd.to_numeric(fallback_series, errors="coerce") if fallback_series is not None else None
    converted_series = series_to_currency(series_idr, currency, fallback_series)
    converted_series = pd.to_numeric(converted_series, errors="coerce").dropna()
    if converted_series.empty:
        converted_min = base_min if currency == "IDR" else base_min / FX_RATE_DEFAULT
        converted_max = base_max if currency == "IDR" else base_max / FX_RATE_DEFAULT
    else:
        converted_min = float(converted_series.min())
        converted_max = float(converted_series.max())
    if converted_min == converted_max:
        return None

    base_state_key = f"{key}_base"
    if base_state_key not in st.session_state:
        st.session_state[base_state_key] = (base_min, base_max)
    sel_min_idr, sel_max_idr = st.session_state[base_state_key]
    sel_min_idr = max(base_min, min(sel_min_idr, base_max))
    sel_max_idr = max(sel_min_idr, min(sel_max_idr, base_max))

    display_default_min = scalar_to_currency(sel_min_idr, currency)
    if display_default_min is None:
        display_default_min = converted_min
    display_default_max = scalar_to_currency(sel_max_idr, currency)
    if display_default_max is None:
        display_default_max = converted_max

    step = _suggest_step(converted_min, converted_max)

    default_min_display = float(max(converted_min, min(display_default_min, converted_max)))
    default_max_display = float(max(converted_min, min(display_default_max, converted_max)))

    col_min, col_max = st.sidebar.columns(2)
    with col_min:
        min_input = st.number_input(
            f"{label} Min ({currency})",
            min_value=float(converted_min),
            max_value=float(converted_max * 1000),
            value=default_min_display,
            step=step,
            format="%0.0f",
            key=f"{key}_{currency}_min",
            help="Enter the lower bound; values switch automatically when you change currency.",
        )
    with col_max:
        max_input = st.number_input(
            f"{label} Max ({currency})",
            min_value=float(converted_min),
            max_value=float(converted_max * 1000),
            value=default_max_display,
            step=step,
            format="%0.0f",
            key=f"{key}_{currency}_max",
            help="Enter the upper bound; values switch automatically when you change currency.",
        )

    if max_input < min_input:
        st.sidebar.warning("Max value must be greater than or equal to min value.")
        max_input = min_input

    display_tolerance = max(abs(default_min_display), abs(default_max_display), 1.0) * 1e-6
    values_unchanged = (
        abs(min_input - default_min_display) <= display_tolerance
        and abs(max_input - default_max_display) <= display_tolerance
    )

    if min_input < converted_min:
        st.sidebar.warning(f"{label} Min is below available data. Using dataset minimum instead.")
        min_input = converted_min
    if max_input < min_input:
        st.sidebar.warning("Max value must be greater than or equal to min value.")
        max_input = min_input

    if currency_changed and values_unchanged:
        min_idr, max_idr = st.session_state[base_state_key]
    else:
        if currency == "IDR":
            min_idr, max_idr = float(min_input), float(max_input)
        else:
            min_idr = float(min_input) * FX_RATE_DEFAULT
            max_idr = float(max_input) * FX_RATE_DEFAULT

        min_idr = max(base_min, min(min_idr, base_max))
        max_idr = max(min_idr, min(max_idr, base_max))
        st.session_state[base_state_key] = (min_idr, max_idr)

    tolerance = max(abs(base_min), abs(base_max), 1.0) * 1e-6
    if abs(min_idr - base_min) <= tolerance and abs(max_idr - base_max) <= tolerance:
        return None
    return (min_idr, max_idr)


def _numeric_range_input(
    label: str,
    key: str,
    series: pd.Series,
) -> Optional[Tuple[float, float]]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    base_min = float(numeric.min())
    base_max = float(numeric.max())
    if base_min == base_max:
        return None

    state_key = f"{key}_range"
    if state_key not in st.session_state:
        st.session_state[state_key] = (base_min, base_max)
    sel_min, sel_max = st.session_state[state_key]
    sel_min = max(base_min, min(sel_min, base_max))
    sel_max = max(sel_min, min(sel_max, base_max))

    step = _suggest_step(base_min, base_max)

    # Use container-aware columns so content stays inside the current expander/sidebar section
    col_min, col_max = st.columns(2)
    with col_min:
        min_input = st.number_input(
            f"{label} Min",
            min_value=float(base_min),
            max_value=float(base_max * 1000),
            value=float(sel_min),
            step=step,
            format="%0.0f",
            key=f"{key}_min",
            help="Enter the minimum value for this range.",
        )
    with col_max:
        max_input = st.number_input(
            f"{label} Max",
            min_value=float(base_min),
            max_value=float(base_max * 1000),
            value=float(sel_max),
            step=step,
            format="%0.0f",
            key=f"{key}_max",
            help="Enter the maximum value for this range.",
        )

    if max_input < min_input:
        st.warning("Max value must be greater than or equal to min value.")
        return None

    st.session_state[state_key] = (float(min_input), float(max_input))

    tolerance = max(abs(base_min), abs(base_max), 1.0) * 1e-6
    if abs(min_input - base_min) <= tolerance and abs(max_input - base_max) <= tolerance:
        return None
    return (float(min_input), float(max_input))


def _derive_date_range(date_series: pd.Series) -> tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    if date_series.empty:
        return None, None

    start_default = date_series.min()
    end_default = date_series.max()

    preset = st.sidebar.selectbox(
        "Date Preset",
        DATE_PRESETS,
        index=0,
        key="sa_date_preset",
        help="Choose a preset or select Custom to use the date range below.",
    )

    # Render custom date inputs only when preset is Custom, side-by-side to save space
    start_input = None
    end_input = None
    if preset == "Custom":
        col_start, col_end = st.sidebar.columns(2)
        with col_start:
            start_input = st.date_input(
                "Start",
                value=_as_date(st.session_state.get("sa_date_start"), start_default),
                key="sa_date_start",
            )
        with col_end:
            end_input = st.date_input(
                "End",
                value=_as_date(st.session_state.get("sa_date_end"), end_default),
                key="sa_date_end",
            )

    # Initialize with full range; override per preset
    end = end_default
    start = start_default
    today = pd.Timestamp.utcnow().normalize()
    if preset == "5Y":
        end = end_default or today
        start = end - pd.DateOffset(years=5)
    elif preset == "3Y":
        end = end_default or today
        start = end - pd.DateOffset(years=3)
    elif preset == "1Y":
        end = end_default or today
        start = end - pd.DateOffset(years=1)
    elif preset == "6M":
        end = end_default or today
        start = end - pd.DateOffset(months=6)
    elif preset == "YTD":
        end = end_default or today
        start = pd.Timestamp(year=end.year, month=1, day=1)
    elif preset == "QTD":
        end = end_default or today
        quarter = (end.month - 1) // 3 + 1
        quarter_start_month = 3 * (quarter - 1) + 1
        start = pd.Timestamp(year=end.year, month=quarter_start_month, day=1)
    elif preset == "Custom":
        # Use the inputs when preset is Custom
        start = pd.to_datetime(start_input)
        end = pd.to_datetime(end_input)

    # Validate order: ensure start <= end
    if start is not None and end is not None and start > end:
        st.sidebar.warning("Start date must be before or equal to End date. Adjusting range.")
        start, end = end, start

    return start, end


def sidebar_filters_ui(
    df: pd.DataFrame, defaults: GlobalFilters = DEFAULT_FILTERS
) -> GlobalFilters:
    """
    Render the sidebar filter controls and return the selected values.
    """
    st.sidebar.header("Global Filters")
    working = df if not df.empty else pd.DataFrame()

    with st.sidebar.expander("Listing Basics", expanded=True):
        listing_state_key = "sa_listing_type"
        listing_types = sorted(
            working["listing_type"].dropna().unique().tolist()
        ) if "listing_type" in working else []
        listing_type_options = ["All"] + listing_types
        if listing_state_key not in st.session_state:
            st.session_state[listing_state_key] = listing_type_options[0]
        if "sa_listing_type_pending" in st.session_state:
            st.session_state[listing_state_key] = st.session_state.pop("sa_listing_type_pending")
        current_listing_value = st.session_state.get(listing_state_key, listing_type_options[0])
        listing_type_choice = st.selectbox(
            "Listing Type",
            options=listing_type_options,
            index=listing_type_options.index(current_listing_value) if current_listing_value in listing_type_options else 0,
            key=listing_state_key,
            help="Filter listings by For Sale or For Rent.",
        )
        listing_type_value = st.session_state.get(listing_state_key, listing_type_choice)
        listing_type = None if listing_type_value == "All" else listing_type_value

        if "listing_date_effective" in working and working["listing_date_effective"].notna().any():
            date_series = working["listing_date_effective"].dropna().sort_values()
        elif "listing_date" in working and working["listing_date"].notna().any():
            date_series = working["listing_date"].dropna().sort_values()
        elif "scraped_at" in working and working["scraped_at"].notna().any():
            date_series = working["scraped_at"].dropna().sort_values()
        else:
            date_series = pd.Series(dtype="datetime64[ns]")
        date_range = _derive_date_range(date_series)

        granularity_label = st.selectbox(
            "Date Granularity",
            list(GRANULARITY_OPTIONS.keys()),
            index=list(GRANULARITY_OPTIONS.values()).index(defaults.date_granularity)
            if defaults.date_granularity in GRANULARITY_OPTIONS.values()
            else 2,
            key="sa_date_granularity",
            help="Choose the resampling cadence for time-based charts.",
        )
        date_granularity = GRANULARITY_OPTIONS[granularity_label]

        property_types = (
            sorted(working["property_type"].dropna().unique().tolist())
            if "property_type" in working
            else []
        )
        areas = (
            sorted(working["area"].dropna().unique().tolist())
            if "area" in working
            else []
        )
        ownership_values = (
            sorted(working["ownership_type"].dropna().unique().tolist())
            if "ownership_type" in working
            else []
        )
        property_status_values = (
            sorted(working["property_status"].dropna().unique().tolist())
            if "property_status" in working
            else []
        )
        selected_property_types = _multiselect_with_counts(
            "Property Type",
            key="sa_property_type",
            options=property_types,
            series=working.get("property_type", pd.Series(dtype=str)),
        )
        if selected_property_types and len(selected_property_types) == len(property_types):
            selected_property_types = []

        selected_areas = _multiselect_with_counts(
            "Area",
            key="sa_area",
            options=areas,
            series=working.get("area", pd.Series(dtype=str)),
        )
        if selected_areas and len(selected_areas) == len(areas):
            selected_areas = []

        selected_ownership = _multiselect_with_counts(
            "Ownership Type",
            key="sa_ownership",
            options=ownership_values,
            series=working.get("ownership_type", pd.Series(dtype=str)),
        )
        if selected_ownership and len(selected_ownership) == len(ownership_values):
            selected_ownership = []

        selected_property_status = _multiselect_with_counts(
            "Property Status",
            key="sa_property_status",
            options=property_status_values,
            series=working.get("property_status", pd.Series(dtype=str)),
        )
        if selected_property_status and len(selected_property_status) == len(property_status_values):
            selected_property_status = []

        bedrooms_bucket = st.multiselect(
            "Bedrooms Bucket",
            options=BEDROOM_BUCKETS,
            default=BEDROOM_BUCKETS,
            key="sa_bedrooms_bucket",
            help="Filter inventory by simplified bedroom groupings.",
        )
        if bedrooms_bucket and len(bedrooms_bucket) == len(BEDROOM_BUCKETS):
            bedrooms_bucket = []

        if st.button("Reset Listing Filters", key="sa_reset_listing_filters", type="primary"):
            _clear_state_prefixes([
                "sa_listing_type",
                "sa_date_preset",
                "sa_date_start",
                "sa_date_end",
                "sa_date_granularity",
                "sa_property_type",
                "sa_area",
                "sa_ownership",
                "sa_property_status",
                "sa_bedrooms_bucket",
                "sa_listing_type_pending",
            ])
            st.rerun()

    with st.sidebar.expander("Pricing & Currency", expanded=True):
        prev_currency = st.session_state.get("sa_currency_prev", defaults.currency)
        currency = st.radio(
            "Display Currency",
            options=["IDR", "USD"],
            index=0 if defaults.currency == "IDR" else 1,
            key="sa_currency",
        )
        currency_changed = prev_currency != currency

        price_series = working.get("price_sale_idr", working.get("price_idr", pd.Series(dtype=float)))
        price_numeric = pd.to_numeric(price_series, errors="coerce").dropna()
        price_bounds = (
            float(price_numeric.min()),
            float(price_numeric.max()),
        ) if not price_numeric.empty else None

        rent_series = working.get("rent_price_month_idr_norm", pd.Series(dtype=float))
        rent_numeric = pd.to_numeric(rent_series, errors="coerce").dropna()
        rent_bounds = (
            float(rent_numeric.min()),
            float(rent_numeric.max()),
        ) if not rent_numeric.empty else None

        preset_cols = st.columns(3)
        listing_state_key = "sa_listing_type"
        listing_options = ["All"] + listing_types
        listing_type_default = st.session_state.get(listing_state_key, listing_options[0])

        def _set_listing_type(value: Optional[str]):
            st.session_state["sa_listing_type_pending"] = "All" if value is None else value

        if price_bounds:
            entry_min = price_bounds[0]
            entry_max = min(price_bounds[1], 2_000_000_000)
            if entry_min <= entry_max and preset_cols[0].button("Entry <2B", key="sa_price_preset_entry"):
                _set_listing_type("for sale")
                if rent_bounds:
                    _set_currency_range_state("sa_rent_range", rent_bounds[0], rent_bounds[1])
                _set_currency_range_state("sa_price_range", entry_min, entry_max)
                st.rerun()
            mid_min = max(price_bounds[0], 2_000_000_000)
            mid_max = min(price_bounds[1], 5_000_000_000)
            if mid_min < mid_max and preset_cols[1].button("Mid 2–5B", key="sa_price_preset_mid"):
                _set_listing_type("for sale")
                if rent_bounds:
                    _set_currency_range_state("sa_rent_range", rent_bounds[0], rent_bounds[1])
                _set_currency_range_state("sa_price_range", mid_min, mid_max)
                st.rerun()
            luxury_min = max(price_bounds[0], 10_000_000_000)
            if luxury_min <= price_bounds[1] and preset_cols[2].button("Luxury 10B+", key="sa_price_preset_lux"):
                _set_listing_type("for sale")
                if rent_bounds:
                    _set_currency_range_state("sa_rent_range", rent_bounds[0], rent_bounds[1])
                _set_currency_range_state("sa_price_range", luxury_min, price_bounds[1])
                st.rerun()

        price_range = _currency_range_input(
            label="Sale Price",
            key="sa_price_range",
            series_idr=price_series,
            currency=currency,
            fallback_series=working.get("price_usd"),
            currency_changed=currency_changed,
        )

        rent_cols = st.columns(2)
        if rent_bounds:
            affordable_max = min(rent_bounds[1], 30_000_000)
            if rent_bounds[0] <= affordable_max and rent_cols[0].button("<=30M", key="sa_rent_preset_affordable"):
                _set_listing_type("for rent")
                if price_bounds:
                    _set_currency_range_state("sa_price_range", price_bounds[0], price_bounds[1])
                _set_currency_range_state("sa_rent_range", rent_bounds[0], affordable_max)
                st.rerun()
            premium_min = max(rent_bounds[0], 50_000_000)
            if premium_min <= rent_bounds[1] and rent_cols[1].button(">=50M", key="sa_rent_preset_premium"):
                _set_listing_type("for rent")
                if price_bounds:
                    _set_currency_range_state("sa_price_range", price_bounds[0], price_bounds[1])
                _set_currency_range_state("sa_rent_range", premium_min, rent_bounds[1])
                st.rerun()

        rent_range = _currency_range_input(
            label="Rent Price / Month",
            key="sa_rent_range",
            series_idr=rent_series,
            currency=currency,
            currency_changed=currency_changed,
        )
        if st.button("Reset Pricing", key="sa_reset_pricing", type="primary"):
            if price_bounds:
                _set_currency_range_state("sa_price_range", price_bounds[0], price_bounds[1])
            else:
                _clear_state_prefixes(["sa_price_range_"])
            if rent_bounds:
                _set_currency_range_state("sa_rent_range", rent_bounds[0], rent_bounds[1])
            else:
                _clear_state_prefixes(["sa_rent_range_"])
            _set_listing_type(None)
            st.rerun()

    with st.sidebar.expander("Size Filters", expanded=False):
        building_size_range = _numeric_range_input(
            label="Building Size (sqm)",
            key="sa_building_size",
            series=working.get("building_size_sqm", pd.Series(dtype=float)),
        )

        land_size_range = _numeric_range_input(
            label="Land Size (sqm)",
            key="sa_land_size",
            series=working.get("land_size_sqm", pd.Series(dtype=float)),
        )
        if st.button("Reset Size", key="sa_reset_size", type="primary"):
            _reset_numeric_range_state("sa_building_size")
            _reset_numeric_range_state("sa_land_size")
            st.rerun()

    st.session_state["sa_currency_prev"] = currency

    st.sidebar.divider()

    hide_outliers = st.sidebar.checkbox(
        "Hide Outliers (P1–P99)",
        value=defaults.hide_outliers,
        key="sa_hide_outliers",
        help="Removes observations flagged as statistical outliers in key price metrics.",
    )

    with st.sidebar.expander("PPSY Options", expanded=False):
        basis_ppsy = st.selectbox(
            "PPSY Basis",
            options=["building", "land"],
            index=0 if defaults.basis_ppsy == "building" else 1,
            key="sa_ppsy_basis",
            help="Choose whether PPSY calculations use building size or land size.",
        )
        ppsy_toggle_freehold = st.checkbox(
            "Enable Freehold PPSY assumption",
            value=defaults.ppsy_toggle_freehold,
            key="sa_ppsy_freehold_toggle",
        )
        assumed_horizon = defaults.assumed_freehold_horizon
        if ppsy_toggle_freehold:
            assumed_horizon = int(
                st.number_input(
                    "Freehold horizon (years)",
                    min_value=5,
                    max_value=99,
                    value=defaults.assumed_freehold_horizon,
                    step=1,
                    key="sa_ppsy_freehold_horizon",
                )
            )

    final_listing_type = st.session_state.get("sa_listing_type", "All")
    final_listing_type = None if final_listing_type == "All" else final_listing_type

    return GlobalFilters(
        date_range=date_range,
        date_granularity=date_granularity,
        listing_type=final_listing_type,
        property_types=selected_property_types or None,
        areas=selected_areas or None,
        bedrooms_bucket=bedrooms_bucket or None,
        ownership=selected_ownership or None,
        property_status=selected_property_status or None,
        seller_type=None,
        price_range=price_range,
        rent_range=rent_range,
        building_size_range=building_size_range,
        land_size_range=land_size_range,
        currency=currency,
        hide_outliers=hide_outliers,
        basis_ppsy=basis_ppsy,
        assumed_freehold_horizon=assumed_horizon,
        ppsy_toggle_freehold=ppsy_toggle_freehold,
    )
def _clear_state_prefixes(prefixes: List[str]) -> None:
    for prefix in prefixes:
        for key in list(st.session_state.keys()):
            if key.startswith(prefix):
                del st.session_state[key]


def _set_currency_range_state(key: str, min_idr: float, max_idr: float) -> None:
    st.session_state[f"{key}_base"] = (float(min_idr), float(max_idr))
    _clear_state_prefixes([
        f"{key}_IDR_",
        f"{key}_USD_",
    ])


def _reset_numeric_range_state(key: str) -> None:
    _clear_state_prefixes([f"{key}_"])


def _inject_sidebar_primary_button_red() -> None:
    """Style PRIMARY buttons in the sidebar as red (danger-like) so we can mark reset actions clearly.

    Notes:
    - We only mark reset buttons as type="primary" so presets and other actions remain default styling.
    - Scoped to the sidebar container to avoid impacting primary buttons in the main content.
    """
    st.sidebar.markdown(
        """
        <style>
        /* Streamlit uses test IDs for buttons; cover both attribute patterns */
        div[data-testid="stSidebar"] button[kind="primary"],
        div[data-testid="stSidebar"] button[data-testid="baseButton-primary"] {
            background-color: #e53935 !important; /* red 600 */
            border-color: #e53935 !important;
            color: #ffffff !important;
        }
        div[data-testid="stSidebar"] button[kind="primary"]:hover,
        div[data-testid="stSidebar"] button[data-testid="baseButton-primary"]:hover {
            background-color: #c62828 !important; /* red 800 */
            border-color: #c62828 !important;
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
