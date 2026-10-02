"""Simplified and transparent asset-class stress calculations."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from risk_engine.stress.models import (
    BondPosition,
    DerivativePosition,
    EquityPosition,
    InstrumentStressResult,
    LoanPosition,
    Position,
    Scenario,
)

CENT = Decimal("0.01")
BASIS_POINTS = Decimal("10000")


def money(value: Decimal) -> Decimal:
    """Round monetary values consistently to cents."""

    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _loan_expected_loss(position: LoanPosition) -> Decimal:
    return money(
        position.market_value * position.probability_of_default * position.loss_given_default
    )


def value_position(
    position: Position,
    scenario: Scenario,
    *,
    affected: bool,
) -> InstrumentStressResult:
    """Apply the relevant transparent approximation to one position."""

    before = money(position.market_value)
    expected_before = (
        _loan_expected_loss(position) if isinstance(position, LoanPosition) else CENT * 0
    )
    if not affected:
        return InstrumentStressResult(
            instrument_id=position.instrument_id,
            issuer_id=position.issuer_id,
            sector=position.sector,
            asset_class=position.asset_class,
            affected=False,
            before_value=before,
            after_value=before,
            loss=CENT * 0,
            expected_loss_before=expected_before,
            expected_loss_after=expected_before,
            applied_shocks={},
            rationale="Position is outside the scenario scope.",
        )

    expected_after = expected_before
    if isinstance(position, BondPosition):
        rate_move = position.duration_years * scenario.rate_shock_bps / BASIS_POINTS
        spread_move = (
            position.spread_duration_years * scenario.credit_spread_shock_bps / BASIS_POINTS
        )
        after = money(max(Decimal(0), before * (Decimal(1) - rate_move - spread_move)))
        shocks = {
            "rate_shock_bps": scenario.rate_shock_bps,
            "credit_spread_shock_bps": scenario.credit_spread_shock_bps,
        }
        rationale = "Duration approximation: value × (1 - duration×rate - spread-duration×spread)."
    elif isinstance(position, LoanPosition):
        stressed_pd = min(Decimal(1), position.probability_of_default * scenario.loan_pd_multiplier)
        stressed_lgd = min(
            Decimal(1), max(Decimal(0), position.loss_given_default + scenario.loan_lgd_addon)
        )
        expected_after = money(before * stressed_pd * stressed_lgd)
        after = money(max(Decimal(0), before - (expected_after - expected_before)))
        shocks = {
            "loan_pd_multiplier": scenario.loan_pd_multiplier,
            "loan_lgd_addon": scenario.loan_lgd_addon,
        }
        rationale = "Loan value falls by the increase in PD × LGD expected loss."
    elif isinstance(position, EquityPosition):
        after = money(before * (Decimal(1) + scenario.equity_price_shock))
        shocks = {"equity_price_shock": scenario.equity_price_shock}
        rationale = "Equity value receives the configured direct percentage shock."
    elif isinstance(position, DerivativePosition):
        pnl = (
            position.delta_exposure * scenario.derivative_underlying_shock
            - position.dv01 * scenario.rate_shock_bps
        )
        after = money(before + pnl)
        shocks = {
            "derivative_underlying_shock": scenario.derivative_underlying_shock,
            "rate_shock_bps": scenario.rate_shock_bps,
        }
        rationale = "Derivative P&L uses delta exposure plus the DV01 rate approximation."
    else:  # pragma: no cover - discriminated contracts make this unreachable
        raise TypeError(f"Unsupported position type: {type(position).__name__}")

    return InstrumentStressResult(
        instrument_id=position.instrument_id,
        issuer_id=position.issuer_id,
        sector=position.sector,
        asset_class=position.asset_class,
        affected=True,
        before_value=before,
        after_value=after,
        loss=money(before - after),
        expected_loss_before=expected_before,
        expected_loss_after=expected_after,
        applied_shocks=shocks,
        rationale=rationale,
    )
