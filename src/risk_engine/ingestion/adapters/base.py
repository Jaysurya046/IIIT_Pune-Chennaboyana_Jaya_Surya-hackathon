"""Common source-adapter interface and errors."""

from __future__ import annotations

from typing import Protocol

from risk_engine.ingestion.models import IngestionRequest, SourceRecord, SourceType


class SourceAdapterError(RuntimeError):
    """A safe, user-displayable source retrieval or parsing failure."""


class SourceAdapter(Protocol):
    """Contract implemented by live and offline text sources."""

    name: str
    source_type: SourceType

    def fetch(self, request: IngestionRequest) -> list[SourceRecord]:
        """Fetch and validate source records for one bounded request."""
        ...
