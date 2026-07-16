# Source Trust And Priority Review

Date: 2026-06-24

Purpose: decide whether self-listed/classified sources like OLX should be used for the first real acquisition pipeline.

## Decision

Do not use OLX as an MVP acquisition source.

Keep OLX only for:

- noisy fixture tests,
- quarantine stress testing,
- later market-coverage research,
- understanding the low-trust classified market.

Reason:

- OLX mixes direct-owner and dealer listings.
- Self-listed records can be incomplete, inconsistent, misleading, or poorly formatted.
- Listing-card fields often miss pricing-critical attributes like fuel and transmission.
- The platform has huge coverage, but coverage is not the same as trustworthy price intelligence.

For the first real pipeline, prioritize verified, inspected, certified, or platform/OEM-backed sources.

## Core Dataset Policy Update

Date: 2026-06-25

The model-training dataset should use only trusted, evaluated inventory sources:

- Spinny,
- Mahindra First Choice,
- Maruti Suzuki True Value,
- later OEM certified sources such as Honda Auto Terrace, Hyundai Promise, and Toyota U Trust.

Reason:

- vehicles are inspected/evaluated by a platform, dealer, or OEM-backed program,
- listed prices are less likely to be arbitrary customer self-pricing,
- condition/warranty/ownership signals are more consistent,
- the model target is closer to realistic transactable dealer/platform market price.

Customer-priced or self-listed marketplaces should not be included in the first model-training dataset. They can
remain useful for a separate noisy-market or classifieds analysis after the trusted-source model exists.

## Source Trust Criteria

Prefer sources with:

- inspected or certified inventory,
- warranty or return-policy signals,
- platform-owned or dealer-backed stock,
- consistent listing-card fields,
- less free-form seller text,
- clear price, year, brand, model, km, fuel, and transmission,
- fewer self-reported fields,
- repeatable page structure.

Avoid or delay sources with:

- self-listed records,
- mixed private/dealer inventory with weak verification,
- missing fuel/transmission,
- very low unrealistic prices,
- noisy titles,
- seller-written descriptions,
- duplicate/reposted listings,
- phone/contact-heavy pages.

## Recommended MVP Source Priority

### Tier 1: First Acquisition Candidates

These are best for the first production-quality pipeline.

| Priority | Source | Why |
| --- | --- | --- |
| 1 | Spinny | Inspected/assured positioning, clean cards, strong core fields. |
| 2 | Mahindra First Choice | Multi-brand certified source, warranty/inspection positioning. |
| 3 | Maruti Suzuki True Value | OEM-backed evaluated inventory and strong dealer network. |

Recommended first source:

```text
Spinny
```

Reason:

- Good visible core fields.
- Cleaner card structure.
- Less self-listing noise.
- Strong fit for parser and schema validation.

### Tier 2: Trusted But Brand-Biased Sources

These are useful after the first multi-brand source works.

| Source | Why | Caveat |
| --- | --- | --- |
| Honda Auto Terrace | 350-point inspection and certified Honda inventory claims. | Honda brand bias. |
| Maruti Suzuki True Value | OEM-backed certified used-car channel. | Validated for Hyderabad, but Maruti-only brand bias remains. |
| Hyundai Promise | Hyundai-backed certified pre-owned program. | Hyundai brand bias and dealer-page variability. |
| Toyota U Trust | Toyota certified used-car program with inspection/warranty positioning. | Toyota brand bias and fewer cross-brand examples. |
| Volkswagen Certified Pre-Owned | Certified pre-owned positioning. | May have limited inventory and dealer variability. |

These sources are better for clean data than classifieds, but they will bias the dataset toward specific brands and certified-condition vehicles.

### Tier 3: Rich Marketplaces With Filtering

Use only after the quality layer is strong.

