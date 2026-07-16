"""True Value Kaggle external dataset integration.

This module keeps external Kaggle data separated from live scraped snapshots
while still applying the same canonical schema, quality gate, and modeling
artifact style used by the rest of the project.
"""

from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from statistics import median
import re
from typing import Any

from used_car_price_intelligence.adapters.common import stable_hash
from used_car_price_intelligence.parsers import (
    normalize_null,
    parse_fuel_type,
    parse_km_driven,
    parse_ownership,
    parse_price_inr,
    parse_registration,
    parse_transmission,
)
from used_car_price_intelligence.quality import QualityResult, evaluate_listing, load_source_registry
from used_car_price_intelligence.reporting import (
    build_baseline_model_report,
    build_eda_summary,
    build_modeling_data_dictionary,
    render_data_dictionary_markdown,
    render_dataset_manifest_markdown,
    render_eda_summary_markdown,
    write_modeling_dataset_package,
)
from used_car_price_intelligence.reporting.modeling_dataset import MODELING_COLUMNS
from used_car_price_intelligence.schema import CanonicalListing


TRUE_VALUE_KAGGLE_SOURCE = "true_value_external_kaggle"
TRUE_VALUE_KAGGLE_DATASET_ID = "true_value_kaggle_focusedmonk"
TRUE_VALUE_KAGGLE_DATASET_SLUG = "focusedmonk/true-value-cars-dataset"
TRUE_VALUE_KAGGLE_DATASET_URL = "https://www.kaggle.com/datasets/focusedmonk/true-value-cars-dataset"
TRUE_VALUE_KAGGLE_LICENSE = "CC0-1.0"
TRUE_VALUE_KAGGLE_CAPTURE_DATE = "2021-05-30"
TRUE_VALUE_KAGGLE_CAPTURED_AT = "2021-05-30T00:00:00Z"
TRUE_VALUE_KAGGLE_RUN_ID = "run_20260628_true_value_external_kaggle_focusedmonk"
TRUE_VALUE_KAGGLE_PARSER_VERSION = "true_value_external_kaggle_adapter_v0.1"

EXPECTED_COLUMNS = [
    "id",
    "car_name",
    "yr_mfr",
    "fuel_type",
    "kms_run",
    "sale_price",
    "city",
    "times_viewed",
    "body_type",
    "transmission",
    "variant",
    "assured_buy",
    "registered_city",
    "registered_state",
    "is_hot",
    "rto",
    "source",
    "make",
    "model",
    "car_availability",
    "total_owners",
    "broker_quote",
    "original_price",
    "car_rating",
    "ad_created_on",
    "fitness_certificate",
    "emi_starts_from",
    "booking_down_pymnt",
    "reserved",
    "warranty_avail",
]

NUMERIC_PROFILE_COLUMNS = [
    "yr_mfr",
    "kms_run",
    "sale_price",
    "total_owners",
    "broker_quote",
    "original_price",
    "emi_starts_from",
    "booking_down_pymnt",
]

