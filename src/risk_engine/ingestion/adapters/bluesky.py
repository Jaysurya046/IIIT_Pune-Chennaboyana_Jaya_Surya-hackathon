"""Bluesky public AppView adapter for social posts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from risk_engine import __version__
from risk_engine.ingestion.adapters.base import SourceAdapterError
from risk_engine.ingestion.http import get_json
from risk_engine.ingestion.models import IngestionRequest, SourceRecord, SourceType
from risk_engine.ingestion.time import parse_source_datetime, utc_now


class BlueskyAdapter:
    """Retrieve public posts through `app.bsky.feed.searchPosts`."""

    name = "bluesky"
    source_type = SourceType.SOCIAL
    _SEARCH_PATH = "/xrpc/app.bsky.feed.searchPosts"

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        client: httpx.Client | None = None,
        bearer_token: str | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        headers = {"User-Agent": f"RiskSignalEngine/{__version__}"}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers=headers,
        )
        if client is not None and bearer_token:
            self._client.headers["Authorization"] = f"Bearer {bearer_token}"
        self._max_attempts = max_attempts

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch(self, request: IngestionRequest) -> list[SourceRecord]:
        retrieved_at = utc_now()
        since = request.since or retrieved_at.replace(microsecond=0) - timedelta(
            hours=request.lookback_hours
        )
        params: dict[str, str | int] = {
            "q": request.query,
            "sort": "latest",
            "limit": request.limit,
            "since": since.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        }

        payload = get_json(
            self._client,
            f"{self._base_url}{self._SEARCH_PATH}",
            params=params,
            source_name="Bluesky",
            max_attempts=self._max_attempts,
        )

        if not isinstance(payload, dict) or not isinstance(payload.get("posts"), list):
            raise SourceAdapterError("Bluesky returned an unexpected response shape")

        records: list[SourceRecord] = []
        for post in payload["posts"]:
            record = self._parse_post(post, request.query, retrieved_at)
            if record is not None:
                records.append(record)
        return records

    @staticmethod
    def _parse_post(
        post: object, query: str, retrieved_at: datetime
    ) -> SourceRecord | None:
        if not isinstance(post, dict):
            return None

        uri = post.get("uri")
        record_data = post.get("record")
        author_data = post.get("author")
        if not isinstance(uri, str) or not isinstance(record_data, dict):
            return None
        if not isinstance(author_data, dict):
            author_data = {}

        text = record_data.get("text")
        handle = author_data.get("handle")
        if not isinstance(text, str) or not text.strip():
            return None
        if not isinstance(handle, str) or not handle.strip():
            return None

        try:
            published_at = parse_source_datetime(
                record_data.get("createdAt") or post.get("indexedAt")
            )
            return SourceRecord(
                source="bluesky",
                source_type=SourceType.SOCIAL,
                source_id=uri,
                text=text,
                url=_public_post_url(handle, uri),
                published_at=published_at,
                retrieved_at=retrieved_at,
                author=handle,
                language=_first_language(record_data.get("langs")),
                query=query,
                synthetic=False,
                metadata={
                    "cid": _json_scalar(post.get("cid")),
                    "author_did": _json_scalar(author_data.get("did")),
                    "author_display_name": _json_scalar(author_data.get("displayName")),
                    "reply_count": _json_scalar(post.get("replyCount")),
                    "repost_count": _json_scalar(post.get("repostCount")),
                    "like_count": _json_scalar(post.get("likeCount")),
                    "quote_count": _json_scalar(post.get("quoteCount")),
                },
            )
        except (TypeError, ValueError):
            return None


def _public_post_url(handle: str, uri: str) -> str:
    record_key = uri.rsplit("/", maxsplit=1)[-1]
    return f"https://bsky.app/profile/{handle}/post/{record_key}"


def _first_language(value: object) -> str:
    if isinstance(value, list) and value and isinstance(value[0], str):
        return value[0].lower()
    return "und"


def _json_scalar(value: object) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
