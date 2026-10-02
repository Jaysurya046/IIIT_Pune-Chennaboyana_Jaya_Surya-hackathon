"""Live and fixture-backed ingestion adapters."""

from risk_engine.ingestion.adapters.bluesky import BlueskyAdapter
from risk_engine.ingestion.adapters.fixture import FixtureAdapter
from risk_engine.ingestion.adapters.gdelt import GdeltAdapter

__all__ = ["BlueskyAdapter", "FixtureAdapter", "GdeltAdapter"]
