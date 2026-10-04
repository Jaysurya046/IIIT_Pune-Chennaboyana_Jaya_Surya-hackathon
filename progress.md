# Implementation Progress

Last updated: 2026-10-04

## Phase Status

| Phase | Status | Deliverables | Verification | Planned Commit |
|---|---|---|---|---|
| 0 Architecture and roadmap | complete | Requirements, architecture decisions, scope, progress tracker, README baseline | Documentation review and `git diff --check` | `docs: define project architecture and implementation roadmap` |
| 1 Application scaffold | complete | Python package, configuration, dependencies, test tooling, CI | Import smoke test, Ruff, Pytest | `chore: scaffold risk engine and quality gates` |
| 2 Data ingestion | complete | GDELT, Bluesky and fixture adapters, normalization, deduplication, provenance | Adapter and normalization tests | `feat(data): ingest and normalize news and social text` |
| 3 NLP risk engine | complete | Entity resolution, sentiment, event classification, impact scoring | Golden NLP fixtures and boundary tests | `feat(nlp): generate explainable financial risk signals` |
| 4 Stress engine | complete | Synthetic portfolio, scenario matrix, valuation and reconciliation | Asset-level and portfolio-level tests | `feat(stress): simulate event driven portfolio losses` |
| 5 API and persistence | complete | SQLite repositories and versioned FastAPI endpoints | API contract and persistence tests | `feat(api): expose risk signals and stress results` |
| 6 Dashboard | complete | Signal monitor and portfolio stress views | Dashboard contract tests and rendered walkthrough | `feat(ui): add risk monitoring and stress dashboard` |
| 7 Validation | complete | End-to-end tests, benchmark, failure and performance checks | Offline suite and recorded metrics | `test: validate the complete risk intelligence workflow` |
| 8 Implementation documentation | complete | Final quickstart, architecture image, dataset guide, results and demo script | Clean-clone rehearsal | `docs: finalize reproducible implementation guide` |
| 9 Deterministic as-of time (P0 T1) | complete | Stable fixture/replay recency and scores | Frozen-time NLP, API, CLI and validation tests | `fix(nlp): anchor replay recency to batch time` |
| 10 Organic replay trigger (P0 T2) | complete | New synthetic replay mode and natural 8+ signal | Exact-score replay, API, CLI and AppTest coverage | `feat(replay): add organic high-impact stress scenario` |
| 11 Hypothetical what-if (P0 T3) | complete | Non-persisted what-if API and dashboard panel | API, persistence, stress and AppTest coverage | `feat(stress): add hypothetical what-if simulation` |
| 12 Real-data benchmark (P1 T4) | complete | External CSV evaluation and documented metrics | Metric, CLI, failure and real-data evidence | `feat(benchmark): compare deterministic and model NLP quality` |
| 13 Model-mode hygiene (P1 T5) | complete | Cached embeddings, batched sentiment, warm-up and mode UI | NLP, API, benchmark and dashboard tests | `perf(nlp): batch model inference and expose mode controls` |
| 14 Dashboard evidence (P1 T6) | complete | Timeline, loss waterfall and screenshots | Chart contracts, AppTest and rendered checks | `feat(ui): add timeline waterfall and evidence screenshots` |
| 15 Assumption honesty (P1 T7) | planned | Sentiment-direction and DV01 disclosures | UI-state and documentation tests | `docs(risk): clarify directional and valuation assumptions` |
| 16 Release and demo hygiene (P1 T8) | planned | Version sync, docs move, CI matrix, presentation and demo command | CLI lifecycle, PDF, clean-clone and CI checks | `chore(release): finalize demo workflow and repository hygiene` |
| 17 Deterministic NLP robustness (P2 T9) | optional | Suffix and negation rules, ambiguous-token removal | NLP, dashboard and benchmark comparison | `fix(nlp): improve deterministic matching and negation` |
| 18 Live path and sector proxy (P2 T10) | optional | Watchlist queries, public snapshot and illustrative mapping | Mocked live, provenance and stress tests | `feat(data): strengthen live ingestion and sector proxy stress` |
| 19 Streaming and polling (P2 T11) | optional | SSE, auto-stress and bounded polling | Streaming, idempotency and lifecycle tests | `feat(api): stream signals and automate stress decisions` |
| 20 Portfolio generator (P2 T12) | optional-blocked | Seeded 200-position synthetic generator | Determinism, privacy and reconciliation tests | `feat(portfolio): generate reproducible synthetic portfolios` |

