# Project Notebook

Project: Used Car Price Intelligence Platform

Purpose: preserve the full thinking, planning, execution, decisions, changes, and learning journey from start to finish.

This file is the human-readable project journal. It should be updated whenever the project direction changes, a major file is created, a technical decision is made, or a result teaches us something important.

## How To Use This Notebook

Every meaningful work session should add:

- Date.
- Goal.
- What we discussed.
- Decisions made.
- Files changed.
- Why the plan changed, if it changed.
- Verification performed.
- Next step.
- Content notes for future Medium, LinkedIn, or YouTube storytelling.

Small typo fixes do not need a long note. Anything that affects architecture, data strategy, schema, scraping approach, validation, modeling, API, UI, or deployment should be recorded.

## Project Storyline

The old project was a notebook-based Cars24 scraping and EDA project. It proved the basic idea but had the common early-project problems:

- Single source.
- Brittle scraper logic.
- Notebook state inconsistency.
- Hardcoded local paths.
- Weak reproducibility.
- No source registry.
- No schema contract.
- No validation or quarantine layer.
- No production-style data pipeline.

The new project is being built as a separate, production-grade portfolio project focused on data quality first.

The core thesis:

> Used-car price intelligence is only as good as the data foundation. Scraping is not the product. Trusted, validated, comparable market data is the product.

## Current Operating Principles

- Build a new standalone project, separate from the old notebook repo.
- Treat data as the key asset.
- Do not rush into scraping before defining the data contract.
- Keep raw data separate from cleaned data.
- Use source adapters instead of one-off scraper scripts.
- Measure field completeness and parser success.
- Quarantine bad records instead of silently dropping them.
- Use gold pricing-ready rows only when pricing-critical fields are complete.
- Keep the project understandable enough to turn into a written article and video walkthrough.

## Decision Log

### D-001: Start A New Repository

Date: 2026-06-24

Decision: create a new standalone repository for the Used Car Price Intelligence Platform instead of modifying the old web scraping and EDA notebook project.

Reason:

- The old repo is useful history, but the new project needs a cleaner architecture.
- A new repo makes the story stronger: basic notebook project to production-style data platform.

Impact:

- Initialized this workspace as its own Git repository.
- Created a clean README, docs, data folders, and planning files.

### D-002: Data-First Before Scraper-First

Date: 2026-06-24

Decision: define the data model, storage layers, source strategy, and quality gates before writing scrapers.

Reason:

- The user's earlier pain came from inconsistent, null-heavy, messy scraped data.
- Multi-site scraping will multiply that problem unless the data foundation exists first.

Impact:

- Created data strategy, architecture, and quality planning docs.
- Defined raw, bronze, silver, and gold layers.

### D-003: Column-First Source Review

Date: 2026-06-24

Decision: inspect used-car sites by visible columns/features first, then design the canonical schema.

Reason:

- Different sites expose different fields.
- We need to know common fields before choosing required columns.
- This avoids each scraper producing its own dataframe shape.

Impact:

- Created source feature matrix.
- Identified likely first fixture sources: Spinny, CarDekho, OLX.

### D-004: Pricing-Ready Rows Need Strict Completeness

Date: 2026-06-24

Decision: enforce 100% completeness for pricing-critical fields in the gold pricing-ready table, while measuring but not blocking optional fields.

Reason:

- Missing values in pricing-critical columns will damage price intelligence.
- Forcing 100% completeness on every optional column would delete useful data and bias the dataset.

Impact:

- Added completeness targets and row completeness scoring to the data quality plan.

### D-005: Keep A Project Notebook

Date: 2026-06-24

Decision: maintain this notebook as the running project narrative.

Reason:

- The project will take days.
- The user wants to turn the process into documentation, a Medium article, a LinkedIn post, and a YouTube showcase.
- Important reasoning should not be lost in chat history.

Impact:

- Created `PROJECT_NOTEBOOK.md`.
- Future major steps should update this file.

### D-006: Specify Parsers Before Coding Scrapers

Date: 2026-06-24

Decision: define shared parser behavior and machine-readable parser rules before implementing source adapters.

Reason:

- The project's main risk is inconsistent multi-site data.
- Shared parsers prevent every scraper from inventing its own cleanup logic.
- Parser tests can run offline with fixtures, which makes the pipeline more reliable before live acquisition.

Impact:

- Created `docs/10-parser-specifications.md`.
- Created `config/parser_rules.yml`.
- Created first fixture directories under `tests/fixtures/`.

### D-007: Canonical Model Means Model Family

Date: 2026-06-24

Decision: canonical `model` should represent the comparable model family, not engine size, displacement, gearbox, or trim.

Reason:

- Source titles often mix model, engine, trim, and gearbox into one string.
- If values like `1.0`, `1.2`, `2.0`, `Turbo`, `CVT`, or `DCT` enter the `model` column, grouping and comparison become noisy.
- These details still matter, but they belong in `variant` or later structured fields such as `engine_cc`.

Example:

- `Wagon-R-1-0` should parse as model `Wagon R`, variant `1.0`.
- It should not parse as model `Wagon R 1.0`.

Impact:

- Updated parser model dictionary and variant normalization.
- Updated canonical schema and parser docs.
- Added more OLX fixture cases and tests.

### D-008: Add A Blind-Spot Review Before Scaling Scraping

Date: 2026-06-24

Decision: pause before source adapters and run a structured blind-spot review.

Reason:

- The `Wagon-R-1-0` issue showed that valid-looking parsed data can still be semantically wrong.
- More fixtures and live scraping will create bigger downstream problems if schema and quarantine logic do not catch these issues.

Impact:

- Created `docs/12-blind-spots-and-risk-review.md`.
- Added BH/Bharat registration parsing.
- Added schema fields for registration type/year and separate manufacture/registration years.
- Confirmed the next implementation should be schema validation and quarantine logic.

### D-009: Avoid OLX As MVP Acquisition Source

Date: 2026-06-24

Decision: do not use OLX as a core MVP acquisition source.

Reason:

- OLX is a classified/self-listed marketplace with mixed direct-owner and dealer inventory.
- Self-listed records can be incomplete, inconsistent, misleading, or poorly formatted.
- OLX is valuable for testing noisy records, but weak for building a trusted first price-intelligence dataset.

Impact:

- OLX remains in fixtures as a noisy/quarantine stress-test source.
- First live source priority changes to trusted/certified sources: Spinny, Mahindra First Choice, Cars24, then OEM certified sources.
- Created `docs/13-source-trust-and-priority-review.md`.
- Updated `config/source_registry.yml` priorities.

## Execution Log

### E-001: Workspace Foundation

Date: 2026-06-24

Goal: create the initial project foundation.

Actions:

- Initialized the workspace as a standalone Git repository.
- Added `.gitignore`.
- Created `README.md`.
- Created `data/raw`, `data/bronze`, `data/silver`, `data/gold`, and `data/tmp`.
- Added `data/README.md`.

Result:

- The project now has a clean starting structure.

Verification:

- `git diff --check` passed.
- Non-ASCII scan passed.

### E-002: Planning Documents

Date: 2026-06-24

Goal: define the initial operating model and data-first plan.

Actions:

- Created `docs/00-operating-principles.md`.
- Created `docs/01-data-strategy.md`.
- Created `docs/02-data-architecture.md`.
- Created `docs/03-technology-decisions.md`.
- Created `docs/04-first-90-days-roadmap.md`.
- Created `docs/05-github-repo-plan.md`.
- Created source evaluation docs.

Result:

- The project has an initial architecture and roadmap.

### E-003: Data Acquisition Research

Date: 2026-06-24

Goal: understand how used-car data appears on company pages and what issues to expect.

Actions:

- Reviewed major Indian used-car sources.
- Documented where fields appear: listing cards, detail pages, HTML, rendered DOM, embedded state, and frontend responses.
- Created `docs/06-data-acquisition-research-and-plan.md`.

Result:

- The project has a source acquisition strategy and risk model.

### E-004: Data Quality Plan

Date: 2026-06-24

Goal: address multi-site inconsistency, nulls, empty values, and messy source formats.

Actions:

- Created `docs/07-data-quality-and-source-normalization-plan.md`.
- Added null policy, completeness targets, quarantine strategy, source quality metrics, and testing strategy.

Result:

- The project now treats data quality as a core system, not cleanup after scraping.

### E-005: Source Feature Matrix

Date: 2026-06-24

Goal: compare visible fields across used-car sites.

Actions:

- Created `docs/08-source-feature-matrix.md`.
- Compared fields across Cars24, Spinny, CarDekho, CarWale, OLX, Droom, CarTrade, Mahindra First Choice, True Value, Hyundai Promise, Honda Auto Terrace, and Toyota U Trust.

Result:

- Identified core fields and first candidate sources.

### E-006: Source Registry And Canonical Schema

Date: 2026-06-24

Goal: convert planning into the first data contract artifacts.

Actions:

- Created `PROJECT_NOTEBOOK.md`.
- Created `config/source_registry.yml`.
- Created `docs/09-canonical-listing-schema.md`.

Result:

- The project now has a living notebook, source registry, and first canonical schema specification.

### E-007: Parser Specifications And Fixture Structure

Date: 2026-06-24

Goal: define source-independent parser contracts before scraper implementation.

Actions:

- Created `docs/10-parser-specifications.md`.
- Created `config/parser_rules.yml`.
- Created fixture folders for Spinny, CarDekho, and OLX.
- Linked parser specs, parser rules, and fixtures from `README.md`.

Result:

- The project now has explicit parsing rules for price, kilometers, ownership, fuel type, transmission, registration, title parsing, seller type, availability, completeness scoring, and quarantine triggers.
- The next code step can be test-driven parser implementation instead of live scraping.

### E-008: First Parser Implementation

Date: 2026-06-24

Goal: turn parser specifications into executable, tested parser functions.

Actions:

- Created `pyproject.toml`.
- Created `src/used_car_price_intelligence/`.
- Implemented shared parser functions in `src/used_car_price_intelligence/parsers/core.py`.
- Added unit tests in `tests/unit/test_parsers.py`.

Result:

- The project now has executable parser logic for null normalization, price, kilometers, ownership, fuel type, transmission, registration, and title parsing.
- The implementation is intentionally source-independent; source adapters will call these shared parsers.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 20 tests.
- `git diff --check` passed.
- YAML parse checks passed for `config/source_registry.yml` and `config/parser_rules.yml`.

### E-009: First Source Fixture Capture

Date: 2026-06-24

Goal: create small source-like parser fixtures from the first three target sources.

Actions:

- Inspected public listing-page text from Spinny, CarDekho, and OLX Hyderabad pages.
- Created 5 listing-card examples each for Spinny, CarDekho, and OLX.
- Added fixture-based parser tests in `tests/unit/test_source_fixtures.py`.
- Improved title parsing with brand aliases and starter known model dictionaries.
- Created `docs/11-source-fixture-capture-notes.md`.

Result:

- The parser layer is now tested against 15 source-like listing-card records.
- The fixture pass confirmed that Spinny is clean, CarDekho is rich but narrative-heavy, and OLX is useful but incomplete at listing-card level.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 23 tests.
- `git diff --check` passed.
- Fixture JSON parse checks passed.
- ASCII scan passed.

### E-010: Model Family Normalization Refinement

Date: 2026-06-24

Goal: refine title parsing after reviewing fixture behavior.

Problem:

- `Wagon-R-1-0` was previously normalized as model `Wagon R 1.0`.
- This is too granular for the canonical `model` column.

Actions:

- Changed `Wagon-R-1-0` handling to model `Wagon R`, variant `1.0`.
- Added more OLX fixture records for `S-Cross`, `Vitara-Brezza`, `Micra Active`, and `Renault Kiger`.
- Added tests for engine suffixes, hyphenated family models, and multi-word models.
- Updated schema and parser documentation to state that model means model family.

Result:

- The title parser now keeps model-family grouping cleaner while preserving details in `variant`.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 26 tests.
- Fixture counts: Spinny 5, CarDekho 5, OLX 9.
- `git diff --check` passed.

### E-011: Blind-Spot Risk Review

Date: 2026-06-24

Goal: identify blind spots that could create future data-quality or modeling problems.

Actions:

- Reviewed current schema, parser docs, parser code, tests, and fixtures.
- Performed a short external knowledge check on valuation factors, VIN-style vehicle identity, and BH registration.
- Created `docs/12-blind-spots-and-risk-review.md`.
- Added BH/Bharat registration parsing and test coverage.
- Updated schema docs for `registration_type`, `registration_year`, `manufacture_year`, and registration-year separation.

Result:

- Key risks are now explicit: model-family normalization, price ambiguity, full-card parser contamination, fuel/transmission missingness, model/manufacture/registration-year confusion, registration special cases, source bias, duplicates, sold listings, and condition/history gaps.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 27 tests.
- `git diff --check` passed.
- YAML and fixture JSON parse checks passed.
- ASCII scan passed.

### E-012: Source Trust Priority Review

Date: 2026-06-24

Goal: decide whether OLX should be avoided because of self-listing and misinformation risk.

Actions:

- Checked current source positioning for Spinny, Cars24, Mahindra First Choice, Honda Auto Terrace, Toyota U Trust, Hyundai Promise, Volkswagen Certified Pre-Owned, and OLX.
- Created `docs/13-source-trust-and-priority-review.md`.
- Updated `config/source_registry.yml` to move OLX to research-only priority and add Hyundai Promise and Toyota U Trust.
- Updated `docs/08-source-feature-matrix.md` to reflect the new trusted-source MVP order.

Result:

- New MVP source order is Spinny first, then Mahindra First Choice or Cars24, then one OEM certified source.
- OLX is retained only for noisy fixtures and quarantine testing.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 27 tests.
- `git diff --check` passed.
- YAML and fixture JSON parse checks passed.
- ASCII scan passed.

### E-013: Schema And Quality Gate Implementation

Date: 2026-06-24

Goal: make the OLX/source-trust and completeness decisions enforceable in code.

Actions:

- Created `src/used_car_price_intelligence/schema/`.
- Created `src/used_car_price_intelligence/quality/`.
- Added `CanonicalListing` dataclass.
- Added registry-aware `evaluate_listing()` quality gate.
- Added tests for trusted records, OLX/research-only records, missing fuel/transmission, unknown fuel, unavailable listings, non-listing records, model pollution, low parser confidence, and invalid price.

Result:

- The project can now classify a canonical record as silver-valid, gold pricing-ready, or rejected with quarantine reasons.
- OLX-type records can remain in fixtures but are blocked from the MVP pricing-ready dataset by source policy.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 36 tests.
- `git diff --check` passed.
- YAML and fixture JSON parse checks passed.
- ASCII scan passed.

### E-014: First Trusted Source Adapter In Fixture Mode

Date: 2026-06-24

Goal: create the first end-to-end source adapter path without live scraping.

Actions:

- Created `src/used_car_price_intelligence/adapters/`.
- Added `SpinnyFixtureAdapter`.
- Added deterministic source listing IDs and raw record hashes.
- Converted Spinny fixture records into `CanonicalListing` records.
- Added adapter tests that pass converted records through `evaluate_listing()`.

Result:

- The first trusted source now has an end-to-end fixture-mode path:
  extracted fixture -> parsers -> canonical listing -> quality gate -> pricing-ready record.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 38 tests.
- `git diff --check` passed.
- YAML and fixture JSON parse checks passed.
- ASCII scan passed.

### E-015: Fixture Pipeline CLI Runner

Date: 2026-06-24

Goal: make the Spinny fixture pipeline runnable from the terminal with quality metrics.

Actions:

- Created `src/used_car_price_intelligence/pipeline/`.
- Added `run_fixture_pipeline()`.
- Added `FixtureRunSummary`.
- Created `src/used_car_price_intelligence/cli.py`.
- Added CLI tests and fixture-runner tests.
- Updated `README.md` with fixture runner commands.

Result:

