# True Value 5-City Fast Collection Run

Date: 2026-06-25

Purpose: prove the fastest trusted-source collection path before running browser-heavy Mahindra First Choice and Spinny batches.

## Decision

Execute True Value first because it uses dealer discovery plus GraphQL and does not require browser page rendering for every city.

Hyderabad was already validated, so the batch used resume/skip behavior to avoid rerunning it.

## Command

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id true_value_hyderabad_40 --batch-id true_value_bengaluru_100 --batch-id true_value_delhi_ncr_100 --batch-id true_value_mumbai_100 --batch-id true_value_chennai_100 --capture-date 2026-06-25 --batch-run-id batch_20260625_true_value_5city_fast_execute --skip-passed --execute --json
```

## Result

Final batch status:

```text
pass
```

Batch manifest:

```text
data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_true_value_5city_fast_execute_batch_manifest.json
```

Batch summary:

```text
data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_true_value_5city_fast_execute_batch_summary.md
```

## Row Results

| City | Batch | Pricing Ready | Quarantined | Source Total Observed | Required | High Value |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Hyderabad | `true_value_hyderabad_40` | 40 | 0 | 247 | 100.00% | 100.00% |
| Bengaluru | `true_value_bengaluru_100` | 100 | 0 | 221 | 100.00% | 100.00% |
| Delhi NCR | `true_value_delhi_ncr_100` | 100 | 0 | 617 | 100.00% | 100.00% |
| Mumbai | `true_value_mumbai_100` | 100 | 0 | 311 | 100.00% | 100.00% |
| Chennai | `true_value_chennai_100` | 89 | 0 | 95 | 100.00% | 100.00% |

Total pricing-ready rows:

```text
429
```

Total quarantined rows:

```text
0
```

## Data Problems Found During Scaling

### 1. Unavailable Inventory

Bengaluru initially returned one active payload row with `inStock=false`.

Fix:

- skip unavailable products before canonical conversion,
- record `unavailable_rows_skipped` in listing capture metrics.

### 2. Missing Pricing-Critical Product Fields

Delhi NCR returned one active product missing model and variant.

Fix:

- skip products missing required listing fields before payload validation,
- record `incomplete_rows_skipped` in listing capture metrics.

### 3. Odometer Outliers

Chennai returned rows with extreme odometer values:

```text
304,687 km
908,653 km
```

The gold quality gate correctly rejected them because they produced low parse confidence or invalid km warnings.

Fix:

- skip True Value rows above the pricing-ready odometer ceiling before canonical conversion,
- record `km_outlier_rows_skipped` in listing capture metrics.

## Why This Matters

This run proved the right production behavior:

- source-specific row filters are needed before gold outputs,
- batch resume avoids rerunning passed cities,
- a strict gold gate is useful because it caught real source defects,
- 100-row city batches are realistic for True Value in major cities,
- smaller cities or smaller dealer networks may return fewer than the requested maximum, as Chennai returned 89 pricing-ready rows after filters.

## Current True Value Scale Signal

Observed source totals in the 5-city run:

```text
Hyderabad: 247
Bengaluru: 221
Delhi NCR: 617
Mumbai: 311
Chennai: 95
```

Total observed active/source-side inventory signal:

```text
1,491 listings across 5 city-radius queries
```

This reinforces the 100k plan:

- True Value is a fast bulk source,
- it is not enough by itself for 100k current unique rows,
- it is very useful for repeated clean market observations.

## Next Step

Run Mahindra First Choice planned city batches next because it is the next fastest structured path.

Do not run Spinny detail-heavy batches until MFC multi-city behavior is understood.
