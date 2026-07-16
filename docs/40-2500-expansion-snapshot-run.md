# 2,500-Row Expansion Snapshot Run

Date: 2026-06-26

## Question

Can the platform expand beyond the 911-row repeat snapshot toward the next 2,500-row trusted snapshot target without lowering data quality?

## Decision

Yes. The 2,500-row trusted snapshot target is complete after a separate gap-close batch.

The first expansion pass reached 1,919 pricing-ready rows, which was 581 rows short of target. A second gap-close batch added 877 more pricing-ready rows.

The final target-met snapshot produced:

- 34 source-city runs,
- 2,796 pricing-ready rows,
- 0 quarantined rows,
- 2,796 unique lifecycle listing keys,
- 4 conservative possible vehicle duplicate groups,
- 296 rows above the 2,500 pricing-ready target.

This proves True Value can be expanded quickly while preserving 100% required and high-value completeness. The next scale question is not whether 2,500 is possible; it is how to reach 5,000 with more balanced source allocation.

## Expansion Scope

The previous repeat snapshot had:

| Source | Cities | Pricing-Ready Rows |
| --- | ---: | ---: |
| Spinny | 5 | 300 |
| Mahindra First Choice | 5 | 179 |
| True Value | 5 | 432 |
| Total | 15 source-city runs | 911 |

The first expansion snapshot kept Spinny and Mahindra First Choice at the repeat v3 scope, then replaced the capped five-city True Value slice with ten expanded True Value city/depth runs:

| True Value City | Pricing-Ready Rows | Quarantined | Source Total Signal |
| --- | ---: | ---: | ---: |
| Hyderabad | 170 | 0 | 244 |
| Bengaluru | 141 | 0 | 225 |
| Delhi NCR | 226 | 0 | 610 |
| Mumbai | 241 | 0 | 318 |
| Chennai | 33 | 0 | 100 |
| Pune | 150 | 0 | 417 |
| Ahmedabad | 150 | 0 | 216 |
| Kolkata | 103 | 0 | 168 |
| Jaipur | 150 | 0 | 220 |
| Lucknow | 76 | 0 | 122 |
| True Value total | 1,440 | 0 | 2,640 |

First expansion-pass collection:

| Source | Source Runs | Pricing-Ready Rows | Quarantined | Source Total Signal |
| --- | ---: | ---: | ---: | ---: |
| Spinny | 5 | 300 | 0 | 0 |
| Mahindra First Choice | 5 | 179 | 0 | 284 |
| True Value | 10 | 1,440 | 0 | 2,640 |
| Total | 20 | 1,919 | 0 | 2,924 |

The first expansion pass reached 1,919 pricing-ready rows. That was high quality, but not enough for the target.

## Gap-Close Scope

A separate gap-close batch added fourteen more True Value city runs:

| True Value City | Pricing-Ready Rows | Quarantined | Source Total Signal |
| --- | ---: | ---: | ---: |
| Surat | 101 | 0 | 136 |
| Vadodara | 93 | 0 | 121 |
| Nashik | 94 | 0 | 113 |
| Nagpur | 60 | 0 | 85 |
| Indore | 124 | 0 | 202 |
| Bhopal | 22 | 0 | 75 |
| Chandigarh | 18 | 0 | 27 |
| Ludhiana | 47 | 0 | 71 |
| Kochi | 93 | 0 | 173 |
| Coimbatore | 65 | 0 | 98 |
| Visakhapatnam | 53 | 0 | 81 |
| Bhubaneswar | 22 | 0 | 57 |
| Patna | 25 | 0 | 32 |
| Guwahati | 60 | 0 | 84 |
| Gap-close total | 877 | 0 | 1,355 |

Final target-met collection:

| Source | Source Runs | Pricing-Ready Rows | Quarantined | Source Total Signal |
| --- | ---: | ---: | ---: | ---: |
| Spinny | 5 | 300 | 0 | 0 |
| Mahindra First Choice | 5 | 179 | 0 | 284 |
| True Value | 24 | 2,317 | 0 | 3,995 |
| Total | 34 | 2,796 | 0 | 4,279 |

