# Batch Runner Foundation

Date: 2026-06-25

## Decision

Add a batch runner before scaling data collection.

Manual one-off commands were useful for proving Spinny, Mahindra First Choice, and True Value. They are not enough for source-city acquisition at project scale because they do not give a single place to plan jobs, inspect commands, write batch manifests, and execute controlled subsets.

## What Was Added

Batch runner module:

```text
src/used_car_price_intelligence/pipeline/batch_runner.py
```

CLI command:

```text
run-batches
```

Config source:

```text
config/acquisition_batches.yml
```

Dry-run manifest location:

```text
data/gold/batch_runs/capture_date=YYYY-MM-DD/
```

## Safety Model

`run-batches` is plan-only by default.

It writes a batch manifest and does not touch live websites unless `--execute` is provided.

This prevents accidental long-running collection when the user only wants to inspect planned commands.

## Current Validated Hyderabad Batch Plan

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --status validated --capture-date 2026-06-25 --batch-run-id batch_20260625_validated_hyderabad_dry_run --json
```

Result:

- Status: `planned`.
- Job count: 3.
- Jobs:
  - `spinny_hyderabad_60_detail60`
  - `mfc_hyderabad_40`
  - `true_value_hyderabad_40`

Manifest:

```text
data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_validated_hyderabad_dry_run_batch_manifest.json
```

## Planned Commands

The runner builds source-specific smoke commands from the config.

Spinny:

```text
spinny-live-smoke
```

Mahindra First Choice:

```text
mfc-live-smoke
```

True Value:

```text
true-value-live-smoke
```

Each planned job gets:

- batch id,
- source,
- city and state,
- source URL,
- generated run id,
- payload output path,
- complete command list,
- planned job status.

## Why This Matters

This is the transition from source proving to controlled data collection.

The validated source contracts are now:

| Source | Validated Hyderabad target |
| --- | --- |
| Spinny | 60 rows with 60 detail pages |
| Mahindra First Choice | 40 rows |
| True Value | 40 rows |

The runner gives one operator surface for those jobs.

## Current Limitations

This started as batch-runner v0.1. It could plan jobs, write manifests, and execute jobs when explicitly requested.

Current update:

- resume already-passed jobs from an existing batch manifest is implemented through `--resume-from-manifest`,
- skip passed jobs from the target manifest is implemented through `--skip-passed`,
- batch-level Markdown summary output is implemented,
- source-city throttling windows are still pending,
- per-job retry policy at the batch level is still pending,
- scheduled execution is still pending.

## Next Step

Use dry-run mode first for every new batch set.

Safe execution proof:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id true_value_hyderabad_40 --capture-date 2026-06-25 --batch-run-id batch_20260625_true_value_execute_check --execute --json
```

Result:

- Batch status: `pass`.
- Job count: 1.
- Batch id: `true_value_hyderabad_40`.
- Job exit code: 0.
- Job run id: `run_20260625_true_value_hyderabad_40_batch_20260625_true_value_execute_check`.
- Pricing-ready records from nested smoke run: 40/40.
- Quarantine rows from nested smoke run: 0.

Batch manifest:

```text
data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_true_value_execute_check_batch_manifest.json
```

Nested source-run manifest:

```text
data/gold/acquisition_runs/capture_date=2026-06-25/true_value_run_20260625_true_value_hyderabad_40_batch_20260625_true_value_execute_check_manifest.json
```

Next engineering task:

```text
run the 5-city planned batch dry run, then execute fast structured sources first
```

## Resume And Summary Commands

Resume from a prior manifest:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id true_value_hyderabad_40 --capture-date 2026-06-25 --batch-run-id batch_resume_example --resume-from-manifest data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_true_value_execute_check_batch_manifest.json --execute --json
```

Skip passed jobs when rerunning the same target manifest:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --status planned --capture-date 2026-06-25 --batch-run-id batch_20260625_five_city_planned --skip-passed --execute --json
```

The runner now writes:

```text
data/gold/batch_runs/capture_date=YYYY-MM-DD/<batch_run_id>_batch_manifest.json
data/gold/batch_runs/capture_date=YYYY-MM-DD/<batch_run_id>_batch_summary.md
```

The summary report rolls up job status, pricing-ready rows, quarantine rows, source total rows when present, and completeness metrics when nested source-run manifests exist.
