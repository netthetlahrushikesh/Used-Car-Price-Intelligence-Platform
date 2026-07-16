# Dataset Packaging, EDA, and Baseline Model

Date: 2026-06-27

Purpose: convert the phase-final trusted snapshot into an analysis-ready modeling dataset, run the first EDA pass, train a transparent baseline model, and document what is ready before any 100k extraction.

## Decision

Proceed with dataset packaging and baseline modeling from `snapshot_20260627_final_spinny_mfc_try`.

Do not start the final 100k extraction yet. The current dataset is good enough for EDA, baseline modeling, and project storytelling, but the model results show exactly why the high-scale phase should be repeated trusted snapshots with better source balance, not one giant scrape.

## Packaged Dataset

Generated dataset id:

```text
snapshot_20260627_final_spinny_mfc_try_modeling_v0
```

Input snapshot:

```text
data/gold/snapshots/snapshot_20260627_final_spinny_mfc_try_manifest.json
```

Output directory:

```text
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/
```

Validation result:

| Check | Result |
| --- | --- |
| Records match snapshot pricing-ready rows | pass |
| Records match lifecycle unique listing keys | pass |
| Listing keys are unique | pass |
| Required modeling fields complete | pass |
| Target price positive | pass |

Dataset shape:

| Metric | Value |
| --- | ---: |
| Rows | 3,492 |
| Columns | 30 |
| Train rows | 2,830 |
| Test rows | 662 |
| Duplicate listing keys | 0 |

Hard-required modeling fields are complete: source, city, brand, model, model year, fuel type, transmission, kilometers driven, and listed price.

Ownership is not treated as a hard blocker because 16 Spinny rows are missing it. It remains a high-value feature and audit warning.

## EDA Result

Price and usage distribution:

| Field | Median | P25 | P75 |
| --- | ---: | ---: | ---: |
| Listed price | 415,000 | 265,000 | 635,000 |
| Price in lakh | 4.15 | 2.65 | 6.35 |
| Kilometers driven | 70,090 | 44,966 | 98,562 |
| Vehicle age years | 8 | 5 | 11 |

Source mix:

| Source | Rows | Share |
| --- | ---: | ---: |
| True Value | 2,448 | 70.10% |
| Mahindra First Choice | 562 | 16.09% |
| Spinny | 482 | 13.80% |

Top city counts:

| City | Rows |
| --- | ---: |
| Mumbai | 338 |
| Delhi NCR | 329 |
| Bengaluru | 316 |
| Hyderabad | 310 |
| Pune | 216 |

Top brand-model groups:

| Brand Model | Rows |
| --- | ---: |
| Maruti Suzuki Wagon R | 552 |
| Maruti Suzuki Swift | 279 |
| Maruti Suzuki Alto 800 | 273 |
| Maruti Suzuki Swift Dzire | 236 |
| Maruti Suzuki Baleno | 163 |

EDA warnings:

- True Value contributes 70.10% of rows, so source-level metrics are biased.
- 172 rows, or 4.93%, are in brand-model groups with fewer than five rows.
- Ownership is missing for 16 rows, or 0.46%.
- Registration code is missing for 41 rows, or 1.17%.

None of these block baseline modeling. They do block claims that this is a final production-grade valuation model.

## Baseline Model

Model:

```text
baseline_comparable_median_v0
```

Method: hierarchical comparable median fallback.

The model predicts listed price from comparable groups in this order:

1. city, brand, model, model year, fuel, transmission, ownership
2. brand, model, model year, fuel, transmission, ownership
3. brand, model, model year, fuel, transmission
4. brand, model, fuel, transmission
5. brand, model
6. brand
7. global median

Source is kept for audit slices but is not used as a prediction feature.

Metrics:

| Model | Test Rows | MAE | RMSE | Median AE | MAPE | Median APE | Within 20% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Comparable median | 662 | 108,475 | 206,767 | 60,000 | 24.03% | 16.36% | 58.01% |
| Global median only | 662 | 244,928 | 423,187 | 160,500 | 60.77% | 39.22% | 26.89% |

The comparable baseline clearly beats the global median, but a 24.03% average percentage error is not good enough for a user-facing valuation product.

## Interpretation

This phase proves three things:

1. The acquisition and quality pipeline can produce a clean pricing-ready dataset.
2. Comparable-based pricing has signal and is a strong first baseline.
3. The model needs more balanced repeated snapshots before moving toward production-grade pricing intelligence.

This is the right point to create the project story:

- old single-site notebook had messy raw scraping,
- new project treated trusted data as the product,
- canonical schema and lifecycle identity made the dataset reproducible,
- EDA revealed source/model imbalance,
- baseline modeling quantified the next data problem.

## Generated Artifacts

```text
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/listings_modeling_dataset.csv
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/listings_modeling_dataset.jsonl
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/data_dictionary.json
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/data_dictionary.md
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/eda_summary.json
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/eda_summary.md
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/baseline_model.json
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/baseline_model.md
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/baseline_predictions.csv
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/dataset_manifest.json
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/dataset_manifest.md
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/final_snapshot_story_summary.md
notebooks/final_snapshot_eda_baseline.py
```

## Reproducible Command

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli package-modeling-dataset --snapshot-manifest data/gold/snapshots/snapshot_20260627_final_spinny_mfc_try_manifest.json --dataset-id snapshot_20260627_final_spinny_mfc_try_modeling_v0 --output-dir data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0 --generated-at 2026-06-27T10:30:00Z
```

## Next Step

Before final 100k extraction:

1. Use this dataset and baseline report for the project write-up.
2. Add a high-scale collection runbook that uses repeated trusted snapshots and source allocation gates.
3. Target the next scaled collection around source balance, not just row count.
4. Move to heavier ML only after repeated snapshots reduce source and model-family imbalance.
