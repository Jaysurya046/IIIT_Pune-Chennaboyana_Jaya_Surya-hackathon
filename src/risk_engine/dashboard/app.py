"""Streamlit entry point for operational risk monitoring and stress exploration."""

from __future__ import annotations

import os
from decimal import Decimal

import pandas as pd
import streamlit as st

from risk_engine.api.models import (
    HealthResponse,
    PortfolioSummaryResponse,
    SignalListResponse,
    SourceMode,
    SourceStatusResponse,
    StressTestResponse,
    WhatIfStressResponse,
)
from risk_engine.dashboard.charts import (
    asset_class_figure,
    event_distribution_figure,
    issuer_loss_figure,
    sentiment_impact_figure,
)
from risk_engine.dashboard.client import DashboardApiClient, DashboardApiError
from risk_engine.dashboard.model import (
    applied_shock_rows,
    impact_factor_rows,
    instrument_rows,
    signal_metrics,
    signal_rows,
    source_rows,
    stress_by_asset_class,
    stress_by_issuer,
    stress_by_sector,
)
from risk_engine.nlp.models import EventType, RiskSignal

DEFAULT_API_URL = "http://127.0.0.1:8000"


@st.cache_data(ttl=15, show_spinner=False)
def _load_base(
    api_url: str,
) -> tuple[HealthResponse, SourceStatusResponse, PortfolioSummaryResponse, SignalListResponse]:
    with DashboardApiClient(api_url) as client:
        return (
            client.health(),
            client.source_status(),
            client.portfolio_summary(),
            client.signals(limit=100),
        )


@st.cache_data(ttl=15, show_spinner=False)
def _load_signals(
    api_url: str,
    event_type: str | None,
    min_impact: int,
    source: str | None,
    entity_id: str | None,
) -> SignalListResponse:
    with DashboardApiClient(api_url) as client:
        return client.signals(
            limit=100,
            event_type=EventType(event_type) if event_type else None,
            min_impact=min_impact if min_impact > 1 else None,
            source=source,
            entity_id=entity_id,
        )


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def _signal_label(signal: RiskSignal) -> str:
    entities = ", ".join(entity.name for entity in signal.entities) or "Unresolved entity"
    return f"Impact {signal.impact_score} · {signal.event.event_type.value} · {entities}"


