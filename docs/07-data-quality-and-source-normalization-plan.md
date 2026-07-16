# Data Quality And Source Normalization Plan

## Purpose

This project will not fail because scraping one page is hard. It will fail if every source produces a different shape of messy data and the cleanup logic becomes scattered across notebooks.

The solution is to treat data quality as the core product system:

- Every source gets its own adapter.
- Raw captures are preserved exactly.
- Parsing is tested against saved fixtures.
- Bad records are quarantined, not silently dropped.
- Canonical records are validated before analytics or modeling.
- Source quality is measured over time.

## The Real Problem

Single-source scraping is manageable because all records are messy in the same way.

Multi-source scraping creates harder problems:

- Different sites name the same fields differently.
- Some sites expose fields directly; others hide them in card text.
- Some fields are missing from listing cards but present on detail pages.
- CSS classes and layouts change.
- Infinite scroll can create partial captures.
- Placeholder cards, ads, banners, and recommendations look like listings.
- Duplicate vehicles appear across sites or get relisted.
- Prices and availability change daily.

The project should assume every source is unreliable until proven otherwise.

## Data Issue Taxonomy

### Structural Issues

Examples:

- Dynamic pages require JavaScript rendering.
- Listing cards load after scrolling.
- CSS classes change.
- Cards are mixed with ads or curated sections.
- Detail links are missing or lazy-loaded.
- Some data is in text, some in attributes, some in embedded scripts.

Controls:

- Source-specific extraction adapters.
- Raw HTML and extracted payload snapshots.
- Screenshot or trace on failed capture.
- Fixture tests for every parser.
- Per-source record-count monitoring.

### Field Completeness Issues

Examples:

- Missing owner count.
- Missing variant.
- Missing registration code.
- Missing exact locality.
- Missing seller type.
- Missing listing ID.
- Empty strings instead of real nulls.

Controls:

- Required, conditionally required, and optional field categories.
- Null normalization: empty strings, whitespace, `NA`, `-`, and `Not Available` become null.
- Field-level completeness reports by source.
- Quarantine records that miss required fields.

## Completeness Philosophy

The goal is not to force every column in the entire project to be 100% populated. That will create a different problem: we would drop too many useful records and bias the dataset toward only the sources that expose every field.

The correct goal is:

- Pricing-critical fields must be complete for every pricing-ready row.
- High-value fields should be aggressively enriched and measured.
- Optional fields should improve the product but not block ingestion.
- Missingness must be visible, not hidden.

This means the platform should maintain multiple quality layers:

```text
raw_records
bronze_records
silver_valid_records
gold_pricing_ready_records
```

`silver_valid_records` can contain controlled nulls in non-critical fields. `gold_pricing_ready_records` should be strict enough for analytics, comparables, and model training.

## Completeness Targets

### Gold Pricing-Ready Rows

Every row used for price intelligence must have 100% completeness for these fields:

```text
source
source_listing_id or listing_url
captured_at
city
brand
model
model_year
listed_price_inr
km_driven
fuel_type
transmission
raw_record_hash
ingestion_run_id
```

If any of these are missing, the record must not enter the pricing-ready table.

### High-Value Completeness

These fields should be targeted at 80% to 95% completeness per source after parser improvement and detail-page enrichment:

```text
variant
ownership
registration_code
locality
seller_type
is_certified
is_available
```

If these are missing, the record can still be useful, but it should receive a lower completeness score and lower pricing confidence.

### Optional Completeness

These fields should be measured but should not block ingestion:

```text
emi_amount_inr
original_price_inr
discount_amount_inr
dealer_name
hub_name
body_type
color
seating_capacity
warranty_label
return_policy_label
finance_label
deal_rating
inspection_score
```

The project should report their completeness by source, but not require them for early modeling.

## Row Completeness Score

Each canonical record should get completeness scores:

```text
required_completeness_score
high_value_completeness_score
optional_completeness_score
overall_completeness_score
pricing_ready_flag
```

