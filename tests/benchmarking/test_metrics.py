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
        impact_scores=[8, 7, 9, 6, 10, 7],
        trigger_threshold=7,
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
    assert metrics.trigger_count == 3
    assert metrics.non_trigger_count == 3
    assert metrics.trigger_rate == 0.5


def test_metrics_reject_empty_or_misaligned_inputs() -> None:
    with pytest.raises(ValueError, match="at least one"):
        calculate_metrics(
            mode="model",
            model_version="test",
            actual=[],
            predicted=[],
            impact_scores=[],
            trigger_threshold=7,
        )

    with pytest.raises(ValueError, match="equal lengths"):
        calculate_metrics(
            mode="model",
            model_version="test",
            actual=[SentimentLabel.NEUTRAL],
            predicted=[],
            impact_scores=[],
            trigger_threshold=7,
        )

    with pytest.raises(ValueError, match="impact scores"):
        calculate_metrics(
            mode="model",
            model_version="test",
            actual=[SentimentLabel.NEUTRAL],
            predicted=[SentimentLabel.NEUTRAL],
            impact_scores=[],
            trigger_threshold=7,
        )
