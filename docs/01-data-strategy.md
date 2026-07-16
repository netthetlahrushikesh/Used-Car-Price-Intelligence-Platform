# Data Strategy

## Data Thesis

The platform wins if it can build a trusted market dataset that captures listing price, vehicle attributes, location, source, and time.

The first product version should not try to know every car in India. It should know a narrow market very well, then expand.

## Source Priority

1. Partner or dealer feeds.
   - Best long-term source.
   - Most stable and legally clean.
   - Harder to acquire early.

2. Public listing pages, where allowed.
   - Useful for early market intelligence.
   - Must respect terms, robots, rate limits, and site load.
   - Should be treated as unstable.

3. Public/open datasets.
   - Useful for enrichment, market context, and model priors.
   - Usually not enough for live pricing.

4. User-submitted listings.
   - Useful later for valuation flows.
   - Must be separated from observed market listings.

5. Synthetic data.
   - Allowed for tests, demos, and load testing.
   - Not acceptable as evidence for price intelligence.

## Acquisition Modes

### API Or Partner Feed

Use this whenever available. It is the preferred production path.

Required controls:

- Contracted field definitions.
- Source freshness SLA.
- Schema version.
- Load timestamp.
- Deduplication key.
- Backfill policy.

### Browser Extraction

Use Playwright when pages are dynamic, infinite-scrolling, or JavaScript-rendered.

Required controls:

- Stable locators where possible.
- Explicit wait strategy.
- Raw HTML or structured payload snapshot.
- Screenshot or trace on failure.
- Per-source rate limits.
- Run-level metrics.

### Crawler Framework

Use Scrapy when the source is crawlable through static pages or stable HTTP responses.

Required controls:

- Auto-throttling.
- Duplicate filtering.
- Item pipelines for validation and persistence.
- Feed export or direct storage to raw lake.

### Manual Seed Dataset

Use a small manually curated dataset only for early parser and schema tests.

Required controls:

- Mark as `source_type = manual_seed`.
- Never mix with production observed listings without a source flag.

## Canonical Listing Record

Minimum canonical fields:

```text
listing_id
source
source_listing_id
listing_url
captured_at
city
state
brand
model
variant
model_year
fuel_type
transmission
ownership
km_driven
registration_state
registration_code
listed_price_inr
currency
is_available
raw_record_hash
ingestion_run_id
schema_version
```

Optional fields for later:

```text
body_type
color
insurance_valid_until
seller_type
dealer_name
listing_age_days
location_latitude
location_longitude
engine_cc
features
images_count
inspection_score
```

## Source Evaluation Checklist

Before writing a scraper for any source:

- Is collection allowed by source terms and robots policy?
- Does the source expose personal data?
- Can we collect only listing-level commercial data?
- Can we identify stable listing IDs?
- Can we capture location and timestamp?
- Can we detect removed or sold listings?
- Does the source block, throttle, or challenge automated access?
- What is the expected maintenance cost?

## What We Will Not Do

- Do not bypass authentication, payment, CAPTCHAs, or access controls.
- Do not scrape private user contact information.
- Do not hammer websites.
- Do not train models on data whose source cannot be explained.
- Do not mix real and synthetic records without explicit flags.
- Do not depend on one fragile CSS selector as the only extraction path.
