# Listing Lifecycle And Dedupe Foundation

Date: 2026-06-26

Purpose: add a production-style listing identity layer before collecting repeated snapshots or scaling toward larger observation counts.

## Why This Step Was Needed

After the first trusted collection reached 909 pricing-ready rows, the next risk was no longer basic scraping.

The next risk was duplicate and lifecycle confusion:

- the same listing may appear again in a later snapshot,
- the same physical car may appear on more than one source,
- source URLs and source IDs may behave differently across websites,
- historical observations should not be mixed with current unique inventory,
- repeated snapshots need `first_seen_at` and `last_seen_at` semantics.

Without this layer, a future 100k-observation dataset could accidentally become duplicate-heavy and misleading for model training.

## Decision

Build a lifecycle index from the curated collection ledger.

Input:

```text
data/gold/collection_ledger/trusted_collection_v2_20260626.json
```

Outputs:

```text
data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.json
data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.md
```

## Identity Policy

The lifecycle index uses two different identity layers.

### 1. Exact Listing Key

Purpose:

- Track the same source listing across repeated snapshots.
- This is the key used for `first_seen_at`, `last_seen_at`, and observation count.

Priority:

1. `source + normalized listing_url`
2. `source + source_listing_id`
3. `source + raw_record_hash`
4. fallback core fields

This is intentionally source-scoped. A Spinny listing and a True Value listing should not be automatically merged only because they describe similar cars.

### 2. Conservative Vehicle Fingerprint

Purpose:

- Flag possible duplicate vehicles for review.
- This is not an automatic merge key.

Fields:

- city
- brand
- model
- variant
- model/manufacture year
- fuel type
- transmission
- ownership
- registration code
- km bucket
- price bucket

Bucket sizes:

| Field | Bucket |
| --- | ---: |
| Kilometers | 5,000 km |
| Price | Rs 50,000 |

## Command

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli listing-lifecycle --lifecycle-id listing_lifecycle_v0_20260626 --collection-ledger data\gold\collection_ledger\trusted_collection_v2_20260626.json --output-json data\gold\listing_lifecycle\listing_lifecycle_v0_20260626.json --output-md data\gold\listing_lifecycle\listing_lifecycle_v0_20260626.md
```

## Result

| Metric | Value |
| --- | ---: |
| Records processed | 909 |
| Source runs | 15 |
| Unique listing keys | 909 |
| Reobserved listing groups | 0 |
| Possible vehicle duplicate groups | 1 |

By source:

| Source | Records | Unique Listing Keys | Reobserved Groups | Possible Vehicle Duplicate Groups |
| --- | ---: | ---: | ---: | ---: |
| Mahindra First Choice | 180 | 180 | 0 | 0 |
| Spinny | 300 | 300 | 0 | 0 |
| True Value | 429 | 429 | 0 | 1 |

## Interpretation

The current selected collection has no repeated source listing keys.

That means the 909-row dataset currently behaves like 909 unique source listings.

The lifecycle index found one conservative possible vehicle duplicate group:

| Source | City | Year | Brand | Model | Variant | Km | Price | Registration |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | --- |
| True Value | Delhi NCR | 2011 | Maruti Suzuki | Wagon R | LXI | 56,158 | 70,000 | DL13 |
| True Value | Delhi NCR | 2011 | Maruti Suzuki | Wagon R | LXI | 56,321 | 68,000 | DL13 |

These are not automatically merged. They are review candidates because public data does not include a full plate/VIN.

## Implementation

Added:

```text
src/used_car_price_intelligence/reporting/listing_lifecycle.py
```

CLI:

```text
listing-lifecycle
```

Tests:

```text
tests/unit/test_listing_lifecycle.py
```

The test fixture covers:

- normalized URL matching across repeated observations,
- listing lifecycle observation counts,
- conservative vehicle duplicate group detection,
- JSON and Markdown output writing,
- CLI output generation.

## Verification

Focused checks:

```powershell
.venv\Scripts\python -m unittest tests.unit.test_listing_lifecycle tests.unit.test_cli
.venv\Scripts\python -m compileall src tests
```

Result:

```text
29 tests passed
compileall passed
```

## Next Step

Build a snapshot manifest and scheduling policy before the next scrape.

The next collection loop should produce:

- snapshot id,
- snapshot date,
- source-city batch list,
- expected row targets,
- previous lifecycle index input,
- new lifecycle index output,
- added listings,
- removed listings,
- still-active listings.

This is the correct bridge from a one-time clean dataset to a time-series market intelligence platform.
