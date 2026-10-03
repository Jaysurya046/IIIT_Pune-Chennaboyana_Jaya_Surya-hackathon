"""Contract tests for the versioned offline FastAPI workflow."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from risk_engine.api.app import create_app
from risk_engine.config import Settings
from risk_engine.persistence import SQLiteStore


@pytest.fixture
def api_client(tmp_path: Path):
    settings = Settings(
        environment="test",
        data_dir=Path("data"),
        database_url=f"sqlite:///{(tmp_path / 'api.db').as_posix()}",
    )
    store = SQLiteStore(settings.database_url)
    app = create_app(settings, store=store)
    with TestClient(app) as client:
        yield client, store
    store.close()


def _ingest_and_analyze(client: TestClient) -> dict[str, object]:
    ingestion = client.post(
        "/api/v1/ingestion/run",
        json={"query": "portfolio risk", "source_mode": "fixtures"},
    )
    assert ingestion.status_code == 201
    analysis = client.post(
        "/api/v1/analyze",
        json={"run_id": ingestion.json()["run_id"], "nlp_mode": "deterministic"},
    )
    assert analysis.status_code == 201
    return analysis.json()


def test_health_empty_status_and_openapi_contract(api_client) -> None:
    client, _ = api_client

    health = client.get("/health")
    sources = client.get("/api/v1/sources/status")
    schema = client.get("/openapi.json").json()

    assert health.status_code == 200
    assert health.json()["version"] == "0.8.0"
    assert health.json()["database"] == "ok"
    assert sources.json()["latest_run_id"] is None
    expected_paths = {
        "/health",
        "/api/v1/sources/status",
        "/api/v1/ingestion/run",
        "/api/v1/analyze",
        "/api/v1/signals",
        "/api/v1/signals/{signal_id}",
        "/api/v1/stress-tests",
        "/api/v1/stress-tests/{result_id}",
        "/api/v1/portfolio/summary",
    }
    assert expected_paths.issubset(schema["paths"])


def test_offline_ingestion_analysis_and_signal_queries(api_client) -> None:
    client, _ = api_client
    analysis = _ingest_and_analyze(client)

    assert analysis["signal_count"] == 6
    expected_as_of = datetime(2026, 10, 1, tzinfo=UTC)
    assert all(
        datetime.fromisoformat(signal["created_at"].replace("Z", "+00:00")) == expected_as_of
        for signal in analysis["signals"]
    )
    signal = analysis["signals"][0]
    listing = client.get(
        "/api/v1/signals",
        params={"source": signal["provenance"]["source"], "entity_id": "northstar-energy"},
    )
    detail = client.get(f"/api/v1/signals/{signal['signal_id']}")
    sources = client.get("/api/v1/sources/status")

    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
    assert detail.status_code == 200
    assert detail.json() == signal
    assert sources.json()["latest_run_id"] is not None
    assert {item["source"] for item in sources.json()["sources"]} == {"gdelt", "bluesky"}


def test_stress_decision_and_persisted_result(api_client) -> None:
    client, store = api_client
    analysis = _ingest_and_analyze(client)
    signal_id = analysis["signals"][0]["signal_id"]

    skipped = client.post("/api/v1/stress-tests", json={"signal_id": signal_id})
    assert skipped.status_code == 200
    assert skipped.json()["decision"]["triggered"] is False

    signal = store.get_signal(signal_id)
    assert signal is not None
    store.save_signals([signal.model_copy(update={"impact_score": 8})])
    triggered = client.post("/api/v1/stress-tests", json={"signal_id": signal_id})
    payload = triggered.json()

    assert triggered.status_code == 200
    assert payload["decision"]["triggered"] is True
    result_id = payload["decision"]["result"]["stress_id"]
    restored = client.get(f"/api/v1/stress-tests/{result_id}")
    assert restored.status_code == 200
    assert restored.json()["stress_id"] == result_id
    assert restored.json()["reconciliation_difference"] == "0.00"


def test_replay_organically_triggers_and_persists_stress_result(api_client) -> None:
    client, store = api_client
    ingestion = client.post(
        "/api/v1/ingestion/run",
        json={"query": "banking stress", "source_mode": "replay"},
    )

    assert ingestion.status_code == 201
    assert ingestion.json()["document_count"] == 4
    assert {item["source"] for item in ingestion.json()["sources"]} == {
        "replay-news",
        "replay-social",
    }

    analysis = client.post(
        "/api/v1/analyze",
        json={"run_id": ingestion.json()["run_id"], "nlp_mode": "deterministic"},
    )
    signals = analysis.json()["signals"]

    assert analysis.status_code == 201
    assert [signal["impact_score"] for signal in signals] == [9, 9, 9, 9]
    assert all(signal["entities"][0]["entity_id"] == "aurora-bank" for signal in signals)
    persisted = store.get_signal(signals[0]["signal_id"])
    assert persisted is not None and persisted.impact_score == 9

    stress = client.post(
        "/api/v1/stress-tests",
        json={"signal_id": signals[0]["signal_id"]},
    )
    payload = stress.json()

    assert stress.status_code == 200
    assert payload["decision"]["triggered"] is True
    assert payload["decision"]["result"]["trigger_impact_score"] == 9
    assert payload["decision"]["result"]["affected_scope"] == ["aurora-bank"]
    result_id = payload["decision"]["result"]["stress_id"]
    assert client.get(f"/api/v1/stress-tests/{result_id}").status_code == 200


def test_portfolio_summary_reconciles_breakdowns(api_client) -> None:
    client, _ = api_client

    response = client.get("/api/v1/portfolio/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["position_count"] == 8
    assert payload["total_market_value"] == "55500000.00"
    assert len(payload["by_asset_class"]) == 4
    assert sum(float(item["market_value"]) for item in payload["by_asset_class"]) == pytest.approx(
        55_500_000
    )


def test_api_validation_not_found_and_offline_live_guard(api_client) -> None:
    client, _ = api_client

    invalid = client.post("/api/v1/ingestion/run", json={"query": "", "limit": 0})
    live = client.post(
        "/api/v1/ingestion/run",
        json={"query": "risk", "source_mode": "live"},
    )
    missing_run = client.post("/api/v1/analyze", json={"run_id": "a" * 32})
    missing_signal = client.get(f"/api/v1/signals/{'b' * 32}")
    missing_result = client.get(f"/api/v1/stress-tests/{'c' * 32}")

    assert invalid.status_code == 422
    assert live.status_code == 409
    assert missing_run.status_code == 404
    assert missing_signal.status_code == 404
    assert missing_result.status_code == 404
