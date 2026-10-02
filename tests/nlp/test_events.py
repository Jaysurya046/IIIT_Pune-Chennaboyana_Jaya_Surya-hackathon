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


def test_embedding_classifier_accepts_injected_encoder() -> None:
    def encode(texts: list[str]) -> list[list[float]]:
        assert len(texts) == 9
        return [[1.0, 0.0], [1.0, 0.0], *([[0.0, 1.0]] * 7)]

    classifier = EmbeddingEventClassifier(
        TAXONOMY,
        "example/minilm",
        "revision",
        encoder=encode,
    )

    result = classifier.classify("Cross-border risk without a taxonomy keyword")

    assert result.event_type is EventType.GEOPOLITICAL
    assert result.semantic_score == 1.0
