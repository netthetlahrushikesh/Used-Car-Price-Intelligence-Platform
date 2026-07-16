# Snapshot Orchestration Foundation

Date: 2026-06-26

## Question

Before collecting more rows, how do we turn the current trusted collection into a repeatable market snapshot that can support added, removed, still-active, and price-change tracking?

## Decision

Create a snapshot layer after the collection ledger and listing lifecycle index.

The order is:

1. Run trusted source-city acquisition batches.
2. Build a collection ledger from passed source manifests.
3. Build a lifecycle index from the collection ledger.
4. Build a snapshot manifest for the current selected scope.
5. Diff the current lifecycle index against the previous lifecycle index.

The snapshot layer does not scrape pages and does not clean source records. It reads lifecycle JSON and produces repeatable tracking artifacts.

## Why This Matters

A one-time dataset can train a static model, but a price intelligence product needs market movement:

- which listings are new,
- which listings disappeared,
- which listings are still active,
- which prices changed,
- which odometer values changed between observations,
- and whether a source-city scrape had enough coverage to trust those movements.

Without this layer, repeated scraping can accidentally create duplicate rows, false sold signals, and misleading trend features.

## Baseline Snapshot

Baseline snapshot id:

```text
snapshot_20260626_trusted_v2_baseline
```

Input lifecycle:

```text
data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.json
```

Input collection ledger:

```text
data/gold/collection_ledger/trusted_collection_v2_20260626.json
```

Scope:

| Dimension | Values |
| --- | --- |
| Sources | Spinny, True Value, Mahindra First Choice |
| Cities | Hyderabad, Bengaluru, Delhi NCR, Mumbai, Chennai |
| Source runs | 15 |
| Pricing-ready rows | 909 |
| Quarantined rows | 0 |
| Unique listing keys | 909 |

By source:

| Source | Source Runs | Pricing-Ready Rows | Quarantined Rows |
| --- | ---: | ---: | ---: |
| Spinny | 5 | 300 | 0 |
| True Value | 5 | 429 | 0 |
| Mahindra First Choice | 5 | 180 | 0 |

Artifacts:

```text
data/gold/snapshots/snapshot_20260626_trusted_v2_manifest.json
data/gold/snapshot_diffs/snapshot_20260626_trusted_v2_baseline_diff.json
data/gold/snapshot_diffs/snapshot_20260626_trusted_v2_baseline_diff.md
```

## Command

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli snapshot-diff --snapshot-id snapshot_20260626_trusted_v2_baseline --snapshot-date 2026-06-26 --current-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.json --output-json data/gold/snapshot_diffs/snapshot_20260626_trusted_v2_baseline_diff.json --output-md data/gold/snapshot_diffs/snapshot_20260626_trusted_v2_baseline_diff.md
```

Baseline result:

| Metric | Count |
| --- | ---: |
| Previous unique listing keys | 0 |
| Current unique listing keys | 909 |
| Added listings | 909 |
| Removed listings | 0 |
| Still-active listings | 0 |
| Price changes | 0 |
| Km changes | 0 |

Because this is the first snapshot, every listing is counted as added by definition.

## Diff Semantics

The diff uses `listing_key` from the lifecycle index.

Added listing:

- present in the current lifecycle,
- absent from the previous lifecycle.

Removed listing:

- present in the previous lifecycle,
- absent from the current lifecycle.

Still-active listing:

- present in both lifecycle indexes.

Price change:

- same `listing_key` in both lifecycle indexes,
- previous and current `latest_observation.listed_price_inr` are numeric,
- values differ.

Km change:

- same `listing_key` in both lifecycle indexes,
- previous and current `latest_observation.km_driven` are numeric,
- values differ.

## Important Limitation

Removed does not automatically mean sold.

It means the listing was not observed in the current selected lifecycle. It should only be interpreted as sold, unavailable, or delisted when the new source-city scrape had equivalent coverage to the previous snapshot.

Examples:

- If previous True Value Hyderabad captured all discovered dealers and the next True Value Hyderabad run also captures all discovered dealers, a missing listing is a stronger unavailable signal.
- If previous Spinny Bengaluru captured 60 hub listings and the next run captures only 30 because of a timeout, missing listings are weak signals.
- If Mahindra First Choice changes inventory or city routing, removed listings must be interpreted with the MFC-specific acquisition notes.

## Production Runbook

For the next repeated collection:

1. Keep the source-city scope the same as the baseline unless a scope change is intentional.
2. Run acquisition batches by source and city.
3. Let failed or partial source runs remain out of the trusted collection ledger.
4. Build a new collection ledger only from passed runs.
5. Build a new lifecycle index from that ledger.
6. Run `snapshot-diff` with the previous lifecycle index and the new lifecycle index.
7. Review removed listings by source-city coverage before labeling them as sold/unavailable.
8. Use price and km changes as direct market movement features only for still-active listing keys.

Future command shape:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli snapshot-diff --snapshot-id snapshot_YYYYMMDD_trusted_scope --snapshot-date YYYY-MM-DD --previous-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.json --current-lifecycle data/gold/listing_lifecycle/listing_lifecycle_vNEXT_YYYYMMDD.json --output-json data/gold/snapshot_diffs/snapshot_YYYYMMDD_trusted_scope_diff.json --output-md data/gold/snapshot_diffs/snapshot_YYYYMMDD_trusted_scope_diff.md
```

## What This Unlocks

This gives the project a production-style observation model:

- current market inventory,
- source-level freshness,
- listing persistence,
- price revision history,
- early sold/unavailable candidates,
- and repeated observations without duplicate training rows.

It also makes the 100k-row plan more realistic. We do not need 100k unique cars immediately; we can grow toward 100k trusted observations by repeating controlled source-city snapshots and preserving lifecycle identity.

## Next Step

The next engineering step is a collection-scale runbook:

- choose snapshot cadence,
- decide daily versus weekly collection for each source,
- choose which source-city batches are safe for bounded parallel execution,
- and define when a snapshot is considered complete enough to compare against the previous one.
