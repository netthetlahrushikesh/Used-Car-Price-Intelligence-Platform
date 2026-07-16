# Log-Price Baseline Review

Date: 2026-06-28

## Objective

Run the second controlled modeling experiment using the same three-model structure as the raw-price Random Forest baseline, but train on `log1p(listed_price_inr)` and convert predictions back to INR for evaluation.

This experiment was chosen because the raw-price baseline was underpredicting high-price and premium cars.

## Experiment Structure

Notebook:

- `notebooks/used_car_price_intelligence_log_price_modeling.py`
- `notebooks/used_car_price_intelligence_log_price_modeling.ipynb`

Output folder:

- `notebooks/outputs/used_car_price_intelligence_log_price_modeling/`

Models:

1. Live Trusted Market Log-Price Baseline
2. External True Value Historical Log-Price Baseline
3. Combined Trusted Lineage Log-Price Baseline

The feature set and train/test strategy were kept aligned with the raw baseline so the target transformation could be evaluated directly.

## Overall Results

| Dataset | Raw MAE | Log MAE | MAE Change | Raw MAPE | Log MAPE | MAPE Change | Raw R2 | Log R2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| External True Value Historical Dataset | 45,505 | 48,402 | -6.37% | 10.81% | 11.12% | -0.32 pts | 0.882 | 0.834 |
| Combined Trusted Modeling Dataset | 60,826 | 61,943 | -1.84% | 13.66% | 13.48% | +0.18 pts | 0.857 | 0.847 |
| Live Trusted Market Snapshot | 88,512 | 89,581 | -1.21% | 16.94% | 16.44% | +0.50 pts | 0.819 | 0.810 |

Interpretation:

- Log-price slightly improves percentage error on live and combined datasets.
- Log-price worsens MAE and R2 across all three datasets.
- External historical data gets worse on every major metric.
- This is useful as a diagnostic experiment, but it is not a clear production upgrade.

## Price-Tail Result

The key test was whether log-price reduces high-price underprediction.

| Dataset | Price Group | Raw MAE | Log MAE | MAE Change | Raw MAPE | Log MAPE | Signed Error Shift |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Combined Trusted Modeling Dataset | High price tail | 1,528,035 | 1,820,215 | -292,180 | 37.49% | 45.90% | -638,377 |
| Combined Trusted Modeling Dataset | Normal price range | 59,225 | 60,025 | -800 | 13.57% | 13.39% | -9,311 |
| Live Trusted Market Snapshot | High price tail | 2,086,663 | 2,067,995 | +18,668 | 61.21% | 60.63% | +18,668 |
| Live Trusted Market Snapshot | Normal price range | 82,876 | 84,013 | -1,138 | 16.77% | 16.29% | -14,183 |

High-price conclusion:

- Live high-price tail improves only slightly.
- Combined high-price tail gets materially worse.
- High-price rows remain 100% underpredicted in the log-price run.
- Log target alone does not solve premium-car valuation.

## Segment Diagnostics

Important log-price segment metrics:

| Model | Segment | Rows | Underprediction Rate | MAE | MAPE | Mean Signed Error |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Combined Log-Price | Rare brand-model | 85 | 51.76% | 184,110 | 23.71% | -50,883 |
| Combined Log-Price | Common brand-model | 1,737 | 53.77% | 55,965 | 12.98% | -6,706 |
| Combined Log-Price | Spinny Live | 93 | 47.31% | 163,983 | 18.61% | -23,347 |
| Combined Log-Price | Mahindra First Choice Live | 110 | 64.55% | 158,605 | 19.63% | -49,578 |
| Combined Log-Price | True Value Live | 476 | 50.21% | 48,551 | 15.54% | -4,540 |
| Live Log-Price | Rare brand-model | 45 | 57.78% | 292,097 | 26.47% | -201,467 |
| Live Log-Price | Spinny Live | 94 | 55.32% | 213,409 | 21.67% | -84,732 |
| Live Log-Price | Mahindra First Choice Live | 106 | 61.32% | 170,424 | 22.19% | -71,667 |
| Live Log-Price | True Value Live | 500 | 50.80% | 49,163 | 14.23% | -9,720 |

The same structural weaknesses remain:

- Rare brand-model rows are much weaker than common brand-model rows.
- Spinny and Mahindra First Choice remain harder than True Value.
- Premium/current-market rows are not represented strongly enough for a simple Random Forest to price them well.

## Decision

Do not promote the log-price Random Forest as the main production candidate.

Use it as a checkpoint:

- It confirms that percentage-error optimization helps normal market rows a little.
- It also proves that log transformation alone is not enough for high-price cars.
- The project now needs a stronger model class and explicit premium-segment handling.

## Next Modeling Step

Move to a gradient boosting experiment using the same three-model structure and the same segment reporting.

Recommended setup:

1. Train a log-target gradient boosting model.
2. Keep the raw-vs-log comparison outputs.
3. Keep price-tail metrics with `min_rows=1`.
4. Add premium-aware features such as luxury brand flag, age bucket, km bucket, and source-origin interactions.
5. Compare against both raw-price Random Forest and log-price Random Forest.
6. Promote only if it improves live/current-market segments and does not worsen high-price tail underprediction.

The next model should be judged by combined evidence: overall MAE, MAPE, source-level error, rare/common error, and high-price signed error.
