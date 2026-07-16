# Source Feature Matrix

Research date: 2026-06-24

Scope: initial public-page reconnaissance for India / Hyderabad used-car sources.

This is not a scraper specification yet. It is a column discovery document. The goal is to understand what fields are commonly visible across sources before writing source adapters.

## Recommendation

Yes, we should proceed column-first.

The correct order is:

1. Inspect source pages.
2. List visible fields per source.
3. Separate common fields from source-specific fields.
4. Design canonical schema.
5. Build parsers and validation rules.
6. Only then write scrapers/source adapters.

This prevents each scraper from creating its own messy dataframe.

## Anti-Bot Boundary

Do not build around bypassing login, CAPTCHA, or anti-bot systems.

Reasons:

- It is brittle.
- It wastes engineering time.
- It can fail silently and poison the dataset.
- It shifts the project away from data engineering into access-control evasion.

For this project, use public pages that load normally, saved fixtures, and source adapters. If a page blocks automation, mark the source as high-maintenance and move to another source.

## Core Fields Seen Across Sources

These should become the first canonical fields:

```text
source
source_listing_id
listing_url
captured_at
city
locality
brand
model
variant
model_year
listed_price_inr
km_driven
fuel_type
transmission
ownership
registration_code
seller_type
is_certified
is_available
raw_record_hash
ingestion_run_id
```

## Strong Optional Fields

These are useful but inconsistent across sources:

```text
emi_amount_inr
original_price_inr
discount_amount_inr
price_label
deal_rating
inspection_status
inspection_score
warranty_label
return_policy_label
finance_label
hub_name
dealer_name
listing_posted_at
body_type
color
seating_capacity
image_url_count
source_quality_tags
```

## Initial Source Comparison

Legend:

- `Y`: clearly visible on public page or search result.
- `P`: partially visible, derived, inconsistent, or needs detail page.
- `N`: not observed in initial pass.
- `?`: needs deeper browser inspection.

| Source | Price | Year | Brand | Model | Variant | KM | Fuel | Transmission | Owner | Reg Code | Locality/Hub | Dealer/Seller Type | Certification/Inspection | EMI/Finance | Deal Rating |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cars24 | Y | Y | Y | Y | Y | Y | Y | Y | N | Y | Y | P | Y | Y | P |
| Spinny | Y | Y | Y | Y | Y | Y | Y | Y | N | Y | Y | P | Y | Y | P |
| CarDekho | Y | Y | Y | Y | P | Y | Y | Y | Y | N | Y | Y | Y | P | Y |
| CarWale | Y | P | P | P | ? | P | P | P | ? | ? | Y | Y | Y | ? | ? |
| OLX | Y | Y | Y | Y | P | Y | P | P | Y | N | Y | Y | P | P | N |
| Droom | Y | P | P | P | ? | ? | ? | ? | ? | ? | ? | P | Y | P | P |
| CarTrade | Y | Y | Y | Y | ? | Y | Y | ? | ? | ? | Y | Y | P | ? | ? |
| Mahindra First Choice | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y | Dealer | Y | P | Y |
| Maruti True Value | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Dealer | Y | P | N |
| Hyundai Promise | Y | Y | Y | Y | Y | ? | Y | Y | ? | ? | P | Dealer | Y | P | ? |
| Honda Auto Terrace | Y | Y | Y | Y | P | Y | Y | Y | Y | N | P | Dealer | Y | ? | ? |
| Toyota U Trust | Y | Y | Y | Y | Y | ? | ? | ? | ? | N | P | Dealer | Y | ? | ? |

## Source Notes

### Cars24

Observed fields:

- Inventory count.
- Stock ownership label.
- Year, brand, model, variant.
- Kilometers.
- Fuel.
- Transmission.
- Registration code.
- EMI amount.
- Listed price and sometimes crossed/old price.
- Extra charges text.
- Hub or locality.
- Inspection/test-drive/finance messaging.

Data issues:

- Price may have multiple values.
- `+ other charges` needs separate flag.
- Ownership count was not obvious in listing-card evidence.
- Detail pages may be needed for richer data.

### Spinny

Observed fields:

