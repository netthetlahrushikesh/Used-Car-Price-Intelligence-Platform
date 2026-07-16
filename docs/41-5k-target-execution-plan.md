# 5k Target Execution Plan

Date: 2026-06-26

Purpose: move from the completed 2,500-row target to the first 5,000-row trusted snapshot without letting one easy source dominate the dataset.

Status: historical execution runbook. The active phase-final checkpoint is now [Final Spinny/MFC Try and Phase-Final Snapshot](47-final-spinny-mfc-try-and-phase-final-snapshot.md): `snapshot_20260627_final_spinny_mfc_try`, 3,492 pricing-ready rows, 0 quarantine.

## Current Anchor

Use the completed target-met snapshot as the anchor for this phase.

| Metric | Count |
| --- | ---: |
| Anchor snapshot | `snapshot_20260626_2500_target_met` |
| Pricing-ready rows | 2,796 |
| Quarantined rows | 0 |
| Source-city runs | 34 |
| Unique listing keys | 2,796 |
| 5k target gap | 2,204 |

Source split:

| Source | Current Rows | 5k Target Allocation | Gap To Allocation | Decision |
| --- | ---: | ---: | ---: | --- |
| True Value | 2,317 | 2,500 | 183 | Near target; use as buffer, not first default. |
| Mahindra First Choice | 179 | 1,500 | 1,321 | Underrepresented; run inventory probe first. |
| Spinny | 300 | 1,000 | 700 | Quality anchor; expand after incremental detail path. |

## Current 5k Progress

The latest 5k progress checkpoint now includes the MFC probe, the promoted Spinny incremental-detail Hyderabad replacement, and the controlled True Value buffer.

| Metric | Count |
| --- | ---: |
| Progress snapshot | `snapshot_20260627_true_value_buffer` |
| Pricing-ready rows | 3,278 |
| Quarantined rows | 0 |
| Ledger source-city rows | 51 |
| Listing-producing source runs | 50 |
| Unique listing keys | 3,278 |
| Remaining 5k gap | 1,722 |

Updated source split:

| Source | Current Rows | 5k Target Allocation | Gap To Allocation | Decision |
| --- | ---: | ---: | ---: | --- |
| True Value | 2,448 | 2,500 | 52 | Near allocation; pause large extra True Value batches. |
| Mahindra First Choice | 510 | 1,500 | 990 | Useful but inventory-constrained; do not rely on it alone. |
| Spinny | 320 | 1,000 | 680 | Incremental manifest path is working; use it for targeted expansion. |

Final-for-phase update:

| Metric | Count |
| --- | ---: |
| Final snapshot | `snapshot_20260627_final_spinny_mfc_try` |
| Pricing-ready rows | 3,492 |
| Quarantined rows | 0 |
| Unique listing keys | 3,492 |
| Remaining 5k gap | 1,508 |

Final source split:

| Source | Rows |
| --- | ---: |
| True Value | 2,448 |
| Mahindra First Choice | 562 |
| Spinny | 482 |

## Decision

Do not start the 5k phase by simply adding more True Value rows.

True Value proved it can add volume quickly, and the v8 checkpoint was still heavily True Value:

```text
2,448 / 3,278 = 74.68%
```

That is acceptable for proving the 2,500-row milestone, but it is not ideal for a market-price intelligence dataset. The next phase should first test whether MFC can add more multi-brand rows, then improve Spinny throughput, and only then use True Value as the final gap-close buffer.

## Execution Sequence

### Phase A: MFC 5k Capacity Probe

Status in `config/acquisition_batches.yml`:

```text
mfc_5k_probe
```

Probe shape:

- 12 additional Mahindra First Choice cities.
- `max_records=80` per city.
- `max_pages=4` per city.
- `min_records=10`, with source-aware low-inventory pass behavior.
- no detail pages, because MFC listing rows already expose enough structured pricing-ready data.

Dry run first:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --status mfc_5k_probe --capture-date 2026-06-26 --batch-run-id batch_20260626_mfc_5k_probe_dry_run --json
```

Dry-run result:

| Metric | Value |
| --- | --- |
| Batch run id | `batch_20260626_mfc_5k_probe_dry_run` |
| Status | `planned` |
| Jobs planned | 12 |
| Jobs executed | 0 |

Dry-run artifacts:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5k_probe_dry_run_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5k_probe_dry_run_batch_summary.md
```

