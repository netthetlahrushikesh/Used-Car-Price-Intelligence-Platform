# Canonical Listing Schema

Status: draft v0.1

Created: 2026-06-24

Purpose: define the first trusted used-car listing contract before writing scrapers.

## Design Goals

The canonical schema should:

- Support fair-price estimation and comparable listings.
- Work across multiple Indian used-car sources.
- Separate required pricing fields from optional enrichment fields.
- Preserve source lineage.
- Make missingness measurable.
- Prevent messy source-specific dataframes.

## Dataset Layers

The same vehicle listing can exist in multiple layers:

```text
raw_capture
bronze_source_record
silver_canonical_listing
gold_pricing_ready_listing
```

Only `gold_pricing_ready_listing` is allowed for pricing intelligence, dashboards, and model training.

## Field Groups

### Identity And Lineage

| Field | Type | Required For Gold | Notes |
| --- | --- | --- | --- |
| `listing_id` | string | Y | Internal deterministic ID. |
| `source` | string | Y | Source key from `config/source_registry.yml`. |
| `source_listing_id` | string/null | N | Native source ID when available. |
| `listing_url` | string | Y | Canonical URL or captured source URL. |
| `captured_at` | datetime | Y | UTC timestamp of capture. |
| `ingestion_run_id` | string | Y | Unique run ID for traceability. |
| `raw_record_hash` | string | Y | Hash of raw source record. |
| `parser_version` | string | Y | Parser version used to produce canonical record. |
| `schema_version` | string | Y | Canonical schema version. |

Rule:

- Gold requires either `source_listing_id` or a stable `listing_url`, but `listing_url` should still be stored whenever available.

### Location

| Field | Type | Required For Gold | Notes |
| --- | --- | --- | --- |
| `city` | string | Y | Example: Hyderabad. |
| `state` | string/null | N | Example: Telangana. |
| `locality` | string/null | N | Area, hub, or neighborhood. |
| `hub_name` | string/null | N | Platform hub or store name. |
| `registration_state` | string/null | N | Example: Telangana. |
| `registration_code` | string/null | N | Example: TS07. |
| `registration_type` | enum/null | N | `state_rto`, `bharat_series`, or unknown. |
| `registration_year` | integer/null | N | Useful for Bharat/BH-style registrations. |

Rule:

- `city` is required for gold because price intelligence is location-sensitive.
- Registration should not be treated as a simple state code only. Bharat/BH registrations are not tied to one state.
- Do not infer registration code from city alone.

### Vehicle Attributes

| Field | Type | Required For Gold | Notes |
| --- | --- | --- | --- |
| `brand` | string | Y | Normalized make. |
| `model` | string | Y | Normalized model family used for comparables. |
| `variant` | string/null | N | Trim, engine, gearbox, edition, or displacement details. |
| `model_year` | integer | Y | Vehicle manufacturing or model year. |
| `manufacture_year` | integer/null | N | Use when source separately exposes manufacturing year. |
| `registration_year` | integer/null | N | Use when source separately exposes first registration year. |
| `fuel_type` | enum | Y | Controlled vocabulary. |
| `transmission` | enum | Y | Controlled vocabulary. |
| `km_driven` | integer | Y | Normalized kilometers. |
| `ownership` | integer/null | N | 1 for first owner, 2 for second owner. |
| `body_type` | enum/null | N | Hatchback, sedan, SUV, etc. |
| `color` | string/null | N | Normalized color when available. |
| `seating_capacity` | integer/null | N | Useful later for enrichment. |

Rules:

- `model_year` must be realistic.
- If a source separately exposes manufacturing year and registration year, store both instead of overwriting one with the other.
- Use `model_year` for the headline vehicle year used in comparable grouping, and preserve source-specific year text in bronze.
- `model` should not include engine or displacement details such as `1.0`, `1.2`, `2.0`, `Turbo`, `CVT`, or `DCT`.
- Those details should be preserved in `variant` or later structured fields.
- `km_driven` must be non-negative and realistic.
- `fuel_type` and `transmission` must map to controlled vocabularies.

### Pricing

| Field | Type | Required For Gold | Notes |
| --- | --- | --- | --- |
| `listed_price_inr` | integer | Y | Main listed price in INR. |
| `original_price_inr` | integer/null | N | Crossed or previous price. |
| `discount_amount_inr` | integer/null | N | Derived or explicit discount. |
| `emi_amount_inr` | integer/null | N | Monthly EMI shown by source. |
| `currency` | string | Y | Always `INR` for initial version. |
| `price_label` | string/null | N | Source text such as fixed price. |
| `deal_rating` | string/null | N | Source-specific rating like great price. |

Rules:

- `listed_price_inr` must be positive.
- EMI must not replace listed price.
- Extra fees should be captured separately later, not mixed into listed price.

### Seller And Availability

