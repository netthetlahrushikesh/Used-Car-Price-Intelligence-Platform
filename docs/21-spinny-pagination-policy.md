# Spinny Pagination Policy

Date: 2026-06-25

Purpose: scale Spinny listing capture beyond the first visible card batch without allowing silent row under-capture.

## Decision

Spinny Hyderabad hub uses infinite scroll batches, not a normal next-page URL pattern.

For this project, a pagination "page" means one bounded scroll-loaded batch:

- page 1: initially visible listing cards,
- page 2: listing cards visible after one successful scroll batch,
- page N: the next successful scroll batch.

Pagination must stay bounded with explicit caps:

- `--max-pages`: maximum scroll batches to attempt,
- `--max-records`: maximum listing-card rows to return,
- `--min-records`: minimum parsed rows required for a smoke run to pass.

For `spinny-live-smoke`, `--min-records` defaults to `--max-records`. This is intentional. A smoke run should not pass when it was asked for 40 rows but silently captured only 22.

## Why This Matters

Field completeness alone is not enough.

A run can produce 100% complete rows and still be operationally wrong if the infinite-scroll loader only returned the first batch. That would bias market data toward the top of the page and hide coverage loss behind good-looking quality metrics.

The smoke workflow now has two separate gates:

1. Data quality gate: every captured row must be pricing-ready.
2. Listing coverage gate: captured parsed rows must meet `min_records`.

## Implementation

Changed Spinny live listing capture:

- added bounded infinite-scroll batch capture,
- deduplicated listing cards by normalized `listing_url`,
- preserved pagination metrics in the extracted payload,
- made scrolling more persistent by scrolling the last card into view, scrolling to document bottom, and using mouse-wheel movement,
- added `min_records` support to the acquisition function,
- retry capture attempts when the payload is valid but below the requested row floor.

Changed smoke reporting:

- smoke JSON and Markdown now include `listing_capture`,
- smoke JSON and Markdown now include `listing_coverage`,
- coverage failures write a smoke report but stop before canonical raw/silver/gold listing outputs.

Changed parser aliases:

- added `Jaguar -> XE` after a two-page run exposed `2018 Jaguar XE`,
- added `Lexus -> NX` after a two-page run exposed `2020 Lexus NX 300h Luxury`.

Both were added as controlled model-family aliases, not broad fuzzy matching.

## Command

Two-page listing-card smoke:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page2_cards_min40_retry.json --captured-at 2026-06-25T04:50:00Z --run-id run_20260625_spinny_page2_cards_min40_retry_smoke --capture-date 2026-06-25 --max-pages 2 --max-records 40 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --json
```

Two-page listing capture with detail enrichment capped to 20 detail pages:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page2_detail20_min40.json --captured-at 2026-06-25T05:05:00Z --run-id run_20260625_spinny_page2_detail20_min40_smoke --capture-date 2026-06-25 --max-pages 2 --max-records 40 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --detail-pages 20 --detail-attempts 2 --detail-delay-ms 3000 --json
```

## Verification

Card-only two-page smoke result:

- run ID: `run_20260625_spinny_page2_cards_min40_retry_smoke`,
- listing records: 40,
- minimum records required: 40,
- coverage gate: pass,
- payload validation: pass,
- pricing-ready records: 40,
- quarantined records: 0,
- required completeness: 100.00%,
- high-value completeness: 85.71%,
- optional completeness: 23.33%.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page2_cards_min40_retry_smoke_smoke_report.md
```

Two-page plus detail-capped smoke result:

- run ID: `run_20260625_spinny_page2_detail20_min40_smoke`,
- listing records: 40,
- minimum records required: 40,
- coverage gate: pass,
- detail pages requested: 20,
- detail pages attempted: 20,
- detail pages successful: 20,
- detail pages failed: 0,
- retries used: 0,
- timeouts: 0,
- ownership records: 20/40,
- payload validation: pass,
- enriched payload validation: pass,
- pricing-ready records: 40,
- quarantined records: 0,
- required completeness: 100.00%,
- high-value completeness: 92.85%,
- optional completeness: 31.42%,
- overall completeness: 91.72%.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page2_detail20_min40_smoke_smoke_report.md
```

