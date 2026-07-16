# Gradient Boosting Modeling Review

Date: 2026-06-28

## Objective

Test whether a stronger tabular model can improve the weaknesses found in the raw-price and log-price Random Forest baselines:

- high-price and premium-car underprediction
- weaker Spinny and Mahindra First Choice performance
- rare brand-model instability
- source drift between live and external rows

The experiment keeps the same three-dataset structure:

1. Live Trusted Market Snapshot
2. External True Value Historical Dataset
3. Combined Trusted Modeling Dataset

## Final Experiment Design

Notebook:

- `notebooks/used_car_price_intelligence_gradient_boosting_modeling.py`
- `notebooks/used_car_price_intelligence_gradient_boosting_modeling.ipynb`

Model:

- `HistGradientBoostingRegressor`
- target: `log1p(listed_price_inr)`
- categorical encoding: ordinal encoding with unknown value `-1`
- sample weighting: premium, rare brand-model, live premium-source, and high-price rows receive higher training weight

Feature additions:

- luxury brand flag
- vehicle age bucket
- kilometer bucket
- km per year
- log km driven
- age/km interaction
- low/high km-for-age flags
- source-city interaction
- source-brand interaction
- city-brand interaction
- brand-fuel interaction
- brand-transmission interaction
- luxury-transmission interaction

Important implementation note:

- Dense one-hot gradient boosting was too slow for iteration and hit the local run timeout.
- The final implementation uses ordinal encoding, which completed the full three-model run in under one minute locally.

## Overall Results

| Model | Dataset | MAE | RMSE | MAPE | R2 | Underprediction Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Premium-Weighted Log-Gradient Boosting | External True Value Historical Dataset | 41,362 | 79,996 | 9.39% | 0.882 | 50.13% |
| Premium-Weighted Log-Gradient Boosting | Combined Trusted Modeling Dataset | 56,753 | 114,706 | 11.86% | 0.876 | 52.52% |
| Premium-Weighted Log-Gradient Boosting | Live Trusted Market Snapshot | 90,271 | 178,436 | 16.43% | 0.825 | 54.29% |

## Improvement Against Previous Baselines

| Dataset | Baseline | Baseline MAE | Gradient MAE | MAE Change | Baseline MAPE | Gradient MAPE | MAPE Change | R2 Change |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Combined Trusted Modeling Dataset | Raw-Price Random Forest | 60,826 | 56,753 | +6.70% | 13.66% | 11.86% | +1.80 pts | +0.0197 |
| Combined Trusted Modeling Dataset | Log-Price Random Forest | 61,943 | 56,753 | +8.38% | 13.48% | 11.86% | +1.62 pts | +0.0291 |
| External True Value Historical Dataset | Raw-Price Random Forest | 45,505 | 41,362 | +9.11% | 10.81% | 9.39% | +1.42 pts | ~flat |
| External True Value Historical Dataset | Log-Price Random Forest | 48,402 | 41,362 | +14.55% | 11.12% | 9.39% | +1.74 pts | +0.0476 |
| Live Trusted Market Snapshot | Raw-Price Random Forest | 88,512 | 90,271 | -1.99% | 16.94% | 16.43% | +0.51 pts | +0.0058 |
| Live Trusted Market Snapshot | Log-Price Random Forest | 89,581 | 90,271 | -0.77% | 16.44% | 16.43% | +0.01 pts | +0.0153 |

Interpretation:

- This is the strongest combined-dataset model so far.
- It clearly beats both Random Forest baselines on combined MAPE and R2.
- It improves external historical rows strongly.
- Live-only MAE is slightly worse than raw Random Forest, but live MAPE and R2 improve.

## High-Price Tail

| Dataset | Baseline | Baseline High-Tail MAE | Gradient High-Tail MAE | MAE Improvement | Baseline MAPE | Gradient MAPE |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Combined Trusted Modeling Dataset | Raw-Price Random Forest | 1,528,035 | 1,330,252 | +197,783 | 37.49% | 34.82% |
| Combined Trusted Modeling Dataset | Log-Price Random Forest | 1,820,215 | 1,330,252 | +489,963 | 45.90% | 34.82% |
| Live Trusted Market Snapshot | Raw-Price Random Forest | 2,086,663 | 1,753,663 | +333,000 | 61.21% | 51.44% |
| Live Trusted Market Snapshot | Log-Price Random Forest | 2,067,995 | 1,753,663 | +314,332 | 60.63% | 51.44% |

This is the most important improvement from the experiment.

The model still underpredicts all high-price tail rows, but the absolute error is materially lower than both Random Forest baselines.

## Segment Weaknesses Still Present

The model is not final.

Remaining issues:

- Rare brand-model rows remain much weaker than common brand-model rows.
- High-price rows are still 100% underpredicted.
- Live Spinny and Mahindra First Choice rows still have higher MAE than True Value rows.
- Live-only MAE does not beat the raw Random Forest baseline.

Important segment metrics:

| Model/Dataset | Segment | Rows | MAE | MAPE | Underprediction Rate |
| --- | --- | ---: | ---: | ---: | ---: |
| Combined Gradient | Rare brand-model | 85 | 205,212 | 22.53% | 62.35% |
| Combined Gradient | Common brand-model | 1,737 | 49,489 | 11.34% | 52.04% |
| Combined Gradient | Spinny Live | 93 | 151,938 | 17.07% | 44.09% |
| Combined Gradient | Mahindra First Choice Live | 110 | 160,617 | 19.91% | 56.36% |
| Combined Gradient | True Value Live | 476 | 49,771 | 14.93% | 53.99% |

## Decision

Promote the premium-weighted log-gradient boosting model as the current strongest combined-model candidate, not as the final production model.

Why:

- It improves the combined model over both Random Forest baselines.
- It improves the high-price tail, which was the main reason for this experiment.
- It has better combined R2 and MAPE.
- It keeps the same dataset and segment-evaluation structure.

Why not final:

- Rare brand-model error is still high.
- High-price rows are improved but still underpredicted.
- Live-only MAE is slightly worse than raw Random Forest.

## Next Step

The next experiment should not be another generic model.

Recommended next phase:

1. Keep this model as the current primary combined baseline.
2. Add explicit premium-segment feature review:
   - luxury/premium brand list validation
   - body type if available
   - engine/trim parsing if available
   - city-source premium density
3. Add rare-category strategy:
   - brand-model frequency features
   - brand-level fallback features
   - variant cleanup and grouping
4. Try a two-stage approach:
   - stage 1: classify normal vs premium/high-price likelihood
   - stage 2: price model with premium-adjusted features
5. Continue using the same source, rare/common, and price-tail metrics.

This is the first model that looks like a serious candidate for the project story, but it still needs premium-segment hardening before we call it final.
