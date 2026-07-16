# Mahindra First Choice Source Evaluation

Date: 2026-06-25

Source URL: <https://www.mahindrafirstchoice.com/used-cars/hyderabad>

## Decision

Mahindra First Choice is approved as the second trusted source candidate after Spinny.

MFC should stay separate from Spinny at the acquisition, payload, adapter, smoke-command, and source-contract layers. It should merge with other sources only after canonicalization into the shared listing schema.

The first implementation scope is structured listing acquisition only. Detail-page enrichment is deferred because the current MFC listing flow already exposes enough structured data for pricing-ready rows, while detail pages behave differently from Spinny and should not be forced into the same code path.

## Why This Source Fits

Mahindra First Choice is a controlled dealer/certified inventory source, not an open classified source. That makes it better aligned with the first model-training dataset than customer self-listed sources.

Observed source positioning:

- certified used cars,
- multi-brand inventory,
- dealer-backed inventory,
- pricing guide / confidence messaging,
- warranty, buyback, return, and finance messaging.

This does not make the data perfect, but it does make the listed price closer to a platform/dealer market price than a random customer-entered asking price.

## Current Hyderabad Page Evidence

The Hyderabad listing page currently exposes 88 certified used cars in search output.

Visible listing-card fields:

- MFC rating / score,
- title with year, brand, and model,
- variant details,
- kilometers driven,
- fuel type,
- transmission,
- listed price,
- optional EMI,
- locality,
- request-call-back action.

Structured listing payload fields observed through the public page and browser pagination flow:

- listing id,
- title,
- price,
- kilometer reading,
- fuel type,
- transmission,
- ownership,
- body type,
- color,
- dealer name,
- locality,
- optional EMI,
- listing posted date,
- warranty label,
- registration number where available.

Visible filters:

- price range,
- brand and model,
- body type,
- manufactured year,
- kilometers driven,
- fuel type,
- transmission,
- ownership.

Important difference from Spinny:

- Spinny acquisition currently uses rendered listing cards, infinite scroll, and optional detail-page enrichment.
- MFC page 1 data comes from the Next.js `__NEXT_DATA__` state.
- MFC pagination uses browser-triggered XHR responses from the `carandbike.com` API path.
- Direct API calls without the frontend browser context returned an authorization failure during testing, but the normal website flow loaded page 2 and page 3 correctly in browser XHR.
- MFC structured rows include ownership, body type, color, dealer, warranty, and posted-date fields without visiting detail pages.
- Registration is partial: present where the structured row exposes a registration number, missing otherwise.
- MFC rating remains source-specific and should not be mixed with Spinny inspection fields.

## Why MFC Must Stay Separate From Spinny

Keep these source-specific layers separate:

- acquisition module,
- raw payload contract,
- adapter mapping,
- live smoke command,
- retry and pagination policy,
- source-specific evidence docs.

Use shared layers only after source-specific extraction succeeds:

- canonical listing schema,
- parser library,
- validation and quarantine,
- storage partitions,
- quality profile,
- smoke reports,
- run manifests,
- gold pricing-ready outputs.

This avoids forcing one source's website mechanics onto another. Spinny and MFC may both produce trusted used-car rows, but they do not produce those rows in the same technical shape.

## Canonical Field Mapping

| MFC card field | Canonical field | Status |
| --- | --- | --- |
| title | `model_year`, `brand`, `model` | required |
| variant segment | `variant` | high value |
| km segment | `km_driven` | required |
| fuel segment | `fuel_type` | required |
| transmission segment | `transmission` | required |
| price | `listed_price_inr` | required |
| EMI text | `emi_amount_inr`, `finance_label` | optional |
| locality | `locality`, `hub_name` | high value |
| owner | `ownership` | high value |
| registration_number | `registration_code`, `registration_state`, `registration_type` | high value, partial |
| body_type | `body_type` | optional |
| color | `color` | optional |
| dealer_name | `dealer_name` | optional |
| posted_on | `listing_posted_at` | optional |
| warranty | `warranty_label` | optional |
| MFC score | `extra_fields.mahindra_first_choice.rating_score` | source specific |
| certified source | `seller_type=dealer`, `is_certified=true` | high value |

