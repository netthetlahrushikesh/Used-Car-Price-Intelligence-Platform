# Batch Acquisition And 100k Row Plan

Date: 2026-06-25

Purpose: define how to scale acquisition after the first trusted Spinny 60/60 baseline without blindly increasing one long scrape.

## Decision

Do not scale by running one huge scrape.

Scale by controlled batches:

```text
source x city x batch_size x detail_cap x capture_date x run_id
```

Every batch should write a source-run manifest, quality summary, smoke report, raw payload, silver output, and quarantine file.

## Why Not Just Increase Beyond 60 Rows

The current Spinny pipeline has proven:

- 60 listing rows,
- 60 detail pages,
- 60 pricing-ready rows,
- 0 quarantined rows,
- 100% required completeness,
- 100% high-value completeness.

The next risk is no longer "can one Spinny page parse correctly?"

The next risks are:

- repeated-run observability,
- city coverage,
- source bias,
- drift in page structure,
- duplicate listings over time,
- uneven model/city coverage,
- excessive runtime for detail pages.

That means manifests and batch orchestration are more important than raising one run from 60 to 100 rows.

## Can We Reach 100k Rows?

Yes, but the meaning of "100k rows" matters.

### 100k Current Unique Active Listings

This is unlikely from trusted/certified sources alone on one day.

Based on public inventory signals checked on 2026-06-25:

- Spinny city pages show hundreds to low thousands of listings in major cities, not tens of thousands per city.
- Cars24 city pages show larger inventory, including several thousand in major cities and 10k+ in Delhi NCR.
- Mahindra First Choice and Maruti True Value show broad networks, but public listing availability is distributed across dealers/cities and may not expose one clean 100k active listing pool.

Trusted sources can probably give a useful current dataset in the thousands to tens of thousands if multiple cities and sources are included. A clean 100k active trusted listing dataset likely needs marketplace partnerships, licensed datasets, or inclusion of noisier classified/marketplace sources.

### 100k Listing Observations Over Time

This is realistic.

If we treat each repeated capture as a market observation, not necessarily a unique car, then:

```text
3 sources x 10 cities x 100 rows x 34 weekly runs = 102,000 observations
```

or:

```text
5 sources x 10 cities x 100 rows x 20 runs = 100,000 observations
```

This is actually better for price intelligence because repeated snapshots show:

- price changes,
- listing freshness,
- sold/removed behavior,
- market seasonality,
- source drift,
- city/model supply changes.

## Recommended Dataset Targets

### Portfolio Analytics MVP

Target:

```text
1,000 to 2,000 pricing-ready rows
```

Plan:

```text
Spinny: 5 cities x 60 rows = 300 rows
Second trusted source: 5 cities x 60 rows = 300 rows
Third trusted/OEM source: 5 cities x 40-60 rows = 200-300 rows
Repeat key batches once or twice = 1,000+ observations
```

This is enough for:

- market profile dashboards,
- brand/model/year distributions,
- comparable listing search,
- basic outlier detection,
- storytelling and portfolio demonstration.

### Baseline Modeling MVP

Target:

```text
5,000 to 10,000 pricing-ready rows or observations
```

Plan:

```text
3 to 5 sources
8 to 12 cities
60 to 150 rows per source-city batch
repeated weekly snapshots
```

This is enough for:

- first price model,
- train/test split,
- model limitations,
- city/source-level confidence,
- comparable-listing evidence.

### Serious Price Intelligence Dataset

Target:

```text
50,000 to 100,000+ observations
```

Plan:

```text
multiple trusted sources
major cities plus tier-2 markets
scheduled repeated snapshots
deduplication and listing lifecycle tracking
source-run manifests
source quality scoring
```

This should be treated as a multi-week to multi-month data product, not a single scraping task.

## City Plan

### Phase 1: Validated City

```text
Hyderabad
```

Reason:

- current parser and enrichment path are validated here,
- current source URL and locality behavior are known,
- 60/60 Spinny baseline already passes.

### Phase 2: Major Metro Expansion

```text
Hyderabad
Bengaluru
Delhi NCR
Mumbai or Pune
Chennai
```

Reason:

- strong used-car supply,
- different regional price behavior,
- enough inventory for comparable listings,
- better story than one-city scraping.

