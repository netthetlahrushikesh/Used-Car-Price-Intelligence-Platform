"""Collection ledger reports from selected run manifests."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


LEDGER_INCLUDED_JOB_STATUSES = {"pass", "skipped_passed", "no_inventory"}
LEDGER_INCLUDED_ROW_STATUSES = {"pass", "no_inventory"}


def build_collection_ledger(
    *,
    collection_id: str,
    batch_manifest_paths: list[str | Path] | None = None,
    source_manifest_paths: list[str | Path] | None = None,
    output_root: str | Path = "data",
    generated_at: str | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen_run_keys: set[tuple[str, str]] = set()
    output_root_path = Path(output_root)

    for source_manifest_path in source_manifest_paths or []:
        manifest = _load_json(source_manifest_path)
        row = _row_from_source_manifest(
            manifest=manifest,
            manifest_path=Path(source_manifest_path),
            manifest_type="source_run",
        )
        _append_row(rows, row, seen_run_keys)

    for batch_manifest_path in batch_manifest_paths or []:
        batch_manifest = _load_json(batch_manifest_path)
        for result in list(batch_manifest.get("job_results") or []):
            if not isinstance(result, dict) or not _is_passing_job_result(result):
                continue
            source = str(result.get("source") or "")
            run_id = str(result.get("resumed_from_run_id") or result.get("run_id") or "")
            source_manifest_path = _find_source_manifest(
                output_root=output_root_path,
                source=source,
                run_id=run_id,
                preferred_capture_date=str(batch_manifest.get("capture_date") or ""),
            )
            if source_manifest_path is None:
                row = _missing_source_manifest_row(
                    batch_manifest=batch_manifest,
                    batch_manifest_path=Path(batch_manifest_path),
                    result=result,
                    run_id=run_id,
                )
            else:
                source_manifest = _load_json(source_manifest_path)
                row = _row_from_source_manifest(
                    manifest=source_manifest,
                    manifest_path=source_manifest_path,
                    manifest_type="batch_job",
                    batch_manifest=batch_manifest,
                    batch_manifest_path=Path(batch_manifest_path),
                    job_result=result,
                )
            _append_row(rows, row, seen_run_keys)

    rows.sort(key=lambda row: (row["source"], row["city"], row["capture_date"], row["run_id"]))
    return {
        "collection_id": collection_id,
        "generated_at": generated_at or _utc_now(),
        "rows": rows,
        "totals": _totals(rows),
    }


def render_collection_ledger_markdown(ledger: dict[str, Any]) -> str:
    rows = list(ledger.get("rows") or [])
    totals = dict(ledger.get("totals") or {})
    lines = [
        "# Collection Ledger",
        "",
        f"Collection id: `{ledger.get('collection_id', '')}`",
        f"Generated at: `{ledger.get('generated_at', '')}`",
        "",
        "## Totals",
        "",
        f"- Pricing-ready rows: {totals.get('pricing_ready', 0)}",
        f"- Quarantined rows: {totals.get('quarantined', 0)}",
        f"- Source runs: {totals.get('source_runs', 0)}",
        "",
        "## By Source",
        "",
        "| Source | Runs | Pricing Ready | Quarantined | Source Total Signal |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for source, source_total in sorted(dict(totals.get("by_source") or {}).items()):
        lines.append(
            "| {source} | {runs} | {pricing_ready} | {quarantined} | {source_total_signal} |".format(
                source=source,
                runs=source_total.get("source_runs", 0),
                pricing_ready=source_total.get("pricing_ready", 0),
                quarantined=source_total.get("quarantined", 0),
                source_total_signal=source_total.get("source_total_signal", 0),
            )
        )

    lines.extend(
        [
            "",
            "## Runs",
            "",
            "| Source | City | Capture Date | Status | Pricing Ready | Quarantined | Source Total | Coverage | Required | High Value | Run ID |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| {source} | {city} | {capture_date} | {status} | {pricing_ready} | {quarantined} | "
            "{source_total_items} | {coverage_reason} | {required} | {high_value} | `{run_id}` |".format(
                source=row["source"],
                city=row["city"],
                capture_date=row["capture_date"],
                status=row["status"],
                pricing_ready=row["pricing_ready"],
                quarantined=row["quarantined"],
                source_total_items=row["source_total_items"],
                coverage_reason=row["coverage_reason"],
                required=_format_percent(row.get("required_completeness_avg")),
                high_value=_format_percent(row.get("high_value_completeness_avg")),
                run_id=row["run_id"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_collection_ledger_json(path: str | Path, ledger: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def write_collection_ledger_markdown(path: str | Path, ledger: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_collection_ledger_markdown(ledger), encoding="utf-8")
    return output_path


def _row_from_source_manifest(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    manifest_type: str,
    batch_manifest: dict[str, Any] | None = None,
    batch_manifest_path: Path | None = None,
    job_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality = _as_dict(manifest.get("quality_summary"))
    listing_capture = _as_dict(manifest.get("listing_capture"))
    listing_coverage = _as_dict(manifest.get("listing_coverage"))
    row_status = str(manifest.get("status") or "")
    if job_result is not None and str(job_result.get("status") or "") == "no_inventory":
        row_status = "no_inventory"
    row = {
        "manifest_type": manifest_type,
        "source": str(manifest.get("source") or ""),
        "run_id": str(manifest.get("run_id") or ""),
        "status": row_status,
        "capture_date": str(manifest.get("capture_date") or ""),
        "city": str(manifest.get("city") or ""),
        "state": str(manifest.get("state") or ""),
        "source_url": str(manifest.get("source_url") or ""),
        "pricing_ready": int(quality.get("pricing_ready") or 0),
        "quarantined": int(quality.get("quarantined") or 0),
        "records_total": int(quality.get("records_total") or 0),
        "source_total_items": int(listing_capture.get("source_total_items") or 0),
        "coverage_reason": str(listing_coverage.get("reason") or ""),
        "required_completeness_avg": quality.get("required_completeness_avg"),
        "high_value_completeness_avg": quality.get("high_value_completeness_avg"),
        "optional_completeness_avg": quality.get("optional_completeness_avg"),
        "overall_completeness_avg": quality.get("overall_completeness_avg"),
        "duration_seconds": manifest.get("duration_seconds"),
        "manifest_path": str(manifest_path),
    }
    if batch_manifest is not None and job_result is not None:
        row["batch_run_id"] = str(batch_manifest.get("batch_run_id") or "")
        row["batch_id"] = str(job_result.get("batch_id") or "")
        row["job_status"] = str(job_result.get("status") or "")
        row["batch_manifest_path"] = str(batch_manifest_path or "")
    return row


def _missing_source_manifest_row(
    *,
    batch_manifest: dict[str, Any],
    batch_manifest_path: Path,
    result: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    return {
        "manifest_type": "batch_job_missing_source_manifest",
        "source": str(result.get("source") or ""),
        "run_id": run_id,
        "status": "missing_source_manifest",
        "capture_date": str(batch_manifest.get("capture_date") or ""),
        "city": "",
        "state": "",
        "source_url": "",
        "pricing_ready": 0,
        "quarantined": 0,
        "records_total": 0,
        "source_total_items": 0,
        "coverage_reason": "",
        "required_completeness_avg": None,
        "high_value_completeness_avg": None,
        "optional_completeness_avg": None,
        "overall_completeness_avg": None,
        "duration_seconds": None,
        "manifest_path": "",
        "batch_run_id": str(batch_manifest.get("batch_run_id") or ""),
        "batch_id": str(result.get("batch_id") or ""),
        "job_status": str(result.get("status") or ""),
        "batch_manifest_path": str(batch_manifest_path),
    }


def _append_row(rows: list[dict[str, Any]], row: dict[str, Any], seen: set[tuple[str, str]]) -> None:
    if row["status"] not in LEDGER_INCLUDED_ROW_STATUSES:
        return
    key = (row["source"], row["run_id"])
    if key in seen:
        return
    seen.add(key)
    rows.append(row)


def _is_passing_job_result(result: dict[str, Any]) -> bool:
    return str(result.get("status") or "") in LEDGER_INCLUDED_JOB_STATUSES and result.get("exit_code") == 0


def _find_source_manifest(
    *,
    output_root: Path,
    source: str,
    run_id: str,
    preferred_capture_date: str,
) -> Path | None:
    candidates = []
    if preferred_capture_date:
        candidates.append(
            output_root
            / "gold"
            / "acquisition_runs"
            / f"capture_date={preferred_capture_date}"
            / f"{source}_{run_id}_manifest.json"
        )
    root = output_root / "gold" / "acquisition_runs"
    if root.exists():
        candidates.extend(root.glob(f"capture_date=*/{source}_{run_id}_manifest.json"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, dict[str, int]] = {}
    for row in rows:
        source = str(row["source"])
        source_totals = by_source.setdefault(
            source,
            {
                "source_runs": 0,
                "pricing_ready": 0,
                "quarantined": 0,
                "source_total_signal": 0,
            },
        )
        source_totals["source_runs"] += 1
        source_totals["pricing_ready"] += int(row["pricing_ready"])
        source_totals["quarantined"] += int(row["quarantined"])
        source_totals["source_total_signal"] += int(row["source_total_items"])
    return {
        "source_runs": len(rows),
        "pricing_ready": sum(int(row["pricing_ready"]) for row in rows),
        "quarantined": sum(int(row["quarantined"]) for row in rows),
        "source_total_signal": sum(int(row["source_total_items"]) for row in rows),
        "by_source": by_source,
    }


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest must be a JSON object: {path}")
    return payload


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _format_percent(value: object) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "n/a"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
