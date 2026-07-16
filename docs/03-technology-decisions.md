# Technology Decisions

These decisions are intentionally conservative. The goal is production quality without unnecessary infrastructure.

## Decision 1: Python First

Use Python for data acquisition, parsing, validation, analytics, and early modeling.

Why:

- Strong scraping, data, and ML ecosystem.
- Easy transition from notebook work to production modules.
- Fits Polars, DuckDB, Pydantic, Pandera, scikit-learn, and FastAPI.

Initial target: Python 3.12 for broad library stability. Revisit Python 3.13 after dependencies are confirmed.

## Decision 2: Playwright For Dynamic Pages

Use Playwright for JavaScript-heavy sites and browser-based extraction.

Why:

- Browser contexts provide isolated sessions.
- Locators have auto-waiting and retry behavior.
- Failure artifacts like screenshots and traces can be attached to runs.

Use it carefully: browser automation is slower and more expensive than direct HTTP extraction.

Implementation note: Playwright is kept in the optional `acquisition` dependency group so parser, schema,
quality, and reporting tests do not require browser binaries.

## Decision 3: Scrapy For Broad Crawling

Use Scrapy when the source can be crawled through stable HTTP pages.

Why:

- Built-in item pipelines.
- Feed exports.
- AutoThrottle for polite crawling.
- Better fit for broad crawling than hand-written loops.

## Decision 4: Pydantic For Raw Record Contracts

Use Pydantic models for individual listing records and source metadata.

Why:

- Typed Python models.
- JSON schema generation.
- Good fit for API boundaries and parser outputs.

## Decision 5: Pandera For DataFrame Validation

Use Pandera for batch-level validation over tabular datasets.

Why:

- DataFrame schema checks.
- Column constraints.
- Good fit for validating silver and gold tables.

## Decision 6: Polars And DuckDB For Analytics

Use Polars for transformation pipelines and DuckDB for SQL exploration over Parquet.

Why:

- Polars can lazily scan Parquet and push work down.
- DuckDB can query Parquet directly and is excellent for local analytical workflows.
- Both avoid heavyweight infrastructure at the start.

## Decision 7: Parquet First, Delta Later

Use Parquet for early raw, bronze, silver, and gold datasets.

Move to Delta Lake or Apache Iceberg when we need:

- Time travel.
- Transactional table updates.
- Concurrent writes.
- Schema evolution at larger scale.
- Cloud lakehouse interoperability.

## Decision 8: Dagster When Orchestration Becomes Real

Start with CLI commands for the first pipeline. Move to Dagster when we have multiple assets, schedules, freshness checks, and dependencies.

Why:

- Dagster models data assets directly.
- It gives lineage and observability without treating data as anonymous tasks.

## Decision 9: No Kafka, Spark, Or Kubernetes At The Start

These are not rejected forever. They are rejected for the first milestone.

Use them only when a real bottleneck appears:

- Kafka: event streaming or high-volume ingestion.
- Spark: distributed processing beyond single-machine limits.
- Kubernetes: multi-service deployment and scaling needs.

## References Checked

- Playwright locators and browser contexts: https://playwright.dev/python/docs/api/class-locator and https://playwright.dev/python/docs/api/class-browsercontext
- Scrapy item pipelines, feed exports, and AutoThrottle: https://docs.scrapy.org/en/latest/topics/item-pipeline.html, https://docs.scrapy.org/en/latest/topics/feed-exports.html, and https://docs.scrapy.org/en/latest/topics/autothrottle.html
- DuckDB Parquet support: https://duckdb.org/docs/current/data/parquet/overview
- Polars Parquet read/write/scan: https://docs.pola.rs/user-guide/io/parquet/
- Delta Lake Python ecosystem: https://delta-io.github.io/delta-rs/
- Dagster assets: https://docs.dagster.io/guides/build/assets
- Pandera DataFrame schemas: https://pandera.readthedocs.io/en/stable/dataframe_schemas.html
- Pydantic validation: https://pydantic.dev/docs/validation/latest/get-started/