- Year, brand, model.
- Price.
- Variant.
- EMI amount.
- Kilometers.
- Fuel.
- Transmission.
- Registration code.
- Hub/locality.
- Quality or reason-to-buy tags.
- Warranty/inspection platform benefits.

Data issues:

- Kilometers appear as `40K km`, `13.5K km`, `143.5K km`.
- Fuel/transmission appear lowercase.
- Owner count was not observed in listing-card evidence.
- Variant can contain trim, engine, and gearbox mixed together.

### CarDekho

Observed fields:

- Year, brand, model.
- Price.
- Kilometers.
- Transmission.
- Fuel.
- Locality/city.
- Owner count inside natural-language AI text.
- Inspection and warranty text.
- Deal label such as `Great Price`.
- Seller action controls.
- Direct owner / featured labels in some cards.
- Body type sections.
- Model-level inventory count and starting price tables.

Data issues:

- Owner count is embedded in narrative text.
- Ads and curated sections appear between listing cards.
- Some variant data is present in links/images but not always clean text.
- AI-generated descriptions should not be treated as ground truth without confidence flags.

### CarWale

Observed fields:

- City inventory count.
- Dealer count.
- Individual seller count.
- Locality names.
- Recently added count.
- Price range.
- Certified/quality report filters.
- Seller type filters.
- Make/model filters.

Data issues:

- Initial public page evidence gives strong aggregate data but less clean card-level text.
- Listing-card extraction likely needs rendered-page inspection.
- Good for source coverage metrics and market-size context.

### OLX

Observed fields:

- Price.
- Year.
- Kilometers.
- Brand/model title.
- Locality.
- Posted date.
- Featured flag.
- Warranty/document-transfer/return/finance labels on some listings.
- Filters for make/model, budget, year, owner count, inspection status, kilometers, fuel, and transmission.

Data issues:

- Card text is compact and inconsistent.
- Fuel/transmission may appear in title, filters, or detail page rather than every listing card.
- Classified listings may contain more spelling and formatting noise.
- Seller type and owner count need careful extraction.

### Droom

Observed fields:

- Inventory count.
- Starting price.
- Fixed price label.
- Trust score / platform trust indicators.
- Refundable token amount messaging.

Data issues:

- More page inspection is needed for reliable card-level fields.
- Good candidate for detail-page fixture research before scraper work.

### CarTrade

Observed fields:

- City inventory count.
- Popular models.
- Price range.
- Brand list.
- Template evidence for make year, car name, car price, kilometers, fuel, city, seller name, and seller phone.

Data issues:

- Initial page contains templated placeholders in some sections.
- Do not collect phone numbers.
- Listing-card extraction needs rendered-page inspection.

### Mahindra First Choice

Observed fields:

- Current Hyderabad page inventory count: 88 certified used cars.
- Rating/score.
- Year, brand, model.
- Variant.
- Kilometers.
- Fuel.
- Transmission.
- Price.
- Locality.
- Request-call-back action.
- Warranty, buyback, return, and pricing-guide messaging.

Data issues:

- Mostly dealer/certified source; useful but biased toward certified stock.
- Owner count and registration code not observed in listing cards.
- Ownership appears as a filter, but not as a per-card value.
- Detail page inspection returned a blocked/403 response during research.
- Rating should be kept as source-specific quality feature.
- First implementation should be listing-card acquisition only.

### Maruti True Value

Observed fields:

- OEM-backed used-car source.
- Dealer discovery by latitude/longitude.
- Structured GraphQL inventory rows.
- Price, year, model, variant, km, fuel, transmission, ownership, registration, dealer, body type, color, certification, warranty code, and ratings.

Data issues:

- Brand bias: Maruti Suzuki inventory only.
- Active row count changes with dealer radius and live inventory.
- Certification and DMS status are source-specific.
- Optional color and DMS fields can be missing on a small number of rows.
- Do not collect dealer contact fields for the model dataset.

### Hyundai Promise

Observed fields from official/dealer pages:

- Certified label.
- Year.
- Brand/model/variant.
- Fuel.
- Transmission.
- Price.
- Warranty/checkpoint messaging.

Data issues:

- Hyundai/dealer pages may vary by dealer.
- Kilometers and location need source-specific inspection.
- Brand/dealer bias.

