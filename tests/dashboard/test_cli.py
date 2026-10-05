"""Dashboard command construction tests."""

from subprocess import CompletedProcess

import pytest
import uvicorn

from risk_engine import cli
from risk_engine.api import app as api_app
from risk_engine.api.models import SourceMode
from risk_engine.dashboard import app
from risk_engine.nlp.sentiment import ModelDependencyError


class FakeProcess:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.return_code: int | None = None

    def poll(self) -> int | None:
        return self.return_code

    def terminate(self) -> None:
        self.events.append("api-terminate")
        self.return_code = 0

    def wait(self, *, timeout: float) -> int:
        self.events.append(f"api-wait-{timeout}")
        return self.return_code or 0

    def kill(self) -> None:
        self.events.append("api-kill")
        self.return_code = -9


def test_dashboard_module_exposes_streamlit_entrypoint() -> None:
    assert callable(app.main)


def test_dashboard_command_passes_bind_and_api_configuration(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, *, env, check):
        captured.update(command=command, env=env, check=check)
        return CompletedProcess(command, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    code = cli.main(
        [
            "dashboard",
            "--host",
            "0.0.0.0",
            "--port",
            "8600",
            "--api-url",
            "http://api.internal:8000",
        ]
    )

    assert code == 0
    assert captured["check"] is False
    assert captured["env"]["RISK_ENGINE_API_URL"] == "http://api.internal:8000"
    command = captured["command"]
    assert command[1:4] == ["-m", "streamlit", "run"]
    assert command[-6:] == [
        "--server.address",
        "0.0.0.0",
        "--server.port",
        "8600",
        "--browser.gatherUsageStats",
        "false",
    ]


def test_serve_command_passes_explicit_model_warm_up(monkeypatch) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_create_app(settings, *, warm_model_mode):
        captured.update(settings=settings, warm_model_mode=warm_model_mode)
        return sentinel

    def fake_run(app, *, host, port):
        captured.update(app=app, host=host, port=port)

    monkeypatch.setattr(api_app, "create_app", fake_create_app)
    monkeypatch.setattr(uvicorn, "run", fake_run)

    code = cli.main(["serve", "--host", "0.0.0.0", "--port", "8100", "--warm-models"])

    assert code == 0
    assert captured["warm_model_mode"] is True
    assert captured["app"] is sentinel
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 8100


def test_demo_seeds_before_startup_and_cleans_up_api(monkeypatch) -> None:
    events: list[str] = []
    captured: dict[str, object] = {}
    process = FakeProcess(events)

    def available(host: str, port: int, label: str) -> None:
        events.append(f"port-{label}-{host}-{port}")

    def seed(settings, source_mode, nlp_mode):
        events.append(f"seed-{source_mode.value}-{nlp_mode}")
        return 4, 4

    def popen(command, *, env):
        events.append("api-start")
        captured.update(api_command=command, api_env=env)
        return process

    def wait_for_api(started_process, health_url):
        assert started_process is process
        events.append("api-ready")
        captured["health_url"] = health_url

    def run(command, *, env, check):
        events.append("dashboard-run")
        captured.update(dashboard_command=command, dashboard_env=env, check=check)
        return CompletedProcess(command, 0)

    monkeypatch.setattr(cli, "_assert_demo_port_available", available)
    monkeypatch.setattr(cli, "_seed_demo", seed)
    monkeypatch.setattr(cli.subprocess, "Popen", popen)
    monkeypatch.setattr(cli, "_wait_for_demo_api", wait_for_api)
    monkeypatch.setattr(cli.subprocess, "run", run)

    code = cli.main(
        [
            "demo",
            "--host",
            "0.0.0.0",
            "--api-port",
            "8100",
            "--dashboard-port",
            "8600",
            "--no-open-browser",
        ]
    )

    assert code == 0
    assert events == [
        "port-API-0.0.0.0-8100",
        "port-dashboard-0.0.0.0-8600",
        "seed-replay-deterministic",
        "api-start",
        "api-ready",
        "dashboard-run",
        "api-terminate",
        "api-wait-5",
    ]
    assert captured["health_url"] == "http://127.0.0.1:8100/health"
    assert captured["dashboard_env"]["RISK_ENGINE_API_URL"] == "http://127.0.0.1:8100"
    assert captured["dashboard_command"][-4:] == [
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    assert captured["check"] is False


def test_demo_readiness_failure_still_cleans_up_api(monkeypatch, capsys) -> None:
    events: list[str] = []
    process = FakeProcess(events)

    monkeypatch.setattr(cli, "_assert_demo_port_available", lambda *args: None)
    monkeypatch.setattr(cli, "_seed_demo", lambda *args: (4, 4))
    monkeypatch.setattr(cli.subprocess, "Popen", lambda *args, **kwargs: process)

    def fail_readiness(*args) -> None:
        raise cli.DemoCommandError("API readiness failed")

    monkeypatch.setattr(cli, "_wait_for_demo_api", fail_readiness)
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("dashboard must not start"),
    )

    assert cli.main(["demo"]) == 1
    assert events == ["api-terminate", "api-wait-5"]
    assert "API readiness failed" in capsys.readouterr().err


def test_demo_port_conflict_fails_before_seeding(monkeypatch, capsys) -> None:
    def unavailable(host: str, port: int, label: str) -> None:
        raise cli.DemoCommandError(f"{label} port {host}:{port} is unavailable")

    monkeypatch.setattr(cli, "_assert_demo_port_available", unavailable)
    monkeypatch.setattr(
        cli,
        "_seed_demo",
        lambda *args: pytest.fail("port checks must precede seeding"),
    )

    assert cli.main(["demo"]) == 1
    assert "API port 127.0.0.1:8000 is unavailable" in capsys.readouterr().err


def test_demo_model_failure_has_no_mode_fallback(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_assert_demo_port_available", lambda *args: None)

    def unavailable_model(settings, source_mode, nlp_mode):
        assert source_mode is SourceMode.FIXTURES
        assert nlp_mode == "model"
        raise ModelDependencyError("pinned model unavailable")

    monkeypatch.setattr(cli, "_seed_demo", unavailable_model)
    monkeypatch.setattr(
        cli.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("API must not start after seed failure"),
    )

    code = cli.main(["demo", "--source-mode", "fixtures", "--nlp-mode", "model"])

    assert code == 1
    error = capsys.readouterr().err
    assert "ModelDependencyError" in error
    assert "pinned model unavailable" in error


def test_demo_rejects_live_source_mode_without_fallback() -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["demo", "--source-mode", "live"])

    assert error.value.code == 2