TOP_VALUE_COLUMNS = [
    "fuel_type",
    "transmission",
    "city",
    "registered_state",
    "make",
    "model",
    "body_type",
    "car_availability",
    "source",
    "assured_buy",
    "reserved",
    "warranty_avail",
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

CITY_STATE_MAP = {
    "ahmedabad": "Gujarat",
    "bengaluru": "Karnataka",
    "chennai": "Tamil Nadu",
    "faridabad": "Haryana",
    "ghaziabad": "Uttar Pradesh",
    "gurgaon": "Haryana",
    "hyderabad": "Telangana",
    "kolkata": "West Bengal",
    "lucknow": "Uttar Pradesh",
    "mumbai": "Maharashtra",
    "new delhi": "Delhi",
    "noida": "Uttar Pradesh",
    "pune": "Maharashtra",
}

BRAND_MAP = {
    "audi": "Audi",
    "bmw": "BMW",
    "chevrolet": "Chevrolet",
    "datsun": "Datsun",
    "fiat": "Fiat",
    "ford": "Ford",
    "honda": "Honda",
    "hyundai": "Hyundai",
    "jeep": "Jeep",
    "mahindra": "Mahindra",
    "maruti": "Maruti Suzuki",
    "mercedes benz": "Mercedes-Benz",
    "mg": "MG",
    "nissan": "Nissan",
    "renault": "Renault",
    "skoda": "Skoda",
    "tata": "Tata",
    "toyota": "Toyota",
    "volkswagen": "Volkswagen",
}

UNTRUSTED_SOURCE_CHANNELS = {"customer_to_customer"}
AVAILABLE_STATES = {"in_stock", "in_transit"}
UNAVAILABLE_STATES = {"out_of_stock", "pickup_pending"}


def build_true_value_kaggle_package(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    profile_output_dir: str | Path | None = None,
    generated_at: str | None = None,
    min_group_size: int = 3,
    test_ratio: float = 0.2,
    split_seed: str = "true_value_external_kaggle_baseline_v0",
    source_registry_path: str | Path = "config/source_registry.yml",
) -> dict[str, Any]:
    """Build a separated True Value external dataset package."""

    resolved_generated_at = generated_at or _utc_now()
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    profile_path = Path(profile_output_dir) if profile_output_dir else output_path
    rows = load_true_value_kaggle_rows(input_path)
    raw_profile = profile_true_value_kaggle_rows(rows=rows, input_dir=input_path)
    registry = load_source_registry(source_registry_path)

    canonical_rows: list[CanonicalListing] = []
    quality_results: list[QualityResult] = []
    pricing_ready: list[CanonicalListing] = []
    quarantine_rows: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()

    for index, row in enumerate(rows, start=1):
        listing = true_value_kaggle_row_to_canonical(row, row_index=index)
        canonical_rows.append(listing)
        quality = evaluate_listing(listing, registry)
        policy_reasons = _policy_quarantine_reasons(row)
        fingerprint = _vehicle_fingerprint(listing)
        if fingerprint in seen_fingerprints:
            policy_reasons.append("duplicate_vehicle_fingerprint")
        else:
            seen_fingerprints.add(fingerprint)

        combined_reasons = list(dict.fromkeys([*quality.quarantine_reasons, *policy_reasons]))
        quality_results.append(quality)
        if quality.pricing_ready and not policy_reasons:
            pricing_ready.append(listing)
        else:
            quarantine_rows.append(
                {
                    "source_listing_id": listing.source_listing_id,
                    "listing_url": listing.listing_url,
                    "input_file": row.get("_input_file"),
                    "input_split": row.get("_split"),
                    "row_number": row.get("_row_number"),
                    "quality_pricing_ready": quality.pricing_ready,
                    "quarantine_reasons": combined_reasons,
                    "warnings": quality.warnings,
                    "record": listing.to_dict(),
                }
            )

    modeling_records = [
        canonical_to_modeling_record(
            listing,
            split_seed=split_seed,
            test_ratio=test_ratio,
            snapshot_year=2021,
        )
        for listing in pricing_ready
    ]
    modeling_records.sort(key=lambda item: str(item.get("listing_key") or ""))
    validation = _validate_modeling_records(modeling_records)
    dataset_manifest = _build_dataset_manifest(
        generated_at=resolved_generated_at,
        input_dir=input_path,
        output_dir=output_path,
        raw_profile=raw_profile,
        canonical_rows=canonical_rows,
        pricing_ready=pricing_ready,
        quarantine_rows=quarantine_rows,
        validation=validation,
        test_ratio=test_ratio,
        split_seed=split_seed,
        min_group_size=min_group_size,
    )
    data_dictionary = build_modeling_data_dictionary(generated_at=resolved_generated_at)
    eda_summary = build_eda_summary(
        records=modeling_records,
        snapshot_manifest=_external_snapshot_manifest(len(modeling_records)),
        lifecycle=_external_lifecycle(len(modeling_records)),
        generated_at=resolved_generated_at,
    )
    baseline_model = build_baseline_model_report(
        records=modeling_records,
        generated_at=resolved_generated_at,
        test_ratio=test_ratio,
        min_group_size=min_group_size,
        split_seed=split_seed,
    )
    dataset_manifest["baseline_split"] = baseline_model["split"]
    package = {
        "manifest": dataset_manifest,
        "records": modeling_records,
        "data_dictionary": data_dictionary,
        "eda_summary": eda_summary,
        "baseline_model": baseline_model,
    }

    output_path.mkdir(parents=True, exist_ok=True)
    profile_path.mkdir(parents=True, exist_ok=True)
    _write_json(profile_path / "true_value_external_kaggle_raw_profile.json", raw_profile)
    (profile_path / "true_value_external_kaggle_raw_profile.md").write_text(
        render_raw_profile_markdown(raw_profile),
        encoding="utf-8",
    )
    _write_jsonl(output_path / "true_value_external_kaggle_canonical_all.jsonl", [row.to_dict() for row in canonical_rows])
    _write_jsonl(
        output_path / "true_value_external_kaggle_pricing_ready.jsonl",
        [row.to_dict() for row in pricing_ready],
    )
    _write_jsonl(output_path / "true_value_external_kaggle_quarantine.jsonl", quarantine_rows)
    quality_summary = _quality_summary(
        rows=rows,
        canonical_rows=canonical_rows,
        quality_results=quality_results,
        pricing_ready=pricing_ready,
        quarantine_rows=quarantine_rows,
    )
    _write_json(output_path / "quality_summary.json", quality_summary)
    (output_path / "quality_summary.md").write_text(
        render_quality_summary_markdown(quality_summary),
        encoding="utf-8",
    )

    output_paths = write_modeling_dataset_package(output_dir=output_path, package=package)
    final_manifest = json.loads(Path(output_paths["dataset_manifest_json"]).read_text(encoding="utf-8"))
    final_manifest["outputs"].update(
        {
            "canonical_all_jsonl": _path_text(output_path / "true_value_external_kaggle_canonical_all.jsonl"),
            "pricing_ready_jsonl": _path_text(output_path / "true_value_external_kaggle_pricing_ready.jsonl"),
            "quarantine_jsonl": _path_text(output_path / "true_value_external_kaggle_quarantine.jsonl"),
            "quality_summary_json": _path_text(output_path / "quality_summary.json"),
            "quality_summary_markdown": _path_text(output_path / "quality_summary.md"),
            "raw_profile_json": _path_text(profile_path / "true_value_external_kaggle_raw_profile.json"),
            "raw_profile_markdown": _path_text(profile_path / "true_value_external_kaggle_raw_profile.md"),
        }
    )
    _write_json(Path(output_paths["dataset_manifest_json"]), final_manifest)
    Path(output_paths["dataset_manifest_markdown"]).write_text(
        render_dataset_manifest_markdown(final_manifest),
        encoding="utf-8",
    )
    (output_path / "data_dictionary.md").write_text(
        render_data_dictionary_markdown(data_dictionary),
        encoding="utf-8",
    )
    (output_path / "eda_summary.md").write_text(
        render_eda_summary_markdown(eda_summary),
        encoding="utf-8",
    )

    return {
        "dataset_manifest": final_manifest,
        "raw_profile": raw_profile,
        "quality_summary": quality_summary,
        "output_paths": final_manifest["outputs"],
    }


def load_true_value_kaggle_rows(input_dir: str | Path) -> list[dict[str, Any]]:
    input_path = Path(input_dir)
    rows: list[dict[str, Any]] = []
    for split_name in ("train", "test"):
        csv_path = input_path / f"{split_name}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing True Value Kaggle input file: {csv_path}")
        with csv_path.open(newline="", encoding="utf-8") as file_obj:
            reader = csv.DictReader(file_obj)
            if reader.fieldnames != EXPECTED_COLUMNS:
                raise ValueError(
                    f"Unexpected columns in {csv_path}: expected {EXPECTED_COLUMNS}, got {reader.fieldnames}"
                )
            for row_number, row in enumerate(reader, start=2):
                normalized_row = dict(row)
                normalized_row["_split"] = split_name
                normalized_row["_input_file"] = csv_path.name
                normalized_row["_row_number"] = row_number
                rows.append(normalized_row)
    return rows


