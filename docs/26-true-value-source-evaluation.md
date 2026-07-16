# Maruti Suzuki True Value Source Evaluation

Date: 2026-06-25

Source URL: <https://www.marutisuzukitruevalue.com/buy-car>

## Decision

Maruti Suzuki True Value is approved as the third trusted source contract.

It should stay separate from Spinny and Mahindra First Choice at the acquisition layer. The site has its own mechanics: dealer discovery by latitude/longitude, followed by structured GraphQL product search using True Value dealer codes.

True Value is a strong data source for Maruti Suzuki inventory, but it is not a multi-brand source. Use it to improve trusted Maruti coverage and OEM-certified source diversity, not as a replacement for Spinny or Mahindra First Choice.

## Why This Source Fits

True Value is an OEM-backed used-car program. For this project, that matters because the first model-training dataset should prefer evaluated platform, dealer, or OEM inventory over customer self-listed inventory.

The source gives structured fields that are directly useful for price intelligence:

- listed price,
- model year,
- model,
- variant,
- kilometers driven,
- fuel type,
- transmission,
- ownership,
- registration code,
- dealer location,
- body type,
- color,
- certification and DMS status,
- warranty code,
- source-specific ratings.

## Source Mechanics

Observed public flow:

1. The generic `/buy-car` page renders the inventory application.
2. The frontend requests nearby True Value dealers with latitude, longitude, radius, and `dealerType=TV`.
3. The frontend queries the True Value GraphQL endpoint with the discovered dealer codes.
4. The GraphQL product rows include product identity, price, stock status, image count, and a structured attributes array.

Implemented acquisition module:

```text
src/used_car_price_intelligence/acquisition/true_value_live.py
```

Implemented CLI commands:

```text
capture-true-value-live
true-value-live-smoke
```

Pagination type:

```text
dealer_discovery_plus_graphql
```

This is intentionally different from:

- Spinny: rendered listing cards, infinite scroll, optional detail pages.
- Mahindra First Choice: Next.js page state plus browser-triggered XHR pagination.

