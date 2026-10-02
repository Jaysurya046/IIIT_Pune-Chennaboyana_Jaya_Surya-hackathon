"""Construct the configured portfolio stress engine."""

from __future__ import annotations

from risk_engine.config import Settings
from risk_engine.stress.config import load_portfolio, load_scenario_book
from risk_engine.stress.engine import StressEngine


def build_stress_engine(settings: Settings) -> StressEngine:
    """Load versioned synthetic configuration and return a ready engine."""

    portfolio_dir = settings.data_dir / "portfolio"
    return StressEngine(
        load_portfolio(portfolio_dir / "portfolio.json"),
        load_scenario_book(portfolio_dir / "scenarios.json"),
        trigger_threshold=settings.stress_trigger_threshold,
    )
