"""Versioned HTTP request and response contracts."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from risk_engine.ingestion.models import SourceRunStatus, StrictModel
from risk_engine.nlp.models import RiskSignal
from risk_engine.stress.models import HypotheticalStressAssumptions, StressDecision

Identifier = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]


class SourceMode(StrEnum):
    """Explicit source selection with no fallback between data modes."""

    FIXTURES = "fixtures"
    REPLAY = "replay"
    LIVE = "live"


class HealthResponse(StrictModel):
    status: Literal["ok"]
    application: str
    version: str
    database: Literal["ok"]
    offline_mode: bool


class IngestionRunRequest(StrictModel):
    query: Annotated[str, Field(min_length=1, max_length=500)]
    limit: Annotated[int, Field(ge=1, le=100)] = 25
    lookback_hours: Annotated[int, Field(ge=1, le=2_160)] = 24
    since: AwareDatetime | None = None
    source_mode: SourceMode = SourceMode.FIXTURES


class IngestionRunResponse(StrictModel):
    run_id: Identifier
    query: str
    document_count: int
    successful_source_count: int
    failed_source_count: int
    sources: tuple[SourceRunStatus, ...]


class AnalysisRequest(StrictModel):
    run_id: Identifier
    nlp_mode: Literal["deterministic", "model"] | None = None


class AnalysisResponse(StrictModel):
    run_id: Identifier
    signal_count: int
    signals: tuple[RiskSignal, ...]


class SourceStatusResponse(StrictModel):
    latest_run_id: Identifier | None = None
    query: str | None = None
    completed_at: AwareDatetime | None = None
    sources: tuple[SourceRunStatus, ...] = ()


class SignalListResponse(StrictModel):
    total: int
    limit: int
    offset: int
    items: tuple[RiskSignal, ...]


class StressTestRequest(StrictModel):
    signal_id: Identifier


class StressTestResponse(StrictModel):
    decision_id: Identifier
    decision: StressDecision


class WhatIfStressRequest(HypotheticalStressAssumptions):
    """Strict request contract for a non-persisted hypothetical stress run."""


class WhatIfStressResponse(StrictModel):
    hypothetical: Literal[True] = True
    assumptions: HypotheticalStressAssumptions
    decision: StressDecision


class PortfolioBreakdown(StrictModel):
    key: str
    position_count: int
    market_value: Decimal


class PortfolioSummaryResponse(StrictModel):
    portfolio_id: str
    portfolio_version: str
    base_currency: str
    position_count: int
    total_market_value: Decimal
    base_expected_loss: Decimal
    by_asset_class: tuple[PortfolioBreakdown, ...]
    by_sector: tuple[PortfolioBreakdown, ...]
    by_issuer: tuple[PortfolioBreakdown, ...]
