"""Tests for environment-backed configuration."""

from __future__ import annotations

import pytest

from risk_engine.config import Settings


def test_settings_use_safe_offline_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RISK_ENGINE_OFFLINE_MODE", raising=False)
    monkeypatch.delenv("RISK_ENGINE_ENVIRONMENT", raising=False)

    settings = Settings.from_env()

    assert settings.environment == "development"
    assert settings.offline_mode is True
    assert settings.database_url.startswith("sqlite:///")


def test_settings_read_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RISK_ENGINE_ENVIRONMENT", "test")
    monkeypatch.setenv("RISK_ENGINE_LOG_LEVEL", "debug")
    monkeypatch.setenv("RISK_ENGINE_OFFLINE_MODE", "no")
    monkeypatch.setenv("RISK_ENGINE_BLUESKY_BEARER_TOKEN", "secret-token")

    settings = Settings.from_env()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.offline_mode is False
    assert settings.bluesky_bearer_token == "secret-token"
    assert settings.public_summary()["bluesky_auth_configured"] is True
    assert "bluesky_bearer_token" not in settings.public_summary()


@pytest.mark.parametrize("value", ["sometimes", "2", "enabled"])
def test_settings_reject_invalid_boolean(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("RISK_ENGINE_OFFLINE_MODE", value)

    with pytest.raises(ValueError, match="RISK_ENGINE_OFFLINE_MODE"):
        Settings.from_env()


def test_settings_reject_insecure_source_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RISK_ENGINE_GDELT_BASE_URL", "http://example.test")

    with pytest.raises(ValueError, match="must use HTTPS"):
        Settings.from_env()