Do not map MFC score directly to the global `inspection_score` yet. It may not be equivalent to Spinny inspection scoring or OEM certification scoring.

## Fixture Contract

Added fixture:

```text
tests/fixtures/mahindra_first_choice/listing_cards_extracted.json
```

Fixture coverage:

- 9 listing-card examples,
- Mahindra SUV records,
- Maruti hatchback records,
- Hyundai and Honda examples,
- manual, automatic, and AMT transmissions,
- optional EMI rows,
- locality variation.

Added adapter:

```text
src/used_car_price_intelligence/adapters/mahindra_first_choice.py
```

The payload contract requires:

```text
score
title
variant_details
price
locality
```

The `variant_details` text must contain four pipe-separated segments:

```text
variant | km | fuel | transmission
```

## Offline Fixture Validation Result

Command:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source mahindra_first_choice --captured-at 2026-06-25T03:30:00Z --run-id run_20260625_mfc_fixture_cli_check --json
```

Result:

- Records: 9.
- Silver-valid: 9.
- Pricing-ready: 9.
- Quarantined: 0.
- Required completeness: 100.00%.
- High-value completeness: 71.43%.
- Optional completeness: 16.29%.
- Overall completeness: 85.92%.

Known fixture field gap:

- `ownership`: 0/9.
- `registration_code`: 0/9.

This was acceptable for the first hand-built listing-card fixture because those two fields were not visible in the card text captured manually.

The live structured payload is better than the manual visible-card fixture: ownership is present in structured rows, and registration is present for a subset of rows.

## Live Hyderabad Smoke Result

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli mfc-live-smoke --payload-output data/tmp/mfc_live_smoke_payload_2026-06-25_hyderabad_40.json --captured-at 2026-06-25T09:10:00Z --run-id run_20260625_mfc_hyderabad_40_smoke --capture-date 2026-06-25 --city Hyderabad --state Telangana --max-pages 2 --max-records 40 --min-records 40 --capture-attempts 3 --retry-delay-ms 2000 --page-scroll-delay-ms 2500 --timeout-ms 60000 --json
```

Result:

- Listing records: 40.
- Source total items observed: 88.
- Source max page observed: 3.
- Unique cards seen during browser pagination: 88.
- Stop reason: `record_cap_reached`.
- Pricing-ready records: 40.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 91.78%.
- Optional completeness: 36.50%.
- Overall completeness: 92.01%.
- Ownership: 40/40.
- Registration code: 17/40.
- Detail pages: 0.

Generated outputs:

```text
data/raw/source=mahindra_first_choice/capture_date=2026-06-25/run_id=run_20260625_mfc_hyderabad_40_smoke/fixture_source_payload.json
data/silver/listings/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_silver.json
data/gold/quality_summary/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_quality_summary.json
data/gold/acquisition_runs/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_manifest.json
data/gold/smoke_reports/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_smoke_report.md
```

## Parser Improvements Triggered

MFC research and fixtures expanded parser coverage for:

- `S-Presso`,
- `BR-V`,
- `Tigor EV`,
- compact `Petrol+LPG`,
- `IMT`,
- `IVT`.

The `Tigor EV` model rule is important even if it is not in the current MFC fixture, because EV variants can have materially different pricing from their ICE model families.

## Next Engineering Step

The live MFC Hyderabad 40-row smoke is validated. The next source-specific MFC step is either:

- run the current visible Hyderabad inventory with a higher cap, likely `max_pages=3`, `max_records=88`, and a slightly lower `min_records` such as `80` because live inventory can change; or
- pause MFC scaling and add True Value source evaluation so the project has three trusted source contracts before larger batch collection.

Update: the True Value evaluation is now complete, and the current next step is batch-runner resume/skip behavior before executing all three validated Hyderabad batches together.

Validated live target:

```text
source: mahindra_first_choice
city: Hyderabad
min_records: 40 passed
detail_pages: 0
required_completeness: 100%
pricing_ready: 40/40
known_remaining_gap: partial registration_code
```

Do not require Spinny-level 100% high-value completeness for MFC unless registration coverage is solved through detail pages or another stable structured field. MFC can still be pricing-ready because the pricing-critical fields are complete.
