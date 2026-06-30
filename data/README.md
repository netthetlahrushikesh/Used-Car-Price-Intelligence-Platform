# Data Directory

Production and large local data files are not committed to Git.

Expected local layout:

```text
data/
  raw/      immutable source captures
  bronze/   source-normalized records
  silver/   validated canonical listings
  gold/     aggregates, feature tables, model datasets
  tmp/      disposable intermediate files
```

Each data file must be reproducible from a recorded run configuration and source metadata.

Fixture-mode outputs are written with partition-style paths, for example:

```text
data/raw/source=spinny/capture_date=2026-06-24/run_id=.../fixture_source_payload.json
data/silver/listings/capture_date=2026-06-24/spinny_..._silver.json
data/silver/quarantine/source=spinny/capture_date=2026-06-24/..._quarantine.json
data/gold/quality_summary/capture_date=2026-06-24/spinny_..._quality_summary.json
```

Run:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source spinny --write
```

Inspect the generated quality summary:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli quality-report --summary data/gold/quality_summary/capture_date=2026-06-24/spinny_run_20260624_spinny_fixture_cli_quality_summary.json
```

Temporary live-capture payloads should be written under `data/tmp/` and validated before canonical conversion.

The controlled Spinny live smoke workflow writes:

```text
data/tmp/spinny_live_smoke_payload_2026-06-24.json
data/raw/source=spinny/capture_date=2026-06-24/run_id=run_20260624_spinny_live_smoke/fixture_source_payload.json
data/silver/listings/capture_date=2026-06-24/spinny_run_20260624_spinny_live_smoke_silver.json
data/silver/quarantine/source=spinny/capture_date=2026-06-24/run_20260624_spinny_live_smoke_quarantine.json
data/gold/quality_summary/capture_date=2026-06-24/spinny_run_20260624_spinny_live_smoke_quality_summary.json
```
