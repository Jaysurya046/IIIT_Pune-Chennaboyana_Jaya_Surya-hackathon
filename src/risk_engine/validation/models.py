"""Strict contracts for machine-readable validation evidence."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from risk_engine.ingestion.models import StrictModel

Accuracy = Annotated[float, Field(ge=0.0, le=1.0)]
Duration = Annotated[float, Field(ge=0.0)]


class SourceIntegrityMetrics(StrictModel):
    artifact_count: int
    fixture_record_count: int
    unique_source_id_count: int
    synthetic_fixture_count: int
    passed: bool
    issues: tuple[str, ...] = ()


class QualityMetrics(StrictModel):
    case_count: int
    taxonomy_coverage_count: int
    event_accuracy: Accuracy
    sentiment_accuracy: Accuracy
    entity_accuracy: Accuracy
    synthetic: Literal[True] = True


class WorkflowMetrics(StrictModel):
    document_count: int
    source_count: int
    signal_count: int
    unique_document_count: int
    unique_signal_count: int
    synthetic_signal_count: int
    persisted_signal_count: int
    stress_probe_triggered: bool
    stress_probe_persisted: bool
    portfolio_total: Decimal
    stress_total_loss: Decimal
    reconciliation_difference: Decimal
    passed: bool
    issues: tuple[str, ...] = ()


class PerformanceMetrics(StrictModel):
    source_integrity_seconds: Duration
    golden_benchmark_seconds: Duration
    workflow_seconds: Duration
    total_seconds: Duration
    budget_seconds: Annotated[float, Field(gt=0.0)]
    within_budget: bool


class ValidationReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    application_version: str
    generated_at: AwareDatetime
    classification: Literal["synthetic-offline-validation"] = "synthetic-offline-validation"
    passed: bool
    source_integrity: SourceIntegrityMetrics
    quality: QualityMetrics
    workflow: WorkflowMetrics
    performance: PerformanceMetrics
    issues: tuple[str, ...] = ()
    caveats: tuple[str, ...] = (
        "Golden cases are synthetic regression evidence, not real-world accuracy estimates.",
        "Portfolio positions and scenario shocks are synthetic illustrative assumptions.",
        "Performance is a local deterministic-path measurement, not a production SLA.",
    )
