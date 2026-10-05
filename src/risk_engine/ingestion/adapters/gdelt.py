"""GDELT DOC API adapter for recent news headlines and metadata."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from time import sleep

import httpx

from risk_engine import __version__
from risk_engine.ingestion.adapters.base import SourceAdapterError
from risk_engine.ingestion.http import get_json
from risk_engine.ingestion.models import IngestionRequest, SourceRecord, SourceType
from risk_engine.ingestion.time import parse_source_datetime, utc_now


class GdeltAdapter:
    """Retrieve article-list results from the public GDELT DOC API."""

    name = "gdelt"
    source_type = SourceType.NEWS

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        client: httpx.Client | None = None,
        max_attempts: int = 3,
        request_spacing_seconds: float = 0.0,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self._base_url = base_url
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": f"RiskSignalEngine/{__version__}"},
        )
        self._max_attempts = max_attempts
        if request_spacing_seconds < 0:
            raise ValueError("request_spacing_seconds must not be negative")
        self._request_spacing_seconds = request_spacing_seconds
        self._sleeper = sleeper

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch(self, request: IngestionRequest) -> list[SourceRecord]:
        retrieved_at = utc_now()
        if self._request_spacing_seconds:
            self._sleeper(self._request_spacing_seconds)
        params: dict[str, str | int] = {
            "query": request.query,
            "mode": "artlist",
            "format": "json",
            "sort": "datedesc",
            "maxrecords": request.limit,
        }
        if request.since is None:
            params["timespan"] = f"{request.lookback_hours}h"
        else:
            params["startdatetime"] = request.since.strftime("%Y%m%d%H%M%S")

        payload = get_json(
            self._client,
            self._base_url,
            params=params,
            source_name="GDELT",
            max_attempts=self._max_attempts,
        )

        if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
            raise SourceAdapterError("GDELT returned an unexpected response shape")

        records: list[SourceRecord] = []
        for article in payload["articles"]:
            record = self._parse_article(article, request.query, retrieved_at)
            if record is not None:
                records.append(record)
        return records

    @staticmethod
    def _parse_article(
        article: object,
        query: str,
        retrieved_at: datetime,
    ) -> SourceRecord | None:
        if not isinstance(article, dict):
            return None

        title = article.get("title")
        url = article.get("url")
        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(url, str) or not url.strip():
            return None

        try:
            published_at = parse_source_datetime(article.get("seendate"))
            return SourceRecord(
                source="gdelt",
                source_type=SourceType.NEWS,
                source_id=url,
                title=title,
                text=title,
                url=url,
                published_at=published_at,
                retrieved_at=retrieved_at,
                language=str(article.get("language") or "und").lower(),
                query=query,
                synthetic=False,
                metadata={
                    "domain": _json_scalar(article.get("domain")),
                    "source_country": _json_scalar(article.get("sourcecountry")),
                    "image_url": _json_scalar(article.get("socialimage")),
                },
            )
        except (TypeError, ValueError):
            return None


def _json_scalar(value: object) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
