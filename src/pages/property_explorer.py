import streamlit as st
import pandas as pd


def page_property_explorer(df: pd.DataFrame):
    st.subheader("Property Explorer")
    if df.empty:
        st.info("No data available for current filters.")
        return

    display_cols = [c for c in [
        "property_id", "title", "price_idr", "price_usd", "bedrooms", "bathrooms",
        "land_size_sqm", "building_size_sqm", "price_per_sqm_idr", "property_type",
        "area", "company", "url"
    ] if c in df.columns]

    page_size = 25
    page = st.number_input("Page", min_value=1, value=1, step=1)
    start = (page - 1) * page_size
    end = start + page_size
    subset = df.iloc[start:end]

    if "url" in subset.columns:
        subset = subset.copy()
        subset["title"] = subset.apply(lambda r: f"[{r['title']}]({r['url']})" if r.get('title') and r.get('url') else r.get('title'), axis=1)

    st.dataframe(subset[display_cols], width="stretch")
