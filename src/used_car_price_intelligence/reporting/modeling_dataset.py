"""Analysis-ready dataset packaging and transparent baseline modeling."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import json
from math import sqrt
from pathlib import Path
from statistics import median
from typing import Any


MODELING_DATASET_VERSION = "modeling_dataset_v0.1"
BASELINE_MODEL_VERSION = "comparable_median_baseline_v0.1"

MODELING_COLUMNS = [
    "listing_key",
    "source",
    "source_listing_id",
    "listing_url",
    "capture_date",
    "captured_at",
    "city",
    "state",
    "brand",
    "model",
    "variant",
    "brand_model",
    "model_year",
    "vehicle_age_years",
    "fuel_type",
    "transmission",
    "km_driven",
    "km_bucket_10000",
    "ownership",
    "registration_code",
    "listed_price_inr",
    "price_lakh",
    "is_available",
    "observation_count",
    "first_seen_at",
    "last_seen_at",
    "listing_identity_basis",
    "vehicle_fingerprint",
    "run_id",
    "baseline_split",
]

MODELING_REQUIRED_COLUMNS = [
    "source",
    "city",
    "brand",
    "model",
    "model_year",
    "fuel_type",
    "transmission",
    "km_driven",
    "listed_price_inr",
]

BASELINE_LEVELS = [
    (
        "city_brand_model_year_fuel_transmission_ownership",
        ["city", "brand", "model", "model_year", "fuel_type", "transmission", "ownership"],
    ),
    (
        "brand_model_year_fuel_transmission_ownership",
        ["brand", "model", "model_year", "fuel_type", "transmission", "ownership"],
    ),
    (
        "brand_model_year_fuel_transmission",
        ["brand", "model", "model_year", "fuel_type", "transmission"],
    ),
    ("brand_model_fuel_transmission", ["brand", "model", "fuel_type", "transmission"]),
    ("brand_model", ["brand", "model"]),
    ("brand", ["brand"]),
    ("global", []),
]


def build_modeling_dataset_package(
    *,
    snapshot_manifest_path: str | Path,
    lifecycle_index_path: str | Path | None = None,
    dataset_id: str | None = None,
    generated_at: str | None = None,
    test_ratio: float = 0.2,
    min_group_size: int = 3,
    split_seed: str = "snapshot_baseline_v0",
) -> dict[str, Any]:
    """Build all in-memory artifacts for the phase-final modeling dataset."""

    manifest_path = Path(snapshot_manifest_path)
    snapshot_manifest = _load_json_object(manifest_path)
    lifecycle_path = _resolve_lifecycle_path(
        lifecycle_index_path=lifecycle_index_path,
        snapshot_manifest=snapshot_manifest,
        snapshot_manifest_path=manifest_path,
    )
    lifecycle = _load_json_object(lifecycle_path)
    snapshot_year = _snapshot_year(snapshot_manifest)
    resolved_dataset_id = dataset_id or f"{snapshot_manifest.get('snapshot_id', 'snapshot')}_modeling_v0"
    resolved_generated_at = generated_at or _utc_now()

    records = _records_from_lifecycle(
        lifecycle=lifecycle,
        snapshot_year=snapshot_year,
        split_seed=split_seed,
        test_ratio=test_ratio,
    )
    validation = _validate_records(
        records=records,
        snapshot_manifest=snapshot_manifest,
        lifecycle=lifecycle,
    )
    data_dictionary = build_modeling_data_dictionary(generated_at=resolved_generated_at)
    eda_summary = build_eda_summary(
        records=records,
        snapshot_manifest=snapshot_manifest,
        lifecycle=lifecycle,
        generated_at=resolved_generated_at,
    )
    baseline_model = build_baseline_model_report(
        records=records,
        generated_at=resolved_generated_at,
        test_ratio=test_ratio,
        min_group_size=min_group_size,
        split_seed=split_seed,
    )
    package_manifest = {
        "manifest_version": MODELING_DATASET_VERSION,
        "dataset_id": resolved_dataset_id,
        "generated_at": resolved_generated_at,
        "snapshot_id": str(snapshot_manifest.get("snapshot_id") or ""),
        "snapshot_date": str(snapshot_manifest.get("snapshot_date") or ""),
        "lifecycle_id": str(lifecycle.get("lifecycle_id") or ""),
        "collection_id": str(snapshot_manifest.get("collection_id") or lifecycle.get("collection_id") or ""),
        "inputs": {
            "snapshot_manifest": _path_text(manifest_path),
            "lifecycle_index": _path_text(lifecycle_path),
        },
        "records_total": len(records),
        "columns": MODELING_COLUMNS,
        "target": "listed_price_inr",
        "baseline_model_id": baseline_model["model_id"],
        "baseline_split": baseline_model["split"],
        "validation": validation,
        "policy": {
            "source_scope": "Trusted, dealer/evaluator-backed sources only for this phase.",
            "row_scope": "One latest pricing-ready observation per lifecycle listing key.",
            "model_scope": (
                "Transparent comparable-median baseline. This is an explainable benchmark, "
                "not the final production pricing model."
            ),
            "source_feature_policy": (
                "Source is retained for auditing and bias checks. The baseline predictor does not "
                "use source in its primary comparable hierarchy."
            ),
        },
    }
    return {
        "manifest": package_manifest,
        "records": records,
        "data_dictionary": data_dictionary,
        "eda_summary": eda_summary,
        "baseline_model": baseline_model,
    }


def build_modeling_data_dictionary(*, generated_at: str | None = None) -> dict[str, Any]:
    descriptions = {
        "listing_key": ("string", "Lifecycle-stable source listing identity.", "lifecycle", True),
        "source": ("string", "Trusted source platform name.", "canonical", True),
        "source_listing_id": ("string", "Source-native listing id when available.", "canonical", False),
        "listing_url": ("string", "Public listing URL after source normalization.", "canonical", False),
        "capture_date": ("date", "Date when the source-city run captured the observation.", "lifecycle", True),
        "captured_at": ("datetime", "UTC timestamp for the source observation.", "canonical", False),
        "city": ("string", "Market city used for geographic comparables.", "canonical", True),
        "state": ("string", "Indian state or region for the market city.", "canonical", False),
        "brand": ("string", "Normalized vehicle brand.", "canonical", True),
        "model": ("string", "Normalized vehicle model.", "canonical", True),
        "variant": ("string", "Normalized trim or variant when confidently available.", "canonical", False),
        "brand_model": ("string", "Derived brand plus model group.", "derived", True),
        "model_year": ("integer", "Model or manufacture year used for age features.", "canonical", True),
        "vehicle_age_years": ("integer", "Snapshot year minus model_year.", "derived", True),
        "fuel_type": ("string", "Normalized fuel type.", "canonical", True),
        "transmission": ("string", "Normalized transmission type.", "canonical", True),
        "km_driven": ("integer", "Odometer reading in kilometers.", "canonical", True),
        "km_bucket_10000": ("integer", "Kilometer bucket rounded down to nearest 10,000.", "derived", False),
        "ownership": ("integer", "Ownership count as parsed from source listing.", "canonical", False),
        "registration_code": ("string", "RTO/registration prefix when available.", "canonical", False),
        "listed_price_inr": ("integer", "Listed vehicle price in Indian rupees. This is the target.", "canonical", True),
        "price_lakh": ("float", "Listed price divided by 100,000 for EDA readability.", "derived", True),
        "is_available": ("boolean", "Availability flag when source exposes it.", "canonical", False),
        "observation_count": ("integer", "Number of observations collapsed into the lifecycle entity.", "lifecycle", False),
        "first_seen_at": ("datetime", "First observed timestamp for the lifecycle listing key.", "lifecycle", False),
        "last_seen_at": ("datetime", "Latest observed timestamp for the lifecycle listing key.", "lifecycle", False),
        "listing_identity_basis": ("string", "Field used to build the lifecycle listing key.", "lifecycle", False),
        "vehicle_fingerprint": ("string", "Conservative duplicate-review fingerprint, not a merge key.", "lifecycle", False),
        "run_id": ("string", "Acquisition run id that produced the latest observation.", "lifecycle", False),
        "baseline_split": ("string", "Deterministic train/test split used by the baseline model.", "derived", False),
    }
    return {
        "dictionary_version": MODELING_DATASET_VERSION,
        "generated_at": generated_at or _utc_now(),
        "target_column": "listed_price_inr",
        "required_for_modeling": MODELING_REQUIRED_COLUMNS,
        "columns": [
            {
                "name": name,
                "type": descriptions[name][0],
                "description": descriptions[name][1],
                "origin": descriptions[name][2],
                "required_for_modeling": descriptions[name][3],
            }
            for name in MODELING_COLUMNS
        ],
    }


def build_eda_summary(
    *,
    records: list[dict[str, Any]],
    snapshot_manifest: dict[str, Any],
    lifecycle: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    counts = {
        "source": _count_values(records, "source"),
        "city": _count_values(records, "city"),
        "brand": _count_values(records, "brand"),
        "model": _count_values(records, "model"),
        "brand_model": _count_values(records, "brand_model"),
        "fuel_type": _count_values(records, "fuel_type"),
        "transmission": _count_values(records, "transmission"),
        "ownership": _count_values(records, "ownership"),
        "model_year": _count_values(records, "model_year"),
    }
    numeric = {
        "listed_price_inr": _summary_stats(_numbers(records, "listed_price_inr")),
        "price_lakh": _summary_stats(_numbers(records, "price_lakh")),
        "km_driven": _summary_stats(_numbers(records, "km_driven")),
        "vehicle_age_years": _summary_stats(_numbers(records, "vehicle_age_years")),
    }
    price_breakdowns = {
        "by_source": _group_numeric_summary(records, group_key="source", value_key="listed_price_inr"),
        "by_city": _top_group_numeric_summary(records, group_key="city", value_key="listed_price_inr", limit=20),
        "by_brand": _top_group_numeric_summary(records, group_key="brand", value_key="listed_price_inr", limit=20),
        "by_brand_model": _top_group_numeric_summary(
            records,
            group_key="brand_model",
            value_key="listed_price_inr",
            limit=25,
        ),
    }
    field_completeness = {
        column: _field_completeness(records, column)
        for column in MODELING_COLUMNS
    }
    blind_spots = _eda_blind_spots(records=records, counts=counts)
    return {
        "summary_version": MODELING_DATASET_VERSION,
        "generated_at": generated_at or _utc_now(),
        "snapshot": {
            "snapshot_id": str(snapshot_manifest.get("snapshot_id") or ""),
            "snapshot_date": str(snapshot_manifest.get("snapshot_date") or ""),
            "pricing_ready_rows": _int_value(_as_dict(snapshot_manifest.get("totals")).get("pricing_ready")),
            "unique_listing_keys": _int_value(_as_dict(lifecycle.get("totals")).get("unique_listing_keys")),
        },
        "records_total": len(records),
        "field_completeness": field_completeness,
        "counts": counts,
        "numeric_summary": numeric,
        "price_breakdowns": price_breakdowns,
        "blind_spots": blind_spots,
        "readiness": {
            "status": "baseline_ready" if not blind_spots["blocking"] else "blocked",
            "decision": (
                "Use this dataset for EDA and transparent baseline modeling. Do not treat it as the "
                "final high-scale model dataset until repeated snapshots improve balance."
            ),
        },
    }


def build_baseline_model_report(
    *,
    records: list[dict[str, Any]],
    generated_at: str | None = None,
    test_ratio: float = 0.2,
    min_group_size: int = 3,
    split_seed: str = "snapshot_baseline_v0",
) -> dict[str, Any]:
    rows = [row for row in records if _int_value(row.get("listed_price_inr")) > 0]
    train_rows = [row for row in rows if row.get("baseline_split") == "train"]
    test_rows = [row for row in rows if row.get("baseline_split") == "test"]
    if rows and (not train_rows or not test_rows):
        train_rows, test_rows = _fallback_train_test_split(rows, test_ratio=test_ratio)

    group_tables = _build_baseline_group_tables(train_rows)
    predictions = [
        _predict_baseline(row, group_tables=group_tables, min_group_size=min_group_size)
        for row in test_rows
    ]
    global_predictions = [
        {
            **prediction,
            "predicted_price_inr": group_tables["global"][()]["median_price_inr"],
            "prediction_level": "global",
            "training_group_count": group_tables["global"][()]["count"],
        }
        for prediction in predictions
    ]
    evaluated_predictions = [_evaluate_prediction(prediction) for prediction in predictions]
    evaluated_global = [_evaluate_prediction(prediction) for prediction in global_predictions]
    return {
        "model_id": "baseline_comparable_median_v0",
        "model_version": BASELINE_MODEL_VERSION,
        "generated_at": generated_at or _utc_now(),
        "target": "listed_price_inr",
        "split": {
            "seed": split_seed,
            "test_ratio": test_ratio,
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
        },
        "training_policy": {
            "algorithm": "Hierarchical comparable median fallback.",
            "min_group_size": min_group_size,
            "levels": [
                {"name": name, "features": features}
                for name, features in BASELINE_LEVELS
            ],
            "source_usage": "Source is excluded from the prediction hierarchy and used only for audit slices.",
        },
        "metrics": _prediction_metrics(evaluated_predictions),
        "global_median_metrics": _prediction_metrics(evaluated_global),
        "metrics_by_source": _metrics_by_group(evaluated_predictions, "source"),
        "metrics_by_prediction_level": _metrics_by_group(evaluated_predictions, "prediction_level"),
        "group_coverage": _group_coverage(group_tables),
        "predictions": evaluated_predictions,
        "interpretation": {
            "decision": "Transparent benchmark only.",
            "useful_for": [
                "Establishing a first error baseline.",
                "Explaining comparable-based pricing logic.",
                "Finding where source/city/model coverage is too thin.",
            ],
            "not_yet_useful_for": [
                "Final fair-price decisions.",
                "User-facing valuation claims.",
                "High-confidence rare-model pricing.",
            ],
        },
    }


def write_modeling_dataset_package(
    *,
    output_dir: str | Path,
    package: dict[str, Any],
) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest = dict(package["manifest"])
    records = list(package["records"])
    data_dictionary = dict(package["data_dictionary"])
    eda_summary = dict(package["eda_summary"])
    baseline_model = dict(package["baseline_model"])

    paths = {
        "dataset_csv": output_path / "listings_modeling_dataset.csv",
        "dataset_jsonl": output_path / "listings_modeling_dataset.jsonl",
        "data_dictionary_json": output_path / "data_dictionary.json",
        "data_dictionary_markdown": output_path / "data_dictionary.md",
        "eda_summary_json": output_path / "eda_summary.json",
        "eda_summary_markdown": output_path / "eda_summary.md",
        "baseline_model_json": output_path / "baseline_model.json",
        "baseline_model_markdown": output_path / "baseline_model.md",
        "baseline_predictions_csv": output_path / "baseline_predictions.csv",
        "dataset_manifest_json": output_path / "dataset_manifest.json",
        "dataset_manifest_markdown": output_path / "dataset_manifest.md",
    }
    _write_csv(paths["dataset_csv"], records, MODELING_COLUMNS)
    _write_jsonl(paths["dataset_jsonl"], records)
    _write_json(paths["data_dictionary_json"], data_dictionary)
    paths["data_dictionary_markdown"].write_text(
        render_data_dictionary_markdown(data_dictionary),
        encoding="utf-8",
    )
    _write_json(paths["eda_summary_json"], eda_summary)
    paths["eda_summary_markdown"].write_text(render_eda_summary_markdown(eda_summary), encoding="utf-8")
    _write_json(paths["baseline_model_json"], baseline_model)
    paths["baseline_model_markdown"].write_text(
        render_baseline_model_markdown(baseline_model),
        encoding="utf-8",
    )
    _write_csv(
        paths["baseline_predictions_csv"],
        list(baseline_model.get("predictions") or []),
        [
            "listing_key",
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
    output_paths = {key: _path_text(value) for key, value in paths.items()}
    manifest["outputs"] = output_paths
    _write_json(paths["dataset_manifest_json"], manifest)
    paths["dataset_manifest_markdown"].write_text(
        render_dataset_manifest_markdown(manifest),
        encoding="utf-8",
    )
    return output_paths


def render_data_dictionary_markdown(data_dictionary: dict[str, Any]) -> str:
    lines = [
        "# Modeling Data Dictionary",
        "",
        f"Version: `{data_dictionary.get('dictionary_version', '')}`",
        f"Target column: `{data_dictionary.get('target_column', '')}`",
        "",
        "| Column | Type | Required | Origin | Description |",
        "| --- | --- | --- | --- | --- |",
    ]
    for column in list(data_dictionary.get("columns") or []):
        if not isinstance(column, dict):
            continue
        required = "yes" if column.get("required_for_modeling") else "no"
        lines.append(
            "| {name} | {type} | {required} | {origin} | {description} |".format(
                name=column.get("name", ""),
                type=column.get("type", ""),
                required=required,
                origin=column.get("origin", ""),
                description=column.get("description", ""),
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_eda_summary_markdown(summary: dict[str, Any]) -> str:
    snapshot = _as_dict(summary.get("snapshot"))
    numeric = _as_dict(summary.get("numeric_summary"))
    readiness = _as_dict(summary.get("readiness"))
    blind_spots = _as_dict(summary.get("blind_spots"))
    lines = [
        "# Final Snapshot EDA Summary",
        "",
        f"Snapshot id: `{snapshot.get('snapshot_id', '')}`",
        f"Records: {summary.get('records_total', 0):,}",
        f"Readiness: `{readiness.get('status', '')}`",
        "",
        "## Price And Usage",
        "",
        "| Field | Count | Min | P25 | Median | P75 | P95 | Max | Mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in ["listed_price_inr", "price_lakh", "km_driven", "vehicle_age_years"]:
        stats = _as_dict(numeric.get(key))
        lines.append(
            "| {key} | {count} | {min} | {p25} | {median} | {p75} | {p95} | {max} | {mean} |".format(
                key=key,
                count=stats.get("count", 0),
                min=_format_number(stats.get("min")),
                p25=_format_number(stats.get("p25")),
                median=_format_number(stats.get("median")),
                p75=_format_number(stats.get("p75")),
                p95=_format_number(stats.get("p95")),
                max=_format_number(stats.get("max")),
                mean=_format_number(stats.get("mean")),
            )
        )

    lines.extend(["", "## Source Mix", "", "| Source | Rows | Share |", "| --- | ---: | ---: |"])
    for item in _as_list(_as_dict(summary.get("counts")).get("source")):
        lines.append(f"| {item.get('value', '')} | {item.get('count', 0):,} | {item.get('share_pct', 0):.2f}% |")

    lines.extend(["", "## Top Cities", "", "| City | Rows | Share |", "| --- | ---: | ---: |"])
    for item in _as_list(_as_dict(summary.get("counts")).get("city"))[:15]:
        lines.append(f"| {item.get('value', '')} | {item.get('count', 0):,} | {item.get('share_pct', 0):.2f}% |")

    lines.extend(["", "## Top Brand-Model Groups", "", "| Brand Model | Rows | Share |", "| --- | ---: | ---: |"])
    for item in _as_list(_as_dict(summary.get("counts")).get("brand_model"))[:20]:
        lines.append(f"| {item.get('value', '')} | {item.get('count', 0):,} | {item.get('share_pct', 0):.2f}% |")

    lines.extend(["", "## Blind Spots", ""])
    for warning in list(blind_spots.get("warnings") or []):
        lines.append(f"- {warning}")
    for blocker in list(blind_spots.get("blocking") or []):
        lines.append(f"- BLOCKING: {blocker}")
    if not blind_spots.get("warnings") and not blind_spots.get("blocking"):
        lines.append("No blocking EDA blind spots were detected.")
    lines.extend(["", "## Decision", "", str(readiness.get("decision", "")), ""])
    return "\n".join(lines)


def render_baseline_model_markdown(model: dict[str, Any]) -> str:
    metrics = _as_dict(model.get("metrics"))
    global_metrics = _as_dict(model.get("global_median_metrics"))
    split = _as_dict(model.get("split"))
    policy = _as_dict(model.get("training_policy"))
    lines = [
        "# Baseline Pricing Model",
        "",
        f"Model id: `{model.get('model_id', '')}`",
        f"Version: `{model.get('model_version', '')}`",
        f"Target: `{model.get('target', '')}`",
        "",
        "## Split",
        "",
        f"- Train rows: {split.get('train_rows', 0):,}",
        f"- Test rows: {split.get('test_rows', 0):,}",
        f"- Test ratio: {split.get('test_ratio', 0):.2f}",
        "",
        "## Method",
        "",
        f"- Algorithm: {policy.get('algorithm', '')}",
        f"- Minimum comparable group size: {policy.get('min_group_size', 0)}",
        f"- Source usage: {policy.get('source_usage', '')}",
        "",
        "## Metrics",
        "",
        "| Model | Test Rows | MAE | RMSE | MdAE | MAPE | MdAPE | Within 10% | Within 20% |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        _metric_row("Comparable median", metrics),
        _metric_row("Global median only", global_metrics),
        "",
        "## Metrics By Source",
        "",
        "| Source | Rows | MAE | MAPE | Within 20% |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for source, item in sorted(_as_dict(model.get("metrics_by_source")).items()):
        lines.append(
            "| {source} | {count} | {mae} | {mape} | {within20} |".format(
                source=source,
                count=item.get("count", 0),
                mae=_format_number(item.get("mae")),
                mape=_format_pct(item.get("mape")),
                within20=_format_pct(item.get("within_20_pct")),
            )
        )

    lines.extend(["", "## Prediction Levels", "", "| Level | Rows | MAE | MAPE |", "| --- | ---: | ---: | ---: |"])
    for level, item in sorted(_as_dict(model.get("metrics_by_prediction_level")).items()):
        lines.append(
            f"| {level} | {item.get('count', 0)} | {_format_number(item.get('mae'))} | {_format_pct(item.get('mape'))} |"
        )
    lines.extend(["", "## Interpretation", ""])
    interpretation = _as_dict(model.get("interpretation"))
    lines.append(f"Decision: {interpretation.get('decision', '')}")
    lines.append("")
    lines.append("Useful for:")
    for item in list(interpretation.get("useful_for") or []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Not yet useful for:")
    for item in list(interpretation.get("not_yet_useful_for") or []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def render_dataset_manifest_markdown(manifest: dict[str, Any]) -> str:
    validation = _as_dict(manifest.get("validation"))
    split = _as_dict(manifest.get("baseline_split"))
    outputs = _as_dict(manifest.get("outputs"))
    lines = [
        "# Modeling Dataset Manifest",
        "",
        f"Dataset id: `{manifest.get('dataset_id', '')}`",
        f"Snapshot id: `{manifest.get('snapshot_id', '')}`",
        f"Lifecycle id: `{manifest.get('lifecycle_id', '')}`",
        f"Records: {manifest.get('records_total', 0):,}",
        f"Validation: `{validation.get('status', '')}`",
        "",
        "## Baseline Split",
        "",
        f"- Train rows: {split.get('train_rows', 0):,}",
        f"- Test rows: {split.get('test_rows', 0):,}",
        "",
        "## Outputs",
        "",
    ]
    for key, value in sorted(outputs.items()):
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Validation Checks", ""])
    for check in list(validation.get("checks") or []):
        if isinstance(check, dict):
            lines.append(f"- {check.get('name', '')}: {check.get('status', '')}")
    lines.append("")
    return "\n".join(lines)


def _records_from_lifecycle(
    *,
    lifecycle: dict[str, Any],
    snapshot_year: int,
    split_seed: str,
    test_ratio: float,
) -> list[dict[str, Any]]:
    entities = [entity for entity in lifecycle.get("listing_entities") or [] if isinstance(entity, dict)]
    records: list[dict[str, Any]] = []
    for entity in entities:
        observation = entity.get("latest_observation")
        if not isinstance(observation, dict):
            continue
        model_year = _int_or_none(observation.get("model_year"))
        km_driven = _int_or_none(observation.get("km_driven"))
        listed_price = _int_or_none(observation.get("listed_price_inr"))
        brand = _text(observation.get("brand"))
        model = _text(observation.get("model"))
        listing_key = _text(entity.get("listing_key") or observation.get("listing_key"))
        record = {
            "listing_key": listing_key,
            "source": _text(observation.get("source") or entity.get("source")),
            "source_listing_id": _text(observation.get("source_listing_id")),
            "listing_url": _text(observation.get("listing_url")),
            "capture_date": _text(observation.get("capture_date")),
            "captured_at": _text(observation.get("captured_at")),
            "city": _text(observation.get("city")),
            "state": _text(observation.get("state")),
            "brand": brand,
            "model": model,
            "variant": _text(observation.get("variant")),
            "brand_model": _join_nonempty([brand, model]),
            "model_year": model_year,
            "vehicle_age_years": snapshot_year - model_year if model_year is not None else None,
            "fuel_type": _text(observation.get("fuel_type")),
            "transmission": _text(observation.get("transmission")),
            "km_driven": km_driven,
            "km_bucket_10000": _bucket(km_driven, 10_000),
            "ownership": _int_or_none(observation.get("ownership")),
            "registration_code": _text(observation.get("registration_code")),
            "listed_price_inr": listed_price,
            "price_lakh": round(listed_price / 100_000, 4) if listed_price is not None else None,
            "is_available": observation.get("is_available"),
            "observation_count": _int_value(entity.get("observation_count")),
            "first_seen_at": _text(entity.get("first_seen_at")),
            "last_seen_at": _text(entity.get("last_seen_at")),
            "listing_identity_basis": _text(entity.get("listing_identity_basis")),
            "vehicle_fingerprint": _text(entity.get("vehicle_fingerprint")),
            "run_id": _first_text(observation.get("run_id"), list(entity.get("run_ids") or [])),
        }
        record["baseline_split"] = _split_for_key(listing_key, seed=split_seed, test_ratio=test_ratio)
        records.append(record)
    records.sort(key=lambda row: (str(row.get("source") or ""), str(row.get("listing_key") or "")))
    if records and (all(row["baseline_split"] == "train" for row in records) or all(row["baseline_split"] == "test" for row in records)):
        train_rows, test_rows = _fallback_train_test_split(records, test_ratio=test_ratio)
        test_keys = {row["listing_key"] for row in test_rows}
        for row in records:
            row["baseline_split"] = "test" if row["listing_key"] in test_keys else "train"
    return records


def _validate_records(
    *,
    records: list[dict[str, Any]],
    snapshot_manifest: dict[str, Any],
    lifecycle: dict[str, Any],
) -> dict[str, Any]:
    expected_pricing_ready = _int_value(_as_dict(snapshot_manifest.get("totals")).get("pricing_ready"))
    expected_unique = _int_value(_as_dict(lifecycle.get("totals")).get("unique_listing_keys"))
    listing_keys = [_text(row.get("listing_key")) for row in records]
    duplicate_count = len(listing_keys) - len(set(listing_keys))
    missing_required = {
        column: _field_completeness(records, column)["missing"]
        for column in MODELING_REQUIRED_COLUMNS
    }
    invalid_price_count = sum(1 for row in records if _int_value(row.get("listed_price_inr")) <= 0)
    checks = [
        _check("records_do_not_exceed_snapshot_pricing_ready", len(records) <= expected_pricing_ready),
        _check("records_match_lifecycle_unique_keys", len(records) == expected_unique),
        _check("listing_keys_are_unique", duplicate_count == 0),
        _check("required_modeling_fields_complete", not any(missing_required.values())),
        _check("target_price_positive", invalid_price_count == 0),
    ]
    failing = [check for check in checks if check["status"] != "pass"]
    if failing:
        names = ", ".join(check["name"] for check in failing)
        raise ValueError(f"Modeling dataset validation failed: {names}")
    return {
        "status": "pass",
        "checks": checks,
        "expected_pricing_ready_observations": expected_pricing_ready,
        "expected_unique_listing_keys": expected_unique,
        "duplicate_listing_keys": duplicate_count,
        "missing_required": missing_required,
        "invalid_price_count": invalid_price_count,
    }


def _eda_blind_spots(*, records: list[dict[str, Any]], counts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    warnings: list[str] = []
    blocking: list[str] = []
    total = max(1, len(records))
    source_counts = counts.get("source") or []
    if source_counts and float(source_counts[0]["share_pct"]) > 60:
        warnings.append(
            "Source imbalance: {source} contributes {share:.2f}% of rows. Treat source-level metrics as biased until repeated snapshots improve balance.".format(
                source=source_counts[0]["value"],
                share=source_counts[0]["share_pct"],
            )
        )
    city_counts = counts.get("city") or []
    if city_counts and float(city_counts[0]["share_pct"]) > 20:
        warnings.append(
            "City concentration: {city} contributes {share:.2f}% of rows. City effects need careful validation.".format(
                city=city_counts[0]["value"],
                share=city_counts[0]["share_pct"],
            )
        )
    brand_model_groups = counts.get("brand_model") or []
    small_groups = sum(int(item["count"]) for item in brand_model_groups if int(item["count"]) < 5)
    if small_groups:
        warnings.append(
            f"Thin comparable groups: {small_groups:,} rows ({small_groups / total * 100:.2f}%) sit in brand-model groups with fewer than 5 rows."
        )
    for column in ["ownership", "variant", "registration_code"]:
        completeness = _field_completeness(records, column)
        missing = int(completeness["missing"])
        if missing:
            warnings.append(
                "{column} is missing for {missing:,} rows ({missing_pct:.2f}%). Keep it as an audit/modeling feature, not a hard filter.".format(
                    column=column,
                    missing=missing,
                    missing_pct=missing / total * 100,
                )
            )
    future_year_rows = [row for row in records if _int_value(row.get("vehicle_age_years")) < 0]
    if future_year_rows:
        blocking.append(f"{len(future_year_rows):,} rows have future model years relative to snapshot date.")
    extreme_km = [row for row in records if _int_value(row.get("km_driven")) > 300_000]
    if extreme_km:
        warnings.append(f"{len(extreme_km):,} rows have km_driven above 300,000 and should be reviewed before advanced modeling.")
    extreme_price = [row for row in records if _int_value(row.get("listed_price_inr")) > 10_000_000]
    if extreme_price:
        warnings.append(f"{len(extreme_price):,} rows have listed_price_inr above 1 crore and should be reviewed.")
    return {"warnings": warnings, "blocking": blocking}


def _build_baseline_group_tables(train_rows: list[dict[str, Any]]) -> dict[str, dict[tuple[str, ...], dict[str, Any]]]:
    tables: dict[str, dict[tuple[str, ...], dict[str, Any]]] = {}
    for level_name, features in BASELINE_LEVELS:
        grouped: dict[tuple[str, ...], list[int]] = {}
        for row in train_rows:
            key = _group_key(row, features)
            if key is None:
                continue
            grouped.setdefault(key, []).append(_int_value(row.get("listed_price_inr")))
        tables[level_name] = {
            key: {
                "median_price_inr": int(round(median(values))),
                "count": len(values),
            }
            for key, values in grouped.items()
            if values
        }
    if () not in tables.get("global", {}):
        prices = [_int_value(row.get("listed_price_inr")) for row in train_rows if _int_value(row.get("listed_price_inr")) > 0]
        tables.setdefault("global", {})[()] = {
            "median_price_inr": int(round(median(prices))) if prices else 0,
            "count": len(prices),
        }
    return tables


def _predict_baseline(
    row: dict[str, Any],
    *,
    group_tables: dict[str, dict[tuple[str, ...], dict[str, Any]]],
    min_group_size: int,
) -> dict[str, Any]:
    for level_name, features in BASELINE_LEVELS:
        key = _group_key(row, features)
        if key is None:
            continue
        group = group_tables.get(level_name, {}).get(key)
        if group and (level_name == "global" or int(group["count"]) >= min_group_size):
            return {
                "listing_key": row.get("listing_key"),
                "source": row.get("source"),
                "city": row.get("city"),
                "brand": row.get("brand"),
                "model": row.get("model"),
                "model_year": row.get("model_year"),
                "fuel_type": row.get("fuel_type"),
                "transmission": row.get("transmission"),
                "ownership": row.get("ownership"),
                "km_driven": row.get("km_driven"),
                "actual_price_inr": _int_value(row.get("listed_price_inr")),
                "predicted_price_inr": group["median_price_inr"],
                "prediction_level": level_name,
                "training_group_count": group["count"],
            }
    global_group = group_tables["global"][()]
    return {
        "listing_key": row.get("listing_key"),
        "source": row.get("source"),
        "city": row.get("city"),
        "brand": row.get("brand"),
        "model": row.get("model"),
        "model_year": row.get("model_year"),
        "fuel_type": row.get("fuel_type"),
        "transmission": row.get("transmission"),
        "ownership": row.get("ownership"),
        "km_driven": row.get("km_driven"),
        "actual_price_inr": _int_value(row.get("listed_price_inr")),
        "predicted_price_inr": global_group["median_price_inr"],
        "prediction_level": "global",
        "training_group_count": global_group["count"],
    }


def _evaluate_prediction(prediction: dict[str, Any]) -> dict[str, Any]:
    actual = _int_value(prediction.get("actual_price_inr"))
    predicted = _int_value(prediction.get("predicted_price_inr"))
    absolute_error = abs(actual - predicted)
    ape = absolute_error / actual if actual > 0 else None
    return {
        **prediction,
        "absolute_error_inr": absolute_error,
        "absolute_percentage_error": round(ape, 6) if ape is not None else None,
    }


def _prediction_metrics(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    if not predictions:
        return {
            "count": 0,
            "mae": None,
            "rmse": None,
            "median_absolute_error": None,
            "mape": None,
            "median_absolute_percentage_error": None,
            "within_10_pct": None,
            "within_20_pct": None,
        }
    absolute_errors = [float(row["absolute_error_inr"]) for row in predictions]
    ape_values = [
        float(row["absolute_percentage_error"])
        for row in predictions
        if row.get("absolute_percentage_error") is not None
    ]
    return {
        "count": len(predictions),
        "mae": round(sum(absolute_errors) / len(absolute_errors), 2),
        "rmse": round(sqrt(sum(error * error for error in absolute_errors) / len(absolute_errors)), 2),
        "median_absolute_error": round(float(median(absolute_errors)), 2),
        "mape": round(sum(ape_values) / len(ape_values), 6) if ape_values else None,
        "median_absolute_percentage_error": round(float(median(ape_values)), 6) if ape_values else None,
        "within_10_pct": round(sum(1 for value in ape_values if value <= 0.10) / len(ape_values) * 100, 2)
        if ape_values
        else None,
        "within_20_pct": round(sum(1 for value in ape_values if value <= 0.20) / len(ape_values) * 100, 2)
        if ape_values
        else None,
    }


def _metrics_by_group(predictions: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for prediction in predictions:
        group = _text(prediction.get(key)) or "unknown"
        grouped.setdefault(group, []).append(prediction)
    return {
        group: _prediction_metrics(items)
        for group, items in sorted(grouped.items())
    }


def _group_coverage(group_tables: dict[str, dict[tuple[str, ...], dict[str, Any]]]) -> dict[str, Any]:
    return {
        level_name: {
            "groups": len(groups),
            "rows_covered_by_groups": sum(int(group.get("count") or 0) for group in groups.values()),
        }
        for level_name, groups in group_tables.items()
    }


def _group_key(row: dict[str, Any], features: list[str]) -> tuple[str, ...] | None:
    if not features:
        return ()
    values = [_normalized_feature(row.get(feature)) for feature in features]
    if not all(values):
        return None
    return tuple(values)


def _count_values(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in records:
        value = _text(row.get(key)) or "unknown"
        counts[value] = counts.get(value, 0) + 1
    total = max(1, len(records))
    return [
        {
            "value": value,
            "count": count,
            "share_pct": round(count / total * 100, 4),
        }
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _group_numeric_summary(
    records: list[dict[str, Any]],
    *,
    group_key: str,
    value_key: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = {}
    for row in records:
        value = _float_or_none(row.get(value_key))
        if value is None:
            continue
        grouped.setdefault(_text(row.get(group_key)) or "unknown", []).append(value)
    return [
        {"group": group, **_summary_stats(values)}
        for group, values in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    ]


def _top_group_numeric_summary(
    records: list[dict[str, Any]],
    *,
    group_key: str,
    value_key: str,
    limit: int,
) -> list[dict[str, Any]]:
    return _group_numeric_summary(records, group_key=group_key, value_key=value_key)[:limit]


def _field_completeness(records: list[dict[str, Any]], column: str) -> dict[str, Any]:
    present = sum(1 for row in records if _has_value(row.get(column)))
    total = len(records)
    return {
        "present": present,
        "missing": total - present,
        "completeness_pct": round(present / total * 100, 4) if total else 0,
    }


def _summary_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "p05": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
            "mean": None,
        }
    sorted_values = sorted(values)
    return {
        "count": len(sorted_values),
        "min": round(sorted_values[0], 4),
        "p05": round(_percentile(sorted_values, 0.05), 4),
        "p25": round(_percentile(sorted_values, 0.25), 4),
        "median": round(float(median(sorted_values)), 4),
        "p75": round(_percentile(sorted_values, 0.75), 4),
        "p95": round(_percentile(sorted_values, 0.95), 4),
        "max": round(sorted_values[-1], 4),
        "mean": round(sum(sorted_values) / len(sorted_values), 4),
    }


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    index = (len(sorted_values) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return float(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight)


def _numbers(records: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in records:
        value = _float_or_none(row.get(key))
        if value is not None:
            values.append(value)
    return values


def _fallback_train_test_split(
    rows: list[dict[str, Any]],
    *,
    test_ratio: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sorted_rows = sorted(rows, key=lambda row: str(row.get("listing_key") or ""))
    if len(sorted_rows) <= 1:
        return sorted_rows, []
    test_count = max(1, min(len(sorted_rows) - 1, round(len(sorted_rows) * test_ratio)))
    test_keys = {row["listing_key"] for row in sorted_rows[-test_count:]}
    train_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    for row in sorted_rows:
        row["baseline_split"] = "test" if row["listing_key"] in test_keys else "train"
        if row["baseline_split"] == "test":
            test_rows.append(row)
        else:
            train_rows.append(row)
    return train_rows, test_rows


def _resolve_lifecycle_path(
    *,
    lifecycle_index_path: str | Path | None,
    snapshot_manifest: dict[str, Any],
    snapshot_manifest_path: Path,
) -> Path:
    if lifecycle_index_path:
        path = Path(lifecycle_index_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Lifecycle index does not exist: {path}")
    paths = _as_dict(snapshot_manifest.get("paths"))
    path_text = str(paths.get("lifecycle_index") or "")
    if not path_text:
        raise ValueError("snapshot manifest does not contain paths.lifecycle_index")
    path = Path(path_text)
    candidates = [path] if path.is_absolute() else [path, snapshot_manifest_path.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Lifecycle index does not exist: {path_text}")


def _snapshot_year(snapshot_manifest: dict[str, Any]) -> int:
    snapshot_date = str(snapshot_manifest.get("snapshot_date") or "")
    if len(snapshot_date) >= 4 and snapshot_date[:4].isdigit():
        return int(snapshot_date[:4])
    return datetime.now(UTC).year


def _split_for_key(listing_key: str, *, seed: str, test_ratio: float) -> str:
    material = f"{seed}|{listing_key}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    fraction = int(digest, 16) / float(0xFFFFFFFFFFFF)
    return "test" if fraction < test_ratio else "train"


def _metric_row(label: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {label} | {metrics.get('count', 0)} | {_format_number(metrics.get('mae'))} | "
        f"{_format_number(metrics.get('rmse'))} | {_format_number(metrics.get('median_absolute_error'))} | "
        f"{_format_pct(metrics.get('mape'))} | {_format_pct(metrics.get('median_absolute_percentage_error'))} | "
        f"{_format_pct(metrics.get('within_10_pct'))} | {_format_pct(metrics.get('within_20_pct'))} |"
    )


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


def _load_json_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _check(name: str, ok: bool) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _first_text(value: Any, fallback_values: list[Any]) -> str:
    text = _text(value)
    if text:
        return text
    for item in fallback_values:
        text = _text(item)
        if text:
            return text
    return ""


def _join_nonempty(values: list[str]) -> str:
    return " ".join(value for value in values if value).strip()


def _normalized_feature(value: Any) -> str:
    return _text(value).lower()


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


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


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _bucket(value: int | None, size: int) -> int | None:
    if value is None or value < 0:
        return None
    return (value // size) * size


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def _format_number(value: Any) -> str:
    number = _float_or_none(value)
    if number is None:
        return "n/a"
    if abs(number) >= 1_000:
        return f"{number:,.0f}"
    if number == int(number):
        return str(int(number))
    return f"{number:.2f}"


def _format_pct(value: Any) -> str:
    number = _float_or_none(value)
    if number is None:
        return "n/a"
    if 0 <= number <= 1:
        number *= 100
    return f"{number:.2f}%"


def _path_text(path: Path) -> str:
    return path.as_posix()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
