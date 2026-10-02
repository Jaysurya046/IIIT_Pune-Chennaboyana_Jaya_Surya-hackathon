"""Contract tests for the GDELT news adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from risk_engine.ingestion.adapters.base import SourceAdapterError
from risk_engine.ingestion.adapters.gdelt import GdeltAdapter
from risk_engine.ingestion.models import IngestionRequest, SourceType


def test_gdelt_adapter_maps_article_list_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["query"] == "Northstar Energy"
        assert request.url.params["mode"] == "artlist"
        assert request.url.params["format"] == "json"
        assert request.url.params["timespan"] == "12h"
        return httpx.Response(
            200,
            json={
                "articles": [
                    {
                        "url": "https://news.example/article?utm_source=test",
                        "title": "Northstar Energy spreads widen",
                        "seendate": "20261001T121500Z",
                        "domain": "news.example",
                        "language": "English",
                        "sourcecountry": "United States",
                        "socialimage": "https://news.example/image.jpg",
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = GdeltAdapter("https://api.example/gdelt", client=client)
        records = adapter.fetch(
            IngestionRequest(query="Northstar Energy", limit=10, lookback_hours=12)
        )

    assert len(records) == 1
    record = records[0]
    assert record.source == "gdelt"
    assert record.source_type is SourceType.NEWS
    assert record.text == "Northstar Energy spreads widen"
    assert record.published_at == datetime(2026, 10, 1, 12, 15, tzinfo=UTC)
    assert record.metadata["domain"] == "news.example"
    assert record.synthetic is False


def test_gdelt_adapter_uses_start_datetime_when_supplied() -> None:
    since = datetime(2026, 9, 30, 9, 30, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["startdatetime"] == "20260930093000"
        assert "timespan" not in request.url.params
        return httpx.Response(200, json={"articles": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = GdeltAdapter("https://api.example/gdelt", client=client)
        assert adapter.fetch(IngestionRequest(query="rates", since=since)) == []


def test_gdelt_adapter_rejects_unexpected_response() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"items": []}))
    with httpx.Client(transport=transport) as client:
        adapter = GdeltAdapter("https://api.example/gdelt", client=client)
        with pytest.raises(SourceAdapterError, match="unexpected response shape"):
            adapter.fetch(IngestionRequest(query="credit"))
