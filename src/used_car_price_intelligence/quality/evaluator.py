"""Quality gates for silver validation, gold readiness, and quarantine reasons."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from used_car_price_intelligence.parsers import is_price_like_text
from used_car_price_intelligence.schema import CanonicalListing


ALLOWED_FUEL_TYPES = {
    "petrol",
    "diesel",
    "cng",
    "petrol_cng",
    "petrol_lpg",
    "electric",
    "hybrid",
    "lpg",
}
ALLOWED_TRANSMISSIONS = {"manual", "automatic", "amt", "imt", "cvt", "ivt", "dct"}
ALLOWED_CURRENCIES = {"INR"}

REQUIRED_GROUPS = [
    ("source", ("source",), "missing_source"),
    ("listing_identity", ("source_listing_id", "listing_url"), "missing_listing_identity"),
    ("captured_at", ("captured_at",), "missing_captured_at"),
    ("city", ("city",), "missing_city"),
    ("brand", ("brand",), "missing_brand"),
    ("model", ("model",), "missing_model"),
    ("model_year", ("model_year",), "missing_model_year"),
    ("listed_price_inr", ("listed_price_inr",), "missing_price"),
    ("km_driven", ("km_driven",), "missing_km"),
    ("fuel_type", ("fuel_type",), "missing_fuel_type"),
    ("transmission", ("transmission",), "missing_transmission"),
    ("currency", ("currency",), "missing_currency"),
    ("raw_record_hash", ("raw_record_hash",), "missing_raw_record_hash"),
    ("ingestion_run_id", ("ingestion_run_id",), "missing_ingestion_run_id"),
    ("parser_version", ("parser_version",), "missing_parser_version"),
    ("schema_version", ("schema_version",), "missing_schema_version"),
]

HIGH_VALUE_FIELDS = [
    "variant",
    "ownership",
    "registration_code",
    "locality",
    "seller_type",
    "is_certified",
    "is_available",
]

OPTIONAL_FIELDS = [
    "state",
    "hub_name",
    "manufacture_year",
    "registration_year",
    "registration_state",
    "registration_type",
    "body_type",
    "color",
    "seating_capacity",
    "original_price_inr",
    "discount_amount_inr",
    "emi_amount_inr",
    "token_amount_inr",
    "price_label",
    "deal_rating",
    "extra_charges_flag",
    "dealer_name",
    "inspection_status",
    "inspection_score",
    "condition_grade",
    "accident_history",
    "service_history_available",
    "commercial_vehicle_flag",
    "warranty_label",
    "return_policy_label",
    "finance_label",
    "listing_posted_at",
    "source_record_type",
    "first_seen_at",
    "last_seen_at",
]

SILVER_BLOCKING_REASONS = {
    "missing_source",
    "missing_listing_identity",
    "missing_captured_at",
    "missing_city",
    "missing_brand",
    "missing_model",
    "missing_model_year",
    "missing_price",
    "missing_km",
    "missing_currency",
    "missing_raw_record_hash",
    "missing_ingestion_run_id",
    "missing_parser_version",
    "missing_schema_version",
    "invalid_captured_at",
    "invalid_model_year",
    "invalid_price",
    "invalid_km",
    "invalid_currency",
    "non_listing_record",
}

CRITICAL_PARSE_WARNINGS = {
    "missing_price",
    "missing_km",
    "missing_model_year",
    "missing_brand",
    "missing_model",
    "missing_fuel_type",
    "missing_transmission",
    "unknown_fuel_type",
    "unknown_transmission",
    "invalid_price",
    "invalid_km",
    "invalid_model_year",
    "parse_confidence_below_gold_threshold",
}


@dataclass(frozen=True)
class CompletenessScores:
    required: float
    high_value: float
    optional: float
    overall: float


@dataclass(frozen=True)
class QualityResult:
    silver_valid: bool
    pricing_ready: bool
    quarantine_reasons: list[str]
    warnings: list[str]
    completeness: CompletenessScores


def load_source_registry(path: str | Path = "config/source_registry.yml") -> dict[str, dict[str, Any]]:
    registry_path = Path(path)
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    return {source["name"]: source for source in payload["sources"]}


def evaluate_listing(
    record: CanonicalListing | Mapping[str, Any],
    source_registry: Mapping[str, Mapping[str, Any]] | None = None,
) -> QualityResult:
    listing = record if isinstance(record, CanonicalListing) else CanonicalListing.from_mapping(dict(record))
    reasons: list[str] = []
    warnings: list[str] = []

    completeness = _compute_completeness(listing)

    for _, field_names, reason in REQUIRED_GROUPS:
        if not any(_is_present(getattr(listing, field_name)) for field_name in field_names):
            reasons.append(reason)

    _validate_core_values(listing, reasons, warnings)
    _validate_source_policy(listing, source_registry, reasons, warnings)
    _validate_record_type_and_availability(listing, reasons)
    _validate_parser_quality(listing, reasons, warnings)
    _validate_model_family(listing, reasons, warnings)
    _validate_variant_quality(listing, reasons)

    unique_reasons = list(dict.fromkeys(reasons))
    unique_warnings = list(dict.fromkeys(warnings))
    silver_valid = not any(reason in SILVER_BLOCKING_REASONS for reason in unique_reasons)
    pricing_ready = silver_valid and not unique_reasons and completeness.required == 1.0

    return QualityResult(
        silver_valid=silver_valid,
        pricing_ready=pricing_ready,
        quarantine_reasons=unique_reasons,
        warnings=unique_warnings,
        completeness=completeness,
    )


def _compute_completeness(listing: CanonicalListing) -> CompletenessScores:
    required_present = 0
    for _, field_names, _ in REQUIRED_GROUPS:
        if any(_is_present(getattr(listing, field_name)) for field_name in field_names):
            required_present += 1

    high_value_present = sum(1 for field_name in HIGH_VALUE_FIELDS if _is_present(getattr(listing, field_name)))
    optional_present = sum(1 for field_name in OPTIONAL_FIELDS if _is_present(getattr(listing, field_name)))

    required = required_present / len(REQUIRED_GROUPS)
    high_value = high_value_present / len(HIGH_VALUE_FIELDS)
    optional = optional_present / len(OPTIONAL_FIELDS)
    overall = (required * 0.70) + (high_value * 0.20) + (optional * 0.10)

    return CompletenessScores(
        required=round(required, 4),
        high_value=round(high_value, 4),
        optional=round(optional, 4),
        overall=round(overall, 4),
    )


def _validate_core_values(listing: CanonicalListing, reasons: list[str], warnings: list[str]) -> None:
    if _is_present(listing.captured_at) and not _is_valid_datetime(listing.captured_at):
        reasons.append("invalid_captured_at")

    current_year = date.today().year
    if listing.model_year is not None and not (1990 <= int(listing.model_year) <= current_year + 1):
        reasons.append("invalid_model_year")

    if listing.listed_price_inr is not None:
        if int(listing.listed_price_inr) <= 0:
            reasons.append("invalid_price")
        elif int(listing.listed_price_inr) < 50_000:
            warnings.append("price_below_soft_minimum")

    if listing.km_driven is not None:
        if int(listing.km_driven) < 0 or int(listing.km_driven) > 500_000:
            reasons.append("invalid_km")
        elif int(listing.km_driven) > 300_000:
            warnings.append("km_above_soft_maximum")

    if listing.fuel_type is not None and listing.fuel_type not in ALLOWED_FUEL_TYPES:
        reasons.append("unknown_fuel_type")

    if listing.transmission is not None and listing.transmission not in ALLOWED_TRANSMISSIONS:
        reasons.append("unknown_transmission")

    if listing.currency is not None and listing.currency not in ALLOWED_CURRENCIES:
        reasons.append("invalid_currency")


def _validate_source_policy(
    listing: CanonicalListing,
    source_registry: Mapping[str, Mapping[str, Any]] | None,
    reasons: list[str],
    warnings: list[str],
) -> None:
    if source_registry is None or not listing.source:
        return

    source = source_registry.get(listing.source)
    if source is None:
        reasons.append("unknown_source")
        return

    role = str(source.get("recommended_role", ""))
    priority = int(source.get("first_adapter_priority", 999))
    if role.startswith("research_only") or priority >= 90:
        reasons.append("source_not_mvp_eligible")

    if source.get("source_type") == "classified":
        warnings.append("classified_source")


def _validate_record_type_and_availability(listing: CanonicalListing, reasons: list[str]) -> None:
    if listing.source_record_type and listing.source_record_type != "listing":
        reasons.append("non_listing_record")

    if listing.is_available is False:
        reasons.append("listing_unavailable")

    if listing.commercial_vehicle_flag is True:
        reasons.append("commercial_vehicle")


def _validate_parser_quality(
    listing: CanonicalListing,
    reasons: list[str],
    warnings: list[str],
) -> None:
    parse_confidence = listing.parse_confidence if listing.parse_confidence is not None else 0.0
    if parse_confidence < 0.90:
        reasons.append("parse_confidence_below_gold_threshold")

    for warning in listing.parse_warnings:
        if warning in CRITICAL_PARSE_WARNINGS:
            reasons.append(warning)
        else:
            warnings.append(warning)


def _validate_model_family(
    listing: CanonicalListing,
    reasons: list[str],
    warnings: list[str],
) -> None:
    if not listing.model:
        return

    model_text = listing.model.lower()
    if re.search(r"\b\d\.\d\b", model_text):
        reasons.append("model_contains_engine_or_displacement")

    variant_terms = {"turbo", "cvt", "dct", "amt", "automatic", "manual"}
    if any(re.search(rf"\b{re.escape(term)}\b", model_text) for term in variant_terms):
        warnings.append("model_may_contain_variant_detail")


def _validate_variant_quality(listing: CanonicalListing, reasons: list[str]) -> None:
    if listing.variant and is_price_like_text(listing.variant):
        reasons.append("variant_contains_price_text")


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != "" and value.strip().lower() != "unknown"
    if isinstance(value, list | tuple | set | dict):
        return len(value) > 0
    return True


def _is_valid_datetime(value: Any) -> bool:
    if isinstance(value, datetime):
        return True
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return True
    return False
