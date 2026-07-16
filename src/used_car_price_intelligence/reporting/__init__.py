"""Reporting utilities for local data quality runs."""

from used_car_price_intelligence.reporting.field_profile import (
    FieldCompleteness,
    FieldProfileReport,
    profile_field_completeness,
    render_field_profile,
)
from used_car_price_intelligence.reporting.quality_report import (
    load_quality_summary,
    render_quality_report,
)
from used_car_price_intelligence.reporting.source_comparison import (
    SourceRunProfile,
    load_source_run_profile,
    render_multi_source_comparison_report,
    render_source_comparison_report,
    write_source_comparison_report,
)
from used_car_price_intelligence.reporting.collection_ledger import (
    build_collection_ledger,
    render_collection_ledger_markdown,
    write_collection_ledger_json,
    write_collection_ledger_markdown,
)
from used_car_price_intelligence.reporting.listing_lifecycle import (
    build_listing_lifecycle_index,
    render_listing_lifecycle_markdown,
    write_listing_lifecycle_json,
    write_listing_lifecycle_markdown,
)
from used_car_price_intelligence.reporting.snapshot_diff import (
    build_snapshot_diff,
    render_snapshot_diff_markdown,
    write_snapshot_diff_json,
    write_snapshot_diff_markdown,
)
from used_car_price_intelligence.reporting.snapshot_manifest import (
    build_snapshot_manifest,
    render_snapshot_manifest_markdown,
    write_snapshot_manifest_json,
    write_snapshot_manifest_markdown,
)
from used_car_price_intelligence.reporting.scale_projection import (
    build_scale_projection,
    render_scale_projection_markdown,
    write_scale_projection_json,
    write_scale_projection_markdown,
)
from used_car_price_intelligence.reporting.remaining_gap_strategy import (
    build_remaining_gap_strategy,
    render_remaining_gap_strategy_markdown,
    write_remaining_gap_strategy_json,
    write_remaining_gap_strategy_markdown,
)
from used_car_price_intelligence.reporting.modeling_dataset import (
    build_baseline_model_report,
    build_eda_summary,
    build_modeling_data_dictionary,
    build_modeling_dataset_package,
    render_baseline_model_markdown,
    render_data_dictionary_markdown,
    render_dataset_manifest_markdown,
    render_eda_summary_markdown,
    write_modeling_dataset_package,
)
from used_car_price_intelligence.reporting.smoke_report import (
    default_smoke_report_path,
    render_smoke_report,
    write_smoke_report,
)

__all__ = [
    "FieldCompleteness",
    "FieldProfileReport",
    "SourceRunProfile",
    "build_collection_ledger",
    "build_baseline_model_report",
    "build_eda_summary",
    "build_listing_lifecycle_index",
    "build_modeling_data_dictionary",
    "build_modeling_dataset_package",
    "build_remaining_gap_strategy",
    "build_scale_projection",
    "build_snapshot_diff",
    "build_snapshot_manifest",
    "default_smoke_report_path",
    "load_source_run_profile",
    "load_quality_summary",
    "profile_field_completeness",
    "render_collection_ledger_markdown",
    "render_baseline_model_markdown",
    "render_data_dictionary_markdown",
    "render_dataset_manifest_markdown",
    "render_eda_summary_markdown",
    "render_field_profile",
    "render_listing_lifecycle_markdown",
    "render_multi_source_comparison_report",
    "render_quality_report",
    "render_remaining_gap_strategy_markdown",
    "render_scale_projection_markdown",
    "render_snapshot_diff_markdown",
    "render_snapshot_manifest_markdown",
    "render_source_comparison_report",
    "write_collection_ledger_json",
    "write_collection_ledger_markdown",
    "write_listing_lifecycle_json",
    "write_listing_lifecycle_markdown",
    "write_modeling_dataset_package",
    "write_remaining_gap_strategy_json",
    "write_remaining_gap_strategy_markdown",
    "write_scale_projection_json",
    "write_scale_projection_markdown",
    "write_snapshot_diff_json",
    "write_snapshot_diff_markdown",
    "write_snapshot_manifest_json",
    "write_snapshot_manifest_markdown",
    "render_smoke_report",
    "write_source_comparison_report",
    "write_smoke_report",
]
