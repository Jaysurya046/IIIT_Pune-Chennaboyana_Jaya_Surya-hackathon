"""Dependency-free in-process SSE broker for persisted risk signals."""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from risk_engine.nlp.models import RiskSignal


@dataclass(frozen=True, slots=True)
class SignalEvent:
    event_id: int
    signal: RiskSignal


SignalHistoryLoader = Callable[[int], Sequence[tuple[int, RiskSignal]]]


class SignalEventBroker:
    """Fan out ordered persisted signal events and periodic heartbeat markers."""

    def __init__(
        self,
        *,
        history_loader: SignalHistoryLoader | None = None,
        max_queue_size: int = 100,
    ) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be positive")
        self._history_loader = history_loader
        self._max_queue_size = max_queue_size
        self._lock = threading.RLock()
        self._subscribers: set[queue.Queue[SignalEvent]] = set()
        self._next_event_id = 1

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def publish(self, signal: RiskSignal, event_id: int | None = None) -> SignalEvent:
        with self._lock:
            selected_id = event_id or self._next_event_id
            self._next_event_id = max(self._next_event_id, selected_id + 1)
            event = SignalEvent(event_id=selected_id, signal=signal)
            for subscriber in tuple(self._subscribers):
                try:
                    subscriber.put_nowait(event)
                except queue.Full:
                    subscriber.get_nowait()
                    subscriber.put_nowait(event)
            return event

    def subscribe(
        self,
        *,
        last_event_id: int = 0,
        heartbeat_seconds: float = 15.0,
    ) -> Iterator[SignalEvent | None]:
        if last_event_id < 0:
            raise ValueError("last_event_id must not be negative")
        if heartbeat_seconds <= 0:
            raise ValueError("heartbeat_seconds must be positive")
        pending: queue.Queue[SignalEvent] = queue.Queue(maxsize=self._max_queue_size)
        with self._lock:
            self._subscribers.add(pending)
            history = (
                tuple(self._history_loader(last_event_id))
                if self._history_loader is not None
                else ()
            )
            for event_id, signal in history:
                if event_id > last_event_id:
                    pending.put_nowait(SignalEvent(event_id=event_id, signal=signal))
        try:
            while True:
                try:
                    yield pending.get(timeout=heartbeat_seconds)
                except queue.Empty:
                    yield None
        finally:
            with self._lock:
                self._subscribers.discard(pending)


def format_sse(event: SignalEvent) -> str:
    """Serialize a signal event using stable SSE framing."""

    payload = json.dumps(event.signal.model_dump(mode="json"), separators=(",", ":"))
    return f"id: {event.event_id}\nevent: signal\ndata: {payload}\n\n"


def format_heartbeat() -> str:
    return ": heartbeat\n\n"
