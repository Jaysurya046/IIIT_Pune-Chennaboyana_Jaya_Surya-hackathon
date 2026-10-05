"""Versioned financial event classification."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from risk_engine.nlp.models import EventClassification, EventType
from risk_engine.nlp.sentiment import ModelDependencyError


class EventConfigurationError(ValueError):
    """Raised when the event taxonomy is invalid."""


class _Category(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: EventType
    description: str
    severity_prior: float = Field(ge=0.0, le=1.0)
    keywords: list[str]


class _Taxonomy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    version: str
    categories: list[_Category]


def load_taxonomy(path: Path) -> _Taxonomy:
    try:
        taxonomy = _Taxonomy.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, json.JSONDecodeError) as error:
        raise EventConfigurationError(f"Unable to load event taxonomy: {path}") from error
    expected = set(EventType)
    actual = {category.event_type for category in taxonomy.categories}
    if (
        taxonomy.schema_version != "1.0"
        or actual != expected
        or len(taxonomy.categories) != len(expected)
    ):
        raise EventConfigurationError(
            "Event taxonomy must define every supported event exactly once"
        )
    return taxonomy


class EventClassifier(Protocol):
    model_version: str

    def classify(self, text: str) -> EventClassification: ...

    def severity_prior(self, event_type: EventType) -> float: ...

    def warm_up(self) -> None: ...


class KeywordEventClassifier:
    """Deterministic event baseline with explicit keyword evidence."""

    _INFLECTION_SUFFIXES = ("s", "es", "ed", "ing")

    def __init__(self, taxonomy_path: Path) -> None:
        self._taxonomy = load_taxonomy(taxonomy_path)
        self.model_version = f"deterministic-event-{self._taxonomy.version}"

    def severity_prior(self, event_type: EventType) -> float:
        return next(
            c.severity_prior for c in self._taxonomy.categories if c.event_type is event_type
        )

    @staticmethod
    def _keyword_forms(keyword: str) -> tuple[str, ...]:
        """Return a keyword and bounded singular/plural forms.

        This deliberately handles only common English inflections. It is not a
        stemmer: every match remains explainable as the configured taxonomy
        keyword, and word boundaries prevent substring false positives.
        """

        words = keyword.split()
        final = words[-1]
        forms = [keyword]
        if final.endswith("ies"):
            forms.append(" ".join((*words[:-1], final[:-3] + "y")))
        elif final.endswith("es"):
            forms.append(" ".join((*words[:-1], final[:-2])))
        elif final.endswith("s") and not final.endswith("ss"):
            forms.append(" ".join((*words[:-1], final[:-1])))
        return tuple(dict.fromkeys(forms))

    @classmethod
    def _keyword_pattern(cls, keyword: str) -> str:
        patterns: list[str] = []
        for form in cls._keyword_forms(keyword):
            words = form.split()
            final = re.escape(words[-1])
            suffix = rf"(?:{'|'.join(cls._INFLECTION_SUFFIXES)})?"
            escaped = [re.escape(word) for word in words[:-1]]
            phrase = r"\s+".join((*escaped, final + suffix))
            patterns.append(phrase)
        return rf"(?<!\w)(?:{'|'.join(patterns)})(?!\w)"

    @classmethod
    def _evidence(cls, text: str, category: _Category) -> tuple[str, ...]:
        return tuple(
            keyword
            for keyword in category.keywords
            if re.search(cls._keyword_pattern(keyword), text, re.IGNORECASE)
        )

    def classify(self, text: str) -> EventClassification:
        scored = []
        for index, category in enumerate(self._taxonomy.categories):
            evidence = self._evidence(text, category)
            scored.append((len(evidence), index, category, evidence))
        count, _, category, evidence = max(scored, key=lambda item: (item[0], -item[1]))
        if count == 0:
            category = next(c for c in self._taxonomy.categories if c.event_type is EventType.OTHER)
            return EventClassification(
                event_type=category.event_type,
                confidence=0.6,
                semantic_score=0.0,
                keyword_score=0.0,
            )
        keyword_score = min(1.0, count / 2)
        return EventClassification(
            event_type=category.event_type,
            confidence=min(0.98, 0.65 + 0.15 * count),
            semantic_score=0.0,
            keyword_score=keyword_score,
            evidence=evidence,
        )

    def warm_up(self) -> None:
        """The deterministic implementation has no lazy resources."""


Encoder = Callable[[Sequence[str]], Sequence[Sequence[float]]]


class EmbeddingEventClassifier(KeywordEventClassifier):
    """MiniLM semantic classifier with a bounded keyword evidence boost."""

    def __init__(
        self,
        taxonomy_path: Path,
        model_id: str,
        revision: str,
        *,
        cache_dir: str | None = None,
        encoder: Encoder | None = None,
    ) -> None:
        super().__init__(taxonomy_path)
        self._model_id = model_id
        self._revision = revision
        self._cache_dir = cache_dir
        self._encoder = encoder
        self._category_vectors: tuple[tuple[float, ...], ...] | None = None
        self.model_version = f"{model_id}@{revision}"

    def _get_encoder(self) -> Encoder:
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise ModelDependencyError(
                    "Embedding mode requires the optional NLP dependencies"
                ) from error
            model = SentenceTransformer(
                self._model_id, revision=self._revision, cache_folder=self._cache_dir
            )
            self._encoder = lambda texts: model.encode(
                list(texts),
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return self._encoder

    def _get_category_vectors(self) -> tuple[tuple[float, ...], ...]:
        if self._category_vectors is None:
            descriptions = [category.description for category in self._taxonomy.categories]
            vectors = self._get_encoder()(descriptions)
            if len(vectors) != len(descriptions):
                raise ValueError(
                    "Embedding model returned a different number of category vectors"
                )
            self._category_vectors = tuple(tuple(vector) for vector in vectors)
        return self._category_vectors

    @staticmethod
    def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
        denominator = math.sqrt(sum(v * v for v in left)) * math.sqrt(sum(v * v for v in right))
        return (
            0.0
            if denominator == 0
            else sum(a * b for a, b in zip(left, right, strict=True)) / denominator
        )

    def classify(self, text: str) -> EventClassification:
        category_vectors = self._get_category_vectors()
        text_vectors = self._get_encoder()([text])
        if len(text_vectors) != 1:
            raise ValueError("Embedding model must return exactly one document vector")
        text_vector = text_vectors[0]
        scored: list[tuple[float, _Category, float, tuple[str, ...]]] = []
        for category, vector in zip(self._taxonomy.categories, category_vectors, strict=True):
            semantic = max(0.0, min(1.0, (self._cosine(text_vector, vector) + 1.0) / 2.0))
            evidence = self._evidence(text, category)
            keyword = min(1.0, len(evidence) / 2)
            scored.append((0.8 * semantic + 0.2 * keyword, category, semantic, evidence))
        combined, category, semantic, evidence = max(scored, key=lambda item: item[0])
        return EventClassification(
            event_type=category.event_type,
            confidence=min(1.0, combined),
            semantic_score=semantic,
            keyword_score=min(1.0, len(evidence) / 2),
            evidence=evidence,
        )

    def warm_up(self) -> None:
        """Load the pinned encoder and cache all taxonomy description vectors."""

        self._get_category_vectors()
