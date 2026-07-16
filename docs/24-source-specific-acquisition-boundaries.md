# Source-Specific Acquisition Boundaries

Date: 2026-06-25

## Decision

Keep every source separate until the source adapter produces canonical records.

This is especially important for Mahindra First Choice because its website behavior is materially different from Spinny. It should not reuse Spinny's acquisition assumptions just because both are trusted used-car sources.

## Separate Per Source

Each trusted source should own its own:

- acquisition module,
- raw payload contract,
- browser interaction pattern,
- pagination strategy,
- retry and timeout policy,
- source adapter,
- live smoke command,
- source-specific quality notes,
- run manifest metadata.

Examples:

- Spinny: rendered listing cards, infinite scroll, optional detail-page enrichment.
- Mahindra First Choice: Next.js page state plus browser-triggered XHR pagination, no detail-page requirement for the first pricing-ready rows.
- True Value: dealer discovery by latitude/longitude plus GraphQL product search by dealer code, no detail-page requirement for the first pricing-ready rows.

## Shared After Canonicalization

After a source adapter emits canonical listing records, the project should use the shared pipeline:

- `CanonicalListing`,
- parser rules and parser helpers,
- validation and quarantine gates,
- raw/silver/gold storage layout,
- field profile reports,
- smoke reports,
- acquisition run manifests,
- gold pricing-ready dataset.

This gives us both flexibility and comparability. Source scrapers can adapt to each website, while downstream data remains one unified market dataset.

## Why This Matters

Source websites drift independently:

- pagination can change,
- embedded state can move,
- detail pages can become blocked or redesigned,
- source-specific fields may appear or disappear,
- certification and inspection signals mean different things by source.

If we force all websites into one scraper design, a change in one source can damage the whole acquisition pipeline. If we keep source boundaries clean, a source can fail, pause, or change without corrupting other sources.

## Rule For Future Sources

Before adding a new source to the core dataset:

1. Capture a small fixture or live smoke.
2. Define the source payload contract.
3. Build a source-specific adapter.
4. Measure required, high-value, optional, and overall completeness.
5. Keep source-specific scores in `extra_fields` until their meaning is proven comparable.
6. Merge only the canonical output into shared silver/gold layers.
