# RiskSignal Engine - S&P Global & Crisil Campus Hackathon

**Candidate Name:** Chennaboyana Jaya Surya
**College Email ID:** 112315046@cse.iiitp.ac.in
**College / Campus:** Indian Institute of Information Technology, Pune
**Implementation Status:** Phase 8 complete - implementation and reproducibility baseline ready
**Demo Video Link:** To be added after implementation
**Slide Deck Link:** To be added after implementation

## 1. Project Overview / Problem Statement & Approach

RiskSignal Engine is a modular financial-risk prototype that converts unstructured
news and social-media text into machine-readable risk signals. Each signal includes
a sentiment score, event classification, impact score, entity references, source
provenance, and an explanation of the factors that produced the score.

The implemented downstream application is strategic portfolio stress testing. Events with
an impact score greater than 7 trigger an appropriate scenario against a fictional
wholesale-banking portfolio containing loans, bonds, equities, and derivatives. The
application shows portfolio value and expected loss before and after the stress,
with breakdowns by issuer, sector, asset class, and instrument.

The implementation prioritizes a reproducible offline demonstration while retaining
live adapters for GDELT news and Bluesky public posts. Presentation slides and the
recorded walkthrough are intentionally deferred until the working prototype and its
results are stable.

## 2. Architecture & Tech Stack

![RiskSignal Engine architecture](docs/architecture.png)

The implemented flow is:

```text
GDELT / Bluesky / fixtures
        -> normalization and deduplication
        -> entity resolution
        -> FinBERT sentiment + event classification
        -> explainable impact scoring
        -> SQLite + FastAPI
        -> portfolio stress engine
        -> Streamlit dashboard
```

Stack: Python 3.11–3.13, FastAPI, Pydantic, SQLite, Hugging Face
Transformers, Sentence Transformers, Pandas, Streamlit, Plotly, Pytest, and Ruff.
The full design and interface decisions are documented in
[docs/architecture.md](docs/architecture.md).

## 3. Dataset Used

- Live news metadata and headlines from the public GDELT DOC API.
- Live public social posts from the Bluesky AppView API.
- Small offline fixtures matching both source schemas for deterministic evaluation.
- A fully synthetic portfolio with fictional counterparties and transactions.

Every committed dataset or fixture has a source URL or synthetic declaration,
retrieval details, transformations, redistribution notes, assumptions, and checksum
recorded under `data/`. No proprietary or confidential client data is used.
See [data/README.md](data/README.md) and the machine-readable
[source manifest](data/sources.yaml) for the provenance record. The consolidated
[dataset and assumption guide](docs/dataset-guide.md) distinguishes public interfaces,
committed synthetic artifacts, optional models, and the claims each source can support.

## 4. Quickstart & Installation

Runtime: Python 3.11 through 3.13. CI verifies Python 3.11 on Ubuntu; local development
has been verified on Python 3.13 on Windows.

```bash
git clone https://github.com/Jaysurya046/IIIT_Pune-Chennaboyana_Jaya_Surya-hackathon.git
cd IIIT_Pune-Chennaboyana_Jaya_Surya-hackathon
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` on Windows PowerShell or
`source .venv/bin/activate` on macOS/Linux, then run:

```bash
python -m pip install -r requirements-dev.txt
python -m risk_engine check
python -m risk_engine ingest-fixtures --query "portfolio risk"
python -m risk_engine analyze-fixtures --query "portfolio risk"
python -m risk_engine stress-fixtures --query "portfolio risk"
python -m risk_engine validate --output data/runtime/validation-report.json
python -m ruff check .
python -m pytest
```

Copy `.env.example` to `.env` only when local overrides are required. Do not commit
the resulting `.env` file. The fixture commands exercise both source types through
validation, normalization, provenance capture, and deduplication without requiring
network access.

The analysis command defaults to a transparent deterministic NLP implementation. To
run the pinned FinBERT sentiment and MiniLM semantic event models, install the optional
dependencies and explicitly select model mode:

```bash
python -m pip install -r requirements-nlp.txt
python -m risk_engine analyze-fixtures --query "portfolio risk" --nlp-mode model
```

The first model-mode run downloads weights into the ignored cache directory. Exact
model revisions, license metadata, and limitations are recorded in
[data/models.yaml](data/models.yaml); downloaded weights are not committed.

Start the local API with:

