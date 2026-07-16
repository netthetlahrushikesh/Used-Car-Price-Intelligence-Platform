# Blind Spots And Risk Review

Date: 2026-06-24

Purpose: identify data, parsing, schema, and modeling blind spots before the project scales beyond fixtures.

This document is intentionally conservative. The goal is to catch problems while they are cheap, not after a large scrape creates a broken dataset.

## Executive Summary

The biggest future risks are not just null values. The dangerous issues are values that look valid but mean the wrong thing.

Examples:

- `Wagon R 1.0` entering `model` instead of `variant`.
- Posted year being mistaken for model year.
- EMI being mistaken for listed price.
- `Direct Owner` being mistaken for first owner.
- BH registration being forced into a state RTO code.
- Certified platform prices being mixed with classified prices without source bias controls.

The project should keep moving, but schema validation must be built before more scraping.

## Immediate Blind Spots Found

### 1. Model Family vs Variant

Problem:

- Source titles mix model family, trim, engine size, gearbox, special edition, and fuel text.
- If all of this goes into `model`, grouping becomes messy.

Example:

```text
Bad:
model = Wagon R 1.0

Good:
model = Wagon R
variant = 1.0
```

Decision:

- `model` means comparable model family.
- Engine, trim, gearbox, and edition text go to `variant` or future structured fields.

Status:

- Fixed for `Wagon-R-1-0`.
- More model dictionaries are still needed.

### 2. Model Year vs Registration Year vs Manufacture Year

Problem:

- Listings may show model year, manufacturing year, first registration year, or registration issue year.
- These are not always the same.
- BH registration contains a year-like prefix that must not be confused with model year.

Controls:

- Keep `model_year` for comparable grouping.
- Add optional `manufacture_year`.
- Add optional `registration_year`.
- Preserve source year text in bronze.
- Do not parse full listing-card text as vehicle title.

### 3. Full Card Text Can Poison Parsers

Problem:

Full card text often contains:

```text
price
posted date
model year
kilometers
locality
badges
seller labels
```

If the title parser receives full card text, it may pick the wrong year or model.

Controls:

- Source adapters must extract field-specific text first.
- Shared parsers should parse isolated field text, not unstructured full cards unless explicitly designed for that.
- Keep `listing_text` in bronze for traceability, but do not use it as canonical title input.

### 4. Price Ambiguity

Problem:

Listing cards may include:

- Listed price.
- Original or crossed price.
- EMI amount.
- Token amount.
- Discount.
- Extra charges.
- "Starting from" price.
- Price range.

Controls:

- Keep separate fields:
  - `listed_price_inr`
  - `original_price_inr`
  - `discount_amount_inr`
  - `emi_amount_inr`
  - `token_amount_inr`
  - `price_label`
  - `extra_charges_flag`
- Never use EMI as listed price.
- Do not parse aggregate page prices as listing prices.
- If one isolated listed-price field contains multiple price candidates, keep the first candidate as the current listed price and emit `multiple_price_candidates`.
- The first live Spinny Hyderabad hub snapshot found two discounted cards where a maximum-price rule would have selected the old crossed price instead of the current listed price.

### 5. Registration Is Not Just State Code

Problem:

- Indian registrations include state RTO formats and Bharat/BH series.
- Telangana changed from TS to TG for newer registrations, while TS remains valid for older plates.
- AP plates can appear in Hyderabad listings.
- Registration state can differ from sale city.

Controls:

- Store `registration_code`.
- Store `registration_state`.
- Store `registration_type`.
- Store `registration_year` where available.
- Do not infer registration from sale city.

Status:

- Parser now detects BH registrations as `bharat_series`.

### 6. Fuel And Transmission Are Pricing-Critical But Often Missing

Problem:

- OLX-like listing cards may omit fuel and transmission.
- Some source titles include `Diesel`, `Petrol`, `CVT`, or `AMT`, but not consistently.

Controls:

- For gold pricing-ready rows, fuel and transmission remain required.
- If listing cards omit them, use detail-page enrichment or keep record out of gold.
- Do not infer transmission from variant unless confidence is high.

### 7. Ownership vs Seller Type

Problem:

`Direct Owner` and `First Owner` are different.

Controls:

- `ownership` is owner count.
- `seller_type` is dealer/platform/individual.
- Do not convert `Direct Owner` into owner count.

Status:

- Parser already warns on `Direct Owner` when no owner count is present.

### 8. Condition, Accident History, Service History, And Warranty

Problem:

Used-car value depends heavily on condition and history, but listing cards rarely expose this cleanly.

Important fields:

```text
condition_grade
inspection_score
accident_history
flood_damage_flag
service_history_available
insurance_valid_until
warranty_label
return_policy_label
tyre_condition
ownership_transfer_status
```

Controls:

- Treat these as enrichment, not initial gold requirements.
- Do not assume certified means accident-free.
- Preserve source-specific inspection labels separately.

### 9. Source Bias

Problem:

Different sources represent different market slices:

- Certified platforms skew newer/cleaner.
- Classified sites are noisier and include individual sellers.
- OEM certified sources are brand-biased.
- Luxury sources distort high-price distributions.

Controls:

- Always keep `source` and `source_type`.
- Build source-specific summaries before combining sources.
- Do not train a single model until source bias is measured.
- Include `seller_type` and `is_certified` in gold features later.

### 10. Duplicates And Relisting

Problem:

The same car can appear:

- Across multiple sites.
- On dealer and marketplace pages.
- Reposted after expiry.
- With price changes.

Controls:

