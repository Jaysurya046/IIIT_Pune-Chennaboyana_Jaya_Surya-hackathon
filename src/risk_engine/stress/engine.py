"""Event-driven portfolio stress orchestration and reconciliation."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from datetime import datetime
from decimal import Decimal

from risk_engine.ingestion.time import utc_now
from risk_engine.nlp.models import RiskSignal
from risk_engine.stress.models import (
    Portfolio,
    Scenario,
    ScenarioBook,
    ScenarioScope,
    StressDecision,
    StressResult,
)
from risk_engine.stress.valuation import money, value_position


class ReconciliationError(RuntimeError):
    """Raised when instrument and portfolio totals do not agree to tolerance."""


class StressEngine:
    """Map high-impact risk signals to scenarios and reconcile portfolio outcomes."""

    def __init__(
        self,
        portfolio: Portfolio,
        scenario_book: ScenarioBook,
        *,
        trigger_threshold: int = 7,
        reconciliation_tolerance: Decimal = Decimal("0.01"),
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if not 1 <= trigger_threshold <= 9:
            raise ValueError("trigger_threshold must be between 1 and 9")
        if reconciliation_tolerance < 0:
            raise ValueError("reconciliation_tolerance must not be negative")
        self._portfolio = portfolio
        self._scenario_book = scenario_book
        self._trigger_threshold = trigger_threshold
        self._tolerance = reconciliation_tolerance
        self._clock = clock

    @staticmethod
    def _targets(signal: RiskSignal, scenario: Scenario) -> tuple[str, ...]:
        if scenario.scope is ScenarioScope.PORTFOLIO:
            return ("portfolio",)
        return tuple(sorted({entity.entity_id for entity in signal.entities}))

    @staticmethod
    def _is_affected(issuer_id: str, scenario: Scenario, targets: tuple[str, ...]) -> bool:
        return scenario.scope is ScenarioScope.PORTFOLIO or issuer_id in targets

    def run(self, signal: RiskSignal) -> StressDecision:
        """Return an explicit trigger decision and, when triggered, a stress result."""

        if signal.impact_score <= self._trigger_threshold:
            return StressDecision(
                signal_id=signal.signal_id,
                trigger_threshold=self._trigger_threshold,
                triggered=False,
                reason=(
                    f"Impact score {signal.impact_score} does not exceed "
                    f"the trigger threshold {self._trigger_threshold}."
                ),
            )

        scenario = self._scenario_book.for_event(signal.event.event_type)
        targets = self._targets(signal, scenario)
        instrument_results = tuple(
            value_position(
                position,
                scenario,
                affected=self._is_affected(position.issuer_id, scenario, targets),
            )
            for position in self._portfolio.positions
        )
        before = money(sum((result.before_value for result in instrument_results), Decimal(0)))
        after = money(sum((result.after_value for result in instrument_results), Decimal(0)))
        total_loss = money(before - after)
        instrument_loss = money(sum((result.loss for result in instrument_results), Decimal(0)))
        reconciliation = money(abs(total_loss - instrument_loss))
        if reconciliation > self._tolerance:
            raise ReconciliationError(
                f"Portfolio loss differs from instrument losses by {reconciliation}"
            )
        expected_before = money(
            sum((result.expected_loss_before for result in instrument_results), Decimal(0))
        )
        expected_after = money(
            sum((result.expected_loss_after for result in instrument_results), Decimal(0))
        )
        identity = (
            f"{signal.signal_id}|{scenario.scenario_id}|{self._scenario_book.version}|"
            f"{self._portfolio.portfolio_id}|{self._portfolio.version}"
        )
        result = StressResult(
            stress_id=hashlib.sha256(identity.encode()).hexdigest()[:32],
            signal_id=signal.signal_id,
            trigger_impact_score=signal.impact_score,
            scenario_id=scenario.scenario_id,
            scenario_version=self._scenario_book.version,
            portfolio_id=self._portfolio.portfolio_id,
            portfolio_version=self._portfolio.version,
            base_currency=self._portfolio.base_currency,
            affected_scope=targets,
            affected_position_count=sum(item.affected for item in instrument_results),
            before_value=before,
            after_value=after,
            total_loss=total_loss,
            loss_percentage=(
                (total_loss / before * Decimal(100)).quantize(Decimal("0.000001"))
                if before
                else Decimal(0)
            ),
            expected_loss_before=expected_before,
            expected_loss_after=expected_after,
            expected_loss_change=money(expected_after - expected_before),
            reconciliation_difference=reconciliation,
            instrument_results=instrument_results,
            created_at=self._clock(),
        )
        return StressDecision(
            signal_id=signal.signal_id,
            trigger_threshold=self._trigger_threshold,
            triggered=True,
            reason=(
                f"Impact score {signal.impact_score} exceeds the trigger threshold "
                f"{self._trigger_threshold}; applied {scenario.scenario_id}."
            ),
            result=result,
        )

    def run_many(self, signals: Iterable[RiskSignal]) -> tuple[StressDecision, ...]:
        return tuple(self.run(signal) for signal in signals)
