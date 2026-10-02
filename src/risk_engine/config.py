"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import ClassVar

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _read_boolean(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    value = raw_value.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be one of: true, false, 1, 0, yes, no, on, off")


def _read_positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _read_positive_integer(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated settings shared by future application components."""

    ALLOWED_ENVIRONMENTS: ClassVar[frozenset[str]] = frozenset(
        {"development", "test", "production"}
    )
    ALLOWED_LOG_LEVELS: ClassVar[frozenset[str]] = frozenset(
        {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    )
    ALLOWED_NLP_MODES: ClassVar[frozenset[str]] = frozenset({"deterministic", "model"})

    app_name: str = "RiskSignal Engine"
    environment: str = "development"
    log_level: str = "INFO"
    offline_mode: bool = True
    data_dir: Path = Path("data")
    database_url: str = "sqlite:///data/runtime/risksignal.db"
    request_timeout_seconds: float = 10.0
    max_text_length: int = 10_000
    gdelt_base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    bluesky_base_url: str = "https://public.api.bsky.app"
    bluesky_bearer_token: str | None = None
    nlp_mode: str = "deterministic"
    sentiment_model_id: str = "ProsusAI/finbert"
    sentiment_model_revision: str = "4556d13015211d73dccd3fdd39d39232506f3e43"
    event_model_id: str = "sentence-transformers/all-MiniLM-L6-v2"
    event_model_revision: str = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    model_cache_dir: Path = Path(".cache/huggingface")
    stress_trigger_threshold: int = 7

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from documented environment variables."""

        settings = cls(
            environment=os.getenv("RISK_ENGINE_ENVIRONMENT", "development").strip().lower(),
            log_level=os.getenv("RISK_ENGINE_LOG_LEVEL", "INFO").strip().upper(),
            offline_mode=_read_boolean("RISK_ENGINE_OFFLINE_MODE", True),
            data_dir=Path(os.getenv("RISK_ENGINE_DATA_DIR", "data")),
            database_url=os.getenv(
                "RISK_ENGINE_DATABASE_URL", "sqlite:///data/runtime/risksignal.db"
            ).strip(),
            request_timeout_seconds=_read_positive_float(
                "RISK_ENGINE_REQUEST_TIMEOUT_SECONDS", 10.0
            ),
            max_text_length=_read_positive_integer("RISK_ENGINE_MAX_TEXT_LENGTH", 10_000),
            gdelt_base_url=os.getenv(
                "RISK_ENGINE_GDELT_BASE_URL",
                "https://api.gdeltproject.org/api/v2/doc/doc",
            ).strip(),
            bluesky_base_url=os.getenv(
                "RISK_ENGINE_BLUESKY_BASE_URL", "https://public.api.bsky.app"
            ).strip(),
            bluesky_bearer_token=os.getenv("RISK_ENGINE_BLUESKY_BEARER_TOKEN") or None,
            nlp_mode=os.getenv("RISK_ENGINE_NLP_MODE", "deterministic").strip().lower(),
            sentiment_model_id=os.getenv(
                "RISK_ENGINE_SENTIMENT_MODEL_ID", "ProsusAI/finbert"
            ).strip(),
            sentiment_model_revision=os.getenv(
                "RISK_ENGINE_SENTIMENT_MODEL_REVISION",
                "4556d13015211d73dccd3fdd39d39232506f3e43",
            ).strip(),
            event_model_id=os.getenv(
                "RISK_ENGINE_EVENT_MODEL_ID",
                "sentence-transformers/all-MiniLM-L6-v2",
            ).strip(),
            event_model_revision=os.getenv(
                "RISK_ENGINE_EVENT_MODEL_REVISION",
                "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            ).strip(),
            model_cache_dir=Path(os.getenv("RISK_ENGINE_MODEL_CACHE_DIR", ".cache/huggingface")),
            stress_trigger_threshold=_read_positive_integer(
                "RISK_ENGINE_STRESS_TRIGGER_THRESHOLD", 7
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Reject invalid configuration before services start."""

        if self.environment not in self.ALLOWED_ENVIRONMENTS:
            allowed = ", ".join(sorted(self.ALLOWED_ENVIRONMENTS))
            raise ValueError(f"RISK_ENGINE_ENVIRONMENT must be one of: {allowed}")
        if self.log_level not in self.ALLOWED_LOG_LEVELS:
            allowed = ", ".join(sorted(self.ALLOWED_LOG_LEVELS))
            raise ValueError(f"RISK_ENGINE_LOG_LEVEL must be one of: {allowed}")
        if self.nlp_mode not in self.ALLOWED_NLP_MODES:
            allowed = ", ".join(sorted(self.ALLOWED_NLP_MODES))
            raise ValueError(f"RISK_ENGINE_NLP_MODE must be one of: {allowed}")
        if self.stress_trigger_threshold > 9:
            raise ValueError("RISK_ENGINE_STRESS_TRIGGER_THRESHOLD must be between 1 and 9")
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("RISK_ENGINE_DATABASE_URL must use the sqlite:/// scheme")
        if not self.gdelt_base_url.startswith("https://"):
            raise ValueError("RISK_ENGINE_GDELT_BASE_URL must use HTTPS")
        if not self.bluesky_base_url.startswith("https://"):
            raise ValueError("RISK_ENGINE_BLUESKY_BASE_URL must use HTTPS")

    def public_summary(self) -> dict[str, object]:
        """Return settings safe to display in diagnostics."""

        summary = asdict(self)
        summary["data_dir"] = str(self.data_dir)
        summary["model_cache_dir"] = str(self.model_cache_dir)
        token = summary.pop("bluesky_bearer_token")
        summary["bluesky_auth_configured"] = bool(token)
        return summary
