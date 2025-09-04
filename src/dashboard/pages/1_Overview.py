import streamlit as st
import common as cm

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")

st.title("Overview")

# Load and filter
with st.sidebar:
    st.header("Filters")
df = cm.get_data()
filtered, f = cm.render_global_filters(df)

sale_df = filtered[filtered["status"] == "success"].copy()

col1, col2, col3, col4 = st.columns(4)
with col1:
    cm.kpi_metric("Inventory (Listings)", sale_df["listing_id"].nunique())
with col2:
    cm.kpi_metric("Median Sale Price", cm.safe_median(sale_df["price_sale"]), fmt="currency")
with col3:
    cm.kpi_metric("Median ADR", cm.safe_median(sale_df["adr"]), fmt="currency")
with col4:
    cm.kpi_metric("Data Freshness", cm.freshness_label(sale_df["scrape_time"]))

st.divider()

left, right = st.columns(2)
with left:
    cm.time_series(sale_df, y="price_sale", title="Median Sale Price • Trend")
with right:
    cm.time_series(sale_df, y="adr", title="Median ADR • Trend")

st.divider()

st.subheader("Inventory by Competitor")
comp = sale_df.groupby("competitor", as_index=False)["listing_id"].nunique().rename(columns={"listing_id": "count"})
st.bar_chart(comp.set_index("competitor")[["count"]])

st.divider()

st.subheader("Data Freshness by Source")
by_src = sale_df.groupby("source", as_index=False).agg(last_scrape=("scrape_time", "max"))
if not by_src.empty:
    by_src["age_hours"] = (by_src["last_scrape"].max() - by_src["last_scrape"]).dt.total_seconds() / 3600
    st.dataframe(by_src, use_container_width=True)
else:
    st.info("No data for current filters.")
