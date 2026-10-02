"""Validated loaders for portfolio and scenario configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from risk_engine.stress.models import Portfolio, ScenarioBook


class StressConfigurationError(ValueError):
    """Raised when stress configuration cannot be read or validated."""


def load_portfolio(path: Path) -> Portfolio:
    try:
        return Portfolio.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise StressConfigurationError(f"Unable to load portfolio configuration: {path}") from error


def load_scenario_book(path: Path) -> ScenarioBook:
    try:
        return ScenarioBook.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise StressConfigurationError(f"Unable to load scenario configuration: {path}") from error
