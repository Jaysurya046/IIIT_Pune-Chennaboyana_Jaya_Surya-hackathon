"""End-to-end risk-signal engine tests."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from risk_engine.ingestion.adapters import FixtureAdapter
from risk_engine.ingestion.models import IngestionRequest
from risk_engine.ingestion.service import IngestionService
from risk_engine.nlp.engine import RiskSignalEngine
from risk_engine.nlp.entity import IssuerResolver
from risk_engine.nlp.events import KeywordEventClassifier
from risk_engine.nlp.factory import synthetic_batch_as_of
from risk_engine.nlp.models import EventType
from risk_engine.nlp.sentiment import RuleBasedSentimentAnalyzer


class RecordingSentimentAnalyzer(RuleBasedSentimentAnalyzer):
    def __init__(self) -> None:
        self.batches: list[tuple[str, ...]] = []

    def analyze_batch(self, texts):
        self.batches.append(tuple(texts))
        return super().analyze_batch(texts)


def _engine(clock_time: datetime = datetime(2026, 10, 1, tzinfo=UTC)) -> RiskSignalEngine:
    return RiskSignalEngine(
        IssuerResolver(Path("data/nlp/issuer_watchlist.json")),
        RuleBasedSentimentAnalyzer(),
        KeywordEventClassifier(Path("data/nlp/event_taxonomy.json")),
        clock=lambda: clock_time,
    )


def test_engine_preserves_provenance_and_cross_source_corroboration() -> None:
    sample_dir = Path("data/sample")
    result = IngestionService(
        [
            FixtureAdapter(sample_dir / "gdelt_articles.json"),
            FixtureAdapter(sample_dir / "bluesky_posts.json"),
        ],
        clock=lambda: datetime(2026, 10, 1, tzinfo=UTC),
    ).run(IngestionRequest(query="portfolio risk"))

    signals = _engine().analyze(result.documents)
    corroborated_macro = [
        signal
        for signal in signals
        if signal.event.event_type is EventType.MACROECONOMIC
    ]

    assert len(signals) == 6
    assert len(corroborated_macro) == 2
    assert all(
        signal.impact_factors.cross_source_corroboration == 0.5
        for signal in corroborated_macro
    )
    assert all(signal.provenance.synthetic for signal in signals)
    assert all(signal.rationale and signal.model_versions for signal in signals)


def test_signal_ids_are_stable_for_the_same_inputs() -> None:
    sample = Path("data/sample/gdelt_articles.json")
    result = IngestionService(
        [FixtureAdapter(sample)],
        clock=lambda: datetime(2026, 10, 1, tzinfo=UTC),
    ).run(IngestionRequest(query="risk", limit=1))

    first = _engine().analyze(result.documents)[0]
    second = _engine().analyze(result.documents)[0]

    assert first.signal_id == second.signal_id
    assert first.document_id == second.document_id


def test_explicit_as_of_makes_scores_identical_across_wall_clocks() -> None:
    result = IngestionService(
        [FixtureAdapter(Path("data/sample/gdelt_articles.json"))],
        clock=lambda: datetime(2026, 10, 1, tzinfo=UTC),
    ).run(IngestionRequest(query="risk"))
    as_of = synthetic_batch_as_of(result.documents)

    first = _engine(datetime(2027, 1, 1, tzinfo=UTC)).analyze(
        result.documents,
        as_of=as_of,
    )
    second = _engine(datetime(2037, 1, 1, tzinfo=UTC)).analyze(
        result.documents,
        as_of=as_of,
    )

    assert first == second
    assert as_of == datetime(2026, 10, 1, tzinfo=UTC)
    assert all(signal.created_at == as_of for signal in first)


def test_analysis_rejects_naive_as_of_time() -> None:
    result = IngestionService(
        [FixtureAdapter(Path("data/sample/gdelt_articles.json"))]
    ).run(IngestionRequest(query="risk", limit=1))

    with pytest.raises(ValueError, match="datetime must include a timezone"):
        _engine().analyze(result.documents, as_of=datetime(2026, 10, 1))


def test_live_provenance_uses_engine_clock_and_is_rejected_by_synthetic_policy() -> None:
    result = IngestionService(
        [FixtureAdapter(Path("data/sample/gdelt_articles.json"))]
    ).run(IngestionRequest(query="risk", limit=1))
    document = result.documents[0]
    live_document = document.model_copy(
        update={
            "provenance": document.provenance.model_copy(update={"synthetic": False})
        }
    )
    live_time = datetime(2030, 6, 1, tzinfo=UTC)

    signal = _engine(live_time).analyze((live_document,))[0]

    assert signal.created_at == live_time
    with pytest.raises(ValueError, match="non-synthetic provenance"):
        synthetic_batch_as_of((live_document,))


def test_engine_batches_sentiment_once_and_preserves_document_order() -> None:
    result = IngestionService(
        [FixtureAdapter(Path("data/sample/gdelt_articles.json"))]
    ).run(IngestionRequest(query="risk"))
    sentiment = RecordingSentimentAnalyzer()
    engine = RiskSignalEngine(
        IssuerResolver(Path("data/nlp/issuer_watchlist.json")),
        sentiment,
        KeywordEventClassifier(Path("data/nlp/event_taxonomy.json")),
    )

    signals = engine.analyze(result.documents)

    assert len(sentiment.batches) == 1
    assert len(sentiment.batches[0]) == len(result.documents)
    assert [signal.document_id for signal in signals] == [
        document.document_id for document in result.documents
    ]
