import streamlit as st
import pandas as pd
import io
import common as cm

st.set_page_config(page_title="Settings / Export", page_icon="⚙️", layout="wide")

st.title("Settings / Export")

with st.sidebar:
    st.header("Filters")

df = cm.get_data()
filtered, f = cm.render_global_filters(df)

st.subheader("Download Filtered Data")

csv = filtered.to_csv(index=False).encode('utf-8')
st.download_button("Download CSV", csv, file_name="filtered.csv", mime="text/csv")

# Parquet (in-memory)
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    table = pa.Table.from_pandas(filtered)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    st.download_button("Download Parquet", buf.getvalue(), file_name="filtered.parquet", mime="application/octet-stream")
except Exception:
    st.info("Install pyarrow to enable Parquet downloads.")

st.divider()

st.subheader("Cache & Refresh")
st.toggle("Enable cache", value=True, key="cache_toggle_settings")
if st.button("Refresh Dummy Data"):
    cm.get_data.clear()
    st.success("Dummy data cache cleared. Reload pages to regenerate.")