- Store listing snapshots over time.
- Keep source listing ID when available.
- Build candidate duplicate keys using:

```text
brand
model
variant
model_year
km_bucket
city
registration_code
price_band
```

- Do not delete duplicates too aggressively.

### 11. Sold/Unavailable Listings

Problem:

Sold listings can remain visible and distort price intelligence.

Controls:

- Track `is_available` when visible.
- Track `first_seen_at` and `last_seen_at`.
- Store snapshots, not only latest row.
- Do not treat disappearance as confirmed sale without source evidence.

### 12. Outliers And Fraud-Like Records

Problem:

Some records will be real but extreme; others will be wrong.

Examples:

- Very low price bait listings.
- Wrong kilometers.
- Accident/flood vehicles.
- Commercial vehicles mixed into passenger cars.
- Modified vehicles.

Controls:

- Add outlier flags instead of immediate deletion.
- Keep soft and hard validation bounds.
- Quarantine impossible records.
- Review outlier examples before model training.

### 13. Market Time And Seasonality

Problem:

Used-car prices change with time, demand, inventory, and source behavior.

Controls:

- Every record needs `captured_at`.
- Gold analytics should be time-windowed.
- Model datasets should include as-of date.
- Avoid mixing old and fresh records without time features.

### 14. City, Locality, And Registration Mismatch

Problem:

Listing city, car hub, seller locality, and registration state can differ.

Controls:

- Store sale/listing city.
- Store locality or hub.
- Store registration state separately.
- Do not assume Hyderabad listing means Telangana registration.

### 15. Missingness Is Not Random

Problem:

Missing fields are often systematic:

- Classified sites may omit transmission.
- Certified sites may hide owner count.
- Some sellers omit bad history.

Controls:

- Report completeness by source.
- Do not blindly impute pricing-critical fields.
- Treat missingness itself as a source-quality signal.

## Schema Gaps To Add Soon

Recommended additions before first real adapter:

```text
source_title_text
source_variant_text
manufacture_year
registration_year
registration_type
token_amount_inr
extra_charges_flag
condition_grade
accident_history
service_history_available
commercial_vehicle_flag
source_record_type
first_seen_at
last_seen_at
```

Not all need to be gold-required. Most should start as optional/enrichment fields.

## Parser Gaps To Add Soon

High-priority parser work:

- `parse_model_variant()` with richer model dictionary.
- `parse_years()` that separates model/manufacture/registration/posting years.
- `parse_price_block()` that separates listed price, EMI, token, old price, and extra charges.
- `parse_seller_type()`.
- `parse_availability()`.
- `parse_source_record_type()` to reject ads, filters, and aggregate sections.

## Fixture Gaps

Add fixtures for:

- BH registration.
- Multiple prices in one card.
- Crossed price plus listed price.
- EMI-only text.
- Missing fuel/transmission.
- Sold/unavailable card.
- Dealer card vs individual card.
- Full card text that includes posted date and model year.
- CNG/petrol-CNG listings.
- EV listings.
- Hybrid listings.
- Luxury model names.
- Commercial/taxi-like listings.

## External Knowledge Check

The external review reinforces that valuation depends on more than year, price, and kilometers:

- KBB describes used-car pricing factors including mileage, condition, options, seasonal trends, and regional variation.
- Edmunds describes valuation factors including supply, demand, incentives, options, nearby transactions, mileage, location, and condition.
- NHTSA's VIN decoder shows that robust vehicle identity can include model year, make/model, plant, and other VIN-derived attributes, though Indian listing pages will usually not expose VIN.
- Indian BH/Bharat registration needs separate handling because it is not a normal state RTO code.

## Current Risk Ranking

| Risk | Severity | Current Status | Next Action |
| --- | --- | --- | --- |
| Title/model normalization | High | Partially handled | Expand model dictionary and tests |
| Price ambiguity | High | Partially handled | Build price block parser |
| Fuel/transmission missing on OLX | High | Known gap | Detail-page enrichment or quarantine |
| Model/manufacture/registration year confusion | High | Documented | Build year parser |
| Registration special cases | Medium | BH added | Add more registration fixtures |
| Source bias | High | Documented | Add source quality reports |
| Duplicates/relisting | High | Documented | Add identity snapshot design |
| Condition/history absence | Medium | Documented | Keep optional enrichment fields |
| Sold/unavailable listings | Medium | Documented | Add availability parser and fixtures |
| Full-card parser contamination | High | Documented | Adapters must pass isolated fields |

## Decision

Do not move directly to live scraping yet.

Next step should be canonical schema validation and quarantine logic, because these blind spots need a place to surface as explicit failures or warnings.

Recommended next implementation:

```text
src/used_car_price_intelligence/schema/
src/used_car_price_intelligence/quality/
tests/unit/test_schema.py
tests/unit/test_quality.py
```

This will let us say:

- record is valid silver,
- record is gold pricing-ready,
- or record is quarantined with reasons.

## Sources Checked

- Kelley Blue Book used-car values: https://www.kbb.com/car-values/
- Kelley Blue Book used-car pricing: https://www.kbb.com/used-cars/
- Edmunds appraisal overview: https://www.edmunds.com/appraisal/
- NHTSA VIN decoder: https://www.nhtsa.gov/vin-decoder
- NHTSA vPIC VIN decoder: https://vpic.nhtsa.dot.gov/decoder/
- NIC BH Series overview: https://www.nic.gov.in/newsletter-content/bh-series/
- PIB MoRTH BH registration update: https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=1883991
- Parivahan VAHAN services: https://vahan.parivahan.gov.in/nrservices/
