import streamlit as st
import pandas as pd
from components.quality_checks import (
    missing_values_summary,
    duplicate_count,
    exchange_rate_consistency,
    build_quality_overview,
)


def page_data_quality(df: pd.DataFrame):
    st.subheader("Data Quality & Monitoring")
    if df.empty:
        st.info("Dataset is empty.")
        return

    overview = build_quality_overview(df)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rows", f"{overview['row_count']:,}")
    with col2:
        st.metric("Duplicates", f"{overview['duplicate_count']:,}")
    with col3:
        if overview.get("distinct_properties") is not None:
            st.metric("Distinct Properties", f"{overview['distinct_properties']:,}")

    # Scraped_at parse stats
    if {"scraped_at_parse_ok","scraped_at_raw"}.issubset(df.columns):
        total = len(df)
        valid = int(df["scraped_at_parse_ok"].sum())
        invalid = total - valid
        pct_valid = (valid/total*100) if total else 0
        with st.expander("scraped_at Parsing Stats", expanded=False):
            st.write(f"Valid timestamps: **{valid:,}** ({pct_valid:.2f}%) | Invalid/Empty: **{invalid:,}**")
            # Failure reasons distribution if available
            if "scraped_at_parse_fail_reason" in df.columns:
                reason_counts = (
                    df.loc[~df["scraped_at_parse_ok"], "scraped_at_parse_fail_reason"]
                      .fillna("(blank)")
                      .value_counts()
                      .reset_index()
                )
                reason_counts.columns = ["reason", "count"]
                if not reason_counts.empty:
                    st.write("#### Failure Reasons")
                    st.dataframe(reason_counts, hide_index=True)
            sample_invalid = df.loc[~df["scraped_at_parse_ok"], "scraped_at_raw"].dropna().unique()[:25]
            if len(sample_invalid):
                st.caption("Sample invalid raw values:")
                st.code("\n".join(map(str, sample_invalid)))
            else:
                st.caption("All rows parsed successfully.")

    st.write("### Missing Values")
    mv = missing_values_summary(df)
    st.dataframe(mv, width="stretch", height=400)

    st.write("### Exchange Rate Consistency")
    fx_df = exchange_rate_consistency(df)
    if fx_df.empty:
        st.caption("Insufficient data to compute FX consistency.")
    else:
        st.dataframe(fx_df.head(500), width="stretch")
        st.caption("Showing up to 500 rows.")
