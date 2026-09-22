# MLOps v2 — resume & push checklist

Branch: `mlops-v2` (local). Remote:
https://github.com/netthetlahrushikesh/Used-Car-Price-Intelligence-Platform

## What landed

- [x] `Dockerfile` + `.dockerignore` (uvicorn → `used_car_price_intelligence.api.app:app`)
- [x] `docker-compose.yml` (`api` :8000, `./logs:/app/logs`)
- [x] Prediction JSONL logging on successful `/predict` (best-effort)
- [x] `.github/workflows/ci.yml` (pytest unit tests, no training)
- [x] `scripts/drift_report.py` → `reports/drift_report.md`
- [x] `artifacts/monitoring/reference_feature_stats.json` (fixture bootstrap)
- [x] `docs/70-mlops-v2.md`
- [x] Unit tests: `test_prediction_logging.py`, `test_drift_report.py`
- [x] Vercel entry `app.py` kept

## Paste-later resume bullets

- MLOps v2 adds Docker/Compose, prediction JSONL, GitHub Actions CI, and a
  simple PSI/mean-std drift report — without changing model metrics.
- Logging is best-effort to `logs/predictions.jsonl`; override with
  `USED_CAR_PREDICTION_LOG`.
- Drift reference is fixture-bootstrapped; replace from gold data before
  trusting alerts (`docs/70-mlops-v2.md`).
- Run locally: `docker compose up --build` then `GET /health` and `POST /predict`.
- CI: push/PR runs `pytest tests/unit` on Python 3.11.

## Exact docker run

```bash
cd /path/to/Used-Car-Price-Intelligence-Platform
docker build -t used-car-price-api .
docker run --rm -p 8000:8000 -v "$(pwd)/logs:/app/logs" \
  -e USED_CAR_PREDICTION_LOG=/app/logs/predictions.jsonl \
  used-car-price-api
```

Compose alternative:

```bash
docker compose up --build
```

## Push this branch (needs GitHub auth)

Do **not** force-push.

```bash
cd /path/to/Used-Car-Price-Intelligence-Platform
git checkout mlops-v2
git status
git push -u origin mlops-v2
```

If push fails with auth:

1. Authenticate the GitHub CLI or git credential helper on this machine, e.g.
   `gh auth login` (HTTPS) or configure an SSH key / PAT for
   `github.com/netthetlahrushikesh/Used-Car-Price-Intelligence-Platform`.
2. Retry `git push -u origin mlops-v2`.
3. Open a PR from `mlops-v2` → `main` on GitHub (CI should run automatically).

Local work does not require `gh` auth; only publishing the branch does.

## Verify after pull

```bash
pip install -r requirements.txt pytest httpx
PYTHONPATH=src pytest tests/unit/test_prediction_logging.py tests/unit/test_drift_report.py -q
python scripts/drift_report.py
```

## Build-box notes (2026-09-22 IST)

- New unit tests: **8 passed** (`test_prediction_logging.py`, `test_drift_report.py`).
- Existing API/Vercel tests still green (15 passed in that subset).
- `docker` binary was **not installed** on the agent box (`docker: command not found`); Dockerfile and compose are ready — run `docker build` / `docker compose up --build` on a machine with Docker.

## Local monitoring

- Run `.venv/bin/python scripts/drift_report.py`; the local report is at `reports/drift_report.md` (ignored and not committed).
