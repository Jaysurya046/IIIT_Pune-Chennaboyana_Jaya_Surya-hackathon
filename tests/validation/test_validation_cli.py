"""Validation command output and exit-code tests."""

from __future__ import annotations

import json
from pathlib import Path

from risk_engine.cli import main


def test_validate_command_writes_machine_readable_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    output = tmp_path / "validation.json"

    exit_code = main(["validate", "--max-seconds", "30", "--output", str(output)])
    stdout = json.loads(capsys.readouterr().out)
    saved = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout == saved
    assert saved["passed"] is True
    assert saved["classification"] == "synthetic-offline-validation"