- The project can now run the trusted Spinny fixture path from the terminal and print quality metrics.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 41 tests.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source spinny` returned 5 total records, 5 silver-valid records, 5 pricing-ready records, and 0 quarantined records.
- `git diff --check` passed.
- YAML and fixture JSON parse checks passed.
- ASCII scan passed.

### E-016: Fixture Output Persistence

Date: 2026-06-24

Goal: write reproducible fixture-run outputs into local data layers.

Actions:

- Added `write_fixture_outputs()`.
- Added `FixtureOutputPaths`.
- Added `--write`, `--output-root`, and `--capture-date` CLI options.
- Updated `data/README.md` and `README.md`.
- Added tests for output persistence and CLI write mode.

Result:

- Fixture runs can now write raw source fixture payload, silver records, quarantine records, and gold quality summary files under `data/`.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 43 tests.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source spinny --write --json` wrote raw, silver, quarantine, and quality-summary outputs under `data/`.
- Generated data-layer outputs are ignored by Git as intended.
- `git diff --check` passed.
- YAML and fixture JSON parse checks passed.
- ASCII scan passed.

### E-017: Local Quality Report Reader

Date: 2026-06-24

Goal: make generated quality summary JSON easy to inspect and explain.

Decision:

- Add a small reporting layer instead of mixing report formatting into parsers, adapters, or quality gates.
- Treat the report as an operator checkpoint before moving from offline fixtures to live source capture.

Actions:

- Added `used_car_price_intelligence.reporting`.
- Added `quality-report --summary ...` CLI command.
- Added status classification:
  - `PASS` when records exist, all records are pricing-ready, no rows are quarantined, and required completeness is 100%.
  - `WARN` when some records are pricing-ready but the run still has quality issues.
  - `FAIL` when no records exist or no records are pricing-ready.
- Added unit tests for report rendering, invalid summary validation, and CLI report output.
- Added `docs/14-local-quality-reporting.md`.

Result:

- The saved Spinny fixture quality summary can now be rendered as a Markdown report.
- Current report status is `PASS`: 5 total records, 5 silver-valid, 5 pricing-ready, 0 quarantined.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 47 tests.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli quality-report --summary data/gold/quality_summary/capture_date=2026-06-24/spinny_run_20260624_spinny_fixture_cli_quality_summary.json` rendered the expected report.

### E-018: Live Spinny Hyderabad Hub Fixture

Date: 2026-06-24

Goal: capture a larger public Spinny Hyderabad fixture before building any live adapter.

Actions:

- Reviewed a public Spinny Hyderabad hub search result.
- Added `tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json` with 20 listing-card records.
- Added parser model-family coverage for live records:
  - `Brezza`
  - `XUV700`
  - `Nexon`
  - `Taigun`
  - `Slavia`
  - `Sonet`
  - `Innova Hycross`
  - `A4`
  - `Tiago EV`
  - `GLA`
- Found and fixed a price blind spot: discounted cards can show both current and old prices. The parser now keeps the first price candidate and emits `multiple_price_candidates`.
- Kept the original 5-card Spinny fixture unchanged so earlier baseline output remains stable.

Result:

- Live fixture pipeline result:
  - records total: 20
  - silver-valid: 20
  - pricing-ready: 20
  - quarantined: 0
  - required completeness: 100%
  - warnings: `multiple_price_candidates: 2`

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 50 tests.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source spinny --fixture tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json --captured-at 2026-06-24T04:00:00Z --run-id run_20260624_spinny_live_fixture --json` returned 20 pricing-ready records and 0 quarantined records.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source spinny --fixture tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json --captured-at 2026-06-24T04:00:00Z --run-id run_20260624_spinny_live_fixture --capture-date 2026-06-24 --write --json` wrote ignored data-layer outputs.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli quality-report --summary data/gold/quality_summary/capture_date=2026-06-24/spinny_run_20260624_spinny_live_fixture_quality_summary.json` rendered a `PASS` report.

### E-019: Field-Level Completeness Profiler

Date: 2026-06-24

Goal: move from average quality scores to exact column-level completeness.

Actions:

- Added `used_car_price_intelligence.reporting.field_profile`.
- Added `field-profile` CLI command.
- Added tests for profiler output and CLI behavior.
- Added `docs/15-live-source-field-gap-review.md`.

Result:

- The live Spinny fixture has 100% completeness for all required pricing-ready fields.
- High-value fields are mostly complete, but `ownership` is 0/20.
- Optional valuation/explainability fields are mostly missing from listing-card fixture data:
  - manufacture year
  - body type
  - color
  - original price
  - discount amount
  - inspection status
  - accident history
  - service history
  - warranty
  - listing lifecycle timestamps

Decision:

- Do not make these missing fields required yet.
- Treat them as enrichment targets for detail pages or future sources.
- Build the first live adapter around listing-card capture first, with explicit quality reporting.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 53 tests.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli field-profile --source spinny --fixture tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json --captured-at 2026-06-24T04:00:00Z --run-id run_20260624_spinny_live_fixture` showed required fields at 20/20 and ownership at 0/20.

### E-020: First Live Adapter Contract

Date: 2026-06-24

Goal: define and enforce the payload contract before building browser/network acquisition.

Decision:

- Separate live extraction from canonical normalization.
- Require live extraction to produce isolated raw listing-card fields first.
- Fail closed when the extracted payload is malformed or missing required raw fields.
- Reuse the same adapter path for fixtures and future live capture payloads.

Actions:

- Added `docs/16-first-live-adapter-contract-and-failure-modes.md`.
- Added `SpinnyExtractedPayloadAdapter`.
- Kept `SpinnyFixtureAdapter` as a file-loader wrapper on top of the extracted-payload adapter.
- Added `validate_spinny_extracted_payload()`.
- Added `PayloadContractFailure` and `PayloadContractResult`.
- Added `validate-payload` CLI command.
- Added tests for:
  - valid live fixture payload contract,
  - missing required raw field,
  - adapter fail-closed behavior,
  - CLI success result,
  - CLI nonzero result on contract failure.

Contract:

- Payload-level required fields:
  - `source`
  - `source_url`
  - `records`
- Raw listing-card required fields:
  - `title`
  - `price`
  - `variant`
  - `km`
  - `fuel`
  - `transmission`
  - `registration`
  - `locality`

Result:

- The current 20-record Spinny live fixture passes extracted payload validation.
- The adapter now prevents selector failures from silently becoming null-heavy canonical records.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 58 tests.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli validate-payload --source spinny --payload tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json --json` returned `ok: true`, `records_total: 20`, and no failures.

### E-021: Bounded Live Capture Command

Date: 2026-06-24

Goal: add a first local command that can capture one public Spinny listing page into the extracted payload contract.

Decision:

- Keep live browser capture optional so base parser/schema/quality tests remain lightweight.
- Use Playwright for browser-style extraction when the optional acquisition dependency is installed.
- The capture command should write only an extracted payload and validate it. It should not yet write canonical data.

Actions:

- Added optional `acquisition` dependency group with `playwright`.
- Added `used_car_price_intelligence.acquisition.spinny_live`.
- Added `capture-spinny-live` CLI command.
- Added offline tests for:
  - parsing Spinny listing-card DOM text,
  - building extracted payloads from card text,
  - preserving missing variant as a contract failure.
- Added `docs/17-bounded-live-capture-command.md`.

Observed live DOM pattern:

```text
2025 Mahindra XUV700
20.44 Lakh
AX 7 Luxury Pack Petrol AT 7 STR
EMI Rs 35,385/m*
26.5K km
Petrol
Automatic
TG07
```

Result:

- The command is available as:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli capture-spinny-live --output data/tmp/spinny_live_payload.json --json
```

- In the current base environment, Python Playwright is not installed. The command returns setup guidance and writes no payload.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 61 tests.
- `$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli capture-spinny-live --output data/tmp/spinny_live_payload_test.json --json` returned the Playwright setup message and did not create `data/tmp/spinny_live_payload_test.json`.

### E-022: First Successful Live Smoke Workflow

Date: 2026-06-24

Goal: turn live capture, payload validation, canonical conversion, quality reporting, and field profiling into one repeatable command.

Actions:

- Created a local `.venv`.
- Installed the optional acquisition dependency:
  - `.venv\Scripts\python -m pip install -e ".[acquisition]"`
  - `.venv\Scripts\python -m playwright install chromium`
- Ran the first live capture.
- Contract validation caught a real extractor issue:
  - `Style 1.0L TSI AT` was initially mistaken for a price-like line.
  - The extractor skipped the variant.
  - Payload validation failed before canonical conversion.
- Fixed the price-line detector so bare engine-size `L` is not treated as a price unit.
- Added regression coverage for `Style 1.0L TSI AT`.
- Added explicit live-observed model aliases:
  - `BYD Seal`
  - `Mahindra Scorpio N`
  - `Jeep Compass`
  - `Tata Harrier`
  - `Skoda Octavia`
  - `BMW X1`
  - `Mercedes-Benz GLC`
  - `Audi Q3`
- Added `spinny-live-smoke` CLI command.
- Added `docs/18-first-live-capture-run.md`.
- Added `docs/19-spinny-live-smoke-workflow.md`.

Result:

- The one-command live smoke workflow passed.
- Payload validation: pass.
- Extracted records: 20.
- Silver-valid records: 20.
- Pricing-ready records: 20.
- Quarantined records: 0.
- Required completeness: 100%.
- Warnings: none.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24.json --captured-at 2026-06-24T05:45:00Z --run-id run_20260624_spinny_live_smoke --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --json
```

Output paths:

```text
data/tmp/spinny_live_smoke_payload_2026-06-24.json
data/raw/source=spinny/capture_date=2026-06-24/run_id=run_20260624_spinny_live_smoke/fixture_source_payload.json
data/silver/listings/capture_date=2026-06-24/spinny_run_20260624_spinny_live_smoke_silver.json
data/silver/quarantine/source=spinny/capture_date=2026-06-24/run_20260624_spinny_live_smoke_quarantine.json
data/gold/quality_summary/capture_date=2026-06-24/spinny_run_20260624_spinny_live_smoke_quality_summary.json
```

Decision:

- The live listing-card acquisition path is proven for one page.
- Do not move to ML/dashboard yet.
- Next production step is to persist compact Markdown smoke reports and then choose between pagination, detail-page enrichment, or adding a second trusted source.

Verification:

- `$env:PYTHONPATH='src'; python -m unittest discover -s tests` passed with 64 tests.
- `.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24.json --captured-at 2026-06-24T05:45:00Z --run-id run_20260624_spinny_live_smoke --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --json` exited 0 with `ok: true`.

### E-023: Persisted Live Smoke Markdown Reports

Goal: make each live acquisition smoke run readable without opening large JSON files.

Reasoning:

- JSON outputs are necessary for pipeline reproducibility, but not enough for human review.
- A production-style data pipeline needs operator artifacts that quickly answer whether the run passed, why it failed, and which fields are still weak.
- Payload contract failures are especially important to document because the pipeline intentionally stops before canonical conversion.

Implementation:

- Added `used_car_price_intelligence.reporting.smoke_report`.
- Added a default report path:
  `data/gold/smoke_reports/capture_date=<date>/<source>_<run_id>_smoke_report.md`.
- Added `--report-output` to `spinny-live-smoke` for explicit report locations.
- Updated `spinny-live-smoke` so successful runs write:
  - extracted payload,
  - raw payload copy,
  - silver records,
  - quarantine records,
  - quality summary,
  - Markdown smoke report.
- Updated `spinny-live-smoke` so payload contract failures still write a Markdown failure report but do not write canonical raw/silver/gold listing outputs.

Report contents:

- pass/fail status,
- source URL,
- run ID,
- captured timestamp,
- payload contract result,
- payload failures if present,
- quality gate counts,
- completeness scores,
- quarantine reasons,
- warnings,
- required and high-value field gaps,
- output paths.

Decision:

- Treat smoke reports as operational artifacts, not source-controlled data.
- Keep them under ignored `data/gold/smoke_reports/` by default.
- Use explicit `--report-output` in tests and demos when a deterministic report path is useful.

Verification:

- Focused smoke/report CLI tests passed:
  `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_smoke_report tests.unit.test_cli`.
- Full test suite passed:
  `$env:PYTHONPATH='src'; python -m unittest discover -s tests` ran 67 tests.
- Live smoke verification passed:
  `.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24_reported.json --captured-at 2026-06-24T06:20:00Z --run-id run_20260624_spinny_live_smoke_reported --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --json` exited 0 with `ok: true`.
- Generated report path:
  `data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_20260624_spinny_live_smoke_reported_smoke_report.md`.

### E-024: Spinny Detail Page Enrichment

Goal: fill high-value fields that listing cards do not expose, starting with ownership.

Reasoning:

- Listing-card capture is already pricing-ready, but ownership stayed at 0/20.
- Owner count materially affects used-car pricing.
- Detail pages expose `No. of Owner`, `Make Year`, `Registration Year`, `RTO`, inspection signals, warranty, return policy, and service due text.
- These fields should be captured as enrichment, not forced into the card parser.

Implementation:

- Changed live card capture to preserve the first detail-page anchor as `raw.listing_url`.
- Added `build_spinny_payload_from_card_snapshots`.
- Added `parse_spinny_detail_text`.
- Added `capture_spinny_detail_payload`.
- Added `merge_spinny_detail_payload_into_listing_payload`.
- Updated `SpinnyExtractedPayloadAdapter` to map detail fields:
  - ownership,
  - manufacture year,
  - registration year,
  - RTO/registration code,
  - inspection status,
  - warranty label,
  - return policy label.
- Preserved source-specific insurance, quality-score, inspection-summary, and service-due fields under `extra_fields.spinny_detail`.
- Extended `spinny-live-smoke` with bounded detail options:
  - `--detail-pages`,
  - `--detail-output`,
  - `--merged-output`,
  - `--detail-delay-ms`.
- Updated smoke reports to show detail enrichment counts.

Important debugging note:

- First bounded detail smoke run captured 3 detail URLs but produced empty detail raw objects.
- Root cause: detail page text was read too early, before the `Car Overview` section hydrated.
- Fix: detail capture now waits until body text contains both `Car Overview` and `No. of Owner`.

Live result after fix:

- Command:
  `.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24_detail_retry.json --captured-at 2026-06-24T07:25:00Z --run-id run_20260624_spinny_detail_smoke_retry --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --timeout-ms 60000 --detail-pages 3 --detail-delay-ms 3000 --json`
