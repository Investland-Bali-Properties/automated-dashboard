from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import streamlit as st

from src.ui.components.formatting import format_currency, format_number, format_percent


@dataclass
class KpiCard:
    label: str
    value: Optional[float] = None
    value_display: Optional[str] = None
    currency: Optional[str] = None
    decimals: int = 0
    compact: bool = True
    delta: Optional[float] = None
    delta_display: Optional[str] = None
    delta_format: str = "pct"  # pct | abs
    help_text: Optional[str] = None


def _format_value(card: KpiCard) -> str:
    if card.value_display is not None:
        return card.value_display
    if card.currency:
        return format_currency(card.value, currency=card.currency, decimals=card.decimals, compact=card.compact)
    return format_number(card.value, decimals=card.decimals)


def _format_delta(card: KpiCard) -> Optional[str]:
    if card.delta_display is not None:
        return card.delta_display
    if card.delta is None:
        return None
    if card.delta_format == "pct":
        return format_percent(card.delta)
    return format_number(card.delta, decimals=card.decimals)


def render_kpi_cards(cards: Sequence[KpiCard], columns: int = 3) -> None:
    """
    Render KPI cards in a responsive grid using Streamlit columns.
    """
    cards = list(cards)
    if not cards:
        st.info("KPI belum tersedia untuk filter saat ini.")
        return

    columns = max(columns, 1)
    for idx in range(0, len(cards), columns):
        row_cards = cards[idx: idx + columns]
        cols = st.columns(len(row_cards))
        for col, card in zip(cols, row_cards):
            with col:
                value = _format_value(card)
                delta = _format_delta(card)
                st.metric(label=card.label, value=value, delta=delta)
                if card.help_text:
                    st.caption(card.help_text)
