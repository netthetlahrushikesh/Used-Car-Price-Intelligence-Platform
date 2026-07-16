"""Command-line interface for local pipeline checks."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from time import monotonic
from pathlib import Path

from used_car_price_intelligence.acquisition import (
    capture_mfc_listing_payload,
    capture_spinny_detail_payload,
    capture_spinny_listing_payload,
    capture_true_value_listing_payload,
    build_spinny_incremental_detail_payload,
    build_spinny_incremental_detail_plan,
    load_spinny_detail_payloads,
    merge_spinny_detail_payload_into_listing_payload,
    summarize_mfc_listing_payload,
    summarize_spinny_listing_payload,
    summarize_spinny_detail_payload,
    summarize_true_value_listing_payload,
)
from used_car_price_intelligence.adapters import (
    validate_mahindra_first_choice_extracted_payload,
    validate_spinny_extracted_payload,
    validate_true_value_extracted_payload,
)
from used_car_price_intelligence.pipeline import (
    build_batch_run_plan,
    build_incremental_detail_run_manifest,
    build_run_manifest,
    default_batch_manifest_path,
    default_batch_summary_path,
    default_run_manifest_path,
    load_batch_manifest,
    passed_jobs_from_manifest,
    render_batch_summary_report,
    run_batch_plan,
    run_fixture_pipeline,
    write_batch_manifest,
    write_batch_summary_report,
    write_fixture_outputs,
    write_run_manifest,
)
from used_car_price_intelligence.reporting import (
    build_collection_ledger,
    build_listing_lifecycle_index,
    build_modeling_dataset_package,
    build_remaining_gap_strategy,
    build_scale_projection,
    build_snapshot_diff,
    default_smoke_report_path,
    load_source_run_profile,
    load_quality_summary,
    profile_field_completeness,
    render_collection_ledger_markdown,
    render_field_profile,
    render_listing_lifecycle_markdown,
    render_multi_source_comparison_report,
    render_quality_report,
    render_remaining_gap_strategy_markdown,
    render_scale_projection_markdown,
    render_snapshot_diff_markdown,
    render_snapshot_manifest_markdown,
    render_source_comparison_report,
    write_collection_ledger_json,
    write_collection_ledger_markdown,
    write_listing_lifecycle_json,
    write_listing_lifecycle_markdown,
    write_modeling_dataset_package,
    write_remaining_gap_strategy_json,
    write_remaining_gap_strategy_markdown,
    write_scale_projection_json,
    write_scale_projection_markdown,
    write_snapshot_diff_json,
    write_snapshot_diff_markdown,
    write_snapshot_manifest_json,
    write_snapshot_manifest_markdown,
    write_source_comparison_report,
    write_smoke_report,
    build_snapshot_manifest,
)


DEFAULT_SPINNY_FIXTURE = "tests/fixtures/spinny/listing_cards_extracted.json"
DEFAULT_FIXTURES = {
    "spinny": DEFAULT_SPINNY_FIXTURE,
    "mahindra_first_choice": "tests/fixtures/mahindra_first_choice/listing_cards_extracted.json",
    "true_value": "tests/fixtures/true_value/listing_cards_extracted.json",
}
FIXTURE_SOURCES = sorted(DEFAULT_FIXTURES)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="used-car-price-intelligence",
        description="Local tooling for the Used Car Price Intelligence Platform.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fixture_parser = subparsers.add_parser(
        "run-fixture",
        help="Run a source fixture through adapter, parser, schema, and quality gates.",
    )
    fixture_parser.add_argument("--source", default="spinny", choices=FIXTURE_SOURCES)
    fixture_parser.add_argument("--fixture", default=None)
    fixture_parser.add_argument("--registry", default="config/source_registry.yml")
    fixture_parser.add_argument("--captured-at", default="2026-06-24T03:00:00Z")
    fixture_parser.add_argument("--run-id", default="run_20260624_spinny_fixture_cli")
    fixture_parser.add_argument("--capture-date", default="2026-06-24")
    fixture_parser.add_argument("--output-root", default="data")
    fixture_parser.add_argument("--city", default="Hyderabad")
    fixture_parser.add_argument("--state", default="Telangana")
    fixture_parser.add_argument("--write", action="store_true", help="Write raw/silver/quarantine/gold outputs.")
    fixture_parser.add_argument("--json", action="store_true", help="Print summary as JSON.")

    report_parser = subparsers.add_parser(
        "quality-report",
        help="Render a generated quality summary JSON file as a Markdown report.",
    )
    report_parser.add_argument("--summary", required=True, help="Path to a quality summary JSON file.")

    field_parser = subparsers.add_parser(
        "field-profile",
        help="Render field-level completeness for a source fixture.",
    )
    field_parser.add_argument("--source", default="spinny", choices=FIXTURE_SOURCES)
    field_parser.add_argument("--fixture", default=None)
    field_parser.add_argument("--registry", default="config/source_registry.yml")
    field_parser.add_argument("--captured-at", default="2026-06-24T03:00:00Z")
    field_parser.add_argument("--run-id", default="run_20260624_spinny_field_profile")
    field_parser.add_argument("--json", action="store_true", help="Print field profile as JSON.")

    compare_parser = subparsers.add_parser(
        "compare-sources",
        help="Render a Markdown field comparison between two canonical source runs.",
    )
    compare_parser.add_argument("--left-source", required=True)
    compare_parser.add_argument("--left-silver", required=True)
    compare_parser.add_argument("--left-quality-summary", required=True)
    compare_parser.add_argument("--left-manifest", required=True)
    compare_parser.add_argument("--right-source", required=True)
    compare_parser.add_argument("--right-silver", required=True)
    compare_parser.add_argument("--right-quality-summary", required=True)
    compare_parser.add_argument("--right-manifest", required=True)
    compare_parser.add_argument("--title", default="Trusted Source Field Comparison")
    compare_parser.add_argument("--generated-at", default="2026-06-25")
    compare_parser.add_argument(
        "--recommendation",
        default="Review source-specific field gaps before scaling acquisition.",
    )
    compare_parser.add_argument("--output", default=None, help="Optional Markdown output path.")

    multi_compare_parser = subparsers.add_parser(
        "compare-source-runs",
        help="Render a Markdown field comparison across two or more canonical source runs.",
    )
    multi_compare_parser.add_argument(
        "--source-run",
        action="append",
        nargs=4,
        metavar=("SOURCE", "SILVER", "QUALITY_SUMMARY", "MANIFEST"),
        required=True,
        help="Repeat for each source run: source silver.json quality_summary.json manifest.json.",
    )
    multi_compare_parser.add_argument("--title", default="Trusted Source Field Comparison")
    multi_compare_parser.add_argument("--generated-at", default="2026-06-25")
    multi_compare_parser.add_argument(
        "--recommendation",
        default="Review source-specific field gaps before scaling acquisition.",
    )
    multi_compare_parser.add_argument("--output", default=None, help="Optional Markdown output path.")

    ledger_parser = subparsers.add_parser(
        "collection-ledger",
        help="Build a collection ledger from selected batch and source-run manifests.",
    )
    ledger_parser.add_argument("--collection-id", required=True)
    ledger_parser.add_argument(
        "--batch-manifest",
        action="append",
        default=None,
        help="Batch manifest to include. Repeat for multiple collection batches.",
    )
    ledger_parser.add_argument(
        "--source-manifest",
        action="append",
        default=None,
        help="Standalone source-run manifest to include. Repeat for multiple runs.",
    )
    ledger_parser.add_argument("--output-root", default="data")
    ledger_parser.add_argument("--generated-at", default=None)
    ledger_parser.add_argument("--output-json", default=None)
    ledger_parser.add_argument("--output-md", default=None)
    ledger_parser.add_argument("--json", action="store_true", help="Print ledger as JSON.")

    lifecycle_parser = subparsers.add_parser(
        "listing-lifecycle",
        help="Build listing identity, dedupe, and lifecycle index from a collection ledger.",
    )
    lifecycle_parser.add_argument("--lifecycle-id", required=True)
    lifecycle_parser.add_argument("--collection-ledger", required=True)
    lifecycle_parser.add_argument("--generated-at", default=None)
    lifecycle_parser.add_argument("--output-json", default=None)
    lifecycle_parser.add_argument("--output-md", default=None)
    lifecycle_parser.add_argument("--json", action="store_true", help="Print lifecycle index as JSON.")

    snapshot_parser = subparsers.add_parser(
        "snapshot-diff",
        help="Diff two listing lifecycle indexes, or create a baseline snapshot from the current lifecycle.",
    )
    snapshot_parser.add_argument("--snapshot-id", required=True)
    snapshot_parser.add_argument("--current-lifecycle", required=True)
    snapshot_parser.add_argument("--previous-lifecycle", default=None)
    snapshot_parser.add_argument("--snapshot-date", default="")
    snapshot_parser.add_argument("--generated-at", default=None)
    snapshot_parser.add_argument("--output-json", default=None)
    snapshot_parser.add_argument("--output-md", default=None)
    snapshot_parser.add_argument("--json", action="store_true", help="Print snapshot diff as JSON.")

    snapshot_manifest_parser = subparsers.add_parser(
        "snapshot-manifest",
        help="Build a snapshot manifest from ledger, lifecycle, and optional diff artifacts.",
    )
    snapshot_manifest_parser.add_argument("--snapshot-id", required=True)
    snapshot_manifest_parser.add_argument("--snapshot-date", required=True)
    snapshot_manifest_parser.add_argument("--collection-ledger", required=True)
    snapshot_manifest_parser.add_argument("--lifecycle-index", required=True)
    snapshot_manifest_parser.add_argument("--snapshot-diff", default=None)
    snapshot_manifest_parser.add_argument("--status", default="pass")
    snapshot_manifest_parser.add_argument("--target-pricing-ready", type=int, default=None)
    snapshot_manifest_parser.add_argument("--previous-snapshot-id", default="")
    snapshot_manifest_parser.add_argument("--previous-lifecycle-id", default="")
    snapshot_manifest_parser.add_argument("--scope-change-vs-previous", default="")
    snapshot_manifest_parser.add_argument("--extra-metadata", default=None)
    snapshot_manifest_parser.add_argument("--generated-at", default=None)
    snapshot_manifest_parser.add_argument("--output-json", default=None)
    snapshot_manifest_parser.add_argument("--output-md", default=None)
    snapshot_manifest_parser.add_argument("--json", action="store_true", help="Print snapshot manifest as JSON.")

    scale_parser = subparsers.add_parser(
        "scale-projection",
        help="Project snapshot counts needed to reach a trusted observation target.",
    )
    scale_parser.add_argument("--target-id", required=True)
    scale_parser.add_argument("--target-observations", type=int, default=100_000)
    scale_parser.add_argument("--current-snapshot-manifest", required=True)
    scale_parser.add_argument("--recommended-rows-per-snapshot", type=int, default=5_000)
    scale_parser.add_argument("--generated-at", default=None)
    scale_parser.add_argument("--output-json", default=None)
    scale_parser.add_argument("--output-md", default=None)
    scale_parser.add_argument("--json", action="store_true", help="Print scale projection as JSON.")

    gap_strategy_parser = subparsers.add_parser(
        "remaining-gap-strategy",
        help="Build a source-aware strategy for closing the current snapshot row gap.",
    )
    gap_strategy_parser.add_argument("--snapshot-manifest", required=True)
    gap_strategy_parser.add_argument("--target-config", default="config/snapshot_targets.yml")
    gap_strategy_parser.add_argument("--target-pricing-ready", type=int, default=None)
    gap_strategy_parser.add_argument(
        "--allocation-key",
        default="recommended_5000_row_source_allocation",
        help="YAML key containing per-source allocation targets.",
    )
    gap_strategy_parser.add_argument("--generated-at", default=None)
    gap_strategy_parser.add_argument("--output-json", default=None)
    gap_strategy_parser.add_argument("--output-md", default=None)
    gap_strategy_parser.add_argument("--json", action="store_true", help="Print remaining-gap strategy as JSON.")

    modeling_parser = subparsers.add_parser(
        "package-modeling-dataset",
        help="Build analysis-ready dataset, EDA summary, and baseline model artifacts from a snapshot.",
    )
    modeling_parser.add_argument("--snapshot-manifest", required=True)
    modeling_parser.add_argument(
        "--lifecycle-index",
        default=None,
        help="Optional lifecycle index override. Defaults to paths.lifecycle_index in the snapshot manifest.",
    )
    modeling_parser.add_argument("--dataset-id", default=None)
    modeling_parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to data/gold/modeling/<dataset-id>.",
    )
    modeling_parser.add_argument("--generated-at", default=None)
    modeling_parser.add_argument("--test-ratio", type=float, default=0.2)
    modeling_parser.add_argument("--min-group-size", type=int, default=3)
    modeling_parser.add_argument("--split-seed", default="snapshot_baseline_v0")
    modeling_parser.add_argument("--json", action="store_true", help="Print dataset manifest as JSON.")

    batch_parser = subparsers.add_parser(
        "run-batches",
        help="Plan or execute configured source-city acquisition batches.",
    )
    batch_parser.add_argument("--config", default="config/acquisition_batches.yml")
    batch_parser.add_argument("--batch-id", action="append", default=None, help="Specific batch id to include.")
    batch_parser.add_argument(
        "--status",
        action="append",
        default=None,
        help="Batch status to include when --batch-id is not provided. Defaults to validated.",
    )
    batch_parser.add_argument("--capture-date", default="2026-06-25")
    batch_parser.add_argument("--batch-run-id", default="batch_manual")
    batch_parser.add_argument("--output-root", default="data")
    batch_parser.add_argument("--manifest-output", default=None)
    batch_parser.add_argument(
        "--resume-from-manifest",
        default=None,
        help="Skip jobs already marked pass in a previous batch manifest.",
    )
    batch_parser.add_argument(
        "--skip-passed",
        action="store_true",
        help="Skip passed jobs from --resume-from-manifest, or from the target manifest when it exists.",
    )
    batch_parser.add_argument("--summary-output", default=None)
    batch_parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the planned batch commands. Without this flag the command only writes a plan.",
    )
    batch_parser.add_argument("--json", action="store_true", help="Print batch manifest as JSON.")

    payload_parser = subparsers.add_parser(
        "validate-payload",
        help="Validate an extracted source payload before canonical conversion.",
    )
    payload_parser.add_argument("--source", default="spinny", choices=FIXTURE_SOURCES)
    payload_parser.add_argument("--payload", required=True, help="Path to extracted payload JSON.")
    payload_parser.add_argument("--json", action="store_true", help="Print validation result as JSON.")

    capture_parser = subparsers.add_parser(
        "capture-spinny-live",
        help="Capture one public Spinny listing page into an extracted payload JSON file.",
    )
    capture_parser.add_argument(
        "--url",
        default="https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/",
    )
    capture_parser.add_argument("--output", required=True, help="Path for extracted payload JSON.")
    capture_parser.add_argument("--captured-at", default=None)
    capture_parser.add_argument("--max-records", type=int, default=20)
    capture_parser.add_argument(
        "--min-records",
        type=int,
        default=None,
        help="Fail capture validation unless at least this many parsed records are returned.",
    )
    capture_parser.add_argument("--max-pages", type=int, default=1)
    capture_parser.add_argument("--locality", default="Nexus Sujana Mall, Kukatpally")
    capture_parser.add_argument("--timeout-ms", type=int, default=30_000)
    capture_parser.add_argument("--capture-attempts", type=int, default=3)
    capture_parser.add_argument("--retry-delay-ms", type=int, default=1_500)
    capture_parser.add_argument("--page-scroll-delay-ms", type=int, default=2_500)
    capture_parser.add_argument("--headful", action="store_true", help="Run browser visibly.")
    capture_parser.add_argument("--json", action="store_true", help="Print validation result as JSON.")

    incremental_detail_parser = subparsers.add_parser(
        "spinny-incremental-detail",
        help="Plan and build Spinny detail enrichment using cached detail payloads plus optional missing capture.",
    )
    incremental_detail_parser.add_argument("--listing-payload", required=True)
    incremental_detail_parser.add_argument(
        "--existing-detail-payload",
        action="append",
        default=None,
        help="Existing Spinny detail payload to reuse. Repeat for multiple payloads.",
    )
    incremental_detail_parser.add_argument("--max-new-records", type=int, default=0)
    incremental_detail_parser.add_argument(
        "--capture-missing",
        action="store_true",
        help="Capture selected missing detail URLs. Without this, the command only reuses cache.",
    )
    incremental_detail_parser.add_argument(
        "--new-detail-output",
        default=None,
        help="Output path for newly captured missing detail records. Required with --capture-missing.",
    )
    incremental_detail_parser.add_argument("--output-plan", default=None)
    incremental_detail_parser.add_argument("--output-detail-payload", default=None)
    incremental_detail_parser.add_argument("--output-merged-payload", default=None)
    incremental_detail_parser.add_argument("--captured-at", default=None)
    incremental_detail_parser.add_argument("--timeout-ms", type=int, default=60_000)
    incremental_detail_parser.add_argument("--detail-delay-ms", type=int, default=3_000)
    incremental_detail_parser.add_argument("--detail-attempts", type=int, default=2)
    incremental_detail_parser.add_argument("--headful", action="store_true", help="Run browser visibly.")
    incremental_detail_parser.add_argument("--json", action="store_true", help="Print incremental detail result as JSON.")

    incremental_manifest_parser = subparsers.add_parser(
        "spinny-incremental-manifest",
        help="Build an acquisition-run manifest for a completed Spinny incremental detail run.",
    )
    incremental_manifest_parser.add_argument("--listing-payload", required=True)
    incremental_manifest_parser.add_argument("--detail-plan", required=True)
    incremental_manifest_parser.add_argument("--detail-payload", required=True)
    incremental_manifest_parser.add_argument("--quality-summary", required=True)
    incremental_manifest_parser.add_argument("--run-id", required=True)
    incremental_manifest_parser.add_argument("--capture-date", required=True)
    incremental_manifest_parser.add_argument("--output-root", default="data")
    incremental_manifest_parser.add_argument("--city", default="Hyderabad")
    incremental_manifest_parser.add_argument("--state", default="Telangana")
    incremental_manifest_parser.add_argument("--source-url", default=None)
    incremental_manifest_parser.add_argument("--captured-at", default=None)
    incremental_manifest_parser.add_argument("--started-at", default=None)
    incremental_manifest_parser.add_argument("--completed-at", default=None)
    incremental_manifest_parser.add_argument("--duration-seconds", type=float, default=None)
    incremental_manifest_parser.add_argument("--min-records", type=int, default=None)
    incremental_manifest_parser.add_argument("--merged-payload", default=None)
    incremental_manifest_parser.add_argument("--new-detail-payload", default=None)
    incremental_manifest_parser.add_argument("--raw-output", default=None)
    incremental_manifest_parser.add_argument("--silver-output", default=None)
    incremental_manifest_parser.add_argument("--quarantine-output", default=None)
    incremental_manifest_parser.add_argument("--manifest-output", default=None)
    incremental_manifest_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the generated source-run manifest as JSON.",
    )

    mfc_capture_parser = subparsers.add_parser(
        "capture-mfc-live",
        help="Capture public Mahindra First Choice listing pages into an extracted payload JSON file.",
    )
    mfc_capture_parser.add_argument("--url", default="https://www.mahindrafirstchoice.com/used-cars/hyderabad")
    mfc_capture_parser.add_argument("--output", required=True, help="Path for extracted payload JSON.")
    mfc_capture_parser.add_argument("--captured-at", default=None)
    mfc_capture_parser.add_argument("--max-records", type=int, default=40)
    mfc_capture_parser.add_argument(
        "--min-records",
        type=int,
        default=None,
        help="Fail capture validation unless at least this many parsed records are returned.",
    )
    mfc_capture_parser.add_argument("--max-pages", type=int, default=2)
    mfc_capture_parser.add_argument("--timeout-ms", type=int, default=60_000)
    mfc_capture_parser.add_argument("--capture-attempts", type=int, default=3)
    mfc_capture_parser.add_argument("--retry-delay-ms", type=int, default=2_000)
    mfc_capture_parser.add_argument("--page-scroll-delay-ms", type=int, default=2_500)
    mfc_capture_parser.add_argument("--headful", action="store_true", help="Run browser visibly.")
    mfc_capture_parser.add_argument("--json", action="store_true", help="Print validation result as JSON.")

    true_value_capture_parser = subparsers.add_parser(
        "capture-true-value-live",
        help="Capture public Maruti Suzuki True Value listings into an extracted payload JSON file.",
    )
    true_value_capture_parser.add_argument("--url", default="https://www.marutisuzukitruevalue.com/buy-car")
    true_value_capture_parser.add_argument("--output", required=True, help="Path for extracted payload JSON.")
    true_value_capture_parser.add_argument("--captured-at", default=None)
    true_value_capture_parser.add_argument("--city", default="Hyderabad")
    true_value_capture_parser.add_argument("--state", default="Telangana")
    true_value_capture_parser.add_argument("--latitude", type=float, default=17.385044)
    true_value_capture_parser.add_argument("--longitude", type=float, default=78.486671)
    true_value_capture_parser.add_argument("--dealer-distance-m", type=int, default=25_000)
    true_value_capture_parser.add_argument("--max-records", type=int, default=40)
    true_value_capture_parser.add_argument(
        "--min-records",
        type=int,
        default=None,
        help="Fail capture validation unless at least this many parsed records are returned.",
    )
    true_value_capture_parser.add_argument("--max-pages", type=int, default=1)
    true_value_capture_parser.add_argument("--page-size", type=int, default=100)
    true_value_capture_parser.add_argument("--timeout-seconds", type=int, default=60)
    true_value_capture_parser.add_argument("--capture-attempts", type=int, default=3)
    true_value_capture_parser.add_argument("--retry-delay-ms", type=int, default=2_000)
    true_value_capture_parser.add_argument("--json", action="store_true", help="Print validation result as JSON.")

    smoke_parser = subparsers.add_parser(
        "spinny-live-smoke",
        help="Capture, validate, canonicalize, and report one public Spinny listing page.",
    )
    smoke_parser.add_argument(
        "--url",
        default="https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/",
    )
    smoke_parser.add_argument("--payload-output", required=True, help="Path for extracted payload JSON.")
    smoke_parser.add_argument("--captured-at", default=None)
    smoke_parser.add_argument("--run-id", default="run_20260624_spinny_live_smoke")
    smoke_parser.add_argument("--capture-date", default="2026-06-24")
    smoke_parser.add_argument("--output-root", default="data")
    smoke_parser.add_argument("--city", default="Hyderabad")
    smoke_parser.add_argument("--state", default="Telangana")
    smoke_parser.add_argument(
        "--report-output",
        default=None,
        help="Path for the persisted Markdown smoke report. Defaults under data/gold/smoke_reports.",
    )
    smoke_parser.add_argument("--registry", default="config/source_registry.yml")
    smoke_parser.add_argument("--max-records", type=int, default=20)
    smoke_parser.add_argument(
        "--min-records",
        type=int,
        default=None,
        help="Minimum parsed records required for the smoke run. Defaults to --max-records.",
    )
    smoke_parser.add_argument("--max-pages", type=int, default=1)
    smoke_parser.add_argument("--locality", default="Nexus Sujana Mall, Kukatpally")
    smoke_parser.add_argument("--timeout-ms", type=int, default=30_000)
    smoke_parser.add_argument("--capture-attempts", type=int, default=3)
    smoke_parser.add_argument("--retry-delay-ms", type=int, default=1_500)
    smoke_parser.add_argument("--page-scroll-delay-ms", type=int, default=2_500)
    smoke_parser.add_argument(
        "--detail-pages",
        type=int,
        default=0,
        help="Capture and merge this many public detail pages after card capture.",
    )
    smoke_parser.add_argument("--detail-output", default=None, help="Path for captured detail-page payload JSON.")
    smoke_parser.add_argument("--merged-output", default=None, help="Path for card payload after detail merge.")
    smoke_parser.add_argument("--detail-delay-ms", type=int, default=1_000)
    smoke_parser.add_argument("--detail-attempts", type=int, default=2)
    smoke_parser.add_argument("--headful", action="store_true", help="Run browser visibly.")
    smoke_parser.add_argument("--json", action="store_true", help="Print smoke result as JSON.")

    mfc_smoke_parser = subparsers.add_parser(
        "mfc-live-smoke",
        help="Capture, validate, canonicalize, and report public Mahindra First Choice listings.",
    )
    mfc_smoke_parser.add_argument("--url", default="https://www.mahindrafirstchoice.com/used-cars/hyderabad")
    mfc_smoke_parser.add_argument("--payload-output", required=True, help="Path for extracted payload JSON.")
    mfc_smoke_parser.add_argument("--captured-at", default=None)
    mfc_smoke_parser.add_argument("--run-id", default="run_20260625_mfc_live_smoke")
    mfc_smoke_parser.add_argument("--capture-date", default="2026-06-25")
    mfc_smoke_parser.add_argument("--output-root", default="data")
    mfc_smoke_parser.add_argument("--city", default="Hyderabad")
    mfc_smoke_parser.add_argument("--state", default="Telangana")
    mfc_smoke_parser.add_argument(
        "--report-output",
        default=None,
        help="Path for the persisted Markdown smoke report. Defaults under data/gold/smoke_reports.",
    )
    mfc_smoke_parser.add_argument("--registry", default="config/source_registry.yml")
    mfc_smoke_parser.add_argument("--max-records", type=int, default=40)
    mfc_smoke_parser.add_argument(
        "--min-records",
        type=int,
        default=None,
        help="Minimum parsed records required for the smoke run. Defaults to --max-records.",
    )
    mfc_smoke_parser.add_argument("--max-pages", type=int, default=2)
    mfc_smoke_parser.add_argument("--timeout-ms", type=int, default=60_000)
    mfc_smoke_parser.add_argument("--capture-attempts", type=int, default=3)
    mfc_smoke_parser.add_argument("--retry-delay-ms", type=int, default=2_000)
    mfc_smoke_parser.add_argument("--page-scroll-delay-ms", type=int, default=2_500)
    mfc_smoke_parser.add_argument("--headful", action="store_true", help="Run browser visibly.")
    mfc_smoke_parser.add_argument("--json", action="store_true", help="Print smoke result as JSON.")

    true_value_smoke_parser = subparsers.add_parser(
        "true-value-live-smoke",
        help="Capture, validate, canonicalize, and report public Maruti Suzuki True Value listings.",
    )
    true_value_smoke_parser.add_argument("--url", default="https://www.marutisuzukitruevalue.com/buy-car")
    true_value_smoke_parser.add_argument("--payload-output", required=True, help="Path for extracted payload JSON.")
    true_value_smoke_parser.add_argument("--captured-at", default=None)
    true_value_smoke_parser.add_argument("--run-id", default="run_20260625_true_value_live_smoke")
    true_value_smoke_parser.add_argument("--capture-date", default="2026-06-25")
    true_value_smoke_parser.add_argument("--output-root", default="data")
    true_value_smoke_parser.add_argument("--city", default="Hyderabad")
    true_value_smoke_parser.add_argument("--state", default="Telangana")
    true_value_smoke_parser.add_argument("--latitude", type=float, default=17.385044)
    true_value_smoke_parser.add_argument("--longitude", type=float, default=78.486671)
    true_value_smoke_parser.add_argument("--dealer-distance-m", type=int, default=25_000)
    true_value_smoke_parser.add_argument(
        "--report-output",
        default=None,
        help="Path for the persisted Markdown smoke report. Defaults under data/gold/smoke_reports.",
    )
    true_value_smoke_parser.add_argument("--registry", default="config/source_registry.yml")
    true_value_smoke_parser.add_argument("--max-records", type=int, default=40)
    true_value_smoke_parser.add_argument(
        "--min-records",
        type=int,
        default=None,
        help="Minimum parsed records required for the smoke run. Defaults to --max-records.",
    )
    true_value_smoke_parser.add_argument("--max-pages", type=int, default=1)
    true_value_smoke_parser.add_argument("--page-size", type=int, default=100)
    true_value_smoke_parser.add_argument("--timeout-seconds", type=int, default=60)
    true_value_smoke_parser.add_argument("--capture-attempts", type=int, default=3)
    true_value_smoke_parser.add_argument("--retry-delay-ms", type=int, default=2_000)
    true_value_smoke_parser.add_argument("--json", action="store_true", help="Print smoke result as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-fixture":
        fixture_path = _resolve_fixture_path(args.source, args.fixture)
        records, results, summary = run_fixture_pipeline(
            source=args.source,
            fixture_path=fixture_path,
            captured_at=args.captured_at,
            ingestion_run_id=args.run_id,
            registry_path=args.registry,
            city=args.city,
            state=args.state,
        )
        output_paths = None
        if args.write:
            output_paths = write_fixture_outputs(
                records=records,
                results=results,
                summary=summary,
                fixture_path=fixture_path,
                output_root=args.output_root,
                capture_date=args.capture_date,
                run_id=args.run_id,
            )

        summary_payload = summary.to_dict()
        if output_paths is not None:
            summary_payload["output_paths"] = output_paths.to_dict()

        if args.json:
            print(json.dumps(summary_payload, indent=2, sort_keys=True))
        else:
            _print_text_summary(summary_payload)
        return 0

    if args.command == "quality-report":
        summary = load_quality_summary(args.summary)
        print(render_quality_report(summary), end="")
        return 0

    if args.command == "field-profile":
        fixture_path = _resolve_fixture_path(args.source, args.fixture)
        records, _, _ = run_fixture_pipeline(
            source=args.source,
            fixture_path=fixture_path,
            captured_at=args.captured_at,
            ingestion_run_id=args.run_id,
            registry_path=args.registry,
        )
        report = profile_field_completeness(source=args.source, records=records)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            print(render_field_profile(report), end="")
        return 0

    if args.command == "compare-sources":
        left = load_source_run_profile(
            source=args.left_source,
            silver_path=args.left_silver,
            quality_summary_path=args.left_quality_summary,
            manifest_path=args.left_manifest,
        )
        right = load_source_run_profile(
            source=args.right_source,
            silver_path=args.right_silver,
            quality_summary_path=args.right_quality_summary,
            manifest_path=args.right_manifest,
        )
        report = render_source_comparison_report(
            left,
            right,
            title=args.title,
            generated_at=args.generated_at,
            recommendation=args.recommendation,
        )
        if args.output:
            write_source_comparison_report(args.output, report)
            print(str(args.output))
        else:
            print(report, end="")
        return 0

    if args.command == "compare-source-runs":
        if len(args.source_run) < 2:
            parser.error("compare-source-runs requires at least two --source-run entries")
            return 2
        profiles = [
            load_source_run_profile(
                source=source,
                silver_path=silver_path,
                quality_summary_path=quality_summary_path,
                manifest_path=manifest_path,
            )
            for source, silver_path, quality_summary_path, manifest_path in args.source_run
        ]
        report = render_multi_source_comparison_report(
            profiles,
            title=args.title,
            generated_at=args.generated_at,
            recommendation=args.recommendation,
        )
        if args.output:
            write_source_comparison_report(args.output, report)
            print(str(args.output))
        else:
            print(report, end="")
        return 0

    if args.command == "collection-ledger":
        if not args.batch_manifest and not args.source_manifest:
            parser.error("collection-ledger requires at least one --batch-manifest or --source-manifest")
            return 2
        ledger = build_collection_ledger(
            collection_id=args.collection_id,
            batch_manifest_paths=args.batch_manifest,
            source_manifest_paths=args.source_manifest,
            output_root=args.output_root,
            generated_at=args.generated_at,
        )
        if args.output_json:
            write_collection_ledger_json(args.output_json, ledger)
        if args.output_md:
            write_collection_ledger_markdown(args.output_md, ledger)
        if args.json:
            print(json.dumps(ledger, indent=2, sort_keys=True))
        elif args.output_md:
            print(str(args.output_md))
        else:
            print(render_collection_ledger_markdown(ledger), end="")
        return 0

    if args.command == "listing-lifecycle":
        index = build_listing_lifecycle_index(
            lifecycle_id=args.lifecycle_id,
            collection_ledger_path=args.collection_ledger,
            generated_at=args.generated_at,
        )
        if args.output_json:
            write_listing_lifecycle_json(args.output_json, index)
        if args.output_md:
            write_listing_lifecycle_markdown(args.output_md, index)
        if args.json:
            print(json.dumps(index, indent=2, sort_keys=True))
        elif args.output_md:
            print(str(args.output_md))
        else:
            print(render_listing_lifecycle_markdown(index), end="")
        return 0

    if args.command == "snapshot-diff":
        diff = build_snapshot_diff(
            snapshot_id=args.snapshot_id,
            current_lifecycle_path=args.current_lifecycle,
            previous_lifecycle_path=args.previous_lifecycle,
            snapshot_date=args.snapshot_date,
            generated_at=args.generated_at,
        )
        if args.output_json:
            write_snapshot_diff_json(args.output_json, diff)
        if args.output_md:
            write_snapshot_diff_markdown(args.output_md, diff)
        if args.json:
            print(json.dumps(diff, indent=2, sort_keys=True))
        elif args.output_md:
            print(str(args.output_md))
        else:
            print(render_snapshot_diff_markdown(diff), end="")
        return 0

    if args.command == "snapshot-manifest":
        manifest = build_snapshot_manifest(
            snapshot_id=args.snapshot_id,
            snapshot_date=args.snapshot_date,
            collection_ledger_path=args.collection_ledger,
            lifecycle_index_path=args.lifecycle_index,
            snapshot_diff_path=args.snapshot_diff,
            status=args.status,
            target_pricing_ready=args.target_pricing_ready,
            previous_snapshot_id=args.previous_snapshot_id,
            previous_lifecycle_id=args.previous_lifecycle_id,
            scope_change_vs_previous=args.scope_change_vs_previous,
            extra_metadata_path=args.extra_metadata,
            generated_at=args.generated_at,
        )
        if args.output_json:
            write_snapshot_manifest_json(args.output_json, manifest)
        if args.output_md:
            write_snapshot_manifest_markdown(args.output_md, manifest)
        if args.json:
            print(json.dumps(manifest, indent=2, sort_keys=True))
        elif args.output_md:
            print(str(args.output_md))
        else:
            print(render_snapshot_manifest_markdown(manifest), end="")
        return 0

    if args.command == "scale-projection":
        projection = build_scale_projection(
            target_id=args.target_id,
            target_observations=args.target_observations,
            current_snapshot_manifest_path=args.current_snapshot_manifest,
            recommended_rows_per_snapshot=args.recommended_rows_per_snapshot,
            generated_at=args.generated_at,
        )
        if args.output_json:
            write_scale_projection_json(args.output_json, projection)
        if args.output_md:
            write_scale_projection_markdown(args.output_md, projection)
        if args.json:
            print(json.dumps(projection, indent=2, sort_keys=True))
        elif args.output_md:
            print(str(args.output_md))
        else:
            print(render_scale_projection_markdown(projection), end="")
        return 0

    if args.command == "remaining-gap-strategy":
        strategy = build_remaining_gap_strategy(
            snapshot_manifest_path=args.snapshot_manifest,
            target_config_path=args.target_config,
            target_pricing_ready=args.target_pricing_ready,
            allocation_key=args.allocation_key,
            generated_at=args.generated_at,
        )
        if args.output_json:
            write_remaining_gap_strategy_json(args.output_json, strategy)
        if args.output_md:
            write_remaining_gap_strategy_markdown(args.output_md, strategy)
        if args.json:
            print(json.dumps(strategy, indent=2, sort_keys=True))
        elif args.output_md:
            print(str(args.output_md))
        else:
            print(render_remaining_gap_strategy_markdown(strategy), end="")
        return 0

    if args.command == "package-modeling-dataset":
        package = build_modeling_dataset_package(
            snapshot_manifest_path=args.snapshot_manifest,
            lifecycle_index_path=args.lifecycle_index,
            dataset_id=args.dataset_id,
            generated_at=args.generated_at,
            test_ratio=args.test_ratio,
            min_group_size=args.min_group_size,
            split_seed=args.split_seed,
        )
        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else Path("data") / "gold" / "modeling" / str(package["manifest"]["dataset_id"])
        )
        output_paths = write_modeling_dataset_package(output_dir=output_dir, package=package)
        manifest = {**package["manifest"], "outputs": output_paths}
        if args.json:
            print(json.dumps(manifest, indent=2, sort_keys=True))
        else:
            print(output_paths["dataset_manifest_markdown"])
        return 0

    if args.command == "run-batches":
        manifest_output = (
            Path(args.manifest_output)
            if args.manifest_output
            else default_batch_manifest_path(
                output_root=args.output_root,
                capture_date=args.capture_date,
                batch_run_id=args.batch_run_id,
            )
        )
        summary_output = (
            Path(args.summary_output)
            if args.summary_output
            else default_batch_summary_path(
                output_root=args.output_root,
                capture_date=args.capture_date,
                batch_run_id=args.batch_run_id,
            )
        )
        resume_manifest_path: Path | None = None
        if args.resume_from_manifest:
            resume_manifest_path = Path(args.resume_from_manifest)
        elif args.skip_passed and manifest_output.exists():
            resume_manifest_path = manifest_output

        try:
            plan = build_batch_run_plan(
                config_path=args.config,
                capture_date=args.capture_date,
                batch_run_id=args.batch_run_id,
                output_root=args.output_root,
                batch_ids=args.batch_id,
                statuses=args.status,
            )
            resume_manifest = (
                load_batch_manifest(resume_manifest_path) if resume_manifest_path is not None else None
            )
            skip_passed_jobs = passed_jobs_from_manifest(resume_manifest) if resume_manifest else {}
            batch_manifest = run_batch_plan(
                plan,
                execute=args.execute,
                cwd=Path.cwd(),
                skip_passed_jobs=skip_passed_jobs,
                resume_manifest_path=resume_manifest_path,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        batch_manifest["manifest_output"] = str(manifest_output)
        batch_manifest["summary_output"] = str(summary_output)
        write_batch_manifest(manifest_output, batch_manifest)
        batch_summary = render_batch_summary_report(
            batch_manifest,
            output_root=args.output_root,
            cwd=Path.cwd(),
        )
        write_batch_summary_report(summary_output, batch_summary)
        if args.json:
            print(json.dumps(batch_manifest, indent=2, sort_keys=True))
        else:
            print(f"batch_manifest: {manifest_output}")
            print(f"batch_summary: {summary_output}")
            print(f"status: {batch_manifest['status']}")
            print(f"job_count: {batch_manifest['job_count']}")
            for job in batch_manifest["job_results"]:
                job_dict = dict(job)
                print(
                    f"- {job_dict['batch_id']}: {job_dict['status']} "
                    f"run_id={job_dict['run_id']}"
                )
        return 0 if batch_manifest["status"] in {"planned", "pass"} else 1

    if args.command == "validate-payload":
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        if args.source == "spinny":
            result = validate_spinny_extracted_payload(payload)
        elif args.source == "mahindra_first_choice":
            result = validate_mahindra_first_choice_extracted_payload(payload)
        elif args.source == "true_value":
            result = validate_true_value_extracted_payload(payload)
        else:
            parser.error(f"Unsupported source: {args.source}")
            return 2

        payload_result = result.to_dict()
        if args.json:
            print(json.dumps(payload_result, indent=2, sort_keys=True))
        else:
            _print_payload_validation(payload_result)
        return 0 if result.ok else 1

    if args.command == "capture-spinny-live":
        try:
            payload = capture_spinny_listing_payload(
                source_url=args.url,
                output_path=args.output,
                captured_at=args.captured_at,
                max_records=args.max_records,
                min_records=args.min_records,
                max_pages=args.max_pages,
                locality_fallback=args.locality,
                timeout_ms=args.timeout_ms,
                capture_attempts=args.capture_attempts,
                retry_delay_ms=args.retry_delay_ms,
                page_scroll_delay_ms=args.page_scroll_delay_ms,
                headless=not args.headful,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        result = validate_spinny_extracted_payload(payload)
        payload_result = result.to_dict()
        payload_result["output_path"] = args.output
        payload_result["listing_capture"] = summarize_spinny_listing_payload(payload)
        coverage_ok = True
        if args.min_records is not None:
            payload_result["listing_coverage"] = _listing_coverage_result(
                payload_result["listing_capture"],
                min_records=args.min_records,
            )
            coverage_ok = bool(payload_result["listing_coverage"]["ok"])
        if args.json:
            print(json.dumps(payload_result, indent=2, sort_keys=True))
        else:
            print(f"output_path: {args.output}")
            _print_payload_validation(payload_result)
        return 0 if result.ok and coverage_ok else 1

    if args.command == "spinny-incremental-detail":
        listing_payload = json.loads(Path(args.listing_payload).read_text(encoding="utf-8"))
        existing_detail_payloads = load_spinny_detail_payloads(args.existing_detail_payload)
        plan = build_spinny_incremental_detail_plan(
            listing_payload=listing_payload,
            existing_detail_payloads=existing_detail_payloads,
            max_new_records=args.max_new_records,
        )
        if args.output_plan:
            _write_json(args.output_plan, plan)

        new_detail_payload = None
        if args.capture_missing:
            if not args.new_detail_output:
                parser.error("spinny-incremental-detail requires --new-detail-output with --capture-missing")
                return 2
            selected_new_urls = list(plan.get("selected_new_urls") or [])
            if selected_new_urls:
                try:
                    new_detail_payload = capture_spinny_detail_payload(
                        listing_urls=selected_new_urls,
                        output_path=args.new_detail_output,
                        captured_at=args.captured_at,
                        max_records=len(selected_new_urls),
                        timeout_ms=args.timeout_ms,
                        delay_ms=args.detail_delay_ms,
                        attempts=args.detail_attempts,
                        headless=not args.headful,
                    )
                except RuntimeError as exc:
                    print(str(exc), file=sys.stderr)
                    return 2
            else:
                new_detail_payload = {
                    "source": "spinny",
                    "captured_for": "incremental_public_detail_enrichment",
                    "capture_method": "no_missing_detail_urls",
                    "captured_at": args.captured_at or _utc_now(),
                    "policy": {
                        "requested_urls": 0,
                        "valid_urls": 0,
                        "max_records": 0,
                        "attempted_records": 0,
                    },
                    "records": [],
                }
                _write_json(args.new_detail_output, new_detail_payload)

        detail_payload = build_spinny_incremental_detail_payload(
            listing_payload=listing_payload,
            existing_detail_payloads=existing_detail_payloads,
            new_detail_payload=new_detail_payload,
            captured_at=args.captured_at,
            max_new_records=args.max_new_records,
        )
        merged_payload = merge_spinny_detail_payload_into_listing_payload(
            listing_payload=listing_payload,
            detail_payload=detail_payload,
        )
        output_paths: dict[str, str] = {}
        if args.output_detail_payload:
            _write_json(args.output_detail_payload, detail_payload)
            output_paths["detail_payload"] = args.output_detail_payload
        if args.output_merged_payload:
            _write_json(args.output_merged_payload, merged_payload)
            output_paths["merged_payload"] = args.output_merged_payload

        result = {
            "source": "spinny",
            "plan": plan,
            "detail_summary": summarize_spinny_detail_payload(detail_payload),
            "merged_records": len([record for record in merged_payload.get("records", []) if isinstance(record, dict)]),
            "output_paths": output_paths,
        }
        if args.capture_missing and args.new_detail_output:
            result["output_paths"]["new_detail_payload"] = args.new_detail_output

        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        elif output_paths:
            for value in output_paths.values():
                print(value)
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "spinny-incremental-manifest":
        listing_payload = _load_json_object(args.listing_payload)
        detail_plan = _load_json_object(args.detail_plan)
        detail_payload = _load_json_object(args.detail_payload)
        quality_summary = _load_json_object(args.quality_summary)

        listing_capture = summarize_spinny_listing_payload(listing_payload)
        min_records = (
            max(0, args.min_records)
            if args.min_records is not None
            else int(listing_capture.get("min_records") or 0)
        )
        listing_coverage = _listing_coverage_result(listing_capture, min_records=min_records)
        detail_enrichment = summarize_spinny_detail_payload(detail_payload)
        detail_policy = detail_payload.get("policy")
        if isinstance(detail_policy, dict):
            detail_enrichment["incremental_policy"] = detail_policy

        captured_at = args.captured_at or str(listing_payload.get("captured_at") or _utc_now())
        started_at = args.started_at or captured_at
        completed_at = args.completed_at or str(detail_payload.get("captured_at") or captured_at)
        source_url = args.source_url or str(listing_payload.get("source_url") or "")
        output_paths = _spinny_incremental_manifest_output_paths(
            output_root=args.output_root,
            run_id=args.run_id,
            capture_date=args.capture_date,
            listing_payload=args.listing_payload,
            detail_plan=args.detail_plan,
            detail_payload=args.detail_payload,
            quality_summary=args.quality_summary,
            raw_output=args.raw_output,
            silver_output=args.silver_output,
            quarantine_output=args.quarantine_output,
            merged_payload=args.merged_payload,
            new_detail_payload=args.new_detail_payload,
        )
        manifest = build_incremental_detail_run_manifest(
            source="spinny",
            source_url=source_url,
            city=args.city,
            state=args.state,
            run_id=args.run_id,
            capture_date=args.capture_date,
            captured_at=captured_at,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=args.duration_seconds,
            run_options={
                "workflow": "spinny_incremental_detail",
                "min_records": min_records,
                "max_new_records": int(detail_plan.get("max_new_records") or 0),
                "cache_hit_count": int(detail_plan.get("cache_hit_count") or 0),
                "pending_count": int(detail_plan.get("pending_count") or 0),
                "selected_new_count": int(detail_plan.get("selected_new_count") or 0),
                "skipped_over_new_cap": int(detail_plan.get("skipped_over_new_cap") or 0),
            },
            listing_capture=listing_capture,
            listing_coverage=listing_coverage,
            detail_plan=detail_plan,
            detail_enrichment=detail_enrichment,
            quality_summary=quality_summary,
            output_paths=output_paths,
        )
        manifest_output = args.manifest_output or default_run_manifest_path(
            output_root=args.output_root,
            capture_date=args.capture_date,
            source="spinny",
            run_id=args.run_id,
        )
        written = write_run_manifest(manifest_output, manifest)
        if args.json:
            print(json.dumps(manifest, indent=2, sort_keys=True))
        else:
            print(str(written))
        return 0

    if args.command == "capture-mfc-live":
        try:
            payload = capture_mfc_listing_payload(
                source_url=args.url,
                output_path=args.output,
                captured_at=args.captured_at,
                max_records=args.max_records,
                min_records=args.min_records,
                max_pages=args.max_pages,
                timeout_ms=args.timeout_ms,
                capture_attempts=args.capture_attempts,
                retry_delay_ms=args.retry_delay_ms,
                page_scroll_delay_ms=args.page_scroll_delay_ms,
                headless=not args.headful,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        result = validate_mahindra_first_choice_extracted_payload(payload)
        payload_result = result.to_dict()
        payload_result["output_path"] = args.output
        payload_result["listing_capture"] = summarize_mfc_listing_payload(payload)
        coverage_ok = True
        if args.min_records is not None:
            payload_result["listing_coverage"] = _listing_coverage_result(
                payload_result["listing_capture"],
                min_records=args.min_records,
            )
            coverage_ok = bool(payload_result["listing_coverage"]["ok"])
        if args.json:
            print(json.dumps(payload_result, indent=2, sort_keys=True))
        else:
            print(f"output_path: {args.output}")
            _print_payload_validation(payload_result)
        return 0 if result.ok and coverage_ok else 1

    if args.command == "capture-true-value-live":
        try:
            payload = capture_true_value_listing_payload(
                source_url=args.url,
                output_path=args.output,
                captured_at=args.captured_at,
                city=args.city,
                state=args.state,
                latitude=args.latitude,
                longitude=args.longitude,
                dealer_distance_m=args.dealer_distance_m,
                max_records=args.max_records,
                min_records=args.min_records,
                max_pages=args.max_pages,
                page_size=args.page_size,
                timeout_seconds=args.timeout_seconds,
                capture_attempts=args.capture_attempts,
                retry_delay_ms=args.retry_delay_ms,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        result = validate_true_value_extracted_payload(payload)
        payload_result = result.to_dict()
        payload_result["output_path"] = args.output
        payload_result["listing_capture"] = summarize_true_value_listing_payload(payload)
        coverage_ok = True
        if args.min_records is not None:
            payload_result["listing_coverage"] = _listing_coverage_result(
                payload_result["listing_capture"],
                min_records=args.min_records,
            )
            coverage_ok = bool(payload_result["listing_coverage"]["ok"])
        if args.json:
            print(json.dumps(payload_result, indent=2, sort_keys=True))
        else:
            print(f"output_path: {args.output}")
            _print_payload_validation(payload_result)
        return 0 if result.ok and coverage_ok else 1

    if args.command == "mfc-live-smoke":
        started_at = _utc_now()
        started_monotonic = monotonic()
        captured_at = args.captured_at or _utc_now()
        min_records = _resolve_smoke_min_records(min_records=args.min_records, max_records=args.max_records)
        report_output = Path(args.report_output) if args.report_output else default_smoke_report_path(
            output_root=args.output_root,
            capture_date=args.capture_date,
            source="mahindra_first_choice",
            run_id=args.run_id,
        )
        manifest_output = default_run_manifest_path(
            output_root=args.output_root,
            capture_date=args.capture_date,
            source="mahindra_first_choice",
            run_id=args.run_id,
        )
        run_options = _mfc_live_smoke_run_options(args, min_records=min_records)
        try:
            payload = capture_mfc_listing_payload(
                source_url=args.url,
                output_path=args.payload_output,
                captured_at=captured_at,
                max_records=args.max_records,
                min_records=min_records,
                max_pages=args.max_pages,
                timeout_ms=args.timeout_ms,
                capture_attempts=args.capture_attempts,
                retry_delay_ms=args.retry_delay_ms,
                page_scroll_delay_ms=args.page_scroll_delay_ms,
                headless=not args.headful,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        payload_validation = validate_mahindra_first_choice_extracted_payload(payload)
        listing_capture = summarize_mfc_listing_payload(payload)
        listing_coverage = _listing_coverage_result(listing_capture, min_records=min_records)
        smoke_payload: dict[str, object] = {
            "source": "mahindra_first_choice",
            "source_url": args.url,
            "run_id": args.run_id,
            "capture_date": args.capture_date,
            "captured_at": str(payload.get("captured_at") or captured_at),
            "payload_output": args.payload_output,
            "payload_validation": payload_validation.to_dict(),
            "listing_capture": listing_capture,
            "listing_coverage": listing_coverage,
        }

        if not payload_validation.ok:
            smoke_payload.update(
                {
                    "ok": False,
                    "output_paths": {
                        "run_manifest": str(manifest_output),
                        "smoke_report": str(report_output),
                    },
                }
            )
            _write_run_manifest_for_smoke(
                manifest_output,
                smoke_payload,
                city=args.city,
                state=args.state,
                started_at=started_at,
                started_monotonic=started_monotonic,
                run_options=run_options,
            )
            write_smoke_report(report_output, smoke_payload)
            if args.json:
                print(json.dumps(smoke_payload, indent=2, sort_keys=True))
            else:
                print(f"payload_output: {args.payload_output}")
                print(f"smoke_report: {report_output}")
                _print_payload_validation(payload_validation.to_dict())
            return 1

        if not listing_coverage["ok"]:
            smoke_payload.update(
                {
                    "ok": False,
                    "quality_skip_reason": "listing coverage did not meet min_records",
                    "output_paths": {
                        "run_manifest": str(manifest_output),
                        "smoke_report": str(report_output),
                    },
                }
            )
            _write_run_manifest_for_smoke(
                manifest_output,
                smoke_payload,
                city=args.city,
                state=args.state,
                started_at=started_at,
                started_monotonic=started_monotonic,
                run_options=run_options,
            )
            write_smoke_report(report_output, smoke_payload)
            if args.json:
                print(json.dumps(smoke_payload, indent=2, sort_keys=True))
            else:
                print(f"payload_output: {args.payload_output}")
                print(f"smoke_report: {report_output}")
                print("listing_coverage: failed")
                _print_counts(listing_coverage)
            return 1

        records, results, summary = run_fixture_pipeline(
            source="mahindra_first_choice",
            fixture_path=args.payload_output,
            captured_at=str(payload.get("captured_at") or captured_at),
            ingestion_run_id=args.run_id,
            registry_path=args.registry,
            city=args.city,
            state=args.state,
        )
        output_paths = write_fixture_outputs(
            records=records,
            results=results,
            summary=summary,
            fixture_path=args.payload_output,
            output_root=args.output_root,
            capture_date=args.capture_date,
            run_id=args.run_id,
        )
        field_profile = profile_field_completeness(source="mahindra_first_choice", records=records)
        output_path_payload = output_paths.to_dict()
        output_path_payload["run_manifest"] = str(manifest_output)
        output_path_payload["smoke_report"] = str(report_output)
        ok = _live_smoke_ok(summary) and bool(listing_coverage["ok"])
        smoke_payload.update(
            {
                "quality_summary": summary.to_dict(),
                "field_profile": field_profile.to_dict(),
                "output_paths": output_path_payload,
                "ok": ok,
            }
        )
        _write_run_manifest_for_smoke(
            manifest_output,
            smoke_payload,
            city=args.city,
            state=args.state,
            started_at=started_at,
            started_monotonic=started_monotonic,
            run_options=run_options,
        )
        write_smoke_report(report_output, smoke_payload)

        if args.json:
            print(json.dumps(smoke_payload, indent=2, sort_keys=True))
        else:
            print(f"payload_output: {args.payload_output}")
            _print_payload_validation(payload_validation.to_dict())
            print()
            _print_text_summary({**summary.to_dict(), "output_paths": output_path_payload})
            print()
            print(render_field_profile(field_profile), end="")

        return 0 if ok else 1

    if args.command == "true-value-live-smoke":
        started_at = _utc_now()
        started_monotonic = monotonic()
        captured_at = args.captured_at or _utc_now()
        min_records = _resolve_smoke_min_records(min_records=args.min_records, max_records=args.max_records)
        report_output = Path(args.report_output) if args.report_output else default_smoke_report_path(
            output_root=args.output_root,
            capture_date=args.capture_date,
            source="true_value",
            run_id=args.run_id,
        )
        manifest_output = default_run_manifest_path(
            output_root=args.output_root,
            capture_date=args.capture_date,
            source="true_value",
            run_id=args.run_id,
        )
        run_options = _true_value_live_smoke_run_options(args, min_records=min_records)
        try:
            payload = capture_true_value_listing_payload(
                source_url=args.url,
                output_path=args.payload_output,
                captured_at=captured_at,
                city=args.city,
                state=args.state,
                latitude=args.latitude,
                longitude=args.longitude,
                dealer_distance_m=args.dealer_distance_m,
                max_records=args.max_records,
                min_records=min_records,
                max_pages=args.max_pages,
                page_size=args.page_size,
                timeout_seconds=args.timeout_seconds,
                capture_attempts=args.capture_attempts,
                retry_delay_ms=args.retry_delay_ms,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        payload_validation = validate_true_value_extracted_payload(payload)
        listing_capture = summarize_true_value_listing_payload(payload)
        listing_coverage = _listing_coverage_result(listing_capture, min_records=min_records)
        smoke_payload: dict[str, object] = {
            "source": "true_value",
            "source_url": args.url,
            "run_id": args.run_id,
            "capture_date": args.capture_date,
            "captured_at": str(payload.get("captured_at") or captured_at),
            "payload_output": args.payload_output,
            "payload_validation": payload_validation.to_dict(),
            "listing_capture": listing_capture,
            "listing_coverage": listing_coverage,
        }

        if not payload_validation.ok:
            smoke_payload.update(
                {
                    "ok": False,
                    "output_paths": {
                        "run_manifest": str(manifest_output),
                        "smoke_report": str(report_output),
                    },
                }
            )
            _write_run_manifest_for_smoke(
                manifest_output,
                smoke_payload,
                city=args.city,
                state=args.state,
                started_at=started_at,
                started_monotonic=started_monotonic,
                run_options=run_options,
            )
            write_smoke_report(report_output, smoke_payload)
            if args.json:
                print(json.dumps(smoke_payload, indent=2, sort_keys=True))
            else:
                print(f"payload_output: {args.payload_output}")
                print(f"smoke_report: {report_output}")
                _print_payload_validation(payload_validation.to_dict())
            return 1

        if not listing_coverage["ok"]:
            smoke_payload.update(
                {
                    "ok": False,
                    "quality_skip_reason": "listing coverage did not meet min_records",
                    "output_paths": {
                        "run_manifest": str(manifest_output),
                        "smoke_report": str(report_output),
                    },
                }
            )
            _write_run_manifest_for_smoke(
                manifest_output,
                smoke_payload,
                city=args.city,
                state=args.state,
                started_at=started_at,
                started_monotonic=started_monotonic,
                run_options=run_options,
            )
            write_smoke_report(report_output, smoke_payload)
            if args.json:
                print(json.dumps(smoke_payload, indent=2, sort_keys=True))
            else:
                print(f"payload_output: {args.payload_output}")
                print(f"smoke_report: {report_output}")
                print("listing_coverage: failed")
                _print_counts(listing_coverage)
            return 1

        records, results, summary = run_fixture_pipeline(
            source="true_value",
            fixture_path=args.payload_output,
            captured_at=str(payload.get("captured_at") or captured_at),
            ingestion_run_id=args.run_id,
            registry_path=args.registry,
            city=args.city,
            state=args.state,
        )
        output_paths = write_fixture_outputs(
            records=records,
            results=results,
            summary=summary,
            fixture_path=args.payload_output,
            output_root=args.output_root,
            capture_date=args.capture_date,
            run_id=args.run_id,
        )
        field_profile = profile_field_completeness(source="true_value", records=records)
        output_path_payload = output_paths.to_dict()
        output_path_payload["run_manifest"] = str(manifest_output)
        output_path_payload["smoke_report"] = str(report_output)
        ok = _live_smoke_ok(summary) and bool(listing_coverage["ok"])
        smoke_payload.update(
            {
                "quality_summary": summary.to_dict(),
                "field_profile": field_profile.to_dict(),
                "output_paths": output_path_payload,
                "ok": ok,
            }
        )
        _write_run_manifest_for_smoke(
            manifest_output,
            smoke_payload,
            city=args.city,
            state=args.state,
            started_at=started_at,
            started_monotonic=started_monotonic,
            run_options=run_options,
        )
        write_smoke_report(report_output, smoke_payload)

        if args.json:
            print(json.dumps(smoke_payload, indent=2, sort_keys=True))
        else:
            print(f"payload_output: {args.payload_output}")
            _print_payload_validation(payload_validation.to_dict())
            print()
            _print_text_summary({**summary.to_dict(), "output_paths": output_path_payload})
            print()
            print(render_field_profile(field_profile), end="")

        return 0 if ok else 1

    if args.command == "spinny-live-smoke":
        started_at = _utc_now()
        started_monotonic = monotonic()
        captured_at = args.captured_at or _utc_now()
        min_records = _resolve_smoke_min_records(min_records=args.min_records, max_records=args.max_records)
        report_output = Path(args.report_output) if args.report_output else default_smoke_report_path(
            output_root=args.output_root,
            capture_date=args.capture_date,
            source="spinny",
            run_id=args.run_id,
        )
        manifest_output = default_run_manifest_path(
            output_root=args.output_root,
            capture_date=args.capture_date,
            source="spinny",
            run_id=args.run_id,
        )
        run_options = _spinny_live_smoke_run_options(args, min_records=min_records)
        try:
            payload = capture_spinny_listing_payload(
                source_url=args.url,
                output_path=args.payload_output,
                captured_at=captured_at,
                max_records=args.max_records,
                min_records=min_records,
                max_pages=args.max_pages,
                locality_fallback=args.locality,
                timeout_ms=args.timeout_ms,
                capture_attempts=args.capture_attempts,
                retry_delay_ms=args.retry_delay_ms,
                page_scroll_delay_ms=args.page_scroll_delay_ms,
                headless=not args.headful,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        payload_validation = validate_spinny_extracted_payload(payload)
        listing_capture = summarize_spinny_listing_payload(payload)
        listing_coverage = _listing_coverage_result(listing_capture, min_records=min_records)
        smoke_payload: dict[str, object] = {
            "source": "spinny",
            "source_url": args.url,
            "run_id": args.run_id,
            "capture_date": args.capture_date,
            "captured_at": str(payload.get("captured_at") or captured_at),
            "payload_output": args.payload_output,
            "payload_validation": payload_validation.to_dict(),
            "listing_capture": listing_capture,
            "listing_coverage": listing_coverage,
        }

        if not payload_validation.ok:
            smoke_payload.update(
                {
                    "ok": False,
                    "output_paths": {
                        "run_manifest": str(manifest_output),
                        "smoke_report": str(report_output),
                    },
                }
            )
            _write_run_manifest_for_smoke(
                manifest_output,
                smoke_payload,
                city=args.city,
                state=args.state,
                started_at=started_at,
                started_monotonic=started_monotonic,
                run_options=run_options,
            )
            write_smoke_report(report_output, smoke_payload)
            if args.json:
                print(json.dumps(smoke_payload, indent=2, sort_keys=True))
            else:
                print(f"payload_output: {args.payload_output}")
                print(f"smoke_report: {report_output}")
                _print_payload_validation(payload_validation.to_dict())
            return 1

        if not listing_coverage["ok"]:
            smoke_payload.update(
                {
                    "ok": False,
                    "quality_skip_reason": "listing coverage did not meet min_records",
                    "output_paths": {
                        "run_manifest": str(manifest_output),
                        "smoke_report": str(report_output),
                    },
                }
            )
            _write_run_manifest_for_smoke(
                manifest_output,
                smoke_payload,
                city=args.city,
                state=args.state,
                started_at=started_at,
                started_monotonic=started_monotonic,
                run_options=run_options,
            )
            write_smoke_report(report_output, smoke_payload)
            if args.json:
                print(json.dumps(smoke_payload, indent=2, sort_keys=True))
            else:
                print(f"payload_output: {args.payload_output}")
                print(f"smoke_report: {report_output}")
                print("listing_coverage: failed")
                _print_counts(listing_coverage)
            return 1

        pipeline_fixture_path = args.payload_output
        detail_output_path: Path | None = None
        merged_output_path: Path | None = None
        if args.detail_pages > 0:
            listing_urls = _listing_urls_from_payload(payload)[: args.detail_pages]
            if not listing_urls:
                smoke_payload.update(
                    {
                        "ok": False,
                        "detail_enrichment": {
                            "requested_records": args.detail_pages,
                            "records_total": 0,
                            "error": "no_listing_urls_available",
                        },
                        "output_paths": {
                            "run_manifest": str(manifest_output),
                            "smoke_report": str(report_output),
                        },
                    }
                )
                _write_run_manifest_for_smoke(
                    manifest_output,
                    smoke_payload,
                    city=args.city,
                    state=args.state,
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                    run_options=run_options,
                )
                write_smoke_report(report_output, smoke_payload)
                if args.json:
                    print(json.dumps(smoke_payload, indent=2, sort_keys=True))
                else:
                    print(f"payload_output: {args.payload_output}")
                    print(f"smoke_report: {report_output}")
                    print("detail_enrichment: no listing URLs available")
                return 1

            detail_output_path = (
                Path(args.detail_output)
                if args.detail_output
                else _payload_sibling_path(args.payload_output, "details")
            )
            merged_output_path = (
                Path(args.merged_output)
                if args.merged_output
                else _payload_sibling_path(args.payload_output, "enriched")
            )
            detail_payload = capture_spinny_detail_payload(
                listing_urls=listing_urls,
                output_path=detail_output_path,
                captured_at=captured_at,
                max_records=args.detail_pages,
                timeout_ms=args.timeout_ms,
                delay_ms=args.detail_delay_ms,
                attempts=args.detail_attempts,
                headless=not args.headful,
            )
            detail_summary = summarize_spinny_detail_payload(detail_payload)
            payload = merge_spinny_detail_payload_into_listing_payload(
                listing_payload=payload,
                detail_payload=detail_payload,
            )
            merged_output_path.parent.mkdir(parents=True, exist_ok=True)
            merged_output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            enriched_validation = validate_spinny_extracted_payload(payload)
            smoke_payload["enriched_payload_validation"] = enriched_validation.to_dict()
            smoke_payload["detail_enrichment"] = {
                **detail_summary,
                "detail_output": str(detail_output_path),
                "merged_output": str(merged_output_path),
            }
            pipeline_fixture_path = str(merged_output_path)

            if not detail_summary["ok"] or not enriched_validation.ok:
                smoke_payload.update(
                    {
                        "ok": False,
                        "output_paths": {
                            "detail_payload": str(detail_output_path),
                            "merged_payload": str(merged_output_path),
                            "run_manifest": str(manifest_output),
                            "smoke_report": str(report_output),
                        },
                    }
                )
                _write_run_manifest_for_smoke(
                    manifest_output,
                    smoke_payload,
                    city=args.city,
                    state=args.state,
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                    run_options=run_options,
                )
                write_smoke_report(report_output, smoke_payload)
                if args.json:
                    print(json.dumps(smoke_payload, indent=2, sort_keys=True))
                else:
                    print(f"payload_output: {args.payload_output}")
                    print(f"detail_output: {detail_output_path}")
                    print(f"merged_output: {merged_output_path}")
                    print(f"smoke_report: {report_output}")
                    if not detail_summary["ok"]:
                        print("detail_enrichment: failed")
                        _print_counts(detail_summary)
                    if not enriched_validation.ok:
                        _print_payload_validation(enriched_validation.to_dict())
                return 1

        records, results, summary = run_fixture_pipeline(
            source="spinny",
            fixture_path=pipeline_fixture_path,
            captured_at=str(payload.get("captured_at") or captured_at),
            ingestion_run_id=args.run_id,
            registry_path=args.registry,
            city=args.city,
            state=args.state,
        )
        output_paths = write_fixture_outputs(
            records=records,
            results=results,
            summary=summary,
            fixture_path=pipeline_fixture_path,
            output_root=args.output_root,
            capture_date=args.capture_date,
            run_id=args.run_id,
        )
        field_profile = profile_field_completeness(source="spinny", records=records)
        output_path_payload = output_paths.to_dict()
        if detail_output_path is not None:
            output_path_payload["detail_payload"] = str(detail_output_path)
        if merged_output_path is not None:
            output_path_payload["merged_payload"] = str(merged_output_path)
        output_path_payload["run_manifest"] = str(manifest_output)
        output_path_payload["smoke_report"] = str(report_output)
        ok = _live_smoke_ok(summary) and bool(listing_coverage["ok"])
        smoke_payload.update(
            {
                "quality_summary": summary.to_dict(),
                "field_profile": field_profile.to_dict(),
                "output_paths": output_path_payload,
                "ok": ok,
            }
        )
        _write_run_manifest_for_smoke(
            manifest_output,
            smoke_payload,
            city=args.city,
            state=args.state,
            started_at=started_at,
            started_monotonic=started_monotonic,
            run_options=run_options,
        )
        write_smoke_report(report_output, smoke_payload)

        if args.json:
            print(json.dumps(smoke_payload, indent=2, sort_keys=True))
        else:
            print(f"payload_output: {args.payload_output}")
            _print_payload_validation(payload_validation.to_dict())
            print()
            _print_text_summary({**summary.to_dict(), "output_paths": output_path_payload})
            print()
            print(render_field_profile(field_profile), end="")

        return 0 if ok else 1

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _resolve_fixture_path(source: str, fixture_path: str | None) -> str:
    if fixture_path:
        return fixture_path
    try:
        return DEFAULT_FIXTURES[source]
    except KeyError as exc:
        raise ValueError(f"Unsupported fixture source: {source}") from exc


def _write_json(path: str | Path, payload: object) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def _load_json_object(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _spinny_incremental_manifest_output_paths(
    *,
    output_root: str | Path,
    run_id: str,
    capture_date: str,
    listing_payload: str,
    detail_plan: str,
    detail_payload: str,
    quality_summary: str,
    raw_output: str | None,
    silver_output: str | None,
    quarantine_output: str | None,
    merged_payload: str | None,
    new_detail_payload: str | None,
) -> dict[str, str]:
    root = Path(output_root)
    paths = {
        "listing_payload": listing_payload,
        "detail_plan": detail_plan,
        "detail_payload": detail_payload,
        "raw": raw_output
        or str(
            root
            / "raw"
            / "source=spinny"
            / f"capture_date={capture_date}"
            / f"run_id={run_id}"
            / "fixture_source_payload.json"
        ),
        "silver": silver_output
        or str(root / "silver" / "listings" / f"capture_date={capture_date}" / f"spinny_{run_id}_silver.json"),
        "quarantine": quarantine_output
        or str(
            root
            / "silver"
            / "quarantine"
            / "source=spinny"
            / f"capture_date={capture_date}"
            / f"{run_id}_quarantine.json"
        ),
        "quality_summary": quality_summary,
    }
    if merged_payload:
        paths["merged_payload"] = merged_payload
    if new_detail_payload:
        paths["new_detail_payload"] = new_detail_payload
    return paths


def _print_text_summary(summary: dict[str, object]) -> None:
    print(f"source: {summary['source']}")
    print(f"records_total: {summary['records_total']}")
    print(f"silver_valid: {summary['silver_valid']}")
    print(f"pricing_ready: {summary['pricing_ready']}")
    print(f"quarantined: {summary['quarantined']}")
    print(f"required_completeness_avg: {summary['required_completeness_avg']}")
    print(f"high_value_completeness_avg: {summary['high_value_completeness_avg']}")
    print(f"optional_completeness_avg: {summary['optional_completeness_avg']}")
    print(f"overall_completeness_avg: {summary['overall_completeness_avg']}")
    print("quarantine_reasons:")
    _print_counts(summary["quarantine_reasons"])
    print("warnings:")
    _print_counts(summary["warnings"])
    if "output_paths" in summary:
        print("output_paths:")
        for key, value in dict(summary["output_paths"]).items():
            print(f"  {key}: {value}")


def _print_counts(counts: object) -> None:
    if not counts:
        print("  none")
        return
    for key, value in dict(counts).items():
        print(f"  {key}: {value}")


def _print_payload_validation(result: dict[str, object]) -> None:
    print(f"source: {result['source']}")
    print(f"records_total: {result['records_total']}")
    print(f"ok: {result['ok']}")
    print("failures:")
    failures = list(result["failures"])
    if not failures:
        print("  none")
        return
    for failure in failures:
        failure_dict = dict(failure)
        print(
            "  "
            f"record={failure_dict['record_index'] or 'payload'} "
            f"field={failure_dict['field_name']} "
            f"reason={failure_dict['reason']}"
        )


def _live_smoke_ok(summary: object) -> bool:
    return (
        getattr(summary, "records_total") > 0
        and getattr(summary, "records_total") == getattr(summary, "pricing_ready")
        and getattr(summary, "quarantined") == 0
        and getattr(summary, "required_completeness_avg") == 1.0
    )


def _resolve_smoke_min_records(*, min_records: int | None, max_records: int) -> int:
    if min_records is None:
        return max(0, max_records)
    return max(0, min_records)


def _listing_coverage_result(listing_capture: dict[str, object], *, min_records: int) -> dict[str, object]:
    records_total = int(listing_capture.get("records_total") or 0)
    min_records = max(0, min_records)
    source_total = int(listing_capture.get("source_total_items") or 0)
    if source_total > 0 and source_total < min_records and records_total >= source_total:
        return {
            "ok": True,
            "min_records": min_records,
            "records_total": records_total,
            "missing_records": 0,
            "source_total_items": source_total,
            "reason": "source_total_below_minimum",
        }
    ok = records_total >= min_records
    return {
        "ok": ok,
        "min_records": min_records,
        "records_total": records_total,
        "missing_records": max(0, min_records - records_total),
        "source_total_items": source_total,
        "reason": "ok" if ok else "records_below_minimum",
    }


def _spinny_live_smoke_run_options(args: argparse.Namespace, *, min_records: int) -> dict[str, object]:
    return {
        "city": args.city,
        "state": args.state,
        "max_pages": args.max_pages,
        "max_records": args.max_records,
        "min_records": min_records,
        "capture_attempts": args.capture_attempts,
        "retry_delay_ms": args.retry_delay_ms,
        "page_scroll_delay_ms": args.page_scroll_delay_ms,
        "timeout_ms": args.timeout_ms,
        "detail_pages": args.detail_pages,
        "detail_attempts": args.detail_attempts,
        "detail_delay_ms": args.detail_delay_ms,
        "headful": bool(args.headful),
    }


def _mfc_live_smoke_run_options(args: argparse.Namespace, *, min_records: int) -> dict[str, object]:
    return {
        "city": args.city,
        "state": args.state,
        "max_pages": args.max_pages,
        "max_records": args.max_records,
        "min_records": min_records,
        "capture_attempts": args.capture_attempts,
        "retry_delay_ms": args.retry_delay_ms,
        "page_scroll_delay_ms": args.page_scroll_delay_ms,
        "timeout_ms": args.timeout_ms,
        "detail_pages": 0,
        "headful": bool(args.headful),
    }


def _true_value_live_smoke_run_options(args: argparse.Namespace, *, min_records: int) -> dict[str, object]:
    return {
        "city": args.city,
        "state": args.state,
        "latitude": args.latitude,
        "longitude": args.longitude,
        "dealer_distance_m": args.dealer_distance_m,
        "max_pages": args.max_pages,
        "page_size": args.page_size,
        "max_records": args.max_records,
        "min_records": min_records,
        "capture_attempts": args.capture_attempts,
        "retry_delay_ms": args.retry_delay_ms,
        "timeout_seconds": args.timeout_seconds,
        "detail_pages": 0,
    }


def _write_run_manifest_for_smoke(
    path: str | Path,
    smoke_payload: dict[str, object],
    *,
    city: str,
    state: str,
    started_at: str,
    started_monotonic: float,
    run_options: dict[str, object],
) -> Path:
    completed_at = _utc_now()
    manifest = build_run_manifest(
        smoke_result=smoke_payload,
        city=city,
        state=state,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=monotonic() - started_monotonic,
        run_options=run_options,
    )
    return write_run_manifest(path, manifest)


def _listing_urls_from_payload(payload: dict[str, object]) -> list[str]:
    urls = []
    for record in list(payload.get("records", [])):
        if not isinstance(record, dict):
            continue
        raw = record.get("raw")
        if not isinstance(raw, dict):
            continue
        listing_url = raw.get("listing_url")
        if isinstance(listing_url, str) and listing_url:
            urls.append(listing_url)
    return list(dict.fromkeys(urls))


def _payload_sibling_path(payload_path: str, suffix: str) -> Path:
    path = Path(payload_path)
    return path.with_name(f"{path.stem}_{suffix}{path.suffix}")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    sys.exit(main())
