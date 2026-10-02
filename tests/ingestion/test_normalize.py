"""Tests for canonical normalization and duplicate handling."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from risk_engine.ingestion.models import SourceRecord, SourceType
from risk_engine.ingestion.normalize import (
    NormalizationError,
    deduplicate_documents,
    normalize_record,
)

FIXED_TIME = datetime(2026, 10, 2, 10, 0, tzinfo=UTC)


def make_record(*, source: str = "gdelt", source_id: str = "one") -> SourceRecord:
    return SourceRecord(
        source=source,
        source_type=SourceType.NEWS if source == "gdelt" else SourceType.SOCIAL,
        source_id=source_id,
        title="  Risk\u00a0headline  ",
        text="  Risk\u00a0headline\nwith   spaces  ",
        url="HTTPS://Example.COM:443/story?utm_source=test&b=2&a=1#section",
        published_at=FIXED_TIME,
        retrieved_at=FIXED_TIME,
        query=" risk ",
        language="English",
    )


def test_normalize_record_canonicalizes_text_url_and_provenance() -> None:
    document = normalize_record(make_record(), max_text_length=1_000, clock=lambda: FIXED_TIME)

    assert document.title == "Risk headline"
    assert document.text == "Risk headline with spaces"
    assert document.canonical_url == "https://example.com/story?a=1&b=2"
    assert document.provenance.query == "risk"
    assert document.provenance.language == "en"
    assert document.normalized_at == FIXED_TIME


def test_normalize_record_rejects_oversized_text() -> None:
    with pytest.raises(NormalizationError, match="maximum length"):
        normalize_record(make_record(), max_text_length=5)


def test_deduplication_is_within_source_not_across_sources() -> None:
    gdelt_one = normalize_record(
        make_record(source="gdelt", source_id="one"),
        max_text_length=1_000,
        clock=lambda: FIXED_TIME,
    )
    gdelt_duplicate = normalize_record(
        make_record(source="gdelt", source_id="two"),
        max_text_length=1_000,
        clock=lambda: FIXED_TIME,
    )
    bluesky_same_text = normalize_record(
        make_record(source="bluesky", source_id="three"),
        max_text_length=1_000,
        clock=lambda: FIXED_TIME,
    )

    unique, duplicate_count = deduplicate_documents(
        [gdelt_one, gdelt_duplicate, bluesky_same_text]
    )

    assert duplicate_count == 1
    assert len(unique) == 2
    assert {document.provenance.source for document in unique} == {"gdelt", "bluesky"}
