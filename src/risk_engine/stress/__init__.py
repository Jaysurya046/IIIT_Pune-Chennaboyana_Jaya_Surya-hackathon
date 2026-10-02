"""Configuration-driven synthetic portfolio stress testing."""

from risk_engine.stress.engine import ReconciliationError, StressEngine
from risk_engine.stress.factory import build_stress_engine
from risk_engine.stress.models import (
    AssetClass,
    InstrumentStressResult,
    Portfolio,
    Scenario,
    ScenarioBook,
    ScenarioScope,
    StressDecision,
    StressResult,
)

__all__ = [
    "AssetClass",
    "InstrumentStressResult",
    "Portfolio",
    "ReconciliationError",
    "Scenario",
    "ScenarioBook",
    "ScenarioScope",
    "StressDecision",
    "StressEngine",
    "StressResult",
    "build_stress_engine",
]
