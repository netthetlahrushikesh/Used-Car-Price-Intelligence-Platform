"""Render persisted reports for live source smoke runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def default_smoke_report_path(
    *,
    output_root: str | Path,
    capture_date: str,
    source: str,
    run_id: str,
) -> Path:
    return (
        Path(output_root)
        / "gold"
        / "smoke_reports"
        / f"capture_date={capture_date}"
        / f"{source}_{run_id}_smoke_report.md"
    )


def write_smoke_report(path: str | Path, smoke_result: dict[str, Any]) -> Path:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_smoke_report(smoke_result), encoding="utf-8")
    return report_path


def render_smoke_report(smoke_result: dict[str, Any]) -> str:
    source = str(smoke_result.get("source", "unknown"))
    payload_validation = _as_dict(smoke_result.get("payload_validation"))
    listing_capture = _as_dict(smoke_result.get("listing_capture"))
    listing_coverage = _as_dict(smoke_result.get("listing_coverage"))
    detail_enrichment = _as_dict(smoke_result.get("detail_enrichment"))
    quality_summary = _as_dict(smoke_result.get("quality_summary"))
    field_profile = _as_dict(smoke_result.get("field_profile"))
    output_paths = _as_dict(smoke_result.get("output_paths"))
    ok = bool(smoke_result.get("ok", False))

    lines = [
        "# Live Source Smoke Report",
        "",
        f"Status: {'PASS' if ok else 'FAIL'}",
        f"Source: {source}",
        f"Run ID: {smoke_result.get('run_id', 'unknown')}",
        f"Captured At: {smoke_result.get('captured_at', 'unknown')}",
        f"Source URL: {smoke_result.get('source_url', 'unknown')}",
        f"Payload Output: {smoke_result.get('payload_output', 'unknown')}",
        "",
        "Payload Contract:",
        f"- ok: {payload_validation.get('ok', False)}",
        f"- records_total: {payload_validation.get('records_total', 0)}",
        "Payload Failures:",
        *_format_failures(payload_validation.get("failures", [])),
    ]

    if listing_capture:
        lines.extend(
            [
                "",
                "Listing Capture:",
                f"- pagination_type: {listing_capture.get('pagination_type', 'unknown')}",
                f"- max_pages: {listing_capture.get('max_pages', 0)}",
                f"- attempted_pages: {listing_capture.get('attempted_pages', 0)}",
                f"- max_records: {listing_capture.get('max_records', 0)}",
                f"- min_records: {listing_capture.get('min_records', 0)}",
                f"- coverage_ok: {listing_capture.get('coverage_ok', False)}",
                f"- records_total: {listing_capture.get('records_total', 0)}",
                f"- unique_cards_seen: {listing_capture.get('unique_cards_seen', 0)}",
                f"- duplicate_cards_skipped: {listing_capture.get('duplicate_cards_skipped', 0)}",
                f"- stop_reason: {listing_capture.get('stop_reason', 'unknown')}",
            ]
        )

    if listing_coverage:
        lines.extend(
            [
                "",
                "Listing Coverage:",
                f"- ok: {listing_coverage.get('ok', False)}",
                f"- min_records: {listing_coverage.get('min_records', 0)}",
                f"- records_total: {listing_coverage.get('records_total', 0)}",
                f"- missing_records: {listing_coverage.get('missing_records', 0)}",
                f"- reason: {listing_coverage.get('reason', 'unknown')}",
            ]
        )

    if detail_enrichment:
        lines.extend(
            [
                "",
                "Detail Enrichment:",
                f"- ok: {detail_enrichment.get('ok', False)}",
                f"- requested_records: {detail_enrichment.get('requested_records', 0)}",
                f"- attempted_records: {detail_enrichment.get('attempted_records', 0)}",
                f"- records_total: {detail_enrichment.get('records_total', 0)}",
                f"- successful_records: {detail_enrichment.get('successful_records', 0)}",
                f"- failed_records: {detail_enrichment.get('failed_records', 0)}",
                f"- ownership_records: {detail_enrichment.get('ownership_records', 0)}",
                f"- retries_used: {detail_enrichment.get('retries_used', 0)}",
                f"- timeout_count: {detail_enrichment.get('timeout_count', 0)}",
                f"- empty_raw_count: {detail_enrichment.get('empty_raw_count', 0)}",
            ]
        )
        if detail_enrichment.get("error"):
            lines.append(f"- error: {detail_enrichment['error']}")

    if quality_summary:
        lines.extend(
            [
                "",
                "Quality Gates:",
                (
                    "- records: "
                    f"{quality_summary.get('records_total', 0)} total | "
                    f"{quality_summary.get('silver_valid', 0)} silver-valid | "
                    f"{quality_summary.get('pricing_ready', 0)} pricing-ready | "
                    f"{quality_summary.get('quarantined', 0)} quarantined"
                ),
                f"- required completeness: {_format_percent(quality_summary.get('required_completeness_avg', 0))}",
                f"- high-value completeness: {_format_percent(quality_summary.get('high_value_completeness_avg', 0))}",
                f"- optional completeness: {_format_percent(quality_summary.get('optional_completeness_avg', 0))}",
                f"- overall completeness: {_format_percent(quality_summary.get('overall_completeness_avg', 0))}",
                "Quarantine Reasons:",
                *_format_counts(quality_summary.get("quarantine_reasons", {})),
                "Warnings:",
                *_format_counts(quality_summary.get("warnings", {})),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Quality Gates:",
                f"- skipped: {smoke_result.get('quality_skip_reason', 'payload contract did not pass')}",
            ]
        )

    if field_profile:
        lines.extend(
            [
                "",
                "Field Gaps:",
                "Required fields below 100%:",
                *_format_field_gaps(field_profile, "required"),
                "High-value fields below 100%:",
                *_format_field_gaps(field_profile, "high_value"),
            ]
        )

    if output_paths:
        lines.extend(["", "Output Paths:", *_format_counts(output_paths)])

    return "\n".join(lines) + "\n"


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _format_failures(failures: object) -> list[str]:
    if not failures:
        return ["- none"]
    if not isinstance(failures, list):
        return ["- invalid failure payload"]

    lines = []
    for failure in failures[:10]:
        if not isinstance(failure, dict):
            lines.append("- invalid failure entry")
            continue
        lines.append(
            "- "
            f"record={failure.get('record_index') or 'payload'} "
            f"field={failure.get('field_name', 'unknown')} "
            f"reason={failure.get('reason', 'unknown')}"
        )

    omitted_count = len(failures) - len(lines)
    if omitted_count > 0:
        lines.append(f"- {omitted_count} more failure(s) omitted")
    return lines


def _format_field_gaps(field_profile: dict[str, Any], group: str) -> list[str]:
    fields = field_profile.get("fields", [])
    if not isinstance(fields, list):
        return ["- invalid field profile"]

    gaps = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        if field.get("field_group") != group:
            continue
        completeness = float(field.get("completeness", 0) or 0)
        if completeness >= 1.0:
            continue
        gaps.append(
            "- "
            f"{field.get('field_name', 'unknown')}: "
            f"{field.get('present_count', 0)}/{field.get('total_count', 0)} "
            f"({_format_percent(completeness)})"
        )

    return gaps or ["- none"]


def _format_counts(counts: object) -> list[str]:
    if not counts:
        return ["- none"]
    if not isinstance(counts, dict):
        return ["- invalid counts payload"]
    return [f"- {key}: {counts[key]}" for key in sorted(counts)]


def _format_percent(value: object) -> str:
    return f"{float(value) * 100:.2f}%"
