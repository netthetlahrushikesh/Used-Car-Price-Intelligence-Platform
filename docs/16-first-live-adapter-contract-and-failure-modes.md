# First Live Adapter Contract and Failure Modes

Date: 2026-06-24

Source: Spinny Hyderabad listing-card pages

First target URL:

```text
https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/
```

## Purpose

The first live adapter must not be a quick scraper. It should be a small, observable data acquisition component
that proves the source can produce complete pricing-ready listing-card rows without weakening the data contract.

The adapter has two separate responsibilities:

1. Capture or extract source listing-card fields.
2. Convert extracted fields into canonical records through the already-tested parser and quality pipeline.

Those responsibilities should stay separate. If live extraction changes, canonical normalization should not be
rewritten.

## Current Implementation Boundary

Implemented now:

- `SpinnyExtractedPayloadAdapter`
- `SpinnyFixtureAdapter`
- `validate_spinny_extracted_payload()`
- `validate-payload` CLI command
- `capture-spinny-live` CLI command

Not implemented yet:

- browser automation,
- network capture,
- selector extraction,
- pagination,
- scheduling,
- proxy rotation,
- login/CAPTCHA/anti-bot bypass.

This is intentional. The source payload contract comes before the live collector.

## Extracted Payload Contract

The live extractor must produce this shape before any parser runs:

```json
{
  "source": "spinny",
  "source_url": "https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/",
  "captured_for": "live_public_search_fixture",
  "fixture_created_at": "2026-06-24",
  "records": [
    {
      "raw": {
        "title": "2022 Kia Seltos",
        "price": "14.58 Lakh",
        "variant": "GTX Plus 1.5 Diesel AT Dual Tone",
        "emi": "EMI Rs 25,218/m*",
        "km": "58.5K km",
        "fuel": "diesel",
        "transmission": "automatic",
        "registration": "TS36",
        "locality": "Nexus Sujana Mall, Kukatpally"
      }
    }
  ]
}
```

Required payload-level fields:

- `source`
- `source_url`
- `records`

Required raw listing-card fields:

- `title`
- `price`
- `variant`
- `km`
- `fuel`
- `transmission`
- `registration`
- `locality`

Optional raw listing-card fields:

- `emi`
- `listing_url`
- `image_url`
- `original_price`
- `discount_label`
- `availability_label`

Validate a payload:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli validate-payload --source spinny --payload tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json --json
```

Expected current result:

```json
{
  "failures": [],
  "ok": true,
  "records_total": 20,
  "source": "spinny"
}
```

## Fail-Closed Rules

The adapter must stop before canonical conversion when:

- payload is not a JSON object,
- `source` is not `spinny`,
- `source_url` is missing,
- `records` is missing or not an array,
- `records` is empty,
- any record lacks a `raw` object,
- any required raw field is missing or empty.

Current failure object:

```json
{
  "record_index": 1,
  "field_name": "fuel",
  "reason": "missing_required_raw_field"
}
```

This prevents a live selector failure from silently becoming null-heavy canonical rows.

## Parser and Quality Expectations

The live adapter must reuse:

- `parse_title()`
- `parse_price_inr()`
- `parse_km_driven()`
- `parse_fuel_type()`
- `parse_transmission()`
- `parse_registration()`
- `evaluate_listing()`
- `run-fixture`
- `quality-report`
- `field-profile`

Expected smoke-test thresholds for the first live Spinny listing-card capture:

- at least 10 extracted listing records,
- 100% required raw-field completeness before parsing,
- 100% required canonical-field completeness after parsing,
- 0 quarantined records for the fixture smoke run,
- warnings allowed only when understood and documented, such as `multiple_price_candidates`.

## Known Current Gaps

Listing-card capture does not yet provide:

- ownership,
- inspection score,
- condition grade,
- accident history,
- service history,
- body type,
- color,
- listing lifecycle dates.

These are enrichment targets, not first-adapter blockers.

## First Live Collector Design

The first collector should:

- accept one source URL,
- capture one page only,
- write a raw extracted payload file first,
- run contract validation on the extracted payload,
- adapt the payload into canonical records,
- run quality evaluation,
- write raw, silver, quarantine, and quality summary outputs,
- render quality and field profile reports,
- stop on contract failure.

No pagination, scheduling, database loading, or ML should be added until this path is stable.

## Failure Modes to Test Before Scaling

Selector changed:

- Expected signal: missing required raw fields.
- Expected behavior: contract failure before canonical conversion.

Page returns no cards:

- Expected signal: empty records.
- Expected behavior: contract failure.

Discounted cards expose current and old prices:

- Expected signal: `multiple_price_candidates`.
- Expected behavior: keep first visible listed price and warn.

Unknown model family:

- Expected signal: `missing_model` or low parse confidence.
- Expected behavior: quarantine or parser fixture update after manual review.

New fuel/transmission label:

- Expected signal: unknown fuel or transmission.
- Expected behavior: quarantine until parser vocabulary is updated.

Unavailable/sold card appears:

- Expected signal: `is_available` false or source record type change.
- Expected behavior: quarantine from pricing-ready data.

## Next Implementation Step

Install the optional acquisition dependency when ready, then run `capture-spinny-live` to write an extracted
payload file. The first goal is to compare the newly captured payload against the existing 20-record fixture and
confirm that required raw fields are still extractable before connecting live capture to canonical output writes.
