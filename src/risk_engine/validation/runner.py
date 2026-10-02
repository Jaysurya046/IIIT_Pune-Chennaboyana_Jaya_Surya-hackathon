"""Independent source, quality, workflow, and performance validation."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter

from risk_engine import __version__
from risk_engine.api.models import IngestionRunRequest, SourceMode
from risk_engine.api.service import RiskApplicationService
from risk_engine.config import Settings
from risk_engine.ingestion.time import utc_now
from risk_engine.nlp.entity import IssuerResolver
from risk_engine.nlp.events import KeywordEventClassifier
from risk_engine.nlp.models import EventType, SentimentLabel
from risk_engine.nlp.sentiment import RuleBasedSentimentAnalyzer
from risk_engine.persistence import SQLiteStore
from risk_engine.validation.models import (
    PerformanceMetrics,
    QualityMetrics,
    SourceIntegrityMetrics,
    ValidationReport,
    WorkflowMetrics,
)

_PATH_PATTERN = re.compile(r"^\s*- path:\s+(?P<path>\S+)\s*$")
_CLASSIFICATION_PATTERN = re.compile(r"^\s+classification:\s+(?P<classification>[a-z-]+)\s*$")
_CHECKSUM_PATTERN = re.compile(r"^\s+sha256:\s+(?P<checksum>[0-9a-f]{64})\s*$")


def _manifest_entries(manifest_path: Path) -> tuple[tuple[str, str | None, str], ...]:
    entries: list[tuple[str, str | None, str]] = []
    pending_path: str | None = None
    pending_classification: str | None = None
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        path_match = _PATH_PATTERN.match(line)
        if path_match:
            pending_path = path_match.group("path")
            pending_classification = None
            continue
        classification_match = _CLASSIFICATION_PATTERN.match(line)
        if classification_match and pending_path is not None:
            pending_classification = classification_match.group("classification")
            continue
        checksum_match = _CHECKSUM_PATTERN.match(line)
        if checksum_match and pending_path is not None:
            entries.append((pending_path, pending_classification, checksum_match.group("checksum")))
            pending_path = None
            pending_classification = None
    return tuple(entries)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_source_integrity(data_dir: Path) -> SourceIntegrityMetrics:
    """Verify manifested checksums and fixture identity, timing, and classification."""

    data_dir = data_dir.resolve()
    repository_root = data_dir.parent
    manifest_path = data_dir / "sources.yaml"
    issues: list[str] = []
    try:
        entries = _manifest_entries(manifest_path)
    except OSError as error:
        return SourceIntegrityMetrics(
            artifact_count=0,
            fixture_record_count=0,
            unique_source_id_count=0,
            synthetic_fixture_count=0,
            passed=False,
            issues=(f"Unable to read source manifest ({type(error).__name__}).",),
        )

    if not entries:
        issues.append("Source manifest contains no checksummed artifacts.")
    for relative_path, classification, expected_checksum in entries:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:1] != ("data",):
            issues.append(f"Manifest path is outside the data directory: {relative_path}.")
            continue
        if classification not in {"synthetic", "project-authored"}:
            issues.append(f"Manifest classification is missing or invalid: {relative_path}.")
        artifact = repository_root / relative_path
        if not artifact.is_file():
            issues.append(f"Manifest artifact is missing: {relative_path}.")
            continue
        observed_checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if observed_checksum != expected_checksum:
            issues.append(f"Checksum mismatch: {relative_path}.")

    fixture_records: list[dict[str, object]] = []
    source_ids: list[str] = []
    synthetic_fixture_count = 0
    for fixture_path in sorted((data_dir / "sample").glob("*.json")):
        try:
            payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            issues.append(f"Invalid fixture {fixture_path.name} ({type(error).__name__}).")
            continue
        if payload.get("synthetic") is not True:
            issues.append(f"Fixture is not explicitly synthetic: {fixture_path.name}.")
        else:
            synthetic_fixture_count += 1
        records = payload.get("records")
        if not isinstance(records, list) or not records:
            issues.append(f"Fixture has no records: {fixture_path.name}.")
            continue
        for record in records:
            fixture_records.append(record)
            source_id = str(record.get("source_id", ""))
            source_ids.append(source_id)
            if not source_id:
                issues.append(f"Fixture record has no source_id: {fixture_path.name}.")
            if not str(record.get("text", "")).strip():
                issues.append(f"Fixture record has empty text: {source_id or fixture_path.name}.")
            try:
                published_at = _parse_timestamp(str(record["published_at"]))
                retrieved_at = _parse_timestamp(str(record["retrieved_at"]))
                if published_at > retrieved_at:
                    issues.append(f"Fixture publication follows retrieval: {source_id}.")
            except (KeyError, TypeError, ValueError):
                issues.append(f"Fixture record has invalid timestamps: {source_id}.")

    duplicates = sorted(key for key, count in Counter(source_ids).items() if key and count > 1)
    if duplicates:
        issues.append(f"Duplicate fixture source_id values: {', '.join(duplicates)}.")
    if synthetic_fixture_count != 2:
        issues.append("Expected exactly two explicitly synthetic fixture bundles.")

    return SourceIntegrityMetrics(
        artifact_count=len(entries),
        fixture_record_count=len(fixture_records),
        unique_source_id_count=len(set(source_ids)),
        synthetic_fixture_count=synthetic_fixture_count,
        passed=not issues,
        issues=tuple(issues),
    )


def _quality_metrics(data_dir: Path) -> QualityMetrics:
    golden_path = data_dir / "evaluation" / "nlp_golden.json"
    payload = json.loads(golden_path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    resolver = IssuerResolver(data_dir / "nlp" / "issuer_watchlist.json")
    events = KeywordEventClassifier(data_dir / "nlp" / "event_taxonomy.json")
    sentiment = RuleBasedSentimentAnalyzer()

    event_correct = 0
    sentiment_correct = 0
    entity_correct = 0
    observed_events: set[EventType] = set()
    for case in cases:
        event = events.classify(case["text"]).event_type
        sentiment_label = sentiment.analyze(case["text"]).label
        entities = {match.entity_id for match in resolver.resolve(case["text"])}
        observed_events.add(EventType(case["expected_event"]))
        event_correct += event is EventType(case["expected_event"])
        sentiment_correct += sentiment_label is SentimentLabel(case["expected_sentiment"])
        entity_correct += entities == set(case["expected_entities"])

    case_count = len(cases)
    return QualityMetrics(
        case_count=case_count,
        taxonomy_coverage_count=len(observed_events),
        event_accuracy=event_correct / case_count if case_count else 0.0,
        sentiment_accuracy=sentiment_correct / case_count if case_count else 0.0,
        entity_accuracy=entity_correct / case_count if case_count else 0.0,
    )


def _expected_portfolio_total(data_dir: Path) -> Decimal:
    payload = json.loads((data_dir / "portfolio" / "portfolio.json").read_text("utf-8"))
    return sum((Decimal(position["market_value"]) for position in payload["positions"]), Decimal(0))


def _workflow_metrics(data_dir: Path, database_path: Path) -> WorkflowMetrics:
    issues: list[str] = []
    settings = Settings(
        environment="test",
        data_dir=data_dir,
        database_url=f"sqlite:///{database_path.as_posix()}",
        offline_mode=True,
        nlp_mode="deterministic",
    )
    store = SQLiteStore(settings.database_url)
    service = RiskApplicationService(settings, store)
    ingestion = service.ingest(
        IngestionRunRequest(query="portfolio risk", source_mode=SourceMode.FIXTURES)
    )
    analysis = service.analyze(ingestion.run_id, "deterministic")
    if analysis is None:  # pragma: no cover - run was just persisted
        raise RuntimeError("Persisted validation ingestion run could not be analyzed")

    documents = store.get_ingestion(ingestion.run_id)
    if documents is None:  # pragma: no cover - run was just persisted
        raise RuntimeError("Validation ingestion run could not be restored")
    document_ids = [item.document_id for item in documents.result.documents]
    signal_ids = [item.signal_id for item in analysis.signals]
    synthetic_signal_count = sum(item.provenance.synthetic for item in analysis.signals)
    source_count = len({item.provenance.source for item in analysis.signals})

    if ingestion.failed_source_count:
        issues.append("One or more fixture sources failed during the offline workflow.")
    if len(document_ids) != len(set(document_ids)):
        issues.append("Offline workflow produced duplicate document identifiers.")
    if len(signal_ids) != len(set(signal_ids)):
        issues.append("Offline workflow produced duplicate signal identifiers.")
    if synthetic_signal_count != len(analysis.signals):
        issues.append("Offline workflow produced a signal without synthetic provenance.")

    portfolio = service.portfolio_summary()
    expected_total = _expected_portfolio_total(data_dir)
    if portfolio.total_market_value != expected_total:
        issues.append("Portfolio API total does not match independent position summation.")
    for label, breakdown in (
        ("asset class", portfolio.by_asset_class),
        ("sector", portfolio.by_sector),
        ("issuer", portfolio.by_issuer),
    ):
        if sum((item.market_value for item in breakdown), Decimal(0)) != expected_total:
            issues.append(f"Portfolio {label} breakdown does not reconcile to total value.")

    probe = next((item for item in analysis.signals if item.entities), analysis.signals[0])
    probe = probe.model_copy(update={"impact_score": 8})
    store.save_signals((probe,))
    stress = service.stress(probe.signal_id)
    if stress is None or stress.decision.result is None:  # pragma: no cover - probe is stored
        raise RuntimeError("High-impact validation probe did not produce a stress result")
    result = stress.decision.result
    independent_before = sum((item.before_value for item in result.instrument_results), Decimal(0))
    independent_after = sum((item.after_value for item in result.instrument_results), Decimal(0))
    independent_loss = sum((item.loss for item in result.instrument_results), Decimal(0))
    if independent_before != result.before_value:
        issues.append("Stress before value does not reconcile to instrument values.")
    if independent_after != result.after_value:
        issues.append("Stress after value does not reconcile to instrument values.")
    if independent_loss != result.total_loss:
        issues.append("Stress total loss does not reconcile to instrument losses.")
    if result.before_value - result.after_value != result.total_loss:
        issues.append("Stress before-after difference does not equal total loss.")

    stress_id = result.stress_id
    store.close()
    reopened = SQLiteStore(settings.database_url)
    persisted_signals, persisted_signal_count = reopened.list_signals(limit=100, offset=0)
    persisted_result = reopened.get_stress_result(stress_id)
    stress_probe_persisted = persisted_result is not None
    if persisted_signal_count != len(analysis.signals):
        issues.append("Persisted signal count changed after database reopen.")
    if not stress_probe_persisted:
        issues.append("Stress result was not recoverable after database reopen.")
    reopened.close()

    return WorkflowMetrics(
        document_count=len(document_ids),
        source_count=source_count,
        signal_count=len(signal_ids),
        unique_document_count=len(set(document_ids)),
        unique_signal_count=len(set(signal_ids)),
        synthetic_signal_count=synthetic_signal_count,
        persisted_signal_count=len(persisted_signals),
        stress_probe_triggered=stress.decision.triggered,
        stress_probe_persisted=stress_probe_persisted,
        portfolio_total=portfolio.total_market_value,
        stress_total_loss=result.total_loss,
        reconciliation_difference=result.reconciliation_difference,
        passed=not issues,
        issues=tuple(issues),
    )


def run_validation(
    *,
    data_dir: Path = Path("data"),
    database_path: Path | None = None,
    max_seconds: float = 5.0,
    clock: Callable[[], datetime] = utc_now,
    timer: Callable[[], float] = perf_counter,
) -> ValidationReport:
    """Run deterministic validation and return inspectable machine-readable evidence."""

    if max_seconds <= 0:
        raise ValueError("max_seconds must be greater than zero")
    data_dir = data_dir.resolve()
    overall_start = timer()

    stage_start = timer()
    source_integrity = validate_source_integrity(data_dir)
    source_integrity_seconds = timer() - stage_start

    stage_start = timer()
    quality = _quality_metrics(data_dir)
    golden_benchmark_seconds = timer() - stage_start

    stage_start = timer()
    temporary_directory: tempfile.TemporaryDirectory[str] | None = None
    if database_path is None:
        temporary_directory = tempfile.TemporaryDirectory(prefix="risksignal-validation-")
        database_path = Path(temporary_directory.name) / "validation.db"
    try:
        workflow = _workflow_metrics(data_dir, database_path.resolve())
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()
    workflow_seconds = timer() - stage_start
    total_seconds = timer() - overall_start

    quality_passed = (
        quality.case_count > 0
        and quality.taxonomy_coverage_count == len(EventType)
        and quality.event_accuracy == 1.0
        and quality.sentiment_accuracy == 1.0
        and quality.entity_accuracy == 1.0
    )
    issues = [*source_integrity.issues, *workflow.issues]
    if not quality_passed:
        issues.append("Synthetic golden regression benchmark did not match all expected labels.")
    within_budget = total_seconds <= max_seconds
    if not within_budget:
        issues.append(
            f"Offline validation took {total_seconds:.6f}s, exceeding {max_seconds:.6f}s."
        )

    return ValidationReport(
        application_version=__version__,
        generated_at=clock(),
        passed=source_integrity.passed and quality_passed and workflow.passed and within_budget,
        source_integrity=source_integrity,
        quality=quality,
        workflow=workflow,
        performance=PerformanceMetrics(
            source_integrity_seconds=source_integrity_seconds,
            golden_benchmark_seconds=golden_benchmark_seconds,
            workflow_seconds=workflow_seconds,
            total_seconds=total_seconds,
            budget_seconds=max_seconds,
            within_budget=within_budget,
        ),
        issues=tuple(issues),
    )
