# Final Spinny/MFC Try and Phase-Final Snapshot

Date: 2026-06-27

Purpose: make one final balanced attempt with Spinny and Mahindra First Choice, keep True Value unchanged, fix data-quality blind spots found during review, and close the current acquisition phase without chasing the full 5,000 rows.

## Decision

Stop the current collection phase at `snapshot_20260627_final_spinny_mfc_try`.

The project has enough trusted, pricing-ready rows to move into dataset packaging, EDA, baseline modeling, and reporting. The remaining 1,508-row gap to 5,000 should not be filled by adding more True Value rows because True Value is already near its intended allocation.

## Final Attempt Results

Spinny final attempt replaced the previous five hub runs with corrected incremental-detail runs:

| City | Pricing Ready | Quarantined |
| --- | ---: | ---: |
| Bengaluru | 95 | 0 |
| Chennai | 100 | 0 |
| Delhi NCR | 100 | 0 |
| Hyderabad | 100 | 0 |
| Mumbai | 87 | 0 |
| Total | 482 | 0 |

Mahindra First Choice final attempt added 12 city probes:

| Result | Count |
| --- | ---: |
| Pricing-ready rows added | 52 |
| Quarantined rows | 0 |
| No-inventory cities | 3 |

No True Value expansion was run in this final attempt.

## Snapshot Result

| Metric | v8 True Value Buffer | v9 Final For Phase |
| --- | ---: | ---: |
| Pricing-ready rows | 3,278 | 3,492 |
| Unique listing keys | 3,278 | 3,492 |
| Quarantined rows | 0 | 0 |
| Ledger source-city rows | 51 | 63 |
| Listing-producing source runs | 50 | 59 |
| No-inventory source runs | 1 | 4 |
| Rows under 5k target | 1,722 | 1,508 |

Source mix after v9:

| Source | Pricing Ready | Source Runs | Notes |
| --- | ---: | ---: | --- |
| True Value | 2,448 | 29 | Unchanged in final attempt |
| Mahindra First Choice | 562 | 29 | Includes 4 no-inventory source-city runs |
| Spinny | 482 | 5 | Corrected final incremental hub runs |

## Data-Quality Fixes

Three blind spots were fixed before finalizing:

1. Spinny card extraction stored discount/price text in `variant` for many rows. The adapter now rejects price-like variant text and recovers the variant from the Spinny listing URL slug.
2. Spinny regenerated silver rows were using the default `Hyderabad/Telangana` context for non-Hyderabad hubs. `run-fixture` now accepts explicit `--city` and `--state`, and all five Spinny final silver outputs were regenerated.
3. Engine-size-only title suffixes such as `Wagon-R-1-0` no longer survive as standalone variants. The normalized model remains `Wagon R`.

Validation check after regeneration:

```text
Spinny canonical rows: 482
Spinny city split: Bengaluru 95, Chennai 100, Delhi NCR 100, Hyderabad 100, Mumbai 87
Price-like Spinny canonical variants: 0
Quarantined rows: 0
```

## Diff

Compared with `snapshot_20260627_true_value_buffer`:

| Diff Metric | Count |
| --- | ---: |
| Previous unique listing keys | 3,278 |
| Current unique listing keys | 3,492 |
| Added listing keys | 235 |
| Removed listing keys | 21 |
| Still-active listing keys | 3,257 |
| Price changes | 221 |
| Km changes | 3 |

The Spinny price changes are expected because the five hub runs were refreshed from current public listing cards and detail payloads. Removed Spinny rows mean not observed in the selected current final run, not automatically sold.

## Artifacts

```text
data/gold/collection_ledger/trusted_collection_v9_20260627_final_spinny_mfc_try.json
data/gold/collection_ledger/trusted_collection_v9_20260627_final_spinny_mfc_try.md
data/gold/listing_lifecycle/listing_lifecycle_v7_20260627_final_spinny_mfc_try.json
data/gold/listing_lifecycle/listing_lifecycle_v7_20260627_final_spinny_mfc_try.md
data/gold/snapshot_diffs/snapshot_20260627_final_spinny_mfc_try_vs_true_value_buffer.json
data/gold/snapshot_diffs/snapshot_20260627_final_spinny_mfc_try_vs_true_value_buffer.md
data/gold/snapshots/snapshot_20260627_final_spinny_mfc_try_metadata.json
data/gold/snapshots/snapshot_20260627_final_spinny_mfc_try_manifest.json
data/gold/snapshots/snapshot_20260627_final_spinny_mfc_try_manifest.md
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.md
```

## Next Step

Move to the final dataset work for this phase:

1. Package the curated pricing-ready rows into analysis-ready data files.
2. Produce EDA tables and plots for source, city, brand, model, year, fuel, ownership, transmission, km, and price.
3. Build a simple baseline pricing model before adding any UI.
4. Write the project narrative for documentation, Medium, LinkedIn, and YouTube.
