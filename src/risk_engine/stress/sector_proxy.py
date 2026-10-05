"""Explicit illustrative mappings from real issuer sectors to synthetic sectors."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field, ValidationError

from risk_engine.ingestion.models import StrictModel


class SectorProxyConfigurationError(ValueError):
    """Raised when the versioned sector-proxy book is invalid."""


class SectorProxyMapping(StrictModel):
    proxy_id: str = Field(min_length=1)
    source_sector: str = Field(min_length=1)
    source_aliases: tuple[str, ...] = Field(min_length=1)
    synthetic_sector: str = Field(min_length=1)
    label: str = "illustrative sector proxy"


class SectorProxyBook(StrictModel):
    schema_version: str
    version: str
    synthetic: bool
    description: str
    mappings: tuple[SectorProxyMapping, ...] = Field(min_length=1)


class SectorProxyMatch(StrictModel):
    source_sector: str
    synthetic_sector: str
    proxy_id: str
    label: str = "illustrative sector proxy"


def load_sector_proxy_book(path: Path) -> SectorProxyBook:
    try:
        book = SectorProxyBook.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise SectorProxyConfigurationError(f"Unable to load sector proxy book: {path}") from error
    if book.schema_version != "1.0" or not book.synthetic:
        raise SectorProxyConfigurationError("Sector proxy book must be synthetic schema 1.0 data")
    ids = [mapping.proxy_id for mapping in book.mappings]
    if len(ids) != len(set(ids)):
        raise SectorProxyConfigurationError("Sector proxy IDs must be unique")
    return book


class SectorProxyResolver:
    """Resolve broad sectors while preserving the illustrative-only boundary."""

    def __init__(self, path: Path) -> None:
        self._book = load_sector_proxy_book(path)
        self.version = self._book.version

    def resolve(self, source_sector: str) -> SectorProxyMatch | None:
        normalized = source_sector.strip().casefold()
        for mapping in self._book.mappings:
            candidates = (mapping.source_sector, *mapping.source_aliases)
            if normalized in {candidate.casefold() for candidate in candidates}:
                return SectorProxyMatch(
                    source_sector=source_sector,
                    synthetic_sector=mapping.synthetic_sector,
                    proxy_id=mapping.proxy_id,
                    label=mapping.label,
                )
        return None

    def resolve_many(self, sectors: tuple[str, ...]) -> tuple[SectorProxyMatch, ...]:
        matches: list[SectorProxyMatch] = []
        seen: set[str] = set()
        for sector in sectors:
            match = self.resolve(sector)
            if match is not None and match.proxy_id not in seen:
                matches.append(match)
                seen.add(match.proxy_id)
        return tuple(matches)
