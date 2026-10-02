"""Boundary tests for each transparent asset-class valuation model."""

from decimal import Decimal

from risk_engine.nlp.models import EventType
from risk_engine.stress.models import (
    BondPosition,
    DerivativePosition,
    EquityPosition,
    LoanPosition,
    Scenario,
    ScenarioScope,
)
from risk_engine.stress.valuation import value_position


def _scenario() -> Scenario:
    return Scenario(
        scenario_id="test-scenario",
        event_type=EventType.MACROECONOMIC,
        name="Test",
        scope=ScenarioScope.PORTFOLIO,
        rate_shock_bps=Decimal(100),
        credit_spread_shock_bps=Decimal(200),
        loan_pd_multiplier=Decimal(2),
        loan_lgd_addon=Decimal("0.10"),
        equity_price_shock=Decimal("-0.20"),
        derivative_underlying_shock=Decimal("-0.10"),
    )


def _fields() -> dict[str, object]:
    return {
        "instrument_id": "TEST-01",
        "issuer_id": "test-issuer",
        "issuer_name": "Test Issuer",
        "sector": "Test",
        "currency": "USD",
        "market_value": Decimal(1000),
    }


def test_bond_uses_rate_and_spread_duration() -> None:
    position = BondPosition(
        **_fields(),
        duration_years=Decimal(5),
        spread_duration_years=Decimal(4),
    )

    result = value_position(position, _scenario(), affected=True)

    assert result.after_value == Decimal("870.00")
    assert result.loss == Decimal("130.00")


def test_loan_value_tracks_incremental_expected_loss() -> None:
    position = LoanPosition(
        **_fields(),
        probability_of_default=Decimal("0.02"),
        loss_given_default=Decimal("0.50"),
    )

    result = value_position(position, _scenario(), affected=True)

    assert result.expected_loss_before == Decimal("10.00")
    assert result.expected_loss_after == Decimal("24.00")
    assert result.after_value == Decimal("986.00")


def test_equity_uses_direct_percentage_shock() -> None:
    result = value_position(EquityPosition(**_fields()), _scenario(), affected=True)

    assert result.after_value == Decimal("800.00")
    assert result.loss == Decimal("200.00")


def test_derivative_uses_delta_and_dv01() -> None:
    position = DerivativePosition(
        **_fields(),
        delta_exposure=Decimal(1000),
        dv01=Decimal(2),
    )

    result = value_position(position, _scenario(), affected=True)

    assert result.after_value == Decimal("700.00")
    assert result.loss == Decimal("300.00")


def test_out_of_scope_position_is_unchanged() -> None:
    result = value_position(EquityPosition(**_fields()), _scenario(), affected=False)

    assert result.affected is False
    assert result.after_value == result.before_value
    assert result.loss == Decimal("0.00")
    assert result.applied_shocks == {}
