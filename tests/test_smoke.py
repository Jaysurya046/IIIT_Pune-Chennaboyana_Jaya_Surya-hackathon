"""Smoke tests for the installable package and CLI."""

from __future__ import annotations

import json

import pytest

from risk_engine import __version__
from risk_engine.cli import main


def test_package_has_version() -> None:
    assert __version__ == "0.7.0"


def test_check_command_prints_public_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["app_name"] == "RiskSignal Engine"
    assert payload["offline_mode"] is True


def test_fixture_command_processes_both_sources(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["ingest-fixtures", "--query", "portfolio risk"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert len(payload["documents"]) == 6
    assert {status["source"] for status in payload["sources"]} == {"gdelt", "bluesky"}
    assert all(document["provenance"]["synthetic"] for document in payload["documents"])


def test_analyze_fixture_command_generates_explainable_signals(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["analyze-fixtures", "--query", "portfolio risk"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert len(payload) == 6
    assert all(1 <= signal["impact_score"] <= 10 for signal in payload)
    assert all(signal["impact_factors"] for signal in payload)
    assert all(signal["model_versions"] for signal in payload)


def test_stress_fixture_command_records_trigger_decisions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["stress-fixtures", "--query", "portfolio risk"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert len(payload) == 6
    assert all(decision["trigger_threshold"] == 7 for decision in payload)
    assert all(not decision["triggered"] for decision in payload)