Execute the probe only after the dry-run manifest is clean:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --status mfc_5k_probe --capture-date 2026-06-26 --batch-run-id batch_20260626_mfc_5k_probe_execute --skip-passed --execute --json
```

Operational note: if one MFC city fails because a city URL or page structure is bad, rerun the remaining cities by `--batch-id` instead of repeatedly executing the full probe. The batch runner intentionally stops on the first failed job so we can inspect the failure before continuing.

Execution result:

| Metric | Count |
| --- | ---: |
| Probe jobs planned | 12 |
| Inventory-producing probe cities | 11 |
| No-inventory probe cities | 1 |
| Added pricing-ready rows | 331 |
| Added quarantined rows | 0 |

MFC probe city result:

| City | Pricing Ready | Source Total | Result |
| --- | ---: | ---: | --- |
| Kolkata | 80 | 86 | strong |
| Indore | 80 | 100 | strong |
| Pune | 66 | 66 | useful |
| Nagpur | 37 | 37 | useful |
| Coimbatore | 35 | 35 | useful |
| Jaipur | 10 | 10 | low inventory |
| Kochi | 9 | 9 | low inventory |
| Lucknow | 4 | 4 | low inventory |
| Chandigarh | 4 | 4 | low inventory |
| Ahmedabad | 3 | 3 | low inventory |
| Surat | 3 | 3 | low inventory |
| Vadodara | 0 | 0 | no inventory |

Important pipeline change:

- The batch runner now supports `allow_zero_inventory` for explicit capacity-probe jobs.
- A zero-inventory city is retained in the collection ledger as `no_inventory`.
- Lifecycle and model inputs still skip no-inventory rows because there are no silver listing records.

### Phase B: Spinny Incremental Detail Plan

Spinny full-detail collection is high quality but slow:

| City | Rows | Runtime Seconds |
| --- | ---: | ---: |
| Hyderabad | 60 | 290.400 |
| Bengaluru | 60 | 655.367 |
| Delhi NCR | 60 | 602.207 |
| Mumbai | 60 | 565.524 |
| Chennai | 60 | 453.608 |

This means broad Spinny growth through the old full-detail path would likely take hours. The incremental path now exists and should be used for targeted Spinny expansion:

- capture listing cards first and enqueue detail pages separately,
- cache successful detail-page payloads by listing URL,
- enrich only rows that need detail fields for high-value completeness,
- write an acquisition-run manifest before a Spinny run enters the curated ledger.

Keep Spinny as the quality anchor, not the emergency volume lane. Use the current manifest-backed path for small high-quality expansions.

### Phase C: True Value Buffer Gap-Close

Status: completed as a controlled five-city buffer.

Result:

| City | Pricing Ready | Source Total |
| --- | ---: | ---: |
| Mysuru | 12 | 31 |
| Mangaluru | 28 | 53 |
| Madurai | 32 | 62 |
| Vijayawada | 34 | 44 |
| Rajkot | 25 | 49 |

The buffer added 131 pricing-ready rows with 0 quarantined rows and moved True Value to 2,448 rows, just 52 rows below its 2,500-row allocation.

Rules:

- Prefer new cities over rerunning the same city-depth pair.
- If increasing depth for a city already in the snapshot, rebuild the final ledger with the replacement deeper run instead of double-counting both old and new runs.
- Keep required and high-value completeness at 100%.
- Keep quarantine rate at 0%, or stop and fix parser/adapter gaps before continuing.
- Avoid large additional True Value batches; the generated strategy reserves True Value for a final capped 52-row buffer.

### Phase D: Rebuild Gold Snapshot Artifacts

After the next expansion batch passes, rebuild artifacts in this order:

1. Collection ledger.
2. Listing lifecycle index.
3. Snapshot diff against the previous lifecycle checkpoint.
4. Snapshot manifest.
5. Project notebook entry.

Ledger command shape:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli collection-ledger --collection-id trusted_collection_v8_20260627_true_value_buffer --source-manifest <all-source-manifests-from-trusted_collection_v7> --batch-manifest data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5k_probe_execute_batch_manifest.json --batch-manifest data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_execute_batch_manifest.json --output-json data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.json --output-md data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.md --json
```