- Listing-card records: 20.
- Detail pages requested: 3.
- Detail pages captured: 3.
- Payload validation: pass.
- Enriched payload validation: pass.
- Pricing-ready records: 20.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness improved from 85.71% to 87.85%.
- Optional completeness improved from 23.33% to 25.66%.
- Overall completeness improved from 89.48% to 90.14%.
- Ownership improved from 0/20 to 3/20.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_20260624_spinny_detail_smoke_retry_smoke_report.md
```

Decision:

- Detail-page enrichment is proven and should now be scaled carefully.
- Do not scrape all detail pages by default yet.
- Next production refinement should be a bounded enrichment policy with per-run caps, timeout metrics, and failure accounting.
- Do not treat Spinny component quality scores as universal `inspection_score` yet; keep them source-specific until we design a cross-source condition schema.

### E-025: Detail Enrichment Policy And Failure Accounting

Goal: make detail-page enrichment observable and fail-closed before scaling it beyond a small sample.

Problem:

- The first detail enrichment implementation could complete even when detail pages returned empty raw objects.
- That would make the run look successful while ownership stayed missing.
- In production data work, this is dangerous because silent enrichment failure creates false confidence.

Implementation:

- Added per-detail-page metadata:
  - `capture_status`,
  - `attempts`,
  - `failure_reason`,
  - `capture_error` when applicable.
- Added detail payload policy metadata:
  - requested URLs,
  - valid URLs,
  - max records,
  - attempted records,
  - invalid URL count,
  - over-cap count,
  - attempts per record,
  - timeout,
  - delay.
- Added `summarize_spinny_detail_payload`.
- Added `--detail-attempts` to `spinny-live-smoke`.
- Updated the smoke command so requested detail enrichment must pass before canonical raw/silver/gold outputs are written.
- Updated smoke reports with detail health metrics:
  - ok,
  - requested records,
  - attempted records,
  - successful records,
  - failed records,
  - ownership records,
  - retries used,
  - timeout count,
  - empty raw count.
- Fixed enriched smoke output persistence so raw output stores the merged payload actually used for canonical conversion.

Decision:

- If `--detail-pages` is greater than zero, detail enrichment is part of the smoke contract.
- Detail failures should stop canonical output writes, while still preserving detail payload, merged payload, and the smoke report for debugging.
- For now, a detail page is considered successful only when owner count is captured.

Verification so far:

- Focused tests passed:
  `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_spinny_live_acquisition tests.unit.test_cli tests.unit.test_smoke_report`.
- Full test suite passed:
  `$env:PYTHONPATH='src'; python -m unittest discover -s tests` ran 75 tests.
- Live policy smoke passed:
  `.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24_detail_policy.json --captured-at 2026-06-24T07:45:00Z --run-id run_20260624_spinny_detail_policy_smoke --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --timeout-ms 60000 --detail-pages 3 --detail-attempts 2 --detail-delay-ms 3000 --json`.
- Detail policy result:
  - attempted detail pages: 3,
  - successful detail pages: 3,
  - failed detail pages: 0,
  - ownership records: 3,
  - retries used: 0,
  - timeouts: 0.
- Quality result:
  - pricing-ready records: 20/20,
  - quarantined records: 0,
  - required completeness: 100.00%,
  - high-value completeness: 87.85%,
  - optional completeness: 25.66%,
  - overall completeness: 90.14%.
- Generated report:
  `data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_20260624_spinny_detail_policy_smoke_smoke_report.md`.

### E-026: Full First-Page Detail Enrichment

Goal: test whether the detail enrichment policy can handle every listing-card row on the current first page.

Reasoning:

- The 3-detail-page policy smoke proved the mechanics.
- The next question was whether owner count and detail fields stay stable across all 20 visible rows.
- This should be tested before pagination because pagination multiplies any failure mode.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-24_detail_all20.json --captured-at 2026-06-24T08:05:00Z --run-id run_20260624_spinny_detail_all20_smoke --capture-date 2026-06-24 --max-records 20 --capture-attempts 4 --retry-delay-ms 2000 --timeout-ms 60000 --detail-pages 20 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- Listing-card records: 20.
- Detail pages requested: 20.
- Detail pages attempted: 20.
- Detail pages successful: 20.
- Detail pages failed: 0.
- Ownership records: 20.
- Retries used: 0.
- Timeouts: 0.
- Invalid URLs: 0.
- Payload validation: pass.
- Enriched payload validation: pass.
- Pricing-ready records: 20.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 100.00%.
- Optional completeness: 39.67%.
- Overall completeness: 93.97%.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_20260624_spinny_detail_all20_smoke_smoke_report.md
```

Decision:

- Full detail enrichment is stable enough for the current first page.
- The first-page acquisition path now produces 20/20 pricing-ready records with 100% high-value completeness.
- Do not move to ML/dashboard yet.
- Next acquisition step should be pagination with strict page and detail caps.

### E-027: Spinny Two-Batch Pagination With Row Coverage Gate

Goal: scale Spinny live acquisition beyond the first visible listing batch without allowing silent row under-capture.

Reasoning:

- Spinny uses infinite scroll, not traditional next-page URLs.
- A capture can have 100% clean rows but still be wrong if only the first batch loaded.
- Therefore pagination needs a row-volume gate in addition to the field-quality gate.
- For `spinny-live-smoke`, `--min-records` now defaults to `--max-records`.

Implementation:

- Added `--max-pages` and `--page-scroll-delay-ms` to listing capture and smoke runs.
- Added `--min-records` and listing coverage checks.
- Made the scroll loader more persistent by scrolling the last card into view, scrolling to document bottom, and using mouse-wheel movement.
- Added pagination metadata to captured payloads.
- Added `listing_capture` and `listing_coverage` sections to smoke JSON and Markdown reports.
- Made under-capture fail closed before canonical raw/silver/gold outputs.

Failure found during live retry:

- First strict two-page run captured 40 rows but quarantined `2020 Lexus NX 300h Luxury`.
- Cause: `Lexus` and `NX` were missing from the controlled parser vocabulary.
- Fix: added `Lexus -> NX` as a model-family alias and added a regression test.

Card-only verification command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page2_cards_min40_retry.json --captured-at 2026-06-25T04:50:00Z --run-id run_20260625_spinny_page2_cards_min40_retry_smoke --capture-date 2026-06-25 --max-pages 2 --max-records 40 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --json
```

Card-only result:

- Listing records: 40.
- Minimum records required: 40.
- Listing coverage: pass.
- Payload validation: pass.
- Pricing-ready records: 40.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 85.71%.
- Optional completeness: 23.33%.

Detail-capped verification command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page2_detail20_min40.json --captured-at 2026-06-25T05:05:00Z --run-id run_20260625_spinny_page2_detail20_min40_smoke --capture-date 2026-06-25 --max-pages 2 --max-records 40 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --detail-pages 20 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Detail-capped result:

- Listing records: 40.
- Minimum records required: 40.
- Listing coverage: pass.
- Detail pages requested: 20.
- Detail pages attempted: 20.
- Detail pages successful: 20.
- Detail pages failed: 0.
- Retries used: 0.
- Timeouts: 0.
- Ownership records: 20/40.
- Payload validation: pass.
- Enriched payload validation: pass.
- Pricing-ready records: 40.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 92.85%.
- Optional completeness: 31.42%.
- Overall completeness: 91.72%.

Generated reports:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page2_cards_min40_retry_smoke_smoke_report.md
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page2_detail20_min40_smoke_smoke_report.md
```

Decision:

- Two-batch Spinny pagination is stable enough for bounded acquisition.
- Row coverage is now a first-class smoke gate, separate from field completeness.
- The next safest scale test is three scroll batches card-only before enriching more detail pages.

### E-028: Spinny Three-Batch Card-Only Pagination

Goal: test one more Spinny infinite-scroll batch without increasing detail-page enrichment cost.

Reasoning:

- The two-batch run proved 40 listing rows.
- The next risk was whether page-3 vocabulary or scroll behavior would introduce new parser gaps or coverage loss.
- Keeping this run card-only isolates listing-card capture from detail-page enrichment.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page3_cards_min60.json --captured-at 2026-06-25T05:35:00Z --run-id run_20260625_spinny_page3_cards_min60_smoke --capture-date 2026-06-25 --max-pages 3 --max-records 60 --min-records 60 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --json
```

Result:

- Listing records: 60.
- Minimum records required: 60.
- Listing coverage: pass.
- Attempted scroll batches: 3.
- Unique listing URLs: 60.
- Duplicate cards skipped: 64.
- Payload validation: pass.
- Pricing-ready records: 60.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 85.71%.
- Optional completeness: 23.33%.
- Overall completeness: 89.48%.

Pagination metrics:

- Batch 1 observed 22 cards.
- Batch 2 observed 42 cards.
- Batch 3 observed 62 cards.
- Returned rows were capped at 60 by `--max-records`.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_cards_min60_smoke_smoke_report.md
```

Decision:

- Three-batch card-only pagination is stable enough as the current listing-volume baseline.
- Do not jump to 80 or 100 listing rows yet.
- Next controlled step should be detail enrichment on the 60-row capture, starting with a bounded 30 detail pages.

### E-029: Sixty Listings With Thirty Detail Pages

Goal: keep the listing volume fixed at 60 rows and increase detail enrichment from 20 pages to 30 pages.

Reasoning:

- The 60-row card-only run already proved listing-card coverage and parser stability.
- The next risk was detail-page reliability at a larger cap.
- We should not increase listing rows and detail-page count in the same experiment.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page3_detail30_min60.json --captured-at 2026-06-25T06:05:00Z --run-id run_20260625_spinny_page3_detail30_min60_smoke --capture-date 2026-06-25 --max-pages 3 --max-records 60 --min-records 60 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --detail-pages 30 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- Listing records: 60.
- Minimum records required: 60.
- Listing coverage: pass.
- Detail pages requested: 30.
- Detail pages attempted: 30.
- Detail pages successful: 30.
- Detail pages failed: 0.
- Retries used: 0.
- Timeouts: 0.
- Ownership records: 30/60.
- First-owner records among enriched rows: 17.
- Second-owner records among enriched rows: 13.
- Payload validation: pass.
- Enriched payload validation: pass.
- Pricing-ready records: 60.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 92.85%.
- Optional completeness: 31.50%.
- Overall completeness: 91.72%.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_detail30_min60_smoke_smoke_report.md
```

Decision:

- Detail enrichment is stable through 30 pages in this bounded run.
- Ownership is now demonstrably useful as a feature: enriched rows include both first-owner and second-owner cars.
- The next controlled step should be full 60/60 detail enrichment before increasing listing volume again.

### E-030: Sixty Listings With Sixty Detail Pages

Goal: verify full detail enrichment for the current 60-row Spinny acquisition baseline.

Reasoning:

- The 60-row card-only run proved listing coverage.
- The 60-row, 30-detail run proved detail-page enrichment at half coverage.
- The next controlled step was to keep listing volume fixed and enrich all 60 listing rows before increasing any volume.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_page3_detail60_min60.json --captured-at 2026-06-25T06:45:00Z --run-id run_20260625_spinny_page3_detail60_min60_smoke --capture-date 2026-06-25 --max-pages 3 --max-records 60 --min-records 60 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --detail-pages 60 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- Listing records: 60.
- Minimum records required: 60.
- Listing coverage: pass.
- Detail pages requested: 60.
- Detail pages attempted: 60.
- Detail pages successful: 60.
- Detail pages failed: 0.
- Retries used: 0.
- Timeouts: 0.
- Ownership records: 60/60.
- First-owner records: 42.
- Second-owner records: 17.
- Third-owner records: 1.
- Payload validation: pass.
- Enriched payload validation: pass.
- Pricing-ready records: 60.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 100.00%.
- Optional completeness: 39.83%.
- Overall completeness: 93.98%.

Generated report:

```text
data/gold/smoke_reports/capture_date=2026-06-25/spinny_run_20260625_spinny_page3_detail60_min60_smoke_smoke_report.md
```

Decision:

- This is the current trusted Spinny baseline: 60 listing rows, 60 enriched detail rows, no quarantine, no manual cleanup.
- This is strong enough to move from acquisition proving to run observability and repeatability.
- Before increasing beyond 60 listing rows, add source-run manifests and acquisition metrics so repeated runs can be compared.

### D-019: Scale By Batches, Not One Huge Scrape

Date: 2026-06-25

Decision: do not increase one Spinny Hyderabad run beyond 60 rows yet. Scale with controlled batches.

Batch shape:

```text
source x city x batch_size x detail_cap x capture_date x run_id
```

Reason:

- The 60/60 Spinny run already proves the first source pipeline.
- Increasing one city from 60 to 100+ rows creates runtime cost without solving source bias or city coverage.
- Batches let us compare sources, cities, runtimes, field completeness, parser warnings, and detail failure rates.

Question answered: can this project reach 100k+ rows?

- 100k current unique active listings from trusted/certified public sources alone is unlikely from one-day scraping.
- 100k observations is realistic through repeated source-city snapshots over time.
- Example: `3 sources x 10 cities x 100 rows x 34 weekly runs = 102,000 observations`.

Files added:

- `docs/22-batch-acquisition-and-100k-row-plan.md`
- `config/acquisition_batches.yml`

Implementation added:

- source-run manifest writer,
- default manifest path under `data/gold/acquisition_runs/capture_date=.../`,
- manifest writing for passing and failing `spinny-live-smoke` runs,
- CLI `--city` and `--state` metadata for live smoke runs.

Next step:

- rerun the trusted Spinny Hyderabad 60/60 baseline with manifest output,
- then use the same batch shape for Bengaluru, Delhi NCR, Mumbai, and Chennai.

### E-031: Manifest-Enabled Spinny Hyderabad Baseline

Goal: rerun the validated Spinny Hyderabad 60/60 batch after adding source-run manifests.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-live-smoke --payload-output data/tmp/spinny_live_smoke_payload_2026-06-25_hyderabad_manifest_60_detail60.json --captured-at 2026-06-25T07:45:00Z --run-id run_20260625_spinny_hyderabad_manifest_60_detail60_smoke --capture-date 2026-06-25 --city Hyderabad --state Telangana --max-pages 3 --max-records 60 --min-records 60 --capture-attempts 4 --retry-delay-ms 2000 --page-scroll-delay-ms 5000 --timeout-ms 60000 --detail-pages 60 --detail-attempts 2 --detail-delay-ms 3000 --json
```

Result:

- Listing records: 60.
- Detail pages requested: 60.
- Detail pages successful: 60.
- Detail pages failed: 0.
- Pricing-ready records: 60.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 100.00%.
- Runtime recorded in manifest: 258.92 seconds.

Manifest:

```text
data/gold/acquisition_runs/capture_date=2026-06-25/spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_manifest.json
```

Decision:

- The source-run manifest structure is now validated on a real passing live run.
- The next Spinny batch should be Bengaluru 60/60 using the same manifest-producing command shape.

### D-020: Trusted Evaluated Sources Only For Core Model Data

Date: 2026-06-25

Decision: use only trusted, evaluated inventory sources for the core model-training dataset.

Core sources:

- Spinny,
- Mahindra First Choice,
- Maruti Suzuki True Value,
- later OEM certified sources such as Honda Auto Terrace, Hyundai Promise, and Toyota U Trust.

Reason:

- these sources are platform/dealer/OEM-evaluated,
- prices are less likely to be arbitrary customer self-pricing,
- condition and ownership signals are more consistent,
- the target variable is closer to realistic dealer/platform market price.

Delayed or excluded from core model training:

- OLX and classifieds,
- customer-priced marketplaces,
- broad marketplace paths where source trust is not proven.

Files updated:

- `config/acquisition_batches.yml`
- `docs/13-source-trust-and-priority-review.md`
- `docs/22-batch-acquisition-and-100k-row-plan.md`

### E-032: Mahindra First Choice Offline Source Contract

Goal: move to the second trusted/evaluated source without running another Spinny city first.

Source:

```text
https://www.mahindrafirstchoice.com/used-cars/hyderabad
```

Research result:

- Current Hyderabad page evidence shows 88 certified used cars.
- Listing cards expose rating/score, title, variant/details, km, fuel, transmission, price, optional EMI, and locality.
- Ownership exists as a filter but not as a visible listing-card value.
- Registration code is not visible on listing cards.
- Detail page inspection returned a blocked/403 response during research, so detail enrichment is deferred.

Implementation added:

- `src/used_car_price_intelligence/adapters/common.py`
- `src/used_car_price_intelligence/adapters/mahindra_first_choice.py`
- `tests/fixtures/mahindra_first_choice/listing_cards_extracted.json`
- `tests/unit/test_mahindra_first_choice_adapter.py`
- CLI support for `mahindra_first_choice` in `run-fixture`, `field-profile`, and `validate-payload`.
- Parser support for `S-Presso`, `BR-V`, `Tigor EV`, `Petrol+LPG`, `IMT`, and `IVT`.

