"""Impact formula and boundary tests."""

from datetime import UTC, datetime, timedelta

from risk_engine.nlp.impact import ImpactScorer
from risk_engine.nlp.models import EventClassification, EventType, SentimentLabel, SentimentResult


def _sentiment(score: float) -> SentimentResult:
    return SentimentResult(
        label=SentimentLabel.NEUTRAL,
        score=score,
        confidence=0.5,
        probabilities={
            SentimentLabel.POSITIVE: 0.25,
            SentimentLabel.NEUTRAL: 0.5,
            SentimentLabel.NEGATIVE: 0.25,
        },
    )


def _event(confidence: float) -> EventClassification:
    return EventClassification(
        event_type=EventType.OTHER,
        confidence=confidence,
        semantic_score=0.0,
        keyword_score=0.0,
    )


def test_impact_formula_reaches_documented_upper_boundary() -> None:
    score, factors = ImpactScorer().score(
        event=_event(1.0),
        sentiment=_sentiment(-1.0),
        event_severity_prior=1.0,
        entity_relevance=1.0,
        cross_source_corroboration=1.0,
        recency=1.0,
    )

    assert score == 10
    assert factors.absolute_sentiment == 1.0


def test_impact_formula_clamps_empty_factors_to_one() -> None:
    score, _ = ImpactScorer().score(
        event=_event(0.0),
        sentiment=_sentiment(0.0),
        event_severity_prior=0.0,
        entity_relevance=0.0,
        cross_source_corroboration=0.0,
        recency=0.0,
    )

    assert score == 1


def test_recency_decays_linearly_over_seventy_two_hours() -> None:
    now = datetime(2026, 10, 2, tzinfo=UTC)

    assert ImpactScorer.recency(now - timedelta(hours=36), now) == 0.5
    assert ImpactScorer.recency(now - timedelta(hours=80), now) == 0.0
