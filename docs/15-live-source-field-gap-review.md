# Live Source Field Gap Review

Date: 2026-06-24

Source reviewed: `https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/`

Fixture: `tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json`

## Why This Step Exists

The project should not move from fixtures to live adapters just because one fixture passes.
Before writing live acquisition code, we need to know which canonical columns are actually supported by
listing-card data and which columns need detail pages, enrichment, or a different source.

## Command

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli field-profile --source spinny --fixture tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json --captured-at 2026-06-24T04:00:00Z --run-id run_20260624_spinny_live_fixture
```

## Result Summary

The 20-record live Spinny fixture has 100% completeness for all pricing-ready required fields:

- source and listing identity,
- capture metadata,
- city,
- brand,
- model,
- model year,
- listed price,
- kilometers driven,
- fuel type,
- transmission,
- currency,
- raw hash,
- run ID,
- parser version,
- schema version.

High-value fields:

- `variant`: 20/20,
- `registration_code`: 20/20,
- `locality`: 20/20,
- `seller_type`: 20/20,
- `is_certified`: 20/20,
- `is_available`: 20/20,
- `ownership`: 0/20.

Important optional fields currently missing from listing-card fixture data:

- manufacture year,
- registration year,
- body type,
- color,
- seating capacity,
- original price,
- discount amount,
- token amount,
- dealer name,
- inspection status and score,
- condition grade,
- accident history,
- service history,
- warranty label,
- return policy label,
- listing posted date,
- first-seen and last-seen dates.

## Interpretation

The current listing-card fixture is strong enough for a first pricing-ready MVP dataset, but not enough for a
full valuation-grade intelligence product.

The required pricing row can be complete, which satisfies the current 90-100% completeness goal for MVP columns.
However, the missing fields are exactly the columns that improve trust and explainability:

- ownership affects valuation,
- condition and accident history affect valuation,
- service history affects valuation,
- original price and discount fields affect price interpretation,
- first-seen and last-seen dates are needed for price-drop and inventory aging analysis.

## Decision

Do not expand the canonical required field list yet. Instead:

1. Keep the current required fields strict.
2. Treat `ownership`, condition, service history, and listing lifecycle fields as enrichment targets.
3. Build the first live adapter around listing-card extraction first.
4. Add detail-page enrichment only after listing-card capture is stable and measurable.

## First Live Adapter Contract

The first live adapter should:

- capture source URL, capture timestamp, run ID, and parser/schema versions,
- extract fields into isolated raw slots before parsing,
- never parse a full card blob when field-specific text is available,
- preserve raw fixture payloads under `data/raw`,
- write canonical valid rows under `data/silver/listings`,
- write rejected rows under `data/silver/quarantine`,
- write quality summaries under `data/gold/quality_summary`,
- emit warnings for `multiple_price_candidates`,
- avoid login, CAPTCHA, or anti-bot bypass,
- fail closed when required selectors or fields disappear.

## Next Step

Create a live adapter design note before coding browser/network acquisition. That note should define:

- input source URL,
- capture method,
- selector strategy,
- retry and timeout policy,
- required extracted fields,
- quarantine behavior,
- fixture refresh process,
- and the exact smoke test that proves the adapter did not silently break.
