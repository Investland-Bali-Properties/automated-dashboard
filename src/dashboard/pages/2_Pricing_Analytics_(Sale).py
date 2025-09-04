import streamlit as st
import pandas as pd
import common as cm

st.set_page_config(page_title="Pricing Analytics (Sale)", page_icon="💵", layout="wide")

st.title("Pricing Analytics (Sale)")

with st.sidebar:
    st.header("Filters")

df = cm.get_data()
filtered, f = cm.render_global_filters(df)

sale_df = filtered[filtered["status"] == "success"].copy()

c1, c2 = st.columns(2)
with c1:
    cm.box_by(sale_df, x="region", y="price_sale", title="Median Price by Region")
with c2:
    cm.box_by(sale_df, x="bedrooms", y="price_sale", title="Median Price by Bedrooms")

c3, c4 = st.columns(2)
with c3:
    cm.box_by(sale_df, x="region", y="price_per_sqm", title="Price per sqm by Region")
with c4:
    cm.box_by(sale_df, x="bedrooms", y="price_per_sqm", title="Price per sqm by Bedrooms")

st.divider()

c5, c6 = st.columns(2)
with c5:
    cm.hist(sale_df, x="price_sale", title="Sale Price Distribution")
with c6:
    cm.time_series(sale_df, y="price_sale", title="Median Sale Price over Time")

st.divider()

st.subheader("Comparable Listings (Comps)")
cols = ["listing_id", "region", "bedrooms", "price_sale", "price_per_sqm", "competitor", "date"]
st.dataframe(sale_df[cols].sort_values("price_sale", ascending=False).head(500), use_container_width=True)
