# Collection Ledger

Date: 2026-06-26

Purpose: create a reproducible collection index from selected source-run and batch manifests.

## Why This Was Needed

After the True Value and Mahindra First Choice 5-city runs, manual row counting became risky.

The repository now contains many manifests:

- exploratory smoke runs,
- failed attempts,
- retried batch runs,
- final passing collection runs.

Counting every manifest would overstate the dataset. The collection ledger solves this by requiring explicit inputs.

## Command

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli collection-ledger --collection-id trusted_collection_v0_20260626 --source-manifest data\gold\acquisition_runs\capture_date=2026-06-25\spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_manifest.json --batch-manifest data\gold\batch_runs\capture_date=2026-06-25\batch_20260625_true_value_5city_fast_execute_batch_manifest.json --batch-manifest data\gold\batch_runs\capture_date=2026-06-26\batch_20260626_mfc_5city_execute_batch_manifest.json --output-json data\gold\collection_ledger\trusted_collection_v0_20260626.json --output-md data\gold\collection_ledger\trusted_collection_v0_20260626.md --json
```

## Outputs

```text
data/gold/collection_ledger/trusted_collection_v0_20260626.json
data/gold/collection_ledger/trusted_collection_v0_20260626.md
```

## Result

Collection id:

```text
trusted_collection_v0_20260626
```

Totals:

| Metric | Value |
| --- | ---: |
| Source runs | 11 |
| Pricing-ready rows | 669 |
| Quarantined rows | 0 |
| Source-total inventory signal | 1,766 |

By source:

| Source | Runs | Pricing Ready | Quarantined | Source Total Signal |
| --- | ---: | ---: | ---: | ---: |
| Mahindra First Choice | 5 | 180 | 0 | 275 |
| Spinny | 1 | 60 | 0 | 0 |
| True Value | 5 | 429 | 0 | 1,491 |

## Selected Inputs

The ledger intentionally includes only the current trusted collection set:

- Spinny Hyderabad 60-row full-detail baseline.
- True Value 5-city fast batch.
- Mahindra First Choice 5-city batch.

It does not include earlier exploratory smoke runs or failed attempts.

## Why This Matters

This is the first proper dataset-level artifact.

It allows the project to answer:

- how many rows are currently pricing-ready,
- which source and city each row set came from,
- which run manifests prove the result,
- whether any rows were quarantined,
- whether low-volume cities were source-limited or pipeline-limited.

## Next Step

Run Spinny multi-city batches through the same batch-runner and ledger pattern.

Recommended order:

1. Run one Spinny non-Hyderabad city first.
2. Regenerate the ledger.
3. If the first non-Hyderabad city passes, run the remaining Spinny planned cities.
4. Add dedupe/lifecycle tracking before repeated snapshots.

## Update: v1 After Spinny Bengaluru

After the first non-Hyderabad Spinny full-detail run passed, the selected collection ledger was regenerated as:

```text
trusted_collection_v1_20260626
```

Outputs:

```text
data/gold/collection_ledger/trusted_collection_v1_20260626.json
data/gold/collection_ledger/trusted_collection_v1_20260626.md
```

Updated totals:

| Metric | Value |
| --- | ---: |
| Source runs | 12 |
| Pricing-ready rows | 729 |
| Quarantined rows | 0 |
| Source-total inventory signal | 1,766 |

By source:

| Source | Runs | Pricing Ready | Quarantined | Source Total Signal |
| --- | ---: | ---: | ---: | ---: |
| Mahindra First Choice | 5 | 180 | 0 | 275 |
| Spinny | 2 | 120 | 0 | 0 |
| True Value | 5 | 429 | 0 | 1,491 |

The new Spinny run is documented in `docs/33-spinny-bengaluru-hub-collection-run.md`.

## Update: v2 After First-Pass Spinny 5-City Completion

After Delhi NCR, Mumbai, and Chennai passed, the selected collection ledger was regenerated as:

```text
trusted_collection_v2_20260626
```

Outputs:

```text
data/gold/collection_ledger/trusted_collection_v2_20260626.json
data/gold/collection_ledger/trusted_collection_v2_20260626.md
```

Updated totals:

| Metric | Value |
| --- | ---: |
| Source runs | 15 |
| Pricing-ready rows | 909 |
| Quarantined rows | 0 |
| Source-total inventory signal | 1,766 |

By source:

| Source | Runs | Pricing Ready | Quarantined | Source Total Signal |
| --- | ---: | ---: | ---: | ---: |
| Mahindra First Choice | 5 | 180 | 0 | 275 |
| Spinny | 5 | 300 | 0 | 0 |
| True Value | 5 | 429 | 0 | 1,491 |

The additional Spinny city runs are documented in `docs/34-spinny-remaining-hubs-collection-run.md`.