def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ink: #17324d; --muted: #587087; --line: #dce6ef; }
        .block-container { max-width: 1440px; padding-top: 1.8rem; padding-bottom: 3rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -0.02em; }
        [data-testid="stMetric"] {
            background: #f7fafc; border: 1px solid var(--line); border-radius: 10px;
            padding: 0.85rem 1rem;
        }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stMetricValue"] { color: var(--ink); }
        [data-testid="stSidebar"] { border-right: 1px solid var(--line); }
        .source-note {
            border-left: 4px solid #f9a825; background: #fff9e6; padding: .75rem 1rem;
            border-radius: 4px; color: #5d4a00; margin: .5rem 0 1rem;
        }
        a:focus, button:focus, input:focus { outline: 3px solid #90caf9 !important; }
        @media (max-width: 900px) {
            [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                flex: 1 1 100% !important; width: 100% !important; min-width: 0 !important;
            }
        }
        @media (max-width: 760px) { .block-container { padding: 1rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_filters(
    base_signals: SignalListResponse,
    health: HealthResponse,
) -> tuple[str | None, int, str | None, str | None]:
    with st.sidebar:
        st.header("Connection")
        st.success(f"API {health.version} connected")
        st.caption(f"Mode: {'offline fixtures' if health.offline_mode else 'live enabled'}")
        if st.button("Refresh dashboard", width="stretch"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.header("Signal filters")
        event_label = st.selectbox(
            "Event type",
            ["All", *(item.value for item in EventType)],
        )
        min_impact = st.slider("Minimum impact", 1, 10, 1)
        sources = sorted({item.provenance.source for item in base_signals.items})
        source_label = st.selectbox("Source", ["All", *sources])
        entities = {
            entity.entity_id: entity.name
            for signal in base_signals.items
            for entity in signal.entities
        }
        entity_options = ["All", *sorted(entities, key=lambda key: entities[key])]
        entity_label = st.selectbox(
            "Entity",
            entity_options,
            format_func=lambda key: "All" if key == "All" else entities[key],
        )

        st.divider()
        st.caption("Filters apply to every signal view and the Stress Lab selector.")

    return (
        None if event_label == "All" else event_label,
        min_impact,
        None if source_label == "All" else source_label,
        None if entity_label == "All" else entity_label,
    )


def _render_signal_detail(signal: RiskSignal) -> None:
    left, right = st.columns([1.1, 0.9])
    with left:
        st.subheader("Selected signal")
        st.write("\n\n".join(signal.rationale))
        st.dataframe(
            pd.DataFrame(impact_factor_rows(signal)),
            hide_index=True,
            width="stretch",
            column_config={
                "Normalized value": st.column_config.ProgressColumn(
                    min_value=0.0, max_value=1.0, format="%.2f"
                )
            },
        )
    with right:
        st.subheader("Source provenance")
        if signal.provenance.source.startswith("replay-"):
            source_kind = "Synthetic replay"
        elif signal.provenance.synthetic:
            source_kind = "Synthetic fixture"
        else:
            source_kind = "Live public source"
        st.markdown(f"**Classification:** {source_kind}")
        st.markdown(f"**Source:** {signal.provenance.source}")
        st.markdown(f"**Published:** {signal.provenance.published_at.isoformat()}")
        st.markdown(f"**Retrieved:** {signal.provenance.retrieved_at.isoformat()}")
        st.markdown(f"**Query:** `{signal.provenance.query}`")
        st.link_button("Open original source", signal.provenance.original_url)
        with st.expander("Model and event evidence"):
            st.json(
                {
                    "event_evidence": signal.event.evidence,
                    "event_confidence": signal.event.confidence,
                    "model_versions": signal.model_versions,
                    "signal_id": signal.signal_id,
                }
            )


def _render_signals(
    response: SignalListResponse,
    portfolio: PortfolioSummaryResponse,
) -> RiskSignal | None:
    metrics = signal_metrics(response)
    columns = st.columns(4)
    columns[0].metric("Matching signals", metrics.total)
    columns[1].metric("Impact > 7", metrics.high_impact)
    columns[2].metric("Mean impact", f"{metrics.mean_impact:.1f} / 10")
    columns[3].metric("Synthetic exposure", _money(portfolio.total_market_value))

    st.markdown(
        '<div class="source-note"><strong>Data note:</strong> committed fixture/replay records '
        "and the portfolio are synthetic demonstration data. Values are illustrative, not "
        "forecasts or investment advice.</div>",
        unsafe_allow_html=True,
    )

    if not response.items:
        st.info("No signals match the current filters. Broaden the sidebar selections.")
        return None

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(
            event_distribution_figure(response.items),
            width="stretch",
            config={"displaylogo": False},
            theme=None,
        )
    with chart_right:
        st.plotly_chart(
            sentiment_impact_figure(response.items),
            width="stretch",
            config={"displaylogo": False},
            theme=None,
        )

    st.subheader("Signal register")
    frame = pd.DataFrame(signal_rows(response.items))
    st.dataframe(
        frame,
        hide_index=True,
        width="stretch",
        column_config={
            "Impact": st.column_config.ProgressColumn(min_value=1, max_value=10, format="%d"),
            "Sentiment score": st.column_config.NumberColumn(format="%.2f"),
            "Synthetic": st.column_config.CheckboxColumn(),
        },
    )

    selected = st.selectbox(
        "Inspect a signal",
        response.items,
        format_func=_signal_label,
        key="signal_inspector",
    )
    _render_signal_detail(selected)
    return selected


def _render_stress_result(
    response: StressTestResponse | WhatIfStressResponse,
    *,
    key_prefix: str,
) -> None:
    decision = response.decision
    if not decision.triggered or decision.result is None:
        st.warning(decision.reason)
        return

    result = decision.result
    st.success(decision.reason)
    st.caption(
        f"Scenario {result.scenario_id} · portfolio {result.portfolio_version} · "
        f"scenario configuration {result.scenario_version}"
    )
    columns = st.columns(4)
    columns[0].metric("Before", _money(result.before_value))
    columns[1].metric("After", _money(result.after_value))
    columns[2].metric(
        "Illustrative loss",
        _money(result.total_loss),
        delta=f"-{result.loss_percentage:.2f}%",
        delta_color="inverse",
    )
    columns[3].metric("Expected-loss change", _money(result.expected_loss_change))

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            asset_class_figure(result),
            width="stretch",
            config={"displaylogo": False},
            theme=None,
            key=f"{key_prefix}_asset_class_chart",
        )
        st.dataframe(
            pd.DataFrame(stress_by_asset_class(result)),
            hide_index=True,
            width="stretch",
            key=f"{key_prefix}_asset_class_table",
        )
    with right:
        st.plotly_chart(
            issuer_loss_figure(result),
            width="stretch",
            config={"displaylogo": False},
            theme=None,
            key=f"{key_prefix}_issuer_chart",
        )
        st.dataframe(
            pd.DataFrame(stress_by_issuer(result)),
            hide_index=True,
            width="stretch",
            key=f"{key_prefix}_issuer_table",
        )

    st.subheader("Sector reconciliation")
    st.dataframe(
        pd.DataFrame(stress_by_sector(result)),
        hide_index=True,
        width="stretch",
        key=f"{key_prefix}_sector_table",
    )

    st.subheader("Instrument reconciliation")
    st.caption(
        f"Instrument losses reconcile to the aggregate with a difference of "
        f"{_money(result.reconciliation_difference)}."
    )
    st.dataframe(
        pd.DataFrame(instrument_rows(result)),
        hide_index=True,
        width="stretch",
        key=f"{key_prefix}_instrument_table",
    )
    with st.expander("Applied scenario shocks"):
        shock_rows = applied_shock_rows(result)
        if shock_rows:
            st.dataframe(
                pd.DataFrame(shock_rows),
                hide_index=True,
                width="stretch",
                key=f"{key_prefix}_shock_table",
            )
        else:
            st.info("This scenario did not apply any shocks to the selected instruments.")


def _render_what_if(api_url: str, portfolio: PortfolioSummaryResponse) -> None:
    st.subheader("Hypothetical what-if")
    st.warning(
        "Hypothetical simulation only: these user-selected assumptions are not an observed "
        "or replay signal, and neither the assumptions nor result are persisted."
    )
    event_type = st.selectbox(
        "Hypothetical event",
        list(EventType),
        format_func=lambda item: item.value,
        key="what_if_event",
    )
    issuer_ids = tuple(item.key for item in portfolio.by_issuer)
    entity_ids = tuple(
        st.multiselect(
            "Hypothetical entities",
            issuer_ids,
            default=[issuer_ids[0]] if issuer_ids else [],
            key="what_if_entities",
        )
    )
    impact_score = st.slider(
        "Hypothetical impact score",
        min_value=1,
        max_value=10,
        value=8,
        key="what_if_impact",
    )
    assumptions_key = (event_type.value, entity_ids, impact_score)
    if st.button(
        "Run hypothetical simulation",
        disabled=not entity_ids,
        type="primary",
    ):
        try:
            with (
                st.spinner("Running non-persisted hypothetical stress..."),
                DashboardApiClient(api_url) as client,
            ):
                result = client.run_what_if(event_type, entity_ids, impact_score)
            st.session_state["latest_what_if"] = (assumptions_key, result)
        except DashboardApiError as error:
            st.error(str(error))

    latest = st.session_state.get("latest_what_if")
    if latest and latest[0] == assumptions_key:
        st.caption(
            "Hypothetical assumptions: "
            f"{event_type.value}; entities {', '.join(entity_ids)}; impact {impact_score}."
        )
        _render_stress_result(latest[1], key_prefix="what_if")
    else:
        st.caption("Run the controls above to calculate a non-persisted hypothetical result.")


def _render_stress_lab(
    api_url: str,
    response: SignalListResponse,
    portfolio: PortfolioSummaryResponse,
) -> None:
    st.markdown(
        '<div class="source-note"><strong>Synthetic scenario:</strong> shocks and portfolio '
        "positions are project-authored assumptions for demonstration. They are not calibrated "
        "regulatory scenarios.</div>",
        unsafe_allow_html=True,
    )
    _render_what_if(api_url, portfolio)
    st.divider()
    st.subheader("Observed or replay signal stress")
    if not response.items:
        st.info("No filtered signals are available for stress testing.")
        return

    selected = st.selectbox(
        "Trigger signal",
        response.items,
        format_func=_signal_label,
        key="stress_signal",
    )
    if selected.impact_score > 7:
        st.success("Eligible: impact is strictly greater than the configured threshold of 7.")
    else:
        st.info("Not eligible: the engine will record a skipped decision because impact is ≤ 7.")

    if st.button("Run stress test", type="primary"):
        try:
            with (
                st.spinner("Applying the configured scenario through the API…"),
                DashboardApiClient(api_url) as client,
            ):
                result = client.run_stress(selected.signal_id)
            st.session_state["latest_stress"] = (selected.signal_id, result)
        except DashboardApiError as error:
            st.error(str(error))

    latest = st.session_state.get("latest_stress")
    if latest and latest[0] == selected.signal_id:
        _render_stress_result(latest[1], key_prefix="observed")
    else:
        st.caption(
            "Run the selected signal to view a persisted stress decision and reconciliation."
        )


def _render_source_health(api_url: str, status: SourceStatusResponse) -> None:
    if status.latest_run_id is None:
        st.info("No ingestion run is stored yet. Use the fixture workflow below to create one.")
    else:
        successful = sum(item.successful for item in status.sources)
        columns = st.columns(3)
        columns[0].metric("Healthy sources", f"{successful} / {len(status.sources)}")
        columns[1].metric("Latest query", status.query or "—")
        columns[2].metric(
            "Last completed (UTC)",
            status.completed_at.strftime("%Y-%m-%d %H:%M") if status.completed_at else "—",
        )
        st.dataframe(pd.DataFrame(source_rows(status)), hide_index=True, width="stretch")

    st.subheader("Reproducible fixture refresh")
    st.caption(
        "This action explicitly uses committed fixtures and deterministic NLP. It never falls "
        "back from a failed live request."
    )
    query = st.text_input("Ingestion query", value="portfolio risk", max_chars=500)
    if st.button("Ingest and analyze fixtures", disabled=not query.strip()):
        try:
            with st.status("Running offline pipeline…", expanded=True) as pipeline_status:
                st.write("Ingesting news and social fixtures")
                with DashboardApiClient(api_url, timeout=30.0) as client:
                    ingestion = client.run_ingestion(
                        query.strip(), source_mode=SourceMode.FIXTURES
                    )
                    st.write(f"Accepted {ingestion.document_count} normalized documents")
                    analysis = client.analyze(ingestion.run_id, nlp_mode="deterministic")
                    st.write(f"Generated {analysis.signal_count} explainable signals")
                pipeline_status.update(label="Fixture workflow completed", state="complete")
            st.cache_data.clear()
            st.success("Data stored. Refresh the dashboard to load the new run.")
        except DashboardApiError as error:
            st.error(str(error))

    st.subheader("Synthetic banking-stress replay")
    st.caption(
        "This separate offline mode runs four project-authored records inspired by the general "
        "March 2023 banking-stress pattern. It is hypothetical, synthetic, and not copied news."
    )
    if st.button("Ingest and analyze synthetic replay"):
        try:
            with st.status("Running synthetic replay...", expanded=True) as replay_status:
                st.write("Ingesting checksummed replay news and social records")
                with DashboardApiClient(api_url, timeout=30.0) as client:
                    ingestion = client.run_ingestion(
                        "banking stress", source_mode=SourceMode.REPLAY
                    )
                    st.write(f"Accepted {ingestion.document_count} normalized documents")
                    analysis = client.analyze(ingestion.run_id, nlp_mode="deterministic")
                    st.write(f"Generated {analysis.signal_count} explainable signals")
                replay_status.update(label="Synthetic replay completed", state="complete")
            st.cache_data.clear()
            st.success("Replay stored. Refresh the dashboard to use it in Stress Lab.")
        except DashboardApiError as error:
            st.error(str(error))

    with st.expander("Source classification and limitations"):
        st.markdown(
            "- **Fixture mode:** committed synthetic records with checksums and provenance under "
            "`data/`; suitable for deterministic demonstrations.\n"
            "- **Replay mode:** separate checksummed synthetic banking-stress records designed "
            "to exercise the unchanged organic trigger path.\n"
            "- **Live mode:** public GDELT and Bluesky adapters; availability and rate "
            "limits vary.\n"
            "- A failed live source is reported independently and is never replaced with "
            "fixture or replay data in the same run."
        )


def main() -> None:
    st.set_page_config(
        page_title="RiskSignal Monitor",
        page_icon="📉",
        layout="wide",
        initial_sidebar_state="auto",
    )
    _apply_styles()
    st.title("RiskSignal Monitor")
    st.caption("Explainable financial-risk signals and event-driven portfolio stress testing")

    api_url = os.getenv("RISK_ENGINE_API_URL", DEFAULT_API_URL)
    try:
        with st.spinner("Connecting to the RiskSignal API…"):
            health, status, portfolio, base_signals = _load_base(api_url)
    except (DashboardApiError, ValueError) as error:
        st.error(str(error))
        st.info(
            "Start the API with `python -m risk_engine serve`, then refresh this page. "
            f"Configured endpoint: `{api_url}`"
        )
        st.stop()

    event_type, min_impact, source, entity_id = _sidebar_filters(base_signals, health)
    try:
        filtered = _load_signals(api_url, event_type, min_impact, source, entity_id)
    except DashboardApiError as error:
        st.error(str(error))
        st.stop()

    signals_tab, stress_tab, sources_tab = st.tabs(["Risk signals", "Stress lab", "Source health"])
    with signals_tab:
        _render_signals(filtered, portfolio)
    with stress_tab:
        _render_stress_lab(api_url, filtered, portfolio)
    with sources_tab:
        _render_source_health(api_url, status)


if __name__ == "__main__":
    main()
