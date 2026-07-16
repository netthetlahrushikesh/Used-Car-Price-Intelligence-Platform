# Data Acquisition Research And Plan

Research date: 2026-06-24

## Executive Summary

Used-car company pages expose useful listing data, but most major platforms are not safe production scraping targets without permission.

The proper startup-grade approach is:

1. Treat public pages as research and source evaluation targets.
2. Build the data platform around permissioned, auditable data first.
3. Use manual seed data to test schemas and pipelines.
4. Pursue dealer feeds, partner feeds, or licensed datasets for scale.
5. Only automate a public website after terms, robots policy, and source approval are clear.

The critical mistake to avoid is building the project around a scraper that is technically impressive but legally fragile.

## What Used-Car Pages Usually Expose

Company listing/search pages often expose:

- Listing title: year, brand, model.
- Variant or trim.
- Listed price.
- Original price or discount, sometimes.
- Kilometers driven.
- Fuel type.
- Transmission.
- Registration code or state.
- City, area, or car hub.
- Inspection/warranty labels.
- Owner count, sometimes directly and sometimes in text snippets.
- Seller/dealer actions, usually behind lead/contact flows.
- Aggregated market content: inventory counts, price ranges, popular models, fuel/transmission summaries.

Detail pages can expose more:

- Images.
- Full variant.
- Inspection report status.
- Features.
- Condition notes.
- Financing/EMI estimates.
- Warranty.
- Seller type.
- Availability status.

## Where The Data Appears Technically

Common page patterns:

- Server-rendered HTML with listing cards.
- Search-engine optimized city/model pages with static listing snippets.
- JavaScript-rendered listings loaded after page open.
- Embedded application state in script tags.
- API responses consumed by the frontend.
- Infinite scrolling or paginated result pages.
- Image alt text that repeats vehicle attributes.
- Detail pages linked from listing cards.

Extraction priority should be:

1. Official/permissioned feed or API.
2. Static HTML and structured data.
3. Browser-rendered page content.
4. Frontend API inspection only when allowed.

Do not bypass authentication, CAPTCHAs, anti-bot systems, paywalls, or private app endpoints.

## Research Findings From Major Indian Used-Car Sites

### Cars24

Useful data exists on public pages, but current terms are restrictive.

Findings:

- Terms reviewed on 2026-06-24 say automated access requires prior written permission.
- Terms restrict scraping, data mining, indexing, or extracting website content for commercial purposes.
- Robots file disallows multiple paths and Next.js assets.

Decision: `needs_permission`

Use Cars24 as:

- Historical benchmark from the old notebook.
- Potential partnership target.
- Manual qualitative research source.

Do not use Cars24 as the first production scraper.

### Spinny

Useful listing data is visible in city pages. Example Hyderabad page exposes inventory count, model price ranges, individual listing cards, price, kilometers, fuel, transmission, registration code, and hub location.

Findings:

- Spinny Hyderabad listing page showed hundreds of used cars and visible fields such as price, kilometers, fuel, transmission, registration code, and hub location.
- Spinny terms prohibit deep-link, robot, spider, automatic device, algorithm, or similar manual process to access, acquire, copy, or monitor platform content.
- Spinny robots disallows `/api/`, account paths, report paths, some dynamic filter/query patterns, and some listing detail paths.

Decision: `needs_permission`

Use Spinny as:

- Source structure reference.
- Potential partnership target.
- Manual seed inspiration.

Do not automate production collection without permission.

### CarDekho

Useful listing data is visible in city pages. Example Hyderabad page exposes title, price, kilometers, transmission, fuel, local area, owner summary, inspection/warranty text, and seller action controls.

Findings:

- CarDekho Hyderabad used-car page exposes individual listings and aggregate category links.
- Terms prohibit copying content through manual or automated means including page scraping, data mining, data gathering, indexing, bots, crawlers, spiders, scripts, deep links, browser plug-ins, or violating robots.txt instructions.
- Terms also prohibit using listing enquiries for data gathering, data mining, relisting, brokering, match-making, or resale.
- Robots disallows `/api/*`, `/searchuc?city=`, `/cars-search/*`, used-car pictures, and several other paths.

Decision: `blocked_for_unpermitted_scraping`

Use CarDekho as:

- Manual research reference.
- Potential partnership target.
- Competitor/source analysis.

Do not automate collection without permission.

### CarWale

CarWale exposes used-car inventory and valuation/research pages, but important used/search and API routes are restricted.

Findings:

- Robots disallows `/used/search_result.aspx`, `/used/page-*/`, `/api/*`, `/webapi/*`, valuation report paths, login/account paths, and lead paths.
- Visitor agreement restricts used-car purchase/enquiry flows to real purchase intent and prohibits enquiries for data gathering, data mining, relisting, brokering, match-making, or resale.

Decision: `blocked_for_unpermitted_scraping`

Use CarWale as:

- Manual research reference.
- Potential partnership/licensed data target.

Do not automate collection without permission.

## Main Challenges

### 1. Legal And Permission Risk

Many sites explicitly restrict automated access, commercial extraction, data mining, copying, or use of leads for data gathering.

Mitigation:

- Source evaluation before coding.
- Permission-first acquisition.
- Written partner/dealer agreements.
- No production automation against blocked sources.
- Keep legal notes with source review date.

### 2. Robots And Crawl Policy Risk

Robots.txt is not a full legal permission system, but it is an important crawl-management signal. It often blocks APIs, search paths, account paths, and dynamic filters.

Mitigation:

- Parse robots.txt before any automated collection.
- Treat disallowed paths as off-limits.
- Also check terms, because terms can be stricter than robots.

### 3. Anti-Bot And Reliability Risk

