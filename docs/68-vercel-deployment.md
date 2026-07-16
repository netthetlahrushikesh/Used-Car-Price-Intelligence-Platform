# Vercel Deployment (FastAPI + Web UI)

Date: 2026-07-15

## Current production deployment

- Public URL: <https://used-car-price-intelligence-platfor.vercel.app>
- Runtime: Vercel FastAPI Python 3.12 function
- Production deployment ID: `dpl_36HKsshzghHRTb44AqAJ81qmjXBP`
- Verification: `/`, `/health`, `/model/metadata`, `/static/styles.css`, and
  `/docs` returned HTTP 200 without an authentication bypass.
- Prediction smoke test: the packaged sample request returned INR 492,808 with
  the expected INR 433,671 to INR 551,945 range and high confidence.

## Goal

Deploy the Stage 2 prediction API and static web UI as a single Vercel Python
function, without changing prediction semantics or frontend design.

## Architecture

| Piece | Location | Role |
| --- | --- | --- |
| Vercel ASGI entrypoint | `app.py` (repo root) | Imports and re-exports the existing FastAPI `app` |
| Application | `src/used_car_price_intelligence/api/app.py` | Routes, static UI, OpenAPI `/docs` |
| Model service | `src/used_car_price_intelligence/api/service.py` | Loads `final_price_model_v1.joblib` |
| Model package | `artifacts/model/final_price_model_v1/` | Runtime artifact (~3.1 MB joblib + metadata) |
| Production deps | `requirements.txt` | FastAPI + sklearn stack only |
| Platform detection | Root `app.py` + `vercel.json` | Vercel uses its FastAPI preset and discovers the exported ASGI app without custom function routing |
| Upload filter | `.vercelignore` | Drops data, notebooks, caches; keeps model + src |

All HTTP traffic (`/`, `/static/*`, `/health`, `/model/metadata`, `/predict`,
`/predict/batch`, `/docs`, `/openapi.json`) is handled by the same ASGI app.

## Prerequisites

1. Node.js 18+ with `npx` (for the Vercel CLI).
2. A Vercel account and project access.
3. Local Python 3.11+ with the API/modeling stack for pre-deploy checks.
4. The model package present at:

   ```text
   artifacts/model/final_price_model_v1/final_price_model_v1.joblib
   ```

   Export if missing:

   ```powershell
   python scripts/export_final_price_model.py
   ```

5. **scikit-learn 1.8.0** must be the runtime used to load the artifact
   (`requirements.txt` pins this).

## Production dependencies

Vercel detects the root `pyproject.toml` and installs its base
`project.dependencies`; it does not automatically install this project's
optional `api` and `modeling` extras. The base dependency list therefore
contains the complete inference runtime, including the exact
`scikit-learn==1.8.0` artifact compatibility pin. `requirements.txt` mirrors
that production set for explicit review and other deployment environments.

Vercel installs root `requirements.txt` for the function runtime. That file is
intentionally smaller than the local notebook/acquisition extras in
`pyproject.toml`:

- included: FastAPI, Pydantic, joblib, numpy, pandas, scikit-learn==1.8.0
- excluded: matplotlib, seaborn, playwright, jupytext/notebook tooling, pytest

Local development continues to use:

```powershell
python -m pip install -e ".[api,modeling,dev]"
```

## Local verification (before deploy)

```powershell
# Unit tests (includes deployment config checks)
python -m pytest

# Syntax / import smoke
python -m compileall app.py src/used_car_price_intelligence/api
python -c "from app import app; print(app.title)"

# Run the API the same way as local Stage 2 work
python scripts/run_prediction_api.py --host 127.0.0.1 --port 8000
```

Smoke checks against a running local server:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/model/metadata

