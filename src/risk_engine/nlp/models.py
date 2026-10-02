"""Strict contracts for explainable NLP risk signals."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, Field

from risk_engine.ingestion.models import Provenance, StrictModel

UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]


class EventType(StrEnum):
    """Financial event categories supported by the versioned taxonomy."""

    GEOPOLITICAL = "Geopolitical"
    MACROECONOMIC = "Macroeconomic"
    CREDIT_EVENT = "Credit Event"
    MERGER_ACQUISITION = "Merger or Acquisition"
    PRODUCT_LAUNCH = "Product Launch"
    REGULATORY = "Regulatory"
    OPERATIONAL = "Operational"
    OTHER = "Other"


class SentimentLabel(StrEnum):
    """Normalized sentiment labels shared by every analyzer."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class EntityMatch(StrictModel):
    """A transparent match to one versioned issuer record."""

    entity_id: str
    name: str
    ticker: str
    sector: str
    country: str
    matched_alias: str
    match_type: str
    confidence: UnitInterval


class SentimentResult(StrictModel):
    """Normalized model output with a signed financial sentiment score."""

    label: SentimentLabel
    score: Annotated[float, Field(ge=-1.0, le=1.0)]
    confidence: UnitInterval
    probabilities: dict[SentimentLabel, UnitInterval]


class EventClassification(StrictModel):
    """Event prediction with semantic and lexical evidence retained."""

    event_type: EventType
    confidence: UnitInterval
    semantic_score: UnitInterval
    keyword_score: UnitInterval
    evidence: tuple[str, ...] = ()


class ImpactFactors(StrictModel):
    """Normalized components used by the documented impact formula."""

    event_severity_prior: UnitInterval
    absolute_sentiment: UnitInterval
    event_confidence: UnitInterval
    entity_relevance: UnitInterval
    cross_source_corroboration: UnitInterval
    recency: UnitInterval


class RiskSignal(StrictModel):
    """Auditable NLP result linked to its source document and model versions."""

    signal_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    document_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    canonical_url: str
    entities: tuple[EntityMatch, ...]
    sentiment: SentimentResult
    event: EventClassification
    impact_score: Annotated[int, Field(ge=1, le=10)]
    impact_factors: ImpactFactors
    rationale: tuple[str, ...]
    model_versions: dict[str, str]
    created_at: AwareDatetime
    provenance: Provenance
