"""Small validated model factories shared by dashboard tests."""

from datetime import UTC, datetime
from pathlib import Path

from risk_engine.config import Settings
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
from risk_engine.stress.factory import build_stress_engine
from risk_engine.stress.models import StressResult

NOW = datetime(2026, 10, 2, tzinfo=UTC)


def sample_signal(*, impact_score: int = 9) -> RiskSignal:
    return RiskSignal(
        signal_id="a" * 32,
        document_id="b" * 32,
        canonical_url="https://news.example.org/test",
        entities=(
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
        ),
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
            event_type=EventType.CREDIT_EVENT,
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
            entity_relevance=1.0,
            cross_source_corroboration=0.5,
            recency=1.0,
        ),
        rationale=("Synthetic test signal.",),
        model_versions={"sentiment": "test"},
        created_at=NOW,
        provenance=Provenance(
            source="gdelt",
            source_type=SourceType.NEWS,
            source_id="test-1",
            original_url="https://news.example.org/test",
            query="test",
            published_at=NOW,
            retrieved_at=NOW,
            language="en",
            synthetic=True,
        ),
    )


def sample_stress_result() -> StressResult:
    settings = Settings(data_dir=Path("data"))
    result = build_stress_engine(settings).run(sample_signal()).result
    assert result is not None
    return result
