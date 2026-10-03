from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from risk_engine.benchmarking import BenchmarkDataError, load_csv, run_benchmark
from risk_engine.config import Settings
from risk_engine.nlp.models import SentimentLabel, SentimentResult
from risk_engine.nlp.sentiment import ModelDependencyError


class FakeAnalyzer:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.model_version = f"fake-{mode}-v1"

    def analyze(self, text: str) -> SentimentResult:
        label = (
            SentimentLabel.NEUTRAL
            if self.mode == "deterministic"
            else SentimentLabel(text)
        )
        probabilities = {candidate: 0.0 for candidate in SentimentLabel}
        probabilities[label] = 1.0
        return SentimentResult(
            label=label,
            score=0.0,
            confidence=1.0,
            probabilities=probabilities,
        )


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_csv_normalizes_named_and_numeric_labels(tmp_path: Path) -> None:
    dataset = _write_csv(
        tmp_path / "benchmark.csv",
        "sentence,sentiment\nnegative, Negative \nneutral,1\npositive,2\n",
    )

    examples = load_csv(dataset, text_column="sentence", label_column="sentiment")

    assert [example.label for example in examples] == [
        SentimentLabel.NEGATIVE,
        SentimentLabel.NEUTRAL,
        SentimentLabel.POSITIVE,
    ]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("wrong,sentiment\ntext,neutral\n", "missing required columns: sentence"),
        ("sentence,sentiment\n,neutral\n", "row 2: text must not be blank"),
        ("sentence,sentiment\ntext,\n", "row 2: label must not be blank"),
        ("sentence,sentiment\ntext,mixed\n", "row 2: unsupported label"),
        ("sentence,sentiment\n", "at least one data row"),
        ("sentence,sentence\ntext,neutral\n", "contains duplicate columns: sentence"),
        ("sentence,sentiment\ntext,neutral,extra\n", "more values than the header"),
    ],
)
def test_load_csv_rejects_malformed_data(
    tmp_path: Path, content: str, message: str
) -> None:
    dataset = _write_csv(tmp_path / "invalid.csv", content)

    with pytest.raises(BenchmarkDataError, match=message):
        load_csv(dataset, text_column="sentence", label_column="sentiment")


def test_run_benchmark_compares_modes_in_stable_order(tmp_path: Path) -> None:
    dataset = _write_csv(
        tmp_path / "benchmark.csv",
        "sentence,label\nnegative,negative\nneutral,neutral\npositive,positive\n",
    )
    requested_modes: list[str] = []

    def build_fake(_settings: Settings, mode: str) -> FakeAnalyzer:
        requested_modes.append(mode)
        return FakeAnalyzer(mode)

    report = run_benchmark(
        dataset,
        text_column="sentence",
        label_column="label",
        settings=Settings(),
        analyzer_factory=build_fake,
    )

    assert requested_modes == ["deterministic", "model"]
    assert report.row_count == 3
    assert report.dataset_sha256 == hashlib.sha256(dataset.read_bytes()).hexdigest()
    assert report.label_distribution == {"negative": 1, "neutral": 1, "positive": 1}
    assert [metrics.mode for metrics in report.modes] == ["deterministic", "model"]
    assert report.modes[0].accuracy == 0.333333
    assert report.modes[1].accuracy == 1.0
    assert report.to_markdown().splitlines()[2].startswith("| deterministic |")
    assert report.to_markdown().splitlines()[3].startswith("| model |")


def test_run_benchmark_propagates_model_failure_without_fallback(tmp_path: Path) -> None:
    dataset = _write_csv(tmp_path / "benchmark.csv", "sentence,label\nneutral,neutral\n")
    requested_modes: list[str] = []

    def fail_model(_settings: Settings, mode: str) -> FakeAnalyzer:
        requested_modes.append(mode)
        if mode == "model":
            raise ModelDependencyError("model weights unavailable")
        return FakeAnalyzer(mode)

    with pytest.raises(ModelDependencyError, match="weights unavailable"):
        run_benchmark(
            dataset,
            text_column="sentence",
            label_column="label",
            settings=Settings(),
            analyzer_factory=fail_model,
        )

    assert requested_modes == ["deterministic", "model"]
