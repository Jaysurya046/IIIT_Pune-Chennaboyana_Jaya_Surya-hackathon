from __future__ import annotations

import pytest

from risk_engine.benchmarking.models import calculate_metrics
from risk_engine.nlp.models import SentimentLabel


def test_metrics_include_deterministic_confusion_counts_and_macro_f1() -> None:
    negative = SentimentLabel.NEGATIVE
    neutral = SentimentLabel.NEUTRAL
    positive = SentimentLabel.POSITIVE

    metrics = calculate_metrics(
        mode="deterministic",
        model_version="test-v1",
        actual=[negative, negative, neutral, positive, positive, positive],
        predicted=[negative, neutral, neutral, positive, negative, positive],
    )

    assert metrics.accuracy == 0.666667
    assert metrics.macro_f1 == 0.655556
    assert metrics.per_class_f1 == {
        "negative": 0.5,
        "neutral": 0.666667,
        "positive": 0.8,
    }
    assert metrics.confusion_matrix == {
        "negative": {"negative": 1, "neutral": 1, "positive": 0},
        "neutral": {"negative": 0, "neutral": 1, "positive": 0},
        "positive": {"negative": 1, "neutral": 0, "positive": 2},
    }


def test_metrics_reject_empty_or_misaligned_inputs() -> None:
    with pytest.raises(ValueError, match="at least one"):
        calculate_metrics(mode="model", model_version="test", actual=[], predicted=[])

    with pytest.raises(ValueError, match="equal lengths"):
        calculate_metrics(
            mode="model",
            model_version="test",
            actual=[SentimentLabel.NEUTRAL],
            predicted=[],
        )
