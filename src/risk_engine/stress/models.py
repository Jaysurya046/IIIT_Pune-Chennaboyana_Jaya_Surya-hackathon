"""Strict contracts for the synthetic portfolio stress engine."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from risk_engine.ingestion.models import StrictModel
from risk_engine.nlp.models import EventType

Money = Annotated[Decimal, Field(max_digits=20, decimal_places=2)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=2)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0)]
Probability = Annotated[Decimal, Field(ge=0, le=1)]
ShockFraction = Annotated[Decimal, Field(ge=-1, le=1)]
EntityIdentifier = Annotated[str, Field(min_length=1, max_length=100)]


class AssetClass(StrEnum):
    """Asset classes covered by the simplified stress models."""

    BOND = "bond"
    LOAN = "loan"
    EQUITY = "equity"
    DERIVATIVE = "derivative"


class ScenarioScope(StrEnum):
    """How a scenario selects positions from the portfolio."""

    PORTFOLIO = "portfolio"
    RESOLVED_ENTITIES = "resolved_entities"


class BasePosition(StrictModel):
    """Fields shared by every fictional portfolio position."""

    instrument_id: str
    issuer_id: str
    issuer_name: str
    sector: str
    currency: str
    market_value: NonNegativeMoney


class BondPosition(BasePosition):
    asset_class: Literal[AssetClass.BOND] = AssetClass.BOND
    duration_years: NonNegativeDecimal
    spread_duration_years: NonNegativeDecimal


class LoanPosition(BasePosition):
    asset_class: Literal[AssetClass.LOAN] = AssetClass.LOAN
    probability_of_default: Probability
    loss_given_default: Probability


class EquityPosition(BasePosition):
    asset_class: Literal[AssetClass.EQUITY] = AssetClass.EQUITY


class DerivativePosition(BasePosition):
    asset_class: Literal[AssetClass.DERIVATIVE] = AssetClass.DERIVATIVE
    delta_exposure: Money
    dv01: Money


Position = Annotated[
    BondPosition | LoanPosition | EquityPosition | DerivativePosition,
    Field(discriminator="asset_class"),
]


class Portfolio(StrictModel):
    """Versioned synthetic portfolio configuration."""

    schema_version: Literal["1.0"]
    portfolio_id: str
    version: str
    name: str
    base_currency: str
    synthetic: Literal[True]
    positions: tuple[Position, ...]

    @model_validator(mode="after")
    def unique_instrument_ids(self) -> Portfolio:
        identifiers = [position.instrument_id for position in self.positions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("portfolio instrument_id values must be unique")
        if not identifiers:
            raise ValueError("portfolio must contain at least one position")
        if any(position.currency != self.base_currency for position in self.positions):
            raise ValueError("all positions must use base_currency until FX stress is supported")
        return self


class Scenario(StrictModel):
    """Configuration-owned shocks for one classified event."""

    scenario_id: str
    event_type: EventType
    name: str
    scope: ScenarioScope
    rate_shock_bps: Decimal
    credit_spread_shock_bps: Decimal
    loan_pd_multiplier: NonNegativeDecimal
    loan_lgd_addon: ShockFraction
    equity_price_shock: ShockFraction
    derivative_underlying_shock: ShockFraction


class ScenarioBook(StrictModel):
    """Versioned one-to-one event-to-scenario mapping."""

    schema_version: Literal["1.0"]
    version: str
    synthetic: Literal[True]
    description: str
    scenarios: tuple[Scenario, ...]

    @model_validator(mode="after")
    def covers_event_taxonomy_once(self) -> ScenarioBook:
        event_types = [scenario.event_type for scenario in self.scenarios]
        if len(event_types) != len(set(event_types)) or set(event_types) != set(EventType):
            raise ValueError("scenario book must map every event type exactly once")
        scenario_ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("scenario_id values must be unique")
        return self

    def for_event(self, event_type: EventType) -> Scenario:
        return next(scenario for scenario in self.scenarios if scenario.event_type is event_type)


class HypotheticalStressAssumptions(StrictModel):
    """User-supplied assumptions for a clearly hypothetical in-memory stress run."""

    event_type: EventType
    entity_ids: Annotated[tuple[EntityIdentifier, ...], Field(min_length=1, max_length=20)]
    impact_score: Annotated[int, Field(ge=1, le=10)]

    @model_validator(mode="after")
    def unique_entity_ids(self) -> HypotheticalStressAssumptions:
        if len(self.entity_ids) != len(set(self.entity_ids)):
            raise ValueError("entity_ids must be unique")
        return self


class InstrumentStressResult(StrictModel):
    """Before/after valuation and evidence for a single position."""

    instrument_id: str
    issuer_id: str
    sector: str
    asset_class: AssetClass
    affected: bool
    before_value: Money
    after_value: Money
    loss: Money
    expected_loss_before: NonNegativeMoney
    expected_loss_after: NonNegativeMoney
    applied_shocks: dict[str, Decimal]
    rationale: str


class StressResult(StrictModel):
    """Reconciled portfolio outcome for one triggering signal."""

    stress_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    signal_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    trigger_impact_score: Annotated[int, Field(ge=1, le=10)]
    scenario_id: str
    scenario_version: str
    portfolio_id: str
    portfolio_version: str
    base_currency: str
    affected_scope: tuple[str, ...]
    affected_position_count: Annotated[int, Field(ge=0)]
    before_value: Money
    after_value: Money
    total_loss: Money
    loss_percentage: Decimal
    expected_loss_before: NonNegativeMoney
    expected_loss_after: NonNegativeMoney
    expected_loss_change: Money
    reconciliation_difference: NonNegativeMoney
    instrument_results: tuple[InstrumentStressResult, ...]
    created_at: AwareDatetime


class StressDecision(StrictModel):
    """Observable trigger decision, including non-triggered signals."""

    signal_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    trigger_threshold: Annotated[int, Field(ge=1, le=9)]
    triggered: bool
    reason: str
    result: StressResult | None = None

    @model_validator(mode="after")
    def result_matches_decision(self) -> StressDecision:
        if self.triggered != (self.result is not None):
            raise ValueError(
                "triggered decisions must contain a result and skipped decisions must not"
            )
        return self
