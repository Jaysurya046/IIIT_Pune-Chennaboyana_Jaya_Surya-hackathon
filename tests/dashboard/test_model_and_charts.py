"""Dashboard calculation and chart-contract tests."""

from decimal import Decimal

from tests.dashboard.helpers import sample_signal, sample_stress_result

from risk_engine.api.models import SignalListResponse
from risk_engine.dashboard.charts import (
    asset_class_figure,
    event_distribution_figure,
    issuer_loss_figure,
    sentiment_impact_figure,
)
from risk_engine.dashboard.model import (
    event_rows,
    signal_metrics,
    signal_rows,
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


def test_stress_groupings_reconcile_exactly() -> None:
    result = sample_stress_result()
    asset_rows = stress_by_asset_class(result)
    issuer_rows = stress_by_issuer(result)
    sector_rows = stress_by_sector(result)

    assert sum((row["Loss (USD)"] for row in asset_rows), Decimal("0")) == result.total_loss
    assert sum((row["Loss (USD)"] for row in issuer_rows), Decimal("0")) == result.total_loss
    assert sum((row["Loss (USD)"] for row in sector_rows), Decimal("0")) == result.total_loss
    assert {row["Group"] for row in asset_rows} == {"bond", "derivative", "equity", "loan"}


def test_figures_have_labeled_data_traces() -> None:
    signal = sample_signal()
    result = sample_stress_result()
    figures = [
        event_distribution_figure((signal,)),
        sentiment_impact_figure((signal,)),
        asset_class_figure(result),
        issuer_loss_figure(result),
    ]

    assert all(figure.data for figure in figures)
    assert figures[0].layout.title.text == "Signals by event type"
    assert figures[1].layout.yaxis.title.text == "Impact"
    assert figures[2].layout.yaxis.title.text == "USD"
    assert figures[3].layout.xaxis.title.text == "Loss (USD)"