Recommended rule:

```text
pricing_ready_flag = true
  only if required_completeness_score == 1.0
  and listed_price_inr is valid
  and km_driven is valid
  and model_year is valid
  and no critical parser warnings exist
```

This lets us keep imperfect records for debugging and enrichment without allowing them to pollute price intelligence.

## Source Completeness Scorecard

Every source run should produce a table like:

```text
source
capture_date
records_captured
records_pricing_ready
pricing_ready_rate
required_field_completeness
variant_completeness
ownership_completeness
registration_completeness
locality_completeness
seller_type_completeness
fuel_parse_success_rate
transmission_parse_success_rate
price_parse_success_rate
km_parse_success_rate
```

This is how we decide whether a source is worth scaling.

Target bands:

```text
excellent_source: pricing_ready_rate >= 0.90
usable_source: pricing_ready_rate >= 0.75
research_only_source: pricing_ready_rate < 0.75
```

For the first version, a source should not be promoted beyond research mode until at least 90% of captured listing-like records become pricing-ready or the missingness is well understood.

## How To Improve Completeness

Use these steps before dropping a source:

1. Improve listing-card extraction.
2. Add detail-page enrichment for fields missing from cards.
3. Add source-specific parser fallbacks.
4. Normalize whitespace, empty strings, placeholders, and symbols early.
5. Parse natural-language snippets only with confidence flags.
6. Use brand/model dictionaries to repair title parsing.
7. Quarantine records with missing required fields.
8. Keep a report of which fields caused each quarantine.

Do not fake missing values. If a field is not present, keep it null, lower confidence, and report it.

### Semantic Normalization Issues

Examples:

- Price: `Rs 5.75L`, `5.75 Lakh`, `575000`, `5,75,000`.
- Kilometers: `64K km`, `64,000 kms`, `64000`, `143.5K km`.
- Fuel: `Petrol`, `petrol`, `CNG`, `Petrol + CNG`.
- Transmission: `AT`, `AMT`, `Automatic`, `Manual`.
- Owner: `1st owner`, `First Owner`, `2 owners`.
- Registration: `TS07`, `TS-07`, `Telangana`, `Hyderabad`.

Controls:

- Central parsing functions for price, kilometers, ownership, fuel, transmission, and registration.
- Controlled vocabularies.
- Preserve raw value next to normalized value in bronze.
- Store parser confidence where extraction is uncertain.

### Vehicle Identity Issues

Examples:

- Same car appears on multiple sources.
- Same source relists a vehicle with a new URL.
- Dealer reposts a sold vehicle.
- Different sites abbreviate model and variant differently.

Controls:

- Source-level identity: `source + source_listing_id` when available.
- URL hash fallback.
- Cross-source candidate key:
  `brand + model + variant + model_year + km_bucket + city + registration_code + price_band`.
- Optional image hash later for stronger duplicate detection.
- Keep duplicate candidates for review instead of deleting aggressively.

### Temporal Issues

Examples:

- Listing price changes.
- Listing disappears after sale.
- Same car returns later.
- Marketplace refreshes old listings.

Controls:

- Capture date on every record.
- Separate listing snapshot from vehicle identity.
- Track `first_seen_at`, `last_seen_at`, and `is_available`.
- Never overwrite historical prices.

### Source Bias Issues

Examples:

- Certified platforms overrepresent newer, cleaner cars.
- Classified sites contain more noisy/dealer/private listings.
- OEM certified sites are brand-biased.
- Luxury sites distort high-end pricing.
- City coverage differs by source.

Controls:

- Keep `source`, `source_type`, and `source_quality_score`.
- Build source-specific market summaries before combining sources.
- Avoid training a single pricing model until source bias is measured.

## Canonical Null Policy

Do not treat all missing data the same.

### Required Fields

A record cannot enter silver without:

