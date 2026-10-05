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


def test_rule_based_sentiment_removes_ambiguous_tokens() -> None:
    result = RuleBasedSentimentAnalyzer().analyze("The fine record was published")

    assert result.label is SentimentLabel.NEUTRAL
    assert result.score == 0.0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Not strong", SentimentLabel.NEGATIVE),
        ("Not not strong", SentimentLabel.POSITIVE),
        ("Not a very good strong", SentimentLabel.POSITIVE),
        ("Not a very strong", SentimentLabel.NEGATIVE),
    ],
)
def test_rule_based_sentiment_uses_an_odd_three_token_negation_window(
    text: str, expected: SentimentLabel
) -> None:
    assert RuleBasedSentimentAnalyzer().analyze(text).label is expected


def test_finbert_adapter_normalizes_injected_model_output() -> None:
    calls: list[list[str]] = []

    def classify(texts: list[str]):
        calls.append(texts)
        return [
            [
                {"label": "positive", "score": 0.7},
                {"label": "neutral", "score": 0.2},
                {"label": "negative", "score": 0.1},
            ]
            for _ in texts
        ]

    analyzer = FinBertSentimentAnalyzer(
        "example/model",
        "revision",
        classifier=classify,
    )

    result = analyzer.analyze("ignored")

    assert result.label is SentimentLabel.POSITIVE
    assert result.score == pytest.approx(0.6)
    assert result.confidence == pytest.approx(0.7)
    assert calls == [["ignored"]]


def test_sentiment_batching_preserves_order_and_uses_one_model_call() -> None:
    calls: list[list[str]] = []

    def classify(texts: list[str]):
        calls.append(texts)
        labels = ("negative", "neutral", "positive")
        return [
            [
                {"label": candidate, "score": 1.0 if candidate == label else 0.0}
                for candidate in labels
            ]
            for label in texts
        ]

    model = FinBertSentimentAnalyzer(
        "example/model",
        "revision",
        classifier=classify,
    )
    deterministic = RuleBasedSentimentAnalyzer()
    texts = ("negative", "neutral", "positive")

    model_results = model.analyze_batch(texts)
    deterministic_results = deterministic.analyze_batch(
        ("Default caused a loss", "Routine timetable", "Strong profit growth")
    )

    assert [result.label.value for result in model_results] == list(texts)
    assert [result.label for result in deterministic_results] == [
        SentimentLabel.NEGATIVE,
        SentimentLabel.NEUTRAL,
        SentimentLabel.POSITIVE,
    ]
    assert calls == [list(texts)]
    assert model.analyze_batch(()) == ()
