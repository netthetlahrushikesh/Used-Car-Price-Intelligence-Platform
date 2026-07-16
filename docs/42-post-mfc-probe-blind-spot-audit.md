# Post-MFC Probe Blind-Spot Audit

Date: 2026-06-27

Purpose: review the 5k progress checkpoint after the MFC capacity probe, Spinny incremental promotion, and controlled True Value buffer, then fix issues that could create misleading data, counts, or next-step decisions.

Status: superseded by [Final Spinny/MFC Try and Phase-Final Snapshot](47-final-spinny-mfc-try-and-phase-final-snapshot.md). The final pass caught and fixed additional Spinny variant and city/state blind spots before closing the acquisition phase.

## Current Checkpoint

| Metric | Count |
| --- | ---: |
| Snapshot | `snapshot_20260627_true_value_buffer` |
| Pricing-ready rows | 3,278 |
| Quarantined rows | 0 |
| Unique listing keys | 3,278 |
| Ledger source-city rows | 51 |
| Listing-producing source runs | 50 |
| Remaining 5k gap | 1,722 |

Source split:

| Source | Rows | Share |
| --- | ---: | ---: |
| True Value | 2,448 | 74.68% |
| Mahindra First Choice | 510 | 15.56% |
| Spinny | 320 | 9.76% |

## Fixed Issues

| Issue | Risk | Fix |
| --- | --- | --- |
| Zero-inventory MFC city blocked the whole probe | A real capacity signal looked like a failed scrape | Added `allow_zero_inventory` and `no_inventory` batch status for explicit probe jobs |
| No-inventory source evidence could disappear | Future planning would forget that a city was tested | Collection ledger now retains `no_inventory` rows |
| No-inventory rows could enter lifecycle/model inputs | Lifecycle could try to load missing silver records | Lifecycle now consumes only `pass` ledger rows |
| Scale projection label used stale `current_scope` wording | 909-row baseline looked like the current checkpoint | Projection now has `current_checkpoint_size` and `original_baseline_scope` |
| README/doc 38 pointed to old projection commands | Operator could regenerate the wrong baseline artifact | README and 5k plan now point to `snapshot_20260627_true_value_buffer` |
| Snapshot manifests were still manually assembled | Hand-copied counts could drift from ledger, lifecycle, or diff artifacts | Added `snapshot-manifest` CLI builder with fail-closed count validation |
| Spinny detail runs had no incremental reuse path | Every expansion implied another expensive full-detail run | Added `spinny-incremental-detail` for cache reuse plus capped missing-detail capture |
| Incremental Spinny outputs were not ledger-ready | A good merged payload could bypass acquisition governance | Added `spinny-incremental-manifest` and promoted the 80-row Hyderabad probe into v7 ledger/snapshot artifacts |
| True Value buffer could overrun source allocation | The easiest source could dominate the 5k checkpoint | Added a capped five-city True Value buffer that moved True Value to 2,448 rows, still just under its 2,500-row allocation |
| Spinny final card rows stored price-like text as `variant` | Model features would treat discount/current price text as trim text | Recovered Spinny variant text from listing URL slugs and added a quality guard for price-like variants |
| Spinny final silver rows used default city/state | Non-Hyderabad hub rows could be modeled as Hyderabad/Telangana | Added explicit `run-fixture --city/--state` and regenerated all five final Spinny silver outputs |
| Engine-size-only title suffixes survived as standalone variants | `Wagon-R-1-0` style titles could create noisy model/variant features | Dropped standalone displacement suffixes while keeping real trim text |

## Remaining Blind Spots

### 1. True Value Dominance

True Value is still 74.68% of the current checkpoint. This is better than the 82.87% share at the 2,500 target, but still high for a multi-source market model.

Mitigation:

- Keep True Value as the final buffer, not the first default.
- Prefer new city coverage over repeating the same city-depth pairs.
- Do not train a final pricing model until source share is documented as a model feature or sampling policy.

### 2. MFC Public Inventory Is Uneven

The MFC probe added 331 rows, but many cities had very low inventory and Vadodara had zero inventory.

Strong MFC probe cities:

| City | Pricing Ready |
| --- | ---: |
| Kolkata | 80 |
| Indore | 80 |
| Pune | 66 |
| Nagpur | 37 |
| Coimbatore | 35 |

Mitigation:

- Treat MFC as a useful multi-brand source, not the primary volume source.
- Do not assume the 1,500-row allocation is reachable from current public city pages in one snapshot.
- Consider repeated snapshots or additional MFC source paths later.

### 3. Spinny Throughput Is The Main Engineering Bottleneck

Spinny has high-quality rows, but full-detail city runs take minutes per 60 rows. Scaling Spinny from 320 to 1,000 rows through the old full-detail path would be slow.

Mitigation:

- Split Spinny into card capture and detail enrichment phases with `spinny-incremental-detail`.
- Cache detail payloads by normalized listing URL.
- Enrich only missing records with explicit `--capture-missing` and `--max-new-records` caps.
- Promote completed incremental runs with `spinny-incremental-manifest` before adding them to collection ledgers.

### 4. Source-Specific Optional Fields Are Still Uneven

Known optional gaps remain across sources: body type, dealer name, inspection score, service history, accident history, discount fields, and listing posted timestamps.

Mitigation:

- Keep pricing-critical fields strict.
- Keep source-specific optional features under `extra_fields` unless normalization is proven.
- Delay feature-heavy modeling until optional-field coverage is profiled on the larger snapshot.

## Current Decision

Do not collect blindly from every source just to reach 5k.

The historical next sequence at this audit point was:

1. Use the generated remaining-gap strategy for the 1,722-row gap.
2. Keep future Spinny additions on the manifest-backed incremental-detail path.
3. Do not add both old and deeper same-source same-city runs to the curated ledger.
4. Avoid large additional True Value batches unless the source-mix tradeoff is explicitly documented.

Generated strategy:

```text
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.json
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.md
```

Decision: `balanced_gap_close_required`. The next concrete collection step is `spinny_incremental_expansion_pack`.

Final decision: `snapshot_20260627_final_spinny_mfc_try` is now `final_for_phase` with 3,492 pricing-ready rows, 0 quarantine, and 1,508 rows under the 5k target. Do not run more acquisition in this phase; move to dataset packaging, EDA, and baseline modeling.

## Snapshot Manifest Builder

Current checkpoint manifest command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli snapshot-manifest --snapshot-id snapshot_20260627_true_value_buffer --snapshot-date 2026-06-27 --collection-ledger data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.json --lifecycle-index data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.json --snapshot-diff data/gold/snapshot_diffs/snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe.json --status in_progress --target-pricing-ready 5000 --previous-snapshot-id snapshot_20260627_spinny_incremental_probe --previous-lifecycle-id listing_lifecycle_v5_20260627_spinny_incremental_probe --extra-metadata data/gold/snapshots/snapshot_20260627_true_value_buffer_metadata.json --scope-change-vs-previous "Added a controlled True Value 5k buffer with five new cities capped at 40 records each: Mysuru, Mangaluru, Madurai, Vijayawada, and Rajkot. MFC and Spinny curated scope stayed unchanged." --output-json data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.json --output-md data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.md
```

The builder validates:

- ledger `collection_id` matches lifecycle `collection_id`,
- ledger pricing-ready rows match lifecycle records,
- listing-producing ledger runs match lifecycle source inputs,
- diff current unique listing keys match lifecycle unique listing keys.

## Validation

Latest validation after fixes:

```text
160 unit tests passed
compileall passed
YAML and JSON parse checks passed
```