```text
source
source_listing_id or listing_url
captured_at
city
brand
model
model_year
listed_price_inr
km_driven
fuel_type
transmission
raw_record_hash
ingestion_run_id
```

### Conditionally Required Fields

These should be present for strong pricing quality, but a record can be quarantined or marked low confidence if missing:

```text
variant
ownership
registration_code
seller_type
is_available
```

### Optional Fields

These enrich the product but should not block early ingestion:

```text
color
body_type
insurance_valid_until
dealer_name
inspection_score
features
images_count
emi_estimate
location_area
```

## Source Adapter Contract

Each source should implement the same conceptual pipeline:

```text
discover_pages()
capture_raw()
extract_raw_items()
parse_bronze_records()
map_to_canonical_records()
validate_records()
write_outputs()
```

Every adapter must output:

```text
raw snapshot files
bronze records
silver candidate records
quarantine records
run metrics
parser version
```

This prevents one source from becoming a special-case mess.

## Bronze Record Design

Bronze keeps source truth and parser work side by side.

Example:

```text
source_price_text = "5.75 Lakh"
listed_price_inr = 575000
source_km_text = "64K km"
km_driven = 64000
source_title_text = "2021 Renault Kiger"
model_year = 2021
brand = "Renault"
model = "Kiger"
parse_confidence = 0.92
parse_warnings = []
```

Never destroy the source text during parsing.

## Quarantine Strategy

Bad records are useful. They show where parsers are weak.

A quarantined record should include:

```text
source
capture_date
ingestion_run_id
raw_record_hash
listing_url
failure_stage
failure_reasons
raw_payload_path
parser_version
```

Common quarantine reasons:

- `missing_price`
- `missing_model`
- `invalid_year`
- `invalid_km`
- `unknown_fuel_type`
- `unknown_transmission`
- `possible_non_listing_card`
- `parse_low_confidence`
- `duplicate_candidate`

## Source Quality Score

Every source should get a score after each run.

Suggested metrics:

```text
raw_records_captured
valid_silver_records
quarantined_records
validation_pass_rate
required_field_completeness
duplicate_rate
price_parse_success_rate
km_parse_success_rate
variant_completeness
owner_completeness
availability_detection_rate
parser_error_count
```

Use this score to decide which sources deserve more engineering effort.

## Testing Strategy

Each source parser needs tests before it is trusted.

Required tests:

- Price parsing tests.
- Kilometer parsing tests.
- Owner parsing tests.
- Fuel and transmission vocabulary tests.
- Listing-card parser tests against saved raw HTML fixtures.
- Detail-page parser tests when detail pages are used.
- Schema validation tests.
- Quarantine tests.
- Duplicate-key tests.

Fixture rule:

- Save 5 to 10 representative raw records per source.
- Include clean records, missing-field records, ads, sold/unavailable records, and weird formatting.
- Tests should run without network access.

## What You Were Missing In The Old Project

The old notebook jumped from scraping directly to a dataframe and EDA.

For this project, we need the missing middle:

- Source registry.
- Source adapter interface.
- Raw snapshot storage.
- Bronze source-normalized records.
- Canonical schema.
- Validation layer.
- Quarantine layer.
- Parser test fixtures.
- Run metrics.
- Duplicate detection.
- Time-series listing snapshots.
- Source quality reports.
- Completeness scorecards.
- Pricing-ready quality gates.

This middle layer is what turns scraping into a data platform.

## Recommended Next Build Sequence

1. Define canonical schema as Pydantic models.
2. Define validation rules with Pandera.
3. Build shared parsers for price, kilometers, owner count, fuel, transmission, and registration.
4. Create manual fixture records for 3 sources.
5. Build the first source adapter against saved fixtures.
6. Write raw, bronze, silver, and quarantine outputs locally.
7. Add DuckDB quality reports.
8. Only then run live acquisition for one source.

The first real milestone is not "scrape many sites." It is "one source can produce trusted silver records with visible failures."
