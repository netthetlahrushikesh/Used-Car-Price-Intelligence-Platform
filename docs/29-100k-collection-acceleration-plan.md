# 100k Collection Acceleration Plan

Date: 2026-06-25

Purpose: define the fastest credible path from the validated trusted-source pilots to a large, pricing-ready used-car dataset.

## Current Answer

Do not try to get 100,000 rows by making one scraper bigger.

The faster production approach is:

1. Use the fastest structured sources first.
2. Run source-city batches with resume and skip support.
3. Store repeated market observations, not only unique current cars.
4. Detail-enrich only where it materially improves modeling quality.
5. Use licensed or partner data if the project requires 100,000 current unique listings quickly.

## Research Snapshot

Checked on 2026-06-25.

| Source | Public signal | Scale implication |
| --- | --- | --- |
| Spinny | Official pages describe 10,000+ inspected used cars across cities. Delhi NCR showed about 1,363 cars; Bengaluru showed about 644 cars. | Good trusted source, but detail enrichment is slow. Best used as high-quality benchmark plus selected metro batches. |
| Maruti Suzuki True Value | Official site shows 30,000+ curated inventory, 648 outlets, and 332 cities. | Best current bulk candidate because our acquisition path uses dealer discovery plus GraphQL and returns structured fields quickly. Brand bias is Maruti-only. |
| Mahindra First Choice | Official site describes certified second-hand cars from 1,000+ dealers. Some city pages can still be small, such as Mumbai showing 10 cars in the checked result. | Useful trusted multi-brand source, but city-level public inventory may be uneven. Keep source-specific and do not assume every city has high volume. |
| OBV / Droom | Orange Book Value is a used-vehicle fair-market-price engine, not a listing inventory source. | Useful later as valuation benchmark or feature validation, not as raw listing rows. |
| Listing data APIs | MarketCheck-type APIs offer real-time vehicle listing datasets at scale, but coverage is not necessarily India-first. | Fastest route to large datasets if licensed data is acceptable; still must check country/source coverage and commercial terms. |

Sources:

- <https://www.spinny.com/>
- <https://www.spinny.com/used-cars-in-delhi-ncr/s/>
- <https://www.spinny.com/used-cars-in-bangalore/s/>
- <https://www.marutisuzukitruevalue.com/>
- <https://www.mahindrafirstchoice.com/>
- <https://www.mahindrafirstchoice.com/used-cars/mumbai>
- <https://orangebookvalue.com/>
- <https://www.marketcheck.com/apis/cars/>

## 100k Rows: What Is Realistic

### 100k Current Unique Trusted Listings

This is unlikely from only Spinny, Mahindra First Choice, and True Value in a single short run.

Reason:

- Spinny public active inventory appears closer to 10k+ total, not 100k+.
- True Value has a strong public inventory signal at 30k+ but is Maruti-only.
- Mahindra First Choice has a large dealer network, but public city inventory is uneven.

To get 100k current unique rows quickly, the realistic paths are:

- licensed marketplace/listing data,
- direct partnership feeds,
- adding more trusted OEM/certified sources,
- carefully including verified dealer marketplaces after source-trust scoring.

### 100k Market Observations

This is realistic and better for price intelligence.

Example:

```text
3 sources x 10 cities x 100 rows x 34 snapshots = 102,000 observations
```

Those rows are not all unique cars. They are market observations across time, which is useful because price intelligence needs:

- price movement,
- listing age,
- sold or removed behavior,
- demand/supply patterns,
- city and source drift.

## Fast Collection Architecture

### Tier 1: Structured Bulk Sources

Use these first when speed matters:

```text
True Value: dealer discovery + GraphQL
Mahindra First Choice: Next.js data + listing API response capture
```

These sources avoid per-card visual parsing for most fields and can return cleaner structured rows.

### Tier 2: High-Quality Detail Enrichment

Use this selectively:

