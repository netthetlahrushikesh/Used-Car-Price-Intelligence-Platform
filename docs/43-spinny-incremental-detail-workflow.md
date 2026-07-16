# Spinny Incremental Detail Workflow

Date: 2026-06-27

Purpose: make Spinny expansion faster without lowering data quality. Spinny remains a high-quality source, but full `detail60` city runs are too slow to scale blindly.

## Decision

Do not treat Spinny as one monolithic full-detail scrape.

Use a two-stage workflow:

1. Capture listing cards with bounded page and row caps.
2. Reuse existing detail payloads by normalized listing URL.
3. Capture only missing detail URLs when explicitly requested.
4. Merge detail fields into the listing payload.
5. Run the normal canonical pipeline only on the merged payload.

## New CLI

The new command is:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-incremental-detail --listing-payload data/tmp/spinny_listing_payload.json --existing-detail-payload data/tmp/prior_spinny_details.json --max-new-records 20 --output-plan data/tmp/spinny_incremental_detail_plan.json --output-detail-payload data/tmp/spinny_incremental_details_combined.json --output-merged-payload data/tmp/spinny_incremental_listing_merged.json --json
```

This mode does not capture new detail pages. It only plans and reuses cache.

To capture missing detail pages, add `--capture-missing` and a `--new-detail-output` path:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-incremental-detail --listing-payload data/tmp/spinny_listing_payload.json --existing-detail-payload data/tmp/prior_spinny_details.json --max-new-records 20 --capture-missing --new-detail-output data/tmp/spinny_incremental_details_new.json --output-plan data/tmp/spinny_incremental_detail_plan.json --output-detail-payload data/tmp/spinny_incremental_details_combined.json --output-merged-payload data/tmp/spinny_incremental_listing_merged.json --json
```

## Guardrails

- `--capture-missing` is required before the command touches live detail pages.
- `--max-new-records` caps new detail fetches.
- Existing detail records are reused by normalized Spinny listing URL, ignoring query strings and trailing slashes.
- Cache records are preferred over failed records.
- Newly captured records override cached records for the same listing URL.
- The command writes a plan artifact before capture, so pending URLs are auditable.

## Output Artifacts

| Artifact | Purpose |
| --- | --- |
| `*_plan.json` | Cache hits, pending URLs, selected new URLs, and coverage before capture |
| `*_details_new.json` | Newly captured missing detail records, only when `--capture-missing` is used |
| `*_details_combined.json` | Cache plus new detail records selected for the listing payload |
| `*_listing_merged.json` | Listing-card payload with detail fields merged by URL |

## What This Fixes

Before this workflow, every Spinny expansion implied another full-detail run. That made 700 more Spinny rows operationally expensive and fragile.

Now we can:

- run card capture independently,
- inspect how many listings already have cached details,
- fetch only missing detail records,
- avoid duplicate detail-page work across repeated snapshots,
- keep detail enrichment observable before records enter the canonical pipeline.

## Current 5k Role

Spinny now has 320 pricing-ready rows in the latest 5k progress snapshot after the successful Hyderabad incremental-detail probe was promoted into the normal manifest and ledger path. The controlled probe proved:

- merged payloads keep 0 quarantine,
- required completeness stays 100%,
- high-value completeness stays at or above 95%,
- runtime is materially lower than full `detail60` per city when cache hits exist.

Spinny can now be used as a quality-anchor expansion lane through the manifest-backed incremental path while the final True Value buffer closes part of the 5k gap.

## Cache-Reuse Proof

The workflow was tested against the existing Hyderabad `60/60` Spinny payload pair without live capture.

