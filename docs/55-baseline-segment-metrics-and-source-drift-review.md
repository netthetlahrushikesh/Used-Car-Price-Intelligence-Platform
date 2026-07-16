# Baseline Segment Metrics And Source Drift Review

Date: 2026-06-28

## Objective

Review the first baseline modeling outputs beyond overall metrics. The key question is not only "which model has the lowest MAE?" but whether the result is trustworthy for a current used-car price intelligence platform.

## Overall Baseline Metrics

| Model | Dataset | Test Rows | MAE | RMSE | MAPE | R2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| External True Value Historical Baseline | External True Value Historical Dataset | 1,123 | 45,505 | 79,945 | 10.81% | 0.882 |
| Combined Trusted Lineage Baseline | Combined Trusted Modeling Dataset | 1,822 | 60,826 | 123,488 | 13.66% | 0.857 |
| Live Trusted Market Baseline | Live Trusted Market Snapshot | 700 | 88,512 | 181,357 | 16.94% | 0.819 |

## Important Interpretation

The External True Value Historical Baseline has the best overall metrics, but it should not automatically be treated as the best production direction.

Why:

- It is a single-source historical dataset.
- It is older: median model year is 2014.
- It has a lower median listed price than the live market snapshot.
- It does not represent the current trusted multi-source market as strongly as the live dataset.

The model with the lowest error is the easiest benchmark dataset, not necessarily the best current-market model.

## Source Drift

| Dataset Origin | Rows | Median Price | Mean Price | Median KM | Median Model Year | Unique Cities | Unique Brand-Models |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| External True Value Historical Dataset | 5,614 | 376,099 | 437,259 | 57,552 | 2014 | 13 | 146 |
| Live Trusted Market Snapshot | 3,496 | 420,000 | 532,440 | 70,004 | 2018 | 29 | 169 |

Live data is newer, geographically broader, and more expensive on average. External data is cleaner/easier, but older and narrower.

## Source-Level Error

### Combined Trusted Lineage Baseline

| Source | Test Rows | MAE | MAPE | R2 |
| --- | ---: | ---: | ---: | ---: |
| Spinny Live | 93 | 167,858 | 20.78% | 0.682 |
| Mahindra First Choice Live | 110 | 150,715 | 19.71% | 0.860 |
| True Value Live | 476 | 49,760 | 16.08% | 0.911 |
| External True Value Historical | 1,143 | 48,076 | 11.49% | 0.836 |

### Live Trusted Market Baseline

| Source | Test Rows | MAE | MAPE | R2 |
| --- | ---: | ---: | ---: | ---: |
| Spinny Live | 94 | 204,193 | 21.50% | 0.553 |
| Mahindra First Choice Live | 106 | 171,432 | 23.65% | 0.829 |
| True Value Live | 500 | 49,185 | 14.66% | 0.906 |

## Source-Level Interpretation

The model is strong on True Value rows but weak on Spinny and Mahindra First Choice rows.

Likely causes:

- Spinny and MFC contain newer and higher-priced vehicles.
- Premium/luxury listings are concentrated in live sources.
- There are fewer Spinny and MFC rows, so the model has less examples.
- Source-specific pricing and inspection standards may differ.

## Dataset-Origin Error In Combined Model

| Origin | Test Rows | MAE | MAPE | R2 |
| --- | ---: | ---: | ---: | ---: |
| Live Trusted Market Snapshot | 679 | 82,290 | 17.31% | 0.861 |
| External True Value Historical Dataset | 1,143 | 48,076 | 11.49% | 0.836 |

The combined model improves over the live-only model on live rows, but still performs much better on external historical rows.

This means the combined model is useful, but it remains source-sensitive.

## Common Vs Rare Brand-Model Error

| Model | Group | Rows | MAE | MAPE | R2 |
| --- | --- | ---: | ---: | ---: | ---: |
| Combined Trusted Lineage Baseline | Rare brand-model | 85 | 181,006 | 24.66% | 0.769 |
| Combined Trusted Lineage Baseline | Common brand-model | 1,737 | 54,945 | 13.12% | 0.863 |
| External True Value Historical Baseline | Rare brand-model | 46 | 125,448 | 26.68% | 0.724 |
| External True Value Historical Baseline | Common brand-model | 1,077 | 42,091 | 10.13% | 0.903 |
| Live Trusted Market Baseline | Rare brand-model | 45 | 282,091 | 26.52% | 0.513 |
| Live Trusted Market Baseline | Common brand-model | 655 | 75,213 | 16.28% | 0.885 |

Rare brand-model performance is a real weakness, not a data blocker. It must become a standard segment metric in every future model.

## Price-Tail Error

Price-tail rows are genuine and were kept, but the model struggles on high-price luxury cars.

| Model | Price Group | Rows | Actual Median | Predicted Median | MAE | MAPE |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Combined Trusted Lineage Baseline | High price tail | 2 | 3,845,000 | 2,663,162 | 1,528,035 | 37.49% |
| Combined Trusted Lineage Baseline | Normal price range | 1,819 | 388,299 | 396,448 | 59,225 | 13.57% |
| Combined Trusted Lineage Baseline | Low price tail | 1 | 30,000 | 68,852 | 38,852 | 129.51% |
| Live Trusted Market Baseline | High price tail | 2 | 3,415,000 | 1,328,337 | 2,086,663 | 61.21% |
| Live Trusted Market Baseline | Normal price range | 697 | 420,000 | 427,042 | 82,876 | 16.77% |
| Live Trusted Market Baseline | Low price tail | 1 | 46,000 | 66,777 | 20,777 | 45.17% |

The high-price tail is under-predicted. This is expected with a baseline model because luxury cars are underrepresented.

## City-Level Notes

Worst live-market city segments by MAE:

- Hyderabad: MAE 207,774
- Chennai: MAE 133,863
- Kolkata: MAE 123,611
- Pune: MAE 108,658

These cities likely have more premium or source-mixed listings in the test sample. Future modeling should evaluate city-source interactions.

## Brand-Model Notes

Worst common brand-model segments by MAE include:

- Honda Amaze
- Hyundai Creta
- Hyundai Verna
- Maruti Suzuki Ciaz
- Maruti Suzuki Brezza

Some R2 values are weak or negative for individual brand-model groups, which means group-specific predictions can be poor even when the overall model looks acceptable.

## Decision

Do not pick the External True Value Historical Baseline as the final direction only because it has the lowest MAE.

Recommended next modeling direction:

1. Treat the External True Value Historical Baseline as the clean historical benchmark.
2. Treat the Combined Trusted Lineage Baseline as the primary improvement candidate because it has broader coverage and improves over live-only on live rows.
3. Keep the Live Trusted Market Baseline as the current-market reference.
4. Improve high-price/premium-car performance.
5. Improve rare brand-model performance.
6. Continue reporting source, origin, rare/common, and price-tail metrics for every future model.

## Next Modeling Experiments

Run these improvements in order:

1. Log-price target baseline.
2. Gradient boosting baseline.
3. Source-aware validation.
4. Rare-category handling.
5. Premium/luxury segment feature review.

The immediate next experiment should be a log-price target model using the same three-dataset structure and the same segment metrics.
