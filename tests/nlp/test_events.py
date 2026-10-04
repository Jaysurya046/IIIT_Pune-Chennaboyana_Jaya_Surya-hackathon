"""Financial event classifier tests."""

from pathlib import Path

from risk_engine.nlp.events import EmbeddingEventClassifier, KeywordEventClassifier
from risk_engine.nlp.models import EventType

TAXONOMY = Path("data/nlp/event_taxonomy.json")


def test_keyword_classifier_retains_evidence() -> None:
    classifier = KeywordEventClassifier(TAXONOMY)

    result = classifier.classify("A regulator opened an investigation and imposed a fine.")

    assert result.event_type is EventType.REGULATORY
    assert result.keyword_score == 1.0
    assert set(result.evidence) == {"regulator", "investigation", "fine"}


def test_keyword_classifier_has_explicit_other_fallback() -> None:
    result = KeywordEventClassifier(TAXONOMY).classify("Routine statement with no category cue.")

    assert result.event_type is EventType.OTHER
    assert result.evidence == ()


def test_embedding_classifier_caches_categories_and_encodes_one_text_at_a_time() -> None:
    calls: list[tuple[str, ...]] = []

    def encode(texts: list[str]) -> list[list[float]]:
        calls.append(tuple(texts))
        if len(texts) == 8:
            return [[1.0, 0.0], *([[0.0, 1.0]] * 7)]
        return [[1.0, 0.0]]

    classifier = EmbeddingEventClassifier(
        TAXONOMY,
        "example/minilm",
        "revision",
        encoder=encode,
    )

    first = classifier.classify("Cross-border risk without a taxonomy keyword")
    second = classifier.classify("Another cross-border concern")

    assert first.event_type is EventType.GEOPOLITICAL
    assert first.semantic_score == 1.0
    assert second.event_type is EventType.GEOPOLITICAL
    assert [len(texts) for texts in calls] == [8, 1, 1]


def test_embedding_warm_up_populates_category_cache_without_document_inference() -> None:
    calls: list[tuple[str, ...]] = []

    def encode(texts: list[str]) -> list[list[float]]:
        calls.append(tuple(texts))
        return [[1.0, 0.0] for _ in texts]

    classifier = EmbeddingEventClassifier(
        TAXONOMY,
        "example/minilm",
        "revision",
        encoder=encode,
    )

    classifier.warm_up()
    classifier.warm_up()

    assert [len(texts) for texts in calls] == [8]
