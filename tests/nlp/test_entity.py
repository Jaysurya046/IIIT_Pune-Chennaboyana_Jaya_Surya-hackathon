"""Issuer resolution tests."""

from pathlib import Path

from risk_engine.nlp.entity import IssuerResolver


def test_resolver_matches_names_tickers_and_deduplicates() -> None:
    resolver = IssuerResolver(Path("data/nlp/issuer_watchlist.json"))

    matches = resolver.resolve("Northstar Energy (NSEY) and Aurora are being reviewed.")

    assert [match.entity_id for match in matches] == ["northstar-energy", "aurora-bank"]
    assert matches[0].matched_alias == "Northstar Energy"
    assert matches[0].confidence == 1.0


def test_resolver_uses_whole_tokens() -> None:
    resolver = IssuerResolver(Path("data/nlp/issuer_watchlist.json"))

    assert resolver.resolve("An atlaslike pattern is not an issuer.") == ()
