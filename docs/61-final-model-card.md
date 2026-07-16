# Final Model Card

Date: 2026-06-29

## Model Identity

| Field | Value |
| --- | --- |
| Model name | Combined Trusted Lineage Target-Encoded Native HGB |
| Model family | HistGradientBoostingRegressor |
| Target | `listed_price_inr` |
| Target transform | `log1p(listed_price_inr)` |
| Primary dataset | Combined Trusted Modeling Dataset |
| Training rows | 7,288 |
| Holdout rows | 1,822 |
| Random state | 42 |
| Status | usable with warning |

This is the final portfolio model candidate for the current phase. It is a
trusted-source listed-price model, not a complete production valuation system.

## Dataset Position

The final modeling package contains three separated datasets:

| Dataset | Rows | Role |
| --- | ---: | --- |
| Live Trusted Market Snapshot | 3,496 | Current-market trusted benchmark |
| External True Value Historical Dataset | 5,614 | Larger historical True Value benchmark |
| Combined Trusted Modeling Dataset | 9,110 | Main training and evaluation dataset with lineage features |

The model intentionally uses trusted/evaluated listing sources and excludes
self-listed marketplaces from the first modeling phase.

## Final Metrics

Primary holdout split:

| Metric | Value |
| --- | ---: |
| MAE | 47,389 INR |
| RMSE | 104,458 INR |
| MAPE | 9.88% |
| R2 | 0.897 |
| Underprediction rate | 50.93% |

Repeated-split validation:

| Metric | Value |
| --- | ---: |
| Validation runs | 7 |
| Mean MAPE | 10.33% |
| MAPE range | 9.88% to 10.73% |
| Mean MAE | 47,589 INR |
| Mean R2 | 0.906 |

Correct claim:

> Built a trusted-source used-car price intelligence pipeline and trained a
> 10%-class price model, reaching 9.88% MAPE on the primary combined split and
> 10.33% mean MAPE across repeated validation splits.

Incorrect claim:

> Guaranteed sub-10% MAPE across all splits.

## Key Predictive Signals

Permutation importance on the final holdout sample shows the model depends most
on market-relevant vehicle attributes:

| Rank | Feature | Type | Holdout MAPE increase after shuffling |
| ---: | --- | --- | ---: |
| 1 | `te_model` | target encoded | 20.97 pts |
| 2 | `age_km_interaction` | numeric | 12.10 pts |
| 3 | `model` | categorical | 6.02 pts |
| 4 | `model_year` | numeric | 3.70 pts |
| 5 | `vehicle_age_years` | numeric | 1.81 pts |
| 6 | `source_city` | categorical | 1.46 pts |
| 7 | `state` | categorical | 0.80 pts |
| 8 | `te_variant` | target encoded | 0.73 pts |
| 9 | `variant` | categorical | 0.66 pts |
| 10 | `city_brand` | categorical | 0.44 pts |

Interpretation note: these are predictive signals, not causal claims. Target
encoding is leakage-controlled through out-of-fold encoding inside the training
split.

## Segment Performance

| Segment | Rows | MAE | MAPE | Interpretation |
| --- | ---: | ---: | ---: | --- |
| External True Value Historical | 1,143 | 34,083 | 7.81% | Easiest and most stable segment |
| Live Trusted Market Snapshot | 679 | 69,787 | 13.37% | Harder because it is newer and more source-diverse |
| Common brand-model | 1,737 | 40,917 | 9.39% | Main reliable operating zone |
| Rare brand-model | 85 | 179,635 | 19.88% | Too sparse for consistent pricing |
| True Value Live | 476 | 40,579 | 12.68% | Moderate live-market difficulty |
| Spinny Live | 93 | 124,530 | 12.62% | Higher-value listings make absolute error larger |
| Mahindra First Choice Live | 110 | 149,896 | 16.97% | Needs more rows/source-specific calibration |

Price-band behavior:

| Price band | Rows | MAE | MAPE |
| --- | ---: | ---: | ---: |
| 0-2.5L | 342 | 26,457 | 15.24% |
| 2.5L-5L | 910 | 29,721 | 8.18% |
| 5L-7.5L | 348 | 45,993 | 7.62% |
| 7.5L-10L | 121 | 89,672 | 10.32% |
| 10L-20L | 90 | 197,750 | 14.10% |

The strongest operating zone is common, normal-market vehicles. Low-price and
higher-price bands have higher relative or absolute error.

## Intended Use

Appropriate uses:

- portfolio demonstration of a data-first ML platform
- used-car listed-price benchmarking
- market segment analysis by city, source, brand, model, fuel type, and year
- identifying likely underpriced or overpriced listings for review
- comparing model performance across trusted listing sources

Inappropriate uses:

- final automated vehicle valuation without human review
- loan, insurance, tax, or legal decisions
- guaranteed transaction-price prediction
- estimating vehicles outside the trusted-source data distribution
- claims of production-grade coverage for premium or rare vehicles

## Known Limitations

- The target is listed price, not final transaction price.
- Premium/high-price vehicles remain difficult.
- Rare brand-model rows have materially higher error.
- Live rows are harder than the historical external True Value rows.
- Source-specific pricing policies can create drift.
- Dataset size is 9,110 modeling rows, not 100,000 unique vehicles.
- The 103,719-row scrape file is an observation history and should not be used
  directly as a supervised modeling dataset.

## Monitoring Needed Before Production

Before treating this as a production model, add:

- source-level drift monitoring
- city-level drift monitoring
- premium-tail model or calibration layer
- rare brand-model fallback rules
- monthly retraining protocol
- holdout evaluation on new unseen live snapshots
- explainability report attached to every model release

## Final Position

This model is credible for a portfolio-grade trusted-source price intelligence
project. It is not a finished commercial pricing engine.

The honest final position is:

> A strong 10%-class listed-price model on trusted used-car listing data, with
> clear reliability on common normal-market vehicles and known weaknesses on
> premium and rare segments.