## Current Phase

The original eight implementation phases, P0 improvement Phases 9–11, and P1 Phases
12–14 are complete. Phase 15 is next: assumption honesty. Phases 15–16 are the remaining
P1 improvement path; Phases 17–20 are optional P2 work. Phase 20 is blocked until a
permitted transaction dataset is supplied. The detailed sequence and task gates are
in [docs/improvement-plan.md](docs/improvement-plan.md).

## Decisions

- Build the unified NLP risk engine and Module B strategic portfolio stress testing.
- Use GDELT news and Bluesky public posts as the two live source types.
- Provide committed offline fixtures for deterministic tests and demonstrations.
- Use FinBERT for financial sentiment and sentence embeddings for event classification.
- Use an explainable weighted impact score and retain its component factors.
- Trigger stress testing only when the impact score is greater than 7.
- Use a fully synthetic portfolio with fictional issuers and configurable scenarios.
- Use SQLite, FastAPI, and Streamlit for a locally reproducible prototype.
- Keep presentation and video work deferred until implementation results are stable.
- Preserve `data/sample/*.json` byte-for-byte throughout the improvement program.
- Use one numbered phase and one conventional commit for each improvement task.
- Treat replay, fixtures, live data, model mode, and hypothetical simulation as explicit
  non-interchangeable modes with no silent fallback.
- Anchor fixture/replay recency to the latest batch retrieval time; keep live analysis
  on its timezone-aware UTC clock.
- Keep the six-record fixture mode unchanged and use a distinct four-record synthetic
  replay mode for the organic stress-trigger demonstration.
- Keep hypothetical assumptions and results outside signal and stress-decision
  persistence, with explicit API and dashboard labels separating them from evidence.
- Keep organizer-provided DOCX files out of the implementation repository; their
  requirements are captured in the README and architecture decision record.

## Verification Log

### 2026-10-02 Phase 0

- Reviewed the problem statement and submission guidelines in full.
- Confirmed the Git remote targets the named hackathon repository.
- Captured functional requirements, data-governance constraints, architecture,
  interfaces, test strategy, scope boundaries, and phased commit history.
- Verified the documentation patch with `git diff --check` before commit.

### 2026-10-02 Phase 1

- Added an installable `src`-layout Python package and diagnostic CLI.
- Added validated environment configuration with safe offline defaults.
- Added consistent logging configuration and a documented environment template.
- Added Pytest and Ruff configuration, smoke tests, and Python 3.11 GitHub Actions CI.
- Verified locally on Python 3.13: configuration check passed, Ruff reported no
  findings, and all 8 Pytest tests passed.

### 2026-10-02 Phase 2

- Added strict Pydantic contracts for source records, normalized documents,
  provenance, ingestion requests, and per-source outcomes.
- Added live GDELT DOC and Bluesky AppView adapters with bounded requests, safe error
  messages, response validation, dependency injection, and mocked contract tests.
- Added deterministic synthetic news and social fixtures with documented provenance
  and SHA-256 checksums.
- Added Unicode and URL normalization, maximum-text validation, stable identifiers,
  content hashes, and within-source deduplication that preserves cross-source evidence.
- Added failure-isolated orchestration and an offline CLI ingestion command.
- Verified locally on Python 3.13: Ruff reported no findings, all 21 Pytest tests
  passed, and the offline command produced six normalized documents from two sources.
