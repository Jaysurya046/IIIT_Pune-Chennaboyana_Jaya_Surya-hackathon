"""Pure dashboard transformations and reconciliation helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from risk_engine.api.models import SignalListResponse, SourceStatusResponse
from risk_engine.nlp.models import RiskSignal
from risk_engine.stress.models import InstrumentStressResult, StressResult


@dataclass(frozen=True)
class SignalMetrics:
    total: int
    high_impact: int
    mean_impact: float
    source_count: int


def signal_metrics(response: SignalListResponse) -> SignalMetrics:
    items = response.items
    return SignalMetrics(
        total=response.total,
        high_impact=sum(item.impact_score > 7 for item in items),
        mean_impact=(sum(item.impact_score for item in items) / len(items) if items else 0.0),
        source_count=len({item.provenance.source for item in items}),
    )


def signal_rows(signals: tuple[RiskSignal, ...]) -> list[dict[str, object]]:
    return [
        {
            "Created (UTC)": signal.created_at.isoformat(),
            "Impact": signal.impact_score,
            "Event": signal.event.event_type.value,
            "Sentiment": signal.sentiment.label.value,
            "Sentiment score": signal.sentiment.score,
            "Entities": ", ".join(entity.name for entity in signal.entities) or "Unresolved",
            "Source": signal.provenance.source,
            "Synthetic": signal.provenance.synthetic,
            "Signal ID": signal.signal_id,
        }
        for signal in signals
    ]


def signal_timeline_rows(signals: tuple[RiskSignal, ...]) -> list[dict[str, object]]:
    """Return publication-grain signal evidence in stable chronological order."""

    rows = [
        {
            "Published (UTC)": signal.provenance.published_at,
            "Impact": signal.impact_score,
            "Event": signal.event.event_type.value,
            "Entities": ", ".join(entity.name for entity in signal.entities) or "Unresolved",
            "Source": signal.provenance.source,
            "Synthetic": signal.provenance.synthetic,
            "Signal ID": signal.signal_id,
        }
        for signal in signals
    ]
    return sorted(rows, key=lambda row: (row["Published (UTC)"], row["Signal ID"]))


def event_rows(signals: tuple[RiskSignal, ...]) -> list[dict[str, object]]:
    aggregates: dict[str, list[int]] = defaultdict(list)
    for signal in signals:
        aggregates[signal.event.event_type.value].append(signal.impact_score)
    return [
        {
            "Event": event,
            "Signal count": len(scores),
            "Mean impact": sum(scores) / len(scores),
        }
        for event, scores in sorted(aggregates.items())
    ]


def impact_factor_rows(signal: RiskSignal) -> list[dict[str, object]]:
    labels = {
        "event_severity_prior": "Event severity prior",
        "absolute_sentiment": "Absolute sentiment",
        "event_confidence": "Event confidence",
        "entity_relevance": "Entity relevance",
        "cross_source_corroboration": "Cross-source corroboration",
        "recency": "Recency",
    }
    values = signal.impact_factors.model_dump()
    return [{"Factor": labels[key], "Normalized value": values[key]} for key in labels]


def source_rows(status: SourceStatusResponse) -> list[dict[str, object]]:
    return [
        {
            "Source": item.source,
            "Type": item.source_type.value,
            "Status": "Healthy" if item.successful else "Failed",
            "Fetched": item.fetched_count,
            "Normalized": item.normalized_count,
            "Rejected": item.rejected_count,
            "Duplicates": item.duplicate_count,
            "Completed (UTC)": item.completed_at.isoformat(),
        }
        for item in status.sources
    ]


def instrument_rows(result: StressResult) -> list[dict[str, object]]:
    return [
        {
            "Instrument": item.instrument_id,
            "Issuer": item.issuer_id,
            "Sector": item.sector,
            "Asset class": item.asset_class.value,
            "Affected": item.affected,
            "Before (USD)": item.before_value,
            "After (USD)": item.after_value,
            "Loss (USD)": item.loss,
            "Expected loss before (USD)": item.expected_loss_before,
            "Expected loss after (USD)": item.expected_loss_after,
            "Rationale": item.rationale,
        }
        for item in result.instrument_results
    ]


def instrument_loss_rows(result: StressResult) -> list[dict[str, object]]:
    """Return descending instrument loss contributions after exact reconciliation."""

    rows = [
        {
            "Instrument": item.instrument_id,
            "Loss (USD)": item.loss,
            "Affected": item.affected,
        }
        for item in result.instrument_results
    ]
    if sum((row["Loss (USD)"] for row in rows), Decimal("0")) != result.total_loss:
        raise ValueError("Instrument loss waterfall does not reconcile to total loss")
    return sorted(rows, key=lambda row: (-row["Loss (USD)"], row["Instrument"]))


def _group_stress(
    items: tuple[InstrumentStressResult, ...], attribute: str
) -> list[dict[str, object]]:
    groups: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"before": Decimal("0"), "after": Decimal("0"), "loss": Decimal("0")}
    )
    for item in items:
        key_value = getattr(item, attribute)
        key = key_value.value if hasattr(key_value, "value") else str(key_value)
        groups[key]["before"] += item.before_value
        groups[key]["after"] += item.after_value
        groups[key]["loss"] += item.loss
    return [
        {
            "Group": key,
            "Before (USD)": amounts["before"],
            "After (USD)": amounts["after"],
            "Loss (USD)": amounts["loss"],
        }
        for key, amounts in sorted(groups.items())
    ]


def stress_by_asset_class(result: StressResult) -> list[dict[str, object]]:
    rows = _group_stress(result.instrument_results, "asset_class")
    if sum((row["Loss (USD)"] for row in rows), Decimal("0")) != result.total_loss:
        raise ValueError("Asset-class stress rows do not reconcile to total loss")
    return rows


def stress_by_issuer(result: StressResult) -> list[dict[str, object]]:
    rows = _group_stress(result.instrument_results, "issuer_id")
    if sum((row["Loss (USD)"] for row in rows), Decimal("0")) != result.total_loss:
        raise ValueError("Issuer stress rows do not reconcile to total loss")
    return rows


def stress_by_sector(result: StressResult) -> list[dict[str, object]]:
    rows = _group_stress(result.instrument_results, "sector")
    if sum((row["Loss (USD)"] for row in rows), Decimal("0")) != result.total_loss:
        raise ValueError("Sector stress rows do not reconcile to total loss")
    return rows


def applied_shock_rows(result: StressResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in result.instrument_results:
        for shock, value in sorted(item.applied_shocks.items()):
            rows.append(
                {
                    "Instrument": item.instrument_id,
                    "Shock": shock.replace("_", " ").title(),
                    "Value": value,
                }
            )
    return rows
