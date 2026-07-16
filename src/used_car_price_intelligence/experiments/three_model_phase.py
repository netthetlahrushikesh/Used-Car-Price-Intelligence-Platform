"""Build the three-model experiment package.

The package keeps three candidate modeling tracks explicit:

1. Live scraped trusted deduped dataset.
2. External True Value Kaggle dataset.
3. Combined experimental dataset with lineage columns.
"""

from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

from used_car_price_intelligence.reporting import (
    build_baseline_model_report,
    render_baseline_model_markdown,
)
from used_car_price_intelligence.reporting.modeling_dataset import MODELING_COLUMNS


THREE_MODEL_PHASE_ID = "three_model_phase_20260628"
COMBINED_DATASET_ID = "combined_live_trusted_plus_external_true_value_20260628"
LIVE_ORIGIN = "live_scraped_100k_deduped"
EXTERNAL_ORIGIN = "external_true_value_kaggle"

EXPERIMENT_EXTRA_COLUMNS = [
    "dataset_origin",
    "dataset_origin_label",
    "data_freshness",
    "market_snapshot_date",
    "market_snapshot_year",
    "original_listing_key",
    "original_baseline_split",
]
COMBINED_COLUMNS = [*MODELING_COLUMNS, *EXPERIMENT_EXTRA_COLUMNS]
REQUIRED_COLUMNS = [
    "source",
    "city",
    "brand",
    "model",
    "model_year",
    "fuel_type",
    "transmission",
    "km_driven",
    "listed_price_inr",
    "dataset_origin",
    "market_snapshot_year",
]


def build_three_model_phase_package(
    *,
    live_dataset_csv: str | Path,
    external_dataset_csv: str | Path,
    output_dir: str | Path,
    generated_at: str | None = None,
    test_ratio: float = 0.2,
    min_group_size: int = 3,
    split_seed: str = "three_model_phase_combined_v0",
) -> dict[str, Any]:
    """Build combined experiment outputs for the next modeling phase."""

    resolved_generated_at = generated_at or _utc_now()
    live_path = Path(live_dataset_csv)
    external_path = Path(external_dataset_csv)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    live_rows = _load_modeling_csv(live_path)
    external_rows = _load_modeling_csv(external_path)
    augmented_live = [
        _augment_row(
            row,
            origin=LIVE_ORIGIN,
            label="Live scraped trusted deduped",
            freshness="current_2026_live_scrape",
            key_prefix="live",
            default_snapshot_date="2026-06-27",
            split_seed=split_seed,
            test_ratio=test_ratio,
        )
        for row in live_rows
    ]
    augmented_external = [
        _augment_row(
            row,
            origin=EXTERNAL_ORIGIN,
            label="External True Value Kaggle",
            freshness="historical_2021_external",
            key_prefix="external_true_value_kaggle",
            default_snapshot_date="2021-05-30",
            split_seed=split_seed,
            test_ratio=test_ratio,
        )
        for row in external_rows
    ]
    combined_rows = sorted(
        [*augmented_live, *augmented_external],
        key=lambda row: str(row.get("listing_key") or ""),
    )
    validation = _validate_combined_rows(combined_rows)
    if validation["status"] != "pass":
        failing = ", ".join(check["name"] for check in validation["checks"] if check["status"] != "pass")
        raise ValueError(f"Combined experiment dataset validation failed: {failing}")

    baseline_model = build_baseline_model_report(
        records=combined_rows,
        generated_at=resolved_generated_at,
        test_ratio=test_ratio,
        min_group_size=min_group_size,
        split_seed=split_seed,
    )
    baseline_model["metrics_by_dataset_origin"] = _metrics_by_dataset_origin(
        predictions=baseline_model.get("predictions") or [],
        records=combined_rows,
    )
    manifest = _combined_manifest(
        generated_at=resolved_generated_at,
        live_path=live_path,
        external_path=external_path,
        output_path=output_path,
        live_rows=augmented_live,
        external_rows=augmented_external,
        combined_rows=combined_rows,
        validation=validation,
        baseline_model=baseline_model,
        test_ratio=test_ratio,
        min_group_size=min_group_size,
        split_seed=split_seed,
    )
    registry = _experiment_registry(
        generated_at=resolved_generated_at,
        live_path=live_path,
        external_path=external_path,
        output_path=output_path,
        live_rows=augmented_live,
        external_rows=augmented_external,
        combined_rows=combined_rows,
        combined_baseline=baseline_model,
        manifest=manifest,
    )

    paths = {
        "combined_dataset_csv": output_path / "combined_modeling_dataset.csv",
        "combined_dataset_jsonl": output_path / "combined_modeling_dataset.jsonl",
        "combined_manifest_json": output_path / "combined_dataset_manifest.json",
        "combined_manifest_markdown": output_path / "combined_dataset_manifest.md",
        "combined_baseline_model_json": output_path / "combined_baseline_model.json",
        "combined_baseline_model_markdown": output_path / "combined_baseline_model.md",
        "combined_baseline_predictions_csv": output_path / "combined_baseline_predictions.csv",
        "experiment_registry_json": output_path / "experiment_registry.json",
        "experiment_registry_markdown": output_path / "experiment_registry.md",
    }
    manifest["outputs"] = {key: _path_text(path) for key, path in paths.items()}
    registry["outputs"] = manifest["outputs"]

    _write_csv(paths["combined_dataset_csv"], combined_rows, COMBINED_COLUMNS)
    _write_jsonl(paths["combined_dataset_jsonl"], combined_rows)
    _write_json(paths["combined_manifest_json"], manifest)
    paths["combined_manifest_markdown"].write_text(
        render_combined_manifest_markdown(manifest),
        encoding="utf-8",
    )
    _write_json(paths["combined_baseline_model_json"], baseline_model)
    paths["combined_baseline_model_markdown"].write_text(
        _render_combined_baseline_markdown(baseline_model),
        encoding="utf-8",
    )
    _write_csv(
        paths["combined_baseline_predictions_csv"],
        _decorate_predictions(baseline_model.get("predictions") or [], combined_rows),
        [
            "listing_key",
            "dataset_origin",
            "source",
            "city",
            "brand",
            "model",
            "model_year",
            "fuel_type",
            "transmission",
            "ownership",
            "km_driven",
            "actual_price_inr",
            "predicted_price_inr",
            "absolute_error_inr",
            "absolute_percentage_error",
            "prediction_level",
            "training_group_count",
        ],
    )
    _write_json(paths["experiment_registry_json"], registry)
    paths["experiment_registry_markdown"].write_text(
        render_experiment_registry_markdown(registry),
        encoding="utf-8",
    )

    return {
        "manifest": manifest,
        "registry": registry,
        "baseline_model": baseline_model,
        "output_paths": {key: _path_text(path) for key, path in paths.items()},
    }


