# Spinny Bengaluru Hub Collection Run

Date: 2026-06-26

Purpose: validate the first non-Hyderabad Spinny full-detail run before running the remaining Spinny city batches.

## Decision

Run one Spinny non-Hyderabad city first instead of immediately scaling all planned Spinny cities.

Reason:

- Spinny is the slowest trusted source because each listing also needs detail-page enrichment.
- Detail enrichment gives high-value fields such as ownership, RTO, inspection status, warranty, and return policy.
- A single city exposes source-specific layout and pagination issues before multi-city collection.

## Initial Failure

The first Bengaluru attempt used the generic city URL:

```text
https://www.spinny.com/used-cars-in-bangalore/s/
```

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id spinny_bengaluru_60_detail60 --capture-date 2026-06-26 --batch-run-id batch_20260626_spinny_bengaluru_detail_execute --execute --json
```

Result:

```text
fail
```

Observed listing capture:

| Metric | Value |
| --- | ---: |
| Records total | 21 |
| Min records | 60 |
| Unique listing URLs | 21 |
| Duplicate cards skipped | 22 |
| Stop reason | `no_new_cards_after_scroll` |

Conclusion:

- The generic city page did not expose enough usable cards through the current public page mechanics.
- This was a source-page selection issue, not a canonical schema issue.

## Hub URL Fix

The Bengaluru batch was switched to the public Spinny hub URL:

```text
https://www.spinny.com/used-cars-at-bangalore-vega-mall-hub-in-bangalore/s/
```

The batch now also passes a source-specific locality fallback:

```text
Vega City Mall, Bengaluru
```

## Second Failure

The first hub run reached almost the full target but failed by one clean row.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id spinny_bengaluru_60_detail60 --capture-date 2026-06-26 --batch-run-id batch_20260626_spinny_bengaluru_hub_detail_execute --execute --json
```

Observed listing capture:

| Metric | Value |
| --- | ---: |
| Records total | 59 |
| Min records | 60 |
| Returned raw cards | 60 |
| Unique listing URLs | 59 |
| Duplicate cards skipped | 64 |
| Stop reason | `record_cap_reached` |

Root cause:

- The scroll loop stopped when it saw 60 raw DOM card snapshots.
- The quality gate counts parsed listing records with valid vehicle fields and listing URLs.
- One raw card did not become a clean parsed listing row, so the run failed at 59/60.

## Production Fix

Spinny acquisition now separates raw-card capture from clean-row output.

Implementation:

- `max_records` still means the desired clean payload cap.
- The live DOM capture uses small raw-card headroom when `min_records` is strict.
- Parsed records are capped back to `max_records` before validation and detail enrichment.
- Manifests now show headroom metrics:
  - `snapshot_max_records`
  - `raw_cards_returned`
  - `parsed_records_before_cap`

This avoids a future blind spot where raw cards, duplicates, banners, or parser-lost cards silently reduce pricing-ready row counts.

## Successful Run

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id spinny_bengaluru_60_detail60 --capture-date 2026-06-26 --batch-run-id batch_20260626_spinny_bengaluru_hub_detail_execute_v2 --execute --json
```

Result:

```text
pass
```

Batch manifest:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_spinny_bengaluru_hub_detail_execute_v2_batch_manifest.json
```

Source manifest:

```text
data/gold/acquisition_runs/capture_date=2026-06-26/spinny_run_20260626_spinny_bengaluru_60_detail60_batch_20260626_spinny_bengaluru_hub_detail_execute_v2_manifest.json
```

## Result Summary

| Metric | Value |
| --- | ---: |
| Pricing-ready rows | 60 |
| Quarantined rows | 0 |
| Required completeness | 100.00% |
| High-value completeness | 100.00% |
| Overall completeness | 93.93% |
| Detail requested | 60 |
| Detail successful | 60 |
| Detail failed | 0 |
| Runtime | 459.478s |

Listing capture:

| Metric | Value |
| --- | ---: |
| Records total | 60 |
| Min records | 60 |
| Unique listing URLs | 60 |
| Raw cards returned | 62 |
| Parsed records before cap | 61 |
| Snapshot max records | 72 |
| Duplicate cards skipped | 64 |

Quality warnings:

| Warning | Count |
| --- | ---: |
| `variant_inferred` | 2 |

## Updated Collection Ledger

The successful Bengaluru run was added to the selected trusted collection ledger.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli collection-ledger --collection-id trusted_collection_v1_20260626 --source-manifest data\gold\acquisition_runs\capture_date=2026-06-25\spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_manifest.json --batch-manifest data\gold\batch_runs\capture_date=2026-06-25\batch_20260625_true_value_5city_fast_execute_batch_manifest.json --batch-manifest data\gold\batch_runs\capture_date=2026-06-26\batch_20260626_mfc_5city_execute_batch_manifest.json --batch-manifest data\gold\batch_runs\capture_date=2026-06-26\batch_20260626_spinny_bengaluru_hub_detail_execute_v2_batch_manifest.json --output-json data\gold\collection_ledger\trusted_collection_v1_20260626.json --output-md data\gold\collection_ledger\trusted_collection_v1_20260626.md --json
```

Ledger totals:

| Metric | Value |
| --- | ---: |
| Source runs | 12 |
| Pricing-ready rows | 729 |
| Quarantined rows | 0 |
| Source-total inventory signal | 1,766 |

By source:

| Source | Runs | Pricing Ready | Quarantined |
| --- | ---: | ---: | ---: |
| Spinny | 2 | 120 | 0 |
| True Value | 5 | 429 | 0 |
| Mahindra First Choice | 5 | 180 | 0 |

## Verification

Focused gates after the acquisition fix:

```powershell
.venv\Scripts\python -m unittest tests.unit.test_spinny_live_acquisition tests.unit.test_batch_runner tests.unit.test_cli
.venv\Scripts\python -m compileall src tests
.venv\Scripts\python -m unittest discover -s tests
```

Result:

```text
43 tests passed
compileall passed
133 tests passed
```

## Next Step

The remaining planned Spinny city batches were run next and are documented in:

```text
docs/34-spinny-remaining-hubs-collection-run.md
```

The follow-up confirmed that Spinny 5-city full-detail collection can produce 300 pricing-ready rows with 0 quarantined rows, but also showed why parser vocabulary and source-specific hub selection must be handled before scaling further.