def profile_true_value_kaggle_rows(*, rows: list[dict[str, Any]], input_dir: Path) -> dict[str, Any]:
    split_counts = Counter(str(row.get("_split") or "unknown") for row in rows)
    id_keys = [str(row.get("id") or "").strip() for row in rows]
    exact_payloads = [_raw_payload_without_internal_fields(row) for row in rows]
    exact_hashes = [stable_hash(payload) for payload in exact_payloads]
    core_fingerprints = [_raw_content_fingerprint(row) for row in rows]
    missing = {
        column: sum(1 for row in rows if normalize_null(row.get(column)) is None)
        for column in EXPECTED_COLUMNS
    }
    top_values = {
        column: _top_values(rows, column)
        for column in TOP_VALUE_COLUMNS
    }
    numeric = {
        column: _numeric_summary([_float_or_none(row.get(column)) for row in rows])
        for column in NUMERIC_PROFILE_COLUMNS
    }
    return {
        "profile_version": "true_value_external_kaggle_profile_v0.1",
        "dataset_id": TRUE_VALUE_KAGGLE_DATASET_ID,
        "source": TRUE_VALUE_KAGGLE_SOURCE,
        "dataset_slug": TRUE_VALUE_KAGGLE_DATASET_SLUG,
        "dataset_url": TRUE_VALUE_KAGGLE_DATASET_URL,
        "license": TRUE_VALUE_KAGGLE_LICENSE,
        "input_dir": _path_text(input_dir),
        "raw_rows": len(rows),
        "files": dict(sorted(split_counts.items())),
        "columns": EXPECTED_COLUMNS,
        "missing_by_column": missing,
        "top_values": top_values,
        "numeric_summary": numeric,
        "duplicate_checks": {
            "duplicate_id_count": len(id_keys) - len(set(id_keys)),
            "duplicate_exact_raw_rows": len(exact_hashes) - len(set(exact_hashes)),
            "duplicate_core_vehicle_price_rows": len(core_fingerprints) - len(set(core_fingerprints)),
            "unique_core_vehicle_price_rows": len(set(core_fingerprints)),
        },
        "notes": [
            "The train/test files are treated as raw Kaggle splits, not as final model splits.",
            "The id column repeats across train.csv and test.csv, so split is part of source_listing_id.",
            "No live scraped True Value rows are mixed into this package.",
        ],
    }


