"""SQLite repositories for ingestion runs, risk signals, and stress decisions."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path

from risk_engine.ingestion.models import IngestionResult
from risk_engine.nlp.models import EventType, RiskSignal
from risk_engine.persistence.models import (
    IngestionRunRecord,
    SignalEventRecord,
    StressDecisionRecord,
)
from risk_engine.stress.models import StressDecision, StressResult

SCHEMA_VERSION = "1"


class PersistenceConfigurationError(ValueError):
    """Raised for an unsupported or unusable database URL."""


def sqlite_path_from_url(database_url: str) -> str:
    """Translate the documented SQLite URL format to a driver path."""

    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise PersistenceConfigurationError("database URL must use the sqlite:/// scheme")
    path = database_url.removeprefix(prefix)
    if not path:
        raise PersistenceConfigurationError("database URL must include a path")
    return path


class SQLiteStore:
    """Small thread-safe repository with explicit schema ownership."""

    def __init__(self, database_url: str) -> None:
        database_path = sqlite_path_from_url(database_url)
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            database_path,
            check_same_thread=False,
            timeout=10,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._closed = False
        self.initialize()

    def initialize(self) -> None:
        schema = """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ingestion_runs (
            run_id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS source_statuses (
            run_id TEXT NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            source_type TEXT NOT NULL,
            successful INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (run_id, source)
        );
        CREATE INDEX IF NOT EXISTS idx_source_statuses_latest
            ON source_statuses(source, completed_at DESC);
        CREATE TABLE IF NOT EXISTS risk_signals (
            signal_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            impact_score INTEGER NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_risk_signals_created
            ON risk_signals(created_at DESC, signal_id);
        CREATE INDEX IF NOT EXISTS idx_risk_signals_filters
            ON risk_signals(event_type, impact_score, source);
        CREATE TABLE IF NOT EXISTS signal_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE REFERENCES risk_signals(signal_id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS signal_entities (
            signal_id TEXT NOT NULL REFERENCES risk_signals(signal_id) ON DELETE CASCADE,
            entity_id TEXT NOT NULL,
            PRIMARY KEY (signal_id, entity_id)
        );
        CREATE INDEX IF NOT EXISTS idx_signal_entities_entity
            ON signal_entities(entity_id, signal_id);
        CREATE TABLE IF NOT EXISTS stress_decisions (
            decision_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL REFERENCES risk_signals(signal_id) ON DELETE CASCADE,
            triggered INTEGER NOT NULL,
            result_id TEXT UNIQUE,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_stress_decisions_signal
            ON stress_decisions(signal_id, created_at DESC);
        """
        with self._lock, self._connection:
            self._connection.executescript(schema)
            row = self._connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if row is not None and row["value"] != SCHEMA_VERSION:
                raise PersistenceConfigurationError(
                    f"database schema {row['value']} is not supported"
                )
            self._connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES ('schema_version', ?)",
                (SCHEMA_VERSION,),
            )

    def ping(self) -> bool:
        with self._lock:
            return self._connection.execute("SELECT 1").fetchone()[0] == 1

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True

    @staticmethod
    def _ingestion_run_id(result: IngestionResult) -> str:
        identity = (
            f"{result.query}|{result.started_at.isoformat()}|{result.completed_at.isoformat()}"
        )
        return hashlib.sha256(identity.encode()).hexdigest()[:32]

    def save_ingestion(self, result: IngestionResult) -> IngestionRunRecord:
        run_id = self._ingestion_run_id(result)
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO ingestion_runs(run_id, query, started_at, completed_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    query = excluded.query,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    payload_json = excluded.payload_json
                """,
                (
                    run_id,
                    result.query,
                    result.started_at.isoformat(),
                    result.completed_at.isoformat(),
                    result.model_dump_json(),
                ),
            )
            self._connection.execute("DELETE FROM source_statuses WHERE run_id = ?", (run_id,))
            self._connection.executemany(
                """
                INSERT INTO source_statuses(
                    run_id, source, source_type, successful, completed_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        status.source,
                        status.source_type.value,
                        int(status.successful),
                        status.completed_at.isoformat(),
                        status.model_dump_json(),
                    )
                    for status in result.sources
                ],
            )
        return IngestionRunRecord(run_id=run_id, result=result)

    def get_ingestion(self, run_id: str) -> IngestionRunRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json FROM ingestion_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return IngestionRunRecord(
            run_id=run_id,
            result=IngestionResult.model_validate_json(row["payload_json"]),
        )

    def latest_ingestion(self) -> IngestionRunRecord | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT run_id, payload_json FROM ingestion_runs
                ORDER BY completed_at DESC, run_id DESC LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return IngestionRunRecord(
            run_id=row["run_id"],
            result=IngestionResult.model_validate_json(row["payload_json"]),
        )

    def save_signals(self, signals: Iterable[RiskSignal]) -> int:
        signal_batch = tuple(signals)
        with self._lock, self._connection:
            for signal in signal_batch:
                self._connection.execute(
                    """
                    INSERT INTO risk_signals(
                        signal_id, document_id, event_type, impact_score,
                        source, created_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(signal_id) DO UPDATE SET
                        document_id = excluded.document_id,
                        event_type = excluded.event_type,
                        impact_score = excluded.impact_score,
                        source = excluded.source,
                        created_at = excluded.created_at,
                        payload_json = excluded.payload_json
                    """,
                    (
                        signal.signal_id,
                        signal.document_id,
                        signal.event.event_type.value,
                        signal.impact_score,
                        signal.provenance.source,
                        signal.created_at.isoformat(),
                        signal.model_dump_json(),
                    ),
                )
                self._connection.execute(
                    "DELETE FROM signal_entities WHERE signal_id = ?", (signal.signal_id,)
                )
                self._connection.executemany(
                    "INSERT INTO signal_entities(signal_id, entity_id) VALUES (?, ?)",
                    [(signal.signal_id, entity.entity_id) for entity in signal.entities],
                )
                self._connection.execute(
                    """
                    INSERT OR IGNORE INTO signal_events(signal_id, created_at, payload_json)
                    VALUES (?, ?, ?)
                    """,
                    (signal.signal_id, signal.created_at.isoformat(), signal.model_dump_json()),
                )
        return len(signal_batch)

    def list_signal_events_after(
        self, event_id: int = 0, *, limit: int = 100
    ) -> tuple[SignalEventRecord, ...]:
        if event_id < 0 or limit < 1:
            raise ValueError("event_id must be non-negative and limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT event_id, payload_json FROM signal_events
                WHERE event_id > ? ORDER BY event_id ASC LIMIT ?
                """,
                (event_id, limit),
            ).fetchall()
        return tuple(
            SignalEventRecord(
                event_id=row["event_id"],
                signal=RiskSignal.model_validate_json(row["payload_json"]),
            )
            for row in rows
        )

    def signal_event(self, signal_id: str) -> SignalEventRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT event_id, payload_json FROM signal_events WHERE signal_id = ?",
                (signal_id,),
            ).fetchone()
        if row is None:
            return None
        return SignalEventRecord(
            event_id=row["event_id"],
            signal=RiskSignal.model_validate_json(row["payload_json"]),
        )

    def count_stress_decisions(self) -> int:
        with self._lock:
            return int(
                self._connection.execute("SELECT COUNT(*) FROM stress_decisions").fetchone()[0]
            )

    def get_signal(self, signal_id: str) -> RiskSignal | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json FROM risk_signals WHERE signal_id = ?", (signal_id,)
            ).fetchone()
        return None if row is None else RiskSignal.model_validate_json(row["payload_json"])

    def list_signals(
        self,
        *,
        limit: int,
        offset: int,
        event_type: EventType | None = None,
        min_impact: int | None = None,
        source: str | None = None,
        entity_id: str | None = None,
    ) -> tuple[tuple[RiskSignal, ...], int]:
        conditions: list[str] = []
        parameters: list[object] = []
        if event_type is not None:
            conditions.append("risk_signals.event_type = ?")
            parameters.append(event_type.value)
        if min_impact is not None:
            conditions.append("risk_signals.impact_score >= ?")
            parameters.append(min_impact)
        if source is not None:
            conditions.append("risk_signals.source = ?")
            parameters.append(source)
        if entity_id is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM signal_entities WHERE "
                "signal_entities.signal_id = risk_signals.signal_id "
                "AND signal_entities.entity_id = ?)"
            )
            parameters.append(entity_id)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._lock:
            total = self._connection.execute(
                f"SELECT COUNT(*) FROM risk_signals{where}", parameters
            ).fetchone()[0]
            rows = self._connection.execute(
                f"""
                SELECT payload_json FROM risk_signals{where}
                ORDER BY created_at DESC, signal_id ASC LIMIT ? OFFSET ?
                """,
                [*parameters, limit, offset],
            ).fetchall()
        return tuple(RiskSignal.model_validate_json(row["payload_json"]) for row in rows), total

    @staticmethod
    def _decision_id(decision: StressDecision) -> str:
        if decision.result is not None:
            return decision.result.stress_id
        identity = f"{decision.signal_id}|{decision.trigger_threshold}|skipped"
        return hashlib.sha256(identity.encode()).hexdigest()[:32]

    def save_stress_decision(self, decision: StressDecision) -> StressDecisionRecord:
        decision_id = self._decision_id(decision)
        result_id = decision.result.stress_id if decision.result is not None else None
        with self._lock, self._connection:
            if decision.result is not None:
                created_at = decision.result.created_at.isoformat()
            else:
                signal_row = self._connection.execute(
                    "SELECT created_at FROM risk_signals WHERE signal_id = ?",
                    (decision.signal_id,),
                ).fetchone()
                if signal_row is None:
                    raise ValueError("stress decision references an unknown signal")
                created_at = signal_row["created_at"]
            self._connection.execute(
                """
                INSERT INTO stress_decisions(
                    decision_id, signal_id, triggered, result_id, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                    triggered = excluded.triggered,
                    result_id = excluded.result_id,
                    created_at = excluded.created_at,
                    payload_json = excluded.payload_json
                """,
                (
                    decision_id,
                    decision.signal_id,
                    int(decision.triggered),
                    result_id,
                    created_at,
                    decision.model_dump_json(),
                ),
            )
        return StressDecisionRecord(decision_id=decision_id, decision=decision)

    def get_stress_result(self, result_id: str) -> StressResult | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json FROM stress_decisions WHERE result_id = ?", (result_id,)
            ).fetchone()
        if row is None:
            return None
        decision = StressDecision.model_validate_json(row["payload_json"])
        return decision.result