Validation command:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli run-fixture --source mahindra_first_choice --captured-at 2026-06-25T03:30:00Z --run-id run_20260625_mfc_fixture_cli_check --json
```

Result:

- Records: 9.
- Pricing-ready: 9.
- Quarantined: 0.
- Required completeness: 100.00%.
- High-value completeness: 71.43%.
- Known high-value gaps: ownership and registration code.

Decision:

- MFC is approved for the next live source milestone.
- First live MFC target should be listing-card-only Hyderabad `min_records=40`, `detail_pages=0`.
- Do not require Spinny-level 100% high-value completeness for MFC until detail enrichment or alternate ownership/registration extraction is solved.

### E-033: Mahindra First Choice Live Smoke And Source Boundary

Goal: validate MFC as a real live source and decide whether it should share Spinny's acquisition path.

Reasoning:

- The user correctly noticed that Mahindra First Choice behaves differently from Spinny.
- Treating MFC as just another Spinny-like scraper would create brittle code and confusing data assumptions.
- The right boundary is source-specific acquisition and adapter logic, followed by shared canonical schema, validation, reporting, storage, and manifests.

Implementation added:

- `src/used_car_price_intelligence/acquisition/mahindra_first_choice_live.py`
- `capture-mfc-live` CLI command.
- `mfc-live-smoke` CLI command.
- Structured MFC payload support in `MahindraFirstChoiceFixtureAdapter`.
- Registration parser support for plate-like values such as `TS07AB1234`.
- `docs/24-source-specific-acquisition-boundaries.md`.

Source behavior found:

- MFC page 1 listings are available in Next.js `__NEXT_DATA__`.
- MFC pagination is loaded by browser-triggered XHR responses.
- Direct API calls without the browser frontend context returned authorization failure during testing.
- Live structured rows include ownership, body type, color, dealer, warranty, posted date, optional EMI, and partial registration data.
- Detail pages are not needed for the first MFC pricing-ready rows.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli mfc-live-smoke --payload-output data/tmp/mfc_live_smoke_payload_2026-06-25_hyderabad_40.json --captured-at 2026-06-25T09:10:00Z --run-id run_20260625_mfc_hyderabad_40_smoke --capture-date 2026-06-25 --city Hyderabad --state Telangana --max-pages 2 --max-records 40 --min-records 40 --capture-attempts 3 --retry-delay-ms 2000 --page-scroll-delay-ms 2500 --timeout-ms 60000 --json
```

Result:

- Source total items observed: 88.
- Unique cards seen during pagination: 88.
- Returned records: 40.
- Pricing-ready records: 40.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 91.78%.
- Optional completeness: 36.50%.
- Overall completeness: 92.01%.
- Ownership: 40/40.
- Registration code: 17/40.
- Detail pages: 0.

Decision:

- MFC stays separate from Spinny in every acquisition-facing way: browser flow, payload contract, adapter, smoke command, and source docs.
- MFC joins the shared system only after canonical records are produced.
- Registration coverage remains the main MFC high-value gap, but it does not block pricing-ready rows because required pricing fields are complete.

### E-034: Spinny vs Mahindra First Choice Field Comparison

Goal: compare the first two trusted live source runs field-by-field after canonicalization.

Reasoning:

- The project should not assume that two trusted sources expose the same feature set.
- The right comparison point is the canonical silver output, not raw website text.
- The comparison should be reproducible, because the same report will be needed again after True Value, OEM certified sources, and later city batches.

Implementation added:

- `src/used_car_price_intelligence/reporting/source_comparison.py`
- `compare-sources` CLI command.
- `tests/unit/test_source_comparison.py`
- CLI regression coverage for writing a source comparison report.
- `docs/25-spinny-vs-mahindra-first-choice-field-comparison.md`

Compared runs:

- Spinny: `run_20260625_spinny_hyderabad_manifest_60_detail60_smoke`
- Mahindra First Choice: `run_20260625_mfc_hyderabad_40_smoke`

Result:

- Spinny: 60 records, 60 pricing-ready, 0 quarantined, required completeness 100.00%, high-value completeness 100.00%.
- MFC: 40 records, 40 pricing-ready, 0 quarantined, required completeness 100.00%, high-value completeness 91.78%.
- Required pricing fields are complete in both sources.
- Ownership is complete in both sources.
- Registration code is complete in Spinny, but partial in MFC: 17/40.
- MFC has fields Spinny currently lacks at canonical level: body type, color, dealer name, and listing posted date.
- Spinny has full detail-page enrichment: registration year/state/type, return policy, and richer inspection/insurance evidence in `extra_fields`.

Decision:

- Both sources can contribute to the gold pricing-ready dataset.
- Source provenance must stay in the model features and reports because field coverage and source semantics differ.
- Source-specific rating and inspection fields should stay in `extra_fields` until a normalization strategy is proven.
- Add True Value as the third source contract before large-scale scraping.

### D-021: True Value Is Validated But Brand-Biased

Date: 2026-06-25

Decision: approve Maruti Suzuki True Value as the third trusted source contract, but treat it as a Maruti/OEM-specific source rather than a general market source.

Reason:

- True Value is OEM-backed and dealer/evaluation-oriented, which matches the trusted-core dataset policy.
- The live source exposes structured price, model, year, variant, km, fuel, transmission, ownership, registration, dealer, body type, color, certification, warranty, and rating fields.
- The source is Maruti-only, so it can strengthen Maruti coverage but will bias a model if overrepresented.

Impact:

- Updated `config/source_registry.yml` to mark True Value as a validated OEM certified source.
- Updated `config/acquisition_batches.yml` with the latest validated True Value Hyderabad run.
- Added `docs/26-true-value-source-evaluation.md`.

### E-035: True Value Fixture, Live Acquisition, And Hyderabad Smoke

Goal: evaluate True Value as the third trusted source and decide whether it is ready for batch collection.

Source:

```text
https://www.marutisuzukitruevalue.com/buy-car
```

Source behavior found:

- The city-specific page was not useful as a direct headless text source.
- The `/buy-car` inventory app loads structured data.
- The acquisition path is dealer discovery by latitude/longitude and radius, followed by GraphQL product search using discovered True Value dealer codes.
- Hyderabad discovery returned 21 True Value dealers for the 25 km radius used in the smoke run.
- The live Hyderabad source total observed in the validated run was 247 rows across 3 GraphQL pages.

Implementation added:

- `src/used_car_price_intelligence/adapters/true_value.py`
- `src/used_car_price_intelligence/acquisition/true_value_live.py`
- `tests/fixtures/true_value/listing_cards_extracted.json`
- `tests/unit/test_true_value_adapter.py`
- `tests/unit/test_true_value_live_acquisition.py`
- CLI support for `capture-true-value-live` and `true-value-live-smoke`.
- Parser vocabulary support for Maruti model families observed during True Value research.

Validated command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli true-value-live-smoke --payload-output data/tmp/true_value_live_smoke_payload_2026-06-25_hyderabad_40.json --run-id run_20260625_true_value_hyderabad_40_smoke --capture-date 2026-06-25 --city Hyderabad --state Telangana --latitude 17.385044 --longitude 78.486671 --dealer-distance-m 25000 --max-pages 1 --page-size 100 --max-records 40 --min-records 40 --capture-attempts 3 --retry-delay-ms 2000 --timeout-seconds 60 --json
```

Result:

- Captured at: `2026-06-25T13:54:29Z`.
- Listing records: 40.
- Minimum records required: 40.
- Dealer count: 21.
- Source total items observed: 247.
- Source total pages: 3.
- Unique source rows seen on first GraphQL page: 100.
- Payload validation: pass.
- Pricing-ready records: 40.
- Quarantined records: 0.
- Required completeness: 100.00%.
- High-value completeness: 100.00%.
- Optional completeness: 42.25%.
- Overall completeness: 94.22%.

Important field observations:

- Registration code: 40/40.
- Ownership: 40/40.
- Body type: 40/40.
- Dealer name: 40/40.
- Color: 39/40.
- DMS certification status: 39/40.
- Warranty code: 40/40, but `0M` means no warranty label.
- True Value certified flag: 27 yes, 13 no.

Decision:

- True Value is ready for controlled acquisition batches.
- Do not normalize True Value ratings or certification status into global inspection scores yet.
- The next project step should be a three-source comparison and then a resumable batch runner for source-city collection.

### E-036: Three-Source Trusted Field Comparison

Goal: compare the three validated Hyderabad source runs field-by-field after canonicalization.

Reasoning:

- Spinny, Mahindra First Choice, and True Value now all produce pricing-ready rows.
- Before data collection scales, the project needs a single evidence document showing what is common and what remains source-specific.
- Pairwise comparison was no longer enough once the third source passed.

Implementation added:

- `render_multi_source_comparison_report()`.
- `compare-source-runs` CLI command.
- Unit coverage for the multi-source renderer and CLI command.
- `docs/27-three-source-field-comparison.md`.

Compared runs:

- Spinny: `run_20260625_spinny_hyderabad_manifest_60_detail60_smoke`
- Mahindra First Choice: `run_20260625_mfc_hyderabad_40_smoke`
- True Value: `run_20260625_true_value_hyderabad_40_smoke`

Result:

- Spinny: 60 records, 60 pricing-ready, 0 quarantined.
- MFC: 40 records, 40 pricing-ready, 0 quarantined.
- True Value: 40 records, 40 pricing-ready, 0 quarantined.
- Required completeness is 100.00% across all three sources.
- Ownership is complete across all three sources.
- Registration code is complete in Spinny and True Value, but partial in MFC.
- Body type and dealer name are complete in MFC and True Value, but missing at canonical level for Spinny.
- Warranty label differs by source: Spinny 57/60, MFC 40/40, True Value 28/40.
- Source-specific ratings, inspection states, and certification statuses stay in `extra_fields`.

Decision:

- The first three Hyderabad trusted source contracts are validated.
- The next engineering step is a resumable batch runner for controlled source-city acquisition.

### E-037: Batch Runner Foundation

Goal: move from manual smoke commands to a controlled batch planning surface.

Reasoning:

- The project now has three validated Hyderabad source contracts.
- Manually running one command at a time will not scale to source-city acquisition.
- Batch collection needs a single manifest that records the planned jobs before execution.
- Execution should be explicit, not accidental, because Spinny full-detail batches can take several minutes.

Implementation added:

- `src/used_car_price_intelligence/pipeline/batch_runner.py`
- `run-batches` CLI command.
- `tests/unit/test_batch_runner.py`
- CLI regression coverage for dry-run batch manifest writing.
- `docs/28-batch-runner-foundation.md`
- explicit validated batch definitions for Spinny Hyderabad, MFC Hyderabad, and True Value Hyderabad in `config/acquisition_batches.yml`.

Dry-run command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --status validated --capture-date 2026-06-25 --batch-run-id batch_20260625_validated_hyderabad_dry_run --json
```

Result:

- Status: `planned`.
- Job count: 3.
- Planned jobs:
  - `spinny_hyderabad_60_detail60`
  - `mfc_hyderabad_40`
  - `true_value_hyderabad_40`
- Manifest written to:

```text
data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_validated_hyderabad_dry_run_batch_manifest.json
```

Decision:

- Batch execution must require `--execute`.
- Dry-run mode should be used before every new batch set.
- The safest first execution proof is `true_value_hyderabad_40`, because it completes quickly compared with Spinny full-detail enrichment.

Execution proof command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id true_value_hyderabad_40 --capture-date 2026-06-25 --batch-run-id batch_20260625_true_value_execute_check --execute --json
```

Execution proof result:

- Batch status: `pass`.
- Batch id: `true_value_hyderabad_40`.
- Job exit code: 0.
- Source run id: `run_20260625_true_value_hyderabad_40_batch_20260625_true_value_execute_check`.
- Nested source smoke result: 40 pricing-ready rows, 0 quarantined rows, required completeness 100.00%, high-value completeness 100.00%.
- Batch manifest:

```text
data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_true_value_execute_check_batch_manifest.json
```

### E-038: Resumable Batch Runner And 100k Acceleration Plan

Question:

- Can we collect 100,000 good rows faster without turning the project into a fragile long scrape?

Decision:

- Do not chase 100,000 current unique rows from only three trusted sites in one short run.
- Treat 100,000 as a repeated market-observation target unless licensed or partner data is introduced.
- Use fast structured sources first:
  - True Value dealer discovery plus GraphQL.
  - Mahindra First Choice structured Next.js/XHR data.
- Keep Spinny full-detail pages as high-value enrichment, but do not make every bulk row wait for full detail capture.

Implementation:

- Added resume/skip support to `run-batches`:
  - `--resume-from-manifest`
  - `--skip-passed`
- Added batch-level Markdown summaries:
  - `data/gold/batch_runs/capture_date=YYYY-MM-DD/<batch_run_id>_batch_summary.md`
- Expanded `config/acquisition_batches.yml` with planned 5-city batches across:
  - Spinny
  - Mahindra First Choice
  - True Value
- Added `docs/29-100k-collection-acceleration-plan.md`.

Research conclusion:

- Spinny appears useful for high-quality trusted rows but is slower when full detail enrichment is required.
- True Value is the fastest current trusted bulk candidate but has Maruti-only brand bias.
- MFC is a useful multi-brand trusted source but public city inventory can be uneven.
- A fast 100,000-current-row dataset likely requires licensed listing data, partner feeds, or adding more trusted/OEM sources.
- A strong 100,000-observation dataset is realistic through repeated snapshots.

Next execution sequence:

1. Dry-run the 5-city planned batch set.
2. Execute True Value city batches first.
3. Execute MFC city batches second.
4. Run Spinny detail batches after fast structured sources complete.
5. Add dedupe/lifecycle tracking before repeated snapshots.

### E-039: True Value 5-City Fast Collection

Question:

- Can the fastest trusted source collect real multi-city rows quickly while preserving gold-quality gates?

Execution:

- Ran the 5-city True Value batch through `run-batches`.
- Hyderabad was skipped from the previous passing batch manifest.
- Bengaluru, Delhi NCR, Mumbai, and Chennai were executed/resumed through the same batch id:

```text
batch_20260625_true_value_5city_fast_execute
```

Final result:

- Batch status: `pass`.
- Pricing-ready rows: 429.
- Quarantined rows: 0.
- Required completeness: 100.00% for every city.
- High-value completeness: 100.00% for every city.

City result:

| City | Pricing-ready rows | Source total observed |
| --- | ---: | ---: |
| Hyderabad | 40 | 247 |
| Bengaluru | 100 | 221 |
| Delhi NCR | 100 | 617 |
| Mumbai | 100 | 311 |
| Chennai | 89 | 95 |

Data-quality issues discovered and fixed:

- Bengaluru returned unavailable inventory; True Value acquisition now skips `inStock=false` products.
- Delhi NCR returned one product missing model and variant; acquisition now skips rows missing pricing-critical product fields.
- Chennai returned odometer outliers at 304,687 km and 908,653 km; acquisition now skips rows above the pricing-ready km ceiling.
- Each skip type is recorded in listing capture metrics:
  - `unavailable_rows_skipped`
  - `incomplete_rows_skipped`
  - `km_outlier_rows_skipped`

Artifacts:

```text
docs/30-true-value-5city-fast-collection-run.md
data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_true_value_5city_fast_execute_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-25/batch_20260625_true_value_5city_fast_execute_batch_summary.md
```

Verification:

```text
.venv\Scripts\python -m unittest discover -s tests
```

Result:

```text
Ran 128 tests in 3.874s
OK
```

Decision:

- True Value is now proven as the fast structured bulk path.
- Next source should be Mahindra First Choice, because it is the next structured source and gives multi-brand coverage.
- Spinny full-detail city batches should still wait until MFC multi-city behavior is understood.

### E-040: Mahindra First Choice 5-City Collection

Question:

- Can MFC work as the second structured multi-city trusted source?

Execution:

- Ran MFC through `run-batches` across:
  - Hyderabad
  - Bengaluru
  - Delhi NCR
  - Mumbai
  - Chennai
- Batch id:

```text
batch_20260626_mfc_5city_execute
```

Final result:

- Batch status: `pass`.
- Pricing-ready rows: 180.
- Quarantined rows: 0.
- Required completeness: 100.00% for every city.

City result:

| City | Pricing-ready rows | Source total observed | Coverage reason |
| --- | ---: | ---: | --- |
| Hyderabad | 40 | 89 | ok |
| Bengaluru | 80 | 126 | ok |
| Delhi NCR | 3 | 3 | source_total_below_minimum |
| Mumbai | 10 | 10 | source_total_below_minimum |
| Chennai | 47 | 47 | ok |

Issues discovered and fixed:

- Browser navigation can fail transiently with `net::ERR_CONNECTION_RESET`; MFC acquisition now catches Playwright navigation errors per attempt and retries.
- Some city pages expose fewer rows than the requested target; listing coverage is now source-aware and can pass with `source_total_below_minimum` when all source-reported rows are captured cleanly.

Artifacts:

```text
docs/31-mahindra-first-choice-5city-collection-run.md
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5city_execute_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5city_execute_batch_summary.md
```

Current trusted row total:

```text
True Value 5-city: 429
MFC 5-city: 180
Spinny Hyderabad full-detail baseline: 60
Combined current pricing-ready rows: 669
```

Verification:

```text
.venv\Scripts\python -m unittest discover -s tests
```

Result:

```text
Ran 129 tests in 6.129s
OK
```

Decision:

- MFC is clean but uneven; it is useful for trusted multi-brand rows but not a high-volume source in every city.
- Before adding more Spinny detail-heavy city runs, build a collection ledger that summarizes all passing source-run manifests.

### E-041: Trusted Collection Ledger

Question:

- How do we count the current trusted dataset without accidentally including old smoke runs or failed retries?

Decision:

- Build an explicit collection ledger from selected batch/source manifests.
- Do not scan every acquisition manifest by default because that would overcount exploratory runs.

Implementation:

- Added `collection-ledger` CLI.
- Added `src/used_car_price_intelligence/reporting/collection_ledger.py`.
- Added tests for ledger generation and CLI output writing.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli collection-ledger --collection-id trusted_collection_v0_20260626 --source-manifest data\gold\acquisition_runs\capture_date=2026-06-25\spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_manifest.json --batch-manifest data\gold\batch_runs\capture_date=2026-06-25\batch_20260625_true_value_5city_fast_execute_batch_manifest.json --batch-manifest data\gold\batch_runs\capture_date=2026-06-26\batch_20260626_mfc_5city_execute_batch_manifest.json --output-json data\gold\collection_ledger\trusted_collection_v0_20260626.json --output-md data\gold\collection_ledger\trusted_collection_v0_20260626.md --json
```

