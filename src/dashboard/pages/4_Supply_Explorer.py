import streamlit as st
import pandas as pd
import common as cm

st.set_page_config(page_title="Supply Explorer", page_icon="📦", layout="wide")

st.title("Supply Explorer")

with st.sidebar:
    st.header("Filters")

df = cm.get_data()
filtered, _ = cm.render_global_filters(df)

ok = filtered[filtered["status"] == "success"].copy()

c1, c2, c3, c4 = st.columns(4)
with c1:
    cm.kpi_metric("Inventory Count", ok["listing_id"].nunique())
with c2:
    # Dummy growth vs prior period
    cm.kpi_metric("Growth vs Prior", 5.2)
with c3:
    cm.kpi_metric("Ownership: Developer %", (ok["owner_type"].eq("Developer").mean() * 100))
with c4:
    cm.kpi_metric("Off-plan Share %", (ok["is_offplan"].mean() * 100))

st.divider()

st.subheader("Interactive Table")
show_cols = [
    "listing_id", "region", "bedrooms", "competitor", "source", "price_sale",
    "price_per_sqm", "adr", "is_offplan", "owner_type", "date"
]
st.dataframe(ok[show_cols].sort_values(["region", "bedrooms", "price_sale"], ascending=[True, True, False]),
             use_container_width=True, height=480)

st.caption("Tip: Use column filters/search in the table header to drill down further.")
