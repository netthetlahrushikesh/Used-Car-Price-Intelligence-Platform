"""Mahindra First Choice source adapter for extracted listing-card fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from used_car_price_intelligence.adapters.common import (
    AdapterRunContext,
    PayloadContractFailure,
    PayloadContractResult,
    format_contract_error,
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


MAHINDRA_FIRST_CHOICE_REQUIRED_RAW_FIELDS = (
    "score",
    "title",
    "variant_details",
    "price",
    "locality",
)


class MahindraFirstChoiceExtractedPayloadAdapter:
    """Convert extracted Mahindra First Choice listing-card payloads into canonical records."""

    source = "mahindra_first_choice"

    def __init__(
        self,
        payload: dict[str, Any],
        source_listing_id_prefix: str = "mahindra_first_choice_extracted",
    ):
        self.payload = payload
        self.source_listing_id_prefix = source_listing_id_prefix

    def validate_payload(self) -> PayloadContractResult:
        return validate_mahindra_first_choice_extracted_payload(self.payload)

    def to_canonical_records(self, context: AdapterRunContext) -> list[CanonicalListing]:
        contract_result = self.validate_payload()
        if not contract_result.ok:
            raise ValueError(format_contract_error("Mahindra First Choice", contract_result))

        payload = self.payload
        records: list[CanonicalListing] = []
        parser_version = context.parser_version or "mahindra_first_choice_listing_card_adapter_v0.1"

        for index, fixture_record in enumerate(payload["records"], start=1):
            raw = fixture_record["raw"]
            raw_hash = stable_hash(raw)
            detail_parts = parse_mfc_variant_details(raw["variant_details"])
            title_result = parse_title(raw.get("title"))
            price_result = parse_price_inr(raw.get("price"))
            km_result = parse_km_driven(raw.get("km") or detail_parts["km"])
            fuel_result = parse_fuel_type(raw.get("fuel") or detail_parts["fuel"])
            transmission_result = parse_transmission(
                raw.get("transmission") or detail_parts["transmission"]
            )
            ownership_result = parse_ownership(raw.get("owner_text") or raw.get("ownership"))
            registration_result = parse_registration(
                raw.get("registration") or raw.get("registration_number")
            )
            emi_result = parse_price_inr(raw.get("emi"))

            title_value = _structured_title_value(raw, title_result.normalized_value or {})
            parse_results = [
                price_result,
                km_result,
                fuel_result,
                transmission_result,
            ]
            title_parse_warnings = [] if _has_structured_title(raw) else title_result.warnings
            parse_warnings = [
                warning for result in parse_results for warning in result.warnings
            ] + title_parse_warnings
            title_confidence = 0.98 if _has_structured_title(raw) else title_result.confidence
            parse_confidence = min([title_confidence, *(result.confidence for result in parse_results)])
            registration_value = registration_result.normalized_value or {}

            records.append(
                CanonicalListing(
                    source=self.source,
                    source_listing_id=_source_listing_id(raw, self.source_listing_id_prefix, index, raw_hash),
                    listing_url=raw.get("listing_url") or f"{payload['source_url']}#record-{index}",
                    captured_at=context.captured_at,
                    city=context.city,
                    state=context.state,
                    locality=raw.get("locality"),
                    hub_name=raw.get("locality"),
                    brand=title_value.get("brand"),
                    model=title_value.get("model"),
                    variant=raw.get("variant") or detail_parts["variant"] or title_value.get("variant"),
                    model_year=title_value.get("model_year"),
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
                    currency="INR",
                    seller_type=_normalize_mfc_seller_type(raw.get("seller_type")),
                    dealer_name=raw.get("dealer_name"),
                    is_certified=_parse_bool_like(raw.get("is_certified"), default=True),
                    inspection_status="mfc_certified_public_card",
                    warranty_label=raw.get("warranty_label"),
                    finance_label="finance_available" if raw.get("emi") else None,
                    is_available=True,
                    listing_posted_at=raw.get("listing_posted_at"),
                    source_record_type="listing",
                    source_title_text=raw.get("title"),
                    source_variant_text=raw.get("variant_details"),
                    raw_record_hash=raw_hash,
                    ingestion_run_id=context.ingestion_run_id,
                    parser_version=parser_version,
                    schema_version=context.schema_version,
                    parse_confidence=parse_confidence,
                    parse_warnings=parse_warnings,
                    extra_fields=_mfc_extra_fields(raw),
                )
            )

        return records


class MahindraFirstChoiceFixtureAdapter(MahindraFirstChoiceExtractedPayloadAdapter):
    """Load a Mahindra First Choice extracted listing-card fixture and adapt it."""

    def __init__(self, fixture_path: str | Path):
        self.fixture_path = Path(fixture_path)
        super().__init__({}, source_listing_id_prefix="mahindra_first_choice_fixture")

    def load_payload(self) -> dict[str, Any]:
        return json.loads(self.fixture_path.read_text(encoding="utf-8"))

    def to_canonical_records(self, context: AdapterRunContext) -> list[CanonicalListing]:
        self.payload = self.load_payload()
        return super().to_canonical_records(context)


def validate_mahindra_first_choice_extracted_payload(
    payload: dict[str, Any],
) -> PayloadContractResult:
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

    if payload.get("source") != "mahindra_first_choice":
        failures.append(
            PayloadContractFailure(
                record_index=None,
                field_name="source",
                reason="source_must_be_mahindra_first_choice",
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

        for field_name in MAHINDRA_FIRST_CHOICE_REQUIRED_RAW_FIELDS:
            if normalize_null(raw.get(field_name)) is None:
                failures.append(
                    PayloadContractFailure(
                        record_index=index,
                        field_name=field_name,
                        reason="missing_required_raw_field",
                    )
                )

        if not _score_is_valid(raw.get("score")):
            failures.append(
                PayloadContractFailure(
                    record_index=index,
                    field_name="score",
                    reason="score_must_be_decimal_0_to_10",
                )
            )

        detail_parts = parse_mfc_variant_details(raw.get("variant_details"))
        for field_name, value in detail_parts.items():
            if normalize_null(value) is None:
                failures.append(
                    PayloadContractFailure(
                        record_index=index,
                        field_name=f"variant_details.{field_name}",
                        reason="missing_variant_detail_segment",
                    )
                )

    return PayloadContractResult(source=source, records_total=len(records), failures=tuple(failures))


def parse_mfc_variant_details(value: Any) -> dict[str, str | None]:
    text = normalize_null(value)
    empty_parts = {
        "variant": None,
        "km": None,
        "fuel": None,
        "transmission": None,
    }
    if text is None:
        return empty_parts

    parts = [normalize_null(part) for part in str(text).split("|")]
    if len(parts) < 4:
        return {
            **empty_parts,
            **{field: parts[index] for index, field in enumerate(empty_parts) if index < len(parts)},
        }

    return {
        "variant": parts[0],
        "km": parts[1],
        "fuel": parts[2],
        "transmission": parts[3],
    }


def _score_is_valid(value: Any) -> bool:
    text = normalize_null(value)
    if text is None:
        return False
    try:
        score = float(text)
    except ValueError:
        return False
    return 0 <= score <= 10


def _mfc_extra_fields(raw: dict[str, Any]) -> dict[str, Any]:
    extra_fields: dict[str, Any] = {
        "rating_score": float(raw["score"]),
        "variant_details": raw.get("variant_details"),
    }
    for key in [
        "id_classified",
        "stock_id",
        "photo_count",
        "mileage",
        "source_price_value",
        "source_city",
        "source_state",
    ]:
        if raw.get(key) not in (None, "", [], {}):
            extra_fields[key] = raw[key]
    if raw.get("emi"):
        extra_fields["emi_text"] = raw["emi"]
    return {"mahindra_first_choice": extra_fields}


def _has_structured_title(raw: dict[str, Any]) -> bool:
    return all(
        normalize_null(raw.get(field_name)) is not None
        for field_name in ("model_year", "brand", "model")
    )


def _structured_title_value(
    raw: dict[str, Any],
    parsed_title_value: dict[str, Any],
) -> dict[str, Any]:
    if not _has_structured_title(raw):
        return parsed_title_value
    return {
        "model_year": int(raw["model_year"]),
        "brand": raw["brand"],
        "model": raw["model"],
        "variant": raw.get("variant") or parsed_title_value.get("variant"),
    }


def _source_listing_id(
    raw: dict[str, Any],
    source_listing_id_prefix: str,
    index: int,
    raw_hash: str,
) -> str:
    id_classified = normalize_null(raw.get("id_classified"))
    if id_classified is not None:
        return f"mfc_{id_classified}"
    stock_id = normalize_null(raw.get("stock_id"))
    if stock_id is not None:
        return f"mfc_stock_{stock_id}"
    return f"{source_listing_id_prefix}_{index:03d}_{raw_hash[:8]}"


def _normalize_mfc_seller_type(value: Any) -> str:
    text = normalize_null(value)
    if text is None:
        return "dealer"
    if text.lower() == "dealer":
        return "dealer"
    return text.lower()


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
    return text.lower() in {"1", "true", "yes", "y", "certified"}