Note: the v8 ledger extends v7 with the True Value buffer batch. It still includes the MFC probe batch manifest so the Vadodara `no_inventory` row stays visible in the ledger.

Lifecycle command shape:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli listing-lifecycle --lifecycle-id listing_lifecycle_v6_20260627_true_value_buffer --collection-ledger data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.json --output-json data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.json --output-md data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.md
```

Diff command shape:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli snapshot-diff --snapshot-id snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe --previous-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v5_20260627_spinny_incremental_probe.json --current-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.json --snapshot-date 2026-06-27 --output-json data/gold/snapshot_diffs/snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe.json --output-md data/gold/snapshot_diffs/snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe.md
```

Progress snapshot manifest command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli snapshot-manifest --snapshot-id snapshot_20260627_true_value_buffer --snapshot-date 2026-06-27 --collection-ledger data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.json --lifecycle-index data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.json --snapshot-diff data/gold/snapshot_diffs/snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe.json --status in_progress --target-pricing-ready 5000 --previous-snapshot-id snapshot_20260627_spinny_incremental_probe --previous-lifecycle-id listing_lifecycle_v5_20260627_spinny_incremental_probe --extra-metadata data/gold/snapshots/snapshot_20260627_true_value_buffer_metadata.json --output-json data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.json --output-md data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.md
```

Progress snapshot manifest outputs:

```text
data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.json
data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.md
data/gold/snapshots/snapshot_20260627_true_value_buffer_metadata.json
```

## Stop Conditions

Stop the 5k expansion and fix the pipeline if any of these happen:

- required completeness drops below 100%,
- pricing-ready rows are quarantined due to parser gaps,
- a source produces a new field format that changes canonical parsing,
- duplicate listing groups rise enough to distort row counts,
- MFC probe returns too little city inventory to justify the 1,500-row allocation,
- Spinny expansion runtime makes the 5k target operationally impractical.

## Success Criteria

The 5k phase is successful when:

- the final snapshot has at least 5,000 pricing-ready rows,
- source mix is materially less dependent on True Value than the 2,500-row snapshot,
- quarantine remains at or near 0,
- lifecycle unique listing count is explainable,
- added/removed/still-active movement is interpreted with source-scope context,
- every run can be reproduced from batch manifests and docs.

## Projection Artifact

The current 100k target projection is generated from the 3,492-row final-for-phase checkpoint:

```powershell
$env:PYTHONPATH='src'; .venv\Scripts\python -m used_car_price_intelligence.cli scale-projection --target-id target_100k_trusted_observations_v0 --target-observations 100000 --current-snapshot-manifest data/gold/snapshots/snapshot_20260627_final_spinny_mfc_try_manifest.json --recommended-rows-per-snapshot 5000 --output-json data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.json --output-md data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.md
```

Outputs:

```text
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.md
```

Historical v8 projection artifact:

```text
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_true_value_buffer.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_true_value_buffer.md
```

Projection result:

| Scenario | Rows Per Future Snapshot | Future Snapshots Needed | Total Snapshots Including Anchor |
| --- | ---: | ---: | ---: |
| Current scope | 909 | 107 | 108 |
| Small scale | 2,500 | 39 | 40 |
| Recommended | 5,000 | 20 | 21 |
| Stretch | 10,000 | 10 | 11 |

## Immediate Next Action

The MFC probe, Spinny incremental manifest promotion, controlled True Value buffer, final Spinny attempt, and final MFC capacity try are complete. True Value is near its allocation, so the remaining gap should not be closed by blindly adding more True Value.

The balanced strategy is now generated at:

```text
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.json
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.md
```

Completed next: built the final Spinny/MFC attempt and rebuilt v9 ledger, lifecycle, diff, and snapshot artifacts.

Next: package the final trusted dataset for EDA and baseline modeling.
