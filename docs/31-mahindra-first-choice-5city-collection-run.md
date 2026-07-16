# Mahindra First Choice 5-City Collection Run

Date: 2026-06-26

Purpose: run the second structured trusted source across the same first-city set after True Value passed the fast 5-city path.

## Decision

Run Mahindra First Choice before Spinny multi-city detail enrichment.

Reason:

- MFC is structured through Next.js page data plus browser-triggered XHR pagination.
- It is multi-brand, unlike True Value.
- It is browser-backed, but still lighter than Spinny full detail-page enrichment.

## Command

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id mfc_hyderabad_40 --batch-id mfc_bengaluru_80 --batch-id mfc_delhi_ncr_80 --batch-id mfc_mumbai_80 --batch-id mfc_chennai_80 --capture-date 2026-06-26 --batch-run-id batch_20260626_mfc_5city_execute --skip-passed --execute --json
```

## Result

Final batch status:

```text
pass
```

Batch manifest:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5city_execute_batch_manifest.json
```

Batch summary:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5city_execute_batch_summary.md
```

## Row Results

| City | Batch | Pricing Ready | Quarantined | Source Total Observed | Coverage Reason | Required | High Value |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| Hyderabad | `mfc_hyderabad_40` | 40 | 0 | 89 | `ok` | 100.00% | 92.85% |
| Bengaluru | `mfc_bengaluru_80` | 80 | 0 | 126 | `ok` | 100.00% | 98.39% |
| Delhi NCR | `mfc_delhi_ncr_80` | 3 | 0 | 3 | `source_total_below_minimum` | 100.00% | 95.24% |
| Mumbai | `mfc_mumbai_80` | 10 | 0 | 10 | `source_total_below_minimum` | 100.00% | 100.00% |
| Chennai | `mfc_chennai_80` | 47 | 0 | 47 | `ok` | 100.00% | 99.09% |

Total pricing-ready rows:

```text
180
```

Total quarantined rows:

```text
0
```

## Issues Found During Scaling

### 1. Transient Browser Navigation Failure

The first Bengaluru attempt failed with:

```text
Page.goto: net::ERR_CONNECTION_RESET
```

Fix:

- MFC acquisition now catches Playwright navigation errors per attempt.
- The capture loop retries instead of crashing the batch job.
- If every attempt fails, the source smoke still writes a controlled failure payload/report instead of only surfacing a traceback.

### 2. Low Public Inventory In Some Cities

Delhi NCR exposed only 3 MFC rows and Mumbai exposed only 10 MFC rows in this source path.

Fix:

- The listing coverage gate is now source-aware.
- If a source reports fewer rows than the requested minimum and we capture all reported rows cleanly, the batch passes with:

```text
source_total_below_minimum
```

This is the correct production behavior. A source with 10 available cars should not fail because the batch target asked for 40, but the low-volume signal must be documented.

## Source Interpretation

MFC is a clean but uneven source.

Strengths:

- 180 pricing-ready rows across 5 cities.
- 0 quarantined rows.
- Multi-brand inventory.
- Strong high-value completeness in the successful city batches.

Limitations:

- Public city inventory can be very small.
- It is not a high-volume path for every metro.
- Browser-backed acquisition is slower and more failure-prone than True Value GraphQL.

## Current Trusted Collection Totals

Current first-pass structured collection:

| Source | Batch | Pricing Ready | Quarantined |
| --- | --- | ---: | ---: |
| True Value | `batch_20260625_true_value_5city_fast_execute` | 429 | 0 |
| Mahindra First Choice | `batch_20260626_mfc_5city_execute` | 180 | 0 |

Combined structured-source pricing-ready rows:

```text
609
```

This does not include the Spinny Hyderabad 60-row full-detail baseline.

Including Spinny Hyderabad:

```text
669 pricing-ready rows
```

## Next Step

Before running Spinny multi-city detail pages, add a lightweight collection ledger or index that can summarize all passing source-run manifests by source, city, capture date, pricing-ready rows, quarantine rows, and source-total signal.

Reason:

- We now have enough run manifests that manual counting is becoming risky.
- The next project step should improve observability before adding more slow source-city jobs.
