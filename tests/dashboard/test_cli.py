"""Dashboard command construction tests."""

from subprocess import CompletedProcess

from risk_engine import cli
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
