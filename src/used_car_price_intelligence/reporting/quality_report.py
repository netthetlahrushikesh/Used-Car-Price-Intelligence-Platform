"""Render human-readable reports from generated quality summary JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_SUMMARY_KEYS = {
    "source",
    "records_total",
    "silver_valid",
    "pricing_ready",
    "quarantined",
    "required_completeness_avg",
    "high_value_completeness_avg",
    "optional_completeness_avg",
    "overall_completeness_avg",
    "quarantine_reasons",
    "warnings",
}


def load_quality_summary(path: str | Path) -> dict[str, Any]:
    summary_path = Path(path)
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Quality summary must be a JSON object: {summary_path}")

    missing_keys = sorted(REQUIRED_SUMMARY_KEYS.difference(payload))
    if missing_keys:
        raise ValueError(f"Quality summary is missing keys: {', '.join(missing_keys)}")

    return payload


def render_quality_report(summary: dict[str, Any]) -> str:
    status = _quality_status(summary)
    lines = [
        "# Fixture Quality Report",
        "",
        f"Status: {status}",
        f"Source: {summary['source']}",
        (
            "Records: "
            f"{summary['records_total']} total | "
            f"{summary['silver_valid']} silver-valid | "
            f"{summary['pricing_ready']} pricing-ready | "
            f"{summary['quarantined']} quarantined"
        ),
        "",
        "Completeness:",
        f"- required: {_format_percent(summary['required_completeness_avg'])}",
        f"- high_value: {_format_percent(summary['high_value_completeness_avg'])}",
        f"- optional: {_format_percent(summary['optional_completeness_avg'])}",
        f"- overall: {_format_percent(summary['overall_completeness_avg'])}",
        "",
        "Quarantine reasons:",
        *_format_counts(summary["quarantine_reasons"]),
        "",
        "Warnings:",
        *_format_counts(summary["warnings"]),
    ]

    output_paths = summary.get("output_paths")
    if output_paths:
        lines.extend(["", "Output paths:", *_format_counts(output_paths)])

    return "\n".join(lines) + "\n"


def _quality_status(summary: dict[str, Any]) -> str:
    records_total = int(summary["records_total"])
    pricing_ready = int(summary["pricing_ready"])
    quarantined = int(summary["quarantined"])
    required_completeness = float(summary["required_completeness_avg"])

    if records_total == 0:
        return "FAIL"
    if pricing_ready == records_total and quarantined == 0 and required_completeness == 1.0:
        return "PASS"
    if pricing_ready > 0:
        return "WARN"
    return "FAIL"


def _format_percent(value: object) -> str:
    return f"{float(value) * 100:.2f}%"


def _format_counts(counts: object) -> list[str]:
    if not counts:
        return ["- none"]
    if not isinstance(counts, dict):
        raise ValueError("Report counts must be dictionaries.")
    return [f"- {key}: {counts[key]}" for key in sorted(counts)]
