"""
Plotly chart factory functions with consistent styling for the dashboard.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


DEFAULT_TEMPLATE = "plotly_white"
DEFAULT_COLOR_SEQUENCE = [
    "#1f77b4",  # blue for sale metrics
    "#ff7f0e",  # orange for rent metrics
    "#2ca02c",  # green for occupancy/yield
    "#d62728",  # red for warnings/outliers
    "#9467bd",
    "#8c564b",
]


def _configure_layout(
    fig: go.Figure,
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    yaxis_tickformat: Optional[str] = None,
    legend_title: Optional[str] = None,
) -> go.Figure:
    fig.update_layout(
        template=DEFAULT_TEMPLATE,
        colorway=DEFAULT_COLOR_SEQUENCE,
        title=title,
        legend_title=legend_title,
        hovermode="x unified",
        margin=dict(l=40, r=20, t=60, b=40),
    )
    if yaxis_title:
        fig.update_yaxes(title=yaxis_title)
    if yaxis_tickformat:
        fig.update_yaxes(tickformat=yaxis_tickformat)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, zeroline=True)
    return fig


def render_plotly(fig: go.Figure) -> None:
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    yaxis_tickformat: Optional[str] = None,
    markers: bool = True,
    category_orders: Optional[Dict[str, List[str]]] = None,
    hover_data: Optional[List[str]] = None,
) -> go.Figure:
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        markers=markers,
        category_orders=category_orders,
        hover_data=hover_data,
    )
    fig = _configure_layout(fig, title, yaxis_title, yaxis_tickformat)
    return fig


def area_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    yaxis_tickformat: Optional[str] = None,
    stackgroup: str = "one",
) -> go.Figure:
    fig = px.area(
        df,
        x=x,
        y=y,
        color=color,
        line_group=color,
    )
    fig.update_traces(stackgroup=stackgroup, mode="none")
    fig = _configure_layout(fig, title, yaxis_title, yaxis_tickformat)
    return fig


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    barmode: str = "group",
    orientation: str = "v",
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    yaxis_tickformat: Optional[str] = None,
    category_orders: Optional[Dict[str, List[str]]] = None,
    text_auto: bool = False,
) -> go.Figure:
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        barmode=barmode,
        orientation=orientation,
        category_orders=category_orders,
        text_auto=text_auto,
    )
    fig = _configure_layout(fig, title, yaxis_title, yaxis_tickformat)
    if text_auto:
        fig.update_traces(textposition="outside", cliponaxis=False)
    return fig


def box_plot(
    df: pd.DataFrame,
    x: Optional[str],
    y: str,
    color: Optional[str] = None,
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    yaxis_tickformat: Optional[str] = None,
) -> go.Figure:
    fig = px.box(
        df,
        x=x,
        y=y,
        color=color,
        points="all",
    )
    fig = _configure_layout(fig, title, yaxis_title, yaxis_tickformat)
    fig.update_traces(boxmean="sd")
    return fig


def strip_plot(
    df: pd.DataFrame,
    x: Optional[str],
    y: str,
    color: Optional[str] = None,
    orientation: str = "v",
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    yaxis_tickformat: Optional[str] = None,
    hover_data: Optional[list[str]] = None,
) -> go.Figure:
    fig = px.strip(
        df,
        x=x,
        y=y,
        color=color,
        orientation=orientation,
        hover_data=hover_data,
    )
    fig = _configure_layout(fig, title, yaxis_title, yaxis_tickformat)
    fig.update_traces(marker=dict(opacity=0.6, size=8), jitter=0.35)
    return fig


def scatter_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    size: Optional[str] = None,
    hover_data: Optional[List[str]] = None,
    log_x: bool = False,
    log_y: bool = False,
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    yaxis_tickformat: Optional[str] = None,
) -> go.Figure:
    fig = px.scatter(
        df,
        x=x,
        y=y,
        color=color,
        size=size,
        hover_data=hover_data,
        log_x=log_x,
        log_y=log_y,
    )
    fig = _configure_layout(fig, title, yaxis_title, yaxis_tickformat)
    return fig


def heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    z: str,
    title: Optional[str] = None,
    color_scale: str = "Viridis",
    text_auto: bool = True,
) -> go.Figure:
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
    fig = px.imshow(
        pivot,
        color_continuous_scale=color_scale,
        aspect="auto",
    )
    fig = _configure_layout(fig, title)
    if text_auto:
        fig.update_traces(texttemplate="%{z:.1f}", textfont_size=12)
    return fig


def histogram(
    df: pd.DataFrame,
    x: str,
    color: Optional[str] = None,
    nbins: Optional[int] = None,
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
) -> go.Figure:
    fig = px.histogram(
        df,
        x=x,
        color=color,
        nbins=nbins,
    )
    fig = _configure_layout(fig, title, yaxis_title)
    return fig


def trend_with_ma(
    df: pd.DataFrame,
    x: str,
    y: str,
    window: int = 3,
    title: Optional[str] = None,
    yaxis_title: Optional[str] = None,
    yaxis_tickformat: Optional[str] = None,
) -> go.Figure:
    line = px.line(df, x=x, y=y)
    line = _configure_layout(line, title, yaxis_title, yaxis_tickformat)
    rolling = df[[x, y]].dropna().copy()
    rolling["ma"] = rolling[y].rolling(window=window).mean()
    if not rolling["ma"].dropna().empty:
        line.add_trace(
            go.Scatter(
                x=rolling[x],
                y=rolling["ma"],
                mode="lines",
                name=f"{window}-period MA",
                line=dict(dash="dash"),
            )
        )
    return line