```bash
python -m risk_engine serve --host 127.0.0.1 --port 8000
```

The interactive API documentation is then available at `http://127.0.0.1:8000/docs`.
The complete endpoint workflow and error semantics are documented in
[docs/api.md](docs/api.md). The default SQLite database is created under the ignored
`data/runtime/` directory.

With the API running, start the dashboard in a second terminal:

```bash
python -m risk_engine dashboard --host 127.0.0.1 --port 8501 --api-url http://127.0.0.1:8000
```

Open `http://127.0.0.1:8501`. On an empty database, use **Source health** to run the
explicit fixture ingestion and deterministic analysis workflow. The dashboard guide,
filter behavior, metric definitions, and source classifications are documented in
[docs/dashboard.md](docs/dashboard.md).

The GDELT adapter is credential-free. Bluesky search availability varies by AppView;
when authentication is required, provide a short-lived bearer token only through the
ignored `RISK_ENGINE_BLUESKY_BEARER_TOKEN` environment setting.

## 5. Key Results & Domain Impact

The deterministic NLP regression set contains eight synthetic cases covering every
event category. The Phase 4 portfolio contains eight fictional positions across four
asset classes. In the tested issuer credit-event scenario, the two Northstar Energy
positions move from a portfolio total of USD 55.50 million to USD 53.15 million: a
USD 2.35 million illustrative loss, including a USD 0.30 million expected-loss
increase. Instrument losses reconcile exactly to the portfolio result.

These figures demonstrate the implemented calculations against synthetic assumptions;
they are not forecasts, calibrated regulatory stress results, or investment advice.
Phase 5 exposes the complete offline workflow through nine documented HTTP endpoints
and preserves ingestion runs, source status, signals, entity indexes, and stress
decisions across process restarts.

Phase 6 adds a typed API-backed monitoring interface with global event, impact, source,
and entity filters; source provenance and score explanations; an explicit stress
trigger; exact asset-class, sector, issuer, and instrument reconciliation; and clear
labels for all synthetic fixture, portfolio, and scenario outputs.

Phase 7 adds a repeatable offline validation command covering source-manifest
integrity, the synthetic NLP golden set, the full persisted workflow, independently
recomputed portfolio and stress totals, failure paths, dashboard filter/reset behavior,
and a bounded performance check. The baseline and its interpretation limits are in
[docs/validation.md](docs/validation.md).

The final implementation delivers two optional live adapters, six committed fixture
records, eight event categories, a USD 55.50 million synthetic portfolio, nine API
endpoints, and three dashboard workspaces. The recorded offline baseline matched all
seven artifact checksums and all eight authored NLP cases, recovered all six persisted
signals after reopening SQLite, and reconciled the boundary-probe stress result to
USD 0.00 difference. These are synthetic regression and implementation results, not
real-world accuracy, market forecasts, or investment advice.

The complete evidence and interpretation are in [docs/results.md](docs/results.md).

## Reviewer Guide

- [Reproducible implementation guide](docs/implementation-guide.md) — clean setup,
  complete run path, optional modes, quality gates, and troubleshooting.
- [Architecture decisions](docs/architecture.md) — components, contracts, scoring,
  valuation, persistence, reliability, and scope boundaries.
- [Dataset source and assumption guide](docs/dataset-guide.md) — public interfaces,
  synthetic artifacts, transformations, redistribution, and limitations.
- [Validation evidence](docs/validation.md) — independent checks, recorded baseline,
  failure paths, and caveats.
- [Results and domain impact](docs/results.md) — implemented capability, evidence,
  usefulness, limitations, and next steps.
- [Demonstration runbook](docs/demo-script.md) — separate five-minute live and
  up-to-ten-minute recorded walkthroughs.
- [Post-implementation improvement plan](docs/improvement-plan.md) — Phases 9–20,
  task dependencies, data gates, tests, commands, and conventional commits.
- [API guide](docs/api.md) and [dashboard guide](docs/dashboard.md) — operational
  contracts, filters, metrics, and error semantics.

Presentation and YouTube recording remain intentionally deferred. When created, the
deck will be limited to five–seven slides and the unlisted YouTube link and deck link
will replace the placeholders at the top of this README. Both links and the public
repository must be tested from an incognito window before submission.

## Development Progress

Implementation status, verification evidence, decisions, and blockers are maintained
in [progress.md](progress.md). Each completed phase is delivered as a focused commit.