- Live smoke requests reached both configured services. GDELT returned HTTP 429 and
  Bluesky returned HTTP 403 without credentials, confirming the need for bounded
  retries, optional Bluesky authentication, source-level error reporting, and the
  deterministic offline path.

### 2026-10-02 Phase 3

- Added strict contracts for issuer matches, sentiment, event classifications,
  weighted impact factors, and fully traceable risk signals.
- Added versioned fictional issuer resolution, a transparent sentiment baseline,
  keyword event classification, and an explicit `Other` fallback.
- Added lazy adapters for the pinned FinBERT and MiniLM revisions without requiring
  model dependencies or downloads during CI.
- Implemented the documented 1-10 impact formula, 72-hour recency decay, and
  cross-source corroboration in a deterministic two-pass pipeline.
- Added a synthetic eight-case golden set covering every event category and recorded
  checksums, assumptions, revisions, licensing metadata, and limitations.
- Added an offline `analyze-fixtures` command that produces six explainable signals
  from the two source types.
- Verified locally on Python 3.13: Ruff reported no findings and all 38 Pytest tests
  passed without network access or downloaded model weights.

### 2026-10-02 Phase 4

- Added a versioned synthetic USD portfolio with eight positions covering loans,
  bonds, equities, and derivatives across the four fictional issuers.
- Added a versioned scenario matrix mapping every event category to explicit,
  project-authored shocks and portfolio-wide or resolved-entity scope.
- Implemented Decimal-based duration, expected-loss, direct equity shock, delta, and
  DV01 calculations with monetary rounding to cents.
- Added strict `StressDecision`, `StressResult`, and instrument-result contracts,
  configurable impact-score triggering, stable identifiers, and scenario provenance.
- Enforced portfolio-to-instrument loss reconciliation within USD 0.01 and retained
  before/after expected loss for loan positions.
- Added the `stress-fixtures` offline command and documented all synthetic assumptions
  and checksums.
- Verified locally on Python 3.13: Ruff reported no findings and all 52 Pytest tests
  passed without network access.

### 2026-10-02 Phase 5

- Added a schema-versioned SQLite repository using transactions, foreign keys, stable
  identifiers, normalized filter indexes, and validated full-payload reconstruction.
- Persisted ingestion runs, source outcomes, risk signals, resolved-entity indexes,
  stress trigger decisions, and triggered stress results across process restarts.
- Added the versioned FastAPI service with health, source status, ingestion, analysis,
  signal list/detail, stress run/detail, and portfolio summary endpoints.
- Added pagination and event, impact, source, and entity filters with explicit HTTP
  404, 409, and 422 behavior.
- Enforced explicit fixture/live source selection so offline mode never silently makes
  network requests or substitutes fixtures for failed live calls.
- Added the `serve` CLI command, interactive OpenAPI documentation, and a durable API
  workflow guide.
- Verified locally on Python 3.13: Ruff reported no findings, all 61 Pytest tests
  passed, dependency checks succeeded, and the offline API workflow required no
  network access.

### 2026-10-02 Phase 6

- Added a typed, sanitized HTTP client so the Streamlit layer consumes the Phase 5 API
  without duplicating ingestion, NLP, persistence, or stress orchestration.
- Added global event, impact, source, and entity filters with KPI, event-distribution,
  sentiment/impact, exact-value, explanation, and provenance views.
- Added a Stress Lab that records trigger decisions and displays aggregate values,
  expected loss, applied assumptions, and reconciled asset-class, sector, issuer, and
  instrument breakdowns from one persisted API response.
- Added source-health monitoring and an explicit fixture-only ingestion plus
  deterministic-analysis workflow for reproducible first-run data.
- Labeled fixture records, portfolio exposure, and stress scenarios as synthetic and
  documented source systems, metric definitions, update behavior, and limitations.
- Added the `dashboard` CLI command, current Streamlit/Pandas/Plotly dependencies, API
  URL configuration, dashboard guide, and expanded architecture decisions.
