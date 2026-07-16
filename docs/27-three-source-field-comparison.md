# Spinny vs Mahindra First Choice vs True Value Field Comparison

Generated at: 2026-06-25

## Decision

All compared runs are approved as pricing-ready trusted-source inputs. They should stay separate at the acquisition layer and become comparable only after each source adapter emits canonical records.

The immediate modeling implication is simple: use all passing trusted sources for gold pricing rows, but keep source provenance and source-specific evidence fields intact.

## Run Summary

| Metric | Spinny | Mahindra First Choice | True Value |
| --- | ---: | ---: | ---: |
| Records | 60 | 40 | 40 |
| Pricing-ready | 60 | 40 | 40 |
| Quarantined | 0 | 0 | 0 |
| Required completeness | 100.00% | 100.00% | 100.00% |
| High-value completeness | 100.00% | 91.78% | 100.00% |
| Optional completeness | 39.83% | 36.50% | 42.25% |
| Overall completeness | 93.98% | 92.01% | 94.22% |
| Runtime seconds | 258.92 | 17.369 | 11.96 |

## Acquisition Behavior

| Metric | Spinny | Mahindra First Choice | True Value |
| --- | --- | --- | --- |
| Run ID | `run_20260625_spinny_hyderabad_manifest_60_detail60_smoke` | `run_20260625_mfc_hyderabad_40_smoke` | `run_20260625_true_value_hyderabad_40_smoke` |
| City | Hyderabad | Hyderabad | Hyderabad |
| Source URL | <https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/> | <https://www.mahindrafirstchoice.com/used-cars/hyderabad> | <https://www.marutisuzukitruevalue.com/buy-car> |
| Pagination type | infinite_scroll_batches | next_data_plus_xhr | dealer_discovery_plus_graphql |
| Attempted pages | 3 | 2 | 1 |
| Unique cards seen | 60 | 88 | 100 |
| Returned records | 60 | 40 | 40 |
| Source total items | n/a | 88 | 247 |
| Detail requested | 60 | 0 | 0 |
| Detail successful | 60 | 0 | 0 |

## Field Coverage

