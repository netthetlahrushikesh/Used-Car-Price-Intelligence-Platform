# Repeat Snapshot V3 Run

Date: 2026-06-26

## Question

Can the platform repeat the same trusted source-city scope and produce a lifecycle diff against the baseline?

## Decision

Yes. The repeat snapshot gate passed.

The repeat run produced:

- 15 source-city runs,
- 911 pricing-ready rows,
- 0 quarantined rows,
- 911 unique lifecycle listing keys,
- a real added/removed/still-active diff against the 909-row baseline.

This means the project can move to the next controlled expansion stage: about 2,500 rows per snapshot before attempting the 5,000-row target.

## Execution Summary

Final batch manifest:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_repeat_snapshot_v3_same_scope_resume2_batch_manifest.json
```

The repeat snapshot needed resumable execution:

1. Initial execute run passed Spinny Hyderabad, MFC Hyderabad, True Value Hyderabad, and Spinny Bengaluru.
2. Initial execute failed on Spinny Delhi NCR with zero cards captured.
3. Resume 1 recovered Spinny Delhi NCR and Spinny Mumbai, then failed on Spinny Chennai due to a detail-page `ERR_CONNECTION_RESET`.
4. Resume 2 recovered Spinny Chennai and completed all remaining MFC and True Value jobs.

These failures were acquisition/runtime failures, not parser or schema failures. The resume process handled them correctly.

## Collection Ledger

Command:

```powershell
.venv\Scripts\python.exe -m used_car_price_intelligence.cli collection-ledger --collection-id trusted_collection_v3_20260626_repeat_snapshot --batch-manifest data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_repeat_snapshot_v3_same_scope_resume2_batch_manifest.json --output-json data/gold/collection_ledger/trusted_collection_v3_20260626_repeat_snapshot.json --output-md data/gold/collection_ledger/trusted_collection_v3_20260626_repeat_snapshot.md
```

Result:

| Source | Source Runs | Pricing-Ready Rows | Quarantined Rows | Source Total Signal |
| --- | ---: | ---: | ---: | ---: |
| Spinny | 5 | 300 | 0 | 0 |
| True Value | 5 | 432 | 0 | 1,501 |
| Mahindra First Choice | 5 | 179 | 0 | 284 |
| Total | 15 | 911 | 0 | 1,785 |

## Lifecycle Index

Command:

```powershell
.venv\Scripts\python.exe -m used_car_price_intelligence.cli listing-lifecycle --lifecycle-id listing_lifecycle_v1_20260626_repeat_snapshot --collection-ledger data/gold/collection_ledger/trusted_collection_v3_20260626_repeat_snapshot.json --output-json data/gold/listing_lifecycle/listing_lifecycle_v1_20260626_repeat_snapshot.json --output-md data/gold/listing_lifecycle/listing_lifecycle_v1_20260626_repeat_snapshot.md
```

Result:

| Metric | Count |
| --- | ---: |
| Records processed | 911 |
| Source runs | 15 |
| Unique listing keys | 911 |
| Reobserved listing groups | 0 |
| Possible vehicle duplicate groups | 0 |

## Snapshot Diff

Command:

```powershell
.venv\Scripts\python.exe -m used_car_price_intelligence.cli snapshot-diff --snapshot-id snapshot_20260626_repeat_v3_vs_baseline --snapshot-date 2026-06-26 --previous-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.json --current-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v1_20260626_repeat_snapshot.json --output-json data/gold/snapshot_diffs/snapshot_20260626_repeat_v3_vs_baseline_diff.json --output-md data/gold/snapshot_diffs/snapshot_20260626_repeat_v3_vs_baseline_diff.md
```

Diff result:

| Metric | Count |
| --- | ---: |
| Previous unique listing keys | 909 |
| Current unique listing keys | 911 |
| Added listings | 101 |
| Removed listings | 99 |
| Still-active listings | 810 |
| Price changes | 3 |
| Km changes | 1 |

By source:

| Source | Previous | Current | Added | Removed | Still Active | Price Changes | Km Changes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Spinny | 300 | 300 | 49 | 49 | 251 | 3 | 1 |
| True Value | 429 | 432 | 44 | 41 | 388 | 0 | 0 |
| Mahindra First Choice | 180 | 179 | 8 | 9 | 171 | 0 | 0 |

## Movement Interpretation

The added/removed movement is real at the listing-key level, but it is not automatically a sold/delisted label.

For this snapshot, many source-city runs are capped:

- Spinny captures 60 rows per city.
- True Value captures up to 100 rows for most cities.
- MFC captures up to 80 rows for most cities.

Because of that, an added/removed pair can mean:

- real inventory churn,
- changed ordering in the source inventory window,
- source-side page/ranking changes,
- or a true sold/unavailable signal.

The safest interpretation is:

- `still_active` is strong evidence of a repeated listing,
- `price_changes` are strong evidence because the same listing key is observed again,
- `removed` is a candidate unavailable/sold signal only when source-city coverage is equivalent.

## Price And Km Signals

Price changes were all Spinny Hyderabad listings:

| Vehicle | Previous Price | Current Price | Delta |
| --- | ---: | ---: | ---: |
| 2023 Kia Seltos GTX Plus 1.4 DCT | 1,567,000 | 1,528,000 | -39,000 |
| 2022 Volkswagen Taigun Topline 1.0 TSI MT | 907,000 | 877,000 | -30,000 |
| 2019 Audi Q3 35 TDI quattro Premium Plus | 1,774,000 | 1,750,000 | -24,000 |

One Spinny Chennai MG Hector listing had a km change from 71,000 to 70,500. Treat km decreases as a source correction signal, not vehicle usage.

## What This Unlocks

The repeat snapshot proves:

- acquisition can be resumed after transient live failures,
- collection ledgers can resolve skipped-passed source runs,
- lifecycle identity can compare two snapshots,
- same-listing price changes can be detected,
- and the platform can now move beyond the 909-row baseline safely.

## Next Step

Move to the small-scale expansion target:

1. Add more True Value source-city coverage first.
2. Add MFC coverage second.
3. Keep Spinny capped until incremental detail enrichment is implemented.
4. Target about 2,500 rows in the next expansion snapshot.
5. Only after that is stable, move toward the 5,000-row production snapshot target.
