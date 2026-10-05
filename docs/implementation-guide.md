# Reproducible Implementation Guide

## What This Guide Reproduces

This guide starts the complete RiskSignal Engine prototype from a clean checkout. The
default path is deliberately offline: it reads two committed synthetic source bundles,
normalizes and analyzes six records, persists explainable signals in SQLite, exposes
them through FastAPI, and renders the Streamlit monitoring and stress-testing UI.

The offline path is the reviewer path because it is deterministic and does not depend
on third-party availability, credentials, or downloaded model weights. Live public
adapters and pinned-model mode are optional extensions, not hidden prerequisites.

## Prerequisites

- Git.
- Python 3.11, 3.12, or 3.13.
- A terminal that can run two long-lived local processes.
- Network access only for the initial package installation.

The implementation has been exercised on Windows with Python 3.13. GitHub Actions
checks Python 3.11 and 3.13 on Ubuntu with the same offline gates. No database server,
API key, container runtime, or GPU is required for the default workflow.

## Clean Installation

```bash
git clone https://github.com/Jaysurya046/IIIT_Pune-Chennaboyana_Jaya_Surya-hackathon.git
cd IIIT_Pune-Chennaboyana_Jaya_Surya-hackathon
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS or Linux
source .venv/bin/activate
```

Install the declared development environment and verify the configuration:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m risk_engine check
```

The expected diagnostic identifies RiskSignal Engine 0.8.0, offline mode, the local
runtime data directory, and the deterministic NLP mode. A local `.env` is optional;
copy `.env.example` only when overrides are needed and never commit the resulting file.

## Fast Offline Proof

Run the complete machine-readable validation before starting the UI:

```bash
python -m risk_engine validate --output data/runtime/validation-report.json
```

A successful report has `"passed": true`. It checks every manifested artifact,
the eight-case synthetic NLP regression set, the persisted ingestion-to-stress path,
independent portfolio and loss totals, and the configured runtime budget. The output
file is ignored because its timestamp and timings are execution-specific.

Individual command-line stages are also available:

```bash
python -m risk_engine ingest-fixtures --query "portfolio risk"
python -m risk_engine analyze-fixtures --query "portfolio risk"
python -m risk_engine stress-fixtures --query "portfolio risk"
python -m risk_engine replay
```

These commands are useful for inspecting contracts, but each is a self-contained
demonstration. Use the API workflow below when persistence across steps matters.

## One-Command Reviewer Demo

The default reviewer path seeds the separate synthetic replay, analyzes it with the
deterministic engine, starts the API, waits for `/health`, and launches Streamlit:

```bash
python -m risk_engine demo
```

The command opens a browser by default and keeps the API child process tied to the
dashboard lifecycle. Closing the dashboard process also stops the API child. Use
`--no-open-browser` for headless use. Every mode and bind choice is explicit:

```bash
python -m risk_engine demo \
  --source-mode fixtures \
  --nlp-mode deterministic \
  --host 127.0.0.1 \
  --api-port 8000 \
  --dashboard-port 8501 \
  --no-open-browser
```

`--source-mode` accepts only `fixtures` or `replay`; replay is the default so the
dashboard starts with four organic impact-9 triggers. Model mode requires the pinned
optional dependencies and weights. Occupied ports, invalid modes, unavailable models,
failed ingestion, and API readiness failure stop the command with an explicit error.
The command never substitutes another source or NLP mode.

## Start the Application

Start the API in terminal one:

```bash
python -m risk_engine serve --host 127.0.0.1 --port 8000
```

For a prepared model-mode demonstration, load both pinned model components before the
API accepts requests:

```bash
python -m risk_engine serve --host 127.0.0.1 --port 8000 --warm-models
```

This option is deliberately strict: missing dependencies, unavailable weights, or model
load failures abort startup visibly. It never starts with deterministic replacements.

Verify `http://127.0.0.1:8000/health`, then start the dashboard in terminal two:

```bash
python -m risk_engine dashboard --host 127.0.0.1 --port 8501 --api-url http://127.0.0.1:8000
```

Open `http://127.0.0.1:8501`. In **Source health**, run **Ingest and analyze synthetic
replay** to populate four impact-9 signals and demonstrate an organic stress trigger.
The separate fixture action remains available for the six-record baseline. Both are
explicitly synthetic and never presented as live data.

The dashboard has three workspaces:

1. **Risk signals** filters the persisted stream and exposes score explanations,
   entity matches, model versions, and source provenance.
2. **Stress lab** evaluates a selected signal against the strict impact-greater-than-7
   trigger and shows the persisted decision and reconciled portfolio result.
3. **Source health** reports per-source outcomes and owns separate fixture/replay actions
   with an explicit deterministic/model NLP selector.

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Optional Live and Model Modes

The GDELT adapter uses a public endpoint. Bluesky search availability depends on the
AppView provider and may require a short-lived bearer token:

```text
RISK_ENGINE_OFFLINE_MODE=false
RISK_ENGINE_BLUESKY_BEARER_TOKEN=<local secret when required>
```

Keep secrets only in the ignored `.env` file or process environment. Live failures are
recorded per source and are never replaced silently with fixtures.

Pinned FinBERT and MiniLM adapters require the optional dependency group and model
downloads:

```bash
python -m pip install -r requirements-nlp.txt
python -m risk_engine analyze-fixtures --query "portfolio risk" --nlp-mode model
python -m risk_engine serve --warm-models
```

Model identifiers, revisions, license metadata, and limitations are recorded in
`data/models.yaml`. A failed model request raises an explicit error; it does not fall
back to deterministic rules. FinBERT processes each analysis batch in one ordered
pipeline call, while MiniLM caches the eight taxonomy-description embeddings once per
engine and encodes only incoming document text thereafter.

## Quality Gates

Run the same local checks used to prepare the submission:

```bash
python -m ruff check .
python -m pytest
python -m pip check
python -m risk_engine validate --max-seconds 5
```

Each Python 3.11 and 3.13 CI job installs `requirements-dev.txt`, runs the configuration
check, Ruff, Pytest, and the offline validator with a ten-second allowance for shared
runners. Transformer and Hugging Face network access stay disabled during these gates.

## Runtime Files and Reset

SQLite databases, JSON validation reports, logs, caches, and downloaded model weights
are ignored. The default database is `data/runtime/risksignal.db`. To restart the demo
from an empty state, stop the API and remove only that runtime database; committed
fixtures and configuration under `data/` must remain unchanged.

## Troubleshooting

| Symptom | Check |
|---|---|
| Dashboard reports that the API is unavailable | Start the API on port 8000 or pass the matching `--api-url` |
| Port already in use | Stop the existing local process or choose another port for both commands |
| `demo` exits before opening the dashboard | Read the structured `demo-error`; free the named port or install the explicitly selected model mode |
| No signals are visible | Run a fixture or replay action in **Source health**, then refresh the dashboard |
| Live request returns HTTP 409 | Set `RISK_ENGINE_OFFLINE_MODE=false` intentionally before using live mode |
| Bluesky returns an authorization error | Supply a permitted bearer token or use the reproducible fixture path |
| Model dependencies or weights are missing | Install `requirements-nlp.txt`; deterministic mode remains available offline |
| Validation reports a checksum mismatch | Restore the manifested artifact or deliberately update its checksum and provenance record |

For endpoint contracts, dashboard metric definitions, dataset provenance, and recorded
validation evidence, see `docs/api.md`, `docs/dashboard.md`,
`docs/dataset-guide.md`, and `docs/validation.md`.
