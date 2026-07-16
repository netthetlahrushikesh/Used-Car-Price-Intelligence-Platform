# Model Stability Validation

Date: 2026-06-29

## Objective

Validate whether the 10% MAPE model is stable or whether the 9.88% result came from a lucky train/test split.

Validated model:

- Combined Trusted Lineage Target-Encoded Native HGB
- target: `log1p(listed_price_inr)`
- target encoding: out-of-fold on training rows only
- single-split checkpoint MAPE: 9.88%

Validation artifact:

- `notebooks/used_car_price_intelligence_model_stability_validation.py`
- `notebooks/used_car_price_intelligence_model_stability_validation.ipynb`

Output folder:

- `notebooks/outputs/used_car_price_intelligence_model_stability_validation/`

## Repeated-Split Setup

The validation used seven stratified train/test split seeds:

- 7
- 13
- 21
- 42
- 67
- 101
- 202

For each run:

- train/test split was regenerated
- target encodings were rebuilt inside the training split
- target encoding used 5 out-of-fold folds
- the model was retrained from scratch
- combined dataset metrics and segment metrics were saved

## Stability Metrics

| Seed | MAE | RMSE | MAPE | R2 | Underprediction Rate |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 45,119 | 82,554 | 10.07% | 0.925 | 51.04% |
| 13 | 48,501 | 112,605 | 10.73% | 0.882 | 52.85% |
| 21 | 46,280 | 88,424 | 10.00% | 0.930 | 49.23% |
| 42 | 47,389 | 104,458 | 9.88% | 0.897 | 50.93% |
| 67 | 48,997 | 108,933 | 10.48% | 0.897 | 49.29% |
| 101 | 48,309 | 92,322 | 10.47% | 0.923 | 50.16% |
| 202 | 48,528 | 115,562 | 10.66% | 0.884 | 50.99% |

Summary:

| Metric | Mean | Std | Min | Median | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| MAE | 47,589 | 1,418 | 45,119 | 48,309 | 48,997 |
| MAPE | 10.33% | 0.34 pts | 9.88% | 10.47% | 10.73% |
| R2 | 0.906 | 0.020 | 0.882 | 0.897 | 0.930 |
| Underprediction rate | 50.64% | 1.25 pts | 49.23% | 50.93% | 52.85% |

## Stability Decision

Validation status:

- `usable_with_warning`

Reason:

- The model is strong and materially better than previous baselines.
- The repeated-split mean MAPE is 10.33%, not below 10%.
- Only 1 of 7 validation splits stayed below 10% MAPE.
- The worst split reached 10.73% MAPE.

Therefore, the model should be described as:

> A strong 10%-class model candidate, with a best checkpoint below 10% MAPE and repeated-split average around 10.33%.

It should not be described as:

> A guaranteed sub-10% model across all splits.

## Segment Stability

Key repeated-split segment means:

| Segment | Mean Rows | Mean MAE | Mean MAPE | Max MAPE |
| --- | ---: | ---: | ---: | ---: |
| Common brand-model | 1,726 | 41,268 | 9.61% | 10.02% |
| Rare brand-model | 96 | 161,094 | 23.19% | 30.41% |
| Normal price range | 1,820 | 46,218 | 10.18% | 10.44% |
| High price tail | 2 | 1,738,146 | 43.83% | 53.74% |
| Spinny Live | 95 | 133,099 | 13.21% | 14.73% |
| Mahindra First Choice Live | 115 | 122,944 | 17.96% | 24.20% |
| True Value Live | 484 | 43,129 | 13.08% | 14.30% |
| External True Value Historical | 1,128 | 34,747 | 8.14% | 8.51% |

The model is stable enough on common/normal-market rows, but rare and premium rows remain unstable.

## Fine-Tuning Check

After the first stability run, alternative smoothing and tree configurations were tested.

| Config | Mean MAPE | Std MAPE | Min MAPE | Max MAPE | Hit Rate <= 10% |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current smoothing 10, lr 0.04, leaf 45 | 10.33% | 0.34 pts | 9.88% | 10.73% | 14.29% |
| Smoothing 20, lr 0.04, leaf 31 | 10.35% | 0.31 pts | 9.94% | 10.79% | 28.57% |
| Smoothing 50, lr 0.05, leaf 31 | 10.39% | 0.33 pts | 9.93% | 10.86% | 14.29% |
| Smoothing 50, lr 0.04, leaf 31 | 10.40% | 0.33 pts | 9.90% | 10.84% | 14.29% |

Decision:

- Do not change the current candidate configuration.
- The alternatives did not improve mean stability.
- The current candidate remains the best balance of single-split performance and repeated-split stability.

## Current Model Status

Freeze this as:

- `Model Candidate v1`
- headline checkpoint: 9.88% combined MAPE
- validation mean: 10.33% combined MAPE
- status: strong candidate, usable with warning

Use this wording in portfolio/storytelling:

> The final candidate achieved 9.88% MAPE on the primary split and averaged 10.33% MAPE across seven repeated validation splits.

## Next Step

Do not keep generic tuning right now.

Recommended next work:

1. Create final model interpretation notebook.
2. Explain target encoding and leakage prevention clearly.
3. Keep premium/high-price tail as a separate improvement track.
4. Prepare final GitHub README and project story with both the 9.88% checkpoint and 10.33% stability result.

The project is now strong enough to move from modeling experiments into final presentation and interpretation.
