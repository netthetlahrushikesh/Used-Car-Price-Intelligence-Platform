# True Value Buffer v8 Checkpoint

Date: 2026-06-27

Purpose: add a small, controlled True Value buffer after the Spinny incremental checkpoint without letting True Value overrun the source allocation.

## Decision

Use five new True Value cities, capped at 40 rows per city:

```text
Mysuru
Mangaluru
Madurai
Vijayawada
Rajkot
```

This keeps the maximum possible addition at 200 rows, close to the 183-row True Value allocation gap that existed before the run.

## Batch Result

Batch:

```text
batch_20260627_true_value_5k_buffer_execute
```

| City | Pricing Ready | Quarantined | Required | High Value | Source Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mysuru | 12 | 0 | 100% | 100% | 31 |
| Mangaluru | 28 | 0 | 100% | 100% | 53 |
| Madurai | 32 | 0 | 100% | 100% | 62 |
| Vijayawada | 34 | 0 | 100% | 100% | 44 |
| Rajkot | 25 | 0 | 100% | 100% | 49 |
| Total | 131 | 0 | 100% | 100% | 239 |

## Snapshot Result

| Metric | Previous v7 | New v8 |
| --- | ---: | ---: |
| Pricing-ready rows | 3,147 | 3,278 |
| Unique listing keys | 3,147 | 3,278 |
| Quarantined rows | 0 | 0 |
| Ledger source-city rows | 46 | 51 |
| Listing-producing source runs | 45 | 50 |
| Rows under 5k target | 1,853 | 1,722 |

Source mix after v8:

| Source | Pricing Ready | Source Runs | Notes |
| --- | ---: | ---: | --- |
| True Value | 2,448 | 29 | Near 2,500-row allocation |
| Mahindra First Choice | 510 | 17 | Includes 1 retained no-inventory city |
| Spinny | 320 | 5 | Uses incremental manifest path for Hyderabad |

## Diff

Compared with `snapshot_20260627_spinny_incremental_probe`:

| Diff Metric | Count |
| --- | ---: |
| Added listing keys | 131 |
| Removed listing keys | 0 |
| Still-active listing keys | 3,147 |
| Price changes | 0 |
| Km changes | 0 |

This is the expected shape for new-city additive coverage: no source-city replacement occurred, so there are no removed listings.

## Artifacts

```text
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_dry_run_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_dry_run_batch_summary.md
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_execute_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_execute_batch_summary.md
data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.json
data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.md
data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.json
data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.md
data/gold/snapshot_diffs/snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe.json
data/gold/snapshot_diffs/snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe.md
data/gold/snapshots/snapshot_20260627_true_value_buffer_metadata.json
data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.json
data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.md
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_true_value_buffer.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_true_value_buffer.md
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.json
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.md
```

## Next Step

True Value is now only 52 rows below its 2,500-row allocation. The generated strategy confirms `balanced_gap_close_required`: do not close the full remaining 1,722-row 5k gap by blindly adding more True Value.

Completed next: [Remaining 5k Gap Strategy](46-remaining-5k-gap-strategy.md), followed by [Final Spinny/MFC Try and Phase-Final Snapshot](47-final-spinny-mfc-try-and-phase-final-snapshot.md).
