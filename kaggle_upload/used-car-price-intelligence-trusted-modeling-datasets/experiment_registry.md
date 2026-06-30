# Three Model Phase Registry

Experiment id: `three_model_phase_20260628`
Generated at: `2026-06-28T04:30:00Z`

## Model Candidates

| Candidate | Rows | Source Scope | Primary Use |
| --- | ---: | --- | --- |
| Live trusted deduped model | 3,496 | Live scraped trusted sources: True Value, Mahindra First Choice, Spinny. | Current-market benchmark and portfolio credibility. |
| External True Value model | 5,614 | Historical external True Value Kaggle rows only. | Larger modeling sandbox and True Value-only pattern learning. |
| Combined live + external model | 9,110 | Live trusted deduped rows plus separated external True Value rows. | Experimental higher-row-count model with lineage features. |

## Baseline Snapshot

| Candidate | MAE | MAPE | Within 20% |
| --- | ---: | ---: | ---: |
| Live trusted deduped model | 106,739.54 | 22.96% | 60.50% |
| External True Value model | 66,238.68 | 16.36% | 76.07% |
| Combined live + external model | 83,336.38 | 20.76% | 70.07% |

## Next Step Checklist

- Run EDA separately for each candidate before fitting stronger models.
- Build the same train/test protocol for all three candidates.
- For the combined model, include dataset_origin and market_snapshot_year as explicit features.
- Compare metrics overall and by dataset_origin/source/city/brand_model.
- Select the main portfolio model based on honest validation, not row count alone.

## Guardrails

- Do not rename 3,496 live unique rows as 3,497.
- Do not merge the external dataset into live scraped gold snapshots.
- Do not train on repeated 103k observations as independent cars.
- Do not present the combined model as production-grade until temporal bias is reviewed.
