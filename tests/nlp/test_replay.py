"""Exact regression contract for the synthetic banking-stress replay."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from risk_engine.config import Settings
from risk_engine.ingestion.adapters import FixtureAdapter
from risk_engine.ingestion.models import IngestionRequest
from risk_engine.ingestion.service import IngestionService
from risk_engine.nlp.factory import build_risk_engine, synthetic_batch_as_of
from risk_engine.nlp.models import EventType, SentimentLabel

EXPECTED = {
    "https://banking-stress.example/news/aurora-funding-review": {
        "sentiment_score": -0.86,
        "evidence": ("default", "downgrade", "restructuring", "credit spread"),
        "recency": 0.9513888888888888,
    },
    "https://banking-stress.example/news/aurora-liquidity-plan": {
        "sentiment_score": -0.79,
        "evidence": (
            "default",
            "missed payment",
            "downgrade",
            "restructuring",
            "bond spread",
        ),
        "recency": 0.9618055555555556,
    },
    "replay://riskobserver.example/aurora-001": {
        "sentiment_score": -0.79,
        "evidence": ("default", "downgrade", "restructuring", "credit spread"),
        "recency": 0.9548611111111112,
    },
    "replay://marketdesk.example/aurora-002": {
        "sentiment_score": -0.86,
        "evidence": (
            "default",
            "missed payment",
            "bankruptcy",
            "downgrade",
            "bond spread",
        ),
        "recency": 0.9664351851851852,
    },
}


def _replay_signals():
    replay_dir = Path("data/replay")
    result = IngestionService(
        [
            FixtureAdapter(replay_dir / "banking_stress_news.json"),
            FixtureAdapter(replay_dir / "banking_stress_social.json"),
        ]
    ).run(IngestionRequest(query="banking stress"))
    signals = build_risk_engine(
        Settings(data_dir=Path("data")), mode="deterministic"
    ).analyze(result.documents, as_of=synthetic_batch_as_of(result.documents))
    return result, signals


def test_replay_has_exact_deterministic_signals_and_scores() -> None:
    result, signals = _replay_signals()

    assert len(result.documents) == len(signals) == 4
    assert {status.source for status in result.sources} == {
        "replay-news",
        "replay-social",
    }
    assert all(document.provenance.synthetic for document in result.documents)
    assert all(signal.impact_score == 9 for signal in signals)
    assert all(signal.created_at == datetime(2026, 10, 2, 12, tzinfo=UTC) for signal in signals)

    for signal in signals:
        expected = EXPECTED[signal.provenance.source_id]
        assert signal.event.event_type is EventType.CREDIT_EVENT
        assert signal.event.confidence == 0.98
        assert signal.event.evidence == expected["evidence"]
        assert signal.sentiment.label is SentimentLabel.NEGATIVE
        assert signal.sentiment.score == expected["sentiment_score"]
        assert [entity.entity_id for entity in signal.entities] == ["aurora-bank"]
        assert signal.impact_factors.model_dump() == {
            "event_severity_prior": 0.95,
            "absolute_sentiment": abs(expected["sentiment_score"]),
            "event_confidence": 0.98,
            "entity_relevance": 1.0,
            "cross_source_corroboration": 0.5,
            "recency": expected["recency"],
        }
