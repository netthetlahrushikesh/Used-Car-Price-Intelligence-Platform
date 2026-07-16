# Stage 2 Model Artifact And API Schema

Date: 2026-06-30

## Goal

Prepare the modeling work for the future website/API layer.

This stage creates:

- a reusable final model artifact
- a stable prediction request schema
- a stable prediction response schema
- a smoke-test path for loading the artifact and producing one prediction

## Artifact Policy

The deployed artifact is trained on the full `9,110` row combined trusted
modeling dataset.

Validation metrics still come from the notebook validation phase:

| Metric | Value |
| --- | ---: |
| Primary split MAPE | 9.88% |
| Repeated split mean MAPE | 10.33% |
| Repeated split range | 9.88% to 10.73% |
| Status | usable_with_warning |

This means:

- use the full-data artifact for app predictions
- use the validation notebooks/model card for performance claims
- do not claim the full-data artifact has a new independent test score

## Generated Artifact

Default output directory:

```text
artifacts/model/final_price_model_v1/
```

Generated files:

```text
final_price_model_v1.joblib
metadata.json
feature_schema.json
manifest.json
sample_request.json
sample_response.json
```

The binary artifact remains local and ignored by Git. It can later be uploaded
to model storage or bundled with a backend service.

## Export Command

```powershell
python scripts/export_final_price_model.py
```

Smoke test:

```powershell
python scripts/smoke_predict_final_price_model.py
```

## API Request Schema

Canonical file:

```text
schemas/prediction_request.schema.json
```

Required user-facing fields:

| Field | Type | Notes |
| --- | --- | --- |
| `brand` | string | car make |
| `model` | string | car model |
| `model_year` | integer | manufacturing/model year |
| `km_driven` | integer | odometer reading |
| `fuel_type` | string | petrol, diesel, cng, petrol_cng, petrol_lpg, electric, hybrid |
| `transmission` | string | manual, automatic, amt |
| `city` | string | market city |

Optional fields:

| Field | Default |
| --- | --- |
| `variant` | `unknown` |
| `ownership` | `unknown` |
| `registration_code` | `unknown` |
| `state` | `unknown` |
| `source_context` | `market_default` |
| `market_snapshot_year` | `2026` |

`source_context` exists because the current model uses source lineage. For a
general website estimate, use `market_default`, which maps internally to the
current trusted-market default.

## API Response Schema

Canonical file:

```text
schemas/prediction_response.schema.json
```

Important response fields:

| Field | Meaning |
| --- | --- |
| `predicted_price_inr` | estimated listed price |
| `price_range_low_inr` | lower guidance band |
| `price_range_high_inr` | upper guidance band |
| `confidence` | high, medium, or low |
| `warning_codes` | segment/data warnings to show in the UI |
| `price_band` | broad predicted price band |

## Product Interpretation

The API should not show a single price as absolute truth. The website should
show a price range plus confidence.

Recommended UI wording:

> Estimated listed price based on trusted-source market data. This is not a
> final transaction price. Confidence can be lower for rare models, premium
> cars, unseen cities, or out-of-range kilometer/year combinations.

## Next Step

Stage 2 has now moved to:

1. backend prediction endpoint
2. frontend form design
3. result-card UI with prediction, range, confidence, and warnings

Backend API notes are tracked in:

```text
docs/65-stage2-prediction-api.md
```
