# Spinny Remaining Hub Collection Run

Date: 2026-06-26

Purpose: complete the first five-city Spinny full-detail collection after Bengaluru validated the hub-page approach.

## Decision

Run the remaining Spinny cities through hub pages, not generic city pages.

Reason:

- Bengaluru proved that the generic city page can under-expose usable listing cards.
- Hub pages expose stable location-specific inventory and preserve locality context.
- Spinny detail enrichment is slow, so each city should start from the best available public listing page.

## Hub URLs Used

| City | Batch | Hub URL | Locality Fallback |
| --- | --- | --- | --- |
| Delhi NCR | `spinny_delhi_ncr_60_detail60` | `https://www.spinny.com/used-cars-at-delhi-dwarka-sector-21-taj-vivanta-hub-in-delhi-ncr/s/` | Dwarka Sector 21, Delhi NCR |
| Mumbai | `spinny_mumbai_60_detail60` | `https://www.spinny.com/used-cars-at-mumbai-dadar-hub-in-mumbai/s/` | Dadar, Mumbai |
| Chennai | `spinny_chennai_60_detail60` | `https://www.spinny.com/used-cars-at-chennai-nexus-vijaya-mall-in-chennai/s/` | Nexus Vijaya Mall, Chennai |

## Issues Found

### 1. Delhi NCR RTO Suffix Codes

The first Delhi batch failed at 19 clean rows even though 62 raw cards were observed.

Root cause:

- Valid Delhi RTO values such as `DL3C`, `DL4C`, and `DL9C` were rejected by the Spinny card parser.
- The parser accepted simple codes like `DL10` and `HR26`, but not district codes with suffix letters.

Fix:

- Widened the Spinny card-level registration detector to accept `AA9A` / `AA99AA`-style RTO tokens.
- Added a regression fixture for a Delhi card with `DL3C`.

### 2. Transient Spinny Navigation Failure

During diagnostics, Spinny navigation hit transient browser/network errors such as:

```text
ERR_CONNECTION_CLOSED
ERR_INTERNET_DISCONNECTED
```

Fix:

- Spinny listing capture now uses one fresh browser page per capture attempt.
- Initial `page.goto` and selector waits are retried under the existing `capture_attempts` policy.
- Failed attempts write structured capture diagnostics instead of only throwing raw Playwright errors.

### 3. Chennai Mini Countryman Vocabulary Gap

The first Chennai full run captured and enriched all 60 detail pages, but quarantined one valid row:

```text
2014 Mini Countryman One
```

Root cause:

- `Mini` / `Countryman` was not in the canonical title parser vocabulary.

Fix:

- Added `Mini` brand aliases.
- Added `Countryman` as a known Mini model.
- Added a parser regression test.

## Commands

Delhi NCR rerun:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id spinny_delhi_ncr_60_detail60 --capture-date 2026-06-26 --batch-run-id batch_20260626_spinny_delhi_hub_detail_execute_v2 --execute --json
```

Mumbai and Chennai batch:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id spinny_mumbai_60_detail60 --batch-id spinny_chennai_60_detail60 --capture-date 2026-06-26 --batch-run-id batch_20260626_spinny_mumbai_chennai_hubs_detail_execute --execute --json
```

Chennai rerun after Mini parser fix:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id spinny_chennai_60_detail60 --capture-date 2026-06-26 --batch-run-id batch_20260626_spinny_chennai_hub_detail_execute_v2 --execute --json
```

## Passing Results

| City | Passing Run ID | Pricing Ready | Quarantined | Required | High Value | Overall | Detail Successful | Runtime |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Delhi NCR | `run_20260626_spinny_delhi_ncr_60_detail60_batch_20260626_spinny_delhi_hub_detail_execute_v2` | 60 | 0 | 100.00% | 100.00% | 93.98% | 60 | 275.601s |
| Mumbai | `run_20260626_spinny_mumbai_60_detail60_batch_20260626_spinny_mumbai_chennai_hubs_detail_execute` | 60 | 0 | 100.00% | 100.00% | 93.99% | 60 | 440.488s |
| Chennai | `run_20260626_spinny_chennai_60_detail60_batch_20260626_spinny_chennai_hub_detail_execute_v2` | 60 | 0 | 100.00% | 100.00% | 94.00% | 60 | 283.533s |

Listing capture diagnostics:

| City | Raw Cards Returned | Parsed Before Cap | Final Records | Variant Warnings |
| --- | ---: | ---: | ---: | ---: |
| Delhi NCR | 62 | 62 | 60 | 3 |
| Mumbai | 62 | 62 | 60 | 6 |
| Chennai | 62 | 62 | 60 | 7 |

## Updated Spinny Status

All first-pass Spinny hub batches are now validated:

| City | Pricing Ready | Quarantined |
| --- | ---: | ---: |
| Hyderabad | 60 | 0 |
| Bengaluru | 60 | 0 |
| Delhi NCR | 60 | 0 |
| Mumbai | 60 | 0 |
| Chennai | 60 | 0 |

Spinny total:

```text
300 pricing-ready rows
```

## Updated Collection Ledger

The passing Spinny source manifests were added to:

```text
trusted_collection_v2_20260626
```

Outputs:

```text
data/gold/collection_ledger/trusted_collection_v2_20260626.json
data/gold/collection_ledger/trusted_collection_v2_20260626.md
```

Ledger totals:

| Metric | Value |
| --- | ---: |
| Source runs | 15 |
| Pricing-ready rows | 909 |
| Quarantined rows | 0 |
| Source-total inventory signal | 1,766 |

By source:

| Source | Runs | Pricing Ready | Quarantined |
| --- | ---: | ---: | ---: |
| Spinny | 5 | 300 | 0 |
| True Value | 5 | 429 | 0 |
| Mahindra First Choice | 5 | 180 | 0 |

## Verification

```powershell
.venv\Scripts\python -m unittest tests.unit.test_parsers tests.unit.test_spinny_live_acquisition tests.unit.test_cli
.venv\Scripts\python -m compileall src
.venv\Scripts\python -m unittest discover -s tests
```

Result:

```text
69 focused tests passed
compileall passed
134 full-suite tests passed
```

## Next Step

Do not collect more rows blindly yet.

The next production-level step should be dedupe and listing lifecycle tracking:

- identify duplicate listings across sources,
- define stable listing identity keys,
- track first_seen and last_seen dates,
- separate current inventory snapshots from historical observations,
- prepare a durable collection schedule for repeated snapshots.
