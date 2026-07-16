"""Source-to-source field coverage comparison reports."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from used_car_price_intelligence.reporting.field_profile import (
    FieldCompleteness,
    FieldProfileReport,
    profile_field_completeness,
)
from used_car_price_intelligence.schema import CanonicalListing


@dataclass(frozen=True)
class ExtraFieldCompleteness:
    field_name: str
    present_count: int
    total_count: int
    completeness: float


@dataclass(frozen=True)
class SourceRunProfile:
    source: str
    silver_path: Path
    quality_summary_path: Path
    manifest_path: Path
    records: list[CanonicalListing]
    quality_summary: dict[str, Any]
    manifest: dict[str, Any]
    field_profile: FieldProfileReport
    extra_fields: list[ExtraFieldCompleteness]


def load_source_run_profile(
    *,
    source: str,
    silver_path: str | Path,
    quality_summary_path: str | Path,
    manifest_path: str | Path,
) -> SourceRunProfile:
    silver = Path(silver_path)
    quality_summary = Path(quality_summary_path)
    manifest = Path(manifest_path)
    records = _load_silver_records(silver)
    return SourceRunProfile(
        source=source,
        silver_path=silver,
        quality_summary_path=quality_summary,
        manifest_path=manifest,
        records=records,
        quality_summary=_load_json_object(quality_summary),
        manifest=_load_json_object(manifest),
        field_profile=profile_field_completeness(source=source, records=records),
        extra_fields=_profile_extra_fields(source=source, records=records),
    )


def render_source_comparison_report(
    left: SourceRunProfile,
    right: SourceRunProfile,
    *,
    title: str,
    generated_at: str,
    recommendation: str,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"Generated at: {generated_at}",
        "",
        "## Decision",
        "",
        _decision_summary(left, right),
        "",
        "The immediate modeling implication is simple: use both sources for gold pricing rows, "
        "but keep source provenance and source-specific evidence fields intact.",
        "",
        "## Run Summary",
        "",
        _run_summary_table(left, right),
        "",
        "## Acquisition Behavior",
        "",
        _acquisition_table(left, right),
        "",
        "## Field Coverage",
        "",
        _field_comparison_table(left, right),
        "",
        "## Source-Specific Extra Fields",
        "",
        _extra_field_table(left, right),
        "",
        "## Interpretation",
        "",
        *_interpretation_lines(left, right),
        "",
        "## Recommended Next Step",
        "",
        recommendation,
        "",
        "## Evidence Files",
        "",
        f"- {left.source} silver: `{_display_path(left.silver_path)}`",
        f"- {left.source} quality summary: `{_display_path(left.quality_summary_path)}`",
        f"- {left.source} manifest: `{_display_path(left.manifest_path)}`",
        f"- {right.source} silver: `{_display_path(right.silver_path)}`",
        f"- {right.source} quality summary: `{_display_path(right.quality_summary_path)}`",
        f"- {right.source} manifest: `{_display_path(right.manifest_path)}`",
    ]
    return "\n".join(lines) + "\n"


def render_multi_source_comparison_report(
    profiles: list[SourceRunProfile],
    *,
    title: str,
    generated_at: str,
    recommendation: str,
) -> str:
    if len(profiles) < 2:
        raise ValueError("At least two source profiles are required for comparison.")

    lines = [
        f"# {title}",
        "",
        f"Generated at: {generated_at}",
        "",
        "## Decision",
        "",
        _multi_decision_summary(profiles),
        "",
        "The immediate modeling implication is simple: use all passing trusted sources for gold pricing rows, "
        "but keep source provenance and source-specific evidence fields intact.",
        "",
        "## Run Summary",
        "",
        _multi_run_summary_table(profiles),
        "",
        "## Acquisition Behavior",
        "",
        _multi_acquisition_table(profiles),
        "",
        "## Field Coverage",
        "",
        _multi_field_comparison_table(profiles),
        "",
        "## Source-Specific Extra Fields",
        "",
        _multi_extra_field_table(profiles),
        "",
        "## Interpretation",
        "",
        *_multi_interpretation_lines(profiles),
        "",
        "## Recommended Next Step",
        "",
        recommendation,
        "",
        "## Evidence Files",
        "",
        *_multi_evidence_lines(profiles),
    ]
    return "\n".join(lines) + "\n"


def _decision_summary(left: SourceRunProfile, right: SourceRunProfile) -> str:
    if _pricing_ready_run(left) and _pricing_ready_run(right):
        return (
            "Both runs are approved as pricing-ready trusted-source inputs, but they should stay "
            "separate at the acquisition layer. They become comparable only after each source adapter "
            "emits canonical records."
        )
    return (
        "At least one run needs review before it is treated as a trusted pricing-ready input. "
        "Compare field gaps and quality status before merging these rows into gold data."
    )


def _multi_decision_summary(profiles: list[SourceRunProfile]) -> str:
    if all(_pricing_ready_run(profile) for profile in profiles):
        return (
            "All compared runs are approved as pricing-ready trusted-source inputs. They should stay "
            "separate at the acquisition layer and become comparable only after each source adapter emits "
            "canonical records."
        )
    return (
        "At least one run needs review before it is treated as a trusted pricing-ready input. "
        "Compare field gaps and quality status before merging these rows into gold data."
    )


def _pricing_ready_run(profile: SourceRunProfile) -> bool:
    records_total = int(profile.quality_summary.get("records_total") or 0)
    return (
        records_total > 0
        and int(profile.quality_summary.get("pricing_ready") or 0) == records_total
        and int(profile.quality_summary.get("quarantined") or 0) == 0
        and float(profile.quality_summary.get("required_completeness_avg") or 0.0) == 1.0
    )


def write_source_comparison_report(path: str | Path, report: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def _multi_run_summary_table(profiles: list[SourceRunProfile]) -> str:
    rows = [
        "| Metric | " + " | ".join(_label(profile) for profile in profiles) + " |",
        "| --- | " + " | ".join("---:" for _ in profiles) + " |",
    ]
    metrics = [
        ("Records", lambda profile: _summary_value(profile, "records_total")),
        ("Pricing-ready", lambda profile: _summary_value(profile, "pricing_ready")),
        ("Quarantined", lambda profile: _summary_value(profile, "quarantined")),
        ("Required completeness", lambda profile: _summary_percent(profile, "required_completeness_avg")),
        ("High-value completeness", lambda profile: _summary_percent(profile, "high_value_completeness_avg")),
        ("Optional completeness", lambda profile: _summary_percent(profile, "optional_completeness_avg")),
        ("Overall completeness", lambda profile: _summary_percent(profile, "overall_completeness_avg")),
        ("Runtime seconds", lambda profile: _manifest_number(profile, "duration_seconds")),
    ]
    for label, formatter in metrics:
        rows.append("| " + label + " | " + " | ".join(formatter(profile) for profile in profiles) + " |")
    return "\n".join(rows)


def _run_summary_table(left: SourceRunProfile, right: SourceRunProfile) -> str:
    rows = [
        "| Metric | " + _label(left) + " | " + _label(right) + " |",
        "| --- | ---: | ---: |",
        f"| Records | {_summary_value(left, 'records_total')} | {_summary_value(right, 'records_total')} |",
        f"| Pricing-ready | {_summary_value(left, 'pricing_ready')} | {_summary_value(right, 'pricing_ready')} |",
        f"| Quarantined | {_summary_value(left, 'quarantined')} | {_summary_value(right, 'quarantined')} |",
        (
            f"| Required completeness | {_summary_percent(left, 'required_completeness_avg')} | "
            f"{_summary_percent(right, 'required_completeness_avg')} |"
        ),
        (
            f"| High-value completeness | {_summary_percent(left, 'high_value_completeness_avg')} | "
            f"{_summary_percent(right, 'high_value_completeness_avg')} |"
        ),
        (
            f"| Optional completeness | {_summary_percent(left, 'optional_completeness_avg')} | "
            f"{_summary_percent(right, 'optional_completeness_avg')} |"
        ),
        (
            f"| Overall completeness | {_summary_percent(left, 'overall_completeness_avg')} | "
            f"{_summary_percent(right, 'overall_completeness_avg')} |"
        ),
        (
            f"| Runtime seconds | {_manifest_number(left, 'duration_seconds')} | "
            f"{_manifest_number(right, 'duration_seconds')} |"
        ),
    ]
    return "\n".join(rows)


def _multi_acquisition_table(profiles: list[SourceRunProfile]) -> str:
    rows = [
        "| Metric | " + " | ".join(_label(profile) for profile in profiles) + " |",
        "| --- | " + " | ".join("---" for _ in profiles) + " |",
    ]
    metrics = [
        ("Run ID", lambda profile: f"`{_manifest_text(profile, 'run_id')}`"),
        ("City", lambda profile: _manifest_text(profile, "city")),
        ("Source URL", _manifest_link),
        ("Pagination type", lambda profile: _listing_text(profile, "pagination_type")),
        ("Attempted pages", lambda profile: _listing_number(profile, "attempted_pages")),
        ("Unique cards seen", lambda profile: _listing_number(profile, "unique_cards_seen")),
        ("Returned records", lambda profile: _listing_number(profile, "returned_records")),
        ("Source total items", lambda profile: _listing_number(profile, "source_total_items")),
        ("Detail requested", lambda profile: _record_count(profile, "detail_requested")),
        ("Detail successful", lambda profile: _record_count(profile, "detail_successful")),
    ]
    for label, formatter in metrics:
        rows.append("| " + label + " | " + " | ".join(formatter(profile) for profile in profiles) + " |")
    return "\n".join(rows)


def _acquisition_table(left: SourceRunProfile, right: SourceRunProfile) -> str:
    rows = [
        "| Metric | " + _label(left) + " | " + _label(right) + " |",
        "| --- | --- | --- |",
        (
            f"| Run ID | `{_manifest_text(left, 'run_id')}` | "
            f"`{_manifest_text(right, 'run_id')}` |"
        ),
        f"| City | {_manifest_text(left, 'city')} | {_manifest_text(right, 'city')} |",
        f"| Source URL | {_manifest_link(left)} | {_manifest_link(right)} |",
        (
            f"| Pagination type | {_listing_text(left, 'pagination_type')} | "
            f"{_listing_text(right, 'pagination_type')} |"
        ),
        f"| Attempted pages | {_listing_number(left, 'attempted_pages')} | {_listing_number(right, 'attempted_pages')} |",
        f"| Unique cards seen | {_listing_number(left, 'unique_cards_seen')} | {_listing_number(right, 'unique_cards_seen')} |",
        f"| Returned records | {_listing_number(left, 'returned_records')} | {_listing_number(right, 'returned_records')} |",
        f"| Source total items | {_listing_number(left, 'source_total_items')} | {_listing_number(right, 'source_total_items')} |",
        (
            f"| Detail requested | {_record_count(left, 'detail_requested')} | "
            f"{_record_count(right, 'detail_requested')} |"
        ),
        (
            f"| Detail successful | {_record_count(left, 'detail_successful')} | "
            f"{_record_count(right, 'detail_successful')} |"
        ),
    ]
    return "\n".join(rows)


def _multi_field_comparison_table(profiles: list[SourceRunProfile]) -> str:
    fields_by_source = [
        {field.field_name: field for field in profile.field_profile.fields}
        for profile in profiles
    ]
    field_names: list[str] = []
    for fields in fields_by_source:
        for field_name in fields:
            if field_name not in field_names:
                field_names.append(field_name)

    rows = [
        "| Group | Field | " + " | ".join(_label(profile) for profile in profiles) + " | Note |",
        "| --- | --- | " + " | ".join("---:" for _ in profiles) + " | --- |",
    ]
    for field_name in field_names:
        fields = [fields.get(field_name) for fields in fields_by_source]
        group = next(field.field_group for field in fields if field is not None)
        rows.append(
            "| "
            + group
            + " | `"
            + field_name
            + "` | "
            + " | ".join(_format_field(field) for field in fields)
            + " | "
            + _multi_field_note(fields)
            + " |"
        )
    return "\n".join(rows)


def _field_comparison_table(left: SourceRunProfile, right: SourceRunProfile) -> str:
    left_fields = {field.field_name: field for field in left.field_profile.fields}
    right_fields = {field.field_name: field for field in right.field_profile.fields}
    field_names = list(left_fields)
    for field_name in right_fields:
        if field_name not in left_fields:
            field_names.append(field_name)

    rows = [
        "| Group | Field | " + _label(left) + " | " + _label(right) + " | Note |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for field_name in field_names:
        left_field = left_fields.get(field_name)
        right_field = right_fields.get(field_name)
        group = (left_field or right_field).field_group
        rows.append(
            "| "
            + group
            + " | `"
            + field_name
            + "` | "
            + _format_field(left_field)
            + " | "
            + _format_field(right_field)
            + " | "
            + _field_note(field_name, left_field, right_field)
            + " |"
        )
    return "\n".join(rows)


def _multi_extra_field_table(profiles: list[SourceRunProfile]) -> str:
    fields_by_source = [
        {field.field_name: field for field in profile.extra_fields}
        for profile in profiles
    ]
    field_names = sorted(set().union(*(set(fields) for fields in fields_by_source)))
    if not field_names:
        return "No source-specific extra fields were present."

    rows = [
        "| Field | " + " | ".join(_label(profile) for profile in profiles) + " |",
        "| --- | " + " | ".join("---:" for _ in profiles) + " |",
    ]
    for field_name in field_names:
        rows.append(
            "| `"
            + field_name
            + "` | "
            + " | ".join(_format_extra_field(fields.get(field_name)) for fields in fields_by_source)
            + " |"
        )
    return "\n".join(rows)


def _extra_field_table(left: SourceRunProfile, right: SourceRunProfile) -> str:
    left_fields = {field.field_name: field for field in left.extra_fields}
    right_fields = {field.field_name: field for field in right.extra_fields}
    field_names = sorted(set(left_fields) | set(right_fields))
    if not field_names:
        return "No source-specific extra fields were present."

    rows = [
        "| Field | " + _label(left) + " | " + _label(right) + " |",
        "| --- | ---: | ---: |",
    ]
    for field_name in field_names:
        rows.append(
            "| `"
            + field_name
            + "` | "
            + _format_extra_field(left_fields.get(field_name))
            + " | "
            + _format_extra_field(right_fields.get(field_name))
            + " |"
        )
    return "\n".join(rows)


def _multi_interpretation_lines(profiles: list[SourceRunProfile]) -> list[str]:
    lines = []
    if all(_pricing_ready_run(profile) for profile in profiles):
        lines.append("- Required pricing fields are complete across all compared runs.")
    else:
        lines.append("- At least one compared run needs review before it is used as gold pricing data.")

    for field_name in ["ownership", "registration_code", "body_type", "dealer_name", "warranty_label"]:
        lines.append(_multi_field_coverage_sentence(field_name, profiles))

    lines.append(
        "- Source-specific ratings, inspection states, and certification statuses should remain in `extra_fields` until a normalization strategy is proven."
    )
    return lines


def _interpretation_lines(left: SourceRunProfile, right: SourceRunProfile) -> list[str]:
    left_fields = {field.field_name: field for field in left.field_profile.fields}
    right_fields = {field.field_name: field for field in right.field_profile.fields}
    return [
        "- Required pricing fields are complete in both runs, so both sources can contribute to gold pricing rows.",
        _comparison_sentence(
            "ownership",
            left,
            right,
            left_fields.get("ownership"),
            right_fields.get("ownership"),
            "Ownership is usable in both current runs.",
        ),
        _comparison_sentence(
            "registration_code",
            left,
            right,
            left_fields.get("registration_code"),
            right_fields.get("registration_code"),
            "Registration is the main cross-source gap to monitor.",
        ),
        _comparison_sentence(
            "body_type",
            left,
            right,
            left_fields.get("body_type"),
            right_fields.get("body_type"),
            "Body type availability differs by source.",
        ),
        _comparison_sentence(
            "dealer_name",
            left,
            right,
            left_fields.get("dealer_name"),
            right_fields.get("dealer_name"),
            "Dealer metadata is source-dependent and should stay optional.",
        ),
        "- Source-specific ratings and inspection evidence should remain in `extra_fields` until a normalization strategy is proven.",
    ]


def _multi_field_coverage_sentence(field_name: str, profiles: list[SourceRunProfile]) -> str:
    parts = []
    complete_sources = []
    partial_sources = []
    missing_sources = []
    for profile in profiles:
        fields = {field.field_name: field for field in profile.field_profile.fields}
        field = fields.get(field_name)
        present = field.present_count if field else 0
        total = field.total_count if field else len(profile.records)
        parts.append(f"{profile.source} {present}/{total}")
        if total > 0 and present == total:
            complete_sources.append(profile.source)
        elif present == 0:
            missing_sources.append(profile.source)
        else:
            partial_sources.append(profile.source)

    if len(complete_sources) == len(profiles):
        return f"- `{field_name}` is complete across all compared runs."
    if complete_sources and not partial_sources:
        return (
            f"- `{field_name}` is complete in {', '.join(complete_sources)} and missing in "
            f"{', '.join(missing_sources)}. Coverage: {', '.join(parts)}."
        )
    return f"- `{field_name}` coverage differs by source: {', '.join(parts)}."


def _comparison_sentence(
    field_name: str,
    left: SourceRunProfile,
    right: SourceRunProfile,
    left_field: FieldCompleteness | None,
    right_field: FieldCompleteness | None,
    fallback: str,
) -> str:
    left_count = left_field.present_count if left_field else 0
    right_count = right_field.present_count if right_field else 0
    left_total = left_field.total_count if left_field else len(left.records)
    right_total = right_field.total_count if right_field else len(right.records)
    if left_count == left_total and right_count == right_total:
        return f"- `{field_name}` is complete in both runs."
    if left_count == left_total and right_count < right_total:
        right_status = "missing" if right_count == 0 else "partial"
        return (
            f"- `{field_name}` is complete in {left.source} ({left_count}/{left_total}) "
            f"but {right_status} in {right.source} ({right_count}/{right_total})."
        )
    if right_count == right_total and left_count < left_total:
        left_status = "missing" if left_count == 0 else "partial"
        return (
            f"- `{field_name}` is complete in {right.source} ({right_count}/{right_total}) "
            f"but {left_status} in {left.source} ({left_count}/{left_total})."
        )
    return f"- {fallback} Current coverage: {left.source} {left_count}/{left_total}, {right.source} {right_count}/{right_total}."


def _multi_field_note(fields: list[FieldCompleteness | None]) -> str:
    values = [field.completeness if field else 0.0 for field in fields]
    if all(value == 1.0 for value in values):
        return "stable across sources"
    if all(value == 0.0 for value in values):
        return "missing across sources"
    if max(values) - min(values) >= 0.5:
        return "source-specific gap"
    return "partial difference"


def _field_note(
    field_name: str,
    left_field: FieldCompleteness | None,
    right_field: FieldCompleteness | None,
) -> str:
    left_value = left_field.completeness if left_field else 0.0
    right_value = right_field.completeness if right_field else 0.0
    if left_value == 1.0 and right_value == 1.0:
        return "stable in both"
    if left_value == 0.0 and right_value == 0.0:
        return "missing in both"
    if abs(left_value - right_value) >= 0.5:
        return "source-specific gap"
    if left_value != right_value:
        return "partial difference"
    if field_name in {"inspection_score", "deal_rating", "condition_grade"}:
        return "keep source-specific until normalized"
    return "same coverage"


def _multi_evidence_lines(profiles: list[SourceRunProfile]) -> list[str]:
    lines = []
    for profile in profiles:
        lines.extend(
            [
                f"- {profile.source} silver: `{_display_path(profile.silver_path)}`",
                f"- {profile.source} quality summary: `{_display_path(profile.quality_summary_path)}`",
                f"- {profile.source} manifest: `{_display_path(profile.manifest_path)}`",
            ]
        )
    return lines


def _profile_extra_fields(*, source: str, records: list[CanonicalListing]) -> list[ExtraFieldCompleteness]:
    total = len(records)
    counts: dict[str, int] = {}
    for record in records:
        flat = _flatten_extra_fields(record.extra_fields)
        for key, value in flat.items():
            if _present(value):
                counts[key] = counts.get(key, 0) + 1
    return [
        ExtraFieldCompleteness(
            field_name=field_name,
            present_count=present_count,
            total_count=total,
            completeness=_ratio(present_count, total),
        )
        for field_name, present_count in sorted(counts.items())
    ]


def _flatten_extra_fields(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value} if prefix else {}
    flattened: dict[str, Any] = {}
    for key, item in value.items():
        next_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, dict):
            flattened.update(_flatten_extra_fields(item, next_key))
        else:
            flattened[next_key] = item
    return flattened


def _load_silver_records(path: Path) -> list[CanonicalListing]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Silver file must contain a JSON list: {path}")
    return [CanonicalListing.from_mapping(record) for record in payload]


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _format_field(field: FieldCompleteness | None) -> str:
    if field is None:
        return "0/0 (0.00%)"
    return f"{field.present_count}/{field.total_count} ({field.completeness * 100:.2f}%)"


def _format_extra_field(field: ExtraFieldCompleteness | None) -> str:
    if field is None:
        return "n/a"
    return f"{field.present_count}/{field.total_count} ({field.completeness * 100:.2f}%)"


def _label(profile: SourceRunProfile) -> str:
    return profile.source.replace("_", " ").title()


def _summary_value(profile: SourceRunProfile, key: str) -> str:
    return str(profile.quality_summary.get(key, "n/a"))


def _summary_percent(profile: SourceRunProfile, key: str) -> str:
    value = profile.quality_summary.get(key)
    if not isinstance(value, int | float):
        return "n/a"
    return f"{value * 100:.2f}%"


def _manifest_text(profile: SourceRunProfile, key: str) -> str:
    value = profile.manifest.get(key)
    return str(value) if value is not None else "n/a"


def _manifest_number(profile: SourceRunProfile, key: str) -> str:
    value = profile.manifest.get(key)
    return str(value) if value is not None else "n/a"


def _manifest_link(profile: SourceRunProfile) -> str:
    url = str(profile.manifest.get("source_url") or "")
    if not url:
        return "n/a"
    return f"<{url}>"


def _listing_text(profile: SourceRunProfile, key: str) -> str:
    listing_capture = profile.manifest.get("listing_capture") or {}
    value = listing_capture.get(key) if isinstance(listing_capture, dict) else None
    return str(value) if value is not None else "n/a"


def _listing_number(profile: SourceRunProfile, key: str) -> str:
    return _listing_text(profile, key)


def _record_count(profile: SourceRunProfile, key: str) -> str:
    record_counts = profile.manifest.get("record_counts") or {}
    value = record_counts.get(key) if isinstance(record_counts, dict) else None
    return str(value) if value is not None else "n/a"


def _display_path(path: Path) -> str:
    return path.as_posix()


def _ratio(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total, 4)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != "" and value.strip().lower() != "unknown"
    if isinstance(value, list | tuple | set | dict):
        return len(value) > 0
    return True
