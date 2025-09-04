import streamlit as st
import common as cm

st.set_page_config(page_title="Rental Analytics", page_icon="🏨", layout="wide")

st.title("Rental Analytics")

with st.sidebar:
    st.header("Filters")

df = cm.get_data()
filtered, _ = cm.render_global_filters(df)

rent_df = filtered[filtered["status"] == "success"].copy()

c1, c2 = st.columns(2)
with c1:
    cm.box_by(rent_df, x="region", y="adr", title="ADR by Region")
with c2:
    cm.box_by(rent_df, x="bedrooms", y="adr", title="ADR by Bedrooms")

st.divider()

cm.time_series(rent_df, y="adr", title="Median ADR over Time")

st.divider()

st.subheader("Inventory Mix")
inv = rent_df.groupby(["region", "bedrooms"], as_index=False)["listing_id"].nunique().rename(columns={"listing_id": "count"})
st.dataframe(inv.sort_values(["region", "bedrooms"]), use_container_width=True)

st.caption("Note: Persistence/turnover are approximated in this dummy app.")