## Failure Found And Fixed

First strict two-page run did capture 40 rows, but failed the quality gate:

- unknown brand/model: `2020 Lexus NX 300h Luxury`,
- result: 39 pricing-ready rows, 1 quarantined row.

The fix was a controlled alias addition:

- brand: `Lexus`,
- model family: `NX`.

This is a good example of why scaling live capture should happen in bounded batches. Each batch exposes real source vocabulary without allowing low-confidence parser behavior into the gold dataset.

## Current Policy

Use this progression before increasing scale:

1. Run card-only pagination with `--max-pages 2 --max-records 40`.
2. Fix only deterministic parser gaps exposed by quarantine.
3. Rerun until coverage and quality both pass.
4. Add detail enrichment with a smaller detail cap.
5. Monitor owner/detail coverage separately from listing-card coverage.
6. Increase one dimension at a time: either more scroll batches or more detail pages, not both.

## Next Step

The three-batch card-only milestone has now passed.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page3_cards_min60.json --captured-at 2026-06-25T05:35:00Z --run-id run_20260625_spinny_page3_cards_min60_smoke --capture-date 2026-06-25 --max-pages 3 --max-records 60 --min-records 60 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --json
```

Result:

- listing records: 60,
- minimum records required: 60,
- listing coverage: pass,
- attempted scroll batches: 3,
- unique listing URLs: 60,
- duplicate cards skipped: 64,
- payload validation: pass,
- pricing-ready records: 60,
- quarantined records: 0,
- required completeness: 100.00%,
- high-value completeness: 85.71%,
- optional completeness: 23.33%,
- overall completeness: 89.48%.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_cards_min60_smoke_smoke_report.md
```

Observed pagination metrics:

- batch 1 observed 22 cards,
- batch 2 observed 42 cards,
- batch 3 observed 62 cards,
- the capture returned 60 records because `--max-records` capped the run.

Next controlled acquisition step:

The 60-row, 30-detail-page milestone has now passed.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page3_detail30_min60.json --captured-at 2026-06-25T06:05:00Z --run-id run_20260625_spinny_page3_detail30_min60_smoke --capture-date 2026-06-25 --max-pages 3 --max-records 60 --min-records 60 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --detail-pages 30 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- listing records: 60,
- minimum records required: 60,
- listing coverage: pass,
- detail pages requested: 30,
- detail pages attempted: 30,
- detail pages successful: 30,
- detail pages failed: 0,
- retries used: 0,
- timeouts: 0,
- ownership records: 30/60,
- first-owner records among enriched rows: 17,
- second-owner records among enriched rows: 13,
- payload validation: pass,
- enriched payload validation: pass,
- pricing-ready records: 60,
- quarantined records: 0,
- required completeness: 100.00%,
- high-value completeness: 92.85%,
- optional completeness: 31.50%,
- overall completeness: 91.72%.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_detail30_min60_smoke_smoke_report.md
```

Next controlled acquisition step:

The 60-row, 60-detail-page milestone has now passed.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page3_detail60_min60.json --captured-at 2026-06-25T06:45:00Z --run-id run_20260625_spinny_page3_detail60_min60_smoke --capture-date 2026-06-25 --max-pages 3 --max-records 60 --min-records 60 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --detail-pages 60 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- listing records: 60,
- minimum records required: 60,
- listing coverage: pass,
- detail pages requested: 60,
- detail pages attempted: 60,
- detail pages successful: 60,
- detail pages failed: 0,
- retries used: 0,
- timeouts: 0,
- ownership records: 60/60,
- first-owner records: 42,
- second-owner records: 17,
- third-owner records: 1,
- payload validation: pass,
- enriched payload validation: pass,
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

Next controlled acquisition step:

- freeze this as the current trusted Spinny acquisition baseline,
- add run manifests / acquisition metrics before raising volume,
- then test four scroll batches card-only with a strict row floor.
