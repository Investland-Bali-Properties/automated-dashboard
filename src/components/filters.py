import streamlit as st
import pandas as pd
from typing import Dict, Any


def _format_with_counts(options, series: pd.Series):
    counts = series.value_counts(dropna=False)
    formatted = []
    mapping = {}
    for opt in options:
        c = counts.get(opt, 0)
        label = f"{opt} ({c})"
        formatted.append(label)
        mapping[label] = opt
    return formatted, mapping


def _multiselect_with_all(label: str, key_base: str, raw_options, series: pd.Series):
    if not raw_options:
        return []
    # Build labels with counts
    display_opts, mapping = _format_with_counts(raw_options, series)
    sel_key = f"{key_base}_selected"
    all_key = f"{key_base}_all"
    if sel_key not in st.session_state:
        st.session_state[sel_key] = raw_options  # store raw values
    # All checkbox first
    all_checked = st.sidebar.checkbox("All", key=all_key, value=len(st.session_state[sel_key]) == len(raw_options))
    if all_checked and len(st.session_state[sel_key]) != len(raw_options):
        st.session_state[sel_key] = raw_options
    # Map current raw selection to label defaults
    default_labels = [lbl for lbl in display_opts if mapping[lbl] in st.session_state[sel_key]]
    selected_labels = st.sidebar.multiselect(label, display_opts, default=default_labels, key=f"{key_base}_labels")
    # Translate back to raw
    selected_raw = [mapping[lbl] for lbl in selected_labels]
    st.session_state[sel_key] = selected_raw
    return selected_raw


