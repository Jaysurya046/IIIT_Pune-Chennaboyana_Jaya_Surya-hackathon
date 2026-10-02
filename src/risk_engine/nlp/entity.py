"""Versioned, explainable issuer resolution."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from risk_engine.nlp.models import EntityMatch


class EntityConfigurationError(ValueError):
    """Raised when the issuer watchlist cannot be validated."""


class _Issuer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    entity_id: str
    name: str
    ticker: str
    sector: str
    country: str
    aliases: list[str]


class _Watchlist(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    version: str
    synthetic: bool
    entities: list[_Issuer]


class IssuerResolver:
    """Resolve issuers through case-insensitive whole-token alias matching."""

    def __init__(self, path: Path) -> None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            watchlist = _Watchlist.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            raise EntityConfigurationError(f"Unable to load issuer watchlist: {path}") from error
        if watchlist.schema_version != "1.0" or not watchlist.synthetic:
            raise EntityConfigurationError("Issuer watchlist must be schema 1.0 synthetic data")
        self._watchlist = watchlist
        self.model_version = f"issuer-watchlist-{watchlist.version}"

    def resolve(self, text: str) -> tuple[EntityMatch, ...]:
        """Return one best (longest) transparent match per issuer."""

        matches: list[tuple[int, EntityMatch]] = []
        for issuer in self._watchlist.entities:
            candidates = [(issuer.name, "name"), (issuer.ticker, "ticker")]
            candidates.extend((alias, "alias") for alias in issuer.aliases)
            found: list[tuple[int, str, str]] = []
            for candidate, match_type in candidates:
                pattern = rf"(?<!\w){re.escape(candidate)}(?!\w)"
                if re.search(pattern, text, flags=re.IGNORECASE):
                    found.append((len(candidate), candidate, match_type))
            if not found:
                continue
            length, alias, match_type = max(found, key=lambda item: item[0])
            confidence = 1.0 if match_type in {"name", "ticker"} else 0.95
            matches.append(
                (
                    length,
                    EntityMatch(
                        entity_id=issuer.entity_id,
                        name=issuer.name,
                        ticker=issuer.ticker,
                        sector=issuer.sector,
                        country=issuer.country,
                        matched_alias=alias,
                        match_type=match_type,
                        confidence=confidence,
                    ),
                )
            )
        return tuple(
            match for _, match in sorted(matches, key=lambda item: (-item[0], item[1].entity_id))
        )
