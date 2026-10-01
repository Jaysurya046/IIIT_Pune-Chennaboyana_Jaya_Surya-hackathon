"""Smoke tests for the installable package and CLI."""

from __future__ import annotations

import json

import pytest

from risk_engine import __version__
from risk_engine.cli import main


def test_package_has_version() -> None:
    assert __version__ == "0.1.0"


def test_check_command_prints_public_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["app_name"] == "RiskSignal Engine"
    assert payload["offline_mode"] is True
