# Post-Implementation Improvement Plan

## Objective and Delivery Rules

This roadmap continues the completed implementation as Phases 9 through 20. Each
phase corresponds to exactly one requested task and one conventional commit. P0 and P1
are the committed delivery path; P2 starts only after P0 and P1 are complete and time,
data access, and review capacity remain.

The following rules apply to every phase:

- Run Ruff, the full offline Pytest suite, and `python -m risk_engine validate` before
  committing. A task is not complete unless all three pass.
- Tests must not use the network. Optional live and model integrations are exercised
  through injected or mocked boundaries in CI.
- Preserve explicit modes. A failed live or model request must never fall back to
  fixtures, replay data, deterministic NLP, or another mode.
- Do not modify `data/sample/gdelt_articles.json` or
  `data/sample/bluesky_posts.json`. They remain checksummed Phase 2 fixtures.
- Add every new committed data artifact to `data/sources.yaml` with an explicit
  classification, redistribution statement, assumptions, and SHA-256 checksum.
- Whenever a data artifact is added, deliberately update the expected artifact totals
  in `tests/validation/test_validation_runner.py`, the SHA-256 count in
  `tests/test_documentation.py`, and the explicit inventory in
  `tests/ingestion/test_data_provenance.py`.
- Label synthetic inputs and hypothetical outputs at the contract, API, dashboard, and
  documentation layers.
- Do not add Module A, Kafka, or cloud deployment.

## Recorded Baseline

Baseline commit: `632bab7 docs: finalize reproducible implementation guide`

Recorded on 2026-10-03 with Python 3.13:

| Command | Result |
|---|---|
| `python -m ruff check .` | Passed with no findings |
| `python -m pytest` | The managed shell could not access its default OS temp directory; no assertion failed |
| `python -m pytest --basetemp data/runtime/improvements-baseline` | 83 passed, one upstream Starlette deprecation warning |
| `python -m risk_engine validate` | Passed; 7/7 artifacts, 6/6 signals persisted, USD 0.00 reconciliation difference, 0.118 seconds |

The `--basetemp` override is an execution-environment workaround, not a project
requirement. CI and normal developer shells continue to run `python -m pytest` exactly.

## Mandatory Gate After Every Phase

Run from the repository root:

```bash
python -m ruff check .
python -m pytest
python -m risk_engine validate
git diff --check
```

In this managed Windows shell only, use a unique ignored workspace temp directory when
Pytest cannot access the user temp root:

```powershell
python -m pytest --basetemp data/runtime/phase-<number>-tests
```

Record the exact counts, warnings, validator measurements, and any environment-only
workaround in `progress.md` until Phase 16 moves that tracker to `docs/progress.md`.

## Priority and Dependency Sequence

```text
P0: Phase 9 (T1) -> Phase 10 (T2) -> Phase 11 (T3)
                         |                |
                         +------ dashboard organic/hypothetical paths

P1: Phase 12 (T4) -> Phase 13 (T5) -> Phase 14 (T6) -> Phase 15 (T7)
                                                           |
                                                           v
                                                    Phase 16 (T8)

P2: Phase 17 (T9) -> Phase 18 (T10) -> Phase 19 (T11)
                                      Phase 20 (T12, requires supplied dataset)
```

Phase 14 uses the organic replay trigger from Phase 10 and the hypothetical workflow
from Phase 11 for screenshots. Phase 16 is last in P1 because it consolidates the final
results, screenshots, presentation PDF, CI matrix, and one-command demo.

## P0 Required First

### Phase 9 — T1 Deterministic As-Of Time

**Outcome.** `RiskSignalEngine.analyze` accepts an explicit timezone-aware `as_of`.
Fixture and replay callers use the maximum `retrieved_at` in the batch, so recency,
created time, impact factors, and scores do not drift with the calendar. Live mode uses
the real analysis clock. The selected policy is explicit at every call site.

**Files changed.**

- `src/risk_engine/nlp/engine.py`
- `src/risk_engine/nlp/factory.py`
- `src/risk_engine/api/service.py`
- `src/risk_engine/cli.py`
- `src/risk_engine/validation/runner.py`
- `tests/nlp/test_engine.py`
- `tests/api/test_api_contract.py`
- `tests/validation/test_validation_runner.py`
- `docs/architecture.md`
- `progress.md`

