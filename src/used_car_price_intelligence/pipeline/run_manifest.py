"""Persist compact acquisition run manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MANIFEST_VERSION = "acquisition_run_manifest_v0.1"


def default_run_manifest_path(
    *,
    output_root: str | Path,
    capture_date: str,
    source: str,
    run_id: str,
) -> Path:
    return (
        Path(output_root)
        / "gold"
        / "acquisition_runs"
        / f"capture_date={capture_date}"
        / f"{source}_{run_id}_manifest.json"
    )


def build_run_manifest(
    *,
    smoke_result: dict[str, Any],
    city: str,
    state: str,
    started_at: str,
    completed_at: str,
    duration_seconds: float,
    run_options: dict[str, Any],
) -> dict[str, Any]:
    output_paths = _as_dict(smoke_result.get("output_paths"))
    quality_summary = _as_dict(smoke_result.get("quality_summary"))
    detail_enrichment = _as_dict(smoke_result.get("detail_enrichment"))
    listing_capture = _as_dict(smoke_result.get("listing_capture"))
    listing_coverage = _as_dict(smoke_result.get("listing_coverage"))

    return {
        "manifest_version": MANIFEST_VERSION,
        "status": "pass" if smoke_result.get("ok") else "fail",
        "source": smoke_result.get("source", "unknown"),
        "source_url": smoke_result.get("source_url", "unknown"),
        "city": city,
        "state": state,
        "run_id": smoke_result.get("run_id", "unknown"),
        "capture_date": smoke_result.get("capture_date", "unknown"),
        "captured_at": smoke_result.get("captured_at", "unknown"),
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": round(duration_seconds, 3),
        "run_options": run_options,
        "record_counts": {
            "payload_records": _as_dict(smoke_result.get("payload_validation")).get("records_total", 0),
            "listing_records": listing_capture.get("records_total", 0),
            "pricing_ready": quality_summary.get("pricing_ready", 0),
            "quarantined": quality_summary.get("quarantined", 0),
            "detail_requested": detail_enrichment.get("requested_records", 0),
            "detail_successful": detail_enrichment.get("successful_records", 0),
            "detail_failed": detail_enrichment.get("failed_records", 0),
        },
        "listing_capture": listing_capture,
        "listing_coverage": listing_coverage,
        "detail_enrichment": detail_enrichment,
        "quality_summary": quality_summary,
        "output_paths": output_paths,
    }


def build_incremental_detail_run_manifest(
    *,
    source: str,
    source_url: str,
    city: str,
    state: str,
    run_id: str,
    capture_date: str,
    captured_at: str,
    started_at: str,
    completed_at: str,
    duration_seconds: float | None,
    run_options: dict[str, Any],
    listing_capture: dict[str, Any],
    listing_coverage: dict[str, Any],
    detail_plan: dict[str, Any],
    detail_enrichment: dict[str, Any],
    quality_summary: dict[str, Any],
    output_paths: dict[str, Any],
) -> dict[str, Any]:
    """Build an acquisition manifest for two-step listing/detail enrichment runs."""

    return {
        "manifest_version": MANIFEST_VERSION,
        "status": _incremental_detail_status(
            listing_capture=listing_capture,
            listing_coverage=listing_coverage,
            detail_enrichment=detail_enrichment,
            quality_summary=quality_summary,
        ),
        "source": source,
        "source_url": source_url,
        "city": city,
        "state": state,
        "run_id": run_id,
        "capture_date": capture_date,
        "captured_at": captured_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": None if duration_seconds is None else round(duration_seconds, 3),
        "run_options": run_options,
        "record_counts": {
            "payload_records": int(quality_summary.get("records_total") or 0),
            "listing_records": int(listing_capture.get("records_total") or 0),
            "pricing_ready": int(quality_summary.get("pricing_ready") or 0),
            "quarantined": int(quality_summary.get("quarantined") or 0),
            "detail_requested": int(detail_plan.get("unique_listing_urls") or 0),
            "detail_attempted": int(detail_enrichment.get("attempted_records") or 0),
            "detail_successful": int(detail_enrichment.get("successful_records") or 0),
            "detail_failed": int(detail_enrichment.get("failed_records") or 0),
            "detail_cache_hits": int(detail_plan.get("cache_hit_count") or 0),
            "detail_pending_before_capture": int(detail_plan.get("pending_count") or 0),
            "detail_selected_new": int(detail_plan.get("selected_new_count") or 0),
            "detail_skipped_over_new_cap": int(detail_plan.get("skipped_over_new_cap") or 0),
            "detail_missing_after_merge": int(
                _as_dict(detail_enrichment.get("incremental_policy")).get("missing_after_merge") or 0
            ),
            "detail_cache_reused": int(
                _as_dict(detail_enrichment.get("incremental_policy")).get("cache_reused_records") or 0
            ),
            "detail_new_records_used": int(
                _as_dict(detail_enrichment.get("incremental_policy")).get("new_records_used") or 0
            ),
        },
        "listing_capture": listing_capture,
        "listing_coverage": listing_coverage,
        "detail_plan": detail_plan,
        "detail_enrichment": detail_enrichment,
        "quality_summary": quality_summary,
        "output_paths": output_paths,
    }


def write_run_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _incremental_detail_status(
    *,
    listing_capture: dict[str, Any],
    listing_coverage: dict[str, Any],
    detail_enrichment: dict[str, Any],
    quality_summary: dict[str, Any],
) -> str:
    listing_records = int(listing_capture.get("records_total") or 0)
    quality_records = int(quality_summary.get("records_total") or 0)
    pricing_ready = int(quality_summary.get("pricing_ready") or 0)
    quarantined = int(quality_summary.get("quarantined") or 0)
    detail_failed = int(detail_enrichment.get("failed_records") or 0)
    if listing_records <= 0:
        return "fail"
    if not bool(listing_coverage.get("ok", True)):
        return "fail"
    if quality_records != listing_records:
        return "fail"
    if pricing_ready != listing_records:
        return "fail"
    if quarantined:
        return "fail"
    if detail_failed:
        return "fail"
    return "pass"
