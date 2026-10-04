"""Dashboard calculation and chart-contract tests."""

from decimal import Decimal

from tests.dashboard.helpers import sample_signal, sample_stress_result

from risk_engine.api.models import SignalListResponse
from risk_engine.dashboard.charts import (
    EVENT_COLORS,
    asset_class_figure,
    event_distribution_figure,
    instrument_loss_waterfall_figure,
    issuer_loss_figure,
    sentiment_impact_figure,
    signal_timeline_figure,
)
from risk_engine.dashboard.model import (
    event_rows,
    instrument_loss_rows,
    signal_metrics,
    signal_rows,
    signal_timeline_rows,
    stress_by_asset_class,
    stress_by_issuer,
    stress_by_sector,
)


def test_signal_metrics_rows_and_event_aggregation() -> None:
    high = sample_signal(impact_score=9)
    low = sample_signal(impact_score=6).model_copy(update={"signal_id": "c" * 32})
    response = SignalListResponse(total=2, limit=100, offset=0, items=(high, low))

    metrics = signal_metrics(response)
    rows = signal_rows(response.items)
    events = event_rows(response.items)

    assert metrics.total == 2
    assert metrics.high_impact == 1
    assert metrics.mean_impact == 7.5
    assert metrics.source_count == 1
    assert rows[0]["Synthetic"] is True
    assert events == [{"Event": "Credit Event", "Signal count": 2, "Mean impact": 7.5}]


def test_signal_timeline_rows_and_figure_use_publication_time() -> None:
    later = sample_signal().model_copy(update={"signal_id": "c" * 32})
    earlier = sample_signal(impact_score=6).model_copy(
        update={
            "signal_id": "d" * 32,
            "provenance": sample_signal().provenance.model_copy(
                update={"published_at": sample_signal().provenance.published_at.replace(day=1)}
            ),
        }
    )

    rows = signal_timeline_rows((later, earlier))
    figure = signal_timeline_figure((later, earlier))

    assert [row["Signal ID"] for row in rows] == ["d" * 32, "c" * 32]
    assert figure.layout.title.text == "Signal publication timeline"
    assert figure.layout.xaxis.title.text == "Published (UTC)"
    assert figure.layout.yaxis.title.text == "Impact"
    assert sum(len(trace.x) for trace in figure.data) == 2
    assert {trace.name for trace in figure.data} == {"Credit Event"}
    assert figure.data[0].marker.color == EVENT_COLORS["Credit Event"]
    assert [str(value)[:10] for value in figure.data[0].x] == ["2026-10-01", "2026-10-02"]
    assert list(figure.data[0].y) == [6, 9]


def test_signal_timeline_empty_state_is_explicit() -> None:
    figure = signal_timeline_figure(())

    assert not figure.data
    assert figure.layout.annotations[0].text == "No signals match the current filters"


def test_stress_groupings_reconcile_exactly() -> None:
    result = sample_stress_result()
    asset_rows = stress_by_asset_class(result)
    issuer_rows = stress_by_issuer(result)
    sector_rows = stress_by_sector(result)

    assert sum((row["Loss (USD)"] for row in asset_rows), Decimal("0")) == result.total_loss
    assert sum((row["Loss (USD)"] for row in issuer_rows), Decimal("0")) == result.total_loss
    assert sum((row["Loss (USD)"] for row in sector_rows), Decimal("0")) == result.total_loss
    assert {row["Group"] for row in asset_rows} == {"bond", "derivative", "equity", "loan"}


def test_instrument_loss_waterfall_is_descending_and_reconciled() -> None:
    result = sample_stress_result()
    rows = instrument_loss_rows(result)
    figure = instrument_loss_waterfall_figure(result)
    trace = figure.data[0]

    losses = [row["Loss (USD)"] for row in rows]
    assert losses == sorted(losses, reverse=True)
    assert all(loss >= Decimal("0") for loss in losses)
    assert sum(losses, Decimal("0")) == result.total_loss
    assert list(trace.y[:-1]) == [row["Instrument"] for row in rows]
    assert trace.y[-1] == "Reconciled total"
    assert list(trace.measure[:-1]) == ["relative"] * len(rows)
    assert trace.measure[-1] == "total"
    assert Decimal(str(trace.x[-1])) == result.total_loss


def test_figures_have_labeled_data_traces() -> None:
    signal = sample_signal()
    result = sample_stress_result()
    figures = [
        event_distribution_figure((signal,)),
        sentiment_impact_figure((signal,)),
        signal_timeline_figure((signal,)),
        asset_class_figure(result),
        issuer_loss_figure(result),
        instrument_loss_waterfall_figure(result),
    ]

    assert all(figure.data for figure in figures)
    assert figures[0].layout.title.text == "Signals by event type"
    assert figures[1].layout.yaxis.title.text == "Impact"
    assert figures[2].layout.yaxis.title.text == "Impact"
    assert figures[3].layout.yaxis.title.text == "USD"
    assert figures[4].layout.xaxis.title.text == "Loss (USD)"
    assert figures[5].layout.xaxis.title.text == "Loss (USD)"
