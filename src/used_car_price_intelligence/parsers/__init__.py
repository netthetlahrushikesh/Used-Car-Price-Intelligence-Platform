"""Shared parsers for normalizing used-car listing fields."""

from used_car_price_intelligence.parsers.core import (
    ParseResult,
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

__all__ = [
    "ParseResult",
    "is_price_like_text",
    "normalize_null",
    "parse_fuel_type",
    "parse_km_driven",
    "parse_ownership",
    "parse_price_inr",
    "parse_registration",
    "parse_spinny_variant_from_listing_url",
    "parse_title",
    "parse_transmission",
]
