# Spinny vs Mahindra First Choice Field Comparison

Generated at: 2026-06-25

## Decision

Both runs are approved as pricing-ready trusted-source inputs, but they should stay separate at the acquisition layer. They become comparable only after each source adapter emits canonical records.

The immediate modeling implication is simple: use both sources for gold pricing rows, but keep source provenance and source-specific evidence fields intact.

## Run Summary

| Metric | Spinny | Mahindra First Choice |
| --- | ---: | ---: |
| Records | 60 | 40 |
| Pricing-ready | 60 | 40 |
| Quarantined | 0 | 0 |
| Required completeness | 100.00% | 100.00% |
| High-value completeness | 100.00% | 91.78% |
| Optional completeness | 39.83% | 36.50% |
| Overall completeness | 93.98% | 92.01% |
| Runtime seconds | 258.92 | 17.369 |

## Acquisition Behavior

| Metric | Spinny | Mahindra First Choice |
| --- | --- | --- |
| Run ID | `run_20260625_spinny_hyderabad_manifest_60_detail60_smoke` | `run_20260625_mfc_hyderabad_40_smoke` |
| City | Hyderabad | Hyderabad |
| Source URL | <https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/> | <https://www.mahindrafirstchoice.com/used-cars/hyderabad> |
| Pagination type | infinite_scroll_batches | next_data_plus_xhr |
| Attempted pages | 3 | 2 |
| Unique cards seen | 60 | 88 |
| Returned records | 60 | 40 |
| Source total items | n/a | 88 |
| Detail requested | 60 | 0 |
| Detail successful | 60 | 0 |

## Field Coverage

| Group | Field | Spinny | Mahindra First Choice | Note |
| --- | --- | ---: | ---: | --- |
| required | `source` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `source_listing_id` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `listing_url` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `captured_at` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `city` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `brand` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `model` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `model_year` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `listed_price_inr` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `km_driven` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `fuel_type` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `transmission` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `currency` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `raw_record_hash` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `ingestion_run_id` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `parser_version` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| required | `schema_version` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| high_value | `variant` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| high_value | `ownership` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| high_value | `registration_code` | 60/60 (100.00%) | 17/40 (42.50%) | source-specific gap |
| high_value | `locality` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| high_value | `seller_type` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| high_value | `is_certified` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| high_value | `is_available` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| optional | `state` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| optional | `hub_name` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| optional | `manufacture_year` | 60/60 (100.00%) | 0/40 (0.00%) | source-specific gap |
| optional | `registration_year` | 60/60 (100.00%) | 0/40 (0.00%) | source-specific gap |
| optional | `registration_state` | 60/60 (100.00%) | 17/40 (42.50%) | source-specific gap |
| optional | `registration_type` | 60/60 (100.00%) | 17/40 (42.50%) | source-specific gap |
| optional | `body_type` | 0/60 (0.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `color` | 0/60 (0.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `seating_capacity` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `original_price_inr` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `discount_amount_inr` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `emi_amount_inr` | 60/60 (100.00%) | 22/40 (55.00%) | partial difference |
| optional | `token_amount_inr` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `price_label` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `deal_rating` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `extra_charges_flag` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `dealer_name` | 0/60 (0.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `inspection_status` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| optional | `inspection_score` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `condition_grade` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `accident_history` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `service_history_available` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `commercial_vehicle_flag` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `warranty_label` | 57/60 (95.00%) | 40/40 (100.00%) | partial difference |
| optional | `return_policy_label` | 60/60 (100.00%) | 0/40 (0.00%) | source-specific gap |
| optional | `finance_label` | 60/60 (100.00%) | 22/40 (55.00%) | partial difference |
| optional | `listing_posted_at` | 0/60 (0.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `source_record_type` | 60/60 (100.00%) | 40/40 (100.00%) | stable in both |
| optional | `first_seen_at` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |
| optional | `last_seen_at` | 0/60 (0.00%) | 0/40 (0.00%) | missing in both |

## Source-Specific Extra Fields

| Field | Spinny | Mahindra First Choice |
| --- | ---: | ---: |
| `mahindra_first_choice.emi_text` | n/a | 22/40 (55.00%) |
| `mahindra_first_choice.id_classified` | n/a | 40/40 (100.00%) |
| `mahindra_first_choice.mileage` | n/a | 40/40 (100.00%) |
| `mahindra_first_choice.photo_count` | n/a | 40/40 (100.00%) |
| `mahindra_first_choice.rating_score` | n/a | 40/40 (100.00%) |
| `mahindra_first_choice.source_city` | n/a | 40/40 (100.00%) |
| `mahindra_first_choice.source_price_value` | n/a | 40/40 (100.00%) |
| `mahindra_first_choice.source_state` | n/a | 40/40 (100.00%) |
| `mahindra_first_choice.stock_id` | n/a | 40/40 (100.00%) |
| `mahindra_first_choice.variant_details` | n/a | 40/40 (100.00%) |
| `spinny_detail.inspection_summary` | 59/60 (98.33%) | n/a |
| `spinny_detail.insurance_type` | 60/60 (100.00%) | n/a |
| `spinny_detail.insurance_validity` | 60/60 (100.00%) | n/a |
| `spinny_detail.quality_scores.core_systems.grade` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.core_systems.score` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.exteriors_lights.grade` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.exteriors_lights.score` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.interiors_ac.grade` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.interiors_ac.score` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.supporting_systems.grade` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.supporting_systems.score` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.wear_tear_parts.grade` | 59/60 (98.33%) | n/a |
| `spinny_detail.quality_scores.wear_tear_parts.score` | 59/60 (98.33%) | n/a |
| `spinny_detail.service_due_text` | 48/60 (80.00%) | n/a |

## Interpretation

- Required pricing fields are complete in both runs, so both sources can contribute to gold pricing rows.
- `ownership` is complete in both runs.
- `registration_code` is complete in spinny (60/60) but partial in mahindra_first_choice (17/40).
- `body_type` is complete in mahindra_first_choice (40/40) but missing in spinny (0/60).
- `dealer_name` is complete in mahindra_first_choice (40/40) but missing in spinny (0/60).
- Source-specific ratings and inspection evidence should remain in `extra_fields` until a normalization strategy is proven.

## Recommended Next Step

Add True Value as the third source contract before large-scale scraping. Spinny and MFC now prove that the shared canonical pipeline works across two very different website mechanics, but a third trusted source will expose schema gaps earlier than simply collecting more of the same two sources.

## Evidence Files

- spinny silver: `data/silver/listings/capture_date=2026-06-25/spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_silver.json`
- spinny quality summary: `data/gold/quality_summary/capture_date=2026-06-25/spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_quality_summary.json`
- spinny manifest: `data/gold/acquisition_runs/capture_date=2026-06-25/spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_manifest.json`
- mahindra_first_choice silver: `data/silver/listings/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_silver.json`
- mahindra_first_choice quality summary: `data/gold/quality_summary/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_quality_summary.json`
- mahindra_first_choice manifest: `data/gold/acquisition_runs/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_manifest.json`
