"""Validated records returned by persistence repositories."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from risk_engine.ingestion.models import IngestionResult, StrictModel
from risk_engine.stress.models import StressDecision

Identifier = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]


class IngestionRunRecord(StrictModel):
    """Stored ingestion run and its stable repository identifier."""

    run_id: Identifier
    result: IngestionResult


class StressDecisionRecord(StrictModel):
    """Stored stress trigger decision and lookup identifier."""

    decision_id: Identifier
    decision: StressDecision
