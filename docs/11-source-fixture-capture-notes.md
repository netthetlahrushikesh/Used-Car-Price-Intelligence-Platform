# Source Fixture Capture Notes

Date: 2026-06-24

Purpose: record the first source-like fixture capture pass for Spinny, CarDekho, and OLX.

This step turns source reconnaissance into testable parser examples. The goal is not to collect a dataset yet. The goal is to create small, stable examples that make parser behavior reproducible.

## Sources Used

```text
Spinny Hyderabad: https://www.spinny.com/used-cars-in-hyderabad/s/
CarDekho Hyderabad: https://www.cardekho.com/used-cars+in+hyderabad
OLX Hyderabad: https://www.olx.in/hyderabad_g4058526/cars_c84
```

## Fixture Files Created

```text
tests/fixtures/spinny/listing_cards_extracted.json
tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json
tests/fixtures/cardekho/listing_cards_extracted.json
tests/fixtures/olx/listing_cards_extracted.json
```

Each original source fixture has 5 listing-card examples. Spinny also has a 20-record live public search snapshot from the Hyderabad Nexus Sujana Mall hub page.

## What We Learned

### Spinny

Spinny is a strong first clean-source candidate.

Observed fixture pattern:

- Title contains year, brand, and model.
- Price is visible.
- Variant is separate.
- Kilometers are visible and often use `K` suffix.
- Fuel and transmission are clean lowercase labels.
- Registration code is visible.
- Locality or hub is visible.
- EMI is visible but must not be parsed as listed price.

Parser impact:

- Kilometer parser must support decimal `K` values such as `145.5K km`.
- Title parser must handle brand alias `Maruti` as `Maruti Suzuki`.
- Registration parser must support `TS`, `TG`, and `AP` examples.
- Live Spinny records introduced more model families that must be recognized before scaling: Brezza, XUV700, Nexon, Taigun, Slavia, Sonet, Innova Hycross, A4, Tiago EV, and GLA.
- Discounted cards can expose both current and old prices. The parser must keep the first visible listed price and warn with `multiple_price_candidates` instead of choosing the larger crossed-out price.

### CarDekho

CarDekho is a rich source but needs careful parsing.

Observed fixture pattern:

- Title contains year, brand, and model.
- Price, kilometers, fuel, and transmission are visible.
- Owner count appears inside natural-language AI text.
- Deal labels such as `Great Price` are visible.
- Inspection and warranty text can appear in source snippets.
- Seller labels like `Direct Owner` can appear near cards.

Parser impact:

- Ownership parser must extract `1st owner` and `2nd owner` from longer sentences.
- Seller-type parsing should not confuse `Direct Owner` with owner count.
- Narrative fields should be parsed with confidence flags later.

### OLX

OLX is useful but noisier and less complete at listing-card level.

Observed fixture pattern:

- Price, year, kilometers, model title, locality, and posted date are visible.
- Fuel and transmission are not consistently visible in listing-card text.
- Titles may contain hyphenated model names like `Swift-Dzire` and `Wagon-R-1-0`.
- Featured/video labels can appear before the price.

Parser impact:

- Title parser needs model aliases and longest-match logic.
- OLX records should not be expected to become pricing-ready unless fuel and transmission are enriched from detail pages or filters.
- Model normalization must keep canonical model as model family. Example: `Wagon-R-1-0` should become model `Wagon R` with variant `1.0`.
- Classified data will be valuable for testing missingness, quarantine, and enrichment flow.

## Parser Improvements Made

The first fixture pass forced these parser improvements:

- Added brand aliases.
- Added starter known model dictionaries.
- Added longest-match model parsing.
- Added model-family normalization so engine/displacement suffixes stay out of canonical `model`.
- Added live Spinny model-family aliases from the Hyderabad hub snapshot.
- Changed multi-price parsing to prefer the first price candidate and emit a warning.
- Added fixture-based parser tests.

This confirmed the value of fixture-first development: source examples immediately exposed weaknesses that unit examples did not.

## Verification

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
```

Result:

```text
Ran 23 tests
OK
```

Additional checks:

- `git diff --check` passed.
- Fixture JSON parse checks passed.
- ASCII scan passed.

## Next Step

Build canonical schema models and validation logic.

Recommended files:

```text
src/used_car_price_intelligence/schema/
tests/unit/test_schema.py
```

The schema layer should use parser outputs to decide whether a record is:

- valid silver,
- gold pricing-ready,
- or quarantined with reasons.