**Tests added or updated.**

- Analyze the same fixture batch with clocks years apart and assert identical signals,
  factors, and scores when the same `as_of` is supplied.
- Reject a naive `as_of` datetime through a clear error.
- Assert fixture API and CLI paths choose `max(document.provenance.retrieved_at)`.
- Assert live mode does not inherit the replay policy.

**Commands and required results.** Run the mandatory gate plus focused NLP and API
tests. All commands must pass; validator counts remain 7 artifacts and 6 signals.

**Commit.** `fix(nlp): anchor replay recency to batch time`

### Phase 10 — T2 Organic Trigger Through a Replay Bundle

**Outcome.** Add a replay-only bundle containing four hand-authored, paraphrased
records inspired by the March 2023 banking-stress pattern. Use fictional issuers,
reserved `.example` domains, two news-shaped records, and two social-shaped records.
The unchanged deterministic engine must produce exact recorded scores of at least 8
for resolved fictional issuers, allowing Stress Lab to trigger without signal mutation.

`SourceMode.REPLAY` is explicit and separate from `FIXTURES` and `LIVE`. Fixture mode
continues to load only the existing `data/sample/*.json` files. Replay mode never makes
a network request and is visibly labeled synthetic.

**Files changed.**

- New `data/replay/banking_stress_news.json`
- New `data/replay/banking_stress_social.json`
- `data/sources.yaml`
- `data/README.md`
- `src/risk_engine/api/models.py`
- `src/risk_engine/api/service.py`
- `src/risk_engine/cli.py`
- `src/risk_engine/dashboard/client.py`
- `src/risk_engine/dashboard/app.py`
- `src/risk_engine/validation/runner.py`
- `tests/ingestion/test_data_provenance.py`
- `tests/api/test_api_contract.py`
- `tests/validation/test_validation_runner.py`
- `tests/validation/test_dashboard_workflow.py`
- `tests/test_documentation.py`
- `docs/dataset-guide.md`
- `docs/demo-script.md`
- `progress.md`

**Tests added or updated.**

- Assert the exact event, sentiment, entities, impact factors, and scores for every
  replay record.
- Assert at least one organic score is 8 or higher and produces a triggered persisted
  stress result without `model_copy`, direct score edits, or the Phase 7 boundary probe.
- Assert fixture mode still returns exactly the original six fixture documents.
- Assert replay mode is synthetic, offline, and isolated from live mode.
- Increase manifested artifact and checksum expectations from 7 to 9.

**Commands and required results.** Run the mandatory gate, the replay CLI command, and
the populated dashboard AppTest. Record the final exact scores in tests and docs only
after the unchanged deterministic engine produces them.

**Commit.** `feat(replay): add organic high-impact stress scenario`

### Phase 11 — T3 Clearly Hypothetical What-If Simulator

**Outcome.** Add `POST /api/v1/stress-tests/what-if` with an event type, unique entity
IDs, and impact score. It runs the existing stress calculations in memory without
creating or persisting a risk signal. The response includes `hypothetical: true`, the
submitted assumptions, trigger decision, and result when triggered. The dashboard
shows a separate What-if panel and warning banner; it never mixes hypothetical output
with observed or replay signals.

**Files changed.**

- `src/risk_engine/api/models.py`
- `src/risk_engine/api/service.py`
- `src/risk_engine/api/app.py`
- `src/risk_engine/stress/models.py`
- `src/risk_engine/stress/engine.py`
- `src/risk_engine/dashboard/client.py`
- `src/risk_engine/dashboard/app.py`
- `tests/api/test_api_contract.py`
- `tests/stress/test_stress_engine.py`
- `tests/dashboard/test_client.py`
- `tests/validation/test_dashboard_workflow.py`
- `docs/api.md`
- `docs/dashboard.md`
- `docs/architecture.md`
- `progress.md`

**Tests added or updated.**

- Contract tests for triggered and skipped hypothetical requests.
- HTTP 404 for unknown entity IDs and HTTP 422 for invalid event, impact, or duplicate
  entity inputs.