### Phase 3: Broader Market Coverage

```text
Kolkata
Ahmedabad
Jaipur
Lucknow
Chandigarh / Kochi / Indore
```

Reason:

- expands beyond metro-only bias,
- improves city-level generalization,
- useful for market-intelligence storytelling.

## Source Plan

Core model data should come only from trusted, evaluated inventory sources. The first training-quality dataset
should not mix in customer-priced or self-listed inventory because that makes the target price noisier.

### Source 1

```text
Spinny
```

Status:

- active first-source pipeline,
- 60/60 Hyderabad baseline passed,
- best current source for clean certified listing-card and detail-page data.

### Source 2

```text
Mahindra First Choice
```

Reason:

- multi-brand,
- dealer/certified evaluated stock,
- useful source-bias contrast against Spinny,
- closer to real dealer-pricing behavior than self-listed marketplaces.

### Source 3

```text
Maruti Suzuki True Value
```

Reason:

- OEM-backed certified/evaluated inventory,
- strong dealer network,
- useful for Maruti-heavy market coverage,
- trusted pricing/inspection signal compared with classifieds.

Status:

- Hyderabad 40-row live smoke passed on 2026-06-25.
- Observed 247 active Hyderabad rows across 21 discovered True Value dealers.
- Required completeness: 100.00%.
- High-value completeness: 100.00%.
- Main caveat: Maruti-only brand bias.

### Later Trusted Sources

```text
Honda Auto Terrace
Hyundai Promise
Toyota U Trust
```

Reason:

- cleaner trust profile,
- useful for certified/OEM bias comparison,
- helps show source-quality scoring.

### Delayed Sources

```text
CarDekho
CarWale
CarTrade
OLX
Cars24, unless filtered to platform/verified evaluated inventory
```

Reason:

- useful coverage,
- but higher data-quality and trust complexity,
- may include customer-priced, verified-seller, or less consistently evaluated inventory depending on path,
- should not be part of the first model-training dataset unless source trust and pricing control are clearly proven.

## Runtime Planning

Current observed Spinny 60/60 run:

```text
about 5 minutes
```

Practical estimates:

```text
1 source x 1 city x 60 full-detail rows: about 5 minutes
1 source x 5 cities x 60 rows: about 25-40 minutes
3 trusted sources x 5 cities x 60 rows: about 1.5-3 hours runtime after adapters exist
```

Development time is larger than runtime:

```text
run manifests and metrics: 0.5-1 day
multi-city Spinny batches: 0.5-1 day
second source adapter: 1-3 days
third source adapter: 1-3 days
analytics layer: 1-2 days
baseline model after enough data: 2-5 days
```

## Next Engineering Step

Add source-run manifests before increasing volume.

Each run manifest should record:

- manifest version,
- source,
- city,
- state,
- source URL,
- run ID,
- capture date,
- started/completed timestamps,
- duration,
- requested batch parameters,
- listing capture metrics,
- listing coverage metrics,
- detail enrichment metrics,
- quality summary,
- output paths.

This allows us to compare runs without opening large raw payloads.

## Immediate Next Batch After Manifests

After manifests are in place:

```text
Spinny Hyderabad 60/60 baseline rerun with manifest
Spinny Bengaluru 60/60
Spinny Delhi NCR 60/60
Spinny Mumbai or Pune 60/60
Spinny Chennai 60/60
```

Then evaluate:

- field completeness by city,
- parser warnings by city,
- detail-page failure rate by city,
- runtime by city,
- model/brand coverage by city,
- duplicate listing behavior.

After the Spinny city batches are stable, start the second trusted adapter:

```text
Mahindra First Choice Hyderabad
```

Then:

```text
True Value Hyderabad
```

Do not add OLX or broad unverified marketplaces to the model-training dataset. Keep them only for noisy-source
research or quarantine stress tests.

Current update:

- True Value Hyderabad is now validated and `docs/27-three-source-field-comparison.md` is generated.
- The batch runner now supports resume/skip behavior and batch summary reports.
- The 100k acceleration plan is documented in `docs/29-100k-collection-acceleration-plan.md`.
- The next engineering step is a dry-run over the 5-city trusted-source plan, followed by executing the fast structured sources first.
