"""Contract tests for the Bluesky social adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from risk_engine.ingestion.adapters.base import SourceAdapterError
from risk_engine.ingestion.adapters.bluesky import BlueskyAdapter
from risk_engine.ingestion.models import IngestionRequest, SourceType


def test_bluesky_adapter_maps_public_post_response() -> None:
    since = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/xrpc/app.bsky.feed.searchPosts"
        assert request.url.params["q"] == "Aurora Bank"
        assert request.url.params["sort"] == "latest"
        assert request.url.params["since"] == "2026-10-01T08:00:00Z"
        return httpx.Response(
            200,
            json={
                "posts": [
                    {
                        "uri": "at://did:plc:abc/app.bsky.feed.post/3xyz",
                        "cid": "bafy-test",
                        "author": {
                            "did": "did:plc:abc",
                            "handle": "analyst.example",
                            "displayName": "Example Analyst",
                        },
                        "record": {
                            "text": "Aurora Bank launched a new trade finance platform.",
                            "createdAt": "2026-10-01T09:00:00Z",
                            "langs": ["en"],
                        },
                        "likeCount": 4,
                        "repostCount": 2,
                        "replyCount": 1,
                        "quoteCount": 0,
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = BlueskyAdapter(
            "https://public.api.example",
            client=client,
            bearer_token="test-token",
        )
        records = adapter.fetch(IngestionRequest(query="Aurora Bank", since=since))

    assert len(records) == 1
    record = records[0]
    assert record.source_type is SourceType.SOCIAL
    assert record.author == "analyst.example"
    assert record.url == "https://bsky.app/profile/analyst.example/post/3xyz"
    assert record.metadata["like_count"] == 4
    assert record.synthetic is False
    assert client.headers["Authorization"] == "Bearer test-token"
    assert adapter.auth_mode == "bearer"


def test_bluesky_adapter_reports_http_failure_without_response_body() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(503, text="internal"))
    with httpx.Client(transport=transport) as client:
        adapter = BlueskyAdapter(
            "https://public.api.example", client=client, max_attempts=1
        )
        with pytest.raises(SourceAdapterError, match="HTTPStatusError") as error:
            adapter.fetch(IngestionRequest(query="risk"))

    assert "internal" not in str(error.value)
    assert "public-unauthenticated" in str(error.value)
