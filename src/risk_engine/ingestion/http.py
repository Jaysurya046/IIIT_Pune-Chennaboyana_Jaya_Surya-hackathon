"""Bounded HTTP retry behavior shared by live source adapters."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping

import httpx

from risk_engine.ingestion.adapters.base import SourceAdapterError

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def get_json(
    client: httpx.Client,
    url: str,
    *,
    params: Mapping[str, str | int],
    source_name: str,
    max_attempts: int = 3,
    sleeper: Callable[[float], None] = time.sleep,
) -> object:
    """GET JSON with bounded transient retries and sanitized terminal errors."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = client.get(url, params=params)
            if response.status_code in _RETRYABLE_STATUS_CODES and attempt + 1 < max_attempts:
                sleeper(_retry_delay(response, attempt))
                continue
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            last_error = error
            if isinstance(error, httpx.TransportError) and attempt + 1 < max_attempts:
                sleeper(min(0.25 * (2**attempt), 2.0))
                continue
            break

    error_name = type(last_error).__name__ if last_error is not None else "UnknownError"
    raise SourceAdapterError(f"{source_name} request failed: {error_name}") from last_error


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 2.0)
        except ValueError:
            pass
    return min(0.25 * (2**attempt), 2.0)
