from pathlib import Path

import pytest

from risk_engine.ingestion.watchlist import WatchlistQueryError, build_watchlist_query


def test_live_query_contains_each_configured_watchlist_identifier() -> None:
    query = build_watchlist_query(Path("data/nlp/issuer_watchlist.json"))

    assert '"Northstar Energy"' in query
    assert '"NSEY"' in query
    assert '"Aurora Bank"' in query
    assert " OR " in query
    assert len(query) <= 500


def test_live_query_rejects_missing_watchlist(tmp_path: Path) -> None:
    with pytest.raises(WatchlistQueryError, match="Unable to load issuer watchlist"):
        build_watchlist_query(tmp_path / "missing.json")