| Field | Type | Required For Gold | Notes |
| --- | --- | --- | --- |
| `seller_type` | enum/null | N | Dealer, platform, individual, unknown. |
| `dealer_name` | string/null | N | Do not store personal phone numbers. |
| `is_certified` | boolean/null | N | Certified or platform-inspected listing. |
| `inspection_status` | string/null | N | Source-specific inspection label. |
| `inspection_score` | float/null | N | Source-specific score if available. |
| `warranty_label` | string/null | N | Warranty text. |
| `return_policy_label` | string/null | N | Return policy text. |
| `finance_label` | string/null | N | Finance availability label. |
| `is_available` | boolean/null | N | Availability flag when known. |
| `listing_posted_at` | datetime/null | N | Posted date when available. |

Rule:

- Availability is high-value but not required for the first gold version because many sources do not expose it cleanly on listing cards.

### Quality And Completeness

| Field | Type | Required For Gold | Notes |
| --- | --- | --- | --- |
| `required_completeness_score` | float | Y | 0.0 to 1.0. |
| `high_value_completeness_score` | float | Y | 0.0 to 1.0. |
| `optional_completeness_score` | float | Y | 0.0 to 1.0. |
| `overall_completeness_score` | float | Y | Weighted completeness score. |
| `pricing_ready_flag` | boolean | Y | True only when gold rules pass. |
| `parse_confidence` | float | Y | Parser confidence, 0.0 to 1.0. |
| `parse_warnings` | list[string] | Y | Empty list when clean. |

Rule:

- A record can be stored in silver with warnings, but gold requires no critical warnings.

## Controlled Vocabularies

### Fuel Type

Allowed values:

```text
petrol
diesel
cng
petrol_cng
electric
hybrid
lpg
unknown
```

Gold rule:

- `unknown` is not allowed in gold pricing-ready rows.

### Transmission

Allowed values:

```text
manual
automatic
amt
cvt
dct
unknown
```

Gold rule:

- `unknown` is not allowed in gold pricing-ready rows.

### Seller Type

Allowed values:

```text
platform
dealer
individual
oem_certified
unknown
```

### Body Type

Allowed values:

```text
hatchback
sedan
suv
muv
coupe
convertible
pickup
van
unknown
```

## Gold Pricing-Ready Rule

A row can enter `gold_pricing_ready_listing` only if:

```text
required_completeness_score == 1.0
listed_price_inr > 0
km_driven >= 0
model_year is realistic
fuel_type != unknown
transmission != unknown
parse_confidence >= 0.90
parse_warnings has no critical warnings
```

Required fields:

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
currency
raw_record_hash
ingestion_run_id
parser_version
schema_version
```

## Null Handling

Normalize these to null in bronze:

```text
""
" "
"-"
"--"
"NA"
"N/A"
"Not Available"
"null"
"None"
```

Do not fake missing values.

Rules:

- Missing required fields quarantine the record.
- Missing high-value fields reduce confidence.
- Missing optional fields are tracked but do not block ingestion.

## Example Gold Record

```yaml
listing_id: spinny_8f2e_example
source: spinny
source_listing_id: null
listing_url: https://www.spinny.com/example-listing
captured_at: 2026-06-24T03:00:00Z
ingestion_run_id: run_20260624_spinny_hyderabad_001
raw_record_hash: sha256_example
parser_version: spinny_parser_v0.1
schema_version: canonical_listing_v0.1
city: Hyderabad
state: Telangana
locality: Gachibowli
hub_name: Spinny Park Hyderabad
registration_state: Telangana
registration_code: TS07
brand: Renault
model: Kiger
variant: RXZ Turbo CVT
model_year: 2021
fuel_type: petrol
transmission: automatic
km_driven: 64000
ownership: null
body_type: suv
color: null
seating_capacity: null
listed_price_inr: 575000
original_price_inr: null
discount_amount_inr: null
emi_amount_inr: 12000
currency: INR
price_label: fixed_price
deal_rating: null
seller_type: platform
dealer_name: null
is_certified: true
inspection_status: inspected
inspection_score: null
warranty_label: platform_warranty
return_policy_label: null
finance_label: finance_available
is_available: true
listing_posted_at: null
required_completeness_score: 1.0
high_value_completeness_score: 0.75
optional_completeness_score: 0.35
overall_completeness_score: 0.82
pricing_ready_flag: true
parse_confidence: 0.94
parse_warnings: []
```

## Implementation Notes

The first code version should implement this schema as:

1. Pydantic models for row-level validation.
2. Pandera schema for dataframe-level validation.
3. Parser functions for normalized fields.
4. Quarantine records for validation failures.
5. DuckDB queries for completeness reports.

## Next Step

Build parser specifications for:

- Price.
- Kilometers.
- Ownership.
- Fuel type.
- Transmission.
- Registration code.
- Title to year, brand, model, and variant.