```text
Spinny full detail pages
```

Spinny detail pages are valuable because they give ownership, inspection, insurance, service, warranty, and quality signals. They are slow because each car has a detail page. For scale, use detail enrichment as a sampling/enrichment layer:

- full detail for first 60 rows per city while validating,
- detail sample for new cities,
- detail only for high-value or uncertain rows,
- detail rerun only when listing fields changed.

### Tier 3: Licensed or Partner Data

Use this only if the target becomes "100k current rows quickly."

Candidate use:

- bulk historical listings,
- dealer inventory feeds,
- valuation benchmarks,
- model pretraining.

This should stay separate from scraped/source-collected rows with its own source policy, schema mapping, and quality score.

## Runtime Strategy

### Do Not Run Everything Serially

Run by source groups:

```text
true_value city batches first
mfc city batches second
spinny detail batches last
```

Reason:

- True Value is fastest and gives immediate row volume.
- MFC is structured but city inventory can be uneven.
- Spinny detail enrichment is slow but high-value.

### Use Bounded Parallelism

Do not blindly parallelize every browser job.

Recommended first limits:

```text
True Value: 3-5 city jobs in parallel later, because it is HTTP/GraphQL based.
MFC: 1-2 browser jobs in parallel after stability is proven.
Spinny: 1 browser job at a time until detail-page failure rates are known.
```

For this repository, the immediate implementation remains sequential and resumable. Parallel execution should be added only after batch manifests, skip/resume, and source-level failure reports are stable.

## Immediate Collection Plan

### Phase A: 5-City First Dataset

Cities:

```text
Hyderabad
Bengaluru
Delhi NCR
Mumbai
Chennai
```

Expected clean output:

```text
700 to 1,500 pricing-ready observations
```

This is enough for:

- source/city data-quality comparison,
- schema drift checks,
- first analytics dashboard,
- baseline model feasibility.

### Phase B: 10-City Snapshot Dataset

Add:

```text
Pune
Kolkata
Ahmedabad
Jaipur
Lucknow
```

Expected output per snapshot:

```text
1,500 to 3,000 pricing-ready observations
```

### Phase C: 100k Observation Dataset

Collect repeated snapshots:

```text
10 cities
3 to 5 trusted sources
daily or weekly schedules
dedupe by source listing id, URL, registration code, city, model, year, km, and price
track listing lifecycle
```

Expected path:

```text
weekly snapshots: multi-month project
daily snapshots: multi-week project
licensed data: fastest if coverage is acceptable
```

## New Engineering Requirement

Before executing a long run, the batch runner must support:

- resume from a prior manifest,
- skip passed jobs,
- write batch-level summary reports,
- preserve failed job evidence,
- allow rerun of only failed or missing batches.

This is now the required operating model for collection.

## Decision

The fastest credible next move is not a 100k scrape. It is:

```text
5-city trusted-source dry run
then execute True Value and MFC city batches first
then run Spinny detail batches selectively
then repeat snapshots with dedupe and lifecycle tracking
```

This gives a strong dataset quickly while keeping the project production-grade.

## Current Collection Evidence

Updated after first 5-city structured runs.

| Source | Batch | Pricing-ready rows | Quarantined rows | Interpretation |
| --- | --- | ---: | ---: | --- |
| True Value | `batch_20260625_true_value_5city_fast_execute` | 429 | 0 | Fastest current bulk source, but Maruti-only. |
| Mahindra First Choice | `batch_20260626_mfc_5city_execute` | 180 | 0 | Clean multi-brand source, but public city inventory is uneven. |

Combined structured-source rows:

```text
609 pricing-ready rows
```

Including the Spinny Hyderabad full-detail baseline:

```text
669 pricing-ready rows
```

This confirms the original conclusion: the project can collect clean trusted rows quickly, but 100,000 current unique trusted rows still requires many more source-city snapshots, additional trusted sources, or licensed/partner data.