def true_value_kaggle_row_to_canonical(row: dict[str, Any], *, row_index: int) -> CanonicalListing:
    raw_payload = _raw_payload_without_internal_fields(row)
    raw_hash = stable_hash(raw_payload)
    price_result = parse_price_inr(row.get("sale_price"))
    km_result = parse_km_driven(row.get("kms_run"))
    fuel_result = parse_fuel_type(row.get("fuel_type"))
    transmission_result = parse_transmission(row.get("transmission"))
    ownership_result = parse_ownership(row.get("total_owners"))
    registration_result = parse_registration(row.get("rto"))
    registration_value = registration_result.normalized_value or {}

    brand = _normalize_brand(row.get("make"))
    model = _normalize_model(row.get("model"))
    variant = _normalize_variant(row.get("variant"))
    model_year = _int_or_none(row.get("yr_mfr"))
    city = _title_case(row.get("city"))
    raw_availability = _clean_text(row.get("car_availability"))

    parse_warnings = [
        warning
        for result in [price_result, km_result, fuel_result, transmission_result, registration_result]
        for warning in result.warnings
    ]
    if brand is None:
        parse_warnings.append("missing_brand")
    if model is None:
        parse_warnings.append("missing_model")
    if model_year is None:
        parse_warnings.append("missing_model_year")

    confidence_candidates = [
        price_result.confidence,
        km_result.confidence,
        fuel_result.confidence,
        transmission_result.confidence,
        registration_result.confidence,
        0.98 if brand else 0.0,
        0.98 if model else 0.0,
        0.98 if model_year else 0.0,
    ]

    source_listing_id = "true_value_external_kaggle_{split}_{id}".format(
        split=_clean_text(row.get("_split")) or "unknown",
        id=_clean_text(row.get("id")) or f"row_{row_index:05d}",
    )
    listing_url = "kaggle://{slug}/{split}/{id}".format(
        slug=TRUE_VALUE_KAGGLE_DATASET_SLUG,
        split=_clean_text(row.get("_split")) or "unknown",
        id=_clean_text(row.get("id")) or f"row_{row_index:05d}",
    )

    return CanonicalListing(
        source=TRUE_VALUE_KAGGLE_SOURCE,
        source_listing_id=source_listing_id,
        listing_url=listing_url,
        captured_at=TRUE_VALUE_KAGGLE_CAPTURED_AT,
        city=city,
        state=CITY_STATE_MAP.get(str(row.get("city") or "").strip().lower()),
        locality=None,
        hub_name=city,
        brand=brand,
        model=model,
        variant=variant,
        model_year=model_year,
        manufacture_year=model_year,
        registration_year=registration_value.get("registration_year"),
        fuel_type=fuel_result.normalized_value,
        transmission=transmission_result.normalized_value,
        km_driven=km_result.normalized_value,
        ownership=ownership_result.normalized_value if ownership_result.ok else None,
        registration_state=registration_value.get("registration_state") or _title_case(row.get("registered_state")),
        registration_code=registration_value.get("registration_code"),
        registration_type=registration_value.get("registration_type"),
        body_type=_title_case(row.get("body_type")),
        listed_price_inr=price_result.normalized_value,
        original_price_inr=_positive_int_or_none(row.get("original_price")),
        emi_amount_inr=_positive_int_or_none(row.get("emi_starts_from")),
        token_amount_inr=_positive_int_or_none(row.get("booking_down_pymnt")),
        currency="INR",
        seller_type="oem_dealer",
        is_certified=_parse_bool(row.get("assured_buy")),
        inspection_status="true_value_external_assured"
        if _parse_bool(row.get("assured_buy"))
        else "true_value_external_inventory",
        condition_grade=_clean_text(row.get("car_rating")),
        warranty_label="warranty_available" if _parse_bool(row.get("warranty_avail")) else None,
        finance_label="finance_available" if _positive_int_or_none(row.get("emi_starts_from")) else None,
        is_available=_availability(raw_availability),
        listing_posted_at=_iso_datetime_or_none(row.get("ad_created_on")),
        source_record_type="listing",
        first_seen_at=_iso_datetime_or_none(row.get("ad_created_on")),
        last_seen_at=TRUE_VALUE_KAGGLE_CAPTURED_AT,
        source_title_text=_clean_text(row.get("car_name")),
        source_variant_text=variant,
        raw_record_hash=raw_hash,
        ingestion_run_id=TRUE_VALUE_KAGGLE_RUN_ID,
        parser_version=TRUE_VALUE_KAGGLE_PARSER_VERSION,
        schema_version="canonical_listing_v0.1",
        parse_confidence=round(min(confidence_candidates), 4),
        parse_warnings=parse_warnings,
        extra_fields={
            "external_dataset": {
                "dataset_id": TRUE_VALUE_KAGGLE_DATASET_ID,
                "dataset_slug": TRUE_VALUE_KAGGLE_DATASET_SLUG,
                "dataset_url": TRUE_VALUE_KAGGLE_DATASET_URL,
                "license": TRUE_VALUE_KAGGLE_LICENSE,
                "input_file": row.get("_input_file"),
                "input_split": row.get("_split"),
                "row_number": row.get("_row_number"),
                "raw_id": row.get("id"),
            },
            "true_value_kaggle": {
                "raw_source_channel": _clean_text(row.get("source")),
                "times_viewed": _int_or_none(row.get("times_viewed")),
                "registered_city": _title_case(row.get("registered_city")),
                "registered_state_raw": _title_case(row.get("registered_state")),
                "is_hot": _parse_bool(row.get("is_hot")),
                "broker_quote": _positive_int_or_none(row.get("broker_quote")),
                "fitness_certificate": _parse_bool(row.get("fitness_certificate")),
                "reserved": _parse_bool(row.get("reserved")),
                "raw_car_availability": raw_availability,
            },
        },
    )