Result:

- Source runs counted: 11.
- Pricing-ready rows: 669.
- Quarantined rows: 0.
- Source-total inventory signal: 1,766.

By source:

| Source | Runs | Pricing-ready rows |
| --- | ---: | ---: |
| Spinny | 1 | 60 |
| True Value | 5 | 429 |
| Mahindra First Choice | 5 | 180 |

Artifacts:

```text
docs/32-collection-ledger.md
data/gold/collection_ledger/trusted_collection_v0_20260626.json
data/gold/collection_ledger/trusted_collection_v0_20260626.md
```

Verification:

```text
.venv\Scripts\python -m unittest discover -s tests
```

Result:

```text
Ran 132 tests in 6.600s
OK
```

Decision:

- The current row count is now manifest-backed and reproducible.
- Next collection step can be Spinny multi-city, starting with one non-Hyderabad city.

### E-042: Spinny Bengaluru Hub Full-Detail Run

Question:

- Can the Spinny full-detail workflow work outside Hyderabad without lowering the 60-row completeness gate?

Decision:

- Start with one non-Hyderabad Spinny city before running all remaining Spinny batches.
- Use the Bengaluru hub page instead of the generic city page after the generic page exposed only 21 clean listing URLs.

Initial failed command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id spinny_bengaluru_60_detail60 --capture-date 2026-06-26 --batch-run-id batch_20260626_spinny_bengaluru_detail_execute --execute --json
```

Initial result:

- Status: fail.
- Records total: 21.
- Minimum required: 60.
- Stop reason: `no_new_cards_after_scroll`.

Hub URL decision:

```text
https://www.spinny.com/used-cars-at-bangalore-vega-mall-hub-in-bangalore/s/
```

Second issue:

- Hub capture reached 59/60 clean records.
- The scraper stopped on 60 raw DOM cards, but the quality gate counts parsed clean listing records.

Fix:

- Spinny acquisition now captures raw-card headroom when a strict `min_records` gate is used.
- The final payload is capped back to `max_records`, so the dataset still contains 60 clean rows.
- New listing-capture diagnostics: `snapshot_max_records`, `raw_cards_returned`, and `parsed_records_before_cap`.

Successful command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --batch-id spinny_bengaluru_60_detail60 --capture-date 2026-06-26 --batch-run-id batch_20260626_spinny_bengaluru_hub_detail_execute_v2 --execute --json
```

Successful result:

- Status: pass.
- Pricing-ready rows: 60.
- Quarantined rows: 0.
- Required completeness: 100.00%.
- High-value completeness: 100.00%.
- Detail successful: 60/60.
- Runtime: 459.478 seconds.
- Listing capture: 62 raw cards returned, 61 parsed records before cap, 60 clean records returned.

Updated ledger:

- Collection id: `trusted_collection_v1_20260626`.
- Source runs counted: 12.
- Pricing-ready rows: 729.
- Quarantined rows: 0.

Artifacts:

```text
docs/33-spinny-bengaluru-hub-collection-run.md
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_spinny_bengaluru_hub_detail_execute_v2_batch_manifest.json
data/gold/acquisition_runs/capture_date=2026-06-26/spinny_run_20260626_spinny_bengaluru_60_detail60_batch_20260626_spinny_bengaluru_hub_detail_execute_v2_manifest.json
data/gold/collection_ledger/trusted_collection_v1_20260626.json
data/gold/collection_ledger/trusted_collection_v1_20260626.md
```

Verification:

```text
.venv\Scripts\python -m unittest tests.unit.test_spinny_live_acquisition tests.unit.test_batch_runner tests.unit.test_cli
.venv\Scripts\python -m compileall src tests
.venv\Scripts\python -m unittest discover -s tests
```

Result:

```text
43 tests passed
compileall passed
133 tests passed
```

Decision:

- The Spinny full-detail path is valid beyond Hyderabad.
- Do not parallelize Spinny detail collection yet because 60 full-detail rows took about 7.7 minutes.
- Run Delhi NCR, Mumbai, and Chennai next, then regenerate the ledger again.

### E-043: Spinny Remaining Hubs And v2 Ledger

Question:

- Can the remaining planned Spinny hub cities pass the same 60-row full-detail gate?

Decision:

- Use official/high-inventory Spinny hub pages for Delhi NCR, Mumbai, and Chennai rather than generic city pages.
- Keep the strict 60-row quality gate.
- Fix parser/source issues instead of lowering thresholds.

Hub pages:

| City | Hub URL |
| --- | --- |
| Delhi NCR | `https://www.spinny.com/used-cars-at-delhi-dwarka-sector-21-taj-vivanta-hub-in-delhi-ncr/s/` |
| Mumbai | `https://www.spinny.com/used-cars-at-mumbai-dadar-hub-in-mumbai/s/` |
| Chennai | `https://www.spinny.com/used-cars-at-chennai-nexus-vijaya-mall-in-chennai/s/` |

Issues found:

- Delhi valid RTO codes like `DL3C`, `DL4C`, and `DL9C` were rejected by the Spinny card parser.
- Spinny initial `page.goto` needed retry handling for transient browser/network failures.
- Chennai included a valid `2014 Mini Countryman One`, but `Mini` was missing from the title parser vocabulary.

Fixes:

- Widened Spinny card-level registration detection for RTO suffix letters.
- Added fresh-page retry handling to Spinny listing capture.
- Added `Mini` brand aliases and `Countryman` model vocabulary.
- Added parser/acquisition regression tests.

Passing results:

| City | Pricing-ready rows | Quarantined rows | Detail success | Runtime |
| --- | ---: | ---: | ---: | ---: |
| Delhi NCR | 60 | 0 | 60/60 | 275.601s |
| Mumbai | 60 | 0 | 60/60 | 440.488s |
| Chennai | 60 | 0 | 60/60 | 283.533s |

Updated Spinny total:

```text
300 pricing-ready rows across 5 cities, 0 quarantined
```

Updated full collection ledger:

- Collection id: `trusted_collection_v2_20260626`.
- Source runs counted: 15.
- Pricing-ready rows: 909.
- Quarantined rows: 0.

By source:

| Source | Runs | Pricing-ready rows |
| --- | ---: | ---: |
| Spinny | 5 | 300 |
| True Value | 5 | 429 |
| Mahindra First Choice | 5 | 180 |

Artifacts:

```text
docs/34-spinny-remaining-hubs-collection-run.md
data/gold/collection_ledger/trusted_collection_v2_20260626.json
data/gold/collection_ledger/trusted_collection_v2_20260626.md
```

Verification:

```text
.venv\Scripts\python -m unittest discover -s tests
```

Result:

```text
134 tests passed
```

Decision:

- First-pass trusted collection is now strong enough to pause scraping and build dedupe/lifecycle tracking.
- Further collection without stable listing identity would risk duplicate rows and weak time-series semantics.

### E-044: Listing Lifecycle And Dedupe Foundation

Question:

- Before scraping more rows, can we prove the current 909-row collection is unique at the listing level and ready for repeated snapshots?

Decision:

- Build a lifecycle index from the curated `trusted_collection_v2_20260626` ledger.
- Separate exact source listing identity from possible vehicle duplicate review.
- Do not automatically merge possible vehicle duplicates without stronger identifiers such as full registration, VIN, or direct source evidence.

Identity policy:

- Exact listing key: `source + normalized listing_url`, falling back to `source_listing_id`, `raw_record_hash`, then core fields.
- Vehicle fingerprint: conservative review key using city, brand, model, variant, year, fuel, transmission, ownership, registration code, km bucket, and price bucket.
- Km bucket: 5,000 km.
- Price bucket: Rs 50,000.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli listing-lifecycle --lifecycle-id listing_lifecycle_v0_20260626 --collection-ledger data\gold\collection_ledger\trusted_collection_v2_20260626.json --output-json data\gold\listing_lifecycle\listing_lifecycle_v0_20260626.json --output-md data\gold\listing_lifecycle\listing_lifecycle_v0_20260626.md
```

Result:

- Records processed: 909.
- Source runs: 15.
- Unique listing keys: 909.
- Reobserved listing groups: 0.
- Possible vehicle duplicate groups: 1.

By source:

| Source | Records | Unique listing keys | Possible duplicate groups |
| --- | ---: | ---: | ---: |
| Spinny | 300 | 300 | 0 |
| True Value | 429 | 429 | 1 |
| Mahindra First Choice | 180 | 180 | 0 |

The only possible duplicate group is two True Value Delhi NCR 2011 Maruti Suzuki Wagon R LXI rows with close km, close price, and the same `DL13` registration code. This is a review signal, not an automatic merge.

Artifacts:

```text
docs/35-listing-lifecycle-dedupe-foundation.md
src/used_car_price_intelligence/reporting/listing_lifecycle.py
tests/unit/test_listing_lifecycle.py
data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.json
data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.md
```

Verification:

```text
.venv\Scripts\python -m unittest tests.unit.test_listing_lifecycle tests.unit.test_cli
.venv\Scripts\python -m compileall src tests
```

Result:

```text
29 tests passed
compileall passed
```

Decision:

- Current selected collection behaves as 909 unique source listings.
- The next platform step is snapshot orchestration: added/removed/still-active listing tracking between lifecycle indexes.

### E-045: Snapshot Orchestration Foundation

Question:

- How do we convert the current 909-row trusted collection into a repeatable baseline market snapshot before collecting more rows?

Decision:

- Add a snapshot diff layer after the collection ledger and lifecycle index.
- Store a compact baseline snapshot manifest for the current trusted scope.
- Treat the current lifecycle as the first baseline snapshot because there is no previous lifecycle to compare against.
- Use lifecycle `listing_key` as the only diff identity key. Do not use fuzzy cross-source vehicle matching for snapshot changes.

Command:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli snapshot-diff --snapshot-id snapshot_20260626_trusted_v2_baseline --snapshot-date 2026-06-26 --current-lifecycle data/gold/listing_lifecycle/listing_lifecycle_v0_20260626.json --output-json data/gold/snapshot_diffs/snapshot_20260626_trusted_v2_baseline_diff.json --output-md data/gold/snapshot_diffs/snapshot_20260626_trusted_v2_baseline_diff.md
```

Result:

- Baseline mode: yes.
- Previous unique listing keys: 0.
- Current unique listing keys: 909.
- Added listings: 909.
- Removed listings: 0.
- Still-active listings: 0.
- Price changes: 0.
- Km changes: 0.

By source:

| Source | Current listing keys | Added in baseline |
| --- | ---: | ---: |
| Spinny | 300 | 300 |
| True Value | 429 | 429 |
| Mahindra First Choice | 180 | 180 |

Artifacts:

```text
docs/36-snapshot-orchestration-foundation.md
src/used_car_price_intelligence/reporting/snapshot_diff.py
tests/unit/test_snapshot_diff.py
data/gold/snapshots/snapshot_20260626_trusted_v2_manifest.json
data/gold/snapshot_diffs/snapshot_20260626_trusted_v2_baseline_diff.json
data/gold/snapshot_diffs/snapshot_20260626_trusted_v2_baseline_diff.md
```

Important interpretation rule:

- Removed listings in a future diff mean "not observed in the current selected lifecycle." They should only be treated as sold/unavailable if the source-city coverage is equivalent to the previous snapshot.

Decision:

- The project now has a repeatable baseline snapshot.
- Future collection runs should build a new ledger, lifecycle index, and snapshot diff before any rows are added to model training.

### E-046: 100k Scale Collection Strategy

Question:

- When should we move toward about 100,000 rows, and can we use Kaggle or other tools to do it faster?

Decision:

- Do not start full 100k scraping immediately.
- First run one repeated equivalent snapshot over the same trusted source-city scope.
- Treat the 100k target as 100k trusted listing observations over repeated snapshots, not 100k unique active cars in one day.
- Use Kaggle for EDA, modeling, and artifact review. Do not make Kaggle the primary live scraper.

Reasoning:

- The current baseline has 909 trusted rows from 15 source-city runs.
- At the same scope, 100k observations would require about 111 snapshots.
- A faster path requires broader trusted source-city coverage, repeated snapshots, bounded parallelism, and incremental detail enrichment.
- Trusted sites have finite evaluated inventory, so repeated observations are more realistic than trying to scrape 100k unique current cars from three sources in one run.

Current scale policy:

```text
config/scale_collection_policy.yml
```

Scale runbook:

```text
docs/37-100k-scale-collection-runbook.md
```

Kaggle bridge:

```text
notebooks/kaggle_collection_bridge.py
```

Go/no-go gates before high scale:

- Repeat same-scope snapshot passes.
- Required completeness stays at 100%.
- High-value completeness stays at or above 95%.
- Quarantine rate stays at or below 1%.
- Lifecycle duplicate signals are explainable.
- Removed listings are interpreted only with equivalent source-city coverage.
- Batch execution can resume and skip passed jobs.

Recommended scaling lanes:

| Lane | Source | Role |
| --- | --- | --- |
| 1 | True Value | First expansion lane because row yield and structured capture are strongest. |
| 2 | Mahindra First Choice | Multi-brand expansion lane, kept separate due different website mechanics. |
| 3 | Spinny | Quality anchor, but detail pages make it slower. |

Decision:

- Next operational step is not 100k yet.
- Next operational step is `trusted_collection_v3`: repeat the same 15 validated source-city jobs, regenerate lifecycle, and diff against the baseline.

### E-047: 5k Snapshot Target

Question:

- What is the ideal row count per snapshot for reaching 100,000 trusted observations?

Decision:

