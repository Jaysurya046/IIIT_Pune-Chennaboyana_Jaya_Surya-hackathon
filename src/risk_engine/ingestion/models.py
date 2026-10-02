"""Strict data contracts shared by all ingestion sources."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
)


class SourceType(StrEnum):
    """Supported categories of unstructured text source."""

    NEWS = "news"
    SOCIAL = "social"


class StrictModel(BaseModel):
    """Base contract that rejects undocumented fields."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class IngestionRequest(StrictModel):
    """A bounded search request that can be applied to every adapter."""

    query: Annotated[str, Field(min_length=1, max_length=500)]
    limit: Annotated[int, Field(ge=1, le=100)] = 25
    lookback_hours: Annotated[int, Field(ge=1, le=2_160)] = 24
    since: AwareDatetime | None = None


class SourceRecord(StrictModel):
    """Validated source output before canonical normalization."""

    source: Annotated[str, Field(min_length=1, max_length=50)]
    source_type: SourceType
    source_id: Annotated[str, Field(min_length=1, max_length=2_048)]
    title: Annotated[str, Field(max_length=2_000)] | None = None
    text: Annotated[str, Field(min_length=1, max_length=100_000)]
    url: Annotated[str, Field(min_length=1, max_length=4_096)]
    published_at: AwareDatetime
    retrieved_at: AwareDatetime
    author: Annotated[str, Field(max_length=500)] | None = None
    language: Annotated[str, Field(min_length=2, max_length=35)] = "und"
    query: Annotated[str, Field(min_length=1, max_length=500)]
    synthetic: bool = False
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def validate_web_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        return value


class Provenance(StrictModel):
    """Traceability fields retained for every normalized document."""

    source: str
    source_type: SourceType
    source_id: str
    original_url: str
    query: str
    published_at: AwareDatetime
    retrieved_at: AwareDatetime
    author: str | None = None
    language: str
    synthetic: bool
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class RawDocument(StrictModel):
    """Canonical document passed to downstream NLP components."""

    document_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    title: str | None = None
    text: Annotated[str, Field(min_length=1)]
    canonical_url: str
    content_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    normalized_at: AwareDatetime
    provenance: Provenance


class SourceRunStatus(StrictModel):
    """Observable outcome for one source in an ingestion run."""

    source: str
    source_type: SourceType
    successful: bool
    fetched_count: int = 0
    normalized_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    error: str | None = None
    started_at: AwareDatetime
    completed_at: AwareDatetime


class IngestionResult(StrictModel):
    """Documents and per-source outcomes from one isolated run."""

    query: str
    started_at: AwareDatetime
    completed_at: AwareDatetime
    documents: tuple[RawDocument, ...]
    sources: tuple[SourceRunStatus, ...]

    @property
    def successful_source_count(self) -> int:
        return sum(status.successful for status in self.sources)

    @property
    def failed_source_count(self) -> int:
        return len(self.sources) - self.successful_source_count


def ensure_utc(value: datetime) -> datetime:
    """Return an aware datetime normalized to UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include a timezone")
    return value.astimezone(UTC)
