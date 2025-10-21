"""
Reusable helpers for rendering data tables with consistent configuration.
"""

from __future__ import annotations

from typing import Dict, Optional, List

import pandas as pd
import streamlit as st

from src.ui.components.formatting import format_currency, format_number, format_percent


def render_table(
    df: pd.DataFrame,
    column_config: Optional[Dict[str, Dict[str, str]]] = None,
    height: int = 400,
    show_index: bool = False,
    export_file_name: str = "export.csv",
    highlight_cols: Optional[List[str]] = None,
) -> None:
    if df.empty:
        st.info("Tidak ada data untuk ditampilkan.")
        return

    formatted_df = df.copy()
    if column_config:
        for column, config in column_config.items():
            if column not in formatted_df.columns:
                continue
            fmt_type = config.get("type")
            if fmt_type == "currency":
                currency = config.get("currency", "IDR")
                decimals = int(config.get("decimals", 0))
                formatted_df[column] = formatted_df[column].apply(
                    lambda v: format_currency(v, currency=currency, decimals=decimals)
                )
            elif fmt_type == "percent":
                decimals = int(config.get("decimals", 1))
                formatted_df[column] = formatted_df[column].apply(
                    lambda v: format_percent(v, decimals=decimals)
                )
            elif fmt_type == "number":
                decimals = int(config.get("decimals", 0))
                formatted_df[column] = formatted_df[column].apply(
                    lambda v: format_number(v, decimals=decimals)
                )

    dataframe_obj = formatted_df
    if highlight_cols:
        highlight_cols = [col for col in highlight_cols if col in formatted_df.columns]
        if highlight_cols:
            def _style_func(val):
                try:
                    if isinstance(val, str):
                        val = val.replace("%", "").replace(",", "")
                    num = float(val)
                except (TypeError, ValueError):
                    return ""
                if num > 0:
                    return "color: #2ca02c;"
                if num < 0:
                    return "color: #d62728;"
                return ""

            dataframe_obj = formatted_df.style.applymap(_style_func, subset=highlight_cols)

    st.dataframe(
        dataframe_obj,
        use_container_width=True,
        height=height,
        hide_index=not show_index,
    )

    csv_bytes = df.to_csv(index=show_index).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=export_file_name,
        mime="text/csv",
    )
