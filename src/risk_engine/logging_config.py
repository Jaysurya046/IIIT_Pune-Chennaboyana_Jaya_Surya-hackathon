"""Consistent application logging configuration."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: str) -> None:
    """Configure root logging once with an ISO-like timestamp format."""

    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Unsupported log level: {level}")

    logging.basicConfig(
        level=numeric_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        force=True,
    )
