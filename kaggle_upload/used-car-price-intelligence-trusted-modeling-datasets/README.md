# Used Car Price Intelligence: Trusted Modeling Datasets

This Kaggle dataset package supports the Used Car Price Intelligence Platform.

It contains three modeling datasets:

| File | Display Name | Rows | Purpose |
| --- | --- | ---: | --- |
| `live_trusted_market_snapshot_3496.csv` | Live Trusted Market Snapshot | 3,496 | Current trusted market snapshot from live source collection |
| `external_true_value_historical_dataset_5614.csv` | External True Value Historical Dataset | 5,614 | Processed historical True Value benchmark dataset |
| `combined_trusted_modeling_dataset_9110.csv` | Combined Trusted Modeling Dataset | 9,110 | Combined live + external experiment dataset with lineage columns |

Recommended usage:

- Use `live_trusted_market_snapshot_3496.csv` for current-market baseline modeling.
- Use `external_true_value_historical_dataset_5614.csv` as a clean historical trusted benchmark.
- Use `combined_trusted_modeling_dataset_9110.csv` for broad-coverage modeling with lineage-aware evaluation.

Important modeling notes:

- Target column: `listed_price_inr`
- Keep reviewed price-tail rows.
- Exclude ID, URL, capture metadata, registration, and fingerprint columns from training.
- Evaluate source, origin, rare brand-model, and price-tail segment metrics.
