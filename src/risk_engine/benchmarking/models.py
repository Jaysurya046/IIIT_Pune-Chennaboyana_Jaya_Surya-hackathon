"""Typed benchmark results and dependency-free classification metrics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from pydantic import Field

from risk_engine.ingestion.models import StrictModel
from risk_engine.nlp.models import SentimentLabel

LABEL_ORDER = (
    SentimentLabel.NEGATIVE,
    SentimentLabel.NEUTRAL,
    SentimentLabel.POSITIVE,
)


class BenchmarkExample(StrictModel):
    """One validated text and human sentiment label."""

    text: str = Field(min_length=1)
    label: SentimentLabel


class ModeMetrics(StrictModel):
    """Classification quality and confusion counts for one explicit NLP mode."""

    mode: str
    model_version: str
    accuracy: float = Field(ge=0.0, le=1.0)
    macro_f1: float = Field(ge=0.0, le=1.0)
    support: dict[str, int]
    per_class_f1: dict[str, float]
    confusion_matrix: dict[str, dict[str, int]]


class BenchmarkReport(StrictModel):
    """Reproducible description and results for one local benchmark CSV."""

    schema_version: str = "1.0"
    classification: str = "external-user-supplied-benchmark"
    dataset_filename: str
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text_column: str
    label_column: str
    row_count: int = Field(gt=0)
    label_distribution: dict[str, int]
    modes: tuple[ModeMetrics, ...]

    def to_markdown(self) -> str:
        """Render one compact results table suitable for project documentation."""

        headers = [
            "Mode",
            "Model/version",
            "Accuracy",
            "Macro-F1",
            "Actual negative → N/Neu/P",
            "Actual neutral → N/Neu/P",
            "Actual positive → N/Neu/P",
        ]
        rows = []
        for metrics in self.modes:
            confusion_cells = []
            for actual in LABEL_ORDER:
                counts = metrics.confusion_matrix[actual.value]
                confusion_cells.append(
                    "/".join(str(counts[predicted.value]) for predicted in LABEL_ORDER)
                )
            rows.append(
                [
                    metrics.mode,
                    metrics.model_version.replace("|", "\\|"),
                    f"{metrics.accuracy:.4f}",
                    f"{metrics.macro_f1:.4f}",
                    *confusion_cells,
                ]
            )
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in rows)
        return "\n".join(lines)


def calculate_metrics(
    *,
    mode: str,
    model_version: str,
    actual: Sequence[SentimentLabel],
    predicted: Sequence[SentimentLabel],
) -> ModeMetrics:
    """Calculate accuracy, macro-F1, and an actual-by-predicted confusion matrix."""

    if not actual:
        raise ValueError("at least one benchmark label is required")
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted labels must have equal lengths")

    confusion = {
        label.value: {candidate.value: 0 for candidate in LABEL_ORDER}
        for label in LABEL_ORDER
    }
    for expected, observed in zip(actual, predicted, strict=True):
        confusion[expected.value][observed.value] += 1

    raw_class_f1: dict[str, float] = {}
    for label in LABEL_ORDER:
        name = label.value
        true_positive = confusion[name][name]
        false_positive = sum(
            confusion[other.value][name] for other in LABEL_ORDER if other is not label
        )
        false_negative = sum(
            confusion[name][other.value] for other in LABEL_ORDER if other is not label
        )
        denominator = (2 * true_positive) + false_positive + false_negative
        raw_class_f1[name] = (2 * true_positive / denominator) if denominator else 0.0

    correct = sum(confusion[label.value][label.value] for label in LABEL_ORDER)
    support_counts = Counter(label.value for label in actual)
    return ModeMetrics(
        mode=mode,
        model_version=model_version,
        accuracy=round(correct / len(actual), 6),
        macro_f1=round(sum(raw_class_f1.values()) / len(LABEL_ORDER), 6),
        support={label.value: support_counts[label.value] for label in LABEL_ORDER},
        per_class_f1={name: round(value, 6) for name, value in raw_class_f1.items()},
        confusion_matrix=confusion,
    )
