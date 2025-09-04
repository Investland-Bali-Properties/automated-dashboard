import streamlit as st
import pandas as pd
import common as cm

st.set_page_config(page_title="Data Quality & Freshness", page_icon="🧪", layout="wide")

st.title("Data Quality & Freshness")

with st.sidebar:
    st.header("Filters")

df = cm.get_data()
filtered, _ = cm.render_global_filters(df)

ok = filtered.copy()

c1, c2, c3 = st.columns(3)
with c1:
    cm.kpi_metric("Success Rows %", ok["status"].eq("success").mean() * 100)
with c2:
    cm.kpi_metric("Failed Rows", ok["status"].eq("failed").sum())
with c3:
    cm.kpi_metric("Last Scrape Age", cm.freshness_label(ok["scrape_time"]))

st.divider()

st.subheader("Missing Fields")
missing = pd.DataFrame({
    "field": ["sqm", "price_sale", "adr"],
    "missing_%": [
        ok['sqm'].isna().mean() * 100,
        ok['price_sale'].isna().mean() * 100,
        ok['adr'].isna().mean() * 100,
    ]
})
st.dataframe(missing, use_container_width=True)

st.divider()

st.subheader("Schema Coverage by Source")
cov = ok.groupby("source").agg(
    rows=("listing_id", "count"),
    price_nulls=("price_sale", lambda s: s.isna().sum()),
    adr_nulls=("adr", lambda s: s.isna().sum()),
)
cov["price_coverage_%"] = (1 - cov["price_nulls"] / cov["rows"]) * 100
cov["adr_coverage_%"] = (1 - cov["adr_nulls"] / cov["rows"]) * 100
st.dataframe(cov.reset_index(), use_container_width=True)

st.divider()

st.subheader("Last Scrape Times by Source")
st.dataframe(ok.groupby("source", as_index=False)["scrape_time"].max(), use_container_width=True)