Command shape:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-incremental-detail --listing-payload data/tmp/spinny_live_smoke_payload_2026-06-25_hyderabad_manifest_60_detail60.json --existing-detail-payload data/tmp/spinny_live_smoke_payload_2026-06-25_hyderabad_manifest_60_detail60_details.json --max-new-records 20 --output-plan data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_cache_reuse_plan.json --output-detail-payload data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_combined_details.json --output-merged-payload data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_incremental_merged_payload.json --json
```

Result:

| Metric | Count |
| --- | ---: |
| Listing records | 60 |
| Unique listing URLs | 60 |
| Cache hit URLs | 60 |
| Pending detail URLs | 0 |
| Merged records | 60 |
| Pricing-ready rows after canonical pipeline | 60 |
| Quarantined rows | 0 |
| Required completeness | 100% |
| High-value completeness | 100% |

Artifacts:

```text
data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_cache_reuse_plan.json
data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_combined_details.json
data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_incremental_merged_payload.json
```

## Controlled 80-Card Probe

The workflow was then tested on an expanded Hyderabad card capture.

Card-capture command shape:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli capture-spinny-live --url https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/ --output data/tmp/spinny_hyderabad_80_cards_probe_20260627.json --max-pages 4 --max-records 80 --min-records 60 --locality "Nexus Sujana Mall, Kukatpally" --timeout-ms 60000 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --json
```

Incremental detail command shape:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-incremental-detail --listing-payload data/tmp/spinny_hyderabad_80_cards_probe_20260627.json --existing-detail-payload data/tmp/spinny_live_smoke_payload_2026-06-25_hyderabad_manifest_60_detail60_details.json --max-new-records 20 --capture-missing --new-detail-output data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_new_details_20.json --output-plan data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_capture20_plan.json --output-detail-payload data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_combined_details_capture20.json --output-merged-payload data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_merged_capture20.json --timeout-ms 60000 --detail-delay-ms 3000 --detail-attempts 2 --json
```

Result:

| Metric | Count |
| --- | ---: |
| Listing-card records | 80 |
| Unique listing URLs | 80 |
| Cache hit URLs | 50 |
| Pending detail URLs before capture | 30 |
| New detail cap | 20 |
| New detail records captured | 20 |
| Combined detail records | 70 |
| Detail failures | 0 |
| Merged records | 80 |
| Pricing-ready rows after canonical pipeline | 80 |
| Quarantined rows | 0 |
| Required completeness | 100% |
| High-value completeness | 98.21% |

Canonical pipeline command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-fixture --source spinny --fixture data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_merged_capture20.json --captured-at 2026-06-27T00:00:00Z --run-id run_20260627_spinny_hyderabad_80_incremental_detail_probe --capture-date 2026-06-27 --write --json
```

Artifacts:

```text
data/tmp/spinny_hyderabad_80_cards_probe_20260627.json
data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_capture20_plan.json
data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_new_details_20.json
data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_combined_details_capture20.json
data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_merged_capture20.json
data/gold/quality_summary/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_quality_summary.json
data/silver/listings/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_silver.json
```

Decision:

- The workflow was promoted into the manifest and ledger path on 2026-06-27.
- The 80-row Hyderabad run replaced the older 60-row Hyderabad Spinny run in the curated ledger.
- Future broad Spinny expansion must use this manifest-backed incremental path instead of one-off merged payloads.

## Manifest And Ledger Promotion

Manifest command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-incremental-manifest --listing-payload data/tmp/spinny_hyderabad_80_cards_probe_20260627.json --detail-plan data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_capture20_plan.json --detail-payload data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_combined_details_capture20.json --quality-summary data/gold/quality_summary/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_quality_summary.json --merged-payload data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_merged_capture20.json --new-detail-payload data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_new_details_20.json --run-id run_20260627_spinny_hyderabad_80_incremental_detail_probe --capture-date 2026-06-27 --city Hyderabad --state Telangana --json
```

Manifest output:

```text
data/gold/acquisition_runs/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_manifest.json
```

Promotion result:

| Metric | Count |
| --- | ---: |
| Old curated Hyderabad Spinny rows replaced | 60 |
| New Hyderabad Spinny rows | 80 |
| Net pricing-ready increase | 20 |
| Current Spinny rows in curated ledger | 320 |
| Current total pricing-ready rows | 3,147 |
| Current rows under 5k target | 1,853 |
| Quarantined rows | 0 |

New gold artifacts:

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
```

Diff interpretation:

- Current unique listing keys increased from 3,127 to 3,147.
- Spinny Hyderabad replacement produced 27 added listing keys and 7 removed listing keys versus the previous checkpoint.
- 53 still-active Spinny listing keys had price changes, which is expected for a fresh source snapshot and should be retained for price-intelligence signals.
