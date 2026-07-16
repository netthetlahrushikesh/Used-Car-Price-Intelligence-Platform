# 100k Observation Identity Recheck

Date: 2026-06-28

## Question

Can the 103,719 observation CSV be deduped with a different identity rule to produce more real unique cars than 3,496?

## Result

No. The honest unique listing count remains 3,496.

The 103,719 rows are repeated observations from repeated extraction rounds. Changing the identity rule can create larger row counts, but those larger counts are not real unique cars.

## Identity Counts Tested

| Identity Rule | Unique Count | Decision |
| --- | ---: | --- |
| Source + normalized listing URL | 3,496 | Use for unique listings |
| Raw record hash | 3,573 | Too sensitive to small payload changes |
| Strict source/city/brand/model/variant/year/fuel/transmission/km/price signature | 3,596 | Inflated by city/search context and small field changes |
| Source listing id | 4,374 | False inflation from Spinny generated fixture ids |

## By Source

| Source | URL Unique | Source Listing ID Unique | Raw Hash Unique |
| --- | ---: | ---: | ---: |
| Mahindra First Choice | 579 | 579 | 579 |
| Spinny | 478 | 1,356 | 516 |
| True Value | 2,439 | 2,439 | 2,478 |

The main trap is Spinny. The same Spinny listing URL can receive different generated `source_listing_id` values across captures, such as `spinny_fixture_001_*`, `spinny_fixture_002_*`, and so on. Those ids are capture artifacts, not separate cars.

## Collision Checks

Observed groups:

| Check | Count |
| --- | ---: |
| Listing URL groups | 3,496 |
| URL groups with multiple source listing ids | 397 |
| URL groups with multiple strict non-location signatures | 1 |
| URL groups with multiple vehicle signatures excluding price/km | 0 |
| Source listing id groups with multiple URLs | 0 |

The one strict non-location signature difference was a same-URL field update, not a different vehicle identity.

## Registration / Number Plate Check

The 103,719-row observation CSV does not contain full number plates.

The available field is `registration_code`, which is an RTO prefix such as `MP09`, `MH12`, `TS07`, or `GJ05`. That tells us the registration region, not the individual vehicle number.

| Rule | Unique Count | Decision |
| --- | ---: | --- |
| Source + registration code only | 609 | Far too low; many cars share one RTO code |
| Source + registration code + brand + model + year | 3,099 | Collapses different trims/cars |
| Source + registration code + vehicle core fields | 3,318 | Still below URL identity and not complete for all MFC rows |
| Source + registration code + vehicle core + km + price | 3,497 | Slightly higher than URL identity, but caused by field/update sensitivity, not confirmed new cars |

Registration completeness:

| Source | Registration Code Completeness | Unique Registration Codes | URL Unique Listings |
| --- | ---: | ---: | ---: |
| Mahindra First Choice | 91.39% | 144 | 579 |
| Spinny | 100.00% | 96 | 478 |
| True Value | 100.00% | 368 | 2,439 |

Full number-plate-like values found: 0.

Decision: keep `registration_code` as a useful modeling and duplicate-review feature, but do not use it as the primary listing identity. If a future source exposes full plate numbers, they should be handled carefully as sensitive data and stored only if the project has a clear privacy policy.

## Decision

Use URL-based lifecycle identity for trusted unique listings:

```text
source + normalized listing_url
```

Keep one latest row per listing URL for normal EDA and supervised price modeling.

Do not use `source_listing_id` as the primary identity across all sources because it incorrectly inflates Spinny unique rows.

## Practical Meaning

Current files:

```text
data/gold/exports/snapshot_20260627_100k_observation_run/snapshot_20260627_100k_observation_run_pricing_ready_observations.csv
```

This is the 103,719-row observation dataset.

```text
data/gold/exports/snapshot_20260627_100k_observation_run/snapshot_20260627_100k_observation_run_unique_latest_full.csv
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/listings_modeling_dataset.csv
```

These are the 3,496-row unique datasets.

To reach 10k or 100k unique listings, the next step must be new inventory coverage or external dataset integration, not a looser duplicate-removal rule.
