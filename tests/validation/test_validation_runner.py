"""Source, quality, workflow, persistence, and performance validation tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from risk_engine.validation import run_validation, validate_source_integrity


def test_validation_report_covers_the_complete_offline_workflow(tmp_path: Path) -> None:
    report = run_validation(
        data_dir=Path("data"),
        database_path=tmp_path / "validation.db",
        max_seconds=30.0,
    )

    assert report.passed is True
    assert report.application_version == "0.8.0"
    assert report.classification == "synthetic-offline-validation"
    assert report.source_integrity.artifact_count == 11
    assert report.source_integrity.fixture_record_count == 6
    assert report.source_integrity.unique_source_id_count == 6
    assert report.quality.case_count == 8
    assert report.quality.taxonomy_coverage_count == 8
    assert report.quality.event_accuracy == 1.0
    assert report.quality.sentiment_accuracy == 1.0
    assert report.quality.entity_accuracy == 1.0
    assert report.workflow.document_count == 6
    assert report.workflow.source_count == 2
    assert report.workflow.signal_count == 6
    assert report.workflow.synthetic_signal_count == 6
    assert report.workflow.persisted_signal_count == 6
    assert report.workflow.stress_probe_triggered is True
    assert report.workflow.stress_probe_persisted is True
    assert report.workflow.portfolio_total == 55_500_000
    assert report.workflow.reconciliation_difference == 0
    assert report.performance.within_budget is True
    assert report.issues == ()


def test_source_integrity_detects_a_tampered_manifest_artifact(tmp_path: Path) -> None:
    copied_data = tmp_path / "data"
    paths = (
        "sample/gdelt_articles.json",
        "sample/bluesky_posts.json",
        "evaluation/nlp_golden.json",
        "nlp/issuer_watchlist.json",
        "nlp/event_taxonomy.json",
        "portfolio/portfolio.json",
        "portfolio/scenarios.json",
        "sources.yaml",
    )
    for relative_path in paths:
        destination = copied_data / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path("data") / relative_path, destination)
    fixture_path = copied_data / "sample" / "gdelt_articles.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture["records"][0]["text"] = "tampered"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    integrity = validate_source_integrity(copied_data)

    assert integrity.passed is False
    assert "Checksum mismatch: data/sample/gdelt_articles.json." in integrity.issues


def test_validation_rejects_non_positive_performance_budget() -> None:
    try:
        run_validation(max_seconds=0)
    except ValueError as error:
        assert str(error) == "max_seconds must be greater than zero"
    else:  # pragma: no cover - required assertion branch
        raise AssertionError("run_validation accepted an invalid performance budget")
