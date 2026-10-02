# RiskSignal HTTP API

## Running Locally

Install the development dependencies and start the service from the repository root:

```bash
python -m pip install -r requirements-dev.txt
python -m risk_engine serve --host 127.0.0.1 --port 8000
```

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs` and
the machine-readable schema at `http://127.0.0.1:8000/openapi.json`.

The default configuration is offline. API requests must select `source_mode` as
`fixtures` or `live`; fixture data is never substituted after a live-source failure.
Requests for live mode return HTTP 409 until `RISK_ENGINE_OFFLINE_MODE=false` is set.

## Version 1 Workflow

1. `POST /api/v1/ingestion/run` validates and persists normalized documents and source
   outcomes, returning a 32-character `run_id`.
2. `POST /api/v1/analyze` reads that run, generates explainable signals, and persists
   them.
3. `GET /api/v1/signals` lists signals with pagination and optional event, impact,
   source, and entity filters.
4. `POST /api/v1/stress-tests` evaluates one stored signal against the strict trigger
   and persists the decision. Triggered decisions include a retrievable stress result.

Example fixture ingestion request:

```json
{
  "query": "portfolio risk",
  "limit": 25,
  "lookback_hours": 24,
  "source_mode": "fixtures"
}
```

Example analysis request:

```json
{
  "run_id": "<run_id returned by ingestion>",
  "nlp_mode": "deterministic"
}
```

Example stress request:

```json
{
  "signal_id": "<stored signal_id>"
}
```

## Endpoint Summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Application, database, version, and offline-mode health |
| GET | `/api/v1/sources/status` | Latest persisted source outcomes |
| POST | `/api/v1/ingestion/run` | Run fixture or explicitly enabled live ingestion |
| POST | `/api/v1/analyze` | Analyze a persisted ingestion run |
| GET | `/api/v1/signals` | Filter and paginate stored signals |
| GET | `/api/v1/signals/{signal_id}` | Retrieve one signal |
| POST | `/api/v1/stress-tests` | Evaluate and persist a stress decision |
| GET | `/api/v1/stress-tests/{result_id}` | Retrieve a triggered stress result |
| GET | `/api/v1/portfolio/summary` | Retrieve portfolio totals and breakdowns |

Missing resources return HTTP 404, invalid request contracts return HTTP 422, and a
live request blocked by offline mode returns HTTP 409.

## Persistence

The SQLite schema version is stored in the database and checked at startup. Repository
tables retain ingestion payloads and per-source outcomes, risk signals and normalized
entity indexes, and stress decisions/results. Complete payloads are validated back into
the strict Pydantic contracts when read.

Runtime databases use `RISK_ENGINE_DATABASE_URL` and default to the ignored
`data/runtime/risksignal.db` path. They are local runtime artifacts and must not be
committed.
