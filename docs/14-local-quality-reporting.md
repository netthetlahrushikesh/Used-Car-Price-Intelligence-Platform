# Local Quality Reporting

This document records how local fixture quality runs are converted into a human-readable report.

## Purpose

The generated quality summary JSON is useful for automation, but it is not enough for project storytelling,
review, or debugging. Each run also needs a short operator-facing report that answers:

- did the run pass,
- how many records reached silver and pricing-ready quality,
- which fields are still weak,
- why any rows were quarantined,
- and whether warnings are increasing over time.

## Command

Generate local data-layer outputs:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source spinny --write --json
```

Render the saved quality summary:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli quality-report --summary data/gold/quality_summary/capture_date=2026-06-24/spinny_run_20260624_spinny_fixture_cli_quality_summary.json
```

## Status Rules

- `PASS`: records exist, every record is pricing-ready, no rows are quarantined, and required completeness is 100%.
- `WARN`: at least one row is pricing-ready, but the run has partial completeness or quarantine issues.
- `FAIL`: no records exist or no records are pricing-ready.

## Current Spinny Fixture Result

The first Spinny fixture run currently reports:

- status: `PASS`,
- records: 5 total,
- silver-valid: 5,
- pricing-ready: 5,
- quarantined: 0,
- required completeness: 100.00%,
- high-value completeness: 85.71%,
- optional completeness: 23.33%,
- warnings: none.

The live Hyderabad hub fixture currently reports:

- status: `PASS`,
- records: 20 total,
- silver-valid: 20,
- pricing-ready: 20,
- quarantined: 0,
- required completeness: 100.00%,
- high-value completeness: 85.71%,
- optional completeness: 23.33%,
- warnings: `multiple_price_candidates: 2`.

## Decision

This report becomes the default checkpoint before moving from offline fixtures to any live source capture.
If the report starts showing quarantine reasons or lower required completeness, the parser/schema layer must be
fixed before the project scales to more sources.
