# Stage 2 Prediction API

Date: 2026-07-01

## Goal

Turn the final model artifact into a small backend service that the future
website can call.

This is still Stage 2, not the website phase. The API proves that the model can
be loaded once, validated through a stable request contract, and used through
HTTP endpoints.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check artifact path, existence, and load state |
| `GET` | `/model/metadata` | Return model version, metrics source, features, and config |
| `POST` | `/predict` | Return one price estimate |
| `POST` | `/predict/batch` | Return up to 50 estimates for offline checks |

## Run Locally

Export the artifact first if it is missing:

```powershell
python scripts/export_final_price_model.py
```

Start the API:

```powershell
python scripts/run_prediction_api.py --host 127.0.0.1 --port 8000
```

Optional custom artifact path:

```powershell
python scripts/run_prediction_api.py --artifact artifacts/model/final_price_model_v1/final_price_model_v1.joblib
```

The same can be configured with:

```powershell
$env:USED_CAR_MODEL_ARTIFACT="C:\path\to\final_price_model_v1.joblib"
```

## Example Request

```powershell
$body = @{
  brand = "Maruti Suzuki"
  model = "Swift"
  variant = "VXI"
  model_year = 2019
  km_driven = 45000
  fuel_type = "petrol"
  transmission = "manual"
  city = "Hyderabad"
  state = "Telangana"
  ownership = 1
  registration_code = "TS"
  source_context = "market_default"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/predict" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

## Response Interpretation

The API returns a range and confidence, not only one number.

Important fields:

- `predicted_price_inr`: estimated listed price.
- `price_range_low_inr` and `price_range_high_inr`: guidance band for UI display.
- `confidence`: high, medium, or low.
- `warning_codes`: model limitations that the website should surface.

Warnings are expected for rare models, unseen cities, premium cars, and inputs
outside training policy.

## Validation

Run the API tests:

```powershell
python -m pytest tests/unit/test_prediction_api.py
```

Full project check:

```powershell
python -m pytest
```

## Decision

Use this FastAPI service as the first backend boundary for the website. The
frontend should call `/predict`, show the price range and confidence, and avoid
presenting the estimate as an exact resale value.

## Next Step

Build the website form and result-card flow against this API contract.

The first web surface is tracked in:

```text
docs/66-stage2-web-prediction-screen.md
```