- Verified the populated dashboard against a real local API: the rendered script had
  three task tabs, seven KPI cards, and source-backed evidence tables without runtime
  exceptions.
- Verified locally on Python 3.13: Ruff reported no findings, all 69 Pytest tests
  passed, and the installed dependency set passed `pip check`.

### 2026-10-03 Phase 7

- Added a strict machine-readable validation report and the `validate` CLI command
  with a configurable performance budget and optional ignored JSON output.
- Recalculated SHA-256 checksums for seven declared data/configuration artifacts and
  validated explicit classification, safe paths, six unique source IDs, source timing,
  non-empty content, and two synthetic fixture bundles.
- Independently evaluated all eight synthetic golden cases: every event category was
  covered and all expected event, sentiment, and entity-set outputs matched.
- Exercised both fixture sources through normalization, deterministic NLP, SQLite
  persistence, database reopen, signal recovery, an impact-8 trigger probe, and stress
  result recovery without network access.
- Independently summed the raw USD 55.50 million portfolio and reconciled asset-class,
  sector, issuer, instrument, before/after, and loss totals to USD 0.00 difference.
- Added tests for fixture tampering, corrupt input redaction, missing model dependencies
  without fallback, incompatible database schemas, validation CLI output, and the
  populated dashboard's Operational filter, reset, and stress-decision interaction.
- Rendered the dashboard at 1600 and 800 pixels, confirmed both charts and all four
  event bars, removed narrow-width compression by stacking analytical columns while
  keeping sidebar filters available, and rechecked horizontal overflow.
- Added the offline validation benchmark to CI and documented methods, observed values,
  scope boundaries, and explicit synthetic/real-world caveats.
- Recorded a 0.119-second local deterministic validation run against a 5-second budget;
  this is a reproducibility baseline, not a production performance SLA.
- Verified the completed phase locally: Ruff reported no findings, all 77 Pytest tests
  passed, the installed package reports version 0.7.0, and `pip check` found no broken
  requirements. One upstream Starlette test-client deprecation warning remains.

### 2026-10-03 Phase 8

- Rechecked the original problem statement and submission guidelines, including the
  public-repository, dataset-clarity, incremental-history, five-minute live demo, and
  up-to-ten-minute recorded walkthrough requirements.
- Added a reviewer-ready implementation guide with clean installation, offline proof,
  service startup, optional live/model modes, quality gates, runtime reset, and
  troubleshooting instructions.
- Added an 1800x1050 architecture PNG and editable SVG showing both source types,
  ingestion, explainable NLP, persistence, API, stress engine, dashboard, provenance,
  and validation responsibilities; visually inspected the final raster output.
- Added a dataset guide that separates public live interfaces from every committed
  synthetic or project-authored artifact and records use, transformation, retention,
  model, portfolio, scenario, and change assumptions.
- Consolidated implemented results and domain impact without presenting the synthetic
  exact-match set as real-world accuracy or the illustrative stress output as advice.
- Added separate five-minute live and up-to-ten-minute recorded demonstration runbooks,
  including setup, disclosure, likely jury questions, and future link-access checks.
- Refreshed the mandatory README sections, embedded the architecture image, added a
  reviewer documentation index, and retained explicit deck and video placeholders.
- Added automated checks for required Phase 8 artifacts, README structure, local links,
  high-resolution PNG dimensions, dataset disclosures, and both demo time limits.
- Bumped the implementation version to 0.8.0 and verified locally: all 83 Pytest tests
  passed, Ruff reported no findings, `pip check` found no broken requirements, and the
  offline validation benchmark passed. One upstream Starlette warning remains.
- Rehearsed the committed Phase 8 snapshot from an independent clean clone and Python
  3.13 virtual environment using the declared requirements. The configuration check, Ruff, all 83
  tests, `pip check`, and the offline validator passed; the clean-clone validator took
  0.179 seconds against its 5-second budget and reconciled stress loss to USD 0.00.

