"""Snapshot manifest builder from trusted collection artifacts."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


SNAPSHOT_MANIFEST_VERSION = "snapshot_manifest_v0.1"


def build_snapshot_manifest(
    *,
    snapshot_id: str,
    snapshot_date: str,
    collection_ledger_path: str | Path,
    lifecycle_index_path: str | Path,
    snapshot_diff_path: str | Path | None = None,
    status: str = "pass",
    target_pricing_ready: int | None = None,
    previous_snapshot_id: str = "",
    previous_lifecycle_id: str = "",
    scope_change_vs_previous: str = "",
    extra_metadata_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ledger_path = Path(collection_ledger_path)
    lifecycle_path = Path(lifecycle_index_path)
    diff_path = Path(snapshot_diff_path) if snapshot_diff_path else None
    ledger = _load_json(ledger_path)
    lifecycle = _load_json(lifecycle_path)
    diff = _load_json(diff_path) if diff_path else None
    extra = _load_json(Path(extra_metadata_path)) if extra_metadata_path else {}

    totals = _build_totals(ledger=ledger, lifecycle=lifecycle, target_pricing_ready=target_pricing_ready)
    validation = _validate_inputs(ledger=ledger, lifecycle=lifecycle, diff=diff, totals=totals)

    manifest: dict[str, Any] = {
        "manifest_version": SNAPSHOT_MANIFEST_VERSION,
        "snapshot_id": snapshot_id,
        "snapshot_date": snapshot_date,
        "generated_at": generated_at or _utc_now(),
        "status": status,
        "collection_id": str(ledger.get("collection_id") or lifecycle.get("collection_id") or ""),
        "lifecycle_id": str(lifecycle.get("lifecycle_id") or ""),
        "previous_snapshot_id": previous_snapshot_id,
        "previous_lifecycle_id": previous_lifecycle_id,
        "paths": _build_paths(
            ledger_path=ledger_path,
            lifecycle_path=lifecycle_path,
            diff_path=diff_path,
            metadata_path=Path(extra_metadata_path) if extra_metadata_path else None,
            extra_paths=_as_dict(extra.get("paths")),
        ),
        "scope": _build_scope(ledger=ledger, scope_change_vs_previous=scope_change_vs_previous, extra_scope=extra.get("scope")),
        "totals": totals,
        "validation": validation,
        "policy": _build_policy(extra.get("policy")),
    }
    if diff is not None:
        manifest["diff_vs_previous"] = _diff_summary(diff)
    if extra:
        manifest = _merge_extra_metadata(manifest, extra)
    return manifest


def render_snapshot_manifest_markdown(manifest: dict[str, Any]) -> str:
    totals = dict(manifest.get("totals") or {})
    scope = dict(manifest.get("scope") or {})
    validation = dict(manifest.get("validation") or {})
    lines = [
        "# Snapshot Manifest",
        "",
        f"Snapshot id: `{manifest.get('snapshot_id', '')}`",
        f"Snapshot date: `{manifest.get('snapshot_date', '')}`",
        f"Status: `{manifest.get('status', '')}`",
        f"Collection id: `{manifest.get('collection_id', '')}`",
        f"Lifecycle id: `{manifest.get('lifecycle_id', '')}`",
        "",
        "## Totals",
        "",
        f"- Pricing-ready rows: {totals.get('pricing_ready', 0):,}",
        f"- Quarantined rows: {totals.get('quarantined', 0):,}",
        f"- Unique listing keys: {totals.get('unique_listing_keys', 0):,}",
        f"- Ledger source-city rows: {totals.get('source_runs', 0):,}",
        f"- Listing-producing source runs: {totals.get('listing_source_runs', 0):,}",
        f"- No-inventory source runs: {totals.get('no_inventory_source_runs', 0):,}",
    ]
    if "target_pricing_ready" in totals:
        lines.append(f"- Target pricing-ready rows: {totals.get('target_pricing_ready', 0):,}")
    if "rows_under_target" in totals:
        lines.append(f"- Rows under target: {totals.get('rows_under_target', 0):,}")
    if "rows_over_target" in totals:
        lines.append(f"- Rows over target: {totals.get('rows_over_target', 0):,}")

    lines.extend(
        [
            "",
            "## By Source",
            "",
            "| Source | Source Runs | Listing Runs | No Inventory | Pricing Ready | Quarantined | Source Total Signal |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for source, item in sorted(dict(totals.get("by_source") or {}).items()):
        lines.append(
            "| {source} | {source_runs} | {listing_source_runs} | {no_inventory_source_runs} | "
            "{pricing_ready} | {quarantined} | {source_total_signal} |".format(
                source=source,
                source_runs=item.get("source_runs", 0),
                listing_source_runs=item.get("listing_source_runs", 0),
                no_inventory_source_runs=item.get("no_inventory_source_runs", 0),
                pricing_ready=item.get("pricing_ready", 0),
                quarantined=item.get("quarantined", 0),
                source_total_signal=item.get("source_total_signal", 0),
            )
        )

    lines.extend(["", "## Scope", ""])
    lines.append(f"- Sources: {', '.join(scope.get('sources') or [])}")
    lines.append(f"- Cities: {len(scope.get('cities') or [])}")
    if scope.get("scope_change_vs_previous"):
        lines.append(f"- Scope change: {scope.get('scope_change_vs_previous')}")

    diff = manifest.get("diff_vs_previous")
    if isinstance(diff, dict):
        lines.extend(
            [
                "",
                "## Diff Vs Previous",
                "",
                f"- Previous unique listing keys: {diff.get('previous_unique_listing_keys', 0):,}",
                f"- Current unique listing keys: {diff.get('current_unique_listing_keys', 0):,}",
                f"- Added listings: {diff.get('added_count', 0):,}",
                f"- Removed listings: {diff.get('removed_count', 0):,}",
                f"- Still-active listings: {diff.get('still_active_count', 0):,}",
                f"- Price changes: {diff.get('price_change_count', 0):,}",
                f"- Km changes: {diff.get('km_change_count', 0):,}",
            ]
        )

    lines.extend(["", "## Validation", ""])
    lines.append(f"- Status: {validation.get('status', '')}")
    for check in validation.get("checks") or []:
        if isinstance(check, dict):
            lines.append(f"- {check.get('name', '')}: {check.get('status', '')}")
    lines.append("")
    return "\n".join(lines)


def write_snapshot_manifest_json(path: str | Path, manifest: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def write_snapshot_manifest_markdown(path: str | Path, manifest: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_snapshot_manifest_markdown(manifest), encoding="utf-8")
    return output_path


def _build_totals(
    *,
    ledger: dict[str, Any],
    lifecycle: dict[str, Any],
    target_pricing_ready: int | None,
) -> dict[str, Any]:
    ledger_rows = [row for row in ledger.get("rows") or [] if isinstance(row, dict)]
    ledger_totals = _as_dict(ledger.get("totals"))
    lifecycle_totals = _as_dict(lifecycle.get("totals"))
    pricing_ready = _int_value(ledger_totals.get("pricing_ready"))
    quarantined = _int_value(ledger_totals.get("quarantined"))
    source_total_signal = _int_value(ledger_totals.get("source_total_signal"))
    source_runs = _int_value(ledger_totals.get("source_runs")) or len(ledger_rows)
    no_inventory_source_runs = sum(1 for row in ledger_rows if str(row.get("status") or "") == "no_inventory")
    listing_source_runs = sum(1 for row in ledger_rows if str(row.get("status") or "") == "pass")

    totals: dict[str, Any] = {
        "source_runs": source_runs,
        "listing_source_runs": listing_source_runs,
        "pricing_ready": pricing_ready,
        "quarantined": quarantined,
        "unique_listing_keys": _int_value(lifecycle_totals.get("unique_listing_keys")),
        "source_total_signal": source_total_signal,
        "no_inventory_source_runs": no_inventory_source_runs,
        "possible_vehicle_duplicate_groups": _int_value(lifecycle_totals.get("possible_vehicle_duplicate_groups")),
        "by_source": _by_source_from_rows(ledger_rows),
    }
    if target_pricing_ready is not None:
        target = int(target_pricing_ready)
        totals["target_pricing_ready"] = target
        if pricing_ready < target:
            totals["rows_under_target"] = target - pricing_ready
        elif pricing_ready > target:
            totals["rows_over_target"] = pricing_ready - target
        else:
            totals["rows_at_target"] = 0
    return totals


def _by_source_from_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "source_runs": 0,
            "listing_source_runs": 0,
            "pricing_ready": 0,
            "quarantined": 0,
            "source_total_signal": 0,
            "no_inventory_source_runs": 0,
        }
    )
    for row in rows:
        source = str(row.get("source") or "")
        if not source:
            continue
        item = totals[source]
        item["source_runs"] += 1
        item["pricing_ready"] += _int_value(row.get("pricing_ready"))
        item["quarantined"] += _int_value(row.get("quarantined"))
        item["source_total_signal"] += _int_value(row.get("source_total_items"))
        if str(row.get("status") or "") == "no_inventory":
            item["no_inventory_source_runs"] += 1
        elif str(row.get("status") or "") == "pass":
            item["listing_source_runs"] += 1
    return {source: dict(item) for source, item in sorted(totals.items())}


def _build_paths(
    *,
    ledger_path: Path,
    lifecycle_path: Path,
    diff_path: Path | None,
    metadata_path: Path | None,
    extra_paths: dict[str, Any],
) -> dict[str, str]:
    paths = {key: str(value) for key, value in extra_paths.items() if value}
    paths.update(
        {
            "collection_ledger": _path_text(ledger_path),
            "lifecycle_index": _path_text(lifecycle_path),
        }
    )
    ledger_md = ledger_path.with_suffix(".md")
    lifecycle_md = lifecycle_path.with_suffix(".md")
    if ledger_md.exists():
        paths["collection_ledger_markdown"] = _path_text(ledger_md)
    if lifecycle_md.exists():
        paths["lifecycle_markdown"] = _path_text(lifecycle_md)
    if diff_path is not None:
        paths["snapshot_diff_json"] = _path_text(diff_path)
        diff_md = diff_path.with_suffix(".md")
        if diff_md.exists():
            paths["snapshot_diff_markdown"] = _path_text(diff_md)
    if metadata_path is not None:
        paths["snapshot_metadata"] = _path_text(metadata_path)
    return paths


def _build_scope(*, ledger: dict[str, Any], scope_change_vs_previous: str, extra_scope: Any) -> dict[str, Any]:
    rows = [row for row in ledger.get("rows") or [] if isinstance(row, dict)]
    scope = _as_dict(extra_scope)
    scope.update(
        {
            "sources": sorted({str(row.get("source") or "") for row in rows if row.get("source")}),
            "cities": sorted({str(row.get("city") or "") for row in rows if row.get("city")}),
        }
    )
    if scope_change_vs_previous:
        scope["scope_change_vs_previous"] = scope_change_vs_previous
    elif "scope_change_vs_previous" not in scope:
        scope["scope_change_vs_previous"] = ""
    return scope


def _diff_summary(diff: dict[str, Any]) -> dict[str, Any]:
    totals = _as_dict(diff.get("totals"))
    return {
        "previous_unique_listing_keys": _int_value(totals.get("previous_unique_listing_keys")),
        "current_unique_listing_keys": _int_value(totals.get("current_unique_listing_keys")),
        "added_count": _int_value(totals.get("added_count")),
        "removed_count": _int_value(totals.get("removed_count")),
        "still_active_count": _int_value(totals.get("still_active_count")),
        "price_change_count": _int_value(totals.get("price_change_count")),
        "km_change_count": _int_value(totals.get("km_change_count")),
        "changed_listing_count": _int_value(totals.get("changed_listing_count")),
        "by_source": _as_dict(totals.get("by_source")),
    }


def _validate_inputs(
    *,
    ledger: dict[str, Any],
    lifecycle: dict[str, Any],
    diff: dict[str, Any] | None,
    totals: dict[str, Any],
) -> dict[str, Any]:
    checks = [
        _check(
            "collection_id_matches_lifecycle",
            str(ledger.get("collection_id") or "") == str(lifecycle.get("collection_id") or ""),
        ),
        _check(
            "ledger_pricing_ready_matches_lifecycle_records",
            _int_value(totals.get("pricing_ready")) == _int_value(_as_dict(lifecycle.get("totals")).get("records_total")),
        ),
        _check(
            "ledger_listing_runs_match_lifecycle_inputs",
            _int_value(totals.get("listing_source_runs"))
            == _int_value(_as_dict(lifecycle.get("totals")).get("source_runs")),
        ),
    ]
    if diff is not None:
        diff_totals = _as_dict(diff.get("totals"))
        checks.append(
            _check(
                "diff_current_unique_matches_lifecycle",
                _int_value(diff_totals.get("current_unique_listing_keys"))
                == _int_value(totals.get("unique_listing_keys")),
            )
        )
    failing = [check for check in checks if check["status"] != "pass"]
    if failing:
        names = ", ".join(str(check["name"]) for check in failing)
        raise ValueError(f"Snapshot manifest validation failed: {names}")
    return {"status": "pass", "checks": checks}


def _check(name: str, ok: bool) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail"}


def _build_policy(extra_policy: Any) -> dict[str, Any]:
    policy = {
        "diff_identity_key": "Lifecycle listing_key, not fuzzy cross-source vehicle matching.",
        "no_inventory_interpretation": (
            "No-inventory source-city rows are retained in the collection ledger as capacity evidence "
            "but skipped by listing lifecycle because they contain no silver listing records."
        ),
    }
    policy.update(_as_dict(extra_policy))
    return policy


def _merge_extra_metadata(manifest: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    protected = {
        "manifest_version",
        "snapshot_id",
        "snapshot_date",
        "generated_at",
        "status",
        "collection_id",
        "lifecycle_id",
        "previous_snapshot_id",
        "previous_lifecycle_id",
        "paths",
        "scope",
        "totals",
        "diff_vs_previous",
        "validation",
        "policy",
    }
    for key, value in extra.items():
        if key in protected:
            continue
        manifest[key] = value
    return manifest


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return 0


def _path_text(path: Path) -> str:
    return path.as_posix()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
