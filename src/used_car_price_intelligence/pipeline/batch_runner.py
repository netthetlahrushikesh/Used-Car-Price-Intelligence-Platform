"""Plan and run controlled source-city acquisition batches."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic
from typing import Any

import yaml


BATCH_MANIFEST_VERSION = "batch_run_manifest_v0.1"
PASSING_JOB_STATUSES = {"pass", "skipped_passed", "no_inventory"}


@dataclass(frozen=True)
class BatchJob:
    batch_id: str
    source: str
    status: str
    city: str
    state: str
    url: str
    run_id: str
    capture_date: str
    payload_output: str
    command: list[str]
    output_root: str = "data"
    allow_zero_inventory: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BatchJobResult:
    batch_id: str
    source: str
    run_id: str
    status: str
    exit_code: int | None
    duration_seconds: float
    command: list[str]
    stdout_tail: str = ""
    stderr_tail: str = ""
    skip_reason: str = ""
    resumed_from_run_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BatchRunPlan:
    batch_run_id: str
    capture_date: str
    config_path: str
    jobs: list[BatchJob]

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_run_id": self.batch_run_id,
            "capture_date": self.capture_date,
            "config_path": self.config_path,
            "jobs": [job.to_dict() for job in self.jobs],
        }


def build_batch_run_plan(
    *,
    config_path: str | Path = "config/acquisition_batches.yml",
    capture_date: str,
    batch_run_id: str,
    output_root: str | Path = "data",
    batch_ids: list[str] | None = None,
    statuses: list[str] | None = None,
    python_executable: str | None = None,
) -> BatchRunPlan:
    config = _load_config(config_path)
    defaults = dict(config.get("defaults") or {})
    selected_batches = _select_batches(
        batches=list(config.get("batches") or []),
        batch_ids=batch_ids,
        statuses=statuses,
    )
    executable = python_executable or sys.executable
    jobs = [
        _batch_job_from_config(
            batch=dict(batch),
            defaults=defaults,
            capture_date=capture_date,
            batch_run_id=batch_run_id,
            output_root=Path(output_root),
            python_executable=executable,
        )
        for batch in selected_batches
    ]
    return BatchRunPlan(
        batch_run_id=batch_run_id,
        capture_date=capture_date,
        config_path=str(config_path),
        jobs=jobs,
    )


def run_batch_plan(
    plan: BatchRunPlan,
    *,
    execute: bool = False,
    cwd: str | Path | None = None,
    skip_passed_jobs: dict[str, dict[str, Any]] | None = None,
    resume_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    started_at = _utc_now()
    started = monotonic()
    results = []
    skip_passed_jobs = skip_passed_jobs or {}
    for job in plan.jobs:
        job_started = monotonic()
        prior_pass = skip_passed_jobs.get(job.batch_id)
        if prior_pass is not None:
            results.append(
                BatchJobResult(
                    batch_id=job.batch_id,
                    source=job.source,
                    run_id=job.run_id,
                    status="skipped_passed",
                    exit_code=0,
                    duration_seconds=0.0,
                    command=job.command,
                    skip_reason="passed_in_resume_manifest",
                    resumed_from_run_id=str(
                        prior_pass.get("resumed_from_run_id") or prior_pass.get("run_id") or ""
                    ),
                )
            )
            continue

        if not execute:
            results.append(
                BatchJobResult(
                    batch_id=job.batch_id,
                    source=job.source,
                    run_id=job.run_id,
                    status="planned",
                    exit_code=None,
                    duration_seconds=0.0,
                    command=job.command,
                )
            )
            continue

        completed = subprocess.run(
            job.command,
            cwd=str(cwd) if cwd is not None else None,
            text=True,
            capture_output=True,
            check=False,
        )
        result_status = "pass" if completed.returncode == 0 else "fail"
        result_exit_code = completed.returncode
        if completed.returncode != 0 and job.allow_zero_inventory and _job_reported_zero_inventory(job, cwd=cwd):
            result_status = "no_inventory"
            result_exit_code = 0

        results.append(
            BatchJobResult(
                batch_id=job.batch_id,
                source=job.source,
                run_id=job.run_id,
                status=result_status,
                exit_code=result_exit_code,
                duration_seconds=round(monotonic() - job_started, 3),
                command=job.command,
                stdout_tail=_tail(completed.stdout),
                stderr_tail=_tail(completed.stderr),
            )
        )
        if result_status == "fail":
            break

    completed_at = _utc_now()
    return {
        "manifest_version": BATCH_MANIFEST_VERSION,
        "batch_run_id": plan.batch_run_id,
        "capture_date": plan.capture_date,
        "status": _batch_status(results, execute=execute),
        "execute": execute,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": round(monotonic() - started, 3),
        "job_count": len(plan.jobs),
        "jobs_executed": sum(1 for result in results if result.status in {"pass", "fail", "no_inventory"}),
        "jobs_skipped": sum(1 for result in results if result.status == "skipped_passed"),
        "resume_manifest": str(resume_manifest_path) if resume_manifest_path else "",
        "jobs_planned": [job.to_dict() for job in plan.jobs],
        "job_results": [result.to_dict() for result in results],
    }


def default_batch_manifest_path(
    *,
    output_root: str | Path,
    capture_date: str,
    batch_run_id: str,
) -> Path:
    return (
        Path(output_root)
        / "gold"
        / "batch_runs"
        / f"capture_date={capture_date}"
        / f"{batch_run_id}_batch_manifest.json"
    )


def write_batch_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def load_batch_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise ValueError(f"Batch manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"Batch manifest must be a JSON object: {manifest_path}")
    return manifest


def passed_jobs_from_manifest(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    passed: dict[str, dict[str, Any]] = {}
    for result in list(manifest.get("job_results") or []):
        if not isinstance(result, dict):
            continue
        status = str(result.get("status") or "")
        exit_code = result.get("exit_code")
        if status not in PASSING_JOB_STATUSES or exit_code != 0:
            continue
        batch_id = str(result.get("batch_id") or "")
        if not batch_id:
            continue
        passed[batch_id] = result
    return passed


def default_batch_summary_path(
    *,
    output_root: str | Path,
    capture_date: str,
    batch_run_id: str,
) -> Path:
    return (
        Path(output_root)
        / "gold"
        / "batch_runs"
        / f"capture_date={capture_date}"
        / f"{batch_run_id}_batch_summary.md"
    )


def write_batch_summary_report(path: str | Path, report: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def render_batch_summary_report(
    manifest: dict[str, Any],
    *,
    output_root: str | Path = "data",
    cwd: str | Path | None = None,
) -> str:
    planned_by_id = {
        str(job.get("batch_id")): job
        for job in list(manifest.get("jobs_planned") or [])
        if isinstance(job, dict)
    }
    rows = []
    source_totals: dict[str, dict[str, int]] = {}
    for result in list(manifest.get("job_results") or []):
        if not isinstance(result, dict):
            continue
        batch_id = str(result.get("batch_id") or "")
        planned = planned_by_id.get(batch_id, {})
        source = str(result.get("source") or planned.get("source") or "")
        run_id = str(result.get("resumed_from_run_id") or result.get("run_id") or "")
        source_manifest = _load_source_manifest(
            output_root=output_root,
            capture_date=str(manifest.get("capture_date") or ""),
            source=source,
            run_id=run_id,
            cwd=cwd,
        )
        row = _summary_row(result=result, planned=planned, source_manifest=source_manifest)
        rows.append(row)
        totals = source_totals.setdefault(source, {"pricing_ready": 0, "quarantined": 0})
        totals["pricing_ready"] += row["pricing_ready_value"]
        totals["quarantined"] += row["quarantined_value"]

    lines = [
        "# Batch Run Summary",
        "",
        f"Batch run id: `{manifest.get('batch_run_id', '')}`",
        f"Capture date: `{manifest.get('capture_date', '')}`",
        f"Status: `{manifest.get('status', '')}`",
        f"Execute: `{manifest.get('execute', False)}`",
        f"Jobs planned: `{manifest.get('job_count', 0)}`",
        f"Jobs executed: `{manifest.get('jobs_executed', 0)}`",
        f"Jobs skipped: `{manifest.get('jobs_skipped', 0)}`",
    ]
    if manifest.get("resume_manifest"):
        lines.append(f"Resume manifest: `{manifest.get('resume_manifest')}`")
    lines.extend(
        [
            "",
            "## Jobs",
            "",
            "| Batch | Source | City | Status | Pricing Ready | Quarantined | Required | High Value | Source Total | Runtime |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        lines.append(
            "| {batch_id} | {source} | {city} | {status} | {pricing_ready} | "
            "{quarantined} | {required} | {high_value} | {source_total} | {runtime} |".format(
                **row
            )
        )

    lines.extend(["", "## Source Totals", ""])
    lines.append("| Source | Pricing Ready | Quarantined |")
    lines.append("| --- | ---: | ---: |")
    for source, totals in sorted(source_totals.items()):
        lines.append(f"| {source} | {totals['pricing_ready']} | {totals['quarantined']} |")
    lines.append("")
    return "\n".join(lines)


def _batch_job_from_config(
    *,
    batch: dict[str, Any],
    defaults: dict[str, Any],
    capture_date: str,
    batch_run_id: str,
    output_root: Path,
    python_executable: str,
) -> BatchJob:
    merged = {**defaults, **batch}
    source = str(merged["source"])
    batch_id = str(merged["batch_id"])
    run_id = f"run_{capture_date.replace('-', '')}_{batch_id}_{batch_run_id}"
    payload_output = str(output_root / "tmp" / f"{run_id}_payload.json")
    command = _source_command(
        source=source,
        options=merged,
        capture_date=capture_date,
        run_id=run_id,
        payload_output=payload_output,
        output_root=str(output_root),
        python_executable=python_executable,
    )
    return BatchJob(
        batch_id=batch_id,
        source=source,
        status=str(merged.get("status") or "unknown"),
        city=str(merged.get("city") or ""),
        state=str(merged.get("state") or ""),
        url=str(merged.get("url") or ""),
        run_id=run_id,
        capture_date=capture_date,
        payload_output=payload_output,
        command=command,
        output_root=str(output_root),
        allow_zero_inventory=bool(merged.get("allow_zero_inventory", False)),
    )


def _source_command(
    *,
    source: str,
    options: dict[str, Any],
    capture_date: str,
    run_id: str,
    payload_output: str,
    output_root: str,
    python_executable: str,
) -> list[str]:
    if source == "spinny":
        return _spinny_command(
            options=options,
            capture_date=capture_date,
            run_id=run_id,
            payload_output=payload_output,
            output_root=output_root,
            python_executable=python_executable,
        )
    if source == "mahindra_first_choice":
        return _mfc_command(
            options=options,
            capture_date=capture_date,
            run_id=run_id,
            payload_output=payload_output,
            output_root=output_root,
            python_executable=python_executable,
        )
    if source == "true_value":
        return _true_value_command(
            options=options,
            capture_date=capture_date,
            run_id=run_id,
            payload_output=payload_output,
            output_root=output_root,
            python_executable=python_executable,
        )
    raise ValueError(f"Unsupported batch source: {source}")


def _spinny_command(
    *,
    options: dict[str, Any],
    capture_date: str,
    run_id: str,
    payload_output: str,
    output_root: str,
    python_executable: str,
) -> list[str]:
    command = _base_smoke_command(
        python_executable=python_executable,
        command_name="spinny-live-smoke",
        options=options,
        payload_output=payload_output,
        run_id=run_id,
        capture_date=capture_date,
        output_root=output_root,
    )
    command.extend(
        [
            "--locality",
            str(options.get("locality") or options.get("city") or ""),
            "--max-pages",
            str(_int_option(options, "max_pages")),
            "--max-records",
            str(_int_option(options, "max_records")),
            "--min-records",
            str(_int_option(options, "min_records")),
            "--capture-attempts",
            str(_int_option(options, "capture_attempts")),
            "--retry-delay-ms",
            str(_int_option(options, "retry_delay_ms")),
            "--page-scroll-delay-ms",
            str(_int_option(options, "page_scroll_delay_ms")),
            "--timeout-ms",
            str(_int_option(options, "timeout_ms")),
            "--detail-pages",
            str(_int_option(options, "detail_pages")),
            "--detail-attempts",
            str(_int_option(options, "detail_attempts")),
            "--detail-delay-ms",
            str(_int_option(options, "detail_delay_ms")),
            "--json",
        ]
    )
    return command


def _mfc_command(
    *,
    options: dict[str, Any],
    capture_date: str,
    run_id: str,
    payload_output: str,
    output_root: str,
    python_executable: str,
) -> list[str]:
    command = _base_smoke_command(
        python_executable=python_executable,
        command_name="mfc-live-smoke",
        options=options,
        payload_output=payload_output,
        run_id=run_id,
        capture_date=capture_date,
        output_root=output_root,
    )
    command.extend(
        [
            "--max-pages",
            str(_int_option(options, "max_pages")),
            "--max-records",
            str(_int_option(options, "max_records")),
            "--min-records",
            str(_int_option(options, "min_records")),
            "--capture-attempts",
            str(_int_option(options, "capture_attempts")),
            "--retry-delay-ms",
            str(_int_option(options, "retry_delay_ms")),
            "--page-scroll-delay-ms",
            str(_int_option(options, "page_scroll_delay_ms")),
            "--timeout-ms",
            str(_int_option(options, "timeout_ms")),
            "--json",
        ]
    )
    return command


def _true_value_command(
    *,
    options: dict[str, Any],
    capture_date: str,
    run_id: str,
    payload_output: str,
    output_root: str,
    python_executable: str,
) -> list[str]:
    command = _base_smoke_command(
        python_executable=python_executable,
        command_name="true-value-live-smoke",
        options=options,
        payload_output=payload_output,
        run_id=run_id,
        capture_date=capture_date,
        output_root=output_root,
    )
    command.extend(
        [
            "--latitude",
            str(options["latitude"]),
            "--longitude",
            str(options["longitude"]),
            "--dealer-distance-m",
            str(_int_option(options, "dealer_distance_m")),
            "--max-pages",
            str(_int_option(options, "max_pages")),
            "--page-size",
            str(_int_option(options, "page_size")),
            "--max-records",
            str(_int_option(options, "max_records")),
            "--min-records",
            str(_int_option(options, "min_records")),
            "--capture-attempts",
            str(_int_option(options, "capture_attempts")),
            "--retry-delay-ms",
            str(_int_option(options, "retry_delay_ms")),
            "--timeout-seconds",
            str(_int_option(options, "timeout_seconds")),
            "--json",
        ]
    )
    return command


def _base_smoke_command(
    *,
    python_executable: str,
    command_name: str,
    options: dict[str, Any],
    payload_output: str,
    run_id: str,
    capture_date: str,
    output_root: str,
) -> list[str]:
    return [
        python_executable,
        "-m",
        "used_car_price_intelligence.cli",
        command_name,
        "--url",
        str(options["url"]),
        "--payload-output",
        payload_output,
        "--run-id",
        run_id,
        "--capture-date",
        capture_date,
        "--output-root",
        output_root,
        "--city",
        str(options["city"]),
        "--state",
        str(options["state"]),
    ]


def _select_batches(
    *,
    batches: list[dict[str, Any]],
    batch_ids: list[str] | None,
    statuses: list[str] | None,
) -> list[dict[str, Any]]:
    if batch_ids:
        requested = set(batch_ids)
        selected = [batch for batch in batches if str(batch.get("batch_id")) in requested]
        missing = sorted(requested - {str(batch.get("batch_id")) for batch in selected})
        if missing:
            raise ValueError(f"Unknown batch_id values: {', '.join(missing)}")
        return selected

    selected_statuses = set(statuses or ["validated"])
    return [batch for batch in batches if str(batch.get("status")) in selected_statuses]


def _load_config(config_path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Batch config must be a YAML object: {config_path}")
    return payload


def _int_option(options: dict[str, Any], key: str) -> int:
    return int(options[key])


def _batch_status(results: list[BatchJobResult], *, execute: bool) -> str:
    if not execute:
        return "planned"
    if not results:
        return "empty"
    if all(result.exit_code == 0 for result in results):
        return "pass"
    return "fail"


def _job_reported_zero_inventory(job: BatchJob, *, cwd: str | Path | None) -> bool:
    manifest = _load_source_manifest(
        output_root=job.output_root,
        capture_date=job.capture_date,
        source=job.source,
        run_id=job.run_id,
        cwd=cwd,
    )
    if not manifest:
        return False
    listing_capture = manifest.get("listing_capture")
    if not isinstance(listing_capture, dict):
        return False

    records_total = int(listing_capture.get("records_total") or 0)
    source_total = int(listing_capture.get("source_total_items") or 0)
    stop_reason = str(listing_capture.get("stop_reason") or "")
    failure_stop_reasons = {
        "capture_attempt_failed",
        "capture_not_attempted",
        "unknown",
    }
    return records_total == 0 and source_total == 0 and stop_reason not in failure_stop_reasons


def _tail(value: str, *, max_chars: int = 2000) -> str:
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def _load_source_manifest(
    *,
    output_root: str | Path,
    capture_date: str,
    source: str,
    run_id: str,
    cwd: str | Path | None,
) -> dict[str, Any]:
    if not source or not run_id:
        return {}
    path = (
        Path(output_root)
        / "gold"
        / "acquisition_runs"
        / f"capture_date={capture_date}"
        / f"{source}_{run_id}_manifest.json"
    )
    if cwd is not None and not path.is_absolute():
        path = Path(cwd) / path
    if not path.exists():
        return {}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return manifest if isinstance(manifest, dict) else {}


def _summary_row(
    *,
    result: dict[str, Any],
    planned: dict[str, Any],
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    quality = source_manifest.get("quality_summary") if source_manifest else {}
    listing_capture = source_manifest.get("listing_capture") if source_manifest else {}
    if not isinstance(quality, dict):
        quality = {}
    if not isinstance(listing_capture, dict):
        listing_capture = {}

    pricing_ready = int(quality.get("pricing_ready") or 0)
    quarantined = int(quality.get("quarantined") or 0)
    return {
        "batch_id": str(result.get("batch_id") or planned.get("batch_id") or ""),
        "source": str(result.get("source") or planned.get("source") or ""),
        "city": str(planned.get("city") or source_manifest.get("city") or ""),
        "status": str(result.get("status") or ""),
        "pricing_ready": str(pricing_ready) if quality else "n/a",
        "pricing_ready_value": pricing_ready,
        "quarantined": str(quarantined) if quality else "n/a",
        "quarantined_value": quarantined,
        "required": _format_ratio(quality.get("required_completeness_avg")) if quality else "n/a",
        "high_value": _format_ratio(quality.get("high_value_completeness_avg")) if quality else "n/a",
        "source_total": _format_optional_int(listing_capture.get("source_total_items")),
        "runtime": _format_seconds(source_manifest.get("duration_seconds")),
    }


def _format_ratio(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "n/a"


def _format_seconds(value: Any) -> str:
    try:
        return f"{float(value):.3f}s"
    except (TypeError, ValueError):
        return "n/a"


def _format_optional_int(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "n/a"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
