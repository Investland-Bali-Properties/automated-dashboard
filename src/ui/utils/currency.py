from __future__ import annotations

import pandas as pd

FX_RATE_DEFAULT = 15_000.0


def series_to_currency(
    series: pd.Series,
    target_currency: str,
    fallback_series: pd.Series | None = None,
    fx_rate: float = FX_RATE_DEFAULT,
) -> pd.Series:
    if target_currency == "IDR":
        return series
    if fallback_series is not None and fallback_series.notna().any():
        return fallback_series
    return series / fx_rate


def scalar_to_currency(
    value: float | None,
    target_currency: str,
    fallback_value: float | None = None,
    fx_rate: float = FX_RATE_DEFAULT,
) -> float | None:
    if value is None:
        return fallback_value if target_currency == "USD" else None
    if target_currency == "IDR":
        return value
    if fallback_value is not None:
        return fallback_value
    return value / fx_rate
