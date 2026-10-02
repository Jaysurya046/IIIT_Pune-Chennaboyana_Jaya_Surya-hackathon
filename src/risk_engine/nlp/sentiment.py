"""Financial sentiment analyzers with deterministic and FinBERT implementations."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol

from risk_engine.nlp.models import SentimentLabel, SentimentResult


class ModelDependencyError(RuntimeError):
    """Raised when optional model dependencies are unavailable."""


class SentimentAnalyzer(Protocol):
    model_version: str

    def analyze(self, text: str) -> SentimentResult: ...


class RuleBasedSentimentAnalyzer:
    """Small transparent baseline used by offline tests and demonstrations."""

    model_version = "deterministic-sentiment-v1"
    _positive = frozenset(
        {
            "approval",
            "approved",
            "gain",
            "growth",
            "launch",
            "launches",
            "profit",
            "record",
            "strong",
            "upgrade",
        }
    )
    _negative = frozenset(
        {
            "bankruptcy",
            "breach",
            "closure",
            "default",
            "downgrade",
            "fine",
            "loss",
            "missed",
            "outage",
            "penalty",
            "recession",
            "sanctions",
        }
    )

    def analyze(self, text: str) -> SentimentResult:
        tokens = re.findall(r"[a-z]+", text.lower())
        positive = sum(token in self._positive for token in tokens)
        negative = sum(token in self._negative for token in tokens)
        total = positive + negative
        if total == 0 or positive == negative:
            probabilities = {
                SentimentLabel.POSITIVE: 0.1,
                SentimentLabel.NEUTRAL: 0.8,
                SentimentLabel.NEGATIVE: 0.1,
            }
            label = SentimentLabel.NEUTRAL
        else:
            strength = min(0.9, 0.55 + 0.1 * abs(positive - negative))
            remainder = 1.0 - strength
            label = SentimentLabel.POSITIVE if positive > negative else SentimentLabel.NEGATIVE
            opposite = (
                SentimentLabel.NEGATIVE
                if label is SentimentLabel.POSITIVE
                else SentimentLabel.POSITIVE
            )
            probabilities = {
                label: strength,
                SentimentLabel.NEUTRAL: remainder * 0.6,
                opposite: remainder * 0.4,
            }
        score = probabilities[SentimentLabel.POSITIVE] - probabilities[SentimentLabel.NEGATIVE]
        return SentimentResult(
            label=label,
            score=round(score, 6),
            confidence=probabilities[label],
            probabilities=probabilities,
        )


ClassifierOutput = Sequence[Mapping[str, object]] | Sequence[Sequence[Mapping[str, object]]]


class FinBertSentimentAnalyzer:
    """Lazy FinBERT adapter pinned to an immutable model revision."""

    def __init__(
        self,
        model_id: str,
        revision: str,
        *,
        cache_dir: str | None = None,
        classifier: Callable[..., ClassifierOutput] | None = None,
    ) -> None:
        self._model_id = model_id
        self._revision = revision
        self._cache_dir = cache_dir
        self._classifier = classifier
        self.model_version = f"{model_id}@{revision}"

    def _get_classifier(self) -> Callable[..., ClassifierOutput]:
        if self._classifier is None:
            try:
                from transformers import (
                    AutoModelForSequenceClassification,
                    AutoTokenizer,
                    pipeline,
                )
            except ImportError as error:
                raise ModelDependencyError(
                    "FinBERT mode requires the optional NLP dependencies"
                ) from error
            tokenizer = AutoTokenizer.from_pretrained(
                self._model_id,
                revision=self._revision,
                cache_dir=self._cache_dir,
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                self._model_id,
                revision=self._revision,
                cache_dir=self._cache_dir,
            )
            self._classifier = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                top_k=None,
                truncation=True,
            )
        return self._classifier

    def analyze(self, text: str) -> SentimentResult:
        raw = self._get_classifier()(text)
        rows = (
            raw[0]
            if raw and isinstance(raw[0], Sequence) and not isinstance(raw[0], Mapping)
            else raw
        )
        probabilities = {label: 0.0 for label in SentimentLabel}
        for row in rows:
            label = SentimentLabel(str(row["label"]).lower())
            probabilities[label] = float(row["score"])
        predicted = max(probabilities, key=probabilities.__getitem__)
        signed_score = (
            probabilities[SentimentLabel.POSITIVE] - probabilities[SentimentLabel.NEGATIVE]
        )
        return SentimentResult(
            label=predicted,
            score=round(signed_score, 6),
            confidence=probabilities[predicted],
            probabilities=probabilities,
        )
