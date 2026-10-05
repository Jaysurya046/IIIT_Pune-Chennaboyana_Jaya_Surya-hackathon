from pathlib import Path

from risk_engine.api.models import IngestionRunRequest, SourceMode
from risk_engine.api.service import RiskApplicationService
from risk_engine.config import Settings
from risk_engine.persistence.sqlite import SQLiteStore


def test_auto_stress_persists_only_triggered_signals_and_is_idempotent(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=Path("data"),
        database_url=f"sqlite:///{(tmp_path / 'auto.db').as_posix()}",
    )
    store = SQLiteStore(settings.database_url)
    service = RiskApplicationService(settings, store, auto_stress=True)

    ingestion = service.ingest(
        IngestionRunRequest(query="banking stress", source_mode=SourceMode.REPLAY)
    )
    service.analyze(ingestion.run_id, "deterministic")
    first_count = store.count_stress_decisions()
    service.analyze(ingestion.run_id, "deterministic")

    assert first_count == 4
    assert store.count_stress_decisions() == first_count
    store.close()