- Use 5,000 rows per snapshot as the first production-scale target.
- Use 10,000 rows per snapshot only as a later stretch target.
- Keep the next immediate snapshot at the current same-scope baseline size before expanding.

Projection:

| Scenario | Rows Per Future Snapshot | Future Snapshots Needed | Total Snapshots Including Baseline |
| --- | ---: | ---: | ---: |
| Current scope | 909 | 110 | 111 |
| Small scale | 2,500 | 40 | 41 |
| Recommended | 5,000 | 20 | 21 |
| Stretch | 10,000 | 10 | 11 |

Recommended 5k allocation:

| Source | Target Rows Per Snapshot | Share |
| --- | ---: | ---: |
| True Value | 2,500 | 50% |
| Mahindra First Choice | 1,500 | 30% |
| Spinny | 1,000 | 20% |

Command:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli scale-projection --target-id target_100k_trusted_observations_v0 --target-observations 100000 --current-snapshot-manifest data/gold/snapshots/snapshot_20260626_trusted_v2_manifest.json --recommended-rows-per-snapshot 5000 --output-json data/gold/scale_projection/target_100k_5k_snapshot_projection.json --output-md data/gold/scale_projection/target_100k_5k_snapshot_projection.md
```

Artifacts:

```text
config/snapshot_targets.yml
docs/38-5k-snapshot-target-plan.md
src/used_car_price_intelligence/reporting/scale_projection.py
tests/unit/test_scale_projection.py
data/gold/scale_projection/target_100k_5k_snapshot_projection.json
data/gold/scale_projection/target_100k_5k_snapshot_projection.md
```

Decision:

- The active scale plan is: repeat baseline, then 2,500 rows, then 5,000 rows, then consider 10,000 rows.

### E-048: Repeat Snapshot V3

Question:

- Can the platform repeat the same 15-job trusted source-city scope and produce a useful lifecycle diff against the baseline?

Decision:

- Yes. The repeat snapshot gate passed.
- The next expansion step can target about 2,500 rows per snapshot before moving toward 5,000 rows.

Execution:

- Initial repeat batch: `batch_20260626_repeat_snapshot_v3_same_scope_execute`
- Resume 1: `batch_20260626_repeat_snapshot_v3_same_scope_resume1`
- Final resume: `batch_20260626_repeat_snapshot_v3_same_scope_resume2`

Transient failures handled:

- Spinny Delhi NCR initially returned 0 cards and failed the payload contract.
- Spinny Chennai later hit a detail-page `ERR_CONNECTION_RESET`.
- Resume flow recovered both and completed the 15-job scope.

Collection result:

| Source | Source Runs | Pricing-Ready Rows | Quarantined |
| --- | ---: | ---: | ---: |
| Spinny | 5 | 300 | 0 |
| True Value | 5 | 432 | 0 |
| Mahindra First Choice | 5 | 179 | 0 |
| Total | 15 | 911 | 0 |

Lifecycle result:

- Lifecycle id: `listing_lifecycle_v1_20260626_repeat_snapshot`
- Records processed: 911.
- Unique listing keys: 911.
- Reobserved listing groups: 0.
- Possible vehicle duplicate groups: 0.

Diff against baseline:

| Metric | Count |
| --- | ---: |
| Previous unique listing keys | 909 |
| Current unique listing keys | 911 |
| Added listings | 101 |
| Removed listings | 99 |
| Still-active listings | 810 |
| Price changes | 3 |
| Km changes | 1 |

By source:

| Source | Added | Removed | Still Active | Price Changes | Km Changes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Spinny | 49 | 49 | 251 | 3 | 1 |
| True Value | 44 | 41 | 388 | 0 | 0 |
| Mahindra First Choice | 8 | 9 | 171 | 0 | 0 |

Artifacts:

```text
docs/39-repeat-snapshot-v3-run.md
data/gold/snapshots/snapshot_20260626_repeat_v3_manifest.json
data/gold/collection_ledger/trusted_collection_v3_20260626_repeat_snapshot.json
data/gold/collection_ledger/trusted_collection_v3_20260626_repeat_snapshot.md
data/gold/listing_lifecycle/listing_lifecycle_v1_20260626_repeat_snapshot.json
data/gold/listing_lifecycle/listing_lifecycle_v1_20260626_repeat_snapshot.md
data/gold/snapshot_diffs/snapshot_20260626_repeat_v3_vs_baseline_diff.json
data/gold/snapshot_diffs/snapshot_20260626_repeat_v3_vs_baseline_diff.md
```

Important interpretation:

- `still_active` is strong repeated-listing evidence.
- `price_changes` are strong same-listing market signals.
- `removed` is still a candidate unavailable/sold signal, not a final label, because current snapshots are capped source windows.

### E-049: 2,500-Row Expansion Snapshot

Question:

- Can the platform expand beyond the 911-row repeat snapshot toward the 2,500-row trusted snapshot target without lowering data quality?

Decision:

- Yes. The 2,500-row trusted snapshot target is complete.
- The first expansion pass reached 1,919 pricing-ready rows, leaving a 581-row gap.
- A separate True Value gap-close batch added 877 pricing-ready rows.
- Final target-met result: 2,796 pricing-ready rows, 0 quarantined, 34 source-city runs.

Execution:

- Added ten True Value `expansion_2500` source-city jobs in `config/acquisition_batches.yml`.
- Final successful batch: `batch_20260626_true_value_2500_expansion_execute_v7`.
- Final True Value expansion result: 1,440 pricing-ready rows, 0 quarantined.
- Added fourteen True Value `gap_close_2500` source-city jobs in `config/acquisition_batches.yml`.
- Final successful gap-close batch: `batch_20260626_true_value_2500_gap_close_resume1`.
- Final True Value gap-close result: 877 pricing-ready rows, 0 quarantined.
- Combined with repeat v3 Spinny/MFC runs: 2,796 pricing-ready rows, 0 quarantined, 34 source-city runs.

Parser hardening:

- First expansion attempts exposed a valid registration parsing issue, not a bad row.
- Added RTO alias parsing for `PORT BLAIR` -> `AN01`, Andaman and Nicobar Islands.
- Added legacy registration prefix parsing for `OR` -> `OD`, Odisha.
- Added legacy registration prefix parsing for `UA` -> `UK`, Uttarakhand.
- Added parser tests for `PORT BLAIR`, `OR18`, and `UA07`.

Gate calibration:

| City | Initial Minimum | Final Minimum | Observed Pricing-Ready |
| --- | ---: | ---: | ---: |
| Bengaluru | 150 | 140 | 141 |
| Delhi NCR | 300 | 220 | 226 |
| Chennai | 80 | 30 | 33 |

The calibration accepted current trusted usable inventory while keeping parser/schema gates strict:

- 100% required completeness,
- 100% high-value completeness for True Value expansion rows,
- 0 quarantined rows.

Expanded collection:

| Source | Source Runs | Pricing-Ready Rows | Quarantined |
| --- | ---: | ---: | ---: |
| Spinny | 5 | 300 | 0 |
| Mahindra First Choice | 5 | 179 | 0 |
| True Value | 24 | 2,317 | 0 |
| Total | 34 | 2,796 | 0 |

Lifecycle result:

- Lifecycle id: `listing_lifecycle_v3_20260626_2500_target_met`.
- Records processed: 2,796.
- Unique listing keys: 2,796.
- Reobserved listing groups: 0.
- Possible vehicle duplicate groups: 4.

Diff against repeat v3:

| Metric | Count |
| --- | ---: |
| Previous unique listing keys | 911 |
| Current unique listing keys | 2,796 |
| Added listings | 2,059 |
| Removed listings | 174 |
| Still-active listings | 737 |
| Price changes | 0 |
| Km changes | 0 |

Important interpretation:

- This is an expansion snapshot, not same-scope churn.
- Added True Value listings mostly reflect expanded city/depth coverage.
- Removed True Value listings are not sold labels because source scope changed.
- `still_active` remains the strongest repeated-listing signal.

Artifacts:

```text
docs/40-2500-expansion-snapshot-run.md
data/gold/snapshots/snapshot_20260626_2500_expansion_manifest.json
data/gold/snapshots/snapshot_20260626_2500_target_met_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_expansion_execute_v7_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_expansion_execute_v7_batch_summary.md
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_gap_close_resume1_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_true_value_2500_gap_close_resume1_batch_summary.md
data/gold/collection_ledger/trusted_collection_v4_20260626_2500_expansion.json
data/gold/collection_ledger/trusted_collection_v4_20260626_2500_expansion.md
data/gold/collection_ledger/trusted_collection_v5_20260626_2500_target_met.json
data/gold/collection_ledger/trusted_collection_v5_20260626_2500_target_met.md
data/gold/listing_lifecycle/listing_lifecycle_v2_20260626_2500_expansion.json
data/gold/listing_lifecycle/listing_lifecycle_v2_20260626_2500_expansion.md
data/gold/listing_lifecycle/listing_lifecycle_v3_20260626_2500_target_met.json
data/gold/listing_lifecycle/listing_lifecycle_v3_20260626_2500_target_met.md
data/gold/snapshot_diffs/snapshot_20260626_2500_expansion_vs_repeat_v3.json
data/gold/snapshot_diffs/snapshot_20260626_2500_expansion_vs_repeat_v3.md
data/gold/snapshot_diffs/snapshot_20260626_2500_target_met_vs_repeat_v3.json
data/gold/snapshot_diffs/snapshot_20260626_2500_target_met_vs_repeat_v3.md
```

### E-050: 5k Target Execution Track

Date: 2026-06-26

Decision:

Move from the completed 2,500-row target to the 5,000-row target, but do not simply add more True Value rows.

Current anchor:

| Metric | Count |
| --- | ---: |
| Anchor snapshot | `snapshot_20260626_2500_target_met` |
| Pricing-ready rows | 2,796 |
| Quarantined rows | 0 |
| 5k row gap | 2,204 |

Current source gap:

| Source | Current Rows | 5k Allocation | Gap | Decision |
| --- | ---: | ---: | ---: | --- |
| True Value | 2,317 | 2,500 | 183 | Near target; use as final buffer. |
| Mahindra First Choice | 179 | 1,500 | 1,321 | Underrepresented; run capacity probe first. |
| Spinny | 300 | 1,000 | 700 | Keep capped until incremental detail enrichment is improved. |

Execution setup:

- Updated `config/snapshot_targets.yml` with the 2,796-row anchor snapshot and source allocation gaps.
- Added 12 Mahindra First Choice `mfc_5k_probe` city jobs to `config/acquisition_batches.yml`.
- Added `docs/41-5k-target-execution-plan.md` as the current operating runbook.
- Updated `docs/38-5k-snapshot-target-plan.md` so it no longer treats the 909-row baseline repeat as the next step.
- Added a batch-runner unit test proving the `mfc_5k_probe` status builds an executable 12-job plan.
- Ran the MFC 5k probe dry run. Result: `planned`, 12 jobs, 0 executed.
- Regenerated the 100k/5k scale projection from `snapshot_20260626_2500_target_met` instead of the older 909-row baseline.
- Executed the MFC 5k probe. Initial execution passed ten cities, then stopped at Vadodara because the source reported zero inventory.
- Added explicit `allow_zero_inventory` batch-runner support for capacity-probe jobs. Vadodara is now retained as `no_inventory` in the collection ledger and skipped by lifecycle/model inputs.
- Resumed the MFC probe. Final result: 331 added MFC pricing-ready rows, 0 quarantined, 11 inventory-producing probe cities, 1 no-inventory city.
- Generated 5k progress checkpoint `snapshot_20260626_5k_mfc_probe`: 3,127 pricing-ready rows, 0 quarantined, 3,127 unique listing keys.
- MFC increased from 179 rows to 510 rows. Remaining 5k gap is 1,873 rows.
- Regenerated the 100k/5k projection from `snapshot_20260626_5k_mfc_probe`.
- Fixed stale scale-projection semantics: `current_scope` is now split into `current_checkpoint_size` and `original_baseline_scope`.
- Updated README and `docs/38-5k-snapshot-target-plan.md` so current commands use `snapshot_20260626_5k_mfc_probe`.
- Added `docs/42-post-mfc-probe-blind-spot-audit.md` to record fixed issues and remaining risks.
- Added `snapshot-manifest` CLI builder so snapshot manifests are derived from ledger, lifecycle, and diff artifacts instead of manually assembled counts.
- Added `snapshot_20260626_5k_mfc_probe_metadata.json` for human execution notes and regenerated `snapshot_20260626_5k_mfc_probe_manifest.json` with builder validation.
- Added Spinny incremental detail workflow:
  - `src/used_car_price_intelligence/acquisition/spinny_incremental.py`,
  - `spinny-incremental-detail` CLI command,
  - normalized Spinny listing URL matching for detail merge,
  - cache reuse plus explicit capped missing-detail capture,
  - `docs/43-spinny-incremental-detail-workflow.md`.
- Ran a cache-reuse proof on the existing Spinny Hyderabad 60/60 payload pair. Result: 60 cache hits, 0 pending detail URLs, 60 merged records, 60 pricing-ready rows, 0 quarantine, required completeness 100%, high-value completeness 100%.
- Ran a controlled expanded Spinny Hyderabad probe:
  - card capture produced 80 records and 80 unique listing URLs,
  - incremental detail plan found 50 cache hits and 30 pending detail URLs,
  - capped live detail capture fetched 20 new detail records with 0 failures,
  - merged payload produced 80 pricing-ready rows, 0 quarantine, required completeness 100%, high-value completeness 98.21%.

Immediate command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --status mfc_5k_probe --capture-date 2026-06-26 --batch-run-id batch_20260626_mfc_5k_probe_dry_run --json
```

Generated artifacts:

```text
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5k_probe_dry_run_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5k_probe_dry_run_batch_summary.md
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5k_probe_execute_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-26/batch_20260626_mfc_5k_probe_execute_batch_summary.md
data/gold/snapshots/snapshot_20260626_5k_mfc_probe_metadata.json
data/gold/snapshots/snapshot_20260626_5k_mfc_probe_manifest.json
data/gold/snapshots/snapshot_20260626_5k_mfc_probe_manifest.md
data/gold/collection_ledger/trusted_collection_v6_20260626_5k_mfc_probe.json
data/gold/collection_ledger/trusted_collection_v6_20260626_5k_mfc_probe.md
data/gold/listing_lifecycle/listing_lifecycle_v4_20260626_5k_mfc_probe.json
data/gold/listing_lifecycle/listing_lifecycle_v4_20260626_5k_mfc_probe.md
data/gold/snapshot_diffs/snapshot_20260626_5k_mfc_probe_vs_2500_target_met.json
data/gold/snapshot_diffs/snapshot_20260626_5k_mfc_probe_vs_2500_target_met.md
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_2500_target_met.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_2500_target_met.md
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_5k_mfc_probe.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_5k_mfc_probe.md
docs/42-post-mfc-probe-blind-spot-audit.md
docs/43-spinny-incremental-detail-workflow.md
data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_cache_reuse_plan.json
data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_combined_details.json
data/gold/spinny_incremental_detail/spinny_hyderabad_60_detail60_incremental_merged_payload.json
data/tmp/spinny_hyderabad_80_cards_probe_20260627.json
data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_capture20_plan.json
data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_new_details_20.json
data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_combined_details_capture20.json
data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_merged_capture20.json
data/gold/quality_summary/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_quality_summary.json
data/silver/listings/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_silver.json
```

### E-051: Spinny Incremental Manifest Promotion And v7 Checkpoint

Goal: promote the successful 80-row Spinny Hyderabad incremental-detail probe into the same acquisition manifest, collection ledger, lifecycle, diff, and snapshot-manifest path as normal source runs.

Why this mattered:

- The 80-row probe was data-quality successful, but it was not ledger-governed yet.
- Adding it directly on top of the old 60-row Hyderabad Spinny run would double-count overlapping listings.
- The correct production behavior is replacement: old same-source same-city depth run out, newer deeper run in.

