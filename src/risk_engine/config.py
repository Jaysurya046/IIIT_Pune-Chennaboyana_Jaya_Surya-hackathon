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


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated settings shared by future application components."""

    ALLOWED_ENVIRONMENTS: ClassVar[frozenset[str]] = frozenset(
        {"development", "test", "production"}
    )
    ALLOWED_LOG_LEVELS: ClassVar[frozenset[str]] = frozenset(
        {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    )

    app_name: str = "RiskSignal Engine"
    environment: str = "development"
    log_level: str = "INFO"
    offline_mode: bool = True
    data_dir: Path = Path("data")
    database_url: str = "sqlite:///data/runtime/risksignal.db"
    gdelt_base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    bluesky_base_url: str = "https://public.api.bsky.app"

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
            gdelt_base_url=os.getenv(
                "RISK_ENGINE_GDELT_BASE_URL",
                "https://api.gdeltproject.org/api/v2/doc/doc",
            ).strip(),
            bluesky_base_url=os.getenv(
                "RISK_ENGINE_BLUESKY_BASE_URL", "https://public.api.bsky.app"
            ).strip(),
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
        if not self.database_url:
            raise ValueError("RISK_ENGINE_DATABASE_URL must not be empty")
        if not self.gdelt_base_url.startswith("https://"):
            raise ValueError("RISK_ENGINE_GDELT_BASE_URL must use HTTPS")
        if not self.bluesky_base_url.startswith("https://"):
            raise ValueError("RISK_ENGINE_BLUESKY_BASE_URL must use HTTPS")

    def public_summary(self) -> dict[str, object]:
        """Return settings safe to display in diagnostics."""

        summary = asdict(self)
        summary["data_dir"] = str(self.data_dir)
        return summary
