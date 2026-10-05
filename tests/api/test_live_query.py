from pathlib import Path

from risk_engine.api.models import IngestionRunRequest, SourceMode
from risk_engine.api.service import RiskApplicationService
from risk_engine.config import Settings
from risk_engine.ingestion.models import SourceType
from risk_engine.persistence.sqlite import SQLiteStore


class _RecordingLiveAdapter:
    name = "recording-live"
    source_type = SourceType.NEWS

    def __init__(self) -> None:
        self.queries: list[str] = []

    def fetch(self, request):
        self.queries.append(request.query)
        return []

    def close(self) -> None:
        return None


def test_live_ingestion_uses_watchlist_query_instead_of_ad_hoc_text(tmp_path: Path) -> None:
    settings = Settings(
        offline_mode=False,
        data_dir=Path("data"),
        database_url=f"sqlite:///{(tmp_path / 'live.db').as_posix()}",
    )
    store = SQLiteStore(settings.database_url)
    service = RiskApplicationService(settings, store)
    adapter = _RecordingLiveAdapter()
    service._live_adapters = lambda: [adapter]  # type: ignore[method-assign]

    response = service.ingest(
        IngestionRunRequest(query="ignored ad-hoc text", source_mode=SourceMode.LIVE)
    )

    assert response.query.startswith('"Northstar Energy" OR')
    assert adapter.queries == [response.query]
    assert "ignored ad-hoc text" not in response.query
    store.close()
