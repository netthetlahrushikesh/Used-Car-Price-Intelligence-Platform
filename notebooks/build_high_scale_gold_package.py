"""Build the high-scale gold dataset package from discovered run manifests."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from used_car_price_intelligence.reporting import (
    build_collection_ledger,
    build_listing_lifecycle_index,
    build_modeling_dataset_package,
    build_snapshot_manifest,
    write_collection_ledger_json,
    write_collection_ledger_markdown,
    write_listing_lifecycle_json,
    write_listing_lifecycle_markdown,
    write_modeling_dataset_package,
    write_snapshot_manifest_json,
    write_snapshot_manifest_markdown,
)


PACKAGE_ID = "20260627_100k_observation_run"
ROUND_BATCH_PREFIX = "batch_20260627_high_scale_r"
SPINNY_MANIFEST_GLOB = "spinny_run_20260627_spinny_*_card100_high_scale*_manifest.json"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    generated_at = utc_now()

    batch_manifests = discover_batch_manifests(root=root, capture_date=args.capture_date)
    source_manifests = discover_spinny_manifests(root=root, capture_date=args.capture_date)
    if not batch_manifests and not source_manifests:
        raise SystemExit("No high-scale manifests found to package.")

    collection_id = f"trusted_collection_v12_{PACKAGE_ID}"
    lifecycle_id = f"listing_lifecycle_v10_{PACKAGE_ID}"
    snapshot_id = f"snapshot_{PACKAGE_ID}"
    dataset_id = f"{snapshot_id}_modeling_v0"

    ledger_path = root / "data" / "gold" / "collection_ledger" / f"{collection_id}.json"
    lifecycle_path = root / "data" / "gold" / "listing_lifecycle" / f"{lifecycle_id}.json"
    snapshot_path = root / "data" / "gold" / "snapshots" / f"{snapshot_id}_manifest.json"
    export_dir = root / "data" / "gold" / "exports" / snapshot_id
    modeling_dir = root / "data" / "gold" / "modeling" / dataset_id

    ledger = build_collection_ledger(
        collection_id=collection_id,
        batch_manifest_paths=batch_manifests,
        source_manifest_paths=source_manifests,
        output_root=root / "data",
        generated_at=generated_at,
    )
    write_collection_ledger_json(ledger_path, ledger)
    write_collection_ledger_markdown(ledger_path.with_suffix(".md"), ledger)

    export_paths = write_observation_exports(
        root=root,
        ledger=ledger,
        export_dir=export_dir,
        snapshot_id=snapshot_id,
    )

    lifecycle = build_listing_lifecycle_index(
        lifecycle_id=lifecycle_id,
        collection_ledger_path=ledger_path,
        generated_at=generated_at,
    )
    write_listing_lifecycle_json(lifecycle_path, lifecycle)
    write_listing_lifecycle_markdown(lifecycle_path.with_suffix(".md"), lifecycle)

    status = "pass" if int(ledger["totals"]["pricing_ready"]) >= args.target_pricing_ready else "target_pending"
    snapshot = build_snapshot_manifest(
        snapshot_id=snapshot_id,
        snapshot_date=args.capture_date,
        collection_ledger_path=ledger_path,
        lifecycle_index_path=lifecycle_path,
        status=status,
        target_pricing_ready=args.target_pricing_ready,
        previous_snapshot_id="snapshot_20260627_high_scale_round1",
        previous_lifecycle_id="listing_lifecycle_v8_20260627_high_scale_round1",
        scope_change_vs_previous=(
            "Repeated trusted-source high-scale observations. Observation-level export keeps repeated "
            "snapshots; modeling package collapses to latest listing key."
        ),
        generated_at=generated_at,
    )
    snapshot.setdefault("paths", {})
    snapshot["paths"].update(export_paths)
    write_snapshot_manifest_json(snapshot_path, snapshot)
    write_snapshot_manifest_markdown(snapshot_path.with_suffix(".md"), snapshot)

    package = build_modeling_dataset_package(
        snapshot_manifest_path=snapshot_path,
        lifecycle_index_path=lifecycle_path,
        dataset_id=dataset_id,
        generated_at=generated_at,
    )
    modeling_paths = write_modeling_dataset_package(output_dir=modeling_dir, package=package)

    summary = build_summary(
        ledger=ledger,
        lifecycle=lifecycle,
        snapshot=snapshot,
        batch_manifests=batch_manifests,
        source_manifests=source_manifests,
        export_paths=export_paths,
        modeling_paths=modeling_paths,
    )
    summary_path = export_dir / "package_summary.json"
    summary_md_path = export_dir / "package_summary.md"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_md_path.write_text(render_summary_markdown(summary), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.require_target and int(ledger["totals"]["pricing_ready"]) < args.target_pricing_ready:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Package high-scale gold observations and modeling dataset.")
    parser.add_argument("--capture-date", default="2026-06-27")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--target-pricing-ready", type=int, default=100_000)
    parser.add_argument("--require-target", action="store_true")
    return parser


def discover_batch_manifests(*, root: Path, capture_date: str) -> list[Path]:
    batch_dir = root / "data" / "gold" / "batch_runs" / f"capture_date={capture_date}"
    if not batch_dir.exists():
        return []
    selected: list[Path] = []
    explicit = [
        "batch_20260627_high_scale_true_value_resume1_batch_manifest.json",
        "batch_20260627_high_scale_mfc_execute_batch_manifest.json",
    ]
    for name in explicit:
        path = batch_dir / name
        if path.exists():
            selected.append(path)
    for path in sorted(batch_dir.glob(f"{ROUND_BATCH_PREFIX}*_batch_manifest.json")):
        name = path.name
        if "_retry" in name:
            continue
        if "_true_value_" in name or "_mfc_" in name:
            selected.append(path)
    return unique_paths(selected)


def discover_spinny_manifests(*, root: Path, capture_date: str) -> list[Path]:
    manifest_dir = root / "data" / "gold" / "acquisition_runs" / f"capture_date={capture_date}"
    if not manifest_dir.exists():
        return []
    return unique_paths(sorted(manifest_dir.glob(SPINNY_MANIFEST_GLOB)))


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    output: list[Path] = []
    for path in paths:
        key = path.resolve().as_posix()
        if key in seen:
            continue
        seen.add(key)
        output.append(path)
    return output


def write_observation_exports(
    *,
    root: Path,
    ledger: dict[str, Any],
    export_dir: Path,
    snapshot_id: str,
) -> dict[str, str]:
    export_dir.mkdir(parents=True, exist_ok=True)
    records = load_observation_records(root=root, ledger=ledger)
    jsonl_path = export_dir / f"{snapshot_id}_pricing_ready_observations.jsonl"
    csv_path = export_dir / f"{snapshot_id}_pricing_ready_observations.csv"
    metadata_path = export_dir / f"{snapshot_id}_observation_export_metadata.json"

    columns = sorted({key for record in records for key in record})
    preferred = [
        "source",
        "ingestion_run_id",
        "capture_date",
        "captured_at",
        "city",
        "state",
        "brand",
        "model",
        "variant",
        "model_year",
        "fuel_type",
        "transmission",
        "km_driven",
        "ownership",
        "registration_code",
        "listed_price_inr",
        "listing_url",
        "source_listing_id",
    ]
    columns = [column for column in preferred if column in columns] + [
        column for column in columns if column not in preferred
    ]

    with jsonl_path.open("w", encoding="utf-8") as file_obj:
        for record in records:
            file_obj.write(json.dumps(record, sort_keys=True) + "\n")

    with csv_path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({column: csv_value(record.get(column)) for column in columns})

    metadata = {
        "snapshot_id": snapshot_id,
        "records_total": len(records),
        "columns": columns,
        "source": "collection_ledger_pass_rows",
        "policy": (
            "Observation-level export includes repeated snapshots. Use the modeling package for one latest "
            "row per listing key."
        ),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "observation_dataset_csv": csv_path.as_posix(),
        "observation_dataset_jsonl": jsonl_path.as_posix(),
        "observation_export_metadata": metadata_path.as_posix(),
    }


def load_observation_records(*, root: Path, ledger: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in ledger.get("rows") or []:
        if not isinstance(row, dict) or row.get("status") != "pass":
            continue
        manifest_path = resolve_path(root=root, value=row.get("manifest_path"))
        if manifest_path is None:
            continue
        manifest = load_json(manifest_path)
        output_paths = manifest.get("output_paths")
        if not isinstance(output_paths, dict):
            continue
        silver_path = resolve_path(root=root, value=output_paths.get("silver"))
        if silver_path is None:
            continue
        silver_records = json.loads(silver_path.read_text(encoding="utf-8"))
        if not isinstance(silver_records, list):
            continue
        for record in silver_records:
            if isinstance(record, dict):
                records.append(record)
    return records


def resolve_path(*, root: Path, value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    candidates = [path] if path.is_absolute() else [path, root / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def build_summary(
    *,
    ledger: dict[str, Any],
    lifecycle: dict[str, Any],
    snapshot: dict[str, Any],
    batch_manifests: list[Path],
    source_manifests: list[Path],
    export_paths: dict[str, str],
    modeling_paths: dict[str, str],
) -> dict[str, Any]:
    totals = dict(snapshot.get("totals") or {})
    return {
        "snapshot_id": snapshot.get("snapshot_id"),
        "status": snapshot.get("status"),
        "pricing_ready_observations": totals.get("pricing_ready", 0),
        "unique_listing_keys": totals.get("unique_listing_keys", 0),
        "rows_under_target": totals.get("rows_under_target", 0),
        "rows_over_target": totals.get("rows_over_target", 0),
        "source_runs": totals.get("source_runs", 0),
        "listing_source_runs": totals.get("listing_source_runs", 0),
        "no_inventory_source_runs": totals.get("no_inventory_source_runs", 0),
        "by_source": totals.get("by_source", {}),
        "reobserved_listing_groups": dict(lifecycle.get("totals") or {}).get("reobserved_listing_groups", 0),
        "inputs": {
            "batch_manifests": [path.as_posix() for path in batch_manifests],
            "source_manifests": [path.as_posix() for path in source_manifests],
        },
        "outputs": {
            "collection_ledger": snapshot.get("paths", {}).get("collection_ledger"),
            "lifecycle_index": snapshot.get("paths", {}).get("lifecycle_index"),
            "snapshot_manifest": f"data/gold/snapshots/{snapshot.get('snapshot_id')}_manifest.json",
            **export_paths,
            **modeling_paths,
        },
        "policy": {
            "observation_export": "All pricing-ready observations from successful source runs, including repeats.",
            "modeling_dataset": "Latest deduped row per lifecycle listing key.",
        },
    }


def render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# High-Scale Gold Package",
        "",
        f"Snapshot id: `{summary.get('snapshot_id', '')}`",
        f"Status: `{summary.get('status', '')}`",
        "",
        "## Totals",
        "",
        f"- Pricing-ready observations: {summary.get('pricing_ready_observations', 0):,}",
        f"- Unique listing keys: {summary.get('unique_listing_keys', 0):,}",
        f"- Source runs: {summary.get('source_runs', 0):,}",
        f"- Listing source runs: {summary.get('listing_source_runs', 0):,}",
        f"- No-inventory source runs: {summary.get('no_inventory_source_runs', 0):,}",
        f"- Rows under target: {summary.get('rows_under_target', 0):,}",
        f"- Rows over target: {summary.get('rows_over_target', 0):,}",
        "",
        "## By Source",
        "",
        "| Source | Runs | Listing Runs | Pricing Ready | Quarantined |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for source, item in sorted(dict(summary.get("by_source") or {}).items()):
        lines.append(
            "| {source} | {source_runs} | {listing_source_runs} | {pricing_ready} | {quarantined} |".format(
                source=source,
                source_runs=item.get("source_runs", 0),
                listing_source_runs=item.get("listing_source_runs", 0),
                pricing_ready=item.get("pricing_ready", 0),
                quarantined=item.get("quarantined", 0),
            )
        )
    outputs = dict(summary.get("outputs") or {})
    lines.extend(["", "## Key Outputs", ""])
    for key in [
        "observation_dataset_csv",
        "dataset_csv",
        "eda_summary_markdown",
        "baseline_model_markdown",
        "dataset_manifest_markdown",
    ]:
        if outputs.get(key):
            lines.append(f"- {key}: `{outputs[key]}`")
    lines.append("")
    return "\n".join(lines)


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
