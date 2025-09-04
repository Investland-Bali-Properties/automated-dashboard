import streamlit as st
import pandas as pd
import common as cm

st.set_page_config(page_title="Competitor Insights", page_icon="🏁", layout="wide")

st.title("Competitor Insights")

with st.sidebar:
    st.header("Filters")

df = cm.get_data()
filtered, _ = cm.render_global_filters(df)

ok = filtered[filtered["status"] == "success"].copy()

st.subheader("Share of Supply")
share = ok.groupby("competitor", as_index=False)["listing_id"].nunique().rename(columns={"listing_id": "count"})
share["share_%"] = share["count"] / share["count"].sum() * 100
st.dataframe(share.sort_values("count", ascending=False), use_container_width=True)

st.divider()

st.subheader("Average Pricing vs Market")
comp_avg = ok.groupby("competitor", as_index=False).agg(
    avg_price=("price_sale", "median"),
    avg_adr=("adr", "median"),
)
market_avg = {
    "avg_price": ok["price_sale"].median(),
    "avg_adr": ok["adr"].median(),
}
comp_avg["price_vs_mkt_%"] = (comp_avg["avg_price"] / market_avg["avg_price"] - 1) * 100
comp_avg["adr_vs_mkt_%"] = (comp_avg["avg_adr"] / market_avg["avg_adr"] - 1) * 100
st.dataframe(comp_avg.sort_values("avg_price", ascending=False), use_container_width=True)

st.divider()

st.subheader("Overlap Proxy (Region x Bedrooms)")
pivot = ok.pivot_table(index=["region", "bedrooms"], columns="competitor", values="listing_id", aggfunc="nunique", fill_value=0)
st.dataframe(pivot, use_container_width=True)

st.caption("Quality score proxies are approximated with price and ADR in this dummy app.")
