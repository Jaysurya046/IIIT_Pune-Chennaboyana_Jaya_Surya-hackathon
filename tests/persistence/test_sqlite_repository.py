"""SQLite repository round-trip and filtering tests."""

from pathlib import Path

from risk_engine.config import Settings
from risk_engine.ingestion.adapters import FixtureAdapter
from risk_engine.ingestion.models import IngestionRequest
from risk_engine.ingestion.service import IngestionService
from risk_engine.nlp.factory import build_risk_engine
from risk_engine.persistence import SQLiteStore
from risk_engine.stress.factory import build_stress_engine


def _settings(database: Path) -> Settings:
    return Settings(data_dir=Path("data"), database_url=f"sqlite:///{database.as_posix()}")


def _ingestion_result():
    sample_dir = Path("data/sample")
    return IngestionService(
        [
            FixtureAdapter(sample_dir / "gdelt_articles.json"),
            FixtureAdapter(sample_dir / "bluesky_posts.json"),
        ]
    ).run(IngestionRequest(query="portfolio risk"))


def test_ingestion_and_signal_round_trip_with_filters(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "repository.db")
    store = SQLiteStore(settings.database_url)
    ingestion = store.save_ingestion(_ingestion_result())
    signals = build_risk_engine(settings).analyze(ingestion.result.documents)

    assert store.save_signals(signals) == 6
    restored_run = store.get_ingestion(ingestion.run_id)
    assert restored_run == ingestion
    assert store.latest_ingestion() == ingestion

    first = signals[0]
    assert store.get_signal(first.signal_id) == first
    by_event, event_total = store.list_signals(
        limit=25,
        offset=0,
        event_type=first.event.event_type,
    )
    by_entity, entity_total = store.list_signals(
        limit=25,
        offset=0,
        entity_id=first.entities[0].entity_id,
    )
    high_impact, high_total = store.list_signals(limit=25, offset=0, min_impact=10)

    assert event_total >= 1 and first.signal_id in {item.signal_id for item in by_event}
    assert entity_total >= 1 and first.signal_id in {item.signal_id for item in by_entity}
    assert high_impact == () and high_total == 0
    store.close()


def test_store_is_durable_and_recovers_stress_result(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "durable.db")
    store = SQLiteStore(settings.database_url)
    ingestion = store.save_ingestion(_ingestion_result())
    signal = build_risk_engine(settings).analyze(ingestion.result.documents)[0]
    high_impact_signal = signal.model_copy(update={"impact_score": 8})
    store.save_signals([high_impact_signal])
    decision_record = store.save_stress_decision(
        build_stress_engine(settings).run(high_impact_signal)
    )
    assert decision_record.decision.result is not None
    result_id = decision_record.decision.result.stress_id
    store.close()

    reopened = SQLiteStore(settings.database_url)

    assert reopened.get_ingestion(ingestion.run_id) == ingestion
    assert reopened.get_signal(signal.signal_id) == high_impact_signal
    assert reopened.get_stress_result(result_id) == decision_record.decision.result
    reopened.close()


def test_signal_pagination_is_stable(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "pagination.db")
    store = SQLiteStore(settings.database_url)
    ingestion = store.save_ingestion(_ingestion_result())
    store.save_signals(build_risk_engine(settings).analyze(ingestion.result.documents))

    first_page, total = store.list_signals(limit=2, offset=0)
    second_page, repeated_total = store.list_signals(limit=2, offset=2)

    assert total == repeated_total == 6
    assert len(first_page) == len(second_page) == 2
    assert {item.signal_id for item in first_page}.isdisjoint(
        item.signal_id for item in second_page
    )
    store.close()
