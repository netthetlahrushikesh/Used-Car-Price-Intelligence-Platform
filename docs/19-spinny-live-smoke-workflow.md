# Spinny Live Smoke Workflow

Date: 2026-06-24

Purpose: run one public Spinny listing page through the complete acquisition quality path.

## Command

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24.json --captured-at 2026-06-24T05:45:00Z --run-id run_20260624_spinny_live_smoke --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --json
```

The command writes a Markdown smoke report by default under:

```text
data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_20260624_spinny_live_smoke_smoke_report.md
```

Use `--report-output path/to/report.md` to override that location.

Bounded detail-page enrichment can be enabled with `--detail-pages`:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24_detail_all20.json --captured-at 2026-06-24T08:05:00Z --run-id run_20260624_spinny_detail_all20_smoke --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --timeout-ms 60000 --detail-pages 20 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Bounded infinite-scroll pagination can be enabled with `--max-pages`. For `spinny-live-smoke`, `--min-records`
defaults to `--max-records`, so row under-capture fails the smoke run even when the captured rows are clean:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page2_cards_min40_retry.json --captured-at 2026-06-25T04:50:00Z --run-id run_20260625_spinny_page2_cards_min40_retry_smoke --capture-date 2026-06-25 --max-pages 2 --max-records 40 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --json
```

## Workflow

The command performs this sequence:

1. Capture one public Spinny listing page with Playwright.
2. Write the extracted payload under `data/tmp/`.
3. Validate the extracted payload contract.
4. Stop before canonical conversion if validation fails.
5. Stop before canonical conversion if the listing coverage floor is not met.
6. Convert valid payload rows into canonical listings.
7. Run quality gates.
8. Write raw, silver, quarantine, and gold quality-summary outputs.
9. Build field-level completeness profile.
10. Persist a compact Markdown smoke report.
11. Return nonzero if the smoke result is not fully pricing-ready.

When `--detail-pages N` is greater than zero, the command also:

1. preserves listing-card detail URLs,
2. captures up to `N` public detail pages,
3. parses owner count, make/registration year, RTO, inspection status, warranty, and return-policy labels,
4. merges detail fields into the listing-card payload,
5. validates the enriched payload before canonical conversion,
6. stops before canonical outputs if requested detail enrichment fails.

## Current Result

Current full-detail Spinny baseline:

- payload validation: pass,
- extracted records: 60,
- listing coverage: pass, minimum 60,
- detail pages successful: 60/60,
- silver-valid: 60,
- pricing-ready: 60,
- quarantined: 0,
- required completeness: 100.00%,
- high-value completeness: 100.00%,
- optional completeness: 39.83%,
- warnings: none.

Output paths:

```text
data/tmp/spinny_live_smoke_payload_2026-06-25_page3_detail60_min60.json
data/raw/source=spinny/capture_date=2026-06-25/run_id=run_20260625_spinny_page3_detail60_min60_smoke/fixture_source_payload.json
data/silver/listings/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_detail60_min60_smoke_silver.json
data/silver/quarantine/source=spinny/capture_date=2026-06-25/run_20260625_spinny_page3_detail60_min60_smoke_quarantine.json
data/gold/quality_summary/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_detail60_min60_smoke_quality_summary.json
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_detail60_min60_smoke_smoke_report.md
```

Earlier two-page capture with detail enrichment capped to 20 detail pages:

- listing records: 40,
- listing coverage: pass, minimum 40,
- detail pages requested: 20,
- detail pages successful: 20,
- detail pages failed: 0,
- ownership records: 20/40,
- pricing-ready: 40,
- quarantined: 0,
- required completeness: 100.00%,
- high-value completeness: 92.85%,
- optional completeness: 31.42%,
- overall completeness: 91.72%.

## Stop Conditions

The command returns nonzero when:

- browser capture cannot run,
- extracted payload contract fails,
- listing coverage is below `--min-records`,
- zero records are captured,
- not every captured row is pricing-ready,
- any row is quarantined,
- required completeness is below 100%.

When the payload contract or listing coverage gate fails, the command still writes the Markdown smoke report but
does not write canonical raw, silver, quarantine, or quality-summary outputs.

## Why This Matters

This command is the first production-style acquisition checkpoint in the project. It proves that the live source
can produce pricing-ready rows without manual editing, while still preserving the fail-closed behavior needed to
avoid silent data corruption.

## Next Step

The smoke run is now reproducible, operator-readable, can capture three infinite-scroll batches with a strict row
floor, and can enrich all 60 captured detail rows. The next decision is whether to:

- add persisted source-run manifests and acquisition metrics,
- test four Spinny scroll batches card-only,
- or add a second trusted source for source-bias comparison.