def sidebar_filters(df: pd.DataFrame) -> Dict[str, Any]:
    st.sidebar.header("Filters")

    property_types = sorted([x for x in df.get("property_type", []).dropna().unique()]) if "property_type" in df else []
    areas = sorted([x for x in df.get("area", []).dropna().unique()]) if "area" in df else []

    selected_property_types = _multiselect_with_all("Property Type", "pt", property_types, df.get("property_type", pd.Series(dtype=str))) if property_types else []
    selected_areas = _multiselect_with_all("Area", "area", areas, df.get("area", pd.Series(dtype=str))) if areas else []

    # Dynamic filtered subset for dependent ranges
    working = df.copy()
    if selected_property_types and 'property_type' in working:
        working = working[working['property_type'].isin(selected_property_types)]
    if selected_areas and 'area' in working:
        working = working[working['area'].isin(selected_areas)]

    # Price filter with auto min/max
    price_min_input = None
    price_max_input = None
    if "price_idr" in df:
        with st.sidebar.expander("Price (IDR)", expanded=False):
            auto_price = st.checkbox("Auto range", value=True, key="price_auto")
            include_missing_price = st.checkbox("Include Missing Price", value=True, key="include_missing_price", help="If checked, rows with blank/NaN price are kept regardless of range.")
            if auto_price:
                # compute from filtered working set
                if not working.get('price_idr', pd.Series(dtype=float)).dropna().empty:
                    pmin = float(working['price_idr'].min())
                    pmax = float(working['price_idr'].max())
                else:
                    pmin = 0.0
                    pmax = 0.0
                st.caption(f"Auto: {pmin:,.0f} - {pmax:,.0f}")
                price_min_input, price_max_input = pmin, pmax
            else:
                # manual inputs persist
                full_min = float(df['price_idr'].min()) if not df['price_idr'].dropna().empty else 0.0
                full_max = float(df['price_idr'].max()) if not df['price_idr'].dropna().empty else 0.0
                colp1, colp2 = st.columns(2)
                with colp1:
                    price_min_input = st.number_input("Min", value=full_min, min_value=0.0, step=1.0, key="price_min_manual")
                with colp2:
                    price_max_input = st.number_input("Max", value=full_max, min_value=0.0, step=1.0, key="price_max_manual")
                if price_max_input < price_min_input:
                    st.warning("Max price is less than Min price; no results will match.")

    # Bedrooms filter with auto
    bedrooms = None
    if "bedrooms" in df:
        with st.sidebar.expander("Bedrooms", expanded=False):
            auto_beds = st.checkbox("Auto range", value=True, key="beds_auto")
            include_missing_bedrooms = st.checkbox("Include Missing Bedrooms", value=True, key="include_missing_bedrooms", help="If checked, rows with blank/NaN bedrooms are kept regardless of range.")
            if auto_beds:
                if 'bedrooms' in working and not working['bedrooms'].dropna().empty:
                    bmin = int(working['bedrooms'].min())
                    bmax = int(working['bedrooms'].max())
                else:
                    bmin = 0
                    bmax = 0
                st.caption(f"Auto: {bmin} - {bmax}")
                bedrooms = (bmin, bmax)
            else:
                full_bmin = int(df['bedrooms'].min()) if not df['bedrooms'].dropna().empty else 0
                full_bmax = int(df['bedrooms'].max()) if not df['bedrooms'].dropna().empty else 0
                colb1, colb2 = st.columns(2)
                with colb1:
                    bmin_input = st.number_input("Min Beds", value=full_bmin, min_value=0, step=1, key="beds_min_manual")
                with colb2:
                    bmax_input = st.number_input("Max Beds", value=full_bmax, min_value=0, step=1, key="beds_max_manual")
                bedrooms = (bmin_input, bmax_input)

    # Date range / presets
    date_range = (None, None)
    quarter = None
    if any(c in df.columns for c in ["listing_date", "scraped_at"]):
        with st.sidebar.expander("Date Range", expanded=False):
            # Build base date series (listing_date preferred else scraped_at)
            date_col = None
            if "listing_date" in df.columns and pd.api.types.is_datetime64_any_dtype(df["listing_date"]):
                date_col = "listing_date"
            elif "scraped_at" in df.columns and pd.api.types.is_datetime64_any_dtype(df["scraped_at"]):
                date_col = "scraped_at"
            if date_col:
                dates = df[date_col].dropna().sort_values()
                min_date = dates.min() if not dates.empty else None
                max_date = dates.max() if not dates.empty else None
                presets = ["All","5Y","3Y","1Y","6M","YTD","QTD","Custom"]
                preset = st.selectbox("Preset", presets, index=0, key="date_preset")
                today = pd.Timestamp.utcnow().normalize()
                start = None
                end = None
                if preset == "All":
                    start, end = min_date, max_date
                else:
                    end = max_date if max_date else today
                    if preset == "5Y":
                        start = end - pd.DateOffset(years=5)
                    elif preset == "3Y":
                        start = end - pd.DateOffset(years=3)
                    elif preset == "1Y":
                        start = end - pd.DateOffset(years=1)
                    elif preset == "6M":
                        start = end - pd.DateOffset(months=6)
                    elif preset == "YTD":
                        end = end
                        start = pd.Timestamp(year=end.year, month=1, day=1)
                    elif preset == "QTD":
                        # Quarter to date: find current quarter boundaries based on end
                        q = (end.month - 1)//3 + 1
                        q_start_month = 3*(q-1)+1
                        start = pd.Timestamp(year=end.year, month=q_start_month, day=1)
                        quarter = q
                    elif preset == "Custom":
                        colcd1, colcd2 = st.columns(2)
                        with colcd1:
                            start = st.date_input("Start", value=min_date.date() if min_date else today.date(), key="custom_start")
                        with colcd2:
                            end = st.date_input("End", value=max_date.date() if max_date else today.date(), key="custom_end")
                        if isinstance(start, pd.Timestamp) is False:
                            start = pd.to_datetime(start)
                        if isinstance(end, pd.Timestamp) is False:
                            end = pd.to_datetime(end) + pd.Timedelta(hours=23, minutes=59, seconds=59)
                if start and end and start > end:
                    st.warning("Start date is after end date; no results will match.")
                date_range = (start, end)
                # Coverage notice for missing listing_date if using fallback
                if date_col == "listing_date":
                    missing_pct = df["listing_date"].isna().mean()*100
                    if missing_pct > 10:
                        st.caption(f"Listing date missing {missing_pct:.1f}% of rows. Consider fallback to scraped_at in future.")
                else:
                    st.caption("Using scraped_at as date source (listing_date missing or not datetime).")

    # Clear filters button
    if st.sidebar.button("Reset Filters"):
        for k in list(st.session_state.keys()):
            if any(k.startswith(pref) for pref in ["pt_", "area_", "price_", "beds_", "date_"]):
                del st.session_state[k]
        st.experimental_rerun()

    return {
        "property_type": selected_property_types,
        "area": selected_areas,
        "price_idr_min": price_min_input,
        "price_idr_max": price_max_input,
        "bedrooms": bedrooms,
    "date_range": date_range,
    "quarter": quarter,
    "include_missing_price": include_missing_price if "price_idr" in df else True,
    "include_missing_bedrooms": include_missing_bedrooms if "bedrooms" in df else True,
    }
