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

    def analyze_batch(self, texts: Sequence[str]) -> tuple[SentimentResult, ...]: ...

    def warm_up(self) -> None: ...


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
            "loss",
            "missed",
            "outage",
            "penalty",
            "recession",
            "sanctions",
        }
    )
    _negations = frozenset({"hardly", "never", "no", "not", "without"})
    _negation_window = 3

    def analyze(self, text: str) -> SentimentResult:
        tokens = re.findall(r"[a-z]+", text.lower())
        positive = 0
        negative = 0
        for index, token in enumerate(tokens):
            if token not in self._positive and token not in self._negative:
                continue
            negated = sum(
                candidate in self._negations
                for candidate in tokens[max(0, index - self._negation_window) : index]
            ) % 2 == 1
            is_positive = token in self._positive
            if negated:
                is_positive = not is_positive
            if is_positive:
                positive += 1
            else:
                negative += 1
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

    def analyze_batch(self, texts: Sequence[str]) -> tuple[SentimentResult, ...]:
        """Preserve input order while applying the transparent rules."""

        return tuple(self.analyze(text) for text in texts)

    def warm_up(self) -> None:
        """The deterministic implementation has no lazy resources."""


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

    @staticmethod
    def _normalize(rows: Sequence[Mapping[str, object]]) -> SentimentResult:
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

    def analyze_batch(self, texts: Sequence[str]) -> tuple[SentimentResult, ...]:
        """Classify an ordered text batch with one transformer pipeline call."""

        if not texts:
            return ()
        raw = self._get_classifier()(list(texts))
        if raw and isinstance(raw[0], Mapping):
            batches: Sequence[Sequence[Mapping[str, object]]] = (raw,)
        else:
            batches = raw  # type: ignore[assignment]
        if len(batches) != len(texts):
            raise ValueError(
                "FinBERT returned a different number of predictions than input texts"
            )
        return tuple(self._normalize(rows) for rows in batches)

    def analyze(self, text: str) -> SentimentResult:
        return self.analyze_batch((text,))[0]

    def warm_up(self) -> None:
        """Load the pinned tokenizer and model without running inference."""

        self._get_classifier()
