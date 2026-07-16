"""Scale projection reports for trusted snapshot collection targets."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import math
from pathlib import Path
from typing import Any


SCALE_PROJECTION_VERSION = "scale_projection_v0.1"
DEFAULT_SCENARIOS = {
    "original_baseline_scope": 909,
    "small_scale": 2_500,
    "recommended": 5_000,
    "stretch": 10_000,
}


def build_scale_projection(
    *,
    target_id: str,
    target_observations: int,
    current_snapshot_manifest_path: str | Path,
    recommended_rows_per_snapshot: int = 5_000,
    generated_at: str | None = None,
) -> dict[str, Any]:
    manifest_path = Path(current_snapshot_manifest_path)
    manifest = _load_json(manifest_path)
    totals = dict(manifest.get("totals") or {})
    current_observations = _int_value(totals.get("pricing_ready"))
    current_unique_listing_keys = _int_value(totals.get("unique_listing_keys"))
    source_runs = _int_value(totals.get("source_runs"))
    remaining_observations = max(target_observations - current_observations, 0)

    scenarios = {"current_checkpoint_size": current_observations}
    scenarios.update(DEFAULT_SCENARIOS)
    scenarios["recommended"] = recommended_rows_per_snapshot

    return {
        "projection_version": SCALE_PROJECTION_VERSION,
        "target_id": target_id,
        "generated_at": generated_at or _utc_now(),
        "target_observations": target_observations,
        "current": {
            "snapshot_id": str(manifest.get("snapshot_id") or ""),
            "snapshot_date": str(manifest.get("snapshot_date") or ""),
            "manifest_path": str(manifest_path),
            "trusted_observations": current_observations,
            "unique_listing_keys": current_unique_listing_keys,
            "source_runs": source_runs,
            "by_source": dict(totals.get("by_source") or {}),
        },
        "remaining_observations": remaining_observations,
        "recommended_rows_per_snapshot": recommended_rows_per_snapshot,
        "scenarios": {
            name: _scenario_projection(
                name=name,
                rows_per_snapshot=rows_per_snapshot,
                current_observations=current_observations,
                target_observations=target_observations,
            )
            for name, rows_per_snapshot in scenarios.items()
        },
        "recommended_allocation": _recommended_allocation(recommended_rows_per_snapshot),
        "readiness_gates": [
            "Repeat the same source-city baseline once before expanding.",
            "Keep pricing-critical required completeness at 100 percent.",
            "Keep quarantine rate at or below 1 percent.",
            "Review lifecycle duplicate groups before model training.",
            "Interpret removed listings only when source-city coverage is equivalent.",
            "Add bounded source-aware parallelism only after the repeat snapshot is stable.",
        ],
    }


def render_scale_projection_markdown(projection: dict[str, Any]) -> str:
    current = dict(projection.get("current") or {})
    scenarios = dict(projection.get("scenarios") or {})
    allocation = dict(projection.get("recommended_allocation") or {})
    lines = [
        "# Snapshot Scale Projection",
        "",
        f"Target id: `{projection.get('target_id', '')}`",
        f"Generated at: `{projection.get('generated_at', '')}`",
        f"Target observations: {projection.get('target_observations', 0):,}",
        f"Current snapshot: `{current.get('snapshot_id', '')}`",
        f"Current trusted observations: {current.get('trusted_observations', 0):,}",
        f"Remaining observations: {projection.get('remaining_observations', 0):,}",
        "",
        "## Snapshot Size Scenarios",
        "",
        "| Scenario | Rows Per Future Snapshot | Future Snapshots Needed | Total Snapshots Including Current |",
        "| --- | ---: | ---: | ---: |",
    ]
    for scenario in scenarios.values():
        lines.append(
            "| {name} | {rows} | {future} | {total} |".format(
                name=scenario.get("name", ""),
                rows=f"{scenario.get('rows_per_snapshot', 0):,}",
                future=scenario.get("future_snapshots_needed", 0),
                total=scenario.get("total_snapshots_including_current", 0),
            )
        )

    lines.extend(
        [
            "",
            "## Recommended Allocation",
            "",
            "| Source | Target Rows Per Snapshot | Share | Reason |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for source, item in allocation.items():
        lines.append(
            "| {source} | {rows} | {share}% | {reason} |".format(
                source=source,
                rows=f"{item.get('target_rows', 0):,}",
                share=item.get("share_pct", 0),
                reason=item.get("reason", ""),
            )
        )

    lines.extend(["", "## Readiness Gates", ""])
    for gate in projection.get("readiness_gates") or []:
        lines.append(f"- {gate}")
    lines.append("")
    return "\n".join(lines)


def write_scale_projection_json(path: str | Path, projection: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def write_scale_projection_markdown(path: str | Path, projection: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_scale_projection_markdown(projection), encoding="utf-8")
    return output_path


def _scenario_projection(
    *,
    name: str,
    rows_per_snapshot: int,
    current_observations: int,
    target_observations: int,
) -> dict[str, Any]:
    remaining = max(target_observations - current_observations, 0)
    future_snapshots_needed = math.ceil(remaining / rows_per_snapshot) if rows_per_snapshot > 0 else 0
    return {
        "name": name,
        "rows_per_snapshot": rows_per_snapshot,
        "future_snapshots_needed": future_snapshots_needed,
        "total_snapshots_including_current": future_snapshots_needed + (1 if current_observations > 0 else 0),
        "projected_total_observations": current_observations + (future_snapshots_needed * rows_per_snapshot),
    }


def _recommended_allocation(rows_per_snapshot: int) -> dict[str, dict[str, Any]]:
    shares = {
        "true_value": {
            "share": 0.50,
            "reason": "Structured OEM-certified inventory and strongest current row yield.",
        },
        "mahindra_first_choice": {
            "share": 0.30,
            "reason": "Multi-brand dealer-evaluated inventory, kept as a separate source lane.",
        },
        "spinny": {
            "share": 0.20,
            "reason": "High-quality evaluated inventory, slower because detail enrichment is expensive.",
        },
    }
    allocation = {}
    allocated = 0
    for source, item in shares.items():
        target_rows = int(rows_per_snapshot * float(item["share"]))
        allocated += target_rows
        allocation[source] = {
            "target_rows": target_rows,
            "share_pct": int(float(item["share"]) * 100),
            "reason": item["reason"],
        }
    remainder = rows_per_snapshot - allocated
    if remainder:
        allocation["true_value"]["target_rows"] += remainder
    return allocation


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return data


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


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
