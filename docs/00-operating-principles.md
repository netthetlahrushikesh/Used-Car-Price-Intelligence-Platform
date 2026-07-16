# Operating Principles

## Positioning

This project is not a notebook cleanup. It is a new product-quality data platform.

The old notebook is useful only as historical context:

- It showed that used-car listing pages can be collected.
- It identified early fields: title, price, kilometers, fuel, owner count, registration, year, brand, and transmission.
- It also showed what must be fixed: brittle selectors, local paths, inconsistent row counts, weak parsing, no tests, and no data lineage.

## Startup-Grade Standard

Production-level does not mean building everything at once. It means every step is designed so it can survive growth.

For this project, that means:

- Clear source ownership and legal boundaries.
- Immutable raw data.
- Versioned schemas.
- Typed parsing.
- Validation before storage.
- Repeatable runs.
- Logs, metrics, and failure reports.
- Tests for parsers and transformations.
- No hidden notebook state.
- No training models on undocumented data.

## Data Product Mindset

The core asset is not the scraper. The core asset is a trusted vehicle-listing dataset with history.

A single high-quality dataset is worth more than many fragile scrapers. Every source must be judged by:

- Legality and terms.
- Coverage.
- Freshness.
- Field completeness.
- Stability.
- Duplicate risk.
- Cost to maintain.
- Ability to preserve source metadata.

## Definition Of Done For A Data Pipeline

A pipeline is not done when it prints rows. It is done when:

- The run has a unique `run_id`.
- Every record has source metadata.
- Raw captures are stored before parsing.
- Parsed rows conform to the canonical schema.
- Validation failures are visible and explainable.
- Duplicates are detected.
- Output is partitioned and queryable.
- The run can be repeated by another developer.
- A test suite covers the critical parsers.

## Build Order

1. Data policy.
2. Data schema.
3. One reliable acquisition path.
4. Raw storage.
5. Parser and validation.
6. Queryable processed data.
7. Basic analysis.
8. Multi-source expansion.
9. Modeling.
10. Product UI.
