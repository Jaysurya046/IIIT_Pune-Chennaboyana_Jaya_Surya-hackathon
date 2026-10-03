"""Typed HTTP client used by the Streamlit dashboard."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self, TypeVar
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ValidationError

from risk_engine.api.models import (
    AnalysisResponse,
    HealthResponse,
    IngestionRunResponse,
    PortfolioSummaryResponse,
    SignalListResponse,
    SourceMode,
    SourceStatusResponse,
    StressTestResponse,
    WhatIfStressResponse,
)
from risk_engine.nlp.models import EventType, RiskSignal
from risk_engine.stress.models import StressResult

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class DashboardApiError(RuntimeError):
    """Safe, user-facing failure raised for API transport and contract errors."""


class DashboardApiClient:
    """Small typed client that keeps dashboard code independent of HTTP details."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        normalized = base_url.rstrip("/")
        parts = urlsplit(normalized)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("API URL must be an absolute HTTP or HTTPS URL")
        if parts.username or parts.password:
            raise ValueError("API URL must not contain credentials")
        self.base_url = normalized
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=normalized, timeout=timeout)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        response_model: type[ResponseModel],
        **kwargs: Any,
    ) -> ResponseModel:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise DashboardApiError(
                f"RiskSignal API returned HTTP {error.response.status_code} for {path}."
            ) from None
        except httpx.HTTPError as error:
            raise DashboardApiError(
                f"RiskSignal API request failed for {path} ({type(error).__name__})."
            ) from None

        try:
            return response_model.model_validate_json(response.content)
        except ValidationError:
            raise DashboardApiError(
                f"RiskSignal API returned an invalid response contract for {path}."
            ) from None

    def health(self) -> HealthResponse:
        return self._request("GET", "/health", HealthResponse)

    def source_status(self) -> SourceStatusResponse:
        return self._request("GET", "/api/v1/sources/status", SourceStatusResponse)

    def signals(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        event_type: EventType | None = None,
        min_impact: int | None = None,
        source: str | None = None,
        entity_id: str | None = None,
    ) -> SignalListResponse:
        params = {
            "limit": limit,
            "offset": offset,
            "event_type": event_type.value if event_type else None,
            "min_impact": min_impact,
            "source": source,
            "entity_id": entity_id,
        }
        return self._request(
            "GET",
            "/api/v1/signals",
            SignalListResponse,
            params={key: value for key, value in params.items() if value is not None},
        )

    def signal(self, signal_id: str) -> RiskSignal:
        return self._request("GET", f"/api/v1/signals/{signal_id}", RiskSignal)

    def portfolio_summary(self) -> PortfolioSummaryResponse:
        return self._request("GET", "/api/v1/portfolio/summary", PortfolioSummaryResponse)

    def run_ingestion(
        self,
        query: str,
        *,
        source_mode: SourceMode = SourceMode.FIXTURES,
        limit: int = 25,
    ) -> IngestionRunResponse:
        return self._request(
            "POST",
            "/api/v1/ingestion/run",
            IngestionRunResponse,
            json={"query": query, "source_mode": source_mode.value, "limit": limit},
        )

    def analyze(self, run_id: str, *, nlp_mode: str = "deterministic") -> AnalysisResponse:
        return self._request(
            "POST",
            "/api/v1/analyze",
            AnalysisResponse,
            json={"run_id": run_id, "nlp_mode": nlp_mode},
        )

    def run_stress(self, signal_id: str) -> StressTestResponse:
        return self._request(
            "POST",
            "/api/v1/stress-tests",
            StressTestResponse,
            json={"signal_id": signal_id},
        )

    def run_what_if(
        self,
        event_type: EventType,
        entity_ids: tuple[str, ...],
        impact_score: int,
    ) -> WhatIfStressResponse:
        return self._request(
            "POST",
            "/api/v1/stress-tests/what-if",
            WhatIfStressResponse,
            json={
                "event_type": event_type.value,
                "entity_ids": list(entity_ids),
                "impact_score": impact_score,
            },
        )

    def stress_result(self, result_id: str) -> StressResult:
        return self._request("GET", f"/api/v1/stress-tests/{result_id}", StressResult)
