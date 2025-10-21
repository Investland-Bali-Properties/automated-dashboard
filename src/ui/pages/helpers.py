from __future__ import annotations

from typing import Iterable, Optional, Tuple

import numpy as np
import pandas as pd


def safe_median(series: pd.Series) -> Optional[float]:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return float(cleaned.median())


def safe_sum(series: pd.Series) -> Optional[float]:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return float(cleaned.sum())


def trim_outliers(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    cleaned = pd.to_numeric(series, errors="coerce")
    if cleaned.dropna().empty:
        return cleaned
    low, high = cleaned.quantile([lower, upper])
    return cleaned.clip(lower=low, upper=high)


def bucketize(series: pd.Series, bins: Iterable[int], labels: Iterable[str]) -> pd.Series:
    return pd.cut(series, bins=bins, labels=labels, include_lowest=True)


def resample_median(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: str = "M",
) -> pd.DataFrame:
    if date_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=[date_col, value_col])
    working = df[[date_col, value_col]].dropna()
    if working.empty:
        return pd.DataFrame(columns=[date_col, value_col])
    ts = (
        working.set_index(date_col)
        .sort_index()
        .resample(freq)
        .median()
        .reset_index()
    )
    return ts


def resample_sum(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: str = "M",
) -> pd.DataFrame:
    if date_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=[date_col, value_col])
    working = df[[date_col, value_col]].dropna()
    if working.empty:
        return pd.DataFrame(columns=[date_col, value_col])
    ts = (
        working.set_index(date_col)
        .sort_index()
        .resample(freq)
        .sum()
        .reset_index()
    )
    return ts


def latest_and_previous(
    df: pd.DataFrame,
    date_col: str,
) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    if date_col not in df.columns or df.empty:
        return None, None
    dates = df[date_col].dropna().sort_values()
    if dates.empty:
        return None, None
    latest = dates.max()
    previous = dates[dates < latest].max() if len(dates) > 1 else None
    return latest, previous


def pct_change(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous in (None, 0):
        return None
    try:
        return ((current - previous) / previous) * 100
    except ZeroDivisionError:
        return None
