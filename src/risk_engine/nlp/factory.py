"""Construct an NLP engine from validated application settings."""

from __future__ import annotations

from risk_engine.config import Settings
from risk_engine.nlp.engine import RiskSignalEngine
from risk_engine.nlp.entity import IssuerResolver
from risk_engine.nlp.events import EmbeddingEventClassifier, KeywordEventClassifier
from risk_engine.nlp.sentiment import FinBertSentimentAnalyzer, RuleBasedSentimentAnalyzer


def build_risk_engine(settings: Settings, *, mode: str | None = None) -> RiskSignalEngine:
    """Build an explicit deterministic or model-backed analysis pipeline."""

    selected_mode = mode or settings.nlp_mode
    if selected_mode not in settings.ALLOWED_NLP_MODES:
        allowed = ", ".join(sorted(settings.ALLOWED_NLP_MODES))
        raise ValueError(f"NLP mode must be one of: {allowed}")

    nlp_dir = settings.data_dir / "nlp"
    resolver = IssuerResolver(nlp_dir / "issuer_watchlist.json")
    taxonomy = nlp_dir / "event_taxonomy.json"
    if selected_mode == "model":
        sentiment = FinBertSentimentAnalyzer(
            settings.sentiment_model_id,
            settings.sentiment_model_revision,
            cache_dir=str(settings.model_cache_dir),
        )
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