### 2026-10-03 Improvement Baseline and Roadmap

- Confirmed the working tree started clean at commit `632bab7` before planning changes.
- Ran Ruff successfully with no findings.
- The first plain Pytest invocation encountered only a managed-shell permission error
  at `C:\Users\jayas\AppData\Local\Temp\pytest-of-jayas`; 69 tests passed before 14
  temporary-directory fixtures errored and no assertion failed.
- Reran the unchanged full suite with `--basetemp data/runtime/improvements-baseline`:
  all 83 tests passed with one upstream Starlette deprecation warning.
- Ran the offline validator successfully: all 7 manifested artifacts matched, all 6
  signals persisted, portfolio value was USD 55.50 million, stress reconciliation
  difference was USD 0.00, and total runtime was 0.118 seconds.
- Added the Phase 9–20 roadmap with one task and one conventional commit per phase,
  mandatory post-task gates, deliberate manifest-count changes, and explicit gates for
  the real benchmark, presentation PDF, checked regression data, and transaction input.
- Verified the roadmap change with Ruff, all 83 tests, the offline validator, and
  `git diff --check`. The validator again matched 7/7 artifacts, persisted 6/6 signals,
  reconciled to USD 0.00, and completed in 0.121 seconds.

### 2026-10-03 Phase 9

- Added an optional, timezone-aware `as_of` argument to `RiskSignalEngine.analyze` and
  normalized it to UTC before using the same value for recency and signal creation.
- Added a strict synthetic-batch policy that selects the maximum document retrieval
  timestamp and rejects mixed or live provenance instead of silently using wall time.
- Applied the policy to API fixture/replay analysis, fixture CLI commands, persistence
  tests, and the complete offline validator; live analysis retains the engine clock.
- Added regression tests proving identical signals with clocks ten years apart, clear
  rejection of naive timestamps, stable API and CLI timestamps, and live-clock use.
- Left all checksummed sample fixtures and the seven-artifact source manifest unchanged.
- Passed the mandatory Phase 9 gate: Ruff reported no findings, all 86 Pytest tests
  passed with one upstream Starlette warning, and the offline validator matched 7/7
  artifacts, persisted 6/6 signals, reconciled to USD 0.00, and completed in 0.165
  seconds against its 5-second budget.

### 2026-10-03 Phase 10

- Started from clean synchronized commit `480d0d4`; Ruff passed, all 86 baseline tests
  passed with one upstream Starlette warning, and validation passed with 7/7 artifacts,
  6/6 persisted fixture signals, USD 0.00 reconciliation difference, and 0.150 seconds
  total runtime.
- Added two checksummed replay bundles containing four hand-authored fictional records
  on reserved `.example` domains. Every record identifies its general March 2023
  banking-stress inspiration and confirms that no article or post text was copied.
- Added explicit `replay` source selection to the API, a deterministic `replay` CLI
  command, and a separate dashboard ingestion action without changing fixture mode.
- Confirmed the unchanged deterministic engine resolves fictional Aurora Bank,
  classifies all four records as `Credit Event`, and produces exact scores `[9, 9, 9,
  9]`; all four signals organically trigger the issuer-credit scenario without score
  mutation and produce a reconciled illustrative loss of USD 3,747,000.00.
- Expanded source integrity from seven to nine manifested artifacts and added exact
  NLP-factor, API persistence, CLI, provenance, and Streamlit Stress Lab coverage.
- Left `data/sample/gdelt_articles.json` and `data/sample/bluesky_posts.json` untouched.
- Passed the mandatory Phase 10 gate: Ruff reported no findings, all 90 Pytest tests
  passed with one upstream Starlette warning, and the offline validator matched 9/9
  artifacts, preserved the 6/6 fixture workflow, reconciled to USD 0.00, and completed
  in 0.196 seconds against its 5-second budget.

### 2026-10-04 Phase 11

