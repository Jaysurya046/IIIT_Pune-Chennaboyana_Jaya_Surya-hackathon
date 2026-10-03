"""Orchestration for explainable document-to-risk-signal analysis."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from risk_engine.ingestion.models import RawDocument, ensure_utc
from risk_engine.ingestion.time import utc_now
from risk_engine.nlp.entity import IssuerResolver
from risk_engine.nlp.events import EventClassifier
from risk_engine.nlp.impact import ImpactScorer
from risk_engine.nlp.models import EntityMatch, EventClassification, RiskSignal, SentimentResult
from risk_engine.nlp.sentiment import SentimentAnalyzer


@dataclass(frozen=True, slots=True)
class _AnalyzedDocument:
    document: RawDocument
    entities: tuple[EntityMatch, ...]
    sentiment: SentimentResult
    event: EventClassification


class RiskSignalEngine:
    """Analyze a batch in two passes so corroboration stays deterministic."""

    def __init__(
        self,
        resolver: IssuerResolver,
        sentiment_analyzer: SentimentAnalyzer,
        event_classifier: EventClassifier,
        impact_scorer: ImpactScorer | None = None,
        *,
        clock: Callable[[], datetime] = utc_now,
        corroboration_window: timedelta = timedelta(hours=6),
    ) -> None:
        self._resolver = resolver
        self._sentiment = sentiment_analyzer
        self._events = event_classifier
        self._impact = impact_scorer or ImpactScorer()
        self._clock = clock
        self._corroboration_window = corroboration_window

    @staticmethod
    def _entity_ids(item: _AnalyzedDocument) -> set[str]:
        return {entity.entity_id for entity in item.entities}

    def _corroboration(
        self, target: _AnalyzedDocument, batch: tuple[_AnalyzedDocument, ...]
    ) -> float:
        target_entities = self._entity_ids(target)
        sources = {target.document.provenance.source}
        for candidate in batch:
            if candidate.document.document_id == target.document.document_id:
                continue
            if candidate.event.event_type is not target.event.event_type:
                continue
            if target_entities and not target_entities.intersection(self._entity_ids(candidate)):
                continue
            time_gap = abs(
                candidate.document.provenance.published_at - target.document.provenance.published_at
            )
            if time_gap <= self._corroboration_window:
                sources.add(candidate.document.provenance.source)
        return min(1.0, max(0.0, (len(sources) - 1) / 2))

    def analyze(
        self,
        documents: Iterable[RawDocument],
        *,
        as_of: datetime | None = None,
    ) -> tuple[RiskSignal, ...]:
        """Analyze documents at one explicit, timezone-aware point in time."""

        analyzed: list[_AnalyzedDocument] = []
        for document in documents:
            text = " ".join(part for part in (document.title, document.text) if part)
            analyzed.append(
                _AnalyzedDocument(
                    document=document,
                    entities=self._resolver.resolve(text),
                    sentiment=self._sentiment.analyze(text),
                    event=self._events.classify(text),
                )
            )

        batch = tuple(analyzed)
        created_at = ensure_utc(as_of if as_of is not None else self._clock())
        signals: list[RiskSignal] = []
        versions = {
            "entity_resolution": self._resolver.model_version,
            "sentiment": self._sentiment.model_version,
            "event_classification": self._events.model_version,
            "impact_scoring": self._impact.model_version,
        }
        for item in batch:
            corroboration = self._corroboration(item, batch)
            entity_relevance = max((entity.confidence for entity in item.entities), default=0.3)
            score, factors = self._impact.score(
                event=item.event,
                sentiment=item.sentiment,
                event_severity_prior=self._events.severity_prior(item.event.event_type),
                entity_relevance=entity_relevance,
                cross_source_corroboration=corroboration,
                recency=self._impact.recency(item.document.provenance.published_at, created_at),
            )
            evidence = (
                ", ".join(item.event.evidence)
                if item.event.evidence
                else "semantic or fallback classification"
            )
            rationale = (
                f"Classified as {item.event.event_type} with evidence: {evidence}.",
                f"Signed sentiment {item.sentiment.score:+.3f} ({item.sentiment.label}).",
                "Impact score uses documented weighted factors retained in impact_factors.",
            )
            identity = f"{item.document.document_id}|{item.event.event_type}|{versions}"
            signals.append(
                RiskSignal(
                    signal_id=hashlib.sha256(identity.encode()).hexdigest()[:32],
                    document_id=item.document.document_id,
                    canonical_url=item.document.canonical_url,
                    entities=item.entities,
                    sentiment=item.sentiment,
                    event=item.event,
                    impact_score=score,
                    impact_factors=factors,
                    rationale=rationale,
                    model_versions=versions,
                    created_at=created_at,
                    provenance=item.document.provenance,
                )
            )
        return tuple(signals)
