# Dashboard Guide

## Purpose and Audience

RiskSignal Monitor is the decision-support interface for analysts evaluating
unstructured financial-risk signals and their illustrative portfolio effects. It is a
local Streamlit application and a read/write client of the versioned FastAPI service;
it does not calculate signals, scenarios, or valuations itself.

The dashboard answers three distinct questions:

1. **Risk signals:** What events are present, how severe are they, and why did the
   engine assign each impact score? How do those signals unfold by publication time?
2. **Stress lab:** Does a selected signal pass the configured trigger, and how does its
   mapped scenario affect the synthetic portfolio, and which instruments contribute to
   the reconciled loss? What would happen under separately labeled, user-selected
   hypothetical assumptions?
3. **Source health:** Which sources completed, what was accepted or rejected, and when
   did the latest ingestion finish?

## Start the Local Application

Install the declared dependencies and start the API in the first terminal:

```bash
python -m pip install -r requirements-dev.txt
python -m risk_engine serve --host 127.0.0.1 --port 8000
```

Start the dashboard in a second terminal:

```bash
python -m risk_engine dashboard --host 127.0.0.1 --port 8501 --api-url http://127.0.0.1:8000
```

Open `http://127.0.0.1:8501`. The API address can also be supplied through
`RISK_ENGINE_API_URL`. The dashboard shows a bounded error state with the start command
when the API is unavailable; it does not expose response bodies or credentials.

On a new database, open **Source health**. Select the explicit `deterministic` or `model`
NLP mode, then choose **Ingest and analyze fixtures** for the six-record baseline or
**Ingest and analyze synthetic replay** for the separate four-record banking-stress
scenario. Model mode requires the optional dependencies and pinned weights; a failure
is shown and never falls back to rules. Use **Refresh dashboard** to invalidate the
15-second view cache immediately.

## Data Sources and Classification

| Displayed data | System of record | Classification | Update behavior |
|---|---|---|---|
| Signals, explanations, entities, provenance | `GET /api/v1/signals` | Synthetic fixture/replay or live public source, per signal | API query; 15-second dashboard cache |
| Source outcomes | `GET /api/v1/sources/status` | Operational metadata | Latest persisted ingestion run |
| Portfolio baseline | `GET /api/v1/portfolio/summary` | Fully synthetic | Versioned project configuration |
| Stress decision and result | `POST /api/v1/stress-tests` | Synthetic scenario output | On analyst request; persisted by API |
| Hypothetical what-if | `POST /api/v1/stress-tests/what-if` | User-selected hypothetical assumptions | In-memory response only; never persisted |

Committed fixture and replay records include source-shaped metadata, explicit
`synthetic=true` provenance, and checksums documented in `data/`. Replay records use
fictional issuers and reserved `.example` domains. A live-source failure is never
silently replaced with either synthetic mode.

## Metric Definitions

| Metric | Definition |
|---|---|
| Matching signals | API result count after all sidebar filters |
| Impact greater than 7 | Visible signals whose integer impact score strictly exceeds the stress trigger |
| Mean impact | Arithmetic mean of visible impact scores on the documented 1–10 scale |
| Synthetic exposure | Total baseline market value returned by the portfolio summary endpoint |
| Before / after | Sum of instrument values before and after the configured scenario |
| Illustrative loss | `before value - after value`; reconciled to instrument losses within USD 0.01 |
| Expected-loss change | Stressed minus baseline loan expected loss |

The signal filters are dashboard-wide: event type, minimum impact, source, and entity
are passed to the API and constrain both the signal register and Stress Lab selector.
Chart tooltips and the exact-value tables expose the same filtered grain. The dashed
impact line at 7 marks the trigger boundary; it does not imply causality between
sentiment and impact.

The **Signal publication timeline** uses source `published_at` in UTC on the x-axis,
integer impact on the y-axis, and a stable color for each event type. Points are ordered
chronologically and retain entity, source, synthetic classification, and signal ID in
their hover evidence. The chart responds to the same API-backed sidebar filters as the
signal register and Stress Lab selector.

## Stress Result Interpretation

The Stress Lab keeps two paths visibly separate. The **Hypothetical what-if** panel has
event, portfolio-entity, and impact controls beneath a persistent warning. Its response
is flagged hypothetical and remains only in dashboard session state; it never appears
in the signal register or persisted stress-result endpoints.

The **Observed or replay signal stress** path records the trigger decision. Scores of 7 or below produce an
auditable skipped decision. Scores above 7 apply the event's configuration-owned
scenario. Result cards, asset-class values, issuer losses, instrument rows, and applied
shocks all come from that single persisted API response.

Asset-class, sector, issuer, and instrument views independently reconcile to the same
portfolio total. Stress values are simplified demonstration results, not forecasts,
investment advice, or calibrated regulatory capital estimates. Model and valuation
limitations are documented in `data/README.md` and `docs/architecture.md`.

The **Illustrative loss waterfall by instrument** orders positive loss contributions
from largest to smallest. Relative bars accumulate to the final **Reconciled total**;
zero-loss instruments remain visible so the complete eight-position population is not
silently narrowed. The adjacent exact-value tables provide the source amounts at cent
precision.

## Evidence Screenshots

The four committed images were captured from the local API and Streamlit application at
1440 x 1000 pixels after loading the six fixture and four replay signals. No live or
proprietary data appears in them.

- [Signal timeline](img/risk-signal-timeline.png) — filtered publication-time evidence
  with the synthetic-data disclosure and strict trigger reference.
- [Source health](img/source-health.png) — the explicit two-source synthetic replay run.
- [Organic stress result](img/organic-stress-result.png) — the unchanged impact-9 replay
  path and its reconciled instrument waterfall.
- [Hypothetical what-if](img/hypothetical-what-if.png) — non-persisted controls with the
  warning and synthetic-scenario disclosure.

## Verification

Dashboard tests cover typed HTTP contracts, query filters, sanitized failures, metric
and grouping transformations, timeline semantics, waterfall ordering, exact stress
reconciliation, figure labels, and CLI launch construction. The release walkthrough
renders the populated Streamlit script
against a real local API seeded from fixture and replay source types. It verifies
hypothetical warnings and controls, skipped and triggered what-if states, the organic
impact-9 persisted path, filter/reset behavior, KPI cards, and evidence tables.
Phase 14 additionally inspected all affected views at 1440 x 1000 and 760 x 1000:
marks, legends, disclosures, amounts, wrapping, and waterfall labels remained visible;
the narrow layout stacked KPI and chart columns without horizontal page overflow.
