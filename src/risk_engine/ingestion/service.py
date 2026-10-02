"""Failure-isolated ingestion orchestration."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from datetime import datetime

from risk_engine.ingestion.adapters.base import SourceAdapter
from risk_engine.ingestion.models import (
    IngestionRequest,
    IngestionResult,
    RawDocument,
    SourceRunStatus,
)
from risk_engine.ingestion.normalize import (
    NormalizationError,
    deduplicate_documents,
    normalize_record,
)
from risk_engine.ingestion.time import utc_now

LOGGER = logging.getLogger(__name__)


class IngestionService:
    """Run independent adapters and retain a status for every source."""

    def __init__(
        self,
        adapters: Iterable[SourceAdapter],
        *,
        max_text_length: int = 10_000,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._adapters = tuple(adapters)
        self._max_text_length = max_text_length
        self._clock = clock

    def run(self, request: IngestionRequest) -> IngestionResult:
        started_at = self._clock()
        documents: list[RawDocument] = []
        statuses: list[SourceRunStatus] = []

        for adapter in self._adapters:
            source_started_at = self._clock()
            try:
                records = adapter.fetch(request)
                normalized: list[RawDocument] = []
                rejected_count = 0
                for record in records:
                    try:
                        normalized.append(
                            normalize_record(
                                record,
                                max_text_length=self._max_text_length,
                                clock=self._clock,
                            )
                        )
                    except NormalizationError as error:
                        rejected_count += 1
                        LOGGER.warning(
                            "Rejected %s record %s: %s",
                            adapter.name,
                            record.source_id,
                            error,
                        )

                unique, duplicate_count = deduplicate_documents(normalized)
                documents.extend(unique)
                statuses.append(
                    SourceRunStatus(
                        source=adapter.name,
                        source_type=adapter.source_type,
                        successful=True,
                        fetched_count=len(records),
                        normalized_count=len(unique),
                        rejected_count=rejected_count,
                        duplicate_count=duplicate_count,
                        started_at=source_started_at,
                        completed_at=self._clock(),
                    )
                )
            except Exception as error:  # noqa: BLE001 - source isolation is intentional
                LOGGER.exception("Source %s failed", adapter.name)
                statuses.append(
                    SourceRunStatus(
                        source=adapter.name,
                        source_type=adapter.source_type,
                        successful=False,
                        error=f"{type(error).__name__}: {error}",
                        started_at=source_started_at,
                        completed_at=self._clock(),
                    )
                )

        return IngestionResult(
            query=request.query,
            started_at=started_at,
            completed_at=self._clock(),
            documents=tuple(documents),
            sources=tuple(statuses),
        )
