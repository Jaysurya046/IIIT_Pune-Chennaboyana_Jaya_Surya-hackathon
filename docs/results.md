# Implemented Results and Domain Impact

## Executive Summary

RiskSignal Engine implements the required AI/NLP risk pipeline and the strategic
portfolio stress-testing module. The reproducible path processes two source types,
produces explainable sentiment, event, entity, and impact outputs, persists them behind
nine HTTP endpoints, and presents their downstream portfolio effect in a dashboard.

The strongest evidence is implementation evidence: all manifested artifacts match
their checksums, all eight synthetic taxonomy cases match their expected deterministic
outputs, the complete persisted workflow reconciles to the cent, and the automated
suite passes offline. These results demonstrate correctness against declared synthetic
contracts; they do not establish predictive accuracy on real financial text.

## Delivered Capability

| Requirement | Implemented result | Evidence |
|---|---|---|
| At least two text sources | GDELT news and Bluesky social adapters, plus matching offline fixtures | Adapter tests, six-record validation workflow |
| Structured NLP output | Signed sentiment, eight event types, entity matches, 1–10 impact score, explanation factors | Strict Pydantic contracts and golden cases |
| Downstream application | Module B event-driven stress testing | Scenario mapping, strict trigger, four valuation paths |
| Machine-readable access | Versioned FastAPI service with nine endpoints | API contract tests and OpenAPI documentation |
| Visualization | Streamlit risk monitor, stress lab, and source-health workspace | Dashboard workflow and rendered checks |
| Data-source clarity | Public interfaces separated from synthetic committed artifacts | Source manifest, checksums, synthetic flags, dataset guide |
| Reproducibility | Default offline mode and one-command validator | CI and clean-install instructions |

## Recorded Offline Evidence

The Phase 7 baseline was recorded on 2026-10-03 using Python 3.13 on Windows:

| Measure | Observed result |
|---|---:|
| Manifested artifacts matching SHA-256 | 7 / 7 |
| Fixture records and unique source IDs | 6 / 6 |
| Source types represented | 2 |
| Event-taxonomy categories represented | 8 / 8 |
| Exact event matches on synthetic golden cases | 8 / 8 |
| Exact sentiment matches on synthetic golden cases | 8 / 8 |
| Exact entity-set matches on synthetic golden cases | 8 / 8 |
| Persisted signals recovered after database reopen | 6 / 6 |
| Independently summed synthetic portfolio value | USD 55.50M |
| Boundary-probe illustrative stress loss | USD 717k |
| Stress reconciliation difference | USD 0.00 |
| Local deterministic validation time | 0.119 seconds |
| Phase 7 automated suite | 77 tests passed |
| Final Phase 8 automated suite | 83 tests passed |

The impact-8 stress result is an explicit boundary probe. It copies one persisted,
entity-bearing fixture signal and changes only the impact score so the strictly-greater-
than-7 workflow can be verified without claiming that the original fixture produced a
high-impact observation.

The final Phase 8 snapshot was also installed into an independent Python 3.13 virtual
environment from a clean clone. The configuration diagnostic, Ruff, all 83 tests,
`pip check`, and the validator passed there; the clean-clone validation run completed
in 0.179 seconds against its five-second local budget.

## Explainability and Auditability

Every signal connects its classification and score to source provenance, resolved
entities, model or rule revisions, and normalized impact factors. Every stress decision
records whether the signal crossed the configured threshold. Triggered results retain
scenario version, applied shocks, scope, before and after values, expected-loss change,
and instrument-level calculations.

This trace makes the prototype reviewable in ways a single opaque sentiment score is
not: an analyst can identify the source, inspect the reasons for the impact score,
see the scenario assumption, and reconcile the portfolio total back to positions.

## Domain Impact

The prototype demonstrates a practical bridge between unstructured event monitoring
and wholesale-portfolio scenario analysis. It reduces the manual handoff between
finding a potentially relevant event and framing a consistent first-pass exposure
question. Explicit source state and persisted trigger decisions also make skipped and
failed paths visible instead of presenting only successful outputs.

The useful decision is not “trade from this signal.” It is “which event deserves
structured review, what synthetic exposures would be affected under the declared
scenario, and which assumptions require expert challenge?” Production use would still
require governed real portfolios, calibrated models, validation, access control,
monitoring, and human approval.

## Limitations and Next Steps

- The committed fixtures and portfolio are synthetic and intentionally small.
- Golden exact-match results are regression evidence, not real-world accuracy metrics.
- Live GDELT and Bluesky behavior depends on external services and is mocked in tests.
- Optional transformer mode is pinned but not downloaded or benchmarked in CI.
- Stress shocks and valuation methods are simplified and are not regulatory models.
- The local prototype has no multi-user identity, authorization, streaming, or cloud
  deployment layer.

The next engineering step after the hackathon would be a governed pilot dataset with
human-labeled events, out-of-sample evaluation, calibrated scenario design, and a
security and deployment review. Presentation and video artifacts are intentionally
prepared only after this implementation baseline is frozen.