## Hyderabad Live Evidence

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli true-value-live-smoke --payload-output data/tmp/true_value_live_smoke_payload_2026-06-25_hyderabad_40.json --run-id run_20260625_true_value_hyderabad_40_smoke --capture-date 2026-06-25 --city Hyderabad --state Telangana --latitude 17.385044 --longitude 78.486671 --dealer-distance-m 25000 --max-pages 1 --page-size 100 --max-records 40 --min-records 40 --capture-attempts 3 --retry-delay-ms 2000 --timeout-seconds 60 --json
```

Result:

- Captured at: `2026-06-25T13:54:29Z`.
- Hyderabad dealer count discovered: 21.
- Dealer radius: 25,000 meters.
- Source total items observed: 247.
- Source total pages: 3.
- Unique source rows seen on first GraphQL page: 100.
- Returned records: 40.
- Pricing-ready records: 40.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 100.00%.
- Optional completeness: 42.25%.
- Overall completeness: 94.22%.

Generated outputs:

```text
data/raw/source=true_value/capture_date=2026-06-25/run_id=run_20260625_true_value_hyderabad_40_smoke/fixture_source_payload.json
data/silver/listings/capture_date=2026-06-25/true_value_run_20260625_true_value_hyderabad_40_smoke_silver.json
data/gold/quality_summary/capture_date=2026-06-25/true_value_run_20260625_true_value_hyderabad_40_smoke_quality_summary.json
data/gold/acquisition_runs/capture_date=2026-06-25/true_value_run_20260625_true_value_hyderabad_40_smoke_manifest.json
data/gold/smoke_reports/capture_date=2026-06-25/true_value_run_20260625_true_value_hyderabad_40_smoke_smoke_report.md
```

## Field Coverage In Validated 40-Row Run

Raw payload fields:

| Field | Coverage |
| --- | ---: |
| sku | 40/40 |
| price | 40/40 |
| model_year | 40/40 |
| model | 40/40 |
| variant | 40/40 |
| km | 40/40 |
| fuel | 40/40 |
| transmission | 40/40 |
| ownership | 40/40 |
| registration | 40/40 |
| registration_date | 40/40 |
| body_type | 40/40 |
| color | 39/40 |
| dealer_name | 40/40 |
| dealer_code | 40/40 |
| true_value_certified | 40/40 |
| dms_certification_status | 39/40 |
| overall_rating | 40/40 |
| warranty_info | 40/40 |
| listing_posted_at | 40/40 |

Canonical quality gates:

| Group | Result |
| --- | ---: |
| Required fields | 100.00% |
| High-value fields | 100.00% |
| Optional fields | 42.25% |
| Pricing-ready rows | 40/40 |
| Quarantine rows | 0/40 |

## Model Mix In Validated Run

Observed models:

| Model | Rows |
| --- | ---: |
| Baleno | 7 |
| Wagon R | 4 |
| Alto 800 | 4 |
| Xl6 | 4 |
| Brezza | 3 |
| Dzire | 3 |
| Omni | 3 |
| Alto | 2 |
| Alto K10 | 2 |
| Ertiga | 2 |
| Fronx | 2 |
| S-Presso | 2 |
| Swift | 2 |

Parser vocabulary was expanded for Maruti model families observed during source research, including `Alto`, `Alto 800`, `Alto K10`, `Baleno`, `Brezza`, `Celerio`, `Ciaz`, `Dzire`, `Eeco`, `Ertiga`, `Fronx`, `Grand Vitara`, `Ignis`, `Omni`, `Ritz`, `S-Cross`, `S-Presso`, `Swift`, `SX4`, `Wagon R`, and `XL6`.

## Certification And Warranty Signals

In the validated 40-row run:

- `true_value_certified=yes`: 27 rows.
- `true_value_certified=no`: 13 rows.
- `dms_certification_status=CR`: 27 rows.
- `dms_certification_status=IO`: 12 rows.
- `dms_certification_status` missing: 1 row.
- `warranty_info=1Y`: 17 rows.
- `warranty_info=6M`: 11 rows.
- `warranty_info=0M`: 12 rows.

Important interpretation:

- True Value is trusted/OEM-backed inventory, but not every row is marked certified in the same way.
- Certification and DMS status should remain source-specific until their meaning is normalized.
- `0M` warranty is correctly treated as no warranty label, not as missing data.

## Canonical Field Mapping

| True Value field | Canonical field | Status |
| --- | --- | --- |
| sku | `source_listing_id` | required |
| urlKey | `listing_url` | required |
| make_year | `model_year`, `manufacture_year` | required/optional |
| car_model | `model` | required |
| car_variant | `variant` | high value |
| price.final.amount.value | `listed_price_inr` | required |
| distance_driven | `km_driven` | required |
| fuel_type | `fuel_type` | required |
| transmission_type | `transmission` | required |
| ownership | `ownership` | high value |
| rto | `registration_code`, `registration_state`, `registration_type` | high value |
| registration_date | `registration_year` | optional |
| dealer_location | `locality`, `hub_name` | high value |
| dealer_name | `dealer_name` | optional |
| body_type | `body_type` | optional |
| color | `color` | optional |
| true_value_certified | `is_certified` | high value |
| dms_certification_status | `inspection_status` when not certified | optional |
| warranty_info | `warranty_label` | optional |
| overall_rating and component ratings | `extra_fields.true_value` | source specific |

## Known Gaps And Blind Spots

True Value is strong, but not perfect.

- It is Maruti-only, so it can bias the model if overrepresented.
- The active row count changes with live inventory; Hyderabad moved from about 250 to 247 during same-day checks.
- Inventory depends on latitude, longitude, dealer radius, and discovered dealers.
- Certification fields are source-specific and need meaning before model use.
- Warranty codes need interpretation: `1Y`, `6M`, and `0M` are not the same as free text.
- Color can be missing on a small number of rows.
- DMS certification status can be missing on a small number of rows.
- Dealer contact or phone fields should not be collected for the model dataset.
- Price intelligence still needs source provenance because an OEM-certified Maruti price may not be directly equivalent to a multi-brand marketplace price.

## Decision For Scaling

True Value is ready for controlled acquisition batches.

Recommended next sequence:

1. Use `docs/27-three-source-field-comparison.md` as the current trusted-source baseline.
2. Build a resumable batch runner instead of manually running one command at a time.
3. Start with Hyderabad for all three validated sources.
4. Then expand by city/source batches with manifests and quality gates.

Validated live target:

```text
source: true_value
city: Hyderabad
min_records: 40 passed
detail_pages: 0
required_completeness: 100%
high_value_completeness: 100%
pricing_ready: 40/40
known_remaining_gap: Maruti-only source bias, optional color and DMS gaps
```
