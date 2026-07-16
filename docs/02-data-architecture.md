# Data Architecture

## Architecture Shape

The first architecture is a small lakehouse-style pipeline:

```text
source
  -> raw capture
  -> bronze source-normalized records
  -> silver validated canonical listings
  -> gold aggregates, features, and model datasets
```

This keeps the system simple now while leaving room for cloud storage, orchestration, and model serving later.

## Layers

### Raw

Purpose: preserve exactly what was collected.

Examples:

- Raw JSON responses.
- Raw HTML snapshots.
- Raw browser-extracted payloads.
- Run metadata.

Rules:

- Immutable.
- Partition by source and capture date.
- Never manually edit.
- Keep enough metadata to replay parsing.

### Bronze

Purpose: convert raw source captures into source-specific structured records.

Rules:

- Preserve source field names where useful.
- Add `source`, `captured_at`, `ingestion_run_id`, and `raw_record_hash`.
- Allow source-specific quirks.
- Do not pretend records are canonical yet.

### Silver

Purpose: validated canonical listing table.

Rules:

- Use a project-wide schema.
- Standardize units and categories.
- Reject or quarantine invalid records.
- Deduplicate listings.
- Track schema version.

### Gold

Purpose: product-ready market intelligence.

Examples:

- Price distribution by city, brand, model, year.
- Comparable listing tables.
- Depreciation curves.
- Model training datasets.
- Deal score feature tables.

## Storage Plan

### Local Development

Use Parquet files plus DuckDB for querying.

Why:

- Parquet is columnar and efficient for analytics.
- DuckDB can query Parquet directly.
- This avoids standing up infrastructure too early.

### Production Direction

Use object storage for raw and processed data.

Options:

- S3-compatible object storage for raw, bronze, silver, and gold files.
- Delta Lake or Apache Iceberg when we need ACID table operations, time travel, and concurrent writes.
- PostgreSQL for application metadata, users, saved valuations, and operational state.

Do not start with Spark unless data volume forces it. A single-machine Polars plus DuckDB setup is enough for the first serious version.

## Partitioning

Recommended path layout:

```text
data/raw/source=cars24/capture_date=2026-06-24/run_id=.../
data/bronze/source=cars24/capture_date=2026-06-24/
data/silver/listings/capture_date=2026-06-24/
data/gold/market_summary/as_of_date=2026-06-24/
```

## Data Quality Gates

Every silver listing must pass:

- `listed_price_inr` is positive and realistic.
- `model_year` is realistic.
- `km_driven` is non-negative and realistic.
- `brand` and `model` are non-empty.
- `fuel_type` is from an accepted vocabulary.
- `transmission` is from an accepted vocabulary.
- `captured_at` is present.
- `source` is present.
- `raw_record_hash` is present.

Records that fail should go to quarantine with failure reasons.

## Observability

Each ingestion run must report:

- Source.
- Start and end time.
- Requested pages.
- Successful pages.
- Failed pages.
- Raw records captured.
- Records parsed.
- Records validated.
- Records quarantined.
- Duplicate count.
- Runtime.
- Error summary.

## Lineage

Every product-facing metric must trace back to:

- Source.
- Capture date.
- Run ID.
- Raw record hash.
- Parser version.
- Schema version.
