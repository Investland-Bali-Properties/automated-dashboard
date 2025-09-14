import pandas as pd
from typing import Optional

def format_currency(v: Optional[float], prefix: str = "", suffix: str = "") -> str:
    if v is None or pd.isna(v):
        return "N/A"
    try:
        v = float(v)
    except Exception:
        return "N/A"
    if v >= 1_000_000_000:
        return f"{prefix}{v/1_000_000_000:.2f}B{suffix}"
    if v >= 1_000_000:
        return f"{prefix}{v/1_000_000:.2f}M{suffix}"
    if v >= 1_000:
        return f"{prefix}{v/1_000:.1f}K{suffix}"
    return f"{prefix}{v:,.0f}{suffix}"


def abbreviate_number(v: Optional[float]) -> str:
    if v is None or pd.isna(v):
        return "N/A"
    try:
        v = float(v)
    except Exception:
        return "N/A"
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{v:,.0f}"
