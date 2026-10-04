"""CSV loading and explicit deterministic-versus-model benchmark execution."""

from __future__ import annotations

import csv
import hashlib
import io
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from risk_engine.benchmarking.models import (
    LABEL_ORDER,
    BenchmarkExample,
    BenchmarkReport,
    calculate_metrics,
)
from risk_engine.config import Settings
from risk_engine.ingestion.models import Provenance, RawDocument, SourceType
from risk_engine.nlp.factory import build_risk_engine
from risk_engine.nlp.models import RiskSignal, SentimentLabel

_BENCHMARK_AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


class BenchmarkEngine(Protocol):
    def analyze(
        self,
        documents: Sequence[RawDocument],
        *,
        as_of: datetime | None = None,
    ) -> tuple[RiskSignal, ...]: ...


EngineFactory = Callable[[Settings, str], BenchmarkEngine]

_LABEL_ALIASES = {
    "0": SentimentLabel.NEGATIVE,
    "negative": SentimentLabel.NEGATIVE,
    "1": SentimentLabel.NEUTRAL,
    "neutral": SentimentLabel.NEUTRAL,
    "2": SentimentLabel.POSITIVE,
    "positive": SentimentLabel.POSITIVE,
}


class BenchmarkDataError(ValueError):
    """Raised when a user-supplied benchmark CSV violates its contract."""


def _normalize_label(value: str, *, row_number: int) -> SentimentLabel:
    normalized = value.strip().lower()
    try:
        return _LABEL_ALIASES[normalized]
    except KeyError as error:
        supported = ", ".join(_LABEL_ALIASES)
        raise BenchmarkDataError(
            f"row {row_number}: unsupported label {value!r}; expected one of: {supported}"
        ) from error


def _read_csv(
    path: Path, *, text_column: str, label_column: str
) -> tuple[bytes, tuple[BenchmarkExample, ...]]:
    if not path.is_file():
        raise BenchmarkDataError(f"benchmark dataset does not exist or is not a file: {path}")
    if not text_column.strip() or not label_column.strip():
        raise BenchmarkDataError("text and label column names must not be blank")
    if text_column == label_column:
        raise BenchmarkDataError("text and label columns must be different")

    payload = path.read_bytes()
    try:
        decoded = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise BenchmarkDataError("benchmark CSV must use UTF-8 encoding") from error

    try:
        reader = csv.DictReader(io.StringIO(decoded, newline=""))
        if reader.fieldnames is None:
            raise BenchmarkDataError("benchmark CSV must contain a header row")
        duplicated = sorted(
            {column for column in reader.fieldnames if reader.fieldnames.count(column) > 1}
        )
        if duplicated:
            raise BenchmarkDataError(
                "benchmark CSV contains duplicate columns: " + ", ".join(duplicated)
            )
        missing = [
            column for column in (text_column, label_column) if column not in reader.fieldnames
        ]
        if missing:
            raise BenchmarkDataError(
                "benchmark CSV is missing required columns: " + ", ".join(missing)
            )

        examples = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise BenchmarkDataError(
                    f"row {row_number}: contains more values than the header defines"
                )
            text = (row.get(text_column) or "").strip()
            raw_label = row.get(label_column) or ""
            if not text:
                raise BenchmarkDataError(f"row {row_number}: text must not be blank")
            if not raw_label.strip():
                raise BenchmarkDataError(f"row {row_number}: label must not be blank")
            examples.append(
                BenchmarkExample(
                    text=text,
                    label=_normalize_label(raw_label, row_number=row_number),
                )
            )
    except csv.Error as error:
        raise BenchmarkDataError(f"invalid benchmark CSV: {error}") from error

    if not examples:
        raise BenchmarkDataError("benchmark CSV must contain at least one data row")
    return payload, tuple(examples)


def load_csv(path: Path, *, text_column: str, label_column: str) -> tuple[BenchmarkExample, ...]:
    """Load and validate a UTF-8 CSV without silently dropping invalid records."""

    _, examples = _read_csv(path, text_column=text_column, label_column=label_column)
    return examples


def _default_engine_factory(settings: Settings, mode: str) -> BenchmarkEngine:
    return build_risk_engine(settings, mode=mode)


def _benchmark_documents(examples: Sequence[BenchmarkExample]) -> tuple[RawDocument, ...]:
    documents = []
    for index, example in enumerate(examples, start=1):
        content_hash = hashlib.sha256(example.text.encode()).hexdigest()
        document_id = hashlib.sha256(f"{index}\0{example.text}".encode()).hexdigest()[:32]
        url = f"https://financial-phrasebank-benchmark.example/records/{document_id}"
        documents.append(
            RawDocument(
                document_id=document_id,
                text=example.text,
                canonical_url=url,
                content_hash=content_hash,
                normalized_at=_BENCHMARK_AS_OF,
                provenance=Provenance(
                    source="financial-phrasebank-benchmark",
                    source_type=SourceType.NEWS,
                    source_id=f"row-{index}",
                    original_url=url,
                    query="external sentiment benchmark",
                    published_at=_BENCHMARK_AS_OF,
                    retrieved_at=_BENCHMARK_AS_OF,
                    language="en",
                    synthetic=False,
                    metadata={
                        "classification": "external-user-supplied-benchmark",
                        "row_number": index,
                    },
                ),
            )
        )
    return tuple(documents)


def run_benchmark(
    dataset: Path,
    *,
    text_column: str,
    label_column: str,
    settings: Settings | None = None,
    engine_factory: EngineFactory = _default_engine_factory,
) -> BenchmarkReport:
    """Run both explicit modes on the same ordered examples with no fallback."""

    payload, examples = _read_csv(
        dataset,
        text_column=text_column,
        label_column=label_column,
    )
    selected_settings = settings or Settings.from_env()
    actual = [example.label for example in examples]
    documents = _benchmark_documents(examples)
    mode_metrics = []
    for mode in ("deterministic", "model"):
        engine = engine_factory(selected_settings, mode)
        signals = engine.analyze(documents, as_of=_BENCHMARK_AS_OF)
        if len(signals) != len(examples):
            raise ValueError("NLP engine returned a different number of signals than rows")
        predicted = [signal.sentiment.label for signal in signals]
        mode_metrics.append(
            calculate_metrics(
                mode=mode,
                model_version=signals[0].model_versions["sentiment"],
                actual=actual,
                predicted=predicted,
                impact_scores=[signal.impact_score for signal in signals],
                trigger_threshold=selected_settings.stress_trigger_threshold,
            )
        )

    distribution = Counter(label.value for label in actual)
    return BenchmarkReport(
        dataset_filename=dataset.name,
        dataset_sha256=hashlib.sha256(payload).hexdigest(),
        text_column=text_column,
        label_column=label_column,
        row_count=len(examples),
        label_distribution={label.value: distribution[label.value] for label in LABEL_ORDER},
        modes=tuple(mode_metrics),
    )
