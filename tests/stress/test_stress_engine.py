"""Trigger, scope, and portfolio reconciliation tests."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from risk_engine.ingestion.models import Provenance, SourceType
from risk_engine.nlp.models import (
    EntityMatch,
    EventClassification,
    EventType,
    ImpactFactors,
    RiskSignal,
    SentimentLabel,
    SentimentResult,
)
from risk_engine.stress.config import load_portfolio, load_scenario_book
from risk_engine.stress.engine import StressEngine
from risk_engine.stress.models import HypotheticalStressAssumptions

NOW = datetime(2026, 10, 2, tzinfo=UTC)


def _signal(
    impact_score: int,
    event_type: EventType = EventType.CREDIT_EVENT,
    *,
    with_entity: bool = True,
    synthetic: bool = True,
) -> RiskSignal:
    entities = (
        (
            EntityMatch(
                entity_id="northstar-energy",
                name="Northstar Energy",
                ticker="NSEY",
                sector="Energy",
                country="United States",
                matched_alias="Northstar Energy",
                match_type="name",
                confidence=1.0,
            ),
        )
        if with_entity
        else ()
    )
    return RiskSignal(
        signal_id="a" * 32,
        document_id="b" * 32,
        canonical_url="https://news.example.org/test",
        entities=entities,
        sentiment=SentimentResult(
            label=SentimentLabel.NEGATIVE,
            score=-0.8,
            confidence=0.9,
            probabilities={
                SentimentLabel.POSITIVE: 0.05,
                SentimentLabel.NEUTRAL: 0.05,
                SentimentLabel.NEGATIVE: 0.9,
            },
        ),
        event=EventClassification(
            event_type=event_type,
            confidence=0.95,
            semantic_score=0.8,
            keyword_score=1.0,
            evidence=("default",),
        ),
        impact_score=impact_score,
        impact_factors=ImpactFactors(
            event_severity_prior=0.95,
            absolute_sentiment=0.8,
            event_confidence=0.95,
            entity_relevance=1.0 if with_entity else 0.3,
            cross_source_corroboration=0.5,
            recency=1.0,
        ),
        rationale=("Synthetic test signal.",),
        model_versions={"sentiment": "test"},
        created_at=NOW,
        provenance=Provenance(
            source="test",
            source_type=SourceType.NEWS,
            source_id="test-1",
            original_url="https://news.example.org/test",
            query="test",
            published_at=NOW,
            retrieved_at=NOW,
            language="en",
            synthetic=synthetic,
        ),
    )


def _engine() -> StressEngine:
    return StressEngine(
        load_portfolio(Path("data/portfolio/portfolio.json")),
        load_scenario_book(Path("data/portfolio/scenarios.json")),
        clock=lambda: NOW,
    )


def test_trigger_is_strictly_greater_than_seven() -> None:
    skipped = _engine().run(_signal(7))
    triggered = _engine().run(_signal(8))

    assert skipped.triggered is False
    assert skipped.result is None
    assert triggered.triggered is True
    assert triggered.result is not None


def test_entity_scenario_only_stresses_matching_issuer_and_reconciles() -> None:
    result = _engine().run(_signal(9)).result

    assert result is not None
    assert result.scenario_id == "issuer-credit-event"
    assert result.affected_scope == ("northstar-energy",)
    assert result.affected_position_count == 2
    assert result.before_value == Decimal("55500000.00")
    assert result.after_value == Decimal("53150000.00")
    assert result.total_loss == Decimal("2350000.00")
    assert result.expected_loss_change == Decimal("300000.00")
    assert result.reconciliation_difference == Decimal("0.00")
    assert sum(item.loss for item in result.instrument_results) == result.total_loss


def test_non_synthetic_signal_result_is_labeled_as_illustrative_proxy() -> None:
    decision = _engine().run(_signal(9, synthetic=False))

    assert decision.result is not None
    assert decision.result.exposure_label == "illustrative sector proxy"


def test_portfolio_scenario_stresses_every_position() -> None:
    decision = _engine().run(_signal(8, EventType.MACROECONOMIC, with_entity=False))

    assert decision.result is not None
    assert decision.result.affected_scope == ("portfolio",)
    assert decision.result.affected_position_count == 8
    assert decision.result.total_loss > 0


def test_entity_scenario_without_resolved_entity_is_auditable_no_op() -> None:
    decision = _engine().run(_signal(8, with_entity=False))

    assert decision.result is not None
    assert decision.result.affected_scope == ()
    assert decision.result.affected_position_count == 0
    assert decision.result.total_loss == Decimal("0.00")


def test_stress_identifier_is_stable() -> None:
    first = _engine().run(_signal(8)).result
    second = _engine().run(_signal(8)).result

    assert first is not None and second is not None
    assert first.stress_id == second.stress_id


def test_hypothetical_stress_uses_assumptions_without_a_risk_signal() -> None:
    assumptions = HypotheticalStressAssumptions(
        event_type=EventType.CREDIT_EVENT,
        entity_ids=("aurora-bank",),
        impact_score=9,
    )

    first = _engine().run_hypothetical(assumptions)
    second = _engine().run_hypothetical(assumptions)

    assert first.triggered is True
    assert first.result is not None
    assert first.result.affected_scope == ("aurora-bank",)
    assert first.result.affected_position_count == 2
    assert first.result.reconciliation_difference == Decimal("0.00")
    assert first.signal_id == second.signal_id
    assert first.result.stress_id == second.result.stress_id


def test_hypothetical_stress_retains_strict_trigger_boundary() -> None:
    decision = _engine().run_hypothetical(
        HypotheticalStressAssumptions(
            event_type=EventType.OPERATIONAL,
            entity_ids=("atlas-manufacturing",),
            impact_score=7,
        )
    )

    assert decision.triggered is False
    assert decision.result is None
