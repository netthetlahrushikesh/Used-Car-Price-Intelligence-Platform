"""Remaining-gap strategy reports for bounded snapshot expansion."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import yaml


REMAINING_GAP_STRATEGY_VERSION = "remaining_gap_strategy_v0.1"


def build_remaining_gap_strategy(
    *,
    snapshot_manifest_path: str | Path,
    target_config_path: str | Path = "config/snapshot_targets.yml",
    target_pricing_ready: int | None = None,
    allocation_key: str = "recommended_5000_row_source_allocation",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a source-aware plan for closing the current snapshot row gap."""

    manifest_path = Path(snapshot_manifest_path)
    config_path = Path(target_config_path)
    manifest = _load_json(manifest_path)
    target_config = _load_yaml(config_path)
    totals = dict(manifest.get("totals") or {})
    by_source = dict(totals.get("by_source") or {})
    allocations = dict(target_config.get(allocation_key) or {})

    current_rows = _int_value(totals.get("pricing_ready"))
    target_rows = target_pricing_ready or _int_value(totals.get("target_pricing_ready")) or current_rows
    rows_under_target = max(target_rows - current_rows, 0)

    source_rows = {
        source: _source_strategy(
            source=source,
            current_rows=_int_value(dict(by_source.get(source) or {}).get("pricing_ready")),
            allocation=dict(allocation),
            target_rows=target_rows,
        )
        for source, allocation in allocations.items()
    }
    allocation_gap_total = sum(int(item["allocation_gap"]) for item in source_rows.values())
    over_allocation_total = sum(int(item["over_allocation"]) for item in source_rows.values())

    return {
        "strategy_version": REMAINING_GAP_STRATEGY_VERSION,
        "strategy_id": _strategy_id(manifest),
        "generated_at": generated_at or _utc_now(),
        "snapshot": {
            "snapshot_id": str(manifest.get("snapshot_id") or ""),
            "snapshot_date": str(manifest.get("snapshot_date") or ""),
            "manifest_path": str(manifest_path),
        },
        "target": {
            "target_pricing_ready": target_rows,
            "current_pricing_ready": current_rows,
            "rows_under_target": rows_under_target,
            "allocation_gap_total": allocation_gap_total,
            "over_allocation_total": over_allocation_total,
        },
        "source_rows": source_rows,
        "decision": _decision(
            source_rows=source_rows,
            rows_under_target=rows_under_target,
            allocation_gap_total=allocation_gap_total,
        ),
        "recommended_sequence": _recommended_sequence(source_rows=source_rows),
        "stop_conditions": [
            "Do not add large True Value batches while True Value is at or above 95 percent of its allocation.",
            "Do not promote a source run if required completeness drops below 100 percent.",
            "Do not promote a source run with quarantined pricing rows until parser or adapter gaps are fixed.",
            "Do not double-count a deeper same-source same-city run; replace the older shallower run in the ledger.",
            "Do not interpret removed listings unless the source-city scope is equivalent to the previous snapshot.",
        ],
    }


def render_remaining_gap_strategy_markdown(strategy: dict[str, Any]) -> str:
    """Render a remaining-gap strategy as an operator-facing Markdown report."""

    snapshot = dict(strategy.get("snapshot") or {})
    target = dict(strategy.get("target") or {})
    decision = dict(strategy.get("decision") or {})
    source_rows = dict(strategy.get("source_rows") or {})
    recommended_sequence = list(strategy.get("recommended_sequence") or [])

    lines = [
        "# Remaining 5k Gap Strategy",
        "",
        f"Strategy id: `{strategy.get('strategy_id', '')}`",
        f"Generated at: `{strategy.get('generated_at', '')}`",
        f"Snapshot: `{snapshot.get('snapshot_id', '')}`",
        f"Current pricing-ready rows: {target.get('current_pricing_ready', 0):,}",
        f"Target pricing-ready rows: {target.get('target_pricing_ready', 0):,}",
        f"Rows under target: {target.get('rows_under_target', 0):,}",
        "",
        "## Source Allocation",
        "",
        "| Source | Current Rows | Target Rows | Gap | Share Now | Share Target | Status | Next Action |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for source, item in source_rows.items():
        lines.append(
            "| {source} | {current} | {target_rows} | {gap} | {current_share:.2f}% | "
            "{target_share:.2f}% | {status} | {next_action} |".format(
                source=source,
                current=int(item.get("current_rows") or 0),
                target_rows=int(item.get("target_rows") or 0),
                gap=int(item.get("allocation_gap") or 0),
                current_share=float(item.get("current_share_pct") or 0.0),
                target_share=float(item.get("target_share_pct") or 0.0),
                status=str(item.get("status") or ""),
                next_action=str(item.get("next_action") or ""),
            )
        )

    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"Decision: `{decision.get('name', '')}`",
            "",
            str(decision.get("reason") or ""),
            "",
            "## Recommended Sequence",
            "",
            "| Order | Step | Source | Target Rows | Rationale |",
            "| ---: | --- | --- | ---: | --- |",
        ]
    )
    for index, step in enumerate(recommended_sequence, start=1):
        lines.append(
            "| {index} | {name} | {source} | {target_rows} | {rationale} |".format(
                index=index,
                name=str(step.get("name") or ""),
                source=str(step.get("source") or ""),
                target_rows=int(step.get("target_rows") or 0),
                rationale=str(step.get("rationale") or ""),
            )
        )

    lines.extend(["", "## Stop Conditions", ""])
    for stop_condition in strategy.get("stop_conditions") or []:
        lines.append(f"- {stop_condition}")
    lines.append("")
    return "\n".join(lines)


