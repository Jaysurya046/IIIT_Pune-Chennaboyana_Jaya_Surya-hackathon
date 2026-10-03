"""Typed dashboard HTTP-client tests."""

import httpx
import pytest
from tests.dashboard.helpers import NOW, sample_signal

from risk_engine.api.models import (
    AnalysisResponse,
    HealthResponse,
    IngestionRunResponse,
    PortfolioBreakdown,
    PortfolioSummaryResponse,
    SignalListResponse,
    SourceMode,
    SourceStatusResponse,
    StressTestResponse,
)
from risk_engine.dashboard.client import DashboardApiClient, DashboardApiError
from risk_engine.ingestion.models import SourceRunStatus, SourceType
from risk_engine.nlp.models import EventType
from risk_engine.stress.models import StressDecision


def _response_models() -> dict[str, object]:
    signal = sample_signal()
    source = SourceRunStatus(
        source="gdelt",
        source_type=SourceType.NEWS,
        successful=True,
        fetched_count=1,
        normalized_count=1,
        started_at=NOW,
        completed_at=NOW,
    )
    return {
        "/health": HealthResponse(
            status="ok",
            application="RiskSignal Engine",
            version="0.6.0",
            database="ok",
            offline_mode=True,
        ),
        "/api/v1/sources/status": SourceStatusResponse(
            latest_run_id="c" * 32,
            query="risk",
            completed_at=NOW,
            sources=(source,),
        ),
        "/api/v1/signals": SignalListResponse(
            total=1,
            limit=100,
            offset=0,
            items=(signal,),
        ),
        f"/api/v1/signals/{signal.signal_id}": signal,
        "/api/v1/portfolio/summary": PortfolioSummaryResponse(
            portfolio_id="portfolio",
            portfolio_version="1.0",
            base_currency="USD",
            position_count=1,
            total_market_value="100.00",
            base_expected_loss="1.00",
            by_asset_class=(
                PortfolioBreakdown(key="loan", position_count=1, market_value="100.00"),
            ),
            by_sector=(),
            by_issuer=(),
        ),
    }


def test_reads_validated_dashboard_contracts_and_filter_params() -> None:
    models = _response_models()
    observed_params: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/signals":
            observed_params.update(dict(request.url.params))
        model = models[request.url.path]
        return httpx.Response(200, json=model.model_dump(mode="json"))

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://api.test")
    client = DashboardApiClient("http://api.test", client=http_client)

    assert client.health().version == "0.6.0"
    assert client.source_status().sources[0].successful is True
    assert client.portfolio_summary().total_market_value == 100
    response = client.signals(
        event_type=EventType.CREDIT_EVENT,
        min_impact=8,
        source="gdelt",
        entity_id="northstar-energy",
    )
    assert response.items[0].signal_id == "a" * 32
    assert observed_params == {
        "limit": "100",
        "offset": "0",
        "event_type": "Credit Event",
        "min_impact": "8",
        "source": "gdelt",
        "entity_id": "northstar-energy",
    }
    http_client.close()


def test_runs_ingestion_analysis_and_stress_workflow() -> None:
    signal = sample_signal()
    requests: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read()
        body = __import__("json").loads(payload) if payload else {}
        requests.append((request.url.path, body))
        if request.url.path == "/api/v1/ingestion/run":
            model = IngestionRunResponse(
                run_id="c" * 32,
                query="risk",
                document_count=1,
                successful_source_count=1,
                failed_source_count=0,
                sources=(),
            )
        elif request.url.path == "/api/v1/analyze":
            model = AnalysisResponse(run_id="c" * 32, signal_count=1, signals=(signal,))
        else:
            model = StressTestResponse(
                decision_id="d" * 32,
                decision=StressDecision(
                    signal_id=signal.signal_id,
                    trigger_threshold=7,
                    triggered=False,
                    reason="Impact score did not exceed 7.",
                ),
            )
        return httpx.Response(200, json=model.model_dump(mode="json"))

    http_client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://api.test")
    client = DashboardApiClient("http://api.test", client=http_client)

    ingestion = client.run_ingestion("risk")
    client.run_ingestion("banking stress", source_mode=SourceMode.REPLAY)
    analysis = client.analyze(ingestion.run_id)
    decision = client.run_stress(analysis.signals[0].signal_id)

    assert [path for path, _ in requests] == [
        "/api/v1/ingestion/run",
        "/api/v1/ingestion/run",
        "/api/v1/analyze",
        "/api/v1/stress-tests",
    ]
    assert requests[0][1]["source_mode"] == "fixtures"
    assert requests[1][1]["source_mode"] == "replay"
    assert requests[2][1]["nlp_mode"] == "deterministic"
    assert decision.decision.triggered is False
    http_client.close()


def test_errors_are_sanitized_and_url_validation_rejects_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "secret upstream token abc123"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://api.test")
    client = DashboardApiClient("http://api.test", client=http_client)

    with pytest.raises(DashboardApiError, match="HTTP 500") as captured:
        client.health()
    assert "abc123" not in str(captured.value)
    with pytest.raises(ValueError, match="must not contain credentials"):
        DashboardApiClient("https://user:password@example.org")
    with pytest.raises(ValueError, match="absolute HTTP"):
        DashboardApiClient("localhost:8000")
    http_client.close()
