# External True Value Dataset Integration

Date: 2026-06-28

## Goal

Process an external True Value-only dataset through the same project pipeline style used for scraped data, while keeping it separate from live scraped gold snapshots.

This phase exists because the 100k observation scrape produced many repeated observations, not 100k unique cars. The external dataset gives us another True Value-only source for EDA and baseline modeling without mixing in OLX-style self-listed data or non-True-Value sources.

## Dataset

| Field | Value |
| --- | --- |
| Dataset | `focusedmonk/true-value-cars-dataset` |
| Source URL | `https://www.kaggle.com/datasets/focusedmonk/true-value-cars-dataset` |
| License | `CC0-1.0` |
| Raw files | `train.csv`, `test.csv` |
| Project source namespace | `true_value_external_kaggle` |
| Raw path | `data/external/raw/true_value_kaggle_focusedmonk/` |
| Gold external path | `data/gold/external/true_value_kaggle_focusedmonk/` |

## Separation Rules

- External Kaggle rows are not merged into live scraped snapshots.
- The source namespace is `true_value_external_kaggle`, not `true_value`.
- Original Kaggle train/test membership is preserved as metadata only.
- The project creates its own deterministic train/test split for baseline modeling.
- Customer-to-customer rows are quarantined from trusted modeling.
- Rows with `assured_buy=False` are quarantined from the trusted modeling dataset.
- Rows must pass canonical quality checks before entering the modeling CSV.

## Pipeline Command

```powershell
.venv\Scripts\python.exe notebooks\build_true_value_external_kaggle_package.py --generated-at 2026-06-28T03:30:00Z
```

The runner calls `used_car_price_intelligence.external.build_true_value_kaggle_package()` and writes:

```text
data/external/profile/true_value_kaggle_focusedmonk/
data/gold/external/true_value_kaggle_focusedmonk/
```

## Raw Profile

| Metric | Count |
| --- | ---: |
| Raw rows | 7,399 |
| Train file rows | 6,399 |
| Test file rows | 1,000 |
| Duplicate raw ids | 1,000 |
| Exact duplicate raw rows | 0 |
| Duplicate core vehicle-price rows | 0 |
| Unique core vehicle-price rows | 7,399 |

Important finding: the `id` column repeats across `train.csv` and `test.csv`, so it cannot be used by itself. The project identity uses:

```text
true_value_external_kaggle_{split}_{id}
```

Top raw missing fields:

| Field | Missing |
| --- | ---: |
| `original_price` | 3,279 |
| `car_availability` | 620 |
| `transmission` | 556 |
| `source` | 126 |
| `body_type` | 103 |

## Canonical Mapping Decisions

| Raw field | Canonical field |
| --- | --- |
| `sale_price` | `listed_price_inr` |
| `kms_run` | `km_driven` |
| `yr_mfr` | `model_year`, `manufacture_year` |
| `make` | `brand` |
| `model` | `model` |
| `variant` | `variant` |
| `fuel_type` | `fuel_type` |
| `transmission` | `transmission` |
| `rto` | `registration_code`, `registration_state` |
| `total_owners` | `ownership` |
| `assured_buy` | `is_certified` |
| `car_availability` | `is_available` |
| `ad_created_on` | `listing_posted_at`, `first_seen_at` |

Model names are normalized before quality evaluation. For example:

```text
Wagon-R-1-0 -> Wagon R
wagon r 1.0 -> Wagon R
```

Engine/displacement details remain useful in `variant`, but they should not pollute the model-family column.

## Quality Result

| Metric | Count |
| --- | ---: |
| Raw rows | 7,399 |
| Canonical rows | 7,399 |
| Trusted pricing-ready modeling rows | 5,614 |
| Quarantined rows | 1,785 |

Quarantine reasons can overlap:

| Reason | Rows |
| --- | ---: |
| `external_assured_buy_false` | 1,258 |
| `parse_confidence_below_gold_threshold` | 569 |
| `missing_transmission` | 556 |
| `listing_unavailable` | 70 |
| `external_untrusted_customer_to_customer_channel` | 43 |
| `missing_price` | 3 |
| `invalid_price` | 3 |
| `invalid_km` | 2 |
| `variant_contains_price_text` | 2 |

Pricing-ready required field completeness:

| Field | Completeness |
| --- | ---: |
| `source` | 100.00% |
| `source_listing_id` | 100.00% |
| `city` | 100.00% |
| `state` | 100.00% |
| `brand` | 100.00% |
| `model` | 100.00% |
| `variant` | 100.00% |
| `model_year` | 100.00% |
| `fuel_type` | 100.00% |
| `transmission` | 100.00% |
| `km_driven` | 100.00% |
| `ownership` | 100.00% |
| `registration_code` | 100.00% |
| `listed_price_inr` | 100.00% |
| `is_certified` | 100.00% |
| `is_available` | 94.75% |

## Modeling Package

Main dataset:

```text
data/gold/external/true_value_kaggle_focusedmonk/listings_modeling_dataset.csv
```

Validation:

| Check | Status |
| --- | --- |
| `records_are_true_value_external_only` | pass |
| `listing_keys_are_unique` | pass |
| `required_modeling_fields_complete` | pass |
| `target_price_positive` | pass |

Baseline split:

| Split | Rows |
| --- | ---: |
| Train | 4,448 |
| Test | 1,166 |

Baseline comparable-median result:

| Metric | Value |
| --- | ---: |
| MAE | 66,239 INR |
| RMSE | 126,628 INR |
| Median absolute error | 38,250 INR |
| MAPE | 16.36% |
| Median APE | 10.15% |
| Within 10% | 49.49% |
| Within 20% | 76.07% |

This is a useful benchmark for EDA and modeling practice. It should not be presented as a production valuation engine because the dataset is historical and single-source.

## Key Output Files

```text
data/external/profile/true_value_kaggle_focusedmonk/true_value_external_kaggle_raw_profile.md
data/gold/external/true_value_kaggle_focusedmonk/dataset_manifest.md
data/gold/external/true_value_kaggle_focusedmonk/listings_modeling_dataset.csv
data/gold/external/true_value_kaggle_focusedmonk/eda_summary.md
data/gold/external/true_value_kaggle_focusedmonk/baseline_model.md
data/gold/external/true_value_kaggle_focusedmonk/quality_summary.md
data/gold/external/true_value_kaggle_focusedmonk/true_value_external_kaggle_canonical_all.jsonl
data/gold/external/true_value_kaggle_focusedmonk/true_value_external_kaggle_pricing_ready.jsonl
data/gold/external/true_value_kaggle_focusedmonk/true_value_external_kaggle_quarantine.jsonl
```

## Limitations

- This is a 2021 historical dataset, not current market inventory.
- It has no live listing URLs, so the package uses `kaggle://...` listing identities.
- It is True Value-only by design, so source-level comparisons are not possible inside this package.
- `original_price` is too incomplete to be a core modeling feature.
- `is_available` is not complete for all pricing-ready rows.
- The model result is a transparent baseline, not the final production model.

## Next Step

Keep this package separate and use it for True Value external EDA/modeling first. If we later combine it with the live scraped True Value-only slice, create a separate bridge manifest that documents:

- source namespaces,
- historical vs current market dates,
- duplicate identity rules,
- feature compatibility,
- leakage risks,
- and the exact combined output path.
