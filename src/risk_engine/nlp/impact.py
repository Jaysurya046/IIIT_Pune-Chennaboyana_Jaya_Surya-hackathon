"""Transparent weighted impact scoring."""

from __future__ import annotations

from datetime import datetime

from risk_engine.ingestion.models import ensure_utc
from risk_engine.nlp.models import (
    EventClassification,
    ImpactFactors,
    SentimentResult,
)


class ImpactScorer:
    """Apply the architecture's fixed weighted formula and retain every factor."""

    model_version = "impact-formula-v1"

    @staticmethod
    def recency(published_at: datetime, now: datetime) -> float:
        age_hours = max(0.0, (ensure_utc(now) - ensure_utc(published_at)).total_seconds() / 3600)
        return max(0.0, 1.0 - age_hours / 72.0)

    def score(
        self,
        *,
        event: EventClassification,
        sentiment: SentimentResult,
        event_severity_prior: float,
        entity_relevance: float,
        cross_source_corroboration: float,
        recency: float,
    ) -> tuple[int, ImpactFactors]:
        factors = ImpactFactors(
            event_severity_prior=event_severity_prior,
            absolute_sentiment=abs(sentiment.score),
            event_confidence=event.confidence,
            entity_relevance=entity_relevance,
            cross_source_corroboration=cross_source_corroboration,
            recency=recency,
        )
        weighted = 10 * (
            0.30 * factors.event_severity_prior
            + 0.20 * factors.absolute_sentiment
            + 0.20 * factors.event_confidence
            + 0.15 * factors.entity_relevance
            + 0.10 * factors.cross_source_corroboration
            + 0.05 * factors.recency
        )
        return max(1, min(10, int(weighted + 0.5))), factors
