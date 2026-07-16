# Spinny Incremental v7 Checkpoint

Date: 2026-06-27

Purpose: promote the successful Spinny Hyderabad incremental-detail probe into the curated collection ledger without double-counting the older Hyderabad Spinny run.

## Decision

The 80-row Spinny Hyderabad incremental run is now a first-class acquisition run.

It replaces this older curated source run:

```text
run_20260626_spinny_hyderabad_60_detail60_batch_20260626_repeat_snapshot_v3_same_scope_execute
```

It adds this source manifest:

```text
data/gold/acquisition_runs/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_manifest.json
```

## Result

| Metric | Value |
| --- | ---: |
| Previous 5k progress rows | 3,127 |
| New 5k progress rows | 3,147 |
| Net pricing-ready increase | 20 |
| Rows under 5k target | 1,853 |
| Quarantined rows | 0 |
| Unique listing keys | 3,147 |
| Source-city ledger rows | 46 |
| Listing-producing source runs | 45 |
| No-inventory source runs | 1 |

Source mix:

| Source | Pricing Ready | Source Runs | Notes |
| --- | ---: | ---: | --- |
| True Value | 2,317 | 24 | Current volume lane |
| Mahindra First Choice | 510 | 17 | Includes 1 retained no-inventory city |
| Spinny | 320 | 5 | Hyderabad promoted from 60 to 80 rows |

## Diff

Compared with `snapshot_20260626_5k_mfc_probe`:

| Diff Metric | Count |
| --- | ---: |
| Added listing keys | 27 |
| Removed listing keys | 7 |
| Still-active listing keys | 3,120 |
| Price changes | 53 |
| Km changes | 0 |

The added and removed counts are not expected to equal exactly +20 and -0 because the replacement run is a fresh Spinny snapshot. Some older Hyderabad listings were no longer visible, while more new listings entered the 80-row capture.

## Artifacts

```text
data/gold/collection_ledger/trusted_collection_v7_20260627_spinny_incremental_probe.json
data/gold/collection_ledger/trusted_collection_v7_20260627_spinny_incremental_probe.md
data/gold/listing_lifecycle/listing_lifecycle_v5_20260627_spinny_incremental_probe.json
data/gold/listing_lifecycle/listing_lifecycle_v5_20260627_spinny_incremental_probe.md
data/gold/snapshot_diffs/snapshot_20260627_spinny_incremental_probe_vs_5k_mfc_probe.json
data/gold/snapshot_diffs/snapshot_20260627_spinny_incremental_probe_vs_5k_mfc_probe.md
data/gold/snapshots/snapshot_20260627_spinny_incremental_probe_manifest.json
data/gold/snapshots/snapshot_20260627_spinny_incremental_probe_manifest.md
data/gold/snapshots/snapshot_20260627_spinny_incremental_probe_metadata.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_spinny_incremental_probe.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_spinny_incremental_probe.md
```

## Next Step

Completed next steps: [True Value Buffer v8 Checkpoint](45-true-value-buffer-v8-checkpoint.md), [Remaining 5k Gap Strategy](46-remaining-5k-gap-strategy.md), and [Final Spinny/MFC Try and Phase-Final Snapshot](47-final-spinny-mfc-try-and-phase-final-snapshot.md).

The current active step is no longer acquisition expansion; it is dataset packaging, EDA, and baseline modeling from the v9 final-for-phase snapshot.
