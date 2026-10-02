"""Synthetic golden-set regression tests for the deterministic NLP path."""

import json
from pathlib import Path

from risk_engine.nlp.entity import IssuerResolver
from risk_engine.nlp.events import KeywordEventClassifier
from risk_engine.nlp.models import EventType, SentimentLabel
from risk_engine.nlp.sentiment import RuleBasedSentimentAnalyzer


def test_golden_cases_cover_taxonomy_and_expected_outputs() -> None:
    payload = json.loads(Path("data/evaluation/nlp_golden.json").read_text(encoding="utf-8"))
    resolver = IssuerResolver(Path("data/nlp/issuer_watchlist.json"))
    events = KeywordEventClassifier(Path("data/nlp/event_taxonomy.json"))
    sentiment = RuleBasedSentimentAnalyzer()

    assert payload["synthetic"] is True
    assert {case["expected_event"] for case in payload["cases"]} == set(EventType)
    for case in payload["cases"]:
        entity_ids = {match.entity_id for match in resolver.resolve(case["text"])}
        assert events.classify(case["text"]).event_type is EventType(case["expected_event"])
        assert sentiment.analyze(case["text"]).label is SentimentLabel(
            case["expected_sentiment"]
        )
        assert entity_ids == set(case["expected_entities"])
