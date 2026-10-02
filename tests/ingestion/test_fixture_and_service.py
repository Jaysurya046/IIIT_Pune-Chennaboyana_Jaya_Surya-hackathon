"""Tests for deterministic fixtures and failure-isolated orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from risk_engine.ingestion.adapters.base import SourceAdapterError
from risk_engine.ingestion.adapters.fixture import FixtureAdapter
from risk_engine.ingestion.models import IngestionRequest, SourceRecord, SourceType
from risk_engine.ingestion.service import IngestionService

FIXED_TIME = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


class FailingAdapter:
    name = "unavailable-source"
    source_type = SourceType.NEWS

    def fetch(self, request: IngestionRequest) -> list[SourceRecord]:
        del request
        raise SourceAdapterError("service unavailable")


def test_fixture_adapter_marks_every_record_synthetic() -> None:
    adapter = FixtureAdapter(Path("data/sample/gdelt_articles.json"))

    records = adapter.fetch(IngestionRequest(query="risk", limit=2))

    assert len(records) == 2
    assert all(record.synthetic for record in records)
    assert all(record.query == "risk" for record in records)


def test_service_continues_after_one_source_fails() -> None:
    fixture = FixtureAdapter(Path("data/sample/bluesky_posts.json"))
    service = IngestionService(
        [FailingAdapter(), fixture],
        clock=lambda: FIXED_TIME,
    )

    result = service.run(IngestionRequest(query="rates"))

    assert result.failed_source_count == 1
    assert result.successful_source_count == 1
    assert len(result.documents) == 3
    failed, successful = result.sources
    assert failed.successful is False
    assert "service unavailable" in (failed.error or "")
    assert successful.successful is True
    assert successful.normalized_count == 3
