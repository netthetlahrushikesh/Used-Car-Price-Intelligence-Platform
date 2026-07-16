"""Live acquisition helpers for public source pages."""

from used_car_price_intelligence.acquisition.mahindra_first_choice_live import (
    build_mfc_payload_from_result_pages,
    capture_mfc_listing_payload,
    mfc_structured_listing_to_raw,
    summarize_mfc_listing_payload,
)
from used_car_price_intelligence.acquisition.spinny_live import (
    build_spinny_payload_from_card_snapshots,
    build_spinny_payload_from_card_texts,
    capture_spinny_detail_payload,
    capture_spinny_listing_payload,
    merge_spinny_detail_payload_into_listing_payload,
    parse_spinny_card_text,
    parse_spinny_detail_text,
    summarize_spinny_listing_payload,
    summarize_spinny_detail_payload,
)
from used_car_price_intelligence.acquisition.spinny_incremental import (
    build_spinny_incremental_detail_payload,
    build_spinny_incremental_detail_plan,
    load_spinny_detail_payloads,
    normalize_spinny_listing_url,
    spinny_detail_cache_index,
    spinny_listing_urls_from_payload,
)
from used_car_price_intelligence.acquisition.true_value_live import (
    build_true_value_payload_from_product_pages,
    capture_true_value_listing_payload,
    discover_true_value_dealers,
    fetch_true_value_product_page,
    summarize_true_value_listing_payload,
    true_value_dealer_ids,
    true_value_product_to_raw,
)

__all__ = [
    "build_mfc_payload_from_result_pages",
    "build_spinny_payload_from_card_snapshots",
    "build_spinny_payload_from_card_texts",
    "build_spinny_incremental_detail_payload",
    "build_spinny_incremental_detail_plan",
    "build_true_value_payload_from_product_pages",
    "capture_mfc_listing_payload",
    "capture_spinny_detail_payload",
    "capture_spinny_listing_payload",
    "capture_true_value_listing_payload",
    "discover_true_value_dealers",
    "fetch_true_value_product_page",
    "load_spinny_detail_payloads",
    "mfc_structured_listing_to_raw",
    "merge_spinny_detail_payload_into_listing_payload",
    "normalize_spinny_listing_url",
    "parse_spinny_card_text",
    "parse_spinny_detail_text",
    "spinny_detail_cache_index",
    "spinny_listing_urls_from_payload",
    "summarize_mfc_listing_payload",
    "summarize_spinny_listing_payload",
    "summarize_spinny_detail_payload",
    "summarize_true_value_listing_payload",
    "true_value_dealer_ids",
    "true_value_product_to_raw",
]
