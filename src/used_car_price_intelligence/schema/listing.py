"""Canonical listing schema for validated used-car records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any


@dataclass
class CanonicalListing:
    """Canonical used-car listing record.

    The dataclass intentionally allows nullable fields because validation decides
    whether a record is silver-valid, gold pricing-ready, or quarantined.
    """

    source: str | None = None
    source_listing_id: str | None = None
    listing_url: str | None = None
    captured_at: datetime | str | None = None
    city: str | None = None
    state: str | None = None
    locality: str | None = None
    hub_name: str | None = None
    brand: str | None = None
    model: str | None = None
    variant: str | None = None
    model_year: int | None = None
    manufacture_year: int | None = None
    registration_year: int | None = None
    fuel_type: str | None = None
    transmission: str | None = None
    km_driven: int | None = None
    ownership: int | None = None
    registration_state: str | None = None
    registration_code: str | None = None
    registration_type: str | None = None
    body_type: str | None = None
    color: str | None = None
    seating_capacity: int | None = None
    listed_price_inr: int | None = None
    original_price_inr: int | None = None
    discount_amount_inr: int | None = None
    emi_amount_inr: int | None = None
    token_amount_inr: int | None = None
    currency: str | None = "INR"
    price_label: str | None = None
    deal_rating: str | None = None
    extra_charges_flag: bool | None = None
    seller_type: str | None = None
    dealer_name: str | None = None
    is_certified: bool | None = None
    inspection_status: str | None = None
    inspection_score: float | None = None
    condition_grade: str | None = None
    accident_history: str | None = None
    service_history_available: bool | None = None
    commercial_vehicle_flag: bool | None = None
    warranty_label: str | None = None
    return_policy_label: str | None = None
    finance_label: str | None = None
    is_available: bool | None = None
    listing_posted_at: datetime | str | None = None
    source_record_type: str | None = "listing"
    first_seen_at: datetime | str | None = None
    last_seen_at: datetime | str | None = None
    source_title_text: str | None = None
    source_variant_text: str | None = None
    raw_record_hash: str | None = None
    ingestion_run_id: str | None = None
    parser_version: str | None = None
    schema_version: str | None = "canonical_listing_v0.1"
    parse_confidence: float | None = 1.0
    parse_warnings: list[str] = field(default_factory=list)
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "CanonicalListing":
        known_fields = {field_info.name for field_info in fields(cls)}
        kwargs = {key: value for key, value in data.items() if key in known_fields}
        extra = {key: value for key, value in data.items() if key not in known_fields}
        record = cls(**kwargs)
        record.extra_fields.update(extra)
        return record

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
