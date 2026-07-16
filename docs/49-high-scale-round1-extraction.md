# High-Scale Round 1 Extraction

Date: 2026-06-27

Purpose: start the unrestricted trusted-source extraction phase using the production batch runner, collect as many usable rows as practical from Spinny, Mahindra First Choice, and True Value, and package the result into a fresh snapshot.

## Decision

Proceed with high-scale extraction.

True Value can dominate the row count because it is the highest-volume trusted source currently integrated. This is acceptable for collection progress, but the dataset must still preserve source provenance and report source bias clearly.

The extraction should still be resumable and manifest-backed. The project should not use a single untracked scrape because failed jobs, no-inventory cities, and duplicate source listings are normal at this scale.

## Execution Order

The original all-source batch started with Spinny detail enrichment and became too slow. The high-scale execution was reordered:

1. True Value first for row volume.
2. Mahindra First Choice second for multi-brand balance.
3. Spinny card-only third to avoid slow detail-page bottlenecks.

Spinny card-only was accepted for this round because pricing-critical required fields were complete. Ownership is missing in card-only Spinny rows and is tracked as a high-value optional field.

## Source Results

| Source | Source-City Runs | Listing Runs | No Inventory | Pricing-Ready Observations | Quarantined |
| --- | ---: | ---: | ---: | ---: | ---: |
| True Value | 34 | 34 | 0 | 2,820 | 0 |
| Mahindra First Choice | 29 | 25 | 4 | 553 | 0 |
| Spinny | 5 | 5 | 0 | 331 | 0 |
| Total | 68 | 64 | 4 | 3,704 | 0 |

MFC no-inventory cities:

- Ludhiana
- Rajkot
- Vadodara
- Vijayawada

## Snapshot Result

Snapshot:

```text
snapshot_20260627_high_scale_round1
```

Collection:

```text
trusted_collection_v10_20260627_high_scale_round1
```

Lifecycle:

```text
listing_lifecycle_v8_20260627_high_scale_round1
```

Counts:

| Metric | Count |
| --- | ---: |
| Pricing-ready observations | 3,704 |
| Unique listing keys | 3,319 |
| Reobserved listing groups | 385 |
| Quarantined rows | 0 |
| Source-city rows | 68 |
| Listing-producing runs | 64 |
| No-inventory runs | 4 |

True Value produced 2,820 pricing-ready observations but 2,435 unique listing keys because overlapping True Value city/radius runs reobserved 385 listings.

## Diff Vs Previous Final Snapshot

Compared with `snapshot_20260627_final_spinny_mfc_try`:

| Metric | Count |
| --- | ---: |
| Previous unique listing keys | 3,492 |
| Current unique listing keys | 3,319 |
| Added listing keys | 261 |
| Removed listing keys | 434 |
| Still-active listing keys | 3,058 |
| Price changes | 2 |
| KM changes | 2 |

The lower unique listing count is not a data-quality failure. It reflects replacing older final-phase source runs with a clean current extraction scope and detecting repeated True Value listings across overlapping runs.

## Modeling Package

Packaged dataset:

```text
snapshot_20260627_high_scale_round1_modeling_v0
```

The modeling dataset uses one latest row per unique listing key:

| Metric | Count |
| --- | ---: |
| Unique modeling rows | 3,319 |
| Train rows | 2,663 |
| Test rows | 656 |
| Expected pricing-ready observations | 3,704 |
| Duplicate listing keys | 0 |

Source mix in the unique modeling dataset:

| Source | Rows | Share |
| --- | ---: | ---: |
| True Value | 2,435 | 73.37% |
| Mahindra First Choice | 553 | 16.66% |
| Spinny | 331 | 9.97% |

Baseline model:

| Model | MAE | RMSE | MAPE | Within 20% |
| --- | ---: | ---: | ---: | ---: |
| Comparable median | 100,647 | 175,096 | 22.89% | 60.82% |
| Global median only | 243,110 | 422,359 | 59.20% | 28.05% |

The comparable baseline improved versus the previous package, but it is still not a production valuation model.

## Data Quality Notes

- Required pricing fields are complete in the packaged modeling dataset.
- Quarantine count is 0 across the successful high-scale runs.
- Spinny card-only rows have missing ownership, so ownership completeness dropped to 90.03%.
- True Value source share rose to 73.37%, so model metrics remain biased toward Maruti Suzuki inventory.
- Overlapping True Value runs produced 385 reobserved listing groups. This is useful for observation-scale growth but must be deduped for unique-listing modeling.

## Generated Artifacts

```text
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_high_scale_true_value_resume1_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_high_scale_true_value_resume1_batch_summary.md
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_high_scale_mfc_execute_batch_manifest.json
data/gold/batch_runs/capture_date=2026-06-27/batch_20260627_high_scale_mfc_execute_batch_summary.md
data/gold/collection_ledger/trusted_collection_v10_20260627_high_scale_round1.json
data/gold/collection_ledger/trusted_collection_v10_20260627_high_scale_round1.md
data/gold/listing_lifecycle/listing_lifecycle_v8_20260627_high_scale_round1.json
data/gold/listing_lifecycle/listing_lifecycle_v8_20260627_high_scale_round1.md
data/gold/snapshot_diffs/snapshot_20260627_high_scale_round1_vs_final.json
data/gold/snapshot_diffs/snapshot_20260627_high_scale_round1_vs_final.md
data/gold/snapshots/snapshot_20260627_high_scale_round1_manifest.json
data/gold/snapshots/snapshot_20260627_high_scale_round1_manifest.md
data/gold/modeling/snapshot_20260627_high_scale_round1_modeling_v0/
```

## Next Step

Continue extraction, but do it in rounds:

1. Run another True Value round only if new city/radius combinations are added or if the same combinations are intentionally treated as repeated market observations.
2. Add more multi-brand/OEM trusted sources before relying on the model for broad market pricing.
3. Keep Spinny card-only for volume, and reserve detail enrichment for smaller quality-focused enrichments.
4. Track both observation count and unique listing count. For 100k-plus scale, observation count can grow through repeated snapshots, but modeling should use deduped latest listing rows unless the task is time-series price movement.
