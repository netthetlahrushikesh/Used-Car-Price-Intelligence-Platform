# MLOps v2 — Docker, CI, prediction logs, drift

Date: 2026-09-22

Production-flavored packaging around the existing FastAPI/Vercel app. Does **not**
change reported model MAPE or retrain the artifact.

## What was added

| Piece | Path | Role |
| --- | --- | --- |
| Image | `Dockerfile`, `.dockerignore` | Slim multi-stage Python 3.11; serves `used_car_price_intelligence.api.app:app` |
| Compose | `docker-compose.yml` | `api` on port 8000; mounts `./logs` → `/app/logs` |
| Prediction JSONL | `src/.../api/prediction_logging.py` | Best-effort append on successful `POST /predict` |
| CI | `.github/workflows/ci.yml` | Python 3.11, install deps + pytest, run `tests/unit` |
| Drift | `scripts/drift_report.py` | Compare request-feature stats vs reference; write `reports/drift_report.md` |
| Reference stats | `artifacts/monitoring/reference_feature_stats.json` | Fixture bootstrap (replace with gold stats for real monitoring) |

The Vercel entry `app.py` → `used_car_price_intelligence.api.app` is unchanged.

## Docker

Build and run with Compose:

```bash
docker compose up --build
```

Or plain Docker:

```bash
docker build -t used-car-price-api .
docker run --rm -p 8000:8000 -v "$(pwd)/logs:/app/logs" \
  -e USED_CAR_PREDICTION_LOG=/app/logs/predictions.jsonl \
  used-car-price-api
```

Health check: `GET http://127.0.0.1:8000/health`

Uvicorn module path matches local runner (`scripts/run_prediction_api.py`):
`used_car_price_intelligence.api.app:app` with `PYTHONPATH=/app/src`.

## Prediction logging

On each successful `/predict`:

- Appends one JSON line to `logs/predictions.jsonl` (override with
  `USED_CAR_PREDICTION_LOG`).
- Fields: `timestamp` (UTC), `request_features` (safe summary), `predicted_price`,
  `latency_ms`.
- Failures to write are swallowed; the HTTP response is never broken by logging.
- Secrets / auth headers are never logged (only known request feature keys).

Batch `/predict/batch` is not logged in v2 (single-predict path only).

## CI

GitHub Actions workflow runs on push and pull_request:

1. Setup Python 3.11
2. `pip install -r requirements.txt pytest httpx`
3. `pytest tests/unit` with `PYTHONPATH=src`

No model training. Fail the job if any unit test fails.

## Drift report

```bash
python scripts/drift_report.py
```

Behavior:

1. Load `artifacts/monitoring/reference_feature_stats.json`.
2. Load recent rows from `logs/predictions.jsonl`, or fall back to
   `tests/fixtures/mlops/sample_predictions.jsonl` if the log is empty.
3. For numeric request fields (`model_year`, `km_driven`, `ownership`,
   `market_snapshot_year`), write mean/std shift and a simple PSI table to
   `reports/drift_report.md`.
4. If fewer than `--min-rows` (default 5) current rows exist, state **insufficient
   data** and make no drift claim.

### Refreshing the reference from gold data

The committed reference is a **fixture bootstrap** for plumbing. To replace it:

1. Load the final modeling table (gold / training parquet used for
   `final_price_model_v1`).
2. For each numeric request-like column, compute `count`, `mean`, `std`, `min`,
   `max` (optionally keep a sample of `values` for PSI).
3. Write JSON shaped like `artifacts/monitoring/reference_feature_stats.json`
   with `source` set to something like `gold_final_price_model_v1`.

Do not treat fixture-vs-fixture PSI as production drift.

## Related docs

- `docs/65-stage2-prediction-api.md` — API contract
- `docs/68-vercel-deployment.md` — serverless path (still valid)
- `MLOPS_V2.md` — resume / push checklist at repo root
