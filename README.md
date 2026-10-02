# RiskSignal Engine - S&P Global & Crisil Campus Hackathon

**Candidate Name:** Chennaboyana Jaya Surya
**College Email ID:** 112315046@cse.iiitp.ac.in
**College / Campus:** Indian Institute of Information Technology, Pune
**Implementation Status:** Phase 2 complete - news and social ingestion pipeline ready
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
python -m ruff check .
python -m pytest
```

Copy `.env.example` to `.env` only when local overrides are required. Do not commit
the resulting `.env` file. Live ingestion and dashboard commands will be added with
their implementation phases. The fixture command currently exercises both source
types through validation, normalization, provenance capture, and deduplication without
requiring network access.

The GDELT adapter is credential-free. Bluesky search availability varies by AppView;
when authentication is required, provide a short-lived bearer token only through the
ignored `RISK_ENGINE_BLUESKY_BEARER_TOKEN` environment setting.

## 5. Key Results & Domain Impact

Results will be populated from the tested implementation rather than estimated in
advance. Planned evidence includes NLP benchmark metrics, end-to-end processing time,
sample risk signals, and reconciled portfolio losses for triggered stress scenarios.

## Development Progress

Implementation status, verification evidence, decisions, and blockers are maintained
in [progress.md](progress.md). Each completed phase is delivered as a focused commit.
