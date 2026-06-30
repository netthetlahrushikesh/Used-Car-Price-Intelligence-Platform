# Combined Modeling Dataset Manifest

Dataset id: `combined_live_trusted_plus_external_true_value_20260628`
Experiment id: `three_model_phase_20260628`
Rows: 9,110
Validation: `pass`

## Input Rows

| Input | Rows |
| --- | ---: |
| Live scraped trusted deduped | 3,496 |
| External True Value Kaggle | 5,614 |
| Combined | 9,110 |

## Baseline Split

- Train rows: 7,276
- Test rows: 1,834

## Dataset Origin Mix

| Origin | Rows | Share |
| --- | ---: | ---: |
| external_true_value_kaggle | 5,614 | 61.62% |
| live_scraped_100k_deduped | 3,496 | 38.38% |

## Source Mix

| Source | Rows | Share |
| --- | ---: | ---: |
| true_value_external_kaggle | 5,614 | 61.62% |
| true_value | 2,439 | 26.77% |
| mahindra_first_choice | 579 | 6.36% |
| spinny | 478 | 5.25% |

## Validation Checks

- listing_keys_are_unique_after_origin_prefix: pass
- required_fields_complete: pass
- target_price_positive: pass
- both_dataset_origins_present: pass

## Policy

- This combined dataset is experimental and lineage-explicit.
- Live scraped rows and external historical Kaggle rows remain available as separate model candidates.
- The combined dataset must use dataset_origin and market_snapshot_year during serious ML modeling.
- Do not treat combined baseline metrics as production valuation metrics until temporal leakage and source bias are reviewed.
- Baseline min_group_size is 3; split seed is three_model_phase_combined_v0; test_ratio is 0.2.

## Outputs

- combined_baseline_model_json: `data/gold/modeling_experiments/three_model_phase_20260628/combined_baseline_model.json`
- combined_baseline_model_markdown: `data/gold/modeling_experiments/three_model_phase_20260628/combined_baseline_model.md`
- combined_baseline_predictions_csv: `data/gold/modeling_experiments/three_model_phase_20260628/combined_baseline_predictions.csv`
- combined_dataset_csv: `data/gold/modeling_experiments/three_model_phase_20260628/combined_modeling_dataset.csv`
- combined_dataset_jsonl: `data/gold/modeling_experiments/three_model_phase_20260628/combined_modeling_dataset.jsonl`
- combined_manifest_json: `data/gold/modeling_experiments/three_model_phase_20260628/combined_dataset_manifest.json`
- combined_manifest_markdown: `data/gold/modeling_experiments/three_model_phase_20260628/combined_dataset_manifest.md`
- experiment_registry_json: `data/gold/modeling_experiments/three_model_phase_20260628/experiment_registry.json`
- experiment_registry_markdown: `data/gold/modeling_experiments/three_model_phase_20260628/experiment_registry.md`
