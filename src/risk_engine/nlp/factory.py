"""Construct an NLP engine from validated application settings."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from risk_engine.config import Settings
from risk_engine.ingestion.models import RawDocument
from risk_engine.nlp.engine import RiskSignalEngine
from risk_engine.nlp.entity import IssuerResolver
from risk_engine.nlp.events import EmbeddingEventClassifier, KeywordEventClassifier
from risk_engine.nlp.sentiment import (
    FinBertSentimentAnalyzer,
    RuleBasedSentimentAnalyzer,
    SentimentAnalyzer,
)


def synthetic_batch_as_of(documents: Sequence[RawDocument]) -> datetime | None:
    """Return the latest retrieval time for an explicitly synthetic batch.

    An empty batch has no analysis time. Mixed or live provenance is rejected so a
    fixture/replay caller cannot silently switch to wall-clock scoring.
    """

    if not documents:
        return None
    if any(not document.provenance.synthetic for document in documents):
        raise ValueError("synthetic batch contains non-synthetic provenance")
    return max(document.provenance.retrieved_at for document in documents)


def build_sentiment_analyzer(settings: Settings, *, mode: str) -> SentimentAnalyzer:
    """Build one explicitly selected sentiment implementation without fallback."""

    if mode not in settings.ALLOWED_NLP_MODES:
        allowed = ", ".join(sorted(settings.ALLOWED_NLP_MODES))
        raise ValueError(f"NLP mode must be one of: {allowed}")
    if mode == "model":
        return FinBertSentimentAnalyzer(
            settings.sentiment_model_id,
            settings.sentiment_model_revision,
            cache_dir=str(settings.model_cache_dir),
        )
    return RuleBasedSentimentAnalyzer()


def build_risk_engine(settings: Settings, *, mode: str | None = None) -> RiskSignalEngine:
    """Build an explicit deterministic or model-backed analysis pipeline."""

    selected_mode = mode or settings.nlp_mode
    if selected_mode not in settings.ALLOWED_NLP_MODES:
        allowed = ", ".join(sorted(settings.ALLOWED_NLP_MODES))
        raise ValueError(f"NLP mode must be one of: {allowed}")

    nlp_dir = settings.data_dir / "nlp"
    resolver = IssuerResolver(nlp_dir / "issuer_watchlist.json")
    taxonomy = nlp_dir / "event_taxonomy.json"
    sentiment = build_sentiment_analyzer(settings, mode=selected_mode)
    if selected_mode == "model":
        events = EmbeddingEventClassifier(
            taxonomy,
            settings.event_model_id,
            settings.event_model_revision,
            cache_dir=str(settings.model_cache_dir),
        )
    else:
        sentiment = RuleBasedSentimentAnalyzer()
        events = KeywordEventClassifier(taxonomy)
    return RiskSignalEngine(resolver, sentiment, events)
