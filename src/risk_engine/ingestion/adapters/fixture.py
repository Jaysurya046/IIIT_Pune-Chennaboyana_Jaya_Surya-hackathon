"""Deterministic offline adapter for committed synthetic fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, ValidationError

from risk_engine.ingestion.adapters.base import SourceAdapterError
from risk_engine.ingestion.models import IngestionRequest, SourceRecord, SourceType


class _FixtureEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str
    title: str | None = None
    text: str
    url: str
    published_at: AwareDatetime
    retrieved_at: AwareDatetime
    author: str | None = None
    language: str = "und"
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class _FixtureBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: str
    source: str
    source_type: SourceType
    synthetic: bool
    description: str
    records: list[_FixtureEntry]


class FixtureAdapter:
    """Read a source-shaped fixture without silently pretending it is live data."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._bundle = self._read_bundle(path)
        if self._bundle.schema_version != "1.0":
            raise SourceAdapterError(f"Unsupported fixture schema: {self._bundle.schema_version}")
        if not self._bundle.synthetic:
            raise SourceAdapterError("Offline fixtures must be explicitly marked synthetic")
        self.name = self._bundle.source
        self.source_type = self._bundle.source_type

    @staticmethod
    def _read_bundle(path: Path) -> _FixtureBundle:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return _FixtureBundle.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            raise SourceAdapterError(
                f"Unable to read fixture {path.name}: {type(error).__name__}"
            ) from error

    def fetch(self, request: IngestionRequest) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for entry in self._bundle.records:
            if request.since is not None and entry.published_at < request.since:
                continue
            records.append(
                SourceRecord(
                    source=self.name,
                    source_type=self.source_type,
                    source_id=entry.source_id,
                    title=entry.title,
                    text=entry.text,
                    url=entry.url,
                    published_at=entry.published_at,
                    retrieved_at=entry.retrieved_at,
                    author=entry.author,
                    language=entry.language,
                    query=request.query,
                    synthetic=True,
                    metadata=entry.metadata,
                )
            )
            if len(records) >= request.limit:
                break
        return records
