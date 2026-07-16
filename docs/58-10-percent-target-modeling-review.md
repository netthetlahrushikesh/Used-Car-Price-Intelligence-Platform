# 10 Percent Target Modeling Review

Date: 2026-06-29

## Objective

Push the combined trusted used-car price model toward a 10% MAPE target without removing genuine rows or hiding hard market-tail cases.

The previous best combined model was the Premium-Weighted Log-Gradient Boosting model:

- Combined MAE: 56,753
- Combined MAPE: 11.86%
- Combined R2: 0.876

The new target was to reach MAPE at or below 10% on the Combined Trusted Modeling Dataset.

## Final Experiment

Notebook:

- `notebooks/used_car_price_intelligence_10_percent_target_modeling.py`
- `notebooks/used_car_price_intelligence_10_percent_target_modeling.ipynb`

Output folder:

- `notebooks/outputs/used_car_price_intelligence_10_percent_target_modeling/`

Model:

- Native categorical `HistGradientBoostingRegressor`
- target: `log1p(listed_price_inr)`
- categorical handling: pandas `category` dtype with native sklearn categorical splits
- high-cardinality protection: top 180 categories retained, remaining values grouped as `__other__`
- target encoding: leakage-controlled out-of-fold target encoding

Target-encoded fields:

- brand
- model
- variant
- brand_model
- source_city
- source_brand
- city_brand
- registration_code
- brand_fuel_type
- brand_transmission

The target encoding is fitted only from training folds. Test rows do not contribute to their own encoded values.

## Overall Results

| Dataset | MAE | RMSE | MAPE | R2 | Underprediction Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| External True Value Historical Dataset | 35,773 | 63,302 | 8.32% | 0.926 | 50.76% |
| Combined Trusted Modeling Dataset | 47,389 | 104,458 | 9.88% | 0.897 | 50.93% |
| Live Trusted Market Snapshot | 73,651 | 157,589 | 13.40% | 0.863 | 53.57% |

## Target Status

The 10% combined target is achieved.

| Metric | Value |
| --- | ---: |
| Combined MAPE | 9.88% |
| Combined MAE | 47,389 |
| Combined R2 | 0.897 |
| Target achieved | yes |

This is now the strongest headline model for the combined trusted dataset.

## Improvement Against Previous Models

| Dataset | Baseline | Baseline MAPE | Target-Encoded MAPE | MAPE Improvement | Baseline MAE | Target-Encoded MAE |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Combined Trusted Modeling Dataset | Raw-Price Random Forest | 13.66% | 9.88% | +3.77 pts | 60,826 | 47,389 |
| Combined Trusted Modeling Dataset | Log-Price Random Forest | 13.48% | 9.88% | +3.59 pts | 61,943 | 47,389 |
| Combined Trusted Modeling Dataset | Premium-Weighted Log-Gradient Boosting | 11.86% | 9.88% | +1.98 pts | 56,753 | 47,389 |
| Live Trusted Market Snapshot | Raw-Price Random Forest | 16.94% | 13.40% | +3.54 pts | 88,512 | 73,651 |
| External True Value Historical Dataset | Raw-Price Random Forest | 10.81% | 8.32% | +2.48 pts | 45,505 | 35,773 |

## Segment Improvements

Important combined model segment metrics:

| Segment | Rows | MAE | MAPE | Underprediction Rate |
| --- | ---: | ---: | ---: | ---: |
| Common brand-model | 1,737 | 40,917 | 9.39% | 50.89% |
| Rare brand-model | 85 | 179,635 | 19.88% | 51.76% |
| Normal price range | 1,819 | 45,678 | 9.80% | 50.91% |
| Spinny Live | 93 | 124,530 | 12.62% | 51.61% |
| Mahindra First Choice Live | 110 | 149,896 | 16.97% | 50.91% |
| True Value Live | 476 | 40,579 | 12.68% | 53.78% |
| External True Value Historical | 1,143 | 34,083 | 7.81% | 49.69% |

The largest improvement is on normal market rows and common brand-model groups.

## Remaining Weakness

The target-encoded model improves the headline combined MAPE, but it is not the best high-price-tail model.

| Dataset | High-Price Tail Model | High-Tail MAE | High-Tail MAPE |
| --- | --- | ---: | ---: |
| Combined Trusted Modeling Dataset | Premium-Weighted Log-Gradient Boosting | 1,330,252 | 34.82% |
| Combined Trusted Modeling Dataset | Raw-Price Random Forest | 1,528,035 | 37.49% |
| Combined Trusted Modeling Dataset | Target-Encoded Native HGB | 1,612,623 | 41.51% |
| Combined Trusted Modeling Dataset | Log-Price Random Forest | 1,820,215 | 45.90% |

This means:

- Target encoding gives the best overall combined model.
- Premium-weighted gradient boosting remains better for high-price tail rows.
- High-price rows are still 100% underpredicted.
- We should not remove those rows to improve the metric.

## Decision

Promote the Target-Encoded Native HGB model as the **main 10% MAPE candidate** for the combined trusted dataset.

Do not call it the final pricing model yet.

Why it should be promoted:

- Combined MAPE is below 10%.
- Combined MAE improves materially.
- Live MAPE improves strongly.
- External historical MAPE improves strongly.
- The improvement is achieved without deleting market-tail rows.

Why it is not final:

- Rare brand-model rows are still much weaker than common rows.
- High-price rows remain underpredicted.
- Premium-weighted gradient boosting is still better on the high-price tail.

## Next Step

Keep two model tracks:

1. Main valuation model:
   - Target-Encoded Native HGB
   - headline combined MAPE: 9.88%

2. Premium-tail improvement track:
   - start from Premium-Weighted Log-Gradient Boosting
   - improve high-price and luxury rows
   - evaluate separately before merging into the main model

The next technical improvement should be premium-tail modeling, not more generic overall-MAPE tuning.

## Post-Validation Update

Repeated-split validation was completed after this checkpoint.

Validation result:

- best/primary split MAPE: 9.88%
- seven-split mean MAPE: 10.33%
- seven-split MAPE range: 9.88% to 10.73%
- validation status: usable with warning

Updated wording:

> The model achieved a 9.88% MAPE primary checkpoint and averaged 10.33% MAPE across repeated validation splits.

Do not describe the model as guaranteed below 10% across all splits.

See:

- `docs/59-model-stability-validation.md`