- Repository assertion that the request does not create a risk-signal row or persisted
  stress decision.
- Dashboard AppTest for the warning, controls, skipped state, and triggered result.

**Commands and required results.** Run the mandatory gate plus focused API, stress, and
dashboard tests. Existing persisted-signal behavior must remain unchanged.

**Commit.** `feat(stress): add hypothetical what-if simulation`

## P1 Required Improvements

### Phase 12 — T4 Real-Data Benchmark Command

**Outcome.** Add:

```bash
python -m risk_engine benchmark --dataset <csv> --text-col <name> --label-col <name>
```

The command validates a user-supplied CSV, normalizes supported sentiment labels, and
compares deterministic and model modes using accuracy, macro-F1, and a per-class
confusion matrix. Metrics are implemented locally to avoid a heavy new scoring
dependency. Output is machine-readable JSON plus a Markdown table suitable for README
section 5 and the presentation.

The raw benchmark dataset is never committed. `docs/benchmark.md` records the chosen
dataset name, version or immutable reference, acquisition steps, license or permitted
use, row-selection rules, label mapping, checksum of the local input, environment,
metrics, and limitations. Model download is an explicit benchmark prerequisite and a
model failure ends the command; it never falls back to deterministic mode.

**Files changed.**

- New `src/risk_engine/benchmarking/__init__.py`
- New `src/risk_engine/benchmarking/models.py`
- New `src/risk_engine/benchmarking/runner.py`
- `src/risk_engine/cli.py`
- New `tests/benchmarking/test_metrics.py`
- New `tests/benchmarking/test_runner.py`
- New `tests/benchmarking/test_cli.py`
- New `docs/benchmark.md`
- `README.md`
- `progress.md`

**Tests added or updated.**

- Temporary synthetic CSV tests for label mapping, confusion counts, macro-F1,
  malformed columns, empty rows, unsupported labels, and deterministic ordering.
- Injected fake model-mode tests; CI does not download weights or use the network.
- Failure test proving unavailable model mode is explicit and does not fall back.

**Commands and required results.** Run the mandatory gate and benchmark unit tests.
Run the real benchmark separately with the approved local dataset and record its exact
results in `docs/benchmark.md`.

**Execution gate.** Before implementing this phase, select or supply a public dataset
whose license permits this evaluation. Metrics must not be invented, and the raw CSV
must remain outside Git.

**Commit.** `feat(benchmark): compare deterministic and model NLP quality`

### Phase 13 — T5 Model-Mode Hygiene and Mode Visibility

**Outcome.** Cache the eight category-description embeddings once per
`EmbeddingEventClassifier`; encode only document text thereafter. Add batch sentiment
analysis so FinBERT receives a list rather than one call per record. Provide an explicit
API startup warm-up option that loads model components and fails visibly on error. Add
an NLP mode selector to the fixture/replay dashboard action and extend benchmark output
with trigger counts and trigger rates for each mode.

**Files changed.**

- `src/risk_engine/nlp/events.py`
- `src/risk_engine/nlp/sentiment.py`
- `src/risk_engine/nlp/engine.py`
- `src/risk_engine/nlp/factory.py`
- `src/risk_engine/api/service.py`
- `src/risk_engine/api/app.py`
- `src/risk_engine/cli.py`
- `src/risk_engine/dashboard/client.py`
- `src/risk_engine/dashboard/app.py`
- `src/risk_engine/benchmarking/models.py`
- `src/risk_engine/benchmarking/runner.py`
- `tests/nlp/test_events.py`
- `tests/nlp/test_sentiment.py`
- `tests/nlp/test_engine.py`
- `tests/api/test_api_contract.py`
- `tests/dashboard/test_client.py`
- `tests/validation/test_dashboard_workflow.py`
- `tests/benchmarking/test_runner.py`
- `docs/benchmark.md`
- `docs/implementation-guide.md`
- `progress.md`

**Tests added or updated.**

- Replace the current `len(texts) == 9` assertion with encoder-call assertions showing
  one eight-description cache call followed by one-text calls.