$body = Get-Content artifacts/model/final_price_model_v1/sample_request.json -Raw
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/predict `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Optional non-destructive CLI checks (no production promote):

```powershell
npx vercel@latest --version
npx vercel@latest build
```

`vercel build` validates packaging when the CLI and project link are available.
It does not publish a production deployment by itself.

## Deploy with Vercel CLI (preview)

From the repository root, with the model package present on disk:

```powershell
npx vercel@latest
```

Follow the prompts the first time (scope, link/create project). Subsequent
preview deploys:

```powershell
npx vercel@latest
```

Production promote (only when you intend to ship):

```powershell
npx vercel@latest --prod
```

### Environment variables

Usually none are required. The service defaults to:

```text
artifacts/model/final_price_model_v1/final_price_model_v1.joblib
```

Override only if the artifact is stored elsewhere:

| Name | Purpose |
| --- | --- |
| `USED_CAR_MODEL_ARTIFACT` | Absolute or repo-relative path to the `.joblib` file |

Set via Project Settings → Environment Variables, or:

```powershell
npx vercel@latest env add USED_CAR_MODEL_ARTIFACT
```

## Git integration

1. Ensure the production model package is committed (`.gitignore` allows
   `artifacts/model/final_price_model_v1/**` while still ignoring other
   artifacts and datasets).
2. Push the branch to GitHub/GitLab/Bitbucket.
3. Import the repo in the Vercel dashboard (Framework Preset: other / Python
   FastAPI detection via `app.py` + `requirements.txt`).
4. Leave the root directory as the repo root.
5. Each push creates a preview deployment; merge to the production branch
   promotes when production branch deploys are enabled.

CLI deploys upload local files filtered by `.vercelignore`. Git deploys use the
Git tree, so the model package must be tracked for Git-based builds.

## Post-deploy smoke checks

Replace `$BASE` with the deployment URL:

```powershell
$BASE = "https://your-deployment.vercel.app"

Invoke-RestMethod "$BASE/health"
Invoke-RestMethod "$BASE/model/metadata"
Invoke-WebRequest "$BASE/" | Select-Object StatusCode
Invoke-WebRequest "$BASE/static/styles.css" | Select-Object StatusCode
Invoke-WebRequest "$BASE/docs" | Select-Object StatusCode

$body = Get-Content artifacts/model/final_price_model_v1/sample_request.json -Raw
Invoke-RestMethod `
  -Uri "$BASE/predict" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Expect:

- `/health` → `status` of `ok` and `artifact_exists: true`
- `/predict` → listed-price estimate with range and confidence fields
- `/` and `/static/*` → 200 HTML/CSS/JS from the existing UI

## Rollback

- **Dashboard:** Deployments → open a previous successful deployment → Promote
  to Production.
- **CLI:** redeploy a known-good commit:

  ```powershell
  git checkout <good-commit>
  npx vercel@latest --prod
  ```

- Instant rollback: promote the prior deployment rather than rebuilding when
  the previous build is still available.

## Known serverless / cold-start constraints

- The app runs as **one** Vercel Python function (Fluid compute by default).
- **Cold start:** first request after idle can take longer while Python imports
  numpy/pandas/sklearn and loads the ~3.1 MB joblib artifact.
- **Memory:** the deployment uses Vercel's current Python/FastAPI function
  defaults. Monitor peak memory before changing the project-level function
  configuration.
- **Duration:** the deployment uses the project default. Single predictions
  should complete far below the function limit once the model is warm.
- **Bundle size:** raw datasets, notebooks, and training outputs are excluded;
  keep them out of the deploy root filter.
- **Stateless:** no durable in-function cache across instances; the service
  lazy-loads the artifact per instance.
- **Not a commercial valuation product:** responses remain listed-price
  estimates with confidence and warning codes, same as local Stage 2.

## Related docs

- [Stage 2 prediction API](65-stage2-prediction-api.md)
- [Stage 2 web prediction screen](66-stage2-web-prediction-screen.md)
- [Stage 2 web redesign](67-stage2-web-redesign.md)
