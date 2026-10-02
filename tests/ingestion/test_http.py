"""Tests for bounded and sanitized live-source retry behavior."""

from __future__ import annotations

import httpx

from risk_engine.ingestion.http import get_json


def test_get_json_retries_rate_limit_then_returns_payload() -> None:
    request_count = 0
    delays: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"items": ["ok"]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        payload = get_json(
            client,
            "https://api.example/items",
            params={"q": "risk"},
            source_name="Example",
            sleeper=delays.append,
        )

    assert payload == {"items": ["ok"]}
    assert request_count == 2
    assert delays == [1.0]
