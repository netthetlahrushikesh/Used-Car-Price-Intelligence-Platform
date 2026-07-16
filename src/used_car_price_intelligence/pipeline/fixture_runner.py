"""Run fixture-mode source adapters and summarize quality results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from statistics import mean
from typing import Any

from used_car_price_intelligence.adapters import (
    AdapterRunContext,
    MahindraFirstChoiceFixtureAdapter,
    SpinnyFixtureAdapter,
    TrueValueFixtureAdapter,
)
from used_car_price_intelligence.quality import QualityResult, evaluate_listing, load_source_registry
from used_car_price_intelligence.schema import CanonicalListing


@dataclass(frozen=True)
class FixtureRunSummary:
    source: str
    records_total: int
    silver_valid: int
    pricing_ready: int
    quarantined: int
    required_completeness_avg: float
    high_value_completeness_avg: float
    optional_completeness_avg: float
    overall_completeness_avg: float
    quarantine_reasons: dict[str, int] = field(default_factory=dict)
    warnings: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FixtureOutputPaths:
    raw: Path
    silver: Path
    quarantine: Path
    quality_summary: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "raw": str(self.raw),
            "silver": str(self.silver),
            "quarantine": str(self.quarantine),
            "quality_summary": str(self.quality_summary),
        }


def run_fixture_pipeline(
    *,
    source: str,
    fixture_path: str,
    captured_at: str,
    ingestion_run_id: str,
    registry_path: str = "config/source_registry.yml",
    city: str = "Hyderabad",
    state: str = "Telangana",
) -> tuple[list[CanonicalListing], list[QualityResult], FixtureRunSummary]:
    adapter_by_source = {
        "spinny": SpinnyFixtureAdapter,
        "mahindra_first_choice": MahindraFirstChoiceFixtureAdapter,
        "true_value": TrueValueFixtureAdapter,
    }
    adapter_cls = adapter_by_source.get(source)
    if adapter_cls is None:
        raise ValueError(f"Unsupported fixture source: {source}")

    registry = load_source_registry(registry_path)
    adapter = adapter_cls(fixture_path)
    records = adapter.to_canonical_records(
        AdapterRunContext(
            captured_at=captured_at,
            ingestion_run_id=ingestion_run_id,
            city=city,
            state=state,
        )
    )
    results = [evaluate_listing(record, registry) for record in records]
    summary = summarize_quality_results(source=source, results=results)
    return records, results, summary


def write_fixture_outputs(
    *,
    records: list[CanonicalListing],
    results: list[QualityResult],
    summary: FixtureRunSummary,
    fixture_path: str,
    output_root: str | Path = "data",
    capture_date: str = "2026-06-24",
    run_id: str,
) -> FixtureOutputPaths:
    output_root = Path(output_root)
    source = summary.source
    raw_dir = output_root / "raw" / f"source={source}" / f"capture_date={capture_date}" / f"run_id={run_id}"
    silver_dir = output_root / "silver" / "listings" / f"capture_date={capture_date}"
    quarantine_dir = (
        output_root / "silver" / "quarantine" / f"source={source}" / f"capture_date={capture_date}"
    )
    gold_dir = output_root / "gold" / "quality_summary" / f"capture_date={capture_date}"

    for directory in [raw_dir, silver_dir, quarantine_dir, gold_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / "fixture_source_payload.json"
    silver_path = silver_dir / f"{source}_{run_id}_silver.json"
    quarantine_path = quarantine_dir / f"{run_id}_quarantine.json"
    summary_path = gold_dir / f"{source}_{run_id}_quality_summary.json"

    raw_payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    _write_json(raw_path, raw_payload)

    silver_records = []
    quarantine_records = []
    for record, result in zip(records, results, strict=True):
        record_payload = _json_safe(record.to_dict())
        if result.silver_valid:
            silver_records.append(record_payload)
        if result.quarantine_reasons:
            quarantine_records.append(
                {
                    "source": record.source,
                    "source_listing_id": record.source_listing_id,
                    "listing_url": record.listing_url,
                    "raw_record_hash": record.raw_record_hash,
                    "ingestion_run_id": record.ingestion_run_id,
                    "quarantine_reasons": result.quarantine_reasons,
                    "warnings": result.warnings,
                    "required_completeness_score": result.completeness.required,
                    "high_value_completeness_score": result.completeness.high_value,
                    "optional_completeness_score": result.completeness.optional,
                    "overall_completeness_score": result.completeness.overall,
                }
            )

    _write_json(silver_path, silver_records)
    _write_json(quarantine_path, quarantine_records)
    _write_json(summary_path, summary.to_dict())

    return FixtureOutputPaths(
        raw=raw_path,
        silver=silver_path,
        quarantine=quarantine_path,
        quality_summary=summary_path,
    )


def summarize_quality_results(*, source: str, results: list[QualityResult]) -> FixtureRunSummary:
    if not results:
        return FixtureRunSummary(
            source=source,
            records_total=0,
            silver_valid=0,
            pricing_ready=0,
            quarantined=0,
            required_completeness_avg=0.0,
            high_value_completeness_avg=0.0,
            optional_completeness_avg=0.0,
            overall_completeness_avg=0.0,
        )

    quarantine_reasons: dict[str, int] = {}
    warnings: dict[str, int] = {}
    for result in results:
        for reason in result.quarantine_reasons:
            quarantine_reasons[reason] = quarantine_reasons.get(reason, 0) + 1
        for warning in result.warnings:
            warnings[warning] = warnings.get(warning, 0) + 1

    return FixtureRunSummary(
        source=source,
        records_total=len(results),
        silver_valid=sum(1 for result in results if result.silver_valid),
        pricing_ready=sum(1 for result in results if result.pricing_ready),
        quarantined=sum(1 for result in results if result.quarantine_reasons),
        required_completeness_avg=round(mean(r.completeness.required for r in results), 4),
        high_value_completeness_avg=round(mean(r.completeness.high_value for r in results), 4),
        optional_completeness_avg=round(mean(r.completeness.optional for r in results), 4),
        overall_completeness_avg=round(mean(r.completeness.overall for r in results), 4),
        quarantine_reasons=dict(sorted(quarantine_reasons.items())),
        warnings=dict(sorted(warnings.items())),
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
