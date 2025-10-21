"""
Utility helpers for formatting numeric values, currency strings, and percentages.
"""

from __future__ import annotations

from typing import Optional

SCALE_FACTORS = [
    (1_000_000_000_000, "T"),
    (1_000_000_000, "B"),
    (1_000_000, "M"),
    (1_000, "K"),
]


def format_number(value: Optional[float], decimals: int = 0) -> str:
    if value is None:
        return "–"
    try:
        return f"{value:,.{decimals}f}"
    except (TypeError, ValueError):
        return "–"


def _scale_value(value: float):
    for factor, suffix in SCALE_FACTORS:
        if abs(value) >= factor:
            return value / factor, suffix
    return value, ""


def format_currency(
    value: Optional[float],
    currency: str = "IDR",
    decimals: int = 0,
    compact: bool = True,
) -> str:
    if value is None:
        return "–"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "–"

    suffix = ""
    display_value = numeric
    if compact:
        display_value, suffix = _scale_value(numeric)
    formatted = f"{display_value:,.{decimals}f}"
    return f"{currency} {formatted}{suffix}"


def format_percent(value: Optional[float], decimals: int = 1) -> str:
    if value is None:
        return "–"
    try:
        return f"{value:.{decimals}f}%"
    except (TypeError, ValueError):
        return "–"