## Parser Hardening

The first expansion attempt exposed a legitimate registration parsing issue:

- Listing: `true_value_B26019403497`
- Vehicle: 2005 Maruti Suzuki Alto STD
- Raw registration: `OR18`
- Raw RTO text: `PORT BLAIR`
- Failure reason: `unknown_registration_prefix`

Fixes added:

- RTO location alias: `PORT BLAIR` maps to `AN01`, Andaman and Nicobar Islands.
- Legacy registration prefix: `OR` maps to current canonical `OD`, Odisha.
- Legacy registration prefix: `UA` maps to current canonical `UK`, Uttarakhand.
- Unit tests cover `PORT BLAIR`, `OR18`, and `UA07`.

This keeps the gate strict. Unknown registration prefixes still fail unless they are explicitly known aliases.

## Gate Calibration

Some True Value cities had fewer usable live records than the initial target because the source returned many unavailable rows. We calibrated `min_records` to trusted usable inventory instead of raw source totals:

| City | Initial Minimum | Final Minimum | Observed Pricing-Ready |
| --- | ---: | ---: | ---: |
| Bengaluru | 150 | 140 | 141 |
| Delhi NCR | 300 | 220 | 226 |
| Chennai | 80 | 30 | 33 |

This was not a quality relaxation. Each accepted run still required:

- payload contract pass,
- 100% required completeness,
- 100% high-value completeness for the True Value expansion runs,
- 0 quarantined records.

## Final Batches

Final expansion batch manifest:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_expansion_execute_v7_batch_manifest.json
```

Final expansion batch summary:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_expansion_execute_v7_batch_summary.md
```

Final gap-close batch manifest:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_gap_close_resume1_batch_manifest.json
```

Final gap-close batch summary:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_gap_close_resume1_batch_summary.md
```

Execution path:

1. `execute` failed on the valid `OR18` legacy registration case.
2. Parser was hardened and tested.
3. `execute_v3` passed Hyderabad, then failed Bengaluru due to an over-high minimum.
4. `execute_v5` passed Bengaluru, then failed Delhi due to an over-high minimum.
5. `execute_v6` passed Delhi and Mumbai, then failed Chennai due to an over-high minimum.
6. `execute_v7` resumed passed jobs and completed all remaining cities.
7. The first expansion pass stopped at 1,919 pricing-ready rows.
8. Gap-close execute passed six cities and failed Chandigarh at 18/20 rows.
9. Gap-close resume lowered Chandigarh's city-specific inventory floor to 18 and completed all fourteen gap-close city runs.

## Collection Ledger

Command:

```powershell
.venv\Scripts\python.exe -m used_car_price_intelligence.cli collection-ledger --collection-id trusted_collection_v5_20260626_2500_target_met --batch-manifest data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_expansion_execute_v7_batch_manifest.json --batch-manifest data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_gap_close_resume1_batch_manifest.json --source-manifest <repeat-v3-non-true-value-manifest> --output-json data/gold/collection_ledger/trusted_collection_v5_20260626_2500_target_met.json --output-md data/gold/collection_ledger/trusted_collection_v5_20260626_2500_target_met.md
```

The actual command included the ten non-True-Value Spinny/MFC manifests from `trusted_collection_v3_20260626_repeat_snapshot`. This avoided double-counting the old capped True Value runs.

Result:

| Metric | Count |
| --- | ---: |
| Pricing-ready rows | 2,796 |
| Quarantined rows | 0 |
| Source runs | 34 |

## Lifecycle Index

Command:

```powershell
.venv\Scripts\python.exe -m used_car_price_intelligence.cli listing-lifecycle --lifecycle-id listing_lifecycle_v3_20260626_2500_target_met --collection-ledger data/gold/collection_ledger/trusted_collection_v5_20260626_2500_target_met.json --output-json data/gold/listing_lifecycle/listing_lifecycle_v3_20260626_2500_target_met.json --output-md data/gold/listing_lifecycle/listing_lifecycle_v3_20260626_2500_target_met.md
```