- Started from clean synchronized commit `1410d6a`; Ruff passed, all 90 baseline tests
  passed with one upstream Starlette warning, and validation passed with 9/9 artifacts,
  6/6 persisted fixture signals, USD 0.00 reconciliation difference, and 0.247 seconds
  total runtime.
- Added `POST /api/v1/stress-tests/what-if` with strict event, unique portfolio-entity,
  and impact assumptions; invalid contracts return HTTP 422 and unknown entities return
  HTTP 404.
- Reused the existing trigger, scenario, valuation, and reconciliation calculations
  through a stable in-memory hypothetical reference without constructing a risk signal.
- Kept hypothetical requests outside SQLite: no signal, stress-decision, or stress-result
  row is written, and a hypothetical result ID is not retrievable from the persisted API.
- Added a separate warned Stress Lab panel with event, entity, and impact controls,
  skipped and triggered states, and panel-specific rendering keys so hypothetical and
  observed/replay results can coexist without UI collisions.
- Added stress-engine, API, typed-client, and real Streamlit AppTest coverage while
  leaving all nine checksummed artifacts and `data/sample/*.json` untouched.
- Passed the mandatory Phase 11 gate: Ruff reported no findings, all 99 Pytest tests
  passed with one upstream Starlette warning, and the offline validator matched 9/9
  artifacts, persisted 6/6 fixture signals, reconciled to USD 0.00, and completed in
  0.238 seconds against its 5-second budget.

### 2026-10-04 Phase 12

- Started from clean synchronized commit `84fc8b0`; Ruff passed, all 99 baseline tests
  passed with one upstream Starlette warning, and validation passed with 9/9 artifacts,
  6/6 persisted fixture signals, USD 0.00 reconciliation difference, and 0.240 seconds
  total runtime.
- Added a strict external-CSV benchmark command with named and numeric label
  normalization, local accuracy/macro-F1/confusion calculations, JSON and Markdown
  outputs, input hashing, and explicit errors instead of model fallback.
- Selected Financial PhraseBank v1.0 `sentences_allagree` at immutable dataset commit
  `598b6aad98f7c8d67be161b12a4b5f2497e07edd` under CC BY-NC-SA 3.0. The raw archive
  and derived 2,264-row CSV remain ignored and uncommitted.
- Verified archive SHA-256 `0e1a06c4900fdae46091d031068601e3773ba067c7cecb5b0da1dcba5ce989a6`
  and local CSV SHA-256 `a7a3128b1380b32d27f28b29c5f57c662492fd6ae6293a778d02593ef5bedae1`.
- Recorded deterministic accuracy/macro-F1 of 0.6767/0.4302 and pinned FinBERT results
  of 0.9717/0.9625, with full class counts and confusion matrices. Documented that
  Financial PhraseBank was used to fine-tune the published model, so its score is not
  an out-of-sample generalization estimate.
- Added 14 offline benchmark tests covering metrics, ordering, label mappings, malformed
  input, output files, and explicit model failure; CI performs no model or dataset
  download.
- Left all nine checksummed artifacts and `data/sample/*.json` untouched.
- Passed the mandatory Phase 12 gate: Ruff reported no findings, all 114 Pytest tests
  passed with one upstream Starlette warning, and the offline validator matched 9/9
  artifacts, persisted 6/6 fixture signals, reconciled to USD 0.00, and completed in
  0.198 seconds against its 5-second budget.

### 2026-10-04 Phase 13

- Started from clean synchronized commit `7c2c998`; Ruff passed, all 114 baseline tests
  passed with one upstream Starlette warning, and validation passed with 9/9 artifacts,
  6/6 persisted fixture signals, USD 0.00 reconciliation difference, and 0.216 seconds
  total runtime.
- Added ordered sentiment batching to both implementations; FinBERT now receives one
  list per engine analysis instead of one pipeline call per document.
