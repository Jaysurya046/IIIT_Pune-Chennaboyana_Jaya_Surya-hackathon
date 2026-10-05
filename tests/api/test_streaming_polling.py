from types import SimpleNamespace

from risk_engine.api import app as api_app
from risk_engine.api.events import SignalEventBroker, format_heartbeat, format_sse
from risk_engine.api.service import PollingWorker
from risk_engine.cli import main


def _signal_stub(signal_id: str = "a" * 32):
    return SimpleNamespace(model_dump=lambda mode="json": {"signal_id": signal_id})


def test_sse_broker_orders_events_and_reconnects_from_cursor() -> None:
    signal = _signal_stub()
    broker = SignalEventBroker(history_loader=lambda cursor: ((1, signal), (2, signal)))
    stream = broker.subscribe(last_event_id=1, heartbeat_seconds=0.01)

    event = next(stream)
    assert event is not None and event.event_id == 2
    assert format_sse(event).startswith("id: 2\nevent: signal\ndata: ")
    stream.close()
    assert broker.subscriber_count == 0


def test_sse_broker_emits_heartbeat_and_cleans_up() -> None:
    broker = SignalEventBroker()
    stream = broker.subscribe(heartbeat_seconds=0.01)

    assert next(stream) is None
    assert format_heartbeat() == ": heartbeat\n\n"
    stream.close()
    assert broker.subscriber_count == 0


def test_polling_worker_runs_once_and_stops_cleanly() -> None:
    calls: list[str] = []
    waits = iter((True,))
    worker = PollingWorker(
        lambda: calls.append("poll"),
        interval_seconds=1.0,
        sleeper=lambda _seconds: next(waits),
    )

    worker.start()
    worker.stop()

    assert calls == ["poll"]
    assert worker.running is False


def test_serve_polling_requires_explicit_mode(monkeypatch, capsys) -> None:
    monkeypatch.setattr(api_app, "create_app", lambda *args, **kwargs: None)

    assert main(["serve", "--poll-minutes", "1"]) == 1
    assert "--source-mode is required" in capsys.readouterr().err


def test_serve_live_polling_respects_offline_guard(capsys) -> None:
    assert main(["serve", "--poll-minutes", "1", "--source-mode", "live"]) == 1
    assert "RISK_ENGINE_OFFLINE_MODE=false" in capsys.readouterr().err
