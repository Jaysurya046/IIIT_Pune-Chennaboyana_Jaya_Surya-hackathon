"""Synthetic portfolio and scenario configuration tests."""

from pathlib import Path

from risk_engine.nlp.models import EventType
from risk_engine.stress.config import load_portfolio, load_scenario_book
from risk_engine.stress.models import AssetClass


def test_synthetic_portfolio_covers_all_asset_classes() -> None:
    portfolio = load_portfolio(Path("data/portfolio/portfolio.json"))

    assert portfolio.synthetic is True
    assert len(portfolio.positions) == 8
    assert {position.asset_class for position in portfolio.positions} == set(AssetClass)
    assert {position.issuer_id for position in portfolio.positions} == {
        "northstar-energy",
        "aurora-bank",
        "meridian-shipping",
        "atlas-manufacturing",
    }


def test_scenario_book_maps_every_event_once() -> None:
    book = load_scenario_book(Path("data/portfolio/scenarios.json"))

    assert book.synthetic is True
    assert len(book.scenarios) == len(EventType)
    assert {scenario.event_type for scenario in book.scenarios} == set(EventType)
    assert book.for_event(EventType.CREDIT_EVENT).scenario_id == "issuer-credit-event"