def canonical_to_modeling_record(
    listing: CanonicalListing,
    *,
    split_seed: str,
    test_ratio: float,
    snapshot_year: int,
) -> dict[str, Any]:
    listing_key = str(listing.source_listing_id or listing.listing_url or listing.raw_record_hash or "")
    model_year = _int_or_none(listing.model_year)
    km_driven = _int_or_none(listing.km_driven)
    price = _int_or_none(listing.listed_price_inr)
    brand = str(listing.brand or "").strip()
    model = str(listing.model or "").strip()
    return {
        "listing_key": listing_key,
        "source": listing.source,
        "source_listing_id": listing.source_listing_id,
        "listing_url": listing.listing_url,
        "capture_date": TRUE_VALUE_KAGGLE_CAPTURE_DATE,
        "captured_at": listing.captured_at,
        "city": listing.city,
        "state": listing.state,
        "brand": brand,
        "model": model,
        "variant": listing.variant,
        "brand_model": " ".join(item for item in [brand, model] if item).strip(),
        "model_year": model_year,
        "vehicle_age_years": snapshot_year - model_year if model_year is not None else None,
        "fuel_type": listing.fuel_type,
        "transmission": listing.transmission,
        "km_driven": km_driven,
        "km_bucket_10000": _bucket(km_driven, 10_000),
        "ownership": _int_or_none(listing.ownership),
        "registration_code": listing.registration_code,
        "listed_price_inr": price,
        "price_lakh": round(price / 100_000, 4) if price is not None else None,
        "is_available": listing.is_available,
        "observation_count": 1,
        "first_seen_at": listing.first_seen_at,
        "last_seen_at": listing.last_seen_at,
        "listing_identity_basis": "external_dataset_split_plus_id",
        "vehicle_fingerprint": _vehicle_fingerprint(listing),
        "run_id": listing.ingestion_run_id,
        "baseline_split": _split_for_key(listing_key, seed=split_seed, test_ratio=test_ratio),
    }


