"""End-to-end risk-signal engine tests."""

from datetime import UTC, datetime
from pathlib import Path

from risk_engine.ingestion.adapters import FixtureAdapter
from risk_engine.ingestion.models import IngestionRequest
from risk_engine.ingestion.service import IngestionService
from risk_engine.nlp.engine import RiskSignalEngine
from risk_engine.nlp.entity import IssuerResolver
from risk_engine.nlp.events import KeywordEventClassifier
from risk_engine.nlp.models import EventType
from risk_engine.nlp.sentiment import RuleBasedSentimentAnalyzer


def _engine() -> RiskSignalEngine:
    return RiskSignalEngine(
        IssuerResolver(Path("data/nlp/issuer_watchlist.json")),
        RuleBasedSentimentAnalyzer(),
        KeywordEventClassifier(Path("data/nlp/event_taxonomy.json")),
        clock=lambda: datetime(2026, 10, 1, tzinfo=UTC),
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
