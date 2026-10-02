"""Canonical text, URL, identifier, and duplicate handling."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable, Iterable
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from risk_engine.ingestion.models import Provenance, RawDocument, SourceRecord
from risk_engine.ingestion.time import utc_now

_WHITESPACE = re.compile(r"\s+")
_TRACKING_PARAMETERS = frozenset(
    {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "source",
    }
)
_LANGUAGE_CODES = {
    "arabic": "ar",
    "chinese": "zh",
    "english": "en",
    "french": "fr",
    "german": "de",
    "hindi": "hi",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "portuguese": "pt",
    "russian": "ru",
    "spanish": "es",
}


class NormalizationError(ValueError):
    """A source record cannot safely enter the downstream pipeline."""


def normalize_text(value: str) -> str:
    """Normalize Unicode and collapse all whitespace to single spaces."""

    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip()


def canonicalize_url(value: str) -> str:
    """Remove fragments and common tracking parameters from a web URL."""

    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    port = parts.port
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"

    query_items = [
        (key, item_value)
        for key, item_value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMETERS
    ]
    normalized_path = parts.path or "/"
    return urlunsplit(
        (scheme, hostname, normalized_path, urlencode(sorted(query_items)), "")
    )


def normalize_language(value: str) -> str:
    """Normalize common source language names while retaining unknown BCP-47 tags."""

    language = value.strip().lower().replace("_", "-")
    return _LANGUAGE_CODES.get(language, language)


def normalize_record(
    record: SourceRecord,
    *,
    max_text_length: int,
    clock: Callable[[], datetime] = utc_now,
) -> RawDocument:
    """Convert one validated source record into the canonical document contract."""

    text = normalize_text(record.text)
    if not text:
        raise NormalizationError("record text is empty after normalization")
    if len(text) > max_text_length:
        raise NormalizationError(
            f"record text exceeds maximum length of {max_text_length} characters"
        )

    title = normalize_text(record.title) if record.title else None
    canonical_url = canonicalize_url(record.url)
    document_id = hashlib.sha256(
        f"{record.source}\0{record.source_id}".encode()
    ).hexdigest()[:32]
    content_hash = hashlib.sha256(text.encode()).hexdigest()

    return RawDocument(
        document_id=document_id,
        title=title,
        text=text,
        canonical_url=canonical_url,
        content_hash=content_hash,
        normalized_at=clock(),
        provenance=Provenance(
            source=record.source.lower(),
            source_type=record.source_type,
            source_id=record.source_id,
            original_url=record.url,
            query=normalize_text(record.query),
            published_at=record.published_at,
            retrieved_at=record.retrieved_at,
            author=normalize_text(record.author) if record.author else None,
            language=normalize_language(record.language),
            synthetic=record.synthetic,
            metadata=record.metadata,
        ),
    )


def deduplicate_documents(
    documents: Iterable[RawDocument],
) -> tuple[list[RawDocument], int]:
    """Remove duplicates within a source while preserving cross-source evidence."""

    unique: list[RawDocument] = []
    seen_ids: set[tuple[str, str]] = set()
    seen_urls: set[tuple[str, str]] = set()
    seen_content: set[tuple[str, str]] = set()
    duplicate_count = 0

    for document in documents:
        source = document.provenance.source
        id_key = (source, document.provenance.source_id)
        url_key = (source, document.canonical_url)
        content_key = (source, document.content_hash)
        if id_key in seen_ids or url_key in seen_urls or content_key in seen_content:
            duplicate_count += 1
            continue

        seen_ids.add(id_key)
        seen_urls.add(url_key)
        seen_content.add(content_key)
        unique.append(document)

    return unique, duplicate_count
