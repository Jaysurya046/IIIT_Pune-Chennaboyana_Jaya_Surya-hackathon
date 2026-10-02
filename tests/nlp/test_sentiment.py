"""Financial sentiment analyzer tests."""

import pytest

from risk_engine.nlp.models import SentimentLabel
from risk_engine.nlp.sentiment import FinBertSentimentAnalyzer, RuleBasedSentimentAnalyzer


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Strong profit growth after approval", SentimentLabel.POSITIVE),
        ("Default and bankruptcy drive a loss", SentimentLabel.NEGATIVE),
        ("The company published its timetable", SentimentLabel.NEUTRAL),
    ],
)
def test_rule_based_sentiment_is_deterministic(text: str, expected: SentimentLabel) -> None:
    result = RuleBasedSentimentAnalyzer().analyze(text)

    assert result.label is expected
    assert sum(result.probabilities.values()) == pytest.approx(1.0)


def test_finbert_adapter_normalizes_injected_model_output() -> None:
    analyzer = FinBertSentimentAnalyzer(
        "example/model",
        "revision",
        classifier=lambda _text: [
            {"label": "positive", "score": 0.7},
            {"label": "neutral", "score": 0.2},
            {"label": "negative", "score": 0.1},
        ],
    )

    result = analyzer.analyze("ignored")

    assert result.label is SentimentLabel.POSITIVE
    assert result.score == pytest.approx(0.6)
    assert result.confidence == pytest.approx(0.7)