| Group | Field | Spinny | Mahindra First Choice | True Value | Note |
| --- | --- | ---: | ---: | ---: | --- |
| required | `source` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `source_listing_id` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `listing_url` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `captured_at` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `city` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `brand` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `model` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `model_year` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `listed_price_inr` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `km_driven` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `fuel_type` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `transmission` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `currency` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `raw_record_hash` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `ingestion_run_id` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `parser_version` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| required | `schema_version` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| high_value | `variant` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| high_value | `ownership` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| high_value | `registration_code` | 60/60 (100.00%) | 17/40 (42.50%) | 40/40 (100.00%) | source-specific gap |
| high_value | `locality` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| high_value | `seller_type` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| high_value | `is_certified` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| high_value | `is_available` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| optional | `state` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| optional | `hub_name` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| optional | `manufacture_year` | 60/60 (100.00%) | 0/40 (0.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `registration_year` | 60/60 (100.00%) | 0/40 (0.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `registration_state` | 60/60 (100.00%) | 17/40 (42.50%) | 40/40 (100.00%) | source-specific gap |
| optional | `registration_type` | 60/60 (100.00%) | 17/40 (42.50%) | 40/40 (100.00%) | source-specific gap |
| optional | `body_type` | 0/60 (0.00%) | 40/40 (100.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `color` | 0/60 (0.00%) | 40/40 (100.00%) | 39/40 (97.50%) | source-specific gap |
| optional | `seating_capacity` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `original_price_inr` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `discount_amount_inr` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `emi_amount_inr` | 60/60 (100.00%) | 22/40 (55.00%) | 0/40 (0.00%) | source-specific gap |
| optional | `token_amount_inr` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `price_label` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `deal_rating` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `extra_charges_flag` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `dealer_name` | 0/60 (0.00%) | 40/40 (100.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `inspection_status` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| optional | `inspection_score` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `condition_grade` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `accident_history` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `service_history_available` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `commercial_vehicle_flag` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `warranty_label` | 57/60 (95.00%) | 40/40 (100.00%) | 28/40 (70.00%) | partial difference |
| optional | `return_policy_label` | 60/60 (100.00%) | 0/40 (0.00%) | 0/40 (0.00%) | source-specific gap |
| optional | `finance_label` | 60/60 (100.00%) | 22/40 (55.00%) | 0/40 (0.00%) | source-specific gap |
| optional | `listing_posted_at` | 0/60 (0.00%) | 40/40 (100.00%) | 40/40 (100.00%) | source-specific gap |
| optional | `source_record_type` | 60/60 (100.00%) | 40/40 (100.00%) | 40/40 (100.00%) | stable across sources |
| optional | `first_seen_at` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |
| optional | `last_seen_at` | 0/60 (0.00%) | 0/40 (0.00%) | 0/40 (0.00%) | missing across sources |

## Source-Specific Extra Fields

| Field | Spinny | Mahindra First Choice | True Value |
| --- | ---: | ---: | ---: |
| `mahindra_first_choice.emi_text` | n/a | 22/40 (55.00%) | n/a |
| `mahindra_first_choice.id_classified` | n/a | 40/40 (100.00%) | n/a |
| `mahindra_first_choice.mileage` | n/a | 40/40 (100.00%) | n/a |
| `mahindra_first_choice.photo_count` | n/a | 40/40 (100.00%) | n/a |
| `mahindra_first_choice.rating_score` | n/a | 40/40 (100.00%) | n/a |
| `mahindra_first_choice.source_city` | n/a | 40/40 (100.00%) | n/a |
| `mahindra_first_choice.source_price_value` | n/a | 40/40 (100.00%) | n/a |
| `mahindra_first_choice.source_state` | n/a | 40/40 (100.00%) | n/a |
| `mahindra_first_choice.stock_id` | n/a | 40/40 (100.00%) | n/a |
| `mahindra_first_choice.variant_details` | n/a | 40/40 (100.00%) | n/a |
| `spinny_detail.inspection_summary` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.insurance_type` | 60/60 (100.00%) | n/a | n/a |
| `spinny_detail.insurance_validity` | 60/60 (100.00%) | n/a | n/a |
| `spinny_detail.quality_scores.core_systems.grade` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.core_systems.score` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.exteriors_lights.grade` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.exteriors_lights.score` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.interiors_ac.grade` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.interiors_ac.score` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.supporting_systems.grade` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.supporting_systems.score` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.wear_tear_parts.grade` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.quality_scores.wear_tear_parts.score` | 59/60 (98.33%) | n/a | n/a |
| `spinny_detail.service_due_text` | 48/60 (80.00%) | n/a | n/a |
| `true_value.dealer_code` | n/a | n/a | 40/40 (100.00%) |
| `true_value.dealer_location` | n/a | n/a | 40/40 (100.00%) |
| `true_value.dealer_map_code` | n/a | n/a | 40/40 (100.00%) |
| `true_value.dealer_parent_group` | n/a | n/a | 40/40 (100.00%) |
| `true_value.dms_certification_status` | n/a | n/a | 39/40 (97.50%) |
| `true_value.electrical_rating` | n/a | n/a | 40/40 (100.00%) |
| `true_value.engine_capacity` | n/a | n/a | 40/40 (100.00%) |
| `true_value.engine_rating` | n/a | n/a | 40/40 (100.00%) |
| `true_value.engine_type` | n/a | n/a | 40/40 (100.00%) |
| `true_value.exterior_rating` | n/a | n/a | 40/40 (100.00%) |
| `true_value.external_id` | n/a | n/a | 40/40 (100.00%) |
| `true_value.frame_rating` | n/a | n/a | 40/40 (100.00%) |
| `true_value.functional_rating` | n/a | n/a | 40/40 (100.00%) |
| `true_value.latitude` | n/a | n/a | 40/40 (100.00%) |
| `true_value.listing_score` | n/a | n/a | 40/40 (100.00%) |
| `true_value.longitude` | n/a | n/a | 40/40 (100.00%) |
| `true_value.number_of_owners` | n/a | n/a | 40/40 (100.00%) |
| `true_value.overall_rating` | n/a | n/a | 40/40 (100.00%) |
| `true_value.registration_date` | n/a | n/a | 40/40 (100.00%) |
| `true_value.rto_code` | n/a | n/a | 40/40 (100.00%) |
| `true_value.sku` | n/a | n/a | 40/40 (100.00%) |
| `true_value.suspension_rating` | n/a | n/a | 40/40 (100.00%) |
| `true_value.url_key` | n/a | n/a | 40/40 (100.00%) |
| `true_value.warranty_info` | n/a | n/a | 40/40 (100.00%) |

## Interpretation

- Required pricing fields are complete across all compared runs.
- `ownership` is complete across all compared runs.
- `registration_code` coverage differs by source: spinny 60/60, mahindra_first_choice 17/40, true_value 40/40.
- `body_type` is complete in mahindra_first_choice, true_value and missing in spinny. Coverage: spinny 0/60, mahindra_first_choice 40/40, true_value 40/40.
- `dealer_name` is complete in mahindra_first_choice, true_value and missing in spinny. Coverage: spinny 0/60, mahindra_first_choice 40/40, true_value 40/40.
- `warranty_label` coverage differs by source: spinny 57/60, mahindra_first_choice 40/40, true_value 28/40.
- Source-specific ratings, inspection states, and certification statuses should remain in `extra_fields` until a normalization strategy is proven.

## Recommended Next Step

Build a resumable batch runner next. The three Hyderabad source contracts now produce pricing-ready rows, but manual commands will not scale to source-city scheduling, retries, run manifests, and controlled data collection.

## Evidence Files

- spinny silver: `data/silver/listings/capture_date=2026-06-25/spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_silver.json`
- spinny quality summary: `data/gold/quality_summary/capture_date=2026-06-25/spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_quality_summary.json`
- spinny manifest: `data/gold/acquisition_runs/capture_date=2026-06-25/spinny_run_20260625_spinny_hyderabad_manifest_60_detail60_smoke_manifest.json`
- mahindra_first_choice silver: `data/silver/listings/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_silver.json`
- mahindra_first_choice quality summary: `data/gold/quality_summary/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_quality_summary.json`
- mahindra_first_choice manifest: `data/gold/acquisition_runs/capture_date=2026-06-25/mahindra_first_choice_run_20260625_mfc_hyderabad_40_smoke_manifest.json`
- true_value silver: `data/silver/listings/capture_date=2026-06-25/true_value_run_20260625_true_value_hyderabad_40_smoke_silver.json`
- true_value quality summary: `data/gold/quality_summary/capture_date=2026-06-25/true_value_run_20260625_true_value_hyderabad_40_smoke_quality_summary.json`
- true_value manifest: `data/gold/acquisition_runs/capture_date=2026-06-25/true_value_run_20260625_true_value_hyderabad_40_smoke_manifest.json`