| Source | Use Case | Caveat |
| --- | --- | --- |
| CarDekho | Rich listings, deal labels, owner text, marketplace breadth. | Narrative text, ads, direct-owner/dealer mix. |
| CarWale | Market-size and coverage context. | Card-level fields need deeper rendered inspection. |
| CarTrade | Marketplace expansion and dealer context. | Placeholder/templated sections and contact fields. |
| Droom | Later marketplace research. | Card-level completeness needs more inspection. |

These can help coverage, but should not be first because they increase parser and trust complexity.

### Tier 4: Research Only For Now

| Source | Reason |
| --- | --- |
| OLX | Self-listed/classified data, mixed direct owner/dealer inventory, noisy titles, missing fields, high misinformation risk. |
| Quikr/Facebook Marketplace style sources | Similar self-listing and data-quality risk. |

Do not delete OLX fixtures. They are valuable as negative examples. The quality layer should prove that it can quarantine or mark such records as non-pricing-ready.

## What This Changes

Previous thinking:

```text
Spinny -> CarDekho -> OLX
```

New trusted-core thinking:

```text
Spinny -> Mahindra First Choice -> True Value -> one more OEM certified source
```

Keep Cars24, CarDekho, and CarWale as later research/benchmark sources unless the specific path is proven to be
dealer/platform-evaluated inventory only.

Keep OLX as a noisy control source, not a core dataset source.

## Validation Update

Date: 2026-06-25

The first three trusted-source contracts are now validated in Hyderabad:

| Source | Validated run | Result |
| --- | --- | --- |
| Spinny | `run_20260625_spinny_hyderabad_manifest_60_detail60_smoke` | 60/60 pricing-ready, 0 quarantined |
| Mahindra First Choice | `run_20260625_mfc_hyderabad_40_smoke` | 40/40 pricing-ready, 0 quarantined |
| Maruti Suzuki True Value | `run_20260625_true_value_hyderabad_40_smoke` | 40/40 pricing-ready, 0 quarantined |

This does not mean the dataset is ready for modeling yet. It means the first three source contracts are strong enough
to move from source proving into controlled batch acquisition.

## Data Quality Implications

Trusted sources reduce but do not eliminate quality issues.

Even certified sources can still have:

- missing owner count,
- missing registration code,
- variant/model ambiguity,
- price labels and EMI confusion,
- source bias toward newer or cleaner cars,
- brand bias in OEM programs,
- sold/unavailable listings,
- changing prices.

So the quality architecture still matters:

```text
raw -> bronze -> silver -> gold_pricing_ready -> quarantine
```

## Updated First Build Plan

1. Keep existing OLX fixtures for stress tests.
2. Do not build the first live OLX adapter.
3. Build schema validation and quarantine logic next.
4. Build the first source adapter for Spinny.
5. Add Mahindra First Choice as the second source.
6. Add True Value as the third source.
7. Reconsider CarDekho later with trusted/certified filters.
8. Reconsider OLX only for separate "classified market noise" analysis, not core price intelligence.

## Sources Checked

- Spinny: https://www.spinny.com/
- Spinny Assured: https://www.spinny.com/spinny-assured/
- Cars24 used cars: https://www.cars24.com/buy-used-cars/
- Cars24 warranty/why Cars24: https://www.cars24.com/why-cars24/warranty/
- Mahindra First Choice: https://www.mahindrafirstchoice.com/
- Mahindra First Choice warranty: https://www.mahindrafirstchoice.com/warranty
- Honda Auto Terrace: https://www.hondaautoterrace.com/
- Toyota U Trust: https://www.toyotautrust.in/
- Toyota certified used cars: https://www.toyotabharat.com/certified-used-cars/
- Hyundai Promise: https://clicktobuy.hyundai.co.in/hyundaipromise/
- Hyundai H Promise: https://hmp.hyundaimotor.in/click-to-buy/h-promise
- Volkswagen Certified Pre-Owned India: https://www.vwcertifiedpreowned.co.in/
- OLX used cars India: https://www.olx.in/cars_c84
- OLX Hyderabad used cars: https://www.olx.in/hyderabad_g4058526/cars_c84