def render_raw_profile_markdown(profile: dict[str, Any]) -> str:
    duplicates = profile.get("duplicate_checks") or {}
    missing = profile.get("missing_by_column") or {}
    numeric = profile.get("numeric_summary") or {}
    top_values = profile.get("top_values") or {}
    lines = [
        "# True Value External Kaggle Raw Profile",
        "",
        f"Dataset id: `{profile.get('dataset_id', '')}`",
        f"Source namespace: `{profile.get('source', '')}`",
        f"Rows: {profile.get('raw_rows', 0):,}",
        f"License: `{profile.get('license', '')}`",
        f"Dataset URL: {profile.get('dataset_url', '')}",
        "",
        "## Input Files",
        "",
        "| File split | Rows |",
        "| --- | ---: |",
    ]
    for split, count in sorted((profile.get("files") or {}).items()):
        lines.append(f"| {split} | {count:,} |")
    lines.extend(
        [
            "",
            "## Duplicate Checks",
            "",
            "| Check | Count |",
            "| --- | ---: |",
            f"| Duplicate ids across raw files | {duplicates.get('duplicate_id_count', 0):,} |",
            f"| Exact duplicate raw rows | {duplicates.get('duplicate_exact_raw_rows', 0):,} |",
            f"| Duplicate core vehicle-price rows | {duplicates.get('duplicate_core_vehicle_price_rows', 0):,} |",
            f"| Unique core vehicle-price rows | {duplicates.get('unique_core_vehicle_price_rows', 0):,} |",
            "",
            "## Missing Values",
            "",
            "| Column | Missing |",
            "| --- | ---: |",
        ]
    )
    for column, count in sorted(missing.items(), key=lambda item: (-int(item[1]), item[0])):
        if int(count):
            lines.append(f"| {column} | {int(count):,} |")
    lines.extend(["", "## Numeric Profile", "", "| Column | Count | Min | Median | Max |", "| --- | ---: | ---: | ---: | ---: |"])
    for column, summary in numeric.items():
        lines.append(
            "| {column} | {count} | {min} | {median} | {max} |".format(
                column=column,
                count=summary.get("count", 0),
                min=_format_number(summary.get("min")),
                median=_format_number(summary.get("median")),
                max=_format_number(summary.get("max")),
            )
        )
    lines.extend(["", "## Top Values", ""])
    for column, values in top_values.items():
        lines.append(f"### {column}")
        lines.append("")
        lines.append("| Value | Rows |")
        lines.append("| --- | ---: |")
        for item in values[:10]:
            lines.append(f"| {item.get('value', '')} | {item.get('count', 0):,} |")
        lines.append("")
    for note in profile.get("notes") or []:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def render_quality_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# True Value External Kaggle Quality Summary",
        "",
        f"Raw rows: {summary.get('raw_rows', 0):,}",
        f"Canonical rows: {summary.get('canonical_rows', 0):,}",
        f"Pricing-ready trusted rows: {summary.get('pricing_ready_rows', 0):,}",
        f"Quarantined rows: {summary.get('quarantine_rows', 0):,}",
        "",
        "## Quarantine Reasons",
        "",
        "| Reason | Rows |",
        "| --- | ---: |",
    ]
    for item in summary.get("quarantine_reasons") or []:
        lines.append(f"| {item.get('reason', '')} | {item.get('count', 0):,} |")
    lines.extend(["", "## Pricing-Ready Field Completeness", "", "| Field | Present | Missing | Completeness |", "| --- | ---: | ---: | ---: |"])
    for field, item in (summary.get("pricing_ready_field_completeness") or {}).items():
        lines.append(
            f"| {field} | {item.get('present', 0):,} | {item.get('missing', 0):,} | {item.get('completeness_pct', 0):.2f}% |"
        )
    lines.extend(["", "## Policy", ""])
    for item in summary.get("policy") or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _build_dataset_manifest(
    *,
    generated_at: str,
    input_dir: Path,
    output_dir: Path,
    raw_profile: dict[str, Any],
    canonical_rows: list[CanonicalListing],
    pricing_ready: list[CanonicalListing],
    quarantine_rows: list[dict[str, Any]],
    validation: dict[str, Any],
    test_ratio: float,
    split_seed: str,
    min_group_size: int,
) -> dict[str, Any]:
    return {
        "manifest_version": "external_true_value_modeling_dataset_v0.1",
        "dataset_id": TRUE_VALUE_KAGGLE_DATASET_ID,
        "generated_at": generated_at,
        "snapshot_id": f"{TRUE_VALUE_KAGGLE_DATASET_ID}_external_snapshot",
        "snapshot_date": TRUE_VALUE_KAGGLE_CAPTURE_DATE,
        "lifecycle_id": f"{TRUE_VALUE_KAGGLE_DATASET_ID}_external_one_row_per_listing",
        "collection_id": f"{TRUE_VALUE_KAGGLE_DATASET_ID}_external_collection",
        "source": TRUE_VALUE_KAGGLE_SOURCE,
        "records_total": len(pricing_ready),
        "columns": MODELING_COLUMNS,
        "target": "listed_price_inr",
        "inputs": {
            "input_dir": _path_text(input_dir),
            "train_csv": _path_text(input_dir / "train.csv"),
            "test_csv": _path_text(input_dir / "test.csv"),
            "dataset_slug": TRUE_VALUE_KAGGLE_DATASET_SLUG,
            "dataset_url": TRUE_VALUE_KAGGLE_DATASET_URL,
            "license": TRUE_VALUE_KAGGLE_LICENSE,
        },
        "raw_rows": raw_profile.get("raw_rows", 0),
        "canonical_rows": len(canonical_rows),
        "pricing_ready_rows": len(pricing_ready),
        "quarantine_rows": len(quarantine_rows),
        "baseline_split": {
            "seed": split_seed,
            "test_ratio": test_ratio,
            "train_rows": 0,
            "test_rows": 0,
        },
        "validation": validation,
        "policy": {
            "source_scope": "Only the Kaggle True Value dataset is processed in this external package.",
            "separation": "No live scraped rows are mixed into this dataset package.",
            "trusted_row_gate": (
                "Modeling rows must pass canonical quality checks, must not be customer_to_customer, "
                "must have assured_buy=True, and must not be unavailable."
            ),
            "split_policy": "Original Kaggle train/test is retained in metadata; our baseline split is regenerated deterministically.",
            "output_dir": _path_text(output_dir),
        },
    }


