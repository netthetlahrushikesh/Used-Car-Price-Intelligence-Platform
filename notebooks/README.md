# Notebooks

This folder contains both production-facing analysis notebooks and utility scripts used during data packaging.

For GitHub, read the notebooks in this order.

## Final Portfolio Notebooks

| Order | Notebook | Purpose | Status |
| ---: | --- | --- | --- |
| 1 | `used_car_price_intelligence_final_eda.ipynb` | Dataset quality, EDA, readiness checks, rare-category coverage, and model-readiness summary | Final |
| 2 | `used_car_price_intelligence_complete_modeling_story.ipynb` | Single end-to-end modeling story with one real final-model training run, baseline comparison, segment review, and stability validation | Main GitHub modeling notebook |
| 3 | `used_car_price_intelligence_model_interpretation.ipynb` | Final model trust layer: permutation importance, segment reliability, error bands, and example predictions | Final |
| 4 | `used_car_price_intelligence_baseline_modeling.ipynb` | Raw-price Random Forest baseline across live, external, and combined datasets | Detailed checkpoint |
| 5 | `used_car_price_intelligence_log_price_modeling.ipynb` | Log-price Random Forest experiment and raw-vs-log comparison | Detailed checkpoint |
| 6 | `used_car_price_intelligence_gradient_boosting_modeling.ipynb` | Premium-weighted log-gradient boosting experiment for high-price tail improvement | Detailed checkpoint |
| 7 | `used_car_price_intelligence_10_percent_target_modeling.ipynb` | Target-encoded native HGB model that reached the main 9.88% MAPE checkpoint | Detailed checkpoint |
| 8 | `used_car_price_intelligence_model_stability_validation.ipynb` | Repeated-split validation for the main candidate | Detailed checkpoint |

## Final Model Position

Main model candidate:

- `Combined Trusted Lineage Target-Encoded Native HGB`
- Primary split MAPE: `9.88%`
- Repeated-split mean MAPE: `10.33%`
- Repeated-split range: `9.88%` to `10.73%`
- Status: `usable_with_warning`

The model should be described as a strong 10%-class model, not as a guaranteed sub-10% model on every split.

For most readers, the complete modeling story notebook is enough. It retrains
the selected final model once and uses the separate modeling notebooks as audit
trails for each experiment stage and the full repeated-split validation.

## Utility Scripts

These files support data packaging, collection workflows, or earlier checkpoints. They are kept for reproducibility, but they are not the main GitHub reading path:

- `build_true_value_external_kaggle_package.py`
- `build_three_model_phase_package.py`
- `build_high_scale_gold_package.py`
- `high_scale_collection_loop.py`
- `high_scale_spinny_card_round.py`
- `kaggle_collection_bridge.py`
- `kaggle_three_model_eda_starter.py`
- `final_snapshot_eda_baseline.py`

## Output Policy

Notebook output artifacts are written under `notebooks/outputs/`, which is intentionally ignored by Git.

The repository should keep:

- notebook source code
- clean `.ipynb` files without embedded outputs
- documentation summaries
- small metadata/config files

The repository should not commit:

- generated model artifacts
- large CSV datasets
- notebook output folders
- raw scrape payloads
