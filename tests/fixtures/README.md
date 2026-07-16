# Parser Fixtures

Purpose: store small, representative source examples used to test parsers and source adapters without network access.

Do not store large raw datasets here. Keep only minimal examples needed for tests.

## First Fixture Sources

```text
tests/fixtures/spinny/
tests/fixtures/mahindra_first_choice/
tests/fixtures/true_value/
tests/fixtures/cardekho/
tests/fixtures/olx/
```

Each source should eventually contain:

```text
listing_cards_raw.html
listing_cards_extracted.json
detail_page_raw.html
detail_page_extracted.json
expected_bronze_records.json
expected_silver_records.json
expected_quarantine_records.json
```

## Fixture Rules

- Include clean records.
- Include missing-field records.
- Include weird formatting.
- Include sold or unavailable records if the source shows them.
- Include cards that are not listings, such as ads or recommendations.
- Never include personal phone numbers or private contact details.
- Keep fixtures small enough for Git.

## First Target

Start with 5 to 10 listing-card examples each for:

1. Spinny.
2. Mahindra First Choice.
3. True Value.
4. CarDekho.
5. OLX.

These give a useful mix of clean platform inventory, certified dealer inventory, rich marketplace text, and noisy classified listings.

## Current Fixture Files

```text
tests/fixtures/spinny/listing_cards_extracted.json
tests/fixtures/mahindra_first_choice/listing_cards_extracted.json
tests/fixtures/true_value/listing_cards_extracted.json
tests/fixtures/cardekho/listing_cards_extracted.json
tests/fixtures/olx/listing_cards_extracted.json
```

These are small extracted source fixtures based on publicly visible page text or structured public inventory payloads from source reconnaissance passes.
