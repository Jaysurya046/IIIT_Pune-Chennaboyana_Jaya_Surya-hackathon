"""Dashboard command construction tests."""

from subprocess import CompletedProcess

import uvicorn

from risk_engine import cli
from risk_engine.api import app as api_app
from risk_engine.dashboard import app


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