def render_combined_manifest_markdown(manifest: dict[str, Any]) -> str:
    validation = manifest.get("validation") or {}
    counts = manifest.get("counts") or {}
    split = manifest.get("baseline_split") or {}
    lines = [
        "# Combined Modeling Dataset Manifest",
        "",
        f"Dataset id: `{manifest.get('dataset_id', '')}`",
        f"Experiment id: `{manifest.get('experiment_id', '')}`",
        f"Rows: {manifest.get('records_total', 0):,}",
        f"Validation: `{validation.get('status', '')}`",
        "",
        "## Input Rows",
        "",
        "| Input | Rows |",
        "| --- | ---: |",
        f"| Live scraped trusted deduped | {counts.get('live_rows', 0):,} |",
        f"| External True Value Kaggle | {counts.get('external_rows', 0):,} |",
        f"| Combined | {counts.get('combined_rows', 0):,} |",
        "",
        "## Baseline Split",
        "",
        f"- Train rows: {split.get('train_rows', 0):,}",
        f"- Test rows: {split.get('test_rows', 0):,}",
        "",
        "## Dataset Origin Mix",
        "",
        "| Origin | Rows | Share |",
        "| --- | ---: | ---: |",
    ]
    for item in counts.get("by_dataset_origin") or []:
        lines.append(f"| {item['value']} | {item['count']:,} | {item['share_pct']:.2f}% |")
    lines.extend(["", "## Source Mix", "", "| Source | Rows | Share |", "| --- | ---: | ---: |"])
    for item in counts.get("by_source") or []:
        lines.append(f"| {item['value']} | {item['count']:,} | {item['share_pct']:.2f}% |")
    lines.extend(["", "## Validation Checks", ""])
    for check in validation.get("checks") or []:
        lines.append(f"- {check.get('name', '')}: {check.get('status', '')}")
    lines.extend(["", "## Policy", ""])
    for item in manifest.get("policy") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Outputs", ""])
    for key, value in sorted((manifest.get("outputs") or {}).items()):
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def render_experiment_registry_markdown(registry: dict[str, Any]) -> str:
    lines = [
        "# Three Model Phase Registry",
        "",
        f"Experiment id: `{registry.get('experiment_id', '')}`",
        f"Generated at: `{registry.get('generated_at', '')}`",
        "",
        "## Model Candidates",
        "",
        "| Candidate | Rows | Source Scope | Primary Use |",
        "| --- | ---: | --- | --- |",
    ]
    for candidate in registry.get("model_candidates") or []:
        lines.append(
            "| {name} | {rows:,} | {source_scope} | {primary_use} |".format(
                name=candidate.get("name", ""),
                rows=int(candidate.get("rows") or 0),
                source_scope=candidate.get("source_scope", ""),
                primary_use=candidate.get("primary_use", ""),
            )
        )
    lines.extend(["", "## Baseline Snapshot", "", "| Candidate | MAE | MAPE | Within 20% |", "| --- | ---: | ---: | ---: |"])
    for candidate in registry.get("model_candidates") or []:
        metrics = candidate.get("baseline_metrics") or {}
        lines.append(
            "| {name} | {mae} | {mape} | {within20} |".format(
                name=candidate.get("name", ""),
                mae=_format_number(metrics.get("mae")),
                mape=_format_pct(metrics.get("mape")),
                within20=_format_pct(metrics.get("within_20_pct")),
            )
        )
    lines.extend(["", "## Next Step Checklist", ""])
    for item in registry.get("next_step_checklist") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Guardrails", ""])
    for item in registry.get("guardrails") or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _load_modeling_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Modeling CSV does not exist: {path}")
    with path.open(newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        if reader.fieldnames != MODELING_COLUMNS:
            raise ValueError(f"Unexpected modeling columns in {path}: {reader.fieldnames}")
        return [dict(row) for row in reader]


def _augment_row(
    row: dict[str, Any],
    *,
    origin: str,
    label: str,
    freshness: str,
    key_prefix: str,
    default_snapshot_date: str,
    split_seed: str,
    test_ratio: float,
) -> dict[str, Any]:
    original_key = str(row.get("listing_key") or "").strip()
    source = str(row.get("source") or "").strip()
    listing_key = f"{key_prefix}::{source}::{original_key}"
    snapshot_date = str(row.get("capture_date") or default_snapshot_date).strip() or default_snapshot_date
    augmented = dict(row)
    augmented["original_listing_key"] = original_key
    augmented["listing_key"] = listing_key
    augmented["original_baseline_split"] = row.get("baseline_split")
    augmented["baseline_split"] = _split_for_key(listing_key, seed=split_seed, test_ratio=test_ratio)
    augmented["dataset_origin"] = origin
    augmented["dataset_origin_label"] = label
    augmented["data_freshness"] = freshness
    augmented["market_snapshot_date"] = snapshot_date
    augmented["market_snapshot_year"] = _year_from_date(snapshot_date)
    return augmented


def _combined_manifest(
    *,
    generated_at: str,
    live_path: Path,
    external_path: Path,
    output_path: Path,
    live_rows: list[dict[str, Any]],
    external_rows: list[dict[str, Any]],
    combined_rows: list[dict[str, Any]],
    validation: dict[str, Any],
    baseline_model: dict[str, Any],
    test_ratio: float,
    min_group_size: int,
    split_seed: str,
) -> dict[str, Any]:
    return {
        "manifest_version": "three_model_phase_combined_dataset_v0.1",
        "experiment_id": THREE_MODEL_PHASE_ID,
        "dataset_id": COMBINED_DATASET_ID,
        "generated_at": generated_at,
        "records_total": len(combined_rows),
        "columns": COMBINED_COLUMNS,
        "target": "listed_price_inr",
        "inputs": {
            "live_dataset_csv": _path_text(live_path),
            "external_dataset_csv": _path_text(external_path),
        },
        "output_dir": _path_text(output_path),
        "counts": {
            "live_rows": len(live_rows),
            "external_rows": len(external_rows),
            "combined_rows": len(combined_rows),
            "by_dataset_origin": _count_values(combined_rows, "dataset_origin"),
            "by_source": _count_values(combined_rows, "source"),
            "by_market_snapshot_year": _count_values(combined_rows, "market_snapshot_year"),
        },
        "baseline_split": baseline_model.get("split") or {},
        "validation": validation,
        "policy": [
            "This combined dataset is experimental and lineage-explicit.",
            "Live scraped rows and external historical Kaggle rows remain available as separate model candidates.",
            "The combined dataset must use dataset_origin and market_snapshot_year during serious ML modeling.",
            "Do not treat combined baseline metrics as production valuation metrics until temporal leakage and source bias are reviewed.",
            f"Baseline min_group_size is {min_group_size}; split seed is {split_seed}; test_ratio is {test_ratio}.",
        ],
    }


def _experiment_registry(
    *,
    generated_at: str,
    live_path: Path,
    external_path: Path,
    output_path: Path,
    live_rows: list[dict[str, Any]],
    external_rows: list[dict[str, Any]],
    combined_rows: list[dict[str, Any]],
    combined_baseline: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    live_baseline = _load_neighbor_json(live_path, "baseline_model.json")
    external_baseline = _load_neighbor_json(external_path, "baseline_model.json")
    return {
        "registry_version": "three_model_phase_registry_v0.1",
        "experiment_id": THREE_MODEL_PHASE_ID,
        "generated_at": generated_at,
        "model_candidates": [
            {
                "id": "live_trusted_deduped_model",
                "name": "Live trusted deduped model",
                "rows": len(live_rows),
                "dataset_path": _path_text(live_path),
                "source_scope": "Live scraped trusted sources: True Value, Mahindra First Choice, Spinny.",
                "primary_use": "Current-market benchmark and portfolio credibility.",
                "baseline_metrics": _metrics_from_baseline(live_baseline),
                "risk": "Small dataset and source imbalance; still closest to current market.",
            },
            {
                "id": "external_true_value_model",
                "name": "External True Value model",
                "rows": len(external_rows),
                "dataset_path": _path_text(external_path),
                "source_scope": "Historical external True Value Kaggle rows only.",
                "primary_use": "Larger modeling sandbox and True Value-only pattern learning.",
                "baseline_metrics": _metrics_from_baseline(external_baseline),
                "risk": "Historical 2021 data and single-source bias.",
            },
            {
                "id": "combined_live_external_model",
                "name": "Combined live + external model",
                "rows": len(combined_rows),
                "dataset_path": _path_text(output_path / "combined_modeling_dataset.csv"),
                "source_scope": "Live trusted deduped rows plus separated external True Value rows.",
                "primary_use": "Experimental higher-row-count model with lineage features.",
                "baseline_metrics": _metrics_from_baseline(combined_baseline),
                "risk": "Mixes 2021 historical external prices with 2026 scraped market rows; must include lineage/time features.",
            },
        ],
        "combined_manifest": {
            "dataset_id": manifest["dataset_id"],
            "records_total": manifest["records_total"],
            "validation": manifest["validation"],
        },
        "next_step_checklist": [
            "Run EDA separately for each candidate before fitting stronger models.",
            "Build the same train/test protocol for all three candidates.",
            "For the combined model, include dataset_origin and market_snapshot_year as explicit features.",
            "Compare metrics overall and by dataset_origin/source/city/brand_model.",
            "Select the main portfolio model based on honest validation, not row count alone.",
        ],
        "guardrails": [
            "Do not rename 3,496 live unique rows as 3,497.",
            "Do not merge the external dataset into live scraped gold snapshots.",
            "Do not train on repeated 103k observations as independent cars.",
            "Do not present the combined model as production-grade until temporal bias is reviewed.",
        ],
    }


def _validate_combined_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [str(row.get("listing_key") or "") for row in rows]
    duplicate_keys = len(keys) - len(set(keys))
    missing_required = {
        column: _field_completeness(rows, column)["missing"]
        for column in REQUIRED_COLUMNS
    }
    invalid_prices = sum(1 for row in rows if _int_or_none(row.get("listed_price_inr")) in (None, 0))
    origin_counts = Counter(str(row.get("dataset_origin") or "") for row in rows)
    checks = [
        _check("listing_keys_are_unique_after_origin_prefix", duplicate_keys == 0),
        _check("required_fields_complete", not any(missing_required.values())),
        _check("target_price_positive", invalid_prices == 0),
        _check("both_dataset_origins_present", set(origin_counts) == {LIVE_ORIGIN, EXTERNAL_ORIGIN}),
    ]
    return {
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "checks": checks,
        "duplicate_listing_keys": duplicate_keys,
        "missing_required": missing_required,
        "invalid_price_count": invalid_prices,
        "dataset_origin_counts": dict(sorted(origin_counts.items())),
    }


def _metrics_by_dataset_origin(
    *,
    predictions: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    row_by_key = {str(row.get("listing_key") or ""): row for row in records}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for prediction in predictions:
        key = str(prediction.get("listing_key") or "")
        origin = str(row_by_key.get(key, {}).get("dataset_origin") or "unknown")
        grouped.setdefault(origin, []).append(prediction)
    return {origin: _prediction_metrics(items) for origin, items in sorted(grouped.items())}


def _decorate_predictions(
    predictions: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    row_by_key = {str(row.get("listing_key") or ""): row for row in records}
    decorated = []
    for prediction in predictions:
        key = str(prediction.get("listing_key") or "")
        row = row_by_key.get(key, {})
        decorated.append({**prediction, "dataset_origin": row.get("dataset_origin")})
    return decorated


def _render_combined_baseline_markdown(model: dict[str, Any]) -> str:
    base = render_baseline_model_markdown(model).rstrip()
    lines = [
        base,
        "",
        "## Metrics By Dataset Origin",
        "",
        "| Dataset Origin | Rows | MAE | MAPE | Within 20% |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for origin, metrics in (model.get("metrics_by_dataset_origin") or {}).items():
        lines.append(
            "| {origin} | {count} | {mae} | {mape} | {within20} |".format(
                origin=origin,
                count=metrics.get("count", 0),
                mae=_format_number(metrics.get("mae")),
                mape=_format_pct(metrics.get("mape")),
                within20=_format_pct(metrics.get("within_20_pct")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _metrics_from_baseline(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload.get("metrics") or {}
    return {
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "median_absolute_error": metrics.get("median_absolute_error"),
        "mape": metrics.get("mape"),
        "within_20_pct": metrics.get("within_20_pct"),
    }


def _load_neighbor_json(csv_path: Path, filename: str) -> dict[str, Any]:
    path = csv_path.parent / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _prediction_metrics(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    if not predictions:
        return {
            "count": 0,
            "mae": None,
            "median_absolute_error": None,
            "mape": None,
            "within_20_pct": None,
        }
    errors = [_float_value(row.get("absolute_error_inr")) for row in predictions]
    ape_values = [
        _float_value(row.get("absolute_percentage_error"))
        for row in predictions
        if row.get("absolute_percentage_error") not in (None, "")
    ]
    return {
        "count": len(predictions),
        "mae": round(sum(errors) / len(errors), 2),
        "median_absolute_error": round(float(median(errors)), 2),
        "mape": round(sum(ape_values) / len(ape_values), 6) if ape_values else None,
        "within_20_pct": round(sum(1 for value in ape_values if value <= 0.20) / len(ape_values) * 100, 2)
        if ape_values
        else None,
    }


def _count_values(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key) or "unknown") for row in rows)
    total = max(1, len(rows))
    return [
        {"value": value, "count": count, "share_pct": round(count / total * 100, 4)}
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _split_for_key(listing_key: str, *, seed: str, test_ratio: float) -> str:
    material = f"{seed}|{listing_key}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    fraction = int(digest, 16) / float(0xFFFFFFFFFFFF)
    return "test" if fraction < test_ratio else "train"


def _year_from_date(value: str) -> int | None:
    text = str(value or "").strip()
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return None


def _field_completeness(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    present = sum(1 for row in rows if _has_value(row.get(column)))
    total = len(rows)
    return {
        "present": present,
        "missing": total - present,
        "completeness_pct": round(present / total * 100, 4) if total else 0,
    }


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _check(name: str, ok: bool) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail"}


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, sort_keys=True) + "\n")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _csv_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list | dict):
        return json.dumps(value, sort_keys=True)
    return value


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).replace(",", "").strip()
    if text == "":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _float_value(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    return float(str(value).replace(",", "").strip())


def _format_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _format_pct(value: Any) -> str:
    if value is None:
        return ""
    number = float(value)
    if number <= 1:
        number *= 100
    return f"{number:.2f}%"


def _path_text(path: Path) -> str:
    return path.as_posix()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
