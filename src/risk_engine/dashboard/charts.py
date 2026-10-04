"""Plotly figure builders with consistent labels and units."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from risk_engine.dashboard.model import (
    event_rows,
    instrument_loss_rows,
    signal_rows,
    signal_timeline_rows,
    stress_by_asset_class,
    stress_by_issuer,
)
from risk_engine.nlp.models import EventType, RiskSignal
from risk_engine.stress.models import StressResult

COLORS = {
    "navy": "#12355b",
    "blue": "#1976d2",
    "teal": "#00897b",
    "amber": "#f9a825",
    "red": "#c62828",
    "slate": "#607d8b",
}

EVENT_COLORS = {
    EventType.GEOPOLITICAL.value: "#5e35b1",
    EventType.MACROECONOMIC.value: "#1976d2",
    EventType.CREDIT_EVENT.value: "#c62828",
    EventType.MERGER_ACQUISITION.value: "#00897b",
    EventType.PRODUCT_LAUNCH.value: "#43a047",
    EventType.REGULATORY.value: "#f57c00",
    EventType.OPERATIONAL.value: "#6d4c41",
    EventType.OTHER.value: "#607d8b",
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


def signal_timeline_figure(signals: tuple[RiskSignal, ...]) -> go.Figure:
    rows = signal_timeline_rows(signals)
    if not rows:
        figure = go.Figure()
        figure.update_layout(title="Signal publication timeline")
        figure.add_annotation(
            text="No signals match the current filters",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        figure.update_xaxes(title="Published (UTC)")
        figure.update_yaxes(title="Impact", range=(0.5, 10.5))
        return _layout(figure)

    frame = pd.DataFrame(rows)
    figure = px.scatter(
        frame,
        x="Published (UTC)",
        y="Impact",
        color="Event",
        color_discrete_map=EVENT_COLORS,
        category_orders={"Event": [event.value for event in EventType]},
        hover_data=["Entities", "Source", "Synthetic", "Signal ID"],
        range_y=(0.5, 10.5),
        title="Signal publication timeline",
    )
    figure.update_traces(marker={"size": 12, "line": {"width": 1, "color": "white"}})
    figure.add_hline(
        y=7,
        line_dash="dash",
        line_color=COLORS["red"],
        annotation_text="Stress trigger: impact > 7",
        annotation_position="top left",
    )
    figure.update_layout(hovermode="closest")
    figure = _layout(figure, height=390)
    figure.update_layout(margin={"l": 16, "r": 16, "t": 48, "b": 84})
    figure.update_xaxes(title={"text": "Published (UTC)", "standoff": 36})
    return figure


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


def instrument_loss_waterfall_figure(result: StressResult) -> go.Figure:
    rows = instrument_loss_rows(result)
    instruments = [str(row["Instrument"]) for row in rows]
    losses = [float(row["Loss (USD)"]) for row in rows]
    figure = go.Figure(
        go.Waterfall(
            name="Illustrative loss",
            orientation="h",
            measure=[*["relative"] * len(rows), "total"],
            x=[*losses, float(result.total_loss)],
            y=[*instruments, "Reconciled total"],
            text=[*[f"${loss:,.0f}" for loss in losses], f"${result.total_loss:,.0f}"],
            textposition="outside",
            connector={"line": {"color": COLORS["slate"], "width": 1}},
            increasing={"marker": {"color": COLORS["red"]}},
            totals={"marker": {"color": COLORS["navy"]}},
            hovertemplate="%{y}<br>Loss: $%{x:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(title="Illustrative loss waterfall by instrument")
    figure.update_xaxes(
        title="Loss (USD)",
        tickprefix="$",
        tickformat="~s",
        range=(0, float(result.total_loss) * 1.18 if result.total_loss else 1),
    )
    figure.update_yaxes(
        title=None,
        categoryorder="array",
        categoryarray=figure.data[0].y,
        autorange="reversed",
    )
    figure = _layout(figure, height=500)
    figure.update_layout(margin={"l": 112, "r": 128, "t": 48, "b": 56})
    return figure
