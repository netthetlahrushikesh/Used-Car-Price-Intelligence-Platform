# Three Model Phase Readiness

Date: 2026-06-28

## Purpose

Prepare the repository for the next phase: EDA and model development across three clearly separated model candidates.

The project now has:

1. Live trusted deduped data.
2. External True Value Kaggle data.
3. A combined experimental dataset with explicit lineage columns.

## Model Candidates

| Candidate | Rows | Dataset Path | Role |
| --- | ---: | --- | --- |
| Live trusted deduped model | 3,496 | `data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/listings_modeling_dataset.csv` | Current-market benchmark |
| External True Value model | 5,614 | `data/gold/external/true_value_kaggle_focusedmonk/listings_modeling_dataset.csv` | Larger True Value-only modeling sandbox |
| Combined live + external model | 9,110 | `data/gold/modeling_experiments/three_model_phase_20260628/combined_modeling_dataset.csv` | Experimental higher-row-count model |

Important correction: the official live unique row count is `3,496`, not `3,497`. The `3,497` number came from a weaker registration-sensitive identity check and is not the project identity count.

## Build Command

```powershell
.venv\Scripts\python.exe notebooks\build_three_model_phase_package.py --generated-at 2026-06-28T04:30:00Z
```

This command reads the two approved modeling datasets and writes:

```text
data/gold/modeling_experiments/three_model_phase_20260628/
```

## Combined Dataset Design

The combined dataset keeps the original modeling columns and adds lineage columns:

| Column | Purpose |
| --- | --- |
| `dataset_origin` | Separates live scraped rows from external Kaggle rows |
| `dataset_origin_label` | Human-readable origin label |
| `data_freshness` | Marks current live scrape vs historical external data |
| `market_snapshot_date` | Market date represented by the row |
| `market_snapshot_year` | Feature required for combined modeling |
| `original_listing_key` | Preserves the source dataset's original identity |
| `original_baseline_split` | Preserves the source dataset's previous split |

Combined listing keys are prefixed by origin to prevent accidental collisions:

```text
live::{source}::{original_listing_key}
external_true_value_kaggle::{source}::{original_listing_key}
```

## Validation Result

| Check | Status |
| --- | --- |
| `listing_keys_are_unique_after_origin_prefix` | pass |
| `required_fields_complete` | pass |
| `target_price_positive` | pass |
| `both_dataset_origins_present` | pass |

Combined row mix:

| Origin | Rows | Share |
| --- | ---: | ---: |
| `external_true_value_kaggle` | 5,614 | 61.62% |
| `live_scraped_100k_deduped` | 3,496 | 38.38% |

Source mix:

| Source | Rows | Share |
| --- | ---: | ---: |
| `true_value_external_kaggle` | 5,614 | 61.62% |
| `true_value` | 2,439 | 26.77% |
| `mahindra_first_choice` | 579 | 6.36% |
| `spinny` | 478 | 5.25% |

## Baseline Snapshot

The baseline is still the transparent comparable-median benchmark, not the final ML model.

| Candidate | Rows | MAE | MAPE | Within 20% |
| --- | ---: | ---: | ---: | ---: |
| Live trusted deduped | 3,496 | 106,740 INR | 22.96% | 60.50% |
| External True Value | 5,614 | 66,239 INR | 16.36% | 76.07% |
| Combined live + external | 9,110 | 83,336 INR | 20.76% | 70.07% |

Combined baseline by origin:

| Origin | Test Rows | MAE | MAPE | Within 20% |
| --- | ---: | ---: | ---: | ---: |
| `external_true_value_kaggle` | 1,147 | 65,800 INR | 15.26% | 77.33% |
| `live_scraped_100k_deduped` | 687 | 112,615 INR | 29.96% | 57.93% |

## Key Outputs

```text
data/gold/modeling_experiments/three_model_phase_20260628/experiment_registry.md
data/gold/modeling_experiments/three_model_phase_20260628/combined_dataset_manifest.md
data/gold/modeling_experiments/three_model_phase_20260628/combined_modeling_dataset.csv
data/gold/modeling_experiments/three_model_phase_20260628/combined_baseline_model.md
data/gold/modeling_experiments/three_model_phase_20260628/combined_baseline_predictions.csv
```

## Repo Refinements Added

- Added reusable experiment builder: `src/used_car_price_intelligence/experiments/three_model_phase.py`.
- Added notebook-style runner: `notebooks/build_three_model_phase_package.py`.
- Added lineage validation test: `tests/unit/test_three_model_phase.py`.
- Added this readiness document.

## Guardrails For The Next Step

- Do not train on the 103,719 observation CSV as if every row is an independent car.
- Do not silently concatenate live and external rows without `dataset_origin`.
- Do not call the live dataset 3,497 rows; the accepted unique count is 3,496.
- Do not treat the combined model as production-grade until source and time bias are reviewed.
- For serious ML on the combined dataset, include `dataset_origin` and `market_snapshot_year` as explicit features.

## Next Modeling Plan

1. Run EDA independently for all three candidates.
2. Build one preprocessing pipeline shared by all three candidates.
3. Train the same first ML model family on all three datasets.
4. Compare metrics overall and by `dataset_origin`, `source`, `city`, `brand_model`, `fuel_type`, and `model_year`.
5. Pick the best portfolio-facing model based on validation behavior, not only row count.