- Cached all eight MiniLM taxonomy-description embeddings once per classifier and then
  encoded only one incoming document at a time. Repeated classification and warm-up
  reuse the cached category vectors.
- Added `serve --warm-models`, which loads FinBERT and MiniLM before API startup and
  propagates dependency, weight, and model errors without deterministic fallback.
- Added one dashboard NLP-mode selector shared by the fixture and replay actions, with
  explicit model prerequisites, selected-mode status text, and no hidden fallback.
- Extended the real-data benchmark through the full risk-signal engine. Both modes
  triggered 0/2,264 rows above the configured threshold of 7 under fixed, non-persisted
  external benchmark provenance; sentiment accuracy and macro-F1 remained unchanged.
- Documented that the zero trigger rate is descriptive pipeline behavior rather than a
  labelled quality result because Financial PhraseBank contains sentiment labels only.
- Left all nine checksummed artifacts and `data/sample/*.json` untouched.
- Replayed the 2,264-row benchmark with both model providers forced offline; local caches
  reproduced the documented accuracy, macro-F1, confusion, and 0/2,264 trigger results in
  251.6 seconds without network access.
- Passed the mandatory Phase 13 gate: Ruff reported no findings, all 120 Pytest tests
  passed with one upstream Starlette warning, and the offline validator matched 9/9
  artifacts, persisted 6/6 fixture signals, reconciled to USD 0.00, and completed in
  0.122 seconds against its 5-second budget.

### 2026-10-04 Phase 14

- Started from clean synchronized commit `6cad661`; Ruff passed, all 120 baseline tests
  passed with one upstream Starlette warning, and validation passed with 9/9 artifacts,
  6/6 persisted fixture signals, USD 0.00 reconciliation difference, and 0.125 seconds
  total runtime.
- Added a chronological signal timeline using source publication time in UTC, impact on
  the 1–10 scale, stable event colors, filtered provenance tooltips, and the strict
  impact-greater-than-7 stress reference.
- Added a descending horizontal instrument-loss waterfall with all eight instruments,
  non-negative contributions, an exact reconciled-total bar, readable labels, and an
  adjacent synthetic or hypothetical classification.
- Added unit and real Streamlit AppTest coverage for timeline semantics and empty state,
  waterfall ordering/signs/cent-level reconciliation, chart counts, and observed versus
  hypothetical disclosure text; 15 focused tests passed.
- Captured four 1440 x 1000 API-backed screenshots for signal evidence, replay source
  health, organic triggered stress, and hypothetical controls; each visibly identifies
  synthetic or hypothetical content and is used in the README.
- Inspected every affected view at 1440 x 1000 and 760 x 1000. The review confirmed
  responsive stacking, visible marks and legends, readable dates and currency labels,
  explicit empty/filter scope, and no horizontal page overflow.
- Left all nine checksummed artifacts and `data/sample/*.json` untouched.
- Passed the mandatory Phase 14 gate: Ruff reported no findings, all 124 Pytest tests
  passed with one upstream Starlette warning, and the offline validator matched 9/9
  artifacts, persisted 6/6 fixture signals, reconciled to USD 0.00, and completed in
  0.132 seconds against its 5-second budget.

## Risks and Blockers

- Live public APIs can be unavailable or rate-limited; offline fixtures are mandatory.
- Bluesky `searchPosts` may require provider-specific authentication; the live adapter
  supports an optional environment-supplied bearer token and never logs or displays it.
- First-run model downloads may be slow; model revisions and warm-up instructions must
  be documented and the demo environment prepared in advance.
- Public content can have redistribution constraints; only permitted metadata or
  clearly synthetic fixtures will be committed.
- The repository's public visibility cannot be inferred from the local Git remote and
  must be verified through an incognito browser before final submission.

## Deferred Work

- Module A tactical index rebalancing.
- Presentation deck and PDF export.
- Recorded YouTube walkthrough and link validation.
- Cloud deployment and production-scale streaming infrastructure.
