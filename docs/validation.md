# Phase 7 Validation Evidence

## Readiness Assessment

**Ready within the reviewed offline scope.** The deterministic fixture workflow,
synthetic regression set, persistence layer, stress trigger, reconciliation logic, and
dashboard interactions pass the checks described below. This does not establish
real-world predictive accuracy, production scalability, or live-source availability.

## Reproduce the Validation

Run the complete offline suite and write an inspectable JSON report:

```bash
python -m risk_engine validate --output data/runtime/validation-report.json
python -m pytest
python -m ruff check .
python -m pip check
```

The report path is ignored because timestamps and timings are execution-specific. The
validation command exits with status 1 when a checksum, quality expectation, workflow
reconciliation, persistence check, or performance budget fails. CI runs the same
command with a 10-second budget to accommodate shared runners.

## Evidence and Method

| Area | Evidence | Validation method |
|---|---|---|
| Dataset integrity | Seven artifacts declared in `data/sources.yaml` | Recalculate every SHA-256 checksum; require bounded `data/` paths and explicit synthetic or project-authored classification |
| Fixture quality | Three GDELT-shaped and three Bluesky-shaped records | Require non-empty text and source IDs, unique IDs, publication no later than retrieval, and two explicitly synthetic bundles |
| NLP regression | Eight cases in `data/evaluation/nlp_golden.json` | Independently run deterministic entity, sentiment, and event components and compare exact expected outputs |
| Offline workflow | Both committed fixture adapters | Ingest, normalize, analyze, persist, reopen SQLite, and compare unique document/signal counts and provenance |
| Portfolio totals | Raw position values in `portfolio.json` | Independently sum raw values and reconcile API breakdowns by asset class, sector, and issuer |
| Stress calculation | Synthetic impact-8 boundary probe | Persist a copied entity-bearing signal with only its impact score set to 8, run its configured scenario, and independently sum instrument before, after, and loss values |
| Dashboard behavior | Real local API populated with both fixture sources | Render the Streamlit app, apply the Operational event filter, reset to All, and submit a stress decision |

The impact-8 signal is a boundary probe, not an observed fixture result. Fixture signals
remain unchanged, and their original event, source provenance, entity matches, and
model versions are retained for the probe.

## Recorded Baseline

Recorded on 2026-10-03 using Python 3.13 on Windows in deterministic offline mode:

| Check | Result |
|---|---:|
| Manifested artifacts matching checksums | 7 / 7 |
| Fixture records with unique source IDs | 6 / 6 |
| Source types represented | 2 |
| Golden taxonomy categories covered | 8 / 8 |
| Golden event matches | 8 / 8 |
| Golden sentiment matches | 8 / 8 |
| Golden entity-set matches | 8 / 8 |
| Documents produced / unique | 6 / 6 |
| Signals produced / unique / persisted after reopen | 6 / 6 / 6 |
| Synthetic signals | 6 / 6 |
| Independently summed portfolio value | USD 55,500,000.00 |
| Boundary stress illustrative loss | USD 717,000.00 |
| Stress reconciliation difference | USD 0.00 |
| Complete validation runtime | 0.147 seconds |
| Local runtime budget | 5.000 seconds |

The accuracy rows are exact-match results on a small synthetic regression set designed
to cover code paths. They must not be presented as estimates of performance on public
news, social posts, unseen issuers, other languages, or adversarial text. The timing is
one local measurement of the deterministic path and is not a latency SLA.

## Failure and Boundary Coverage

- A failed ingestion source is isolated while healthy sources continue.
- Rate limits and transient HTTP failures use bounded retries.
- Live ingestion is rejected while offline mode is enabled.
- Invalid API payloads return validation errors; missing resources return not found.
- Corrupt fixture content produces a bounded error without echoing its payload.
- Missing optional model dependencies raise explicit errors and never fall back to
  deterministic rules under a model-mode request.
- An incompatible future SQLite schema fails closed.
- Impact 7 is skipped; impact 8 triggers stress testing.
- Entity-scoped scenarios with no resolved entity produce an explicit zero-position
  result rather than stressing unrelated positions.
- Dashboard API errors are sanitized, empty selections are explicit, and a filtered
  population resets to the six-signal total.
- Desktop and 800-pixel rendered checks require visible chart marks and no horizontal
  overflow; analytical columns stack at the narrow width while sidebar filters remain
  available.

## Remaining Caveats

- Live GDELT and Bluesky behavior is mocked for deterministic tests; real services can
  rate-limit, deny unauthenticated search, change schemas, or become unavailable.
- Model mode requires separately installed dependencies and downloaded pinned weights;
  Phase 7 validates failure behavior but does not download or benchmark those models.
- Synthetic scenarios and valuations demonstrate explainable calculation paths, not
  calibrated market, credit, regulatory-capital, or investment results.
- Performance and visual checks cover a local prototype scale, not concurrency,
  multi-user security, large datasets, or production deployment.
