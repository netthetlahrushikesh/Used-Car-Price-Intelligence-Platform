# 100k Gold Package

Date: 2026-06-27

## Result

The trusted high-scale extraction reached the first 100k observation target.

| Metric | Count |
| --- | ---: |
| Pricing-ready observations | 103,719 |
| Target overage | 3,719 |
| Quarantined rows | 0 |
| Source runs | 1,580 |
| Listing-producing source runs | 1,549 |
| No-inventory source runs | 31 |
| Deduped unique listing keys | 3,496 |

## Source Mix

| Source | Pricing Ready | Share |
| --- | ---: | ---: |
| True Value | 78,569 | 75.75% |
| Mahindra First Choice | 14,196 | 13.69% |
| Spinny | 10,954 | 10.56% |

True Value dominates the observation-level dataset. This is acceptable for the first trusted source package because it is dealer/evaluator-backed inventory, but source imbalance must be handled explicitly in EDA and modeling.

## Key Outputs

Observation-level gold export:

```text
data/gold/exports/snapshot_20260627_100k_observation_run/snapshot_20260627_100k_observation_run_pricing_ready_observations.csv
data/gold/exports/snapshot_20260627_100k_observation_run/snapshot_20260627_100k_observation_run_pricing_ready_observations.jsonl
```

Deduped modeling package:

```text
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/listings_modeling_dataset.csv
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/eda_summary.md
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/baseline_model.md
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/dataset_manifest.md
```

Control artifacts:

```text
data/gold/collection_ledger/trusted_collection_v12_20260627_100k_observation_run.json
data/gold/listing_lifecycle/listing_lifecycle_v10_20260627_100k_observation_run.json
data/gold/snapshots/snapshot_20260627_100k_observation_run_manifest.json
data/gold/exports/snapshot_20260627_100k_observation_run/package_summary.md
```

## Important Dataset Policy

There are two valid datasets now:

1. Observation export: 103,719 pricing-ready rows. This includes repeated same-day observations of the same listings across repeated rounds.
2. Modeling dataset: 3,496 deduped rows. This keeps one latest row per lifecycle listing key and is the right starting point for normal price modeling.

Do not train a normal supervised price model on the 103k observation CSV without handling repeated listing keys, because it will overweight the same vehicles many times. Use it for source/run QA, repeated snapshot analysis, and pipeline-scale evidence.

## Baseline Modeling Check

The deduped package validation passed:

| Check | Result |
| --- | --- |
| Records do not exceed pricing-ready observations | pass |
| Records match lifecycle unique keys | pass |
| Listing keys are unique | pass |
| Required modeling fields complete | pass |
| Target price positive | pass |

Comparable median baseline on the deduped package:

| Metric | Value |
| --- | ---: |
| Train rows | 2,810 |
| Test rows | 686 |
| MAE | 106,740 INR |
| RMSE | 206,908 INR |
| MAPE | 22.96% |
| Within 10% | 32.94% |
| Within 20% | 60.50% |

This is a transparent benchmark only. It is good enough to start EDA and model development, not to present as a product-grade valuation model.

## Extraction Method

The high-scale loop ran repeated trusted-source rounds:

- True Value batch runs across calibrated city/radius targets.
- Mahindra First Choice stable/probe city set. Low-yield `final_try` cities were excluded from the repeated loop after a transient network failure on Bhopal stopped later MFC jobs.
- Spinny card-only hub captures. Detail-page enrichment was intentionally excluded from scale runs because it was too slow for same-day 100k extraction.

Operational scripts:

```text
notebooks/high_scale_collection_loop.py
notebooks/high_scale_spinny_card_round.py
notebooks/build_high_scale_gold_package.py
```

Final packaging command:

```powershell
$env:PYTHONPATH='src'; .venv\Scripts\python.exe notebooks\build_high_scale_gold_package.py --capture-date 2026-06-27 --require-target
```

## Verification

Commands run after packaging:

```powershell
$env:PYTHONPATH='src'; .venv\Scripts\python.exe -m unittest discover -s tests
.venv\Scripts\python.exe -m compileall src tests notebooks
```

Results:

- 175 unit tests passed.
- `compileall` passed for `src`, `tests`, and `notebooks`.
- Artifact sanity check passed: observation CSV rows = 103,719, modeling CSV rows = 3,496, quarantine = 0.

## Tomorrow's EDA Start

Start with:

```text
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/listings_modeling_dataset.csv
```

Use the 103k observation CSV only when the EDA question is about source reliability, repeated captures, run-level stability, or observation pipeline scale.