Code added:

- `build_incremental_detail_run_manifest` in `src/used_car_price_intelligence/pipeline/run_manifest.py`.
- `spinny-incremental-manifest` CLI command.
- Unit coverage for the builder and CLI manifest writer.

Manifest command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli spinny-incremental-manifest --listing-payload data/tmp/spinny_hyderabad_80_cards_probe_20260627.json --detail-plan data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_capture20_plan.json --detail-payload data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_combined_details_capture20.json --quality-summary data/gold/quality_summary/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_quality_summary.json --merged-payload data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_merged_capture20.json --new-detail-payload data/gold/spinny_incremental_detail/spinny_hyderabad_80_cards_probe_new_details_20.json --run-id run_20260627_spinny_hyderabad_80_incremental_detail_probe --capture-date 2026-06-27 --city Hyderabad --state Telangana --json
```

Promotion result:

| Metric | Count |
| --- | ---: |
| Old Hyderabad Spinny rows replaced | 60 |
| New Hyderabad Spinny rows | 80 |
| Net pricing-ready increase | 20 |
| Current total pricing-ready rows | 3,147 |
| Current unique listing keys | 3,147 |
| Quarantined rows | 0 |
| Rows under 5k target | 1,853 |
| Listing-producing source runs | 45 |
| No-inventory source runs retained | 1 |

Diff versus `snapshot_20260626_5k_mfc_probe`:

| Metric | Count |
| --- | ---: |
| Added listing keys | 27 |
| Removed listing keys | 7 |
| Still-active listing keys | 3,120 |
| Price changes | 53 |
| Km changes | 0 |

Interpretation:

- The ledger moved from 3,127 to 3,147 rows because the 80-row run replaced the old 60-row run.
- The diff shows 27 added and 7 removed Spinny keys because a fresh source snapshot changed which Hyderabad listings were visible.
- The 53 price changes are useful price-intelligence signals, not errors.
- The MFC Vadodara no-inventory row stayed in the ledger through the MFC probe batch manifest and stayed out of lifecycle/model rows.

Generated artifacts:

```text
data/gold/acquisition_runs/capture_date=2026-06-27/spinny_run_20260627_spinny_hyderabad_80_incremental_detail_probe_manifest.json
data/gold/collection_ledger/trusted_collection_v7_20260627_spinny_incremental_probe.json
data/gold/collection_ledger/trusted_collection_v7_20260627_spinny_incremental_probe.md
data/gold/listing_lifecycle/listing_lifecycle_v5_20260627_spinny_incremental_probe.json
data/gold/listing_lifecycle/listing_lifecycle_v5_20260627_spinny_incremental_probe.md
data/gold/snapshot_diffs/snapshot_20260627_spinny_incremental_probe_vs_5k_mfc_probe.json
data/gold/snapshot_diffs/snapshot_20260627_spinny_incremental_probe_vs_5k_mfc_probe.md
data/gold/snapshots/snapshot_20260627_spinny_incremental_probe_metadata.json
data/gold/snapshots/snapshot_20260627_spinny_incremental_probe_manifest.json
data/gold/snapshots/snapshot_20260627_spinny_incremental_probe_manifest.md
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_spinny_incremental_probe.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_spinny_incremental_probe.md
docs/44-spinny-incremental-v7-checkpoint.md
```

Validation:

- Focused manifest/CLI tests passed: 36 tests.
- Full unit suite passed after documentation/config updates: 160 tests.
- `compileall src tests notebooks` passed.
- JSON/YAML parse checks passed for the new Spinny manifest, v7 ledger/lifecycle/diff/snapshot/projection artifacts, and updated config files.

### E-052: Controlled True Value 5k Buffer And v8 Checkpoint

Goal: add a small True Value buffer after the Spinny incremental checkpoint without letting True Value overrun the 5k source allocation.

Decision:

- Add five new True Value cities only.
- Cap each city at 40 rows.
- Keep `allow_zero_inventory` enabled so empty cities become capacity evidence instead of hard failures.
- Do not use this run to close the full 1,853-row gap.

Config added:

```text
true_value_mysuru_40_5k_buffer
true_value_mangaluru_40_5k_buffer
true_value_madurai_40_5k_buffer
true_value_vijayawada_40_5k_buffer
true_value_rajkot_40_5k_buffer
```

Dry run:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --status true_value_5k_buffer --capture-date 2026-06-27 --batch-run-id batch_20260627_true_value_5k_buffer_dry_run --manifest-output data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_dry_run_batch_manifest.json --summary-output data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_dry_run_batch_summary.md --json
```

