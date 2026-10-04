# Demonstration and Walkthrough Runbook

## Purpose

This runbook keeps the demonstration reproducible and separates the two organizer
constraints: the functional live demonstration fits within five minutes, while the
submitted screen-recorded walkthrough may use up to ten minutes. Both paths use only
the committed synthetic data and the deterministic NLP mode.

## Pre-Demo Checklist

Complete these steps before recording or joining a jury session:

- Confirm the repository is public in an incognito browser.
- Start from a clean or deliberately seeded `data/runtime/risksignal.db`.
- Run `python -m risk_engine validate` and retain the successful console result.
- Start the API on `127.0.0.1:8000` and confirm `/health` reports version 0.8.0.
- Start the dashboard on `127.0.0.1:8501` and keep the tab open.
- If the database is empty, use **Source health** to ingest and analyze the synthetic replay.
- Use browser zoom and window size that keep KPI cards and charts readable.
- Close unrelated applications, notifications, terminals, and browser tabs.
- Do not display `.env`, tokens, local usernames, or private browser content.

## Five-Minute Functional Demonstration

| Time | Screen | Narration and action |
|---|---|---|
| 0:00–0:25 | README and architecture image | State the problem: turn news and social text into explainable risk signals and use Module B to test a synthetic portfolio. Point out the offline reproducible path. |
| 0:25–0:55 | Terminal | Show the validation command completing successfully. Explain that it verifies checksums, golden cases, persistence, reconciliation, and runtime budget without network access. |
| 0:55–1:30 | Source health | Run the separate synthetic replay. State that its four fictional, checksummed records are inspired only by a general public banking-stress pattern and contain no copied text. |
| 1:30–2:35 | Risk signals | Filter to one event category, then reset to All. Open one signal and show sentiment, event, impact factors, entity evidence, model versions, and source provenance. |
| 2:35–3:45 | Stress lab | Select an impact-9 replay signal and run the stress decision. Explain the strict score-greater-than-7 rule and that the unchanged engine produced the score without manual editing. State that absolute sentiment is direction-agnostic; a positive trigger would reflect magnitude and other factors, not harmful positive sentiment. |
| 3:45–4:30 | Stress result | Show before/after value, illustrative loss, applied shocks, and issuer or asset-class breakdown. Point out exact instrument reconciliation. For derivatives, state that positive DV01 is USD loss per +1 bp rate rise and positive rate shock means rates rise. |
| 4:30–5:00 | Results and limitations | Summarize two sources, eight event categories, nine API endpoints, USD 55.50M synthetic exposure, and offline quality gates. Close with the synthetic-data and non-advice limitation. |

If a live UI action is slow, continue with the already-populated view rather than
switching to live external sources. The reliable demonstration is the committed
offline path.

## Up-to-Ten-Minute Recorded Walkthrough

Use the same sequence with additional implementation detail:

1. **0:00–0:40 — Problem and approach.** Introduce the unified risk engine and the
   selected strategic stress-testing module.
2. **0:40–1:30 — Architecture.** Trace sources, normalization, NLP outputs, SQLite,
   FastAPI, stress orchestration, dashboard, and cross-cutting provenance.
3. **1:30–2:15 — Setup.** Show the exact README commands, Python version, offline
   default, and one-command validator.
4. **2:15–3:15 — Dataset clarity.** Show `data/sources.yaml`; distinguish public live
   interfaces from baseline fixtures, the separate replay, portfolio data, and scenarios.
5. **3:15–5:10 — End-to-end UI.** Run replay ingestion, inspect source health, filter
   the impact-9 signals, and open their explanation and synthetic provenance detail.
6. **5:10–6:40 — Stress workflow.** Explain the threshold, scenario scope, simplified
   valuation methods, and persisted decision. Demonstrate the stress result.
7. **6:40–7:40 — Results.** Show the recorded validation metrics and reconciliation.
   Describe business usefulness without making accuracy or efficiency claims that the
   synthetic evidence cannot support.
8. **7:40–8:35 — Reliability.** Mention source isolation, bounded retries, offline/live
   separation, strict contracts, database schema checks, and CI.
9. **8:35–9:20 — Limitations.** State the fixture, model, scenario, scale, and security
   boundaries directly.
10. **9:20–10:00 — Close.** Restate the implemented outcome and identify governed
    real-data evaluation and calibrated scenarios as next steps.

## Expected Reviewer Questions

**Why use synthetic data?** It provides a redistributable, deterministic review path
without confidential client information or unstable external dependencies. It does
not replace later evaluation on governed public or licensed data.

**Why offer deterministic and transformer modes?** Deterministic mode keeps tests and
the demo inspectable and offline. Model mode provides the planned FinBERT and MiniLM
path with pinned revisions. Mode selection is explicit and never silently falls back.

**How is the impact score explained?** The score combines event severity, absolute
sentiment, classification confidence, entity relevance, corroboration, and recency
using documented weights. Each factor is stored with the signal. Absolute sentiment is
direction-agnostic, so positive and negative language of equal magnitude contribute
equally; a positive trigger is not a claim that positive sentiment is harmful.

**What derivative convention is used?** Delta exposure is signed USD, the underlying
shock is a decimal return, positive DV01 is USD loss per +1 bp rate rise, and positive
`rate_shock_bps` means rates rise. The linear approximation is `P&L = delta_exposure x
underlying_shock - DV01 x rate_shock_bps`, followed by `value after = value before +
P&L`.

**Why is the trigger strictly greater than seven?** That boundary comes from the
problem statement example and is encoded explicitly. Tests verify that seven is
skipped and eight triggers.

**Can these stress results guide investment or capital decisions?** No. They exercise
simplified valuation paths against fictional positions and authored shocks. Production
use requires model governance, calibration, real portfolio controls, and expert review.

**What happens when a source fails?** The adapter records its failure while other
sources continue. Live failure never causes fixtures to be substituted within the run.

## Recording Handoff

The future video should be uploaded to YouTube as **Unlisted**, linked from the root
README, and tested in an incognito window. The future deck should contain five to seven
slides, be committed as `docs/presentation.pdf` or linked from an unrestricted host,
and also be tested without an authenticated session. Those artifacts remain deferred
until the user requests the presentation and recording phase.