Used-car sites may use dynamic rendering, lazy loading, changing CSS classes, bot checks, rate limits, CAPTCHAs, and app-only endpoints.

Mitigation:

- Do not bypass protections.
- Prefer official feeds.
- If allowed, use stable page semantics and conservative crawl rates.
- Capture raw snapshots and failure artifacts.
- Add source-specific monitoring.

### 4. Data Quality Problems

Expected issues:

- Different price formats: `Rs 5.75L`, `5.75 Lakh`, `575000`.
- Different distance formats: `13,000 kms`, `14K km`, `143.5K km`.
- Fuel labels vary: petrol, Petrol, CNG, cng, hybrid.
- Transmission labels vary: Manual, manual, AMT, automatic.
- Owner count may be missing or hidden in narrative text.
- Registration format may be partial: TS07, TS-07, Telangana, Hyderabad.
- Model and variant parsing is difficult.
- Same vehicle can appear across sources.
- Price may change over time.
- Listings disappear after sale.
- Some listings are sponsored or partner listings.

Mitigation:

- Canonical schema.
- Pydantic record validation.
- Pandera batch validation.
- Quarantine invalid records.
- Raw record hashing.
- Source-specific parsers.
- Cross-source dedup keys.
- Capture date and listing status.

### 5. Completeness And Bias

Observed marketplace listings are not the whole used-car market. Some platforms overrepresent certified cars, dealers, high-quality inventory, certain cities, or certain price bands.

Mitigation:

- Store `source` and `source_type`.
- Track coverage by city, brand, model, price band.
- Do not train one universal model from one source.
- Use source quality scores.
- Build city/model-specific confidence intervals.

### 6. PII And Sensitive Data

Some pages expose seller contact flows, location, WhatsApp actions, dealer names, or user-generated information.

Mitigation:

- Do not collect phone numbers, personal seller names, account data, or contact-flow information.
- Collect listing-level commercial attributes only.
- Document allowed and disallowed fields per source.

## Recommended Acquisition Strategy

### Phase A: Manual Seed Dataset

Purpose:

- Validate schema.
- Test parsers.
- Build storage layers.
- Build first market profile.

Scope:

- 50 to 200 records.
- Hyderabad only.
- Manually curated from allowed observation or synthetic-but-realistic samples marked clearly.
- No contact data.

Output:

- `data/raw/manual_seed/...`
- `data/silver/listings/...`
- Parser tests.
- Quality report.

### Phase B: Dealer / Partner Feed

Purpose:

- Build real repeatable data supply.

Possible format:

- CSV.
- Google Sheet export.
- Email attachment converted manually at first.
- API later.

Required fields:

- Listing ID.
- Brand.
- Model.
- Variant.
- Year.
- Kilometers.
- Fuel.
- Transmission.
- Ownership.
- Registration state.
- City.
- Listed price.
- Availability.
- Updated date.

Output:

- Permissioned source connector.
- Contracted schema.
- Scheduled ingestion.

### Phase C: Licensed / Public Dataset Enrichment

Purpose:

- Model priors and market context.

Use for:

- Brand/model normalization.
- Vehicle specs.
- Segment/body type.
- New-car ex-showroom price references.
- RTO/state code lookup.

Do not treat outdated datasets as live pricing truth.

### Phase D: Permissioned Marketplace Connectors

Purpose:

- Scale coverage.

Only after:

- Written permission.
- Clear rate limits.
- Source contract.
- Allowed fields.
- Data usage rights.

## Recommended Technical Process

1. Source intake.
   - Fill source evaluation template.
   - Record terms URL, robots URL, review date, allowed fields, blocked fields, and decision.

2. Data contract.
   - Define source-specific raw schema.
   - Map to canonical listing schema.

3. Raw capture.
   - Store source snapshots exactly as received.
   - Include run metadata.

4. Bronze normalization.
   - Parse source fields without over-cleaning.
   - Preserve source quirks.

5. Silver validation.
   - Normalize units and categories.
   - Validate with strict rules.
   - Quarantine failures.

6. Gold analytics.
   - Build market aggregates.
   - Build comparable listing tables.
   - Build feature tables.

7. Monitoring.
   - Track record counts, failures, missing fields, duplicates, and freshness.

## First Practical Build Recommendation

Start with this sequence:

1. Create canonical schema models.
2. Create 100-record manual seed dataset for Hyderabad.
3. Build parser and validation tests.
4. Store raw and silver Parquet.
5. Build DuckDB market summary queries.
6. Then approach one local dealer or small dealer group for a permissioned feed.

This gives us a production-grade data pipeline without taking on legal risk from day one.

## Sources Reviewed

- Cars24 Terms and Conditions: https://www.cars24.com/terms-and-conditions/
- Cars24 robots.txt: https://www.cars24.com/robots.txt
- Spinny Hyderabad listing page: https://www.spinny.com/used-cars-in-hyderabad/s/
- Spinny Terms of Use: https://www.spinny.com/terms-and-conditions/value-drive/
- Spinny robots.txt: https://www.spinny.com/robots.txt
- CarDekho Hyderabad listing page: https://www.cardekho.com/used-cars+in+hyderabad
- CarDekho Terms and Conditions: https://www.cardekho.com/info/terms_and_condition
- CarDekho robots.txt: https://www.cardekho.com/robots.txt
- CarWale Visitor Agreement: https://www.carwale.com/visitor-agreement/
- CarWale robots.txt: https://www.carwale.com/robots.txt
- Google robots.txt guidance: https://developers.google.com/search/docs/crawling-indexing/robots/intro
- Playwright locator documentation: https://playwright.dev/python/docs/api/class-locator
- Scrapy AutoThrottle documentation: https://docs.scrapy.org/en/latest/topics/autothrottle.html
- Scrapy item pipeline documentation: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