- Assert repeated classification reuses cached category vectors.
- Assert FinBERT and deterministic sentiment batching preserve input order and contract
  values.
- Assert warm-up success and explicit dependency/model failure without fallback.
- Assert dashboard requests the selected mode and benchmark trigger rates reconcile to
  per-mode row counts.

**Commands and required results.** Run the mandatory gate plus focused NLP, benchmark,
API, and dashboard tests. Optional real model smoke testing is outside CI and requires
locally available pinned weights.

**Commit.** `perf(nlp): batch model inference and expose mode controls`

### Phase 14 — T6 Dashboard Evidence

**Outcome.** Add a signal timeline using publication time on the x-axis, impact on the
y-axis, and event type as color. Add an instrument loss waterfall sorted by descending
loss with a reconciled total. Capture three or four synthetic/replay dashboard images
under `docs/img/` showing source health, signal evidence, organic triggered stress, and
the hypothetical panel. Every screenshot visibly identifies synthetic or hypothetical
content.

**Files changed.**

- `src/risk_engine/dashboard/charts.py`
- `src/risk_engine/dashboard/model.py`
- `src/risk_engine/dashboard/app.py`
- `tests/dashboard/test_model_and_charts.py`
- `tests/validation/test_dashboard_workflow.py`
- New `docs/img/source-health.png`
- New `docs/img/risk-signal-timeline.png`
- New `docs/img/organic-stress-result.png`
- New `docs/img/hypothetical-what-if.png`
- `docs/dashboard.md`
- `progress.md`

**Tests added or updated.**

- Assert timeline x/y/color mappings, labels, ordering, and empty behavior.
- Assert waterfall ordering, signs, total, and cent-level reconciliation.
- Update AppTest chart counts and interaction checks.
- Add required screenshot existence, dimensions, and non-empty checks.
- Render normal and narrow dashboard widths and inspect every affected view.

**Commands and required results.** Run the mandatory gate, focused chart/AppTest tests,
and a rendered dashboard walkthrough. Record screenshot dimensions and visual findings.

**Commit.** `feat(ui): add timeline waterfall and evidence screenshots`

### Phase 15 — T7 Documentation Honesty

**Outcome.** State beside the impact formula that sentiment magnitude is
direction-agnostic: strongly positive and strongly negative language can both increase
severity. When a positive-sentiment signal triggers, show an explicit UI note that the
trigger reflects magnitude and other factors, not a claim that positive sentiment is
harmful. Document the derivative DV01 convention, units, shock sign, and the exact
valuation equation used by the implementation.

**Files changed.**

- `src/risk_engine/dashboard/app.py`
- `tests/validation/test_dashboard_workflow.py`
- `docs/architecture.md`
- `docs/dashboard.md`
- `docs/results.md`
- `docs/demo-script.md`
- `data/README.md`
- `README.md`
- `progress.md`

**Tests added or updated.**

- Dashboard test for the positive-sentiment trigger note.
- Documentation assertions for “direction-agnostic” and the DV01 sign convention.
- Negative and neutral trigger paths must not show the positive-sentiment note.

**Commands and required results.** Run the mandatory gate plus dashboard and
documentation tests. Reinspect the affected dashboard state at normal and narrow width.

**Commit.** `docs(risk): clarify directional and valuation assumptions`

### Phase 16 — T8 Release, Repository, and Demo Hygiene

**Outcome.** Use the package `__version__` as the FastAPI application version. Move
`progress.md` to `docs/progress.md` and update every link. Rewrite README section 5 as
one evidence table plus the Phase 14 screenshots. Remove stale “deferred” wording. Run
CI on Python 3.11 and 3.13. Add a real five-to-seven-slide `docs/presentation.pdf` to
the required-artifacts test. Add `python -m risk_engine demo`, which seeds an explicit
fixture or replay mode, analyzes it, starts the API, waits for health, launches the
dashboard, and cleans up the API child process when the dashboard exits.

The demo command defaults to replay mode so the reviewer can see an organic trigger.
`--source-mode`, `--nlp-mode`, host, API port, dashboard port, and browser behavior are
explicit. Invalid or unavailable modes fail; the command never changes mode silently.

**Files changed.**

