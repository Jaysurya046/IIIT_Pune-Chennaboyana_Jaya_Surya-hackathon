"""Plotly figure builders with consistent labels and units."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from risk_engine.dashboard.model import (
    event_rows,
    signal_rows,
    stress_by_asset_class,
    stress_by_issuer,
)
from risk_engine.nlp.models import RiskSignal
from risk_engine.stress.models import StressResult

COLORS = {
    "navy": "#12355b",
    "blue": "#1976d2",
    "teal": "#00897b",
    "amber": "#f9a825",
    "red": "#c62828",
    "slate": "#607d8b",
}


def _layout(figure: go.Figure, *, height: int = 350) -> go.Figure:
    figure.update_layout(
        height=height,
        margin={"l": 16, "r": 16, "t": 48, "b": 16},
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"family": "Inter, Segoe UI, sans-serif", "color": "#213547"},
        legend_title_text="",
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#e7edf3")
    return figure


def event_distribution_figure(signals: tuple[RiskSignal, ...]) -> go.Figure:
    frame = pd.DataFrame(event_rows(signals))
    figure = px.bar(
        frame,
        x="Event",
        y="Signal count",
        color="Mean impact",
        color_continuous_scale=["#bbdefb", COLORS["navy"]],
        range_color=(1, 10),
        title="Signals by event type",
        text_auto=True,
    )
    return _layout(figure)


def sentiment_impact_figure(signals: tuple[RiskSignal, ...]) -> go.Figure:
    frame = pd.DataFrame(signal_rows(signals))
    figure = px.scatter(
        frame,
        x="Sentiment score",
        y="Impact",
        color="Event",
        hover_data=["Entities", "Source", "Synthetic"],
        range_x=(-1.05, 1.05),
        range_y=(0.5, 10.5),
        title="Sentiment and assessed impact",
    )
    figure.add_hline(y=7, line_dash="dash", line_color=COLORS["red"])
    return _layout(figure)


def asset_class_figure(result: StressResult) -> go.Figure:
    frame = pd.DataFrame(stress_by_asset_class(result))
    melted = frame.melt(
        id_vars="Group",
        value_vars=["Before (USD)", "After (USD)"],
        var_name="Valuation",
        value_name="USD",
    )
    figure = px.bar(
        melted,
        x="Group",
        y="USD",
        color="Valuation",
        barmode="group",
        color_discrete_map={
            "Before (USD)": COLORS["slate"],
            "After (USD)": COLORS["blue"],
        },
        title="Portfolio value by asset class",
    )
    figure.update_yaxes(tickprefix="$", tickformat="~s")
    return _layout(figure)


def issuer_loss_figure(result: StressResult) -> go.Figure:
    frame = pd.DataFrame(stress_by_issuer(result))
    frame = frame.sort_values("Loss (USD)", ascending=True)
    figure = px.bar(
        frame,
        x="Loss (USD)",
        y="Group",
        orientation="h",
        color_discrete_sequence=[COLORS["red"]],
        title="Illustrative loss by issuer",
    )
    figure.update_xaxes(tickprefix="$", tickformat="~s")
    return _layout(figure)