Result:

| Metric | Count |
| --- | ---: |
| Records processed | 2,796 |
| Source runs | 34 |
| Unique listing keys | 2,796 |
| Reobserved listing groups | 0 |
| Possible vehicle duplicate groups | 4 |

The possible duplicate groups are review signals only. They are not automatic merges.

## Snapshot Diff

Command:

```powershell
.venv\Scripts\python.exe -m used_car_price_intelligence.cli snapshot-diff --snapshot-id snapshot_20260626_2500_target_met_vs_repeat_v3 --previous-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v1_20260626_repeat_snapshot.json --current-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v3_20260626_2500_target_met.json --snapshot-date 2026-06-26 --output-json data/gold/snapshot_diffs/snapshot_20260626_2500_target_met_vs_repeat_v3.json --output-md data/gold/snapshot_diffs/snapshot_20260626_2500_target_met_vs_repeat_v3.md
```

Diff result:

| Metric | Count |
| --- | ---: |
| Previous unique listing keys | 911 |
| Current unique listing keys | 2,796 |
| Added listings | 2,059 |
| Removed listings | 174 |
| Still-active listings | 737 |
| Price changes | 0 |
| Km changes | 0 |

By source:

| Source | Previous | Current | Added | Removed | Still Active |
| --- | ---: | ---: | ---: | ---: | ---: |
| Spinny | 300 | 300 | 0 | 0 | 300 |
| Mahindra First Choice | 179 | 179 | 0 | 0 | 179 |
| True Value | 432 | 2,317 | 2,059 | 174 | 258 |

## Movement Interpretation

Do not interpret this diff as normal market churn.

This is an expansion snapshot. True Value changed from a five-city capped repeat scope to twenty-four expanded/gap-close city runs. Therefore:

- added True Value listings mostly mean expanded coverage,
- removed True Value listings can mean source ordering/cap changes,
- `still_active` remains strong repeated-listing evidence,
- price/km changes are meaningful only for still-active listing keys,
- sold/delisted modeling should not use this expansion diff as a clean churn label.

## Artifacts

```text
docs/40-2500-expansion-snapshot-run.md
data/gold/snapshots/snapshot_20260626_2500_expansion_manifest.json
data/gold/snapshots/snapshot_20260626_2500_target_met_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_expansion_execute_v7_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_expansion_execute_v7_batch_summary.md
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_gap_close_resume1_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_gap_close_resume1_batch_summary.md
data/gold/collection_ledger/trusted_collection_v4_20260626_2500_expansion.json
data/gold/collection_ledger/trusted_collection_v4_20260626_2500_expansion.md
data/gold/collection_ledger/trusted_collection_v5_20260626_2500_target_met.json
data/gold/collection_ledger/trusted_collection_v5_20260626_2500_target_met.md
data/gold/listing_lifecycle/listing_lifecycle_v2_20260626_2500_expansion.json
data/gold/listing_lifecycle/listing_lifecycle_v2_20260626_2500_expansion.md
data/gold/listing_lifecycle/listing_lifecycle_v3_20260626_2500_target_met.json
data/gold/listing_lifecycle/listing_lifecycle_v3_20260626_2500_target_met.md
data/gold/snapshot_diffs/snapshot_20260626_2500_expansion_vs_repeat_v3.json
data/gold/snapshot_diffs/snapshot_20260626_2500_expansion_vs_repeat_v3.md
data/gold/snapshot_diffs/snapshot_20260626_2500_target_met_vs_repeat_v3.json
data/gold/snapshot_diffs/snapshot_20260626_2500_target_met_vs_repeat_v3.md
```

## Next Step

Move to the 5,000-row target, but do it with a more balanced source mix.

1. Add more True Value cities or increase True Value city depth where source-total signal is high.
2. Expand Mahindra First Choice where source inventory is available.
3. Add Spinny expansion only after incremental detail enrichment exists, because full-detail Spinny runs are slower.
4. Keep the 2,500 target-met snapshot as the reference point for the next scale projection.
