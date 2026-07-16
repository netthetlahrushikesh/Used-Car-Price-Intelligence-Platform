# Baseline Modeling Plan

Date: 2026-06-28

## Objective

Move from EDA into a controlled baseline modeling phase. The goal is not to build the final best model immediately. The goal is to train comparable first-pass models, expose data/source bias, and create a defensible benchmark for later improvements.

## Current Data Readiness

The final EDA notebook reports `ready_with_warnings`.

Readiness interpretation:

- Combined Trusted Modeling Dataset has 9,110 rows.
- Live Trusted Market Snapshot has 3,496 rows.
- External True Value Historical Dataset has 5,614 rows.
- Combined duplicate listing keys: 0.
- Required modeling columns: complete.
- Invalid non-price range checks: 0.
- Reviewed price-tail rows: kept as genuine listings.
- Rare brand-model groups: warning only, not a blocker.

## Modeling Experiments

Train three comparable baseline models:

| Experiment | Dataset | Purpose |
| --- | --- | --- |
| Experiment ID | Display Name | Dataset | Purpose |
| --- | --- | --- | --- |
| `live_trusted_market_baseline` | Live Trusted Market Baseline | Live Trusted Market Snapshot | Best view of current trusted market snapshot |
| `external_true_value_historical_baseline` | External True Value Historical Baseline | External True Value Historical Dataset | Historical trusted source benchmark |
| `combined_trusted_lineage_baseline` | Combined Trusted Lineage Baseline | Combined Trusted Modeling Dataset | Larger coverage with explicit source/freshness lineage |

## Target

Target column:

- `listed_price_inr`

Primary modeling target:

- Start with raw `listed_price_inr`.
- Add log-price modeling later only after the raw target baseline is documented.

## Feature Plan

Core features:

- `source`
- `city`
- `state`
- `brand`
- `model`
- `variant`
- `brand_model`
- `model_year`
- `vehicle_age_years`
- `fuel_type`
- `transmission`
- `ownership`
- `km_driven`

Combined-only lineage features:

- `dataset_origin`
- `data_freshness`
- `market_snapshot_year`

Use lineage features only in the combined model. Do not add them to live-only or external-only models.

## Leakage And Excluded Columns

Exclude:

- `listing_key`
- `source_listing_id`
- `listing_url`
- `capture_date`
- `captured_at`
- `vehicle_fingerprint`
- `registration_code`
- `is_available`
- `original_listing_key`
- `original_baseline_split`

Reason: these columns identify the listing, source capture mechanics, or post-acquisition metadata rather than reusable vehicle-price behavior.

## Preprocessing

Numeric features:

- median imputation
- no scaling needed for tree baselines

Categorical features:

- fill missing values with `unknown`
- one-hot encode
- ignore unknown categories at inference

Rare categories:

- keep them in training
- evaluate common vs rare brand-model rows separately
- do not collapse rare categories in baseline v1 unless one-hot dimensionality becomes a practical issue

## Split Strategy

Use a consistent random train/test split for baseline v1:

- test size: 20%
- random seed: 42

Stratification:

- Use binned price stratification when possible.
- If stratification fails because a dataset has sparse bins, fall back to a normal random split.

Future split improvements:

- city-aware validation
- source-aware validation
- time/freshness-aware validation if repeated snapshots are available

## Baseline Algorithm

Use a simple, strong, production-friendly baseline:

- `RandomForestRegressor`

Baseline parameters:

- `n_estimators=300`
- `random_state=42`
- `n_jobs=-1`
- `min_samples_leaf=2`

Reason:

- Handles non-linear relationships.
- Works with mixed tabular data after one-hot encoding.
- Easy to explain for a first benchmark.
- Does not require external dependencies beyond scikit-learn.

Later candidates:

- `HistGradientBoostingRegressor`
- XGBoost
- LightGBM
- CatBoost
- log-price target model

## Metrics

Overall metrics:

- MAE
- RMSE
- MAPE
- R2
- median absolute error

Segment metrics:

- `dataset_origin`
- `source`
- `city`
- `brand_model`
- `fuel_type`
- `transmission`
- `model_year`
- common vs rare brand-model group

Why segment metrics matter:

- A combined model can look good overall while failing specific cities, rare models, luxury cars, or old cars.

## Model Selection Rules

Do not choose the final model only by lowest overall MAE.

Compare:

- overall error
- current-market relevance
- source bias
- rare-model error
- premium-car error
- old-car error
- explainability

Expected interpretation:

- Live-only may best represent current pricing.
- External-only may be cleaner but older.
- Combined may improve coverage but can inherit historical/source bias.

## Required Outputs

The modeling notebook should save:

- `modeling_experiment_metrics.csv`
- `segment_metrics.csv`
- `prediction_samples.csv`
- `modeling_decision_summary.csv`
- trained model artifacts for each experiment

## Definition Of Done

Baseline modeling phase is done when:

- all three experiments train successfully
- all overall metrics are saved
- all segment metrics are saved
- prediction samples are saved
- model decision summary explains which baseline should be improved next
- notebook runs end-to-end without manual edits

## Next Execution Step

Create and run `notebooks/used_car_price_intelligence_baseline_modeling.ipynb` using this plan.
