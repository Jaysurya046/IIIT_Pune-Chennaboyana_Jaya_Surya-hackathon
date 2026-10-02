"""Explicit failure behavior that must not silently degrade or expose payloads."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from risk_engine.ingestion.adapters.base import SourceAdapterError
from risk_engine.ingestion.adapters.fixture import FixtureAdapter
from risk_engine.nlp.events import EmbeddingEventClassifier
from risk_engine.nlp.sentiment import (
    FinBertSentimentAnalyzer,
    ModelDependencyError,
)
from risk_engine.persistence.sqlite import PersistenceConfigurationError, SQLiteStore


def test_invalid_fixture_error_is_bounded_and_does_not_echo_content(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text('{"secret": "must-not-be-echoed"', encoding="utf-8")

    with pytest.raises(SourceAdapterError) as captured:
        FixtureAdapter(fixture)

    assert "JSONDecodeError" in str(captured.value)
    assert "must-not-be-echoed" not in str(captured.value)


def test_model_dependency_failures_do_not_fall_back_to_rules(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "transformers", None)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    sentiment = FinBertSentimentAnalyzer("example/model", "revision")
    events = EmbeddingEventClassifier(
        Path("data/nlp/event_taxonomy.json"),
        "example/embedding",
        "revision",
    )

    with pytest.raises(ModelDependencyError, match="optional NLP dependencies"):
        sentiment.analyze("risk")
    with pytest.raises(ModelDependencyError, match="optional NLP dependencies"):
        events.classify("risk")


def test_incompatible_database_schema_fails_closed(tmp_path: Path) -> None:
    database_path = tmp_path / "future.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    connection.execute("INSERT INTO metadata(key, value) VALUES ('schema_version', '999')")
    connection.commit()
    connection.close()

    with pytest.raises(PersistenceConfigurationError, match="not supported"):
        SQLiteStore(f"sqlite:///{database_path.as_posix()}")
