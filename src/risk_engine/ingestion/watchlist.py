"""Build explicit live-source queries from the configured issuer watchlist."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from risk_engine.nlp.entity import _Watchlist


class WatchlistQueryError(ValueError):
    """Raised when the live query watchlist cannot be loaded safely."""


def build_watchlist_query(path: Path) -> str:
    """Return a bounded OR query containing every configured issuer identifier."""

    try:
        watchlist = _Watchlist.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise WatchlistQueryError(f"Unable to load issuer watchlist: {path}") from error
    if not watchlist.synthetic or watchlist.schema_version != "1.0":
        raise WatchlistQueryError("Live query watchlist must be synthetic schema 1.0 data")
    values: list[str] = []
    for issuer in watchlist.entities:
        for value in (issuer.name, issuer.ticker, *issuer.aliases):
            if value not in values:
                values.append(value)
    query = " OR ".join(f'"{value}"' for value in values)
    if not query or len(query) > 500:
        raise WatchlistQueryError("Issuer watchlist query must contain 1 to 500 characters")
    return query
