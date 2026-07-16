"""Maruti Suzuki True Value source adapter for extracted listing payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from used_car_price_intelligence.adapters.common import (
    AdapterRunContext,
    PayloadContractFailure,
    PayloadContractResult,
    format_contract_error,
    parse_year,
    stable_hash,
)
from used_car_price_intelligence.parsers import (
    normalize_null,
    parse_fuel_type,
    parse_km_driven,
    parse_ownership,
    parse_price_inr,
    parse_registration,
    parse_title,
    parse_transmission,
)
from used_car_price_intelligence.schema import CanonicalListing


TRUE_VALUE_REQUIRED_RAW_FIELDS = (
    "sku",
    "title",
    "price",
    "model_year",
    "model",
    "variant",
    "km",
    "fuel",
    "transmission",
    "ownership",
    "registration",
    "locality",
)


class TrueValueExtractedPayloadAdapter:
    """Convert extracted True Value listing payloads into canonical records."""

    source = "true_value"

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def validate_payload(self) -> PayloadContractResult:
        return validate_true_value_extracted_payload(self.payload)

    def to_canonical_records(self, context: AdapterRunContext) -> list[CanonicalListing]:
        contract_result = self.validate_payload()
        if not contract_result.ok:
            raise ValueError(format_contract_error("True Value", contract_result))

        payload = self.payload
        records: list[CanonicalListing] = []
        parser_version = context.parser_version or "true_value_graphql_adapter_v0.1"

        for index, fixture_record in enumerate(payload["records"], start=1):
            raw = fixture_record["raw"]
            raw_hash = stable_hash(raw)
            title_result = parse_title(raw.get("title"))
            price_result = parse_price_inr(raw.get("price"))
            km_result = parse_km_driven(raw.get("km"))
            fuel_result = parse_fuel_type(raw.get("fuel"))
            transmission_result = parse_transmission(raw.get("transmission"))
            ownership_result = parse_ownership(raw.get("ownership") or raw.get("owner_text"))
            registration_result = parse_registration(raw.get("registration"))
            emi_result = parse_price_inr(raw.get("emi"))

            title_value = title_result.normalized_value or {}
            registration_value = registration_result.normalized_value or {}
            parse_results = [
                title_result,
                price_result,
                km_result,
                fuel_result,
                transmission_result,
                registration_result,
            ]
            parse_warnings = [warning for result in parse_results for warning in result.warnings]
            parse_confidence = min(result.confidence for result in parse_results)

            records.append(
                CanonicalListing(
                    source=self.source,
                    source_listing_id=_source_listing_id(raw, index, raw_hash),
                    listing_url=_listing_url(payload.get("source_url"), raw),
                    captured_at=context.captured_at,
                    city=context.city,
                    state=context.state,
                    locality=raw.get("locality") or raw.get("dealer_location") or raw.get("city"),
                    hub_name=raw.get("dealer_location") or raw.get("locality"),
                    brand=title_value.get("brand") or "Maruti Suzuki",
                    model=title_value.get("model") or raw.get("model"),
                    variant=raw.get("variant") or title_value.get("variant"),
                    model_year=title_value.get("model_year") or _safe_int(raw.get("model_year")),
                    manufacture_year=parse_year(raw.get("make_year") or raw.get("model_year")),
                    registration_year=parse_year(raw.get("registration_date")),
                    fuel_type=fuel_result.normalized_value,
                    transmission=transmission_result.normalized_value,
                    km_driven=km_result.normalized_value,
                    ownership=ownership_result.normalized_value if ownership_result.ok else None,
                    registration_state=registration_value.get("registration_state"),
                    registration_code=registration_value.get("registration_code"),
                    registration_type=registration_value.get("registration_type"),
                    body_type=raw.get("body_type"),
                    color=raw.get("color"),
                    listed_price_inr=price_result.normalized_value,
                    emi_amount_inr=emi_result.normalized_value if emi_result.ok else None,
                    currency=raw.get("currency") or "INR",
                    seller_type="oem_dealer",
                    dealer_name=raw.get("dealer_name"),
                    is_certified=_parse_true_value_certified(raw.get("true_value_certified")),
                    inspection_status=_inspection_status(raw),
                    warranty_label=_warranty_label(raw.get("warranty_info")),
                    finance_label="finance_available" if raw.get("emi") or raw.get("mssf_finance") == "1" else None,
                    is_available=_parse_bool_like(raw.get("in_stock"), default=True),
                    listing_posted_at=raw.get("listing_posted_at"),
                    source_record_type="listing",
                    source_title_text=raw.get("title"),
                    source_variant_text=raw.get("variant"),
                    raw_record_hash=raw_hash,
                    ingestion_run_id=context.ingestion_run_id,
                    parser_version=parser_version,
                    schema_version=context.schema_version,
                    parse_confidence=parse_confidence,
                    parse_warnings=parse_warnings,
                    extra_fields=_true_value_extra_fields(raw),
                )
            )

        return records


class TrueValueFixtureAdapter(TrueValueExtractedPayloadAdapter):
    """Load a True Value extracted fixture and adapt it."""

    def __init__(self, fixture_path: str | Path):
        self.fixture_path = Path(fixture_path)
        super().__init__({})

    def load_payload(self) -> dict[str, Any]:
        return json.loads(self.fixture_path.read_text(encoding="utf-8"))

    def to_canonical_records(self, context: AdapterRunContext) -> list[CanonicalListing]:
        self.payload = self.load_payload()
        return super().to_canonical_records(context)


def validate_true_value_extracted_payload(payload: dict[str, Any]) -> PayloadContractResult:
    failures: list[PayloadContractFailure] = []
    source = str(payload.get("source") or "unknown") if isinstance(payload, dict) else "unknown"

    if not isinstance(payload, dict):
        return PayloadContractResult(
            source=source,
            records_total=0,
            failures=(
                PayloadContractFailure(
                    record_index=None,
                    field_name="payload",
                    reason="payload_must_be_json_object",
                ),
            ),
        )

    if payload.get("source") != "true_value":
        failures.append(
            PayloadContractFailure(
                record_index=None,
                field_name="source",
                reason="source_must_be_true_value",
            )
        )

    if normalize_null(payload.get("source_url")) is None:
        failures.append(
            PayloadContractFailure(
                record_index=None,
                field_name="source_url",
                reason="missing_source_url",
            )
        )

    records = payload.get("records")
    if not isinstance(records, list):
        failures.append(
            PayloadContractFailure(
                record_index=None,
                field_name="records",
                reason="records_must_be_array",
            )
        )
        return PayloadContractResult(source=source, records_total=0, failures=tuple(failures))

    if not records:
        failures.append(
            PayloadContractFailure(
                record_index=None,
                field_name="records",
                reason="records_must_not_be_empty",
            )
        )

    for index, record in enumerate(records, start=1):
        raw = record.get("raw") if isinstance(record, dict) else None
        if not isinstance(raw, dict):
            failures.append(
                PayloadContractFailure(
                    record_index=index,
                    field_name="raw",
                    reason="raw_must_be_object",
                )
            )
            continue

        for field_name in TRUE_VALUE_REQUIRED_RAW_FIELDS:
            if normalize_null(raw.get(field_name)) is None:
                failures.append(
                    PayloadContractFailure(
                        record_index=index,
                        field_name=field_name,
                        reason="missing_required_raw_field",
                    )
                )

        if not _price_is_valid(raw.get("price")):
            failures.append(
                PayloadContractFailure(
                    record_index=index,
                    field_name="price",
                    reason="price_must_be_positive_number",
                )
            )

    return PayloadContractResult(source=source, records_total=len(records), failures=tuple(failures))


def _source_listing_id(raw: dict[str, Any], index: int, raw_hash: str) -> str:
    sku = normalize_null(raw.get("sku"))
    if sku:
        return f"true_value_{sku}"
    external_id = normalize_null(raw.get("external_id"))
    if external_id:
        return f"true_value_external_{external_id}"
    return f"true_value_extracted_{index:03d}_{raw_hash[:8]}"


def _listing_url(source_url: Any, raw: dict[str, Any]) -> str:
    if raw.get("listing_url"):
        return str(raw["listing_url"])
    url_key = normalize_null(raw.get("url_key"))
    if url_key:
        return urljoin(str(source_url or "https://www.marutisuzukitruevalue.com"), f"/{url_key}")
    return f"{source_url}#record-{raw.get('sku', 'unknown')}"


def _inspection_status(raw: dict[str, Any]) -> str:
    dms_status = normalize_null(raw.get("dms_certification_status"))
    if _parse_true_value_certified(raw.get("true_value_certified")):
        return "true_value_certified"
    if dms_status:
        return f"true_value_status_{dms_status.lower()}"
    return "true_value_inventory"


def _warranty_label(value: Any) -> str | None:
    text = normalize_null(value)
    if text is None:
        return None
    upper = text.upper()
    if upper in {"0M", "0", "NO", "N"}:
        return None
    if upper.endswith("Y"):
        years = upper[:-1]
        return f"{years} year warranty" if years == "1" else f"{years} years warranty"
    if upper.endswith("M"):
        months = upper[:-1]
        return f"{months} months warranty"
    return text


def _true_value_extra_fields(raw: dict[str, Any]) -> dict[str, Any]:
    fields = {}
    for key in [
        "sku",
        "external_id",
        "url_key",
        "dealer_code",
        "dealer_location",
        "dealer_map_code",
        "dealer_parent_group",
        "dms_certification_status",
        "number_of_owners",
        "registration_date",
        "rto_code",
        "warranty_info",
        "listing_score",
        "overall_rating",
        "engine_rating",
        "exterior_rating",
        "frame_rating",
        "functional_rating",
        "electrical_rating",
        "suspension_rating",
        "engine_capacity",
        "engine_type",
        "latitude",
        "longitude",
        "mssf_finance",
        "fmp_emi_amount",
    ]:
        if raw.get(key) not in (None, "", [], {}):
            fields[key] = raw[key]
    return {"true_value": fields} if fields else {}


def _parse_true_value_certified(value: Any) -> bool:
    text = normalize_null(value)
    if text is None:
        return False
    return text.lower() in {"1", "true", "yes", "y", "certified", "cr"}


def _parse_bool_like(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = normalize_null(value)
    if text is None:
        return default
    return text.lower() in {"1", "true", "yes", "y"}


def _price_is_valid(value: Any) -> bool:
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
