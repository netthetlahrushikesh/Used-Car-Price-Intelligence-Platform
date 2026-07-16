# Parser Specifications

Status: draft v0.1

Created: 2026-06-24

Purpose: define shared parser behavior before writing source adapters or live scrapers.

These parsers convert messy source text into canonical values. They are source-independent by default. Source adapters can add source-specific extraction logic, but normalized parsing should stay centralized.

## Why This Matters

The old notebook moved quickly from scraped text into a dataframe. That works for one source when the shape is familiar. It breaks when multiple sources use different text formats.

For this project, parsing is a product system:

- Every parser has a clear input and output.
- Every parser returns confidence and warnings.
- Raw source text is preserved.
- Invalid values are quarantined instead of guessed.
- Parser behavior is testable without network access.

## Parser Result Contract

Every parser should return the same conceptual shape:

```yaml
raw_value: original source text
normalized_value: parsed canonical value or null
confidence: 0.0 to 1.0
warnings: []
failure_reason: null
```

Examples:

```yaml
raw_value: "5.75 Lakh"
normalized_value: 575000
confidence: 0.98
warnings: []
failure_reason: null
```

```yaml
raw_value: "Call for price"
normalized_value: null
confidence: 0.0
warnings:
  - missing_price
failure_reason: missing_price
```

## Global Text Normalization

Before field-specific parsing:

1. Convert input to string.
2. Strip leading and trailing whitespace.
3. Collapse repeated whitespace into one space.
4. Normalize common separators: `|`, `/`, bullet-like separators, and newlines.
5. Convert known empty tokens to null.
6. Preserve the original raw value separately.