def _validate_modeling_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [str(row.get("listing_key") or "") for row in records]
    duplicate_keys = len(keys) - len(set(keys))
    missing_required = {
        column: _field_completeness(records, column)["missing"]
        for column in MODELING_REQUIRED_COLUMNS
    }
    invalid_price = sum(1 for row in records if _int_or_none(row.get("listed_price_inr")) in (None, 0))
    source_names = sorted({str(row.get("source") or "") for row in records})
    checks = [
        _check("records_are_true_value_external_only", source_names == [TRUE_VALUE_KAGGLE_SOURCE] if records else True),
        _check("listing_keys_are_unique", duplicate_keys == 0),
        _check("required_modeling_fields_complete", not any(missing_required.values())),
        _check("target_price_positive", invalid_price == 0),
    ]
    return {
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "checks": checks,
        "duplicate_listing_keys": duplicate_keys,
        "missing_required": missing_required,
        "invalid_price_count": invalid_price,
    }


def _quality_summary(
    *,
    rows: list[dict[str, Any]],
    canonical_rows: list[CanonicalListing],
    quality_results: list[QualityResult],
    pricing_ready: list[CanonicalListing],
    quarantine_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    reason_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    for row in quarantine_rows:
        for reason in row.get("quarantine_reasons") or []:
            reason_counts[str(reason)] += 1
        for warning in row.get("warnings") or []:
            warning_counts[str(warning)] += 1
    return {
        "summary_version": "true_value_external_kaggle_quality_v0.1",
        "source": TRUE_VALUE_KAGGLE_SOURCE,
        "dataset_id": TRUE_VALUE_KAGGLE_DATASET_ID,
        "raw_rows": len(rows),
        "canonical_rows": len(canonical_rows),
        "pricing_ready_rows": len(pricing_ready),
        "quarantine_rows": len(quarantine_rows),
        "canonical_quality_pricing_ready_before_external_policy": sum(1 for result in quality_results if result.pricing_ready),
        "quarantine_reasons": [
            {"reason": reason, "count": count}
            for reason, count in reason_counts.most_common()
        ],
        "warnings": [
            {"warning": warning, "count": count}
            for warning, count in warning_counts.most_common()
        ],
        "pricing_ready_field_completeness": {
            column: _field_completeness([row.to_dict() for row in pricing_ready], column)
            for column in [
                "source",
                "source_listing_id",
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
                "is_certified",
                "is_available",
            ]
        },
        "policy": [
            "Rows are from True Value Kaggle only.",
            "Rows with raw source channel customer_to_customer are quarantined from modeling.",
            "Rows with assured_buy=False are quarantined from trusted-only modeling.",
            "Rows marked unavailable or pending are quarantined by the canonical quality gate.",
            "The external package is separate from live scraped gold snapshots.",
        ],
    }


def _policy_quarantine_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    source_channel = str(row.get("source") or "").strip().lower()
    if source_channel in UNTRUSTED_SOURCE_CHANNELS:
        reasons.append("external_untrusted_customer_to_customer_channel")
    if _parse_bool(row.get("assured_buy")) is not True:
        reasons.append("external_assured_buy_false")
    return reasons


def _external_snapshot_manifest(pricing_ready_rows: int) -> dict[str, Any]:
    return {
        "snapshot_id": f"{TRUE_VALUE_KAGGLE_DATASET_ID}_external_snapshot",
        "snapshot_date": TRUE_VALUE_KAGGLE_CAPTURE_DATE,
        "totals": {"pricing_ready": pricing_ready_rows},
    }


def _external_lifecycle(unique_rows: int) -> dict[str, Any]:
    return {"totals": {"unique_listing_keys": unique_rows}}


def _raw_payload_without_internal_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _raw_content_fingerprint(row: dict[str, Any]) -> str:
    fields = [
        "car_name",
        "yr_mfr",
        "fuel_type",
        "kms_run",
        "sale_price",
        "city",
        "body_type",
        "transmission",
        "variant",
        "registered_city",
        "registered_state",
        "rto",
        "make",
        "model",
        "total_owners",
        "original_price",
        "car_rating",
        "ad_created_on",
    ]
    material = "|".join(str(row.get(field) or "").strip().lower() for field in fields)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _vehicle_fingerprint(listing: CanonicalListing) -> str:
    fields = [
        listing.source,
        listing.city,
        listing.brand,
        listing.model,
        listing.variant,
        listing.model_year,
        listing.fuel_type,
        listing.transmission,
        listing.km_driven,
        listing.ownership,
        listing.registration_code,
        listing.listed_price_inr,
        listing.listing_posted_at,
    ]
    material = "|".join(str(field or "").strip().lower() for field in fields)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _top_values(rows: list[dict[str, Any]], column: str, *, limit: int = 20) -> list[dict[str, Any]]:
    counts = Counter(_clean_text(row.get(column)) or "<missing>" for row in rows)
    return [{"value": value, "count": count} for value, count in counts.most_common(limit)]


def _numeric_summary(values: list[float | None]) -> dict[str, Any]:
    clean = sorted(value for value in values if value is not None)
    if not clean:
        return {"count": 0, "missing": len(values), "min": None, "median": None, "max": None, "mean": None}
    return {
        "count": len(clean),
        "missing": len(values) - len(clean),
        "min": clean[0],
        "median": median(clean),
        "max": clean[-1],
        "mean": round(sum(clean) / len(clean), 4),
    }


def _normalize_brand(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    return BRAND_MAP.get(text.lower(), " ".join(part.capitalize() for part in text.split()))


def _normalize_model(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = re.sub(r"[-_]+", " ", text.lower())
    normalized = re.sub(r"\b\d\.\d\b", " ", normalized)
    normalized = re.sub(r"\b\d\s+\d\b$", " ", normalized)
    normalized = re.sub(r"\b(manual|automatic|amt|cvt|dct|imt|petrol|diesel|cng|lpg)\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return None
    return _title_model(normalized)


def _normalize_variant(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = re.sub(r"\s+", " ", text).strip()
    return normalized.upper() if len(normalized) <= 4 else " ".join(part.upper() if part.isupper() else part.capitalize() for part in normalized.split())


def _title_model(value: str) -> str:
    special = {
        "i10": "i10",
        "i20": "i20",
        "x1": "X1",
        "x3": "X3",
        "q3": "Q3",
        "q5": "Q5",
    }
    return " ".join(special.get(part, part.capitalize()) for part in value.split())


def _title_case(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    return " ".join(part.capitalize() for part in text.split())


def _clean_text(value: Any) -> str | None:
    text = normalize_null(value)
    if text is None:
        return None
    return re.sub(r"\s+", " ", str(text).strip())


def _parse_bool(value: Any) -> bool | None:
    text = _clean_text(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    return None


def _availability(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in AVAILABLE_STATES:
        return True
    if lowered in UNAVAILABLE_STATES:
        return False
    return None


def _iso_datetime_or_none(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.isoformat()
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _split_for_key(listing_key: str, *, seed: str, test_ratio: float) -> str:
    material = f"{seed}|{listing_key}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    fraction = int(digest, 16) / float(0xFFFFFFFFFFFF)
    return "test" if fraction < test_ratio else "train"


def _bucket(value: int | None, size: int) -> int | None:
    if value is None:
        return None
    return int((value // size) * size)


def _positive_int_or_none(value: Any) -> int | None:
    parsed = _int_or_none(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


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


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).replace(",", "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _field_completeness(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    total = len(rows)
    present = sum(1 for row in rows if _has_value(row.get(column)))
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


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, sort_keys=True) + "\n")


def _format_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _path_text(path: Path) -> str:
    return path.as_posix()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