- `src/risk_engine/api/app.py`
- `src/risk_engine/cli.py`
- `tests/api/test_api_contract.py`
- `tests/dashboard/test_cli.py`
- `tests/test_documentation.py`
- `.github/workflows/ci.yml`
- `README.md`
- `docs/implementation-guide.md`
- `docs/demo-script.md`
- New `docs/presentation.pdf`
- Move `progress.md` to `docs/progress.md`
- All files linking to the progress tracker

**Tests added or updated.**

- Assert FastAPI metadata version equals `risk_engine.__version__`.
- Mock demo subprocesses and readiness polling; verify seed order, arguments, failure
  cleanup, port conflicts, and no mode fallback.
- Assert the presentation PDF exists, has a PDF signature, and contains five to seven
  pages; a placeholder file is not acceptable.
- Verify README section 5 contains one results table and the committed screenshots.
- Exercise both Python versions in CI with the same offline gates.

**Commands and required results.** Run the mandatory gate, the demo CLI tests, PDF
render and page inspection, a clean-clone rehearsal, and the two CI matrix jobs.

**Execution gate.** The presentation must be authored and visually verified before the
required-artifacts assertion is enabled. This phase must not commit an empty or fake PDF.

**Commit.** `chore(release): finalize demo workflow and repository hygiene`

## P2 Optional Only If Time Remains

### Phase 17 — T9 Deterministic NLP Robustness

**Outcome.** Make keyword evidence tolerant of bounded English suffixes, add a small
documented negation window, and remove ambiguous sentiment tokens such as `fine` and
`record`. Keep behavior transparent and deterministic; do not introduce an unstated
stemming library or model fallback.

**Files changed.**

- `src/risk_engine/nlp/events.py`
- `src/risk_engine/nlp/sentiment.py`
- `tests/nlp/test_events.py`
- `tests/nlp/test_sentiment.py`
- `tests/nlp/test_engine.py`
- `tests/nlp/test_golden_benchmark.py`
- `tests/validation/test_dashboard_workflow.py`
- `docs/architecture.md`
- `docs/benchmark.md`
- `docs/progress.md`
- Possibly `data/evaluation/nlp_golden.json` and its manifest checksum, but only after
  an explicit user checkpoint if the checked-in regression fixture must change

**Tests added or updated.**

- Suffix variants, word-boundary false positives, nearby negation, distant negation,
  double-negation policy, and removed ambiguous-token cases.
- Deliberately update the dashboard Operational-filter expectation and engine outputs.
- Rerun and document the benchmark delta; do not assume robustness improved.

**Commands and required results.** Run the mandatory gate plus the full NLP and
dashboard workflow tests. Compare benchmark metrics before and after.

**Commit.** `fix(nlp): improve deterministic matching and negation`

### Phase 18 — T10 Stronger Live Path and Illustrative Sector Proxies

**Outcome.** Build live queries from the configured watchlist, space GDELT requests,
make Bluesky authentication behavior explicit, and record one permitted metadata-only
public snapshot in a new file. Add a versioned mapping from real issuer sectors to the
matching synthetic portfolio sectors. Any resulting stress output is labeled
illustrative sector proxy, never issuer exposure.

**Files changed.**

- `src/risk_engine/ingestion/adapters/gdelt.py`
- `src/risk_engine/ingestion/adapters/bluesky.py`
- `src/risk_engine/ingestion/service.py`
- `src/risk_engine/api/service.py`
- `src/risk_engine/config.py`
- New `src/risk_engine/stress/sector_proxy.py`
- New `data/live-snapshots/<dated-metadata-snapshot>.json`
- New `data/portfolio/sector_proxy.json`
- `data/sources.yaml`
- `data/README.md`
- Adapter, API, stress, provenance, validator, and documentation tests
- `docs/dataset-guide.md`
- `docs/architecture.md`
- `docs/progress.md`

**Tests added or updated.**

- Mocked watchlist query generation, request spacing, rate limits, authentication,
  redaction, and source isolation; no network in tests.
- Proxy mapping tests for known, unknown, and multi-entity sectors.
- Contract/UI assertions for public-snapshot and illustrative-proxy labels.
- With the Phase 10 two-file replay bundle already present, adding the snapshot and
  proxy configuration raises the expected manifest count from 9 to 11.