Null tokens:

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
"Call for price"
"Ask for price"
```

Do not use parser defaults to invent missing data.

## Price Parser

Canonical output: `listed_price_inr` as integer.

Input examples:

```text
Rs 5.75L
5.75 Lakh
5.75 Lac
575000
5,75,000
Rs. 12.4 lakh
1.02 Cr
10200000
```

Rules:

- Remove currency words and punctuation: `Rs`, `INR`, `rupees`, commas, extra spaces.
- Convert lakh/lac/l suffixes to `value * 100000`.
- Convert crore/cr suffixes to `value * 10000000`.
- Convert k/thousand suffixes to `value * 1000` only when clearly used for price.
- Round to nearest integer.
- Reject values that are missing, zero, negative, or clearly non-price text.

Initial validity bounds:

```text
minimum_soft_price_inr = 50000
maximum_soft_price_inr = 50000000
```

Bounds are warnings, not automatic deletion, because unusual cars can exist. Gold pricing-ready rows should reject impossible values after validation.

Common warnings:

```text
missing_price
multiple_price_candidates
price_below_soft_minimum
price_above_soft_maximum
price_text_contains_emi
price_text_contains_extra_charges
```

Important rule:

- EMI must never be parsed as listed price.
- Crossed/original price must be stored separately from listed price.
- If an isolated listed-price field still contains multiple price candidates, keep the first candidate as the current listed price and emit `multiple_price_candidates`.
- `+ other charges` should become a warning or future fee field, not be added to listed price.

## Kilometer Parser

Canonical output: `km_driven` as integer.

Input examples:

```text
64K km
64,000 kms
64000
143.5K km
13,500 KM
Driven 42,300 km
```

Rules:

- Remove `km`, `kms`, `kilometer`, `kilometers`, and `driven`.
- Remove commas and extra spaces.
- Convert `K` suffix to `value * 1000`.
- Round decimal K values to nearest integer.
- Reject negative values and non-distance text.

Initial validity bounds:

```text
minimum_km = 0
maximum_soft_km = 300000
maximum_hard_km = 500000
```

Common warnings:

```text
missing_km
km_above_soft_maximum
km_above_hard_maximum
ambiguous_km_text
```

Gold rule:

- `km_driven` must be present and below the hard maximum.

## Ownership Parser

Canonical output: `ownership` as integer or null.

Input examples:

```text
1st owner
First Owner
2 owners
Second owner
3rd
Single owner
Direct Owner
```

Rules:

- Map first/single/1st to `1`.
- Map second/2nd to `2`.
- Map third/3rd to `3`.
- Map fourth/4th to `4`.
- Leave `Direct Owner` as seller context unless a numeric owner count is also present.

Common warnings:

```text
missing_ownership
ambiguous_ownership_text
owner_text_is_seller_type_not_owner_count
```

Gold rule:

- Ownership is high-value but not required for first gold pricing-ready rows.
- If ownership is present, it must be between 1 and 5.

## Fuel Type Parser

Canonical output: controlled vocabulary.

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

Rules:

- Match case-insensitively.
- Normalize `Petrol + CNG`, `Petrol/CNG`, and `CNG Petrol` to `petrol_cng`.
- Normalize `EV` to `electric`.
- Normalize `Gasoline` to `petrol`.
- Use `unknown` only when the source text exists but cannot be mapped.
- Return null when the field is truly missing.

Common warnings:

```text
missing_fuel_type
unknown_fuel_type
multiple_fuel_candidates
```

Gold rule:

- Fuel type must not be null or `unknown`.

## Transmission Parser

Canonical output: controlled vocabulary.

Allowed values:

```text
manual
automatic
amt
cvt
dct
unknown
```

Rules:

- Match case-insensitively.
- Normalize `MT` to `manual`.
- Normalize `AT` and `Auto` to `automatic`, unless the source explicitly says `AMT`.
- Normalize `DSG` to `dct`.
- Keep `AMT`, `CVT`, and `DCT` separate because they can affect pricing.
- Return null when truly missing.

Common warnings:

```text
missing_transmission
unknown_transmission
multiple_transmission_candidates
```

Gold rule:

- Transmission must not be null or `unknown`.

## Registration Parser

Canonical outputs:

```text
registration_code
registration_state
registration_type
registration_year
```

Input examples:

```text
TS07
TS-07
TG07
AP 09
KA-03
22 BH 1234 AA
Telangana
Hyderabad
```

Rules:

- Extract two-letter Indian registration prefix plus optional district number.
- Normalize `TS-07`, `TS 07`, and `TS07` to `TS07`.
- Map state prefixes to state names when possible.
- Detect Bharat/BH-series registrations separately. Example: `22 BH 1234 AA` should not be forced into a state registration.
- If only city/state text exists, populate `registration_state` when reliable and leave `registration_code` null.
- Do not infer registration code from city alone.

Common warnings:

```text
missing_registration
registration_state_only
unknown_registration_prefix
ambiguous_registration_text
bharat_series_registration
```

Gold rule:

- Registration is high-value but not required for first gold pricing-ready rows.

## Title Parser

Canonical outputs:

```text
model_year
brand
model
variant
```

Input examples:

```text
2021 Renault Kiger RXZ Turbo CVT
Maruti Suzuki Baleno Delta 2019
2018 Hyundai Creta 1.6 SX Diesel
Honda City VX CVT Petrol
```

Rules:

- Extract a realistic four-digit year from title when present.
- Prefer year near the beginning, but support year at the end.
- Do not parse full listing-card text as title if it also contains posted dates, prices, kilometers, or locality. Source adapters should pass the isolated title text to `parse_title`.
- Match known brands using longest match first. Example: `Maruti Suzuki` before `Maruti`.
- Support brand aliases. Example: `Maruti` should normalize to `Maruti Suzuki`.
- After removing year and brand, split remaining text into model and variant using known model dictionaries when available.
- Match known models using longest match first. Example: `Hector Plus` before `Hector`.
- Keep canonical `model` as the comparable model family. Engine, displacement, gearbox, and trim details should move to `variant`.
- Example: `Wagon-R-1-0` should normalize to model `Wagon R` and variant `1.0`, not model `Wagon R 1.0`.
- If no model dictionary exists yet, use the first remaining token as a temporary model and keep the rest as variant with lower confidence.
- Preserve full source title in bronze.

Confidence guidance:

```text
0.95 to 1.00: year, brand, and model matched from known dictionaries
0.85 to 0.94: year and brand matched, model inferred from remaining text
0.70 to 0.84: brand matched, year or model inferred
below 0.70: do not allow into gold without review
```

Common warnings:

```text
missing_title
missing_model_year
unknown_brand
unknown_model
variant_inferred
multiple_year_candidates
```

Gold rule:

- `model_year`, `brand`, and `model` are required.
- `variant` is high-value but not required for first gold pricing-ready rows.

## Seller Type Parser

Canonical output:

```text
platform
dealer
individual
oem_certified
unknown
```

Rules:

- Platform-owned inventory should map to `platform`.
- Dealer marketplace listings should map to `dealer`.
- Owner/direct-owner classifieds should map to `individual`.
- OEM certified programs should map to `oem_certified`.
- Do not collect phone numbers or personal contact fields.

Gold rule:

- Seller type is high-value but not required for first gold pricing-ready rows.

## Availability Parser

Canonical output: boolean or null.

Rules:

- Map sold, unavailable, booked, reserved to `false`.
- Map active listing cards to `true` only when the source clearly represents active inventory.
- Use null when availability cannot be determined.

Common warnings:

```text
availability_unknown
sold_or_unavailable_listing
```

## Completeness Score Calculation

Required completeness:

```text
present_required_fields / total_required_fields
```

High-value completeness:

```text
present_high_value_fields / total_high_value_fields
```

Optional completeness:

```text
present_optional_fields / total_optional_fields
```

Overall completeness initial weighting:

```text
required_completeness_score * 0.70
+ high_value_completeness_score * 0.20
+ optional_completeness_score * 0.10
```

Gold rule:

```text
required_completeness_score == 1.0
parse_confidence >= 0.90
no critical parser warnings
```

## Quarantine Triggers

Critical parser failures:

```text
missing_price
missing_km
missing_model_year
missing_brand
missing_model
missing_fuel_type
missing_transmission
unknown_fuel_type
unknown_transmission
invalid_price
invalid_km
invalid_model_year
parse_confidence_below_gold_threshold
```

Non-critical warnings:

```text
missing_variant
missing_ownership
missing_registration
registration_state_only
missing_seller_type
missing_locality
missing_availability
```

## Test Requirements

Before live scraping, each parser should have tests for:

- Clean happy paths.
- Empty/null tokens.
- Weird spacing.
- Commas and suffixes.
- Mixed casing.
- Multiple candidates in one string.
- Invalid values.
- Source-like examples from Spinny, CarDekho, and OLX.

The first parser implementation should be tested offline with fixtures only.

## Next Implementation Step

Create:

```text
src/used_car_price_intelligence/parsers/
tests/unit/test_parsers.py
```

Suggested first functions:

```text
parse_price_inr(text)
parse_km_driven(text)
parse_ownership(text)
parse_fuel_type(text)
parse_transmission(text)
parse_registration(text)
parse_title(text)
normalize_null(text)
```
