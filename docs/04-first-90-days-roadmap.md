# First 90 Days Roadmap

This roadmap starts with data. UI and ML come after the dataset is reliable.

## Phase 0: Foundation

Goal: create the project boundary and data operating model.

Deliverables:

- Separate Git repository.
- README.
- Data strategy.
- Canonical listing schema draft.
- Storage architecture.
- Technology decisions.
- First source evaluation checklist.

Exit criteria:

- We know what data we collect.
- We know what data we refuse to collect.
- We know how raw data is stored.
- We know what makes a record valid.

## Phase 1: Single-Source Data MVP

Goal: collect and validate data from one allowed source and one city.

Deliverables:

- Source evaluation document.
- Acquisition command.
- Immutable raw snapshot.
- Parser module.
- Pydantic record model.
- Pandera silver table schema.
- Parser tests.
- Data quality report.
- Processed Parquet output.

Exit criteria:

- Another developer can run the same command and produce the same layer outputs.
- Invalid records are quarantined with reasons.
- Processed data can be queried with DuckDB.

## Phase 2: Market Profile

Goal: convert clean data into useful intelligence.

Deliverables:

- Market summary by city.
- Brand/model/year price distributions.
- Kilometer and age depreciation analysis.
- Comparable listing search logic.
- Basic outlier detection.

Exit criteria:

- We can explain whether a listing looks cheap, fair, or expensive using observed comparable data.

## Phase 3: Multi-Source Expansion

Goal: make the dataset defensible.

Deliverables:

- Second source connector.
- Cross-source deduplication.
- Source quality scoring.
- Freshness dashboard.
- Sold/removed listing tracking if available.

Exit criteria:

- The platform is not dependent on a single website.
- Source drift is visible.

## Phase 4: Price Model

Goal: build a baseline valuation model.

Deliverables:

- Feature table.
- Train/test split by time.
- Baseline model.
- MAE and MAPE metrics.
- Prediction intervals.
- Model card.

Exit criteria:

- The model beats naive baselines.
- Predictions include uncertainty.
- Feature importance and limitations are documented.

## Phase 5: Product MVP

Goal: expose intelligence through a usable interface.

Deliverables:

- Streamlit or lightweight web dashboard.
- Fair price estimator.
- Comparable listings panel.
- Market overview page.
- Data freshness indicator.

Exit criteria:

- A user can enter a car profile and get an evidence-backed price range.

## Immediate Next Step

Before writing the first scraper, create the source evaluation for the first target source and city.

Historical comparison target:

```text
source: Cars24
market: Hyderabad
reason: matches the old notebook context, so we can compare new output against historical expectations
```

Important: this is not automatically approved for production scraping. The current Cars24 terms require prior written permission for automated access and restrict scraping, data mining, indexing, or extracting website content for commercial purposes. Treat Cars24 as a historical benchmark or partnership target unless permission is obtained.

Recommended production-safe first target:

```text
source: manually curated seed dataset or permissioned dealer feed
market: Hyderabad
reason: lets us build schema, validation, storage, and analytics without depending on a legally blocked scraper
```
