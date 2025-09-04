import streamlit as st
import common as cm

st.set_page_config(page_title="Regional Heatmap", page_icon="🗺️", layout="wide")

st.title("Regional Heatmap")

with st.sidebar:
    st.header("Filters")

df = cm.get_data()
filtered, _ = cm.render_global_filters(df)

ok = filtered[filtered["status"] == "success"].copy()

metric = st.selectbox("Metric", ["price_sale", "price_per_sqm", "adr"])  # selectable metric

cm.pivot_heat(ok, rows="region", cols="bedrooms", value=metric, title=f"Median {metric} by Region x Bedrooms")
