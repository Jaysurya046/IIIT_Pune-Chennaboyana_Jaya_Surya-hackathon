"""Timestamp helpers for heterogeneous external source formats."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def parse_source_datetime(value: object) -> datetime:
    """Parse ISO-8601 and GDELT compact timestamps as UTC."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is missing")

    timestamp = value.strip()
    for pattern in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(timestamp, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"unsupported timestamp: {timestamp}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)
