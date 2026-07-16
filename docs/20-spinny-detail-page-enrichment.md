# Spinny Detail Page Enrichment

Date: 2026-06-24

Purpose: enrich listing-card captures with high-value fields that are visible only on public detail pages.

## Why This Step Exists

The Spinny listing-card workflow already produces pricing-ready rows, but the field profile shows important gaps:

- ownership,
- manufacture year,
- registration year,
- inspection status,
- warranty label,
- return policy label,
- service due text,
- insurance fields.

These fields matter for price intelligence because two cars with the same model year, variant, fuel, transmission,
and kilometers can still have different fair prices depending on owner count, warranty coverage, inspection state,
and condition signals.

## Public Detail Fields Observed

The first detail-page inspection found stable labels in the `Car Overview` section:

- `Make Year`
- `Registration Year`
- `Fuel Type`
- `Km driven`
- `Transmission`
- `No. of Owner`
- `Insurance Validity`
- `Insurance Type`
- `RTO`
- `Car Location`

The same public page also exposes quality and benefit signals:

- `Quality report`
- parts-evaluated summary,
- component quality scores,
- `Next service due ...`,
- warranty label,
- money-back return policy label.

## Implementation

Added acquisition helpers:

- `build_spinny_payload_from_card_snapshots`
- `parse_spinny_detail_text`
- `capture_spinny_detail_payload`
- `merge_spinny_detail_payload_into_listing_payload`

Changed card capture:

- listing cards now preserve the first detail-page anchor as `raw.listing_url`.

Changed canonical adapter mapping:

- `ownership` is parsed from detail `No. of Owner`,
- `manufacture_year` is parsed from detail `Make Year`,
- `registration_year` is parsed from detail `Registration Year`,
- `registration_code` can use detail `RTO`,
- `inspection_status` maps to `quality_report_available`,
- warranty and return-policy labels map to canonical optional fields,
- insurance, quality score details, inspection summary, and service due text are stored under `extra_fields.spinny_detail`.

Changed live smoke command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24_detail_retry.json --captured-at 2026-06-24T07:25:00Z --run-id run_20260624_spinny_detail_smoke_retry --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --timeout-ms 60000 --detail-pages 3 --detail-delay-ms 3000 --json
```

`--detail-pages N` keeps enrichment bounded. The default remains `0`, so the original listing-card smoke workflow
still works unchanged.

Policy controls:

- `--detail-pages`: maximum number of detail pages to enrich in this run.
- `--detail-attempts`: attempts per detail page before marking that page failed.
- `--detail-delay-ms`: wait time before reading detail-page text.
- `--timeout-ms`: browser navigation/read timeout.

Policy behavior:

- The command records per-detail-page `capture_status`, `attempts`, and `failure_reason`.
- Detail enrichment is considered healthy only when every attempted detail page captures the required enrichment
  field, currently `ownership`.
- If detail enrichment is requested and fails, the smoke command writes the detail payload, merged payload, and
  smoke report, then stops before canonical raw/silver/gold listing outputs.
- This prevents a run from looking successful while enrichment silently failed.

## Live Verification

Latest bounded detail smoke run:

- listing-card records: 20,
- requested detail pages: 3,
- captured detail pages: 3,
- payload validation: pass,
- enriched payload validation: pass,
- pricing-ready records: 20,
- quarantined records: 0,
- required completeness: 100.00%,
- high-value completeness: 87.85%,
- optional completeness: 25.66%,
- ownership completeness improved from 0/20 to 3/20.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_20260624_spinny_detail_smoke_retry_smoke_report.md
```

Latest policy smoke run after adding failure accounting:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24_detail_policy.json --captured-at 2026-06-24T07:45:00Z --run-id run_20260624_spinny_detail_policy_smoke --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --timeout-ms 60000 --detail-pages 3 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- attempted detail pages: 3,
- successful detail pages: 3,
- failed detail pages: 0,
- ownership records: 3,
- retries used: 0,
- timeouts: 0,
- pricing-ready records: 20,
- quarantined records: 0.

Generated policy report:

```text
data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_20260624_spinny_detail_policy_smoke_smoke_report.md
```

## Full First-Page Enrichment

After the bounded policy smoke passed for 3 detail pages, the same policy was run against all 20 current listing
cards from the page.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24_detail_all20.json --captured-at 2026-06-24T08:05:00Z --run-id run_20260624_spinny_detail_all20_smoke --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --timeout-ms 60000 --detail-pages 20 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- attempted detail pages: 20,
- successful detail pages: 20,
- failed detail pages: 0,
- ownership records: 20,
- retries used: 0,
- timeouts: 0,
- invalid URLs: 0,
- pricing-ready records: 20,
- quarantined records: 0,
- required completeness: 100.00%,
- high-value completeness: 100.00%,
- optional completeness: 39.67%,
- overall completeness: 93.97%.

Generated full-page detail report:

```text
data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_20260624_spinny_detail_all20_smoke_smoke_report.md
```

Decision: full detail enrichment is stable enough for the current first page. The next acquisition step should be
pagination with strict page/detail caps, not ML/dashboard work.

## Full Sixty-Row Enrichment

After three-batch listing pagination passed, detail enrichment was scaled to all 60 listing rows while keeping the
listing volume fixed.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page3_detail60_min60.json --captured-at 2026-06-25T06:45:00Z --run-id run_20260625_spinny_page3_detail60_min60_smoke --capture-date 2026-06-25 --max-pages 3 --max-records 60 --min-records 60 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --detail-pages 60 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- listing records: 60,
- detail pages requested: 60,
- detail pages attempted: 60,
- detail pages successful: 60,
- detail pages failed: 0,
- ownership records: 60,
- retries used: 0,
- timeouts: 0,
- pricing-ready records: 60,
- quarantined records: 0,
- required completeness: 100.00%,
- high-value completeness: 100.00%,
- optional completeness: 39.83%,
- overall completeness: 93.98%.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_detail60_min60_smoke_smoke_report.md
```

Decision: the detail-page enrichment path is stable for the current 60-row Spinny baseline. Before increasing row
volume, add explicit run manifests and acquisition metrics so repeated runs can be compared over time.

## Decision

Detail-page enrichment works and should be scaled carefully.

Do not jump directly from 3 detail pages to broad crawling. The bounded batch policy is now:

- cap detail pages per run,
- record per-page timeout and retry metrics,
- record detail capture failures separately,
- make ownership completeness a monitored high-value metric,
- fail closed before canonical outputs when requested detail enrichment fails,
- keep quality scores as source-specific extras until a clean cross-source condition schema exists.

## Current Remaining Gaps

- Ownership is complete for the fully enriched first page, but not for future paginated rows unless detail enrichment also runs there.
- Warranty extraction can vary by page layout.
- Detail-page condition scores are source-specific and should not be treated as a universal inspection score yet.
- Accident history and service history are still not safely canonicalized from Spinny detail text.