**Commands and required results.** Run the mandatory gate and mocked live-path suite.
Run any real retrieval manually, record endpoint/date/license/terms, and inspect the
snapshot before committing it.

**Commit.** `feat(data): strengthen live ingestion and sector proxy stress`

### Phase 19 — T11 SSE Streaming and Optional Polling

**Outcome.** Add `GET /api/v1/signals/stream` using Server-Sent Events, an optional
in-process subscriber that creates stress decisions for new high-impact signals, and
`serve --poll-minutes` for bounded polling. Both auto-stress and polling are disabled
by default. Polling requires an explicit source mode and respects offline configuration;
it never substitutes replay or fixtures after a live failure.

**Files changed.**

- New `src/risk_engine/api/events.py`
- `src/risk_engine/api/app.py`
- `src/risk_engine/api/service.py`
- `src/risk_engine/cli.py`
- `src/risk_engine/config.py`
- `src/risk_engine/persistence/sqlite.py`
- New streaming and polling tests under `tests/api/`
- `tests/dashboard/test_cli.py`
- `docs/api.md`
- `docs/architecture.md`
- `docs/progress.md`

**Tests added or updated.**

- SSE framing, event IDs, reconnect cursor, heartbeat, ordering, disconnect cleanup,
  and empty-stream behavior.
- Auto-stress idempotency and threshold behavior.
- Poll timing with an injected clock, explicit mode validation, source failure
  isolation, and clean process shutdown; all adapters are mocked.

**Commands and required results.** Run the mandatory gate plus focused SSE, persistence,
and CLI lifecycle tests. No broker or Kafka dependency is introduced.

**Commit.** `feat(api): stream signals and automate stress decisions`

### Phase 20 — T12 Seeded Larger Synthetic Portfolio

**Outcome.** Add:

```bash
python -m risk_engine generate-portfolio --seed <integer> --positions 200
```

The generator consumes only an approved aggregate profile derived from a user-provided
transaction dataset, never raw rows. It produces a versioned, explicitly synthetic
portfolio with stable IDs, deterministic values, all supported asset classes, and
reconciled totals. The existing eight-position portfolio remains unchanged and remains
the default unless a generated portfolio path is selected explicitly.

**Files changed.**

- New `src/risk_engine/portfolio_generation/__init__.py`
- New `src/risk_engine/portfolio_generation/models.py`
- New `src/risk_engine/portfolio_generation/generator.py`
- `src/risk_engine/cli.py`
- New `data/portfolio/generation_profile.json`
- `data/sources.yaml`
- `data/README.md`
- New tests under `tests/portfolio_generation/`
- Validator, provenance, and documentation count tests
- `docs/dataset-guide.md`
- `docs/implementation-guide.md`
- `docs/progress.md`

**Tests added or updated.**

- Same seed and profile produce byte-stable output; different seeds change positions.
- Exactly 200 unique positions, valid ranges, required asset-class coverage, fictional
  issuer labels, strict schema validation, and portfolio-total reconciliation.
- Temporary synthetic CSV tests prove that raw input rows are not copied into the
  aggregate profile or generated output.
- Adding one aggregate profile raises the expected manifest count from 11 to 12.

**Commands and required results.** Run the mandatory gate, generate twice with the same
seed and compare hashes, then run stress reconciliation against the generated portfolio.

**Execution gate.** This phase cannot produce a truthful aggregate profile until the
user supplies or identifies the permitted transaction dataset. Stop and request that
input before committing the profile; do not invent source statistics.

**Commit.** `feat(portfolio): generate reproducible synthetic portfolios`

## Completion Definition

P0 is complete when fixture scoring is time-stable, replay produces an organic persisted
trigger, and the hypothetical simulator is visibly separate and fully tested. P1 is
complete when real benchmark evidence, model-mode efficiency, dashboard evidence,
honest assumptions, the presentation PDF, dual-version CI, and the one-command demo all
pass from a clean clone. P2 remains optional and may be stopped after any complete task
without weakening the P0/P1 deliverable.