### Honda Auto Terrace

Observed fields:

- Price.
- Kilometers.
- Model year filter.
- Fuel type filter.
- Transmission filter.
- Body type filter.
- Seating capacity filter.
- Color filter.
- Owner filter.
- Honda model counts.

Data issues:

- Card-level owner may require detail page.
- Mostly Honda certified/dealer source.
- Useful source for optional fields such as body type, seating capacity, and color.

### Toyota U Trust

Observed fields:

- Vehicle listing title.
- Stock/reference ID.
- Year, brand, model, variant.
- Price.
- Dealer/location context.

Data issues:

- Need deeper page inspection for km, fuel, transmission, owner, and location.
- Mostly Toyota certified/dealer source.

## Canonical Schema Decision

The first canonical schema should not try to include every interesting field.

Use three tiers:

### Tier 1: Must-Have

These support core price intelligence:

```text
source
listing_url
captured_at
city
brand
model
model_year
listed_price_inr
km_driven
fuel_type
transmission
```

### Tier 2: High-Value

These improve comparables and pricing confidence:

```text
variant
ownership
registration_code
locality
seller_type
is_certified
inspection_status
is_available
```

### Tier 3: Enrichment

These are useful later but should not block ingestion:

```text
emi_amount_inr
dealer_name
hub_name
body_type
color
seating_capacity
warranty_label
return_policy_label
finance_label
deal_rating
source_quality_tags
```

## What This Means For The First Scraper

Do not start with the hardest site.

Choose the first source using this rule:

```text
first_source_score =
  visible_core_fields
  + stable_listing_cards
  + easy_pagination
  + low_parser_complexity
  - heavy_dynamic_rendering
  - frequent missing fields
```

Based on the first reconnaissance pass, clean technical candidates were:

1. Spinny: clean card structure, strong core fields, but owner count missing.
2. Mahindra First Choice: clean text fields, smaller inventory, certified/dealer bias.
3. CarDekho: rich fields, but more ads/narrative parsing.
4. OLX: large inventory, but noisier classified data.

After the source-trust review, the first live sources should be trusted/certified sources, not OLX.

Recommended MVP order:

1. Spinny.
2. Mahindra First Choice.
3. Maruti Suzuki True Value.
4. One more OEM certified source such as Honda Auto Terrace, Hyundai Promise, or Toyota U Trust.

Cars24, CarDekho, CarWale, and OLX should stay out of the first model-training dataset unless the specific path is
proven to be platform/dealer/OEM-evaluated inventory. OLX should remain a noisy fixture and quarantine stress-test
source only.

## Next Action

The first three trusted source contracts now exist for Hyderabad:

1. Spinny.
2. Mahindra First Choice.
3. True Value.

The next action is not another manual source matrix pass. It is a three-source field comparison followed by a
resumable batch runner for controlled source-city acquisition.

Existing OLX fixtures should stay in the test suite as negative/noisy examples, but OLX should not become a core live adapter.

## Reviewed Source URLs

- Cars24 Hyderabad: https://www.cars24.com/buy-used-cars-hyderabad/
- Spinny Hyderabad: https://www.spinny.com/used-cars-in-hyderabad/s/
- CarDekho Hyderabad: https://www.cardekho.com/used-cars%2Bin%2Bhyderabad
- CarWale Hyderabad: https://www.carwale.com/used/hyderabad/
- OLX Hyderabad: https://www.olx.in/hyderabad_g4058526/cars_c84
- Droom Used Cars: https://droom.in/cars/used
- CarTrade Hyderabad: https://www.cartrade.com/second-hand/hyderabad/
- Mahindra First Choice Hyderabad: https://www.mahindrafirstchoice.com/used-cars/hyderabad
- Maruti Suzuki True Value inventory: https://www.marutisuzukitruevalue.com/buy-car
- Hyundai Promise: https://clicktobuy.hyundai.co.in/hyundaipromise/
- Honda Auto Terrace Hyderabad: https://www.hondaautoterrace.com/used-cars/%2Bin-hyderabad
- Toyota U Trust Hyderabad: https://www.toyotautrust.in/used-cars/hyderabad
