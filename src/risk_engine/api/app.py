"""FastAPI application factory for the versioned RiskSignal HTTP API."""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, status

from risk_engine import __version__
from risk_engine.api.models import (
    AnalysisRequest,
    AnalysisResponse,
    HealthResponse,
    IngestionRunRequest,
    IngestionRunResponse,
    PortfolioSummaryResponse,
    SignalListResponse,
    SourceStatusResponse,
    StressTestRequest,
    StressTestResponse,
    WhatIfStressRequest,
    WhatIfStressResponse,
)
from risk_engine.api.service import (
    LiveModeDisabledError,
    RiskApplicationService,
    UnknownPortfolioEntityError,
)
from risk_engine.config import Settings
from risk_engine.nlp.models import EventType, RiskSignal
from risk_engine.persistence.sqlite import SQLiteStore
from risk_engine.stress.models import StressResult


def create_app(
    settings: Settings | None = None,
    *,
    store: SQLiteStore | None = None,
    warm_model_mode: bool = False,
) -> FastAPI:
    """Build an application with injectable settings and storage for deterministic tests."""

    configured = settings or Settings.from_env()
    repository = store or SQLiteStore(configured.database_url)
    service = RiskApplicationService(configured, repository)
    if warm_model_mode:
        service.warm_up_model_mode()
    app = FastAPI(
        title="RiskSignal Engine API",
        version=__version__,
        description="Versioned API for explainable risk signals and portfolio stress tests.",
    )
    app.state.settings = configured
    app.state.store = repository
    app.state.service = service

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        repository.ping()
        return HealthResponse(
            status="ok",
            application=configured.app_name,
            version=__version__,
            database="ok",
            offline_mode=configured.offline_mode,
        )

    @app.get(
        "/api/v1/sources/status",
        response_model=SourceStatusResponse,
        tags=["ingestion"],
    )
    def source_status() -> SourceStatusResponse:
        return service.source_status()

    @app.post(
        "/api/v1/ingestion/run",
        response_model=IngestionRunResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["ingestion"],
    )
    def run_ingestion(request: IngestionRunRequest) -> IngestionRunResponse:
        try:
            return service.ingest(request)
        except LiveModeDisabledError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    @app.post(
        "/api/v1/analyze",
        response_model=AnalysisResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["signals"],
    )
    def analyze(request: AnalysisRequest) -> AnalysisResponse:
        response = service.analyze(request.run_id, request.nlp_mode)
        if response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion run not found"
            )
        return response

    @app.get("/api/v1/signals", response_model=SignalListResponse, tags=["signals"])
    def list_signals(
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
        offset: Annotated[int, Query(ge=0)] = 0,
        event_type: EventType | None = None,
        min_impact: Annotated[int | None, Query(ge=1, le=10)] = None,
        source: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
        entity_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    ) -> SignalListResponse:
        items, total = repository.list_signals(
            limit=limit,
            offset=offset,
            event_type=event_type,
            min_impact=min_impact,
            source=source,
            entity_id=entity_id,
        )
        return SignalListResponse(total=total, limit=limit, offset=offset, items=items)

    @app.get(
        "/api/v1/signals/{signal_id}",
        response_model=RiskSignal,
        tags=["signals"],
    )
    def get_signal(signal_id: str) -> RiskSignal:
        signal = repository.get_signal(signal_id)
        if signal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Risk signal not found"
            )
        return signal

    @app.post(
        "/api/v1/stress-tests",
        response_model=StressTestResponse,
        tags=["stress"],
    )
    def run_stress_test(request: StressTestRequest) -> StressTestResponse:
        response = service.stress(request.signal_id)
        if response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Risk signal not found"
            )
        return response

    @app.post(
        "/api/v1/stress-tests/what-if",
        response_model=WhatIfStressResponse,
        tags=["stress"],
    )
    def run_what_if(request: WhatIfStressRequest) -> WhatIfStressResponse:
        try:
            return service.what_if(request)
        except UnknownPortfolioEntityError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error

    @app.get(
        "/api/v1/stress-tests/{result_id}",
        response_model=StressResult,
        tags=["stress"],
    )
    def get_stress_result(result_id: str) -> StressResult:
        result = repository.get_stress_result(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stress result not found"
            )
        return result

    @app.get(
        "/api/v1/portfolio/summary",
        response_model=PortfolioSummaryResponse,
        tags=["portfolio"],
    )
    def portfolio_summary() -> PortfolioSummaryResponse:
        return service.portfolio_summary()

    return app
