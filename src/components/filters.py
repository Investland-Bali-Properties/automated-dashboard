import streamlit as st
import pandas as pd
from typing import Dict, Any


def sidebar_filters(df: pd.DataFrame) -> Dict[str, Any]:
    st.sidebar.header("Filters")

    property_types = sorted([x for x in df.get("property_type", []).dropna().unique()]) if "property_type" in df else []
    areas = sorted([x for x in df.get("area", []).dropna().unique()]) if "area" in df else []

    selected_property_types = st.sidebar.multiselect("Property Type", property_types, default=property_types[:3] if property_types else [])
    selected_areas = st.sidebar.multiselect("Area", areas, default=areas[:5] if areas else [])

    price_min, price_max = 0, 0
    if "price_idr" in df:
        min_price = float(df["price_idr"].min()) if not df["price_idr"].dropna().empty else 0
        max_price = float(df["price_idr"].max()) if not df["price_idr"].dropna().empty else 0
        price_min, price_max = st.sidebar.slider("Price (IDR)", min_value=min_price, max_value=max_price, value=(min_price, max_price))

    bedrooms = None
    if "bedrooms" in df:
        b_min = int(df["bedrooms"].min()) if not df["bedrooms"].dropna().empty else 0
        b_max = int(df["bedrooms"].max()) if not df["bedrooms"].dropna().empty else 0
        bedrooms = st.sidebar.slider("Bedrooms", min_value=b_min, max_value=b_max, value=(b_min, b_max))

    return {
        "property_type": selected_property_types,
        "area": selected_areas,
        "price_idr": (price_min, price_max),
        "bedrooms": bedrooms,
    }
