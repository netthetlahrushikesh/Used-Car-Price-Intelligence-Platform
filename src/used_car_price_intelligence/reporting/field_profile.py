"""Field-level completeness reports for canonical listing records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from used_car_price_intelligence.quality.evaluator import (
    HIGH_VALUE_FIELDS,
    OPTIONAL_FIELDS,
    REQUIRED_GROUPS,
    _is_present,
)
from used_car_price_intelligence.schema import CanonicalListing


@dataclass(frozen=True)
class FieldCompleteness:
    field_name: str
    field_group: str
    present_count: int
    total_count: int
    completeness: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FieldProfileReport:
    source: str
    records_total: int
    fields: list[FieldCompleteness]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "records_total": self.records_total,
            "fields": [field.to_dict() for field in self.fields],
        }


def profile_field_completeness(
    *,
    source: str,
    records: list[CanonicalListing],
) -> FieldProfileReport:
    total = len(records)
    fields = []
    for field_group, field_name in _profile_fields():
        present_count = sum(1 for record in records if _is_present(getattr(record, field_name)))
        fields.append(
            FieldCompleteness(
                field_name=field_name,
                field_group=field_group,
                present_count=present_count,
                total_count=total,
                completeness=_ratio(present_count, total),
            )
        )

    return FieldProfileReport(source=source, records_total=total, fields=fields)


def render_field_profile(report: FieldProfileReport) -> str:
    lines = [
        "# Fixture Field Profile",
        "",
        f"Source: {report.source}",
        f"Records: {report.records_total}",
    ]

    for group in ["required", "high_value", "optional"]:
        group_fields = [field for field in report.fields if field.field_group == group]
        lines.extend(["", f"{group.replace('_', ' ').title()} Fields:"])
        for field in group_fields:
            lines.append(
                f"- {field.field_name}: "
                f"{field.present_count}/{field.total_count} "
                f"({_format_percent(field.completeness)})"
            )

    return "\n".join(lines) + "\n"


def _profile_fields() -> list[tuple[str, str]]:
    required_fields: list[str] = []
    for _, field_names, _ in REQUIRED_GROUPS:
        for field_name in field_names:
            if field_name not in required_fields:
                required_fields.append(field_name)

    fields: list[tuple[str, str]] = []
    fields.extend(("required", field_name) for field_name in required_fields)
    fields.extend(("high_value", field_name) for field_name in HIGH_VALUE_FIELDS)
    fields.extend(("optional", field_name) for field_name in OPTIONAL_FIELDS)
    return fields


def _ratio(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total, 4)


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"
