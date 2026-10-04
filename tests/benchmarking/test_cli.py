from __future__ import annotations

import json
from pathlib import Path

from risk_engine import cli
from risk_engine.benchmarking.models import BenchmarkReport, ModeMetrics
from risk_engine.nlp.sentiment import ModelDependencyError


def _metrics(mode: str) -> ModeMetrics:
    confusion = {
        "negative": {"negative": 1, "neutral": 0, "positive": 0},
        "neutral": {"negative": 0, "neutral": 1, "positive": 0},
        "positive": {"negative": 0, "neutral": 0, "positive": 1},
    }
    return ModeMetrics(
        mode=mode,
        model_version=f"fake-{mode}",
        accuracy=1.0,
        macro_f1=1.0,
        support={"negative": 1, "neutral": 1, "positive": 1},
        per_class_f1={"negative": 1.0, "neutral": 1.0, "positive": 1.0},
        confusion_matrix=confusion,
        trigger_threshold=7,
        trigger_count=1,
        non_trigger_count=2,
        trigger_rate=0.333333,
    )


def _report() -> BenchmarkReport:
    return BenchmarkReport(
        dataset_filename="external.csv",
        dataset_sha256="a" * 64,
        text_column="sentence",
        label_column="label",
        row_count=3,
        label_distribution={"negative": 1, "neutral": 1, "positive": 1},
        modes=(_metrics("deterministic"), _metrics("model")),
    )


def test_benchmark_command_prints_json_and_writes_requested_outputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    dataset = tmp_path / "external.csv"
    dataset.write_text("unused", encoding="utf-8")
    json_output = tmp_path / "result.json"
    markdown_output = tmp_path / "result.md"

    def fake_run(*args, **kwargs) -> BenchmarkReport:
        assert args == (dataset,)
        assert kwargs["text_column"] == "sentence"
        assert kwargs["label_column"] == "label"
        return _report()

    monkeypatch.setattr(cli, "run_benchmark", fake_run)

    exit_code = cli.main(
        [
            "benchmark",
            "--dataset",
            str(dataset),
            "--text-col",
            "sentence",
            "--label-col",
            "label",
            "--output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
        ]
    )

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert stdout["classification"] == "external-user-supplied-benchmark"
    assert json.loads(json_output.read_text(encoding="utf-8")) == stdout
    markdown = markdown_output.read_text(encoding="utf-8")
    assert "| deterministic | fake-deterministic | 1.0000 |" in markdown
    assert "| 1/3 | 0.3333 |" in markdown


def test_benchmark_command_reports_model_failure_without_result(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    dataset = tmp_path / "external.csv"
    dataset.write_text("unused", encoding="utf-8")

    def fail(*args, **kwargs):
        raise ModelDependencyError("pinned model is unavailable")

    monkeypatch.setattr(cli, "run_benchmark", fail)

    exit_code = cli.main(
        [
            "benchmark",
            "--dataset",
            str(dataset),
            "--text-col",
            "sentence",
            "--label-col",
            "label",
        ]
    )

    captured = capsys.readouterr()
    error = json.loads(captured.err)
    assert exit_code == 1
    assert captured.out == ""
    assert error == {
        "classification": "benchmark-error",
        "error_type": "ModelDependencyError",
        "message": "pinned model is unavailable",
    }