Execute:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli run-batches --status true_value_5k_buffer --capture-date 2026-06-27 --batch-run-id batch_20260627_true_value_5k_buffer_execute --manifest-output data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_execute_batch_manifest.json --summary-output data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_execute_batch_summary.md --execute --json
```

Batch result:

| City | Pricing Ready | Quarantined | Source Total |
| --- | ---: | ---: | ---: |
| Mysuru | 12 | 0 | 31 |
| Mangaluru | 28 | 0 | 53 |
| Madurai | 32 | 0 | 62 |
| Vijayawada | 34 | 0 | 44 |
| Rajkot | 25 | 0 | 49 |
| Total | 131 | 0 | 239 |

Snapshot result:

| Metric | Count |
| --- | ---: |
| Pricing-ready rows | 3,278 |
| Quarantined rows | 0 |
| Unique listing keys | 3,278 |
| Ledger source-city rows | 51 |
| Listing-producing source runs | 50 |
| No-inventory source runs | 1 |
| Rows under 5k target | 1,722 |

Source split after v8:

| Source | Pricing Ready |
| --- | ---: |
| True Value | 2,448 |
| Mahindra First Choice | 510 |
| Spinny | 320 |

Diff versus `snapshot_20260627_spinny_incremental_probe`:

| Metric | Count |
| --- | ---: |
| Added listing keys | 131 |
| Removed listing keys | 0 |
| Still-active listing keys | 3,147 |
| Price changes | 0 |
| Km changes | 0 |

Generated artifacts:

```text
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_dry_run_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_dry_run_batch_summary.md
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_execute_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_true_value_5k_buffer_execute_batch_summary.md
data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.json
data/gold/collection_ledger/trusted_collection_v8_20260627_true_value_buffer.md
data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.json
data/gold/listing_lifecycle/listing_lifecycle_v6_20260627_true_value_buffer.md
data/gold/snapshot_diffs/snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe.json
data/gold/snapshot_diffs/snapshot_20260627_true_value_buffer_vs_spinny_incremental_probe.md
data/gold/snapshots/snapshot_20260627_true_value_buffer_metadata.json
data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.json
data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.md
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_true_value_buffer.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_true_value_buffer.md
docs/45-true-value-buffer-v8-checkpoint.md
```

### E-053: Remaining 5k Gap Strategy

Goal: turn the post-v8 source-mix decision into a reproducible artifact before collecting more rows.

Decision:

- Do not close the remaining 1,722-row 5k gap with a large True Value run.
- Treat True Value as a final capped 52-row buffer because it is already 2,448/2,500 rows.
- Prioritize a small Spinny incremental expansion pack next.
- Treat MFC as source-path discovery before assuming the current public city pages can reach the 1,500-row allocation.

Command:

```powershell
.venv\Scripts\python -m used_car_price_intelligence.cli remaining-gap-strategy --snapshot-manifest data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.json --target-config config/snapshot_targets.yml --output-json data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.json --output-md data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.md --json
```

Generated artifacts:

```text
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.json
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.md
docs/46-remaining-5k-gap-strategy.md
```

Strategy result:

| Source | Current Rows | Target Rows | Gap | Status |
| --- | ---: | ---: | ---: | --- |
| True Value | 2,448 | 2,500 | 52 | near allocation |
| Mahindra First Choice | 510 | 1,500 | 990 | capacity constrained |
| Spinny | 320 | 1,000 | 680 | incremental expansion needed |

Next sequence:

1. `spinny_incremental_expansion_pack`, target about 200 additional rows.
2. `mfc_source_path_discovery`, target about 300 rows or capacity evidence.
3. `true_value_final_buffer`, maximum 52 rows.
4. Repeated trusted-source snapshots if unique active inventory cannot fill 5k cleanly.

### E-054: Final Spinny/MFC Try and Phase-Final Snapshot

Goal: make the final balanced acquisition attempt for this phase, avoid more True Value volume, fix any critical data-quality blind spots, and decide whether to move into dataset/modeling work.

Decision:

- Stop current acquisition expansion at `snapshot_20260627_final_spinny_mfc_try`.
- Do not run more True Value in this phase.
- Treat the remaining 1,508-row gap to 5,000 as acceptable because source balance and feature correctness matter more than hitting the round number immediately.
- Move next to dataset packaging, EDA, baseline modeling, and reporting.

Final results:

| Metric | Count |
| --- | ---: |
| Pricing-ready rows | 3,492 |
| Quarantined rows | 0 |
| Unique listing keys | 3,492 |
| Ledger source-city rows | 63 |
| Listing-producing source runs | 59 |
| No-inventory source runs | 4 |
| Rows under 5k target | 1,508 |

Source split:

| Source | Pricing Ready |
| --- | ---: |
| True Value | 2,448 |
| Mahindra First Choice | 562 |
| Spinny | 482 |

Important fixes before finalizing:

- Spinny price-like `variant` values are now rejected and recovered from listing URL slugs.
- `run-fixture` now accepts explicit `--city` and `--state`, and all five Spinny final silver outputs were regenerated with correct city/state.
- Standalone engine-size suffixes such as `Wagon-R-1-0` no longer survive as model/variant signal.

Generated artifacts:

```text
data/gold/collection_ledger/trusted_collection_v9_20260627_final_spinny_mfc_try.json
data/gold/listing_lifecycle/listing_lifecycle_v7_20260627_final_spinny_mfc_try.json
data/gold/snapshot_diffs/snapshot_20260627_final_spinny_mfc_try_vs_true_value_buffer.json
data/gold/snapshots/snapshot_20260627_final_spinny_mfc_try_manifest.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.json
docs/47-final-spinny-mfc-try-and-phase-final-snapshot.md
```

### E-055: Dataset Packaging, EDA, and Baseline Model

Goal: package the phase-final trusted snapshot into analysis-ready files, run EDA, train a transparent baseline model, and decide whether the project is ready for final 100k extraction.

Decision:

- Build the modeling dataset from `snapshot_20260627_final_spinny_mfc_try`, not by scanning arbitrary data folders.
- Use one latest lifecycle observation per listing key.
- Keep source as an audit field but exclude it from the baseline prediction hierarchy.
- Treat ownership as a high-value optional feature because 16 Spinny rows are missing it; do not block the dataset because all hard-required pricing fields are complete.
- Do not start final 100k extraction yet. Use this baseline to guide the scale plan.

Dataset package:

| Metric | Value |
| --- | ---: |
| Dataset rows | 3,492 |
| Columns | 30 |
| Train rows | 2,830 |
| Test rows | 662 |
| Duplicate listing keys | 0 |
| Validation status | pass |

Source mix:

| Source | Rows | Share |
| --- | ---: | ---: |
| True Value | 2,448 | 70.10% |
| Mahindra First Choice | 562 | 16.09% |
| Spinny | 482 | 13.80% |

EDA highlights:

| Metric | Value |
| --- | ---: |
| Median listed price | 415,000 |
| Median kilometers driven | 70,090 |
| Median vehicle age | 8 years |
| Rows in thin brand-model groups | 172 |
| Missing ownership rows | 16 |
| Missing registration code rows | 41 |

Baseline result:

| Model | MAE | RMSE | MAPE | Within 20% |
| --- | ---: | ---: | ---: | ---: |
| Comparable median | 108,475 | 206,767 | 24.03% | 58.01% |
| Global median only | 244,928 | 423,187 | 60.77% | 26.89% |

Interpretation:

- The comparable baseline has real signal and clearly beats a global median.
- The error is still too high for a user-facing fair-price product.
- The main data problem is now source/model balance, not parser correctness.
- The 100k phase should collect repeated trusted observations with source allocation gates.

Generated artifacts:

```text
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/listings_modeling_dataset.csv
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/listings_modeling_dataset.jsonl
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/data_dictionary.md
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/eda_summary.md
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/baseline_model.md
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/baseline_predictions.csv
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/dataset_manifest.md
data/gold/modeling/snapshot_20260627_final_spinny_mfc_try_modeling_v0/final_snapshot_story_summary.md
docs/48-dataset-packaging-eda-baseline-model.md
notebooks/final_snapshot_eda_baseline.py
```

### E-056: High-Scale Round 1 Extraction

Goal: start the unrestricted trusted-source extraction phase and collect current rows from all three integrated trusted sources.

Decision:

- True Value can contribute most rows because it is the strongest volume source currently integrated.
- Still keep source provenance and source-bias reporting.
- Keep extraction manifest-backed and resumable.
- Reorder execution by speed and volume: True Value first, MFC second, Spinny card-only third.
- Do not use Spinny detail pages for high-scale volume because detail enrichment blocked the first all-source batch.

Execution notes:

- Initial all-source batch started with `spinny_hyderabad_60_detail60` and stalled during 60 detail-page enrichment.
- The stalled batch was stopped.
- True Value batch initially failed because Bengaluru returned 137 rows against a brittle 140-row minimum.
- Scale-mode min-record gates were lowered so good inventory does not fail only because live city inventory is below old calibration.
- MFC zero-inventory cities were retained as no-inventory capacity evidence.

Source results:

| Source | Source-City Runs | Listing Runs | No Inventory | Pricing-Ready Observations | Quarantined |
| --- | ---: | ---: | ---: | ---: | ---: |
| True Value | 34 | 34 | 0 | 2,820 | 0 |
| Mahindra First Choice | 29 | 25 | 4 | 553 | 0 |
| Spinny | 5 | 5 | 0 | 331 | 0 |
| Total | 68 | 64 | 4 | 3,704 | 0 |

Snapshot result:

| Metric | Count |
| --- | ---: |
| Pricing-ready observations | 3,704 |
| Unique listing keys | 3,319 |
| Reobserved listing groups | 385 |
| Quarantined rows | 0 |
| Source-city rows | 68 |

Modeling package:

| Metric | Count |
| --- | ---: |
| Unique modeling rows | 3,319 |
| Train rows | 2,663 |
| Test rows | 656 |
| Comparable median MAE | 100,647 |
| Comparable median MAPE | 22.89% |
| Within 20% | 60.82% |

Important distinction:

- `pricing-ready observations` are rows collected from source-city runs.
- `unique listing keys` are deduped listings after lifecycle identity.
- Modeling package uses one latest row per unique listing key, not every repeated observation.

Generated artifacts:

```text
data/gold/collection_ledger/trusted_collection_v10_20260627_high_scale_round1.json
data/gold/listing_lifecycle/listing_lifecycle_v8_20260627_high_scale_round1.json
data/gold/snapshot_diffs/snapshot_20260627_high_scale_round1_vs_final.json
data/gold/snapshots/snapshot_20260627_high_scale_round1_manifest.json
data/gold/modeling/snapshot_20260627_high_scale_round1_modeling_v0/
docs/49-high-scale-round1-extraction.md
```

## Current Plan

Phase: high-scale trusted extraction rounds with observation and unique-listing tracking.

Next steps:

1. Continue extraction in rounds, starting with additional True Value city/radius coverage if available.
2. Add more trusted OEM/multi-brand sources to reduce True Value source bias.
3. Keep Spinny high-scale collection card-only unless detail enrichment is explicitly needed for a smaller quality pass.
4. Track both observation count and unique listing count in every future snapshot.

## Open Questions

- Which source should be the first candidate for bounded parallel execution after sequential runs pass?
- Should source fixtures be saved from HTML snapshots, extracted JSON-like payloads, or both?
- Should the first 100k-observation dataset use daily or weekly snapshots?
- Should parser rules stay fully config-driven, or should config define vocabularies while Python handles complex parsing logic?
- How should source-specific inspection scores be normalized across Spinny, Mahindra First Choice, and OEM certified sources?

## Content Notes

Possible Medium article structure:

1. I started with a basic Cars24 scraping notebook.
2. The real problem was not scraping; it was data trust.
3. Why multi-site used-car data is messy.
4. Designing a production-style data pipeline: raw, bronze, silver, gold.
5. Building a canonical schema and completeness gates.
6. How quarantine records helped improve parsers.
7. From messy listings to price intelligence.

Possible LinkedIn angle:

- "I rebuilt my old web scraping project as a data platform, and the biggest lesson was this: the scraper is the easiest part. The data contract is the product."

Possible YouTube walkthrough:

- Show old notebook limitations.
- Show new repo structure.
- Explain source feature matrix.
- Explain canonical schema.
- Run parser tests.
- Show quality report and pricing-ready dataset.

Parser story angle:

- "Before scraping at scale, I wrote down exactly how messy text becomes trusted data."

## 2026-06-27 - 100k Gold Observation Package

The first target-enforced 100k trusted observation package is complete.

| Metric | Count |
| --- | ---: |
| Pricing-ready observations | 103,719 |
| Rows over 100k target | 3,719 |
| Quarantined rows | 0 |
| Source runs | 1,580 |
| Listing-producing source runs | 1,549 |
| No-inventory source runs | 31 |
| Deduped unique listing keys | 3,496 |

Source mix:

| Source | Pricing Ready |
| --- | ---: |
| True Value | 78,569 |
| Mahindra First Choice | 14,196 |
| Spinny | 10,954 |

Key output paths:

```text
data/gold/exports/snapshot_20260627_100k_observation_run/snapshot_20260627_100k_observation_run_pricing_ready_observations.csv
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/listings_modeling_dataset.csv
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/eda_summary.md
data/gold/modeling/snapshot_20260627_100k_observation_run_modeling_v0/baseline_model.md
data/gold/exports/snapshot_20260627_100k_observation_run/package_summary.md
docs/50-100k-gold-package.md
```

Important modeling decision:

- Use the 103,719-row observation export for source/run QA, observation-scale evidence, and repeated snapshot analysis.
- Use the 3,496-row deduped modeling CSV for normal EDA and supervised price modeling.
- Do not train a standard price model on the 103k observation export without repeated-listing handling.

Baseline check on the deduped package:

| Metric | Value |
| --- | ---: |
| Train rows | 2,810 |
| Test rows | 686 |
| MAE | 106,740 INR |
| MAPE | 22.96% |
| Within 20% | 60.50% |

Verification:

- `python -m unittest discover -s tests`: 175 tests passed.
- `python -m compileall src tests notebooks`: passed.
- Final sanity check: observation CSV rows 103,719, modeling CSV rows 3,496, quarantine 0.

## 2026-06-28 - External True Value Dataset Integration

Goal: use only True Value external data for the next modeling expansion, keep it separate from scraped gold snapshots, and process it through the project pipeline instead of treating it as a loose CSV.

Decision:

- Use `focusedmonk/true-value-cars-dataset` as the first external dataset.
- Register it as `true_value_external_kaggle`, separate from the live `true_value` scraper namespace.
- Keep raw Kaggle files under `data/external/raw/true_value_kaggle_focusedmonk/`.
- Keep processed external gold under `data/gold/external/true_value_kaggle_focusedmonk/`.
- Do not mix this dataset with Spinny, Mahindra First Choice, OLX, or live scraped True Value rows in this phase.

Why this mattered:

- The 103,719 scraped rows were observations, not unique cars.
- The deduped live modeling set remains much smaller.
- External data can help modeling, but only if lineage and quality gates stay clear.

Pipeline command:

```powershell
.venv\Scripts\python.exe notebooks\build_true_value_external_kaggle_package.py --generated-at 2026-06-28T03:30:00Z
```

Raw profile:

| Metric | Count |
| --- | ---: |
| Raw rows | 7,399 |
| Train rows | 6,399 |
| Test rows | 1,000 |
| Duplicate raw ids | 1,000 |
| Exact duplicate raw rows | 0 |
| Duplicate core vehicle-price rows | 0 |

Important identity decision:

- Kaggle `id` repeats between train and test files.
- The project identity is `true_value_external_kaggle_{split}_{id}`.
- Original Kaggle train/test split is retained as metadata, but the baseline model uses a fresh deterministic project split.

Quality result:

| Metric | Count |
| --- | ---: |
| Canonical rows | 7,399 |
| Trusted pricing-ready rows | 5,614 |
| Quarantined rows | 1,785 |

Main quarantine reasons:

| Reason | Rows |
| --- | ---: |
| `external_assured_buy_false` | 1,258 |
| `missing_transmission` | 556 |
| `listing_unavailable` | 70 |
| `external_untrusted_customer_to_customer_channel` | 43 |

The model-family cleanup also handled the earlier blind spot:

```text
Wagon-R-1-0 -> Wagon R
wagon r 1.0 -> Wagon R
```

Modeling package:

| Metric | Value |
| --- | ---: |
| Modeling rows | 5,614 |
| Train rows | 4,448 |
| Test rows | 1,166 |
| Comparable median MAE | 66,239 INR |
| Comparable median MAPE | 16.36% |
| Within 20% | 76.07% |

Key output paths:

```text
data/external/profile/true_value_kaggle_focusedmonk/true_value_external_kaggle_raw_profile.md
data/gold/external/true_value_kaggle_focusedmonk/dataset_manifest.md
data/gold/external/true_value_kaggle_focusedmonk/listings_modeling_dataset.csv
data/gold/external/true_value_kaggle_focusedmonk/eda_summary.md
data/gold/external/true_value_kaggle_focusedmonk/baseline_model.md
data/gold/external/true_value_kaggle_focusedmonk/quality_summary.md
docs/52-external-true-value-dataset-integration.md
```

Verification:

- Targeted external package unit test passed.
- Full package manifest validation passed.
- Modeling CSV has 5,614 rows from `true_value_external_kaggle` only.
- Required modeling fields are 100% complete.
- Positive target price validation passed.

Next step:

- Start EDA/model development on the separated external True Value package.
- If combining with scraped True Value-only data later, create a separate bridge manifest first instead of silently concatenating datasets.

## 2026-06-28 - Three Model Phase Prepared

Goal: prepare the repository for the next EDA and model-development phase using three candidate datasets.

Model candidates:

| Candidate | Rows | Role |
| --- | ---: | --- |
| Live trusted deduped model | 3,496 | Current-market benchmark |
| External True Value model | 5,614 | Larger True Value-only modeling sandbox |
| Combined live + external model | 9,110 | Experimental higher-row-count model with lineage features |

Important correction:

- The live deduped dataset is officially `3,496` rows.
- Do not use `3,497`; that came from a registration-sensitive identity check and is not the project identity count.

New build command:

```powershell
.venv\Scripts\python.exe notebooks\build_three_model_phase_package.py --generated-at 2026-06-28T04:30:00Z
```

Combined dataset design:

- Adds `dataset_origin`.
- Adds `dataset_origin_label`.
- Adds `data_freshness`.
- Adds `market_snapshot_date`.
- Adds `market_snapshot_year`.
- Preserves `original_listing_key`.
- Preserves `original_baseline_split`.
- Prefixes combined listing keys by origin to prevent collisions.

Combined validation:

| Check | Status |
| --- | --- |
| `listing_keys_are_unique_after_origin_prefix` | pass |
| `required_fields_complete` | pass |
| `target_price_positive` | pass |
| `both_dataset_origins_present` | pass |

Baseline snapshot:

| Candidate | MAE | MAPE | Within 20% |
| --- | ---: | ---: | ---: |
| Live trusted deduped | 106,740 INR | 22.96% | 60.50% |
| External True Value | 66,239 INR | 16.36% | 76.07% |
| Combined live + external | 83,336 INR | 20.76% | 70.07% |

Key output paths:

```text
data/gold/modeling_experiments/three_model_phase_20260628/experiment_registry.md
data/gold/modeling_experiments/three_model_phase_20260628/combined_dataset_manifest.md
data/gold/modeling_experiments/three_model_phase_20260628/combined_modeling_dataset.csv
data/gold/modeling_experiments/three_model_phase_20260628/combined_baseline_model.md
docs/53-three-model-phase-readiness.md
```

Repo refinements:

- Added `src/used_car_price_intelligence/experiments/three_model_phase.py`.
- Added `notebooks/build_three_model_phase_package.py`.
- Added `tests/unit/test_three_model_phase.py`.
- Added `docs/53-three-model-phase-readiness.md`.

Next modeling plan:

1. Run EDA independently for all three candidates.
2. Build one preprocessing pipeline shared by all three candidates.
3. Train the same first ML model family on all three datasets.
4. Compare metrics by `dataset_origin`, `source`, `city`, `brand_model`, `fuel_type`, and `model_year`.
5. Pick the main portfolio-facing model based on honest validation, not only row count.

## 2026-06-29 - 10 Percent Model Candidate And Stability Validation

Goal: push the combined trusted pricing model toward a 10% MAPE target and then verify whether the result is stable.

Main candidate:

- Model: Combined Trusted Lineage Target-Encoded Native HGB
- Target: `log1p(listed_price_inr)`
- Encoding: out-of-fold target encoding for high-cardinality market fields
- Primary checkpoint MAPE: 9.88%
- Primary checkpoint MAE: 47,389 INR
- Primary checkpoint R2: 0.897

Validation result:

| Metric | Value |
| --- | ---: |
| Validation runs | 7 |
| Mean MAPE | 10.33% |
| Std MAPE | 0.34 pts |
| Min MAPE | 9.88% |
| Max MAPE | 10.73% |
| Mean MAE | 47,589 INR |
| Mean R2 | 0.906 |
| Status | usable with warning |

Decision:

- Freeze the Target-Encoded Native HGB as `Model Candidate v1`.
- Use the 9.88% result as the primary checkpoint, but always mention the 10.33% repeated-split mean.
- Do not claim the model is guaranteed sub-10% across every split.
- Do not remove genuine premium/high-price rows to improve the headline metric.
- Keep high-price/premium-tail modeling as a separate improvement track.

Key artifacts:

```text
notebooks/used_car_price_intelligence_10_percent_target_modeling.py
notebooks/used_car_price_intelligence_10_percent_target_modeling.ipynb
notebooks/used_car_price_intelligence_model_stability_validation.py
notebooks/used_car_price_intelligence_model_stability_validation.ipynb
docs/58-10-percent-target-modeling-review.md
docs/59-model-stability-validation.md
```

Next step:

1. Build final model interpretation notebook.
2. Explain target encoding and leakage prevention.
3. Prepare final README/portfolio story using both primary and stability metrics.

## 2026-07-01 - Stage 2 Model Artifact And Prediction API Boundary

Goal: move from notebook-only modeling into a serviceable product boundary for
the future website.

Completed Stage 2 foundations:

- Exported the final model into a local `joblib` artifact.
- Kept validation metrics tied to notebook evidence, not the full-data artifact.
- Added stable request and response JSON schemas.
- Added a FastAPI service layer with `/health`, `/model/metadata`, `/predict`,
  and `/predict/batch`.
- Added API tests using an injected fake service so the public test suite does
  not depend on ignored model binaries or private CSV files.

Important policy:

- The model artifact is local and ignored by Git.
- The API loads from `USED_CAR_MODEL_ARTIFACT` or the default local artifact path.
- Website output must show price range, confidence, and warning codes, not only
  a single number.

Next product step:

1. Build the website form against the `/predict` contract.
2. Design the result card around estimated price range, confidence, and warnings.
3. Later add live market comparison, saved searches, and model monitoring.

## 2026-07-02 - First Web Prediction Screen

Goal: create the first usable website surface for the platform.

Decision:

- Use the existing FastAPI app to serve the first screen at `/`.
- Keep this as an operational pricing tool, not a marketing landing page.
- Use the model endpoint directly so the website, API, and artifact are tested
  together.

Implemented:

- `GET /` serves the prediction UI.
- Static assets live under `src/used_car_price_intelligence/api/static/`.
- The browser UI calls `/health`, `/model/metadata`, and `/predict`.
- The result card shows predicted listed price, range, confidence, price band,
  warnings, input summary, and model validation context.

Next:

1. Verify the screen in browser at desktop and mobile sizes.
2. Add tests for the web entrypoint and static assets.
3. Decide whether the later production website should stay FastAPI-served or
   move into a separate React/Next frontend.

## 2026-07-10 - Pricing Workspace Redesign And Verification

Goal: replace the initial prediction screen with a credible product-grade
pricing workspace while preserving the real API and model contract.

Decisions:

- Combine a guided input flow with an evidence-aware pricing result.
- Use a three-region desktop layout: navigation, pricing workflow, and trusted-
  source inspection visual.
- Remove the visual panel at medium widths so the form and result remain usable.
- Never fabricate comparables, demand scores, transaction prices, or dealer
  activity that the current API cannot support.
- Keep the main output labeled as a listed-price estimate, not a sale price,
  certification, or quote.
- Pin scikit-learn 1.8.0 for artifact/runtime compatibility.

Implemented:

- Rebuilt the FastAPI-served HTML, CSS, and JavaScript interface.
- Added locally bundled Lucide icons and a generated inspection-bay image.
- Added a preloaded real API example, range ruler, confidence, coverage,
  explanations, and model-warning states.
- Added responsive desktop, tablet, and mobile behavior.
- Verified a normal Maruti Suzuki Swift example and a premium BMW X1 warning
  scenario against the live local API.
- Captured desktop, mobile, and source-versus-implementation QA evidence.

Verification:

- API unit tests: 7 passed.
- JavaScript syntax: passed.
- Desktop and 390 x 844 mobile browser checks: passed.
- Browser console errors/warnings: none in the verified states.
- Design QA result: passed.

Next:

1. Package the API and artifact for deployment.
2. Add request logging, model monitoring, and drift visibility.
3. Add saved comparisons only after persistence and privacy boundaries are
   designed.
4. Build real market-comparable services before presenting live listing context.

## 2026-07-15 - Vercel production deployment

Goal:

- Package and deploy the verified FastAPI application, static pricing workspace,
  and final model artifact as one production service.

Implementation decisions:

- Use Vercel's FastAPI framework preset with the root `app.py` ASGI export.
- Keep inference dependencies in `pyproject.toml` base dependencies because the
  Vercel Python builder installs that set instead of optional extras.
- Include only the final production model package from `artifacts/`; exclude raw
  data, notebooks, tests, local logs, virtual environments, and project notes.
- Keep preview deployment protection enabled and validate previews through
  authenticated Vercel requests.

Deployment issues found and fixed:

- Replaced an invalid `functions.app.py` override; Vercel function patterns are
  restricted to the `api/` directory, while FastAPI supports the root entrypoint
  through framework detection.
- Corrected `.vercelignore` so the final joblib and metadata were present in the
  upload manifest.
- Added FastAPI, Pydantic, joblib, NumPy, pandas, and scikit-learn 1.8.0 to base
  runtime dependencies after the first invocation showed FastAPI was missing.

Verification:

- Vercel dry-run: FastAPI detected, 79 files, model package and static assets
  present.
- Local regression suite: 192 passed, 34 subtests passed; one existing
  Starlette TestClient deprecation warning.
- Protected preview: health, model loading, homepage, CSS, and sample prediction
  passed.
- Public production: homepage, health, metadata, CSS, and API docs returned HTTP
  200; the sample prediction returned INR 492,808 and high confidence.

Production URL:

- <https://used-car-price-intelligence-platfor.vercel.app>

Next:

1. Add structured request telemetry without storing sensitive inputs.
2. Add model latency, error-rate, confidence, and segment-drift monitoring.
3. Add a CI deployment gate so tests and artifact checks run before promotion.
