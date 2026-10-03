"""Rendered dashboard validation against a real local API workflow."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from streamlit.testing.v1 import AppTest

from risk_engine.api.app import create_app
from risk_engine.config import Settings
from risk_engine.persistence import SQLiteStore


def _available_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def test_dashboard_replay_trigger_filter_and_reset_states(tmp_path: Path, monkeypatch) -> None:
    port = _available_port()
    settings = Settings(
        environment="test",
        data_dir=Path("data"),
        database_url=f"sqlite:///{(tmp_path / 'dashboard.db').as_posix()}",
    )
    store = SQLiteStore(settings.database_url)
    application = create_app(settings, store=store)
    server = uvicorn.Server(
        uvicorn.Config(application, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{base_url}/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.05)
        else:
            raise AssertionError("Validation API did not become ready")

        ingestion = httpx.post(
            f"{base_url}/api/v1/ingestion/run",
            json={"query": "portfolio risk", "source_mode": "fixtures"},
            timeout=5,
        )
        ingestion.raise_for_status()
        analysis = httpx.post(
            f"{base_url}/api/v1/analyze",
            json={
                "run_id": ingestion.json()["run_id"],
                "nlp_mode": "deterministic",
            },
            timeout=5,
        )
        analysis.raise_for_status()
        replay_ingestion = httpx.post(
            f"{base_url}/api/v1/ingestion/run",
            json={"query": "banking stress", "source_mode": "replay"},
            timeout=5,
        )
        replay_ingestion.raise_for_status()
        replay_analysis = httpx.post(
            f"{base_url}/api/v1/analyze",
            json={
                "run_id": replay_ingestion.json()["run_id"],
                "nlp_mode": "deterministic",
            },
            timeout=5,
        )
        replay_analysis.raise_for_status()
        monkeypatch.setenv("RISK_ENGINE_API_URL", base_url)

        dashboard = AppTest.from_file(Path("src/risk_engine/dashboard/app.py").resolve()).run(
            timeout=30
        )

        assert not dashboard.exception
        assert dashboard.title[0].value == "RiskSignal Monitor"
        assert [tab.label for tab in dashboard.tabs] == [
            "Risk signals",
            "Stress lab",
            "Source health",
        ]
        assert dashboard.metric[0].label == "Matching signals"
        assert dashboard.metric[0].value == "10"
        assert len(dashboard.dataframe) >= 3
        assert len(dashboard.get("plotly_chart")) == 2
        assert any(
            button.label == "Ingest and analyze synthetic replay"
            for button in dashboard.button
        )

        stress_selector = next(
            selectbox for selectbox in dashboard.selectbox if selectbox.label == "Trigger signal"
        )
        high_impact_option = next(
            option for option in stress_selector.options if option.startswith("Impact 9")
        )
        stress_selector.select(high_impact_option).run(timeout=30)
        stress_button = next(
            button for button in dashboard.button if button.label == "Run stress test"
        )
        stress_button.click().run(timeout=30)

        assert not dashboard.exception
        assert any(metric.label == "Illustrative loss" for metric in dashboard.metric)
        assert any("issuer-credit-event" in message.value for message in dashboard.success)

        event_filter = next(
            selectbox for selectbox in dashboard.selectbox if selectbox.label == "Event type"
        )
        event_filter.select("Operational").run(timeout=30)

        assert not dashboard.exception
        assert dashboard.metric[0].value == "1"

        event_filter = next(
            selectbox for selectbox in dashboard.selectbox if selectbox.label == "Event type"
        )
        event_filter.select("All").run(timeout=30)

        assert not dashboard.exception
        assert dashboard.metric[0].value == "10"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        store.close()
