# RiskSignal Engine - S&P Global & Crisil Campus Hackathon

**Candidate Name:** Chennaboyana Jaya Surya
**College Email ID:** 112315046@cse.iiitp.ac.in
**College / Campus:** Indian Institute of Information Technology, Pune
**Implementation Status:** Phase 0 complete - architecture and delivery roadmap defined
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

## 4. Quickstart & Installation

Runtime and exact commands will be added in Phase 1 after the executable application
scaffold is introduced. The planned runtime is Python 3.11.

## 5. Key Results & Domain Impact

Results will be populated from the tested implementation rather than estimated in
advance. Planned evidence includes NLP benchmark metrics, end-to-end processing time,
sample risk signals, and reconciled portfolio losses for triggered stress scenarios.

## Development Progress

Implementation status, verification evidence, decisions, and blockers are maintained
in [progress.md](progress.md). Each completed phase is delivered as a focused commit.
