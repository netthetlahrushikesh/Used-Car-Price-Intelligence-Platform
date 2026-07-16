# First Live Capture Run

Date: 2026-06-24

Source URL:

```text
https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/
```

## Goal

Run the first bounded one-page live capture, validate the extracted payload, and only then write canonical
raw/silver/quarantine/gold outputs.

## Environment Setup

Created a local `.venv` and installed the optional acquisition dependency:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[acquisition]"
.venv\Scripts\python -m playwright install chromium
```

The first `pip install -e ".[acquisition]"` attempt backtracked and failed while resolving Playwright and
`greenlet`. Installing `greenlet` first resolved the dependency path, then the acquisition install succeeded.

## First Capture Attempt

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli capture-spinny-live --output data/tmp/spinny_live_payload_2026-06-24.json --captured-at 2026-06-24T05:00:00Z --max-records 20 --json
```

Result:

```json
{
  "ok": false,
  "records_total": 20,
  "source": "spinny",
  "failures": [
    {
      "record_index": 7,
      "field_name": "variant",
      "reason": "missing_required_raw_field"
    }
  ]
}
```

## Root Cause

Record 7 was:

```text
2023 Skoda Slavia
13.29 Lakh
Style 1.0L TSI AT
EMI Rs 22,972/m*
21K km
Petrol
Automatic
TS07
```

The extractor incorrectly treated `Style 1.0L TSI AT` as a price-like line because of the engine-size token
`1.0L`. That caused the variant to be skipped and the payload contract to fail.

## Fix

Changed live-card price-line detection so listing-card extraction treats price lines as `Lakh`, `Lac`, `Cr`, or
`Crore`, but does not classify bare `L` engine-size tokens as prices.

Added a regression test for:

```text
Style 1.0L TSI AT
```

## Model Vocabulary Updates

The successful live capture introduced or confirmed these model-family aliases:

- `BYD Seal`
- `Mahindra Scorpio N`
- `Jeep Compass`
- `Tata Harrier`
- `Skoda Octavia`
- `BMW X1`
- `Mercedes-Benz GLC`
- `Audi Q3`

These were added to explicit parser model dictionaries instead of relying on fallback inference.

## Successful Capture

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli capture-spinny-live --output data/tmp/spinny_live_payload_2026-06-24_validated.json --captured-at 2026-06-24T05:20:00Z --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --json
```

Result:

```json
{
  "failures": [],
  "ok": true,
  "records_total": 20,
  "source": "spinny"
}
```

## Canonical Output Run

Command:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source spinny --fixture data/tmp/spinny_live_payload_2026-06-24_validated.json --captured-at 2026-06-24T05:20:00Z --run-id run_20260624_spinny_live_capture --capture-date 2026-06-24 --write --json
```

Result:

- records total: 20,
- silver-valid: 20,
- pricing-ready: 20,
- quarantined: 0,
- required completeness: 100.00%,
- high-value completeness: 85.71%,
- optional completeness: 23.33%,
- warnings: none.

Output paths:

```text
data/raw/source=spinny/capture_date=2026-06-24/run_id=run_20260624_spinny_live_capture/fixture_source_payload.json
data/silver/listings/capture_date=2026-06-24/spinny_run_20260624_spinny_live_capture_silver.json
data/silver/quarantine/source=spinny/capture_date=2026-06-24/run_20260624_spinny_live_capture_quarantine.json
data/gold/quality_summary/capture_date=2026-06-24/spinny_run_20260624_spinny_live_capture_quality_summary.json
```

## Field Profile

Required fields stayed at 20/20.

Known gaps remain:

- `ownership`: 0/20,
- condition and inspection fields: 0/20,
- service history and accident history: 0/20,
- lifecycle dates: 0/20.

## Decision

The live listing-card path is now proven for one page. The next step should not be ML or dashboard work yet.

Follow-up completed: `spinny-live-smoke` now performs capture, payload validation, canonical output writing,
quality summary generation, and field profiling in one controlled command.

Additional follow-up completed: each smoke run now writes a compact Markdown smoke report. Payload contract
failures still stop before canonical conversion, but they also produce a readable failure report.
