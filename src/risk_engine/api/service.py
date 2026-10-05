"""Application service coordinating ingestion, NLP, persistence, and stress testing."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal

from risk_engine.api.events import SignalEventBroker
from risk_engine.api.models import (
    AnalysisResponse,
    IngestionRunRequest,
    IngestionRunResponse,
    PortfolioBreakdown,
    PortfolioSummaryResponse,
    SourceMode,
    SourceStatusResponse,
    StressTestResponse,
    WhatIfStressRequest,
    WhatIfStressResponse,
)
from risk_engine.config import Settings
from risk_engine.ingestion.adapters import BlueskyAdapter, FixtureAdapter, GdeltAdapter
from risk_engine.ingestion.models import IngestionRequest
from risk_engine.ingestion.service import IngestionService
from risk_engine.ingestion.watchlist import build_watchlist_query
from risk_engine.nlp.engine import RiskSignalEngine
from risk_engine.nlp.factory import build_risk_engine, synthetic_batch_as_of
from risk_engine.persistence.sqlite import SQLiteStore
from risk_engine.stress.config import load_portfolio
from risk_engine.stress.factory import build_stress_engine
from risk_engine.stress.models import AssetClass, LoanPosition, Portfolio, Position
from risk_engine.stress.valuation import money

LOGGER = logging.getLogger(__name__)


class LiveModeDisabledError(RuntimeError):
    """Raised when a request tries to use the network in configured offline mode."""


class UnknownPortfolioEntityError(ValueError):
    """Raised when hypothetical assumptions reference an unknown portfolio entity."""

    def __init__(self, entity_ids: tuple[str, ...]) -> None:
        self.entity_ids = entity_ids
        super().__init__(f"Unknown portfolio entity IDs: {', '.join(entity_ids)}")


class RiskApplicationService:
    """Use-case layer kept separate from HTTP and storage implementations."""

    def __init__(
        self,
        settings: Settings,
        store: SQLiteStore,
        *,
        event_broker: SignalEventBroker | None = None,
        auto_stress: bool = False,
    ) -> None:
        self.settings = settings
        self.store = store
        self._stress_engine = build_stress_engine(settings)
        self._portfolio = load_portfolio(settings.data_dir / "portfolio" / "portfolio.json")
        self._nlp_engines: dict[str, RiskSignalEngine] = {}
        self._event_broker = event_broker
        self._auto_stress = auto_stress

    def _fixture_adapters(self) -> list[FixtureAdapter]:
        sample_dir = self.settings.data_dir / "sample"
        return [
            FixtureAdapter(sample_dir / "gdelt_articles.json"),
            FixtureAdapter(sample_dir / "bluesky_posts.json"),
        ]

    def _replay_adapters(self) -> list[FixtureAdapter]:
        replay_dir = self.settings.data_dir / "replay"
        return [
            FixtureAdapter(replay_dir / "banking_stress_news.json"),
            FixtureAdapter(replay_dir / "banking_stress_social.json"),
        ]

    def _live_adapters(self) -> list[GdeltAdapter | BlueskyAdapter]:
        if self.settings.offline_mode:
            raise LiveModeDisabledError(
                "Live ingestion is disabled; set RISK_ENGINE_OFFLINE_MODE=false explicitly"
            )
        return [
            GdeltAdapter(
                self.settings.gdelt_base_url,
                timeout_seconds=self.settings.request_timeout_seconds,
                request_spacing_seconds=self.settings.gdelt_request_spacing_seconds,
            ),
            BlueskyAdapter(
                self.settings.bluesky_base_url,
                timeout_seconds=self.settings.request_timeout_seconds,
                bearer_token=self.settings.bluesky_bearer_token,
            ),
        ]

    def ingest(self, request: IngestionRunRequest) -> IngestionRunResponse:
        if request.source_mode is SourceMode.FIXTURES:
            adapters = self._fixture_adapters()
        elif request.source_mode is SourceMode.REPLAY:
            adapters = self._replay_adapters()
        elif request.source_mode is SourceMode.LIVE:
            adapters = self._live_adapters()
        else:  # pragma: no cover - SourceMode validation is exhaustive
            raise AssertionError(f"Unhandled source mode: {request.source_mode}")
        query = request.query
        if request.source_mode is SourceMode.LIVE:
            query = build_watchlist_query(self.settings.data_dir / "nlp" / "issuer_watchlist.json")
        try:
            result = IngestionService(
                adapters,
                max_text_length=self.settings.max_text_length,
            ).run(
                IngestionRequest(
                    query=query,
                    limit=request.limit,
                    lookback_hours=request.lookback_hours,
                    since=request.since,
                )
            )
        finally:
            for adapter in adapters:
                close = getattr(adapter, "close", None)
                if close is not None:
                    close()
        record = self.store.save_ingestion(result)
        return IngestionRunResponse(
            run_id=record.run_id,
            query=result.query,
            document_count=len(result.documents),
            successful_source_count=result.successful_source_count,
            failed_source_count=result.failed_source_count,
            sources=result.sources,
        )

    def _nlp_engine(self, mode: str) -> RiskSignalEngine:
        engine = self._nlp_engines.get(mode)
        if engine is None:
            engine = build_risk_engine(self.settings, mode=mode)
            self._nlp_engines[mode] = engine
        return engine

    def warm_up_model_mode(self) -> None:
        """Load both pinned model components and surface any failure to startup."""

        self._nlp_engine("model").warm_up()

    def analyze(self, run_id: str, nlp_mode: str | None) -> AnalysisResponse | None:
        record = self.store.get_ingestion(run_id)
        if record is None:
            return None
        mode = nlp_mode or self.settings.nlp_mode
        engine = self._nlp_engine(mode)
        documents = record.result.documents
        contains_synthetic_provenance = any(
            document.provenance.synthetic for document in documents
        )
        as_of = (
            synthetic_batch_as_of(documents)
            if contains_synthetic_provenance
            else None
        )
        signals = engine.analyze(documents, as_of=as_of)
        self.store.save_signals(signals)
        if self._event_broker is not None:
            for signal in signals:
                event = self.store.signal_event(signal.signal_id)
                if event is not None:
                    self._event_broker.publish(event.signal, event.event_id)
        if self._auto_stress:
            for signal in signals:
                if signal.impact_score > self.settings.stress_trigger_threshold:
                    self.stress(signal.signal_id)
        return AnalysisResponse(run_id=run_id, signal_count=len(signals), signals=signals)

    def poll_once(
        self,
        *,
        source_mode: SourceMode,
        query: str,
        nlp_mode: str | None = None,
    ) -> AnalysisResponse | None:
        """Run one explicit polling cycle without changing source or NLP modes."""

        ingestion = self.ingest(
            IngestionRunRequest(query=query, source_mode=source_mode)
        )
        if ingestion.failed_source_count:
            LOGGER.warning("Polling source failure; retaining explicit mode %s", source_mode)
        return self.analyze(ingestion.run_id, nlp_mode)

    def source_status(self) -> SourceStatusResponse:
        record = self.store.latest_ingestion()
        if record is None:
            return SourceStatusResponse()
        return SourceStatusResponse(
            latest_run_id=record.run_id,
            query=record.result.query,
            completed_at=record.result.completed_at,
            sources=record.result.sources,
        )

    def stress(self, signal_id: str) -> StressTestResponse | None:
        signal = self.store.get_signal(signal_id)
        if signal is None:
            return None
        record = self.store.save_stress_decision(self._stress_engine.run(signal))
        return StressTestResponse(decision_id=record.decision_id, decision=record.decision)

    def what_if(self, request: WhatIfStressRequest) -> WhatIfStressResponse:
        known_entities = {position.issuer_id for position in self._portfolio.positions}
        unknown_entities = tuple(
            sorted(entity_id for entity_id in request.entity_ids if entity_id not in known_entities)
        )
        if unknown_entities:
            raise UnknownPortfolioEntityError(unknown_entities)
        return WhatIfStressResponse(
            assumptions=request,
            decision=self._stress_engine.run_hypothetical(request),
        )

    @staticmethod
    def _breakdown(
        portfolio: Portfolio,
        key_function: Callable[[Position], str],
    ) -> tuple[PortfolioBreakdown, ...]:
        totals: dict[str, Decimal] = defaultdict(Decimal)
        counts: dict[str, int] = defaultdict(int)
        for position in portfolio.positions:
            key = str(key_function(position))
            totals[key] += position.market_value
            counts[key] += 1
        return tuple(
            PortfolioBreakdown(
                key=key,
                position_count=counts[key],
                market_value=money(totals[key]),
            )
            for key in sorted(totals)
        )

    def portfolio_summary(self) -> PortfolioSummaryResponse:
        portfolio = self._portfolio
        total = money(sum((position.market_value for position in portfolio.positions), Decimal(0)))
        expected_loss = money(
            sum(
                (
                    position.market_value
                    * position.probability_of_default
                    * position.loss_given_default
                    for position in portfolio.positions
                    if isinstance(position, LoanPosition)
                ),
                Decimal(0),
            )
        )
        return PortfolioSummaryResponse(
            portfolio_id=portfolio.portfolio_id,
            portfolio_version=portfolio.version,
            base_currency=portfolio.base_currency,
            position_count=len(portfolio.positions),
            total_market_value=total,
            base_expected_loss=expected_loss,
            by_asset_class=self._breakdown(
                portfolio, lambda item: AssetClass(item.asset_class).value
            ),
            by_sector=self._breakdown(portfolio, lambda item: item.sector),
            by_issuer=self._breakdown(portfolio, lambda item: item.issuer_id),
        )


class PollingWorker:
    """Bounded daemon worker for optional in-process ingestion polling."""

    def __init__(
        self,
        poll: Callable[[], object],
        *,
        interval_seconds: float,
        sleeper: Callable[[float], bool] | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._poll = poll
        self._interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._sleeper = sleeper
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _wait(self) -> bool:
        if self._sleeper is not None:
            return self._sleeper(self._interval_seconds)
        return self._stop.wait(self._interval_seconds)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._poll()
            except Exception:  # noqa: BLE001 - polling must not kill the API process
                LOGGER.exception("Polling cycle failed; source mode remains explicit")
            if self._wait():
                break

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="risk-signal-poller", daemon=True)
        self._thread.start()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout_seconds)
