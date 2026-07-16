"""Spinny source adapter for extracted listing-card fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from used_car_price_intelligence.adapters.common import (
    AdapterRunContext,
    PayloadContractFailure,
    PayloadContractResult,
    format_contract_error,
    parse_year,
    stable_hash,
)
from used_car_price_intelligence.parsers import (
    is_price_like_text,
    normalize_null,
    parse_fuel_type,
    parse_km_driven,
    parse_ownership,
    parse_price_inr,
    parse_registration,
    parse_spinny_variant_from_listing_url,
    parse_title,
    parse_transmission,
)
from used_car_price_intelligence.schema import CanonicalListing


SPINNY_REQUIRED_RAW_FIELDS = (
    "title",
    "price",
    "variant",
    "km",
    "fuel",
    "transmission",
    "registration",
    "locality",
)


class SpinnyExtractedPayloadAdapter:
    """Convert extracted Spinny listing-card payloads into canonical records."""

    source = "spinny"

    def __init__(self, payload: dict[str, Any], source_listing_id_prefix: str = "spinny_extracted"):
        self.payload = payload
        self.source_listing_id_prefix = source_listing_id_prefix

    def validate_payload(self) -> PayloadContractResult:
        return validate_spinny_extracted_payload(self.payload)

    def to_canonical_records(self, context: AdapterRunContext) -> list[CanonicalListing]:
        contract_result = self.validate_payload()
        if not contract_result.ok:
            raise ValueError(_format_contract_error(contract_result))

        payload = self.payload
        records: list[CanonicalListing] = []
        parser_version = context.parser_version or "spinny_extracted_payload_adapter_v0.2"

        for index, fixture_record in enumerate(payload["records"], start=1):
            raw = fixture_record["raw"]
            raw_hash = stable_hash(raw)
            title_result = parse_title(raw.get("title"))
            price_result = parse_price_inr(raw.get("price"))
            km_result = parse_km_driven(raw.get("km"))
            fuel_result = parse_fuel_type(raw.get("fuel"))
            transmission_result = parse_transmission(raw.get("transmission"))
            registration_result = parse_registration(raw.get("rto") or raw.get("registration"))
            ownership_result = parse_ownership(raw.get("ownership"))
            emi_result = parse_price_inr(raw.get("emi"))

            title_value = title_result.normalized_value or {}
            registration_value = registration_result.normalized_value or {}
            variant_value, source_variant_text, variant_warnings = _resolve_spinny_variant(
                raw,
                title_value.get("variant"),
            )
            parse_results = [
                title_result,
                price_result,
                km_result,
                fuel_result,
                transmission_result,
                registration_result,
            ]
            parse_warnings = [
                warning for result in parse_results for warning in result.warnings
            ]
            parse_warnings.extend(variant_warnings)
            parse_confidence = min(result.confidence for result in parse_results)

            records.append(
                CanonicalListing(
                    source=self.source,
                    source_listing_id=f"{self.source_listing_id_prefix}_{index:03d}_{raw_hash[:8]}",
                    listing_url=raw.get("listing_url") or f"{payload['source_url']}#record-{index}",
                    captured_at=context.captured_at,
                    city=context.city,
                    state=context.state,
                    locality=raw.get("detail_locality") or raw.get("locality"),
                    hub_name=raw.get("locality"),
                    brand=title_value.get("brand"),
                    model=title_value.get("model"),
                    variant=variant_value,
                    model_year=title_value.get("model_year"),
                    manufacture_year=parse_year(raw.get("make_year")),
                    registration_year=parse_year(raw.get("registration_year")),
                    fuel_type=fuel_result.normalized_value,
                    transmission=transmission_result.normalized_value,
                    km_driven=km_result.normalized_value,
                    ownership=ownership_result.normalized_value if ownership_result.ok else None,
                    registration_state=registration_value.get("registration_state"),
                    registration_code=registration_value.get("registration_code"),
                    registration_type=registration_value.get("registration_type"),
                    listed_price_inr=price_result.normalized_value,
                    emi_amount_inr=emi_result.normalized_value if emi_result.ok else None,
                    currency="INR",
                    seller_type="platform",
                    is_certified=True,
                    inspection_status=raw.get("inspection_status"),
                    finance_label="finance_available" if raw.get("emi") else None,
                    warranty_label=raw.get("warranty_label"),
                    return_policy_label=raw.get("return_policy_label"),
                    is_available=True,
                    source_record_type="listing",
                    source_title_text=raw.get("title"),
                    source_variant_text=source_variant_text,
                    raw_record_hash=raw_hash,
                    ingestion_run_id=context.ingestion_run_id,
                    parser_version=parser_version,
                    schema_version=context.schema_version,
                    parse_confidence=parse_confidence,
                    parse_warnings=parse_warnings,
                    extra_fields=_detail_extra_fields(raw),
                )
            )

        return records


class SpinnyFixtureAdapter(SpinnyExtractedPayloadAdapter):
    """Load a Spinny extracted listing-card fixture file and adapt it."""

    def __init__(self, fixture_path: str | Path):
        self.fixture_path = Path(fixture_path)
        super().__init__({}, source_listing_id_prefix="spinny_fixture")

    def load_payload(self) -> dict[str, Any]:
        return json.loads(self.fixture_path.read_text(encoding="utf-8"))

    def to_canonical_records(self, context: AdapterRunContext) -> list[CanonicalListing]:
        self.payload = self.load_payload()
        return super().to_canonical_records(context)


def validate_spinny_extracted_payload(payload: dict[str, Any]) -> PayloadContractResult:
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

    if payload.get("source") != "spinny":
        failures.append(
            PayloadContractFailure(
                record_index=None,
                field_name="source",
                reason="source_must_be_spinny",
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

        for field_name in SPINNY_REQUIRED_RAW_FIELDS:
            if normalize_null(raw.get(field_name)) is None:
                failures.append(
                    PayloadContractFailure(
                        record_index=index,
                        field_name=field_name,
                        reason="missing_required_raw_field",
                    )
                )

    return PayloadContractResult(source=source, records_total=len(records), failures=tuple(failures))


def _detail_extra_fields(raw: dict[str, Any]) -> dict[str, Any]:
    detail_fields = {
        key: raw[key]
        for key in [
            "insurance_validity",
            "insurance_type",
            "inspection_summary",
            "quality_scores",
            "service_due_text",
        ]
        if raw.get(key) not in (None, "", [], {})
    }
    if not detail_fields:
        return {}
    return {"spinny_detail": detail_fields}


def _resolve_spinny_variant(
    raw: dict[str, Any],
    title_variant: Any,
) -> tuple[str | None, str | None, list[str]]:
    raw_variant = normalize_null(raw.get("variant"))
    if raw_variant and not is_price_like_text(raw_variant):
        return raw_variant, raw_variant, []

    warnings: list[str] = []
    if raw_variant and is_price_like_text(raw_variant):
        warnings.append("variant_price_text_rejected")

    url_variant = parse_spinny_variant_from_listing_url(raw.get("listing_url"))
    if url_variant:
        warnings.append("variant_recovered_from_listing_url")
        return url_variant, url_variant, warnings

    fallback_variant = normalize_null(title_variant)
    if fallback_variant:
        warnings.append("variant_recovered_from_title")
        return fallback_variant, fallback_variant, warnings

    if raw_variant:
        return None, None, warnings
    return None, None, []


def _format_contract_error(result: PayloadContractResult) -> str:
    return format_contract_error("Spinny", result)