def write_remaining_gap_strategy_json(path: str | Path, strategy: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(strategy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def write_remaining_gap_strategy_markdown(path: str | Path, strategy: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_remaining_gap_strategy_markdown(strategy), encoding="utf-8")
    return output_path


def _source_strategy(
    *,
    source: str,
    current_rows: int,
    allocation: dict[str, Any],
    target_rows: int,
) -> dict[str, Any]:
    target_source_rows = _int_value(allocation.get("target_rows"))
    allocation_gap = max(target_source_rows - current_rows, 0)
    over_allocation = max(current_rows - target_source_rows, 0)
    target_share_pct = _float_value(allocation.get("share_pct"))
    current_share_pct = round((current_rows / target_rows) * 100, 2) if target_rows else 0.0
    allocation_fill_pct = round((current_rows / target_source_rows) * 100, 2) if target_source_rows else 0.0
    status = _source_status(
        source=source,
        current_rows=current_rows,
        target_rows=target_source_rows,
        allocation_gap=allocation_gap,
        allocation_fill_pct=allocation_fill_pct,
    )
    return {
        "source": source,
        "current_rows": current_rows,
        "target_rows": target_source_rows,
        "allocation_gap": allocation_gap,
        "over_allocation": over_allocation,
        "allocation_fill_pct": allocation_fill_pct,
        "current_share_pct": current_share_pct,
        "target_share_pct": target_share_pct,
        "status": status,
        "role": str(allocation.get("role") or ""),
        "configured_next_action": str(allocation.get("next_action") or ""),
        "next_action": _next_action(source=source, status=status, allocation_gap=allocation_gap),
    }


def _source_status(
    *,
    source: str,
    current_rows: int,
    target_rows: int,
    allocation_gap: int,
    allocation_fill_pct: float,
) -> str:
    if target_rows and current_rows > target_rows:
        return "over_allocation"
    if allocation_gap == 0:
        return "allocation_met"
    if source == "true_value" and allocation_fill_pct >= 95:
        return "near_allocation"
    if source == "mahindra_first_choice" and allocation_gap > 0:
        return "capacity_constrained"
    if source == "spinny" and allocation_gap > 0:
        return "incremental_expansion_needed"
    if allocation_gap > 0:
        return "under_allocation"
    return "unknown"


def _next_action(*, source: str, status: str, allocation_gap: int) -> str:
    if status == "near_allocation":
        return f"Use only as a final capped buffer, maximum {allocation_gap} rows."
    if source == "mahindra_first_choice":
        return "Run source-path discovery before assuming the public city pages can fill the gap."
    if source == "spinny":
        return "Use manifest-backed incremental detail expansion; avoid old full-detail broad runs."
    if status in {"allocation_met", "over_allocation"}:
        return "Pause new rows for this source unless replacing older duplicate scope."
    return "Use bounded source-city additions with manifest promotion."


def _decision(
    *,
    source_rows: dict[str, dict[str, Any]],
    rows_under_target: int,
    allocation_gap_total: int,
) -> dict[str, Any]:
    true_value = source_rows.get("true_value", {})
    true_value_status = str(true_value.get("status") or "")
    if true_value_status in {"near_allocation", "allocation_met", "over_allocation"}:
        return {
            "name": "balanced_gap_close_required",
            "reason": (
                "The remaining row gap should not be closed by a large True Value run. "
                "True Value is already near its planned allocation, so the next work should "
                "prioritize Spinny incremental expansion and MFC capacity discovery, then use "
                "True Value only as a small final buffer."
            ),
            "rows_under_target": rows_under_target,
            "allocation_gap_total": allocation_gap_total,
        }
    return {
        "name": "allocation_gap_can_drive_next_batches",
        "reason": "Source gaps still align with the overall row gap. Continue with bounded source-specific batches.",
        "rows_under_target": rows_under_target,
        "allocation_gap_total": allocation_gap_total,
    }


def _recommended_sequence(*, source_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    spinny_gap = int(dict(source_rows.get("spinny") or {}).get("allocation_gap") or 0)
    mfc_gap = int(dict(source_rows.get("mahindra_first_choice") or {}).get("allocation_gap") or 0)
    true_value_gap = int(dict(source_rows.get("true_value") or {}).get("allocation_gap") or 0)
    return [
        {
            "name": "spinny_incremental_expansion_pack",
            "source": "spinny",
            "target_rows": min(spinny_gap, 200),
            "rationale": (
                "The incremental manifest path is already proven, and Spinny is still below allocation."
            ),
        },
        {
            "name": "mfc_source_path_discovery",
            "source": "mahindra_first_choice",
            "target_rows": min(mfc_gap, 300),
            "rationale": (
                "MFC is multi-brand but public city inventory is uneven, so discover capacity before scaling."
            ),
        },
        {
            "name": "true_value_final_buffer",
            "source": "true_value",
            "target_rows": true_value_gap,
            "rationale": "Use only the remaining allocation gap after MFC and Spinny have been attempted.",
        },
        {
            "name": "repeat_snapshot_observations",
            "source": "all_trusted_sources",
            "target_rows": 0,
            "rationale": (
                "If unique active inventory cannot fill 5k cleanly, grow toward 100k through repeated snapshots."
            ),
        },
    ]


def _strategy_id(manifest: dict[str, Any]) -> str:
    snapshot_id = str(manifest.get("snapshot_id") or "snapshot")
    return f"remaining_gap_strategy_from_{snapshot_id}"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return data


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML object at {path}")
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


def _float_value(value: Any) -> float:
    if value is None or isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return 0.0


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
