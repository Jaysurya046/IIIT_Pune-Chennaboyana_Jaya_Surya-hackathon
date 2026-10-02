# RiskSignal Engine - S&P Global & Crisil Campus Hackathon

**Candidate Name:** Chennaboyana Jaya Surya
**College Email ID:** 112315046@cse.iiitp.ac.in
**College / Campus:** Indian Institute of Information Technology, Pune
**Implementation Status:** Phase 6 complete - interactive monitoring dashboard ready
**Demo Video Link:** To be added after implementation
**Slide Deck Link:** To be added after implementation

## 1. Project Overview / Problem Statement & Approach

RiskSignal Engine is a modular financial-risk prototype that converts unstructured
news and social-media text into machine-readable risk signals. Each signal includes
a sentiment score, event classification, impact score, entity references, source
provenance, and an explanation of the factors that produced the score.

The first downstream application is strategic portfolio stress testing. Events with
an impact score greater than 7 trigger an appropriate scenario against a fictional
wholesale-banking portfolio containing loans, bonds, equities, and derivatives. The
application will show portfolio value and expected loss before and after the stress,
with breakdowns by issuer, sector, asset class, and instrument.

The implementation prioritizes a reproducible offline demonstration while retaining
live adapters for GDELT news and Bluesky public posts. Presentation slides and the
recorded walkthrough are intentionally deferred until the working prototype and its
results are stable.

## 2. Architecture & Tech Stack

The planned flow is:

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

Planned stack: Python 3.11, FastAPI, Pydantic, SQLite, Hugging Face
Transformers, Sentence Transformers, Pandas, Streamlit, Plotly, Pytest, and Ruff.
The full design and interface decisions are documented in
[docs/architecture.md](docs/architecture.md).

## 3. Dataset Used

- Live news metadata and headlines from the public GDELT DOC API.
- Live public social posts from the Bluesky AppView API.
- Small offline fixtures matching both source schemas for deterministic evaluation.
- A fully synthetic portfolio with fictional counterparties and transactions.

Every committed dataset or fixture will have a source URL or synthetic declaration,
retrieval details, transformations, redistribution notes, assumptions, and checksum
recorded under `data/`. No proprietary or confidential client data will be used.
See [data/README.md](data/README.md) and the machine-readable
[source manifest](data/sources.yaml) for the current provenance record.

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

With the API running, start the Phase 6 dashboard in a second terminal:

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

## Development Progress

Implementation status, verification evidence, decisions, and blockers are maintained
in [progress.md](progress.md). Each completed phase is delivered as a focused commit.
