"""Bounded Maruti Suzuki True Value public inventory capture."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from used_car_price_intelligence.adapters import validate_true_value_extracted_payload


DEFAULT_TRUE_VALUE_URL = "https://www.marutisuzukitruevalue.com/buy-car"
TRUE_VALUE_GRAPHQL_URL = "https://www.marutisuzukitruevalue.com/truevalue/api/graphql"
TRUE_VALUE_DEALER_DISCOVERY_URL = "https://www.marutisuzukitruevalue.com/app-service/api/v2/dms/nearest-dealers"
DEFAULT_HYDERABAD_LATITUDE = 17.385044
DEFAULT_HYDERABAD_LONGITUDE = 78.486671

TRUE_VALUE_PRODUCT_SEARCH_QUERY = """
query productSearchByDealers($currentPage: Int = 1, $pageSize: Int = 100, $dealerIds: [String!]) {
  productSearch(
    current_page: $currentPage,
    page_size: $pageSize,
    phrase: "",
    filter: [
      {
        attribute: "dealer_code"
        in: $dealerIds
      }
    ],
    sort: [{ attribute: "inStock", direction: DESC }, { attribute: "distance_driven", direction: ASC }]
  ) {
    items {
      productView {
        __typename
        sku
        externalId
        name
        urlKey
        url
        shortDescription
        description
        metaDescription
        metaKeyword
        metaTitle
        lastModifiedAt
        inStock
        images(roles: ["image"]) { url }
        attributes(roles: []) { name value }
        ... on SimpleProductView {
          price {
            regular { amount { currency value } }
            final { amount { currency value } }
          }
        }
      }
    }
    page_info { current_page page_size total_pages }
    total_count
  }
}
"""


def capture_true_value_listing_payload(
    *,
    source_url: str = DEFAULT_TRUE_VALUE_URL,
    output_path: str | Path,
    captured_at: str | None = None,
    city: str = "Hyderabad",
    state: str = "Telangana",
    latitude: float = DEFAULT_HYDERABAD_LATITUDE,
    longitude: float = DEFAULT_HYDERABAD_LONGITUDE,
    dealer_distance_m: int = 25_000,
    max_records: int = 40,
    min_records: int | None = None,
    max_pages: int = 1,
    page_size: int = 100,
    capture_attempts: int = 3,
    retry_delay_ms: int = 2_000,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    captured_at = captured_at or _utc_now()
    required_records = _resolve_min_records(min_records=min_records)
    last_payload: dict[str, Any] | None = None

    for attempt in range(max(1, capture_attempts)):
        dealer_payload = discover_true_value_dealers(
            latitude=latitude,
            longitude=longitude,
            distance_m=dealer_distance_m,
            timeout_seconds=timeout_seconds,
        )
        dealer_ids = true_value_dealer_ids(dealer_payload)
        result_pages = []
        for page_number in range(1, max(1, max_pages) + 1):
            result_page = fetch_true_value_product_page(
                dealer_ids=dealer_ids,
                current_page=page_number,
                page_size=page_size,
                timeout_seconds=timeout_seconds,
            )
            result_pages.append(result_page)
            records_seen = _unique_product_count(result_pages)
            total_pages = int(result_page.get("page_info", {}).get("total_pages") or 1)
            if records_seen >= max_records or page_number >= total_pages:
                break

        payload = build_true_value_payload_from_product_pages(
            source_url=source_url,
            result_pages=result_pages,
            dealer_payload=dealer_payload,
            captured_at=captured_at,
            city=city,
            state=state,
            max_records=max_records,
            pagination={
                "pagination_type": "dealer_discovery_plus_graphql",
                "max_pages": max_pages,
                "attempted_pages": len(result_pages),
                "page_size": page_size,
                "max_records": max_records,
                "min_records": required_records,
                "coverage_ok": _unique_product_count(result_pages) >= required_records,
                "unique_cards_seen": _unique_product_count(result_pages),
                "returned_records": min(_unique_product_count(result_pages), max(0, max_records)),
                "duplicate_cards_skipped": 0,
                "source_total_items": _source_total_items(result_pages),
                "source_total_pages": _source_total_pages(result_pages),
                "dealer_count": len(dealer_ids),
                "dealer_distance_m": dealer_distance_m,
                "stop_reason": _stop_reason(
                    result_pages=result_pages,
                    max_records=max_records,
                    max_pages=max_pages,
                    min_records=required_records,
                ),
            },
        )
        last_payload = payload
        if validate_true_value_extracted_payload(payload).ok and _payload_meets_min_records(
            payload,
            required_records,
        ):
            break
        if attempt < capture_attempts - 1:
            _sleep_ms(retry_delay_ms)

    payload = last_payload or build_true_value_payload_from_product_pages(
        source_url=source_url,
        result_pages=[],
        dealer_payload={"data": []},
        captured_at=captured_at,
        city=city,
        state=state,
        max_records=max_records,
        pagination={
            "pagination_type": "dealer_discovery_plus_graphql",
            "max_pages": max_pages,
            "attempted_pages": 0,
            "page_size": page_size,
            "max_records": max_records,
            "min_records": required_records,
            "coverage_ok": False,
            "unique_cards_seen": 0,
            "returned_records": 0,
            "duplicate_cards_skipped": 0,
            "source_total_items": 0,
            "source_total_pages": 0,
            "dealer_count": 0,
            "dealer_distance_m": dealer_distance_m,
            "stop_reason": "capture_not_attempted",
        },
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def discover_true_value_dealers(
    *,
    latitude: float,
    longitude: float,
    distance_m: int,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    query = urlencode(
        {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "distance": str(distance_m),
            "channel": "NRM",
            "dealerType": "TV",
        }
    )
    return _http_json(f"{TRUE_VALUE_DEALER_DISCOVERY_URL}?{query}", timeout_seconds=timeout_seconds)


def true_value_dealer_ids(dealer_payload: dict[str, Any]) -> list[str]:
    dealer_ids = []
    for dealer in dealer_payload.get("data") or []:
        map_code = dealer.get("mapCd")
        location_code = dealer.get("locCd")
        parent_group = dealer.get("parentGrp")
        if map_code and location_code and parent_group:
            dealer_ids.append(f"{map_code}-{location_code}-{parent_group}")
    return list(dict.fromkeys(dealer_ids))


def fetch_true_value_product_page(
    *,
    dealer_ids: list[str],
    current_page: int,
    page_size: int,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    payload = {
        "query": TRUE_VALUE_PRODUCT_SEARCH_QUERY,
        "variables": {
            "currentPage": current_page,
            "pageSize": page_size,
            "dealerIds": dealer_ids,
        },
    }
    response = _http_json(TRUE_VALUE_GRAPHQL_URL, data=payload, timeout_seconds=timeout_seconds)
    if response.get("errors"):
        raise RuntimeError(f"True Value GraphQL returned errors: {response['errors']}")
    return response["data"]["productSearch"]


def build_true_value_payload_from_product_pages(
    *,
    source_url: str,
    result_pages: list[dict[str, Any]],
    dealer_payload: dict[str, Any],
    captured_at: str,
    city: str,
    state: str,
    max_records: int,
    pagination: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records = []
    seen_skus: set[str] = set()
    duplicate_rows = 0
    unavailable_rows = 0
    incomplete_rows = 0
    km_outlier_rows = 0
    for result_page in result_pages:
        for item in result_page.get("items") or []:
            product = item.get("productView") or {}
            if not _product_is_available(product):
                unavailable_rows += 1
                continue
            if not _product_has_required_listing_fields(product):
                incomplete_rows += 1
                continue
            if not _product_has_pricing_ready_km(product):
                km_outlier_rows += 1
                continue
            raw = true_value_product_to_raw(product, source_url=source_url)
            sku = str(raw.get("sku") or "")
            if sku and sku in seen_skus:
                duplicate_rows += 1
                continue
            if sku:
                seen_skus.add(sku)
            records.append({"raw": raw})
            if len(records) >= max(0, max_records):
                break
        if len(records) >= max(0, max_records):
            break

    payload = {
        "source": "true_value",
        "source_url": source_url,
        "captured_for": "live_public_search_capture",
        "capture_method": "dealer_discovery_plus_graphql",
        "captured_at": captured_at,
        "city": city,
        "state": state,
        "dealer_discovery": {
            "dealers_total": len(dealer_payload.get("data") or []),
            "dealer_ids": true_value_dealer_ids(dealer_payload),
        },
        "records": records,
    }
    if pagination:
        payload["pagination"] = {
            **pagination,
            "duplicate_cards_skipped": duplicate_rows,
            "unavailable_rows_skipped": unavailable_rows,
            "incomplete_rows_skipped": incomplete_rows,
            "km_outlier_rows_skipped": km_outlier_rows,
        }
    return payload


def true_value_product_to_raw(
    product: dict[str, Any],
    *,
    source_url: str = DEFAULT_TRUE_VALUE_URL,
) -> dict[str, Any]:
    attrs = {attribute.get("name"): attribute.get("value") for attribute in product.get("attributes") or []}
    price = product.get("price") or {}
    price_amount = ((price.get("final") or {}).get("amount") or {}) or (
        (price.get("regular") or {}).get("amount") or {}
    )
    model_year = _safe_int(attrs.get("make_year"))
    model = _first_present(attrs.get("car_model"))
    title = " ".join(str(part) for part in [model_year, "Maruti Suzuki", model] if part)
    image_urls = [image.get("url") for image in product.get("images") or [] if image.get("url")]

    return {
        "sku": product.get("sku"),
        "external_id": product.get("externalId"),
        "title": title,
        "model_year": model_year,
        "brand": "Maruti Suzuki",
        "model": model,
        "variant": _first_present(attrs.get("car_variant")),
        "price": price_amount.get("value"),
        "currency": price_amount.get("currency") or "INR",
        "km": _first_present(attrs.get("distance_driven")),
        "fuel": _first_present(attrs.get("fuel_type")),
        "transmission": _first_present(attrs.get("transmission_type")),
        "ownership": _first_present(attrs.get("ownership")),
        "owner_text": _first_present(attrs.get("ownership")),
        "registration": _first_present(attrs.get("rto")),
        "registration_date": _first_present(attrs.get("registration_date")),
        "locality": _first_present(attrs.get("dealer_location"), attrs.get("car_city")),
        "city": _first_present(attrs.get("car_city")),
        "state": _first_present(attrs.get("state")),
        "body_type": _first_present(attrs.get("body_type")),
        "color": _first_present(attrs.get("color")),
        "dealer_name": _first_present(attrs.get("dealer_name")),
        "dealer_location": _first_present(attrs.get("dealer_location")),
        "dealer_code": _first_present(attrs.get("dealer_code")),
        "dealer_map_code": _first_present(attrs.get("dealer_map_code")),
        "dealer_parent_group": _first_present(attrs.get("dealer_parent_group")),
        "true_value_certified": _first_present(attrs.get("true_value_certified")),
        "dms_certification_status": _first_present(attrs.get("dms_certification_status")),
        "overall_rating": _first_present(attrs.get("overall_rating")),
        "engine_rating": _first_present(attrs.get("engine_rating")),
        "exterior_rating": _first_present(attrs.get("exterior_rating")),
        "frame_rating": _first_present(attrs.get("frame_rating")),
        "functional_rating": _first_present(attrs.get("functional_rating")),
        "electrical_rating": _first_present(attrs.get("electrical_rating")),
        "suspension_rating": _first_present(attrs.get("suspension_rating")),
        "engine_capacity": _first_present(attrs.get("engine_capacity")),
        "engine_type": _first_present(attrs.get("engine_type")),
        "warranty_info": _first_present(attrs.get("warranty_info")),
        "number_of_owners": _first_present(attrs.get("number_of_owners")),
        "listing_score": _first_present(attrs.get("listing_score")),
        "listing_posted_at": _first_present(attrs.get("news_from_date")),
        "rto_code": _first_present(attrs.get("rto_code")),
        "latitude": _first_present(attrs.get("latitude")),
        "longitude": _first_present(attrs.get("longitude")),
        "mssf_finance": _first_present(attrs.get("mssf_finance")),
        "fmp_emi_amount": _first_present(attrs.get("fmp_emi_amount")),
        "url_key": product.get("urlKey"),
        "listing_url": _absolute_listing_url(source_url, product.get("urlKey")),
        "in_stock": product.get("inStock"),
        "last_modified_at": product.get("lastModifiedAt"),
        "image_count": len(image_urls),
    }


def summarize_true_value_listing_payload(listing_payload: dict[str, Any]) -> dict[str, Any]:
    pagination = dict(listing_payload.get("pagination") or {})
    records = [record for record in listing_payload.get("records", []) if isinstance(record, dict)]
    listing_urls = []
    for record in records:
        raw = record.get("raw")
        if isinstance(raw, dict) and raw.get("listing_url"):
            listing_urls.append(str(raw["listing_url"]))

    return {
        "records_total": len(records),
        "listing_urls_total": len(listing_urls),
        "unique_listing_urls": len(set(listing_urls)),
        "pagination_type": pagination.get("pagination_type", "dealer_discovery_plus_graphql"),
        "max_pages": int(pagination.get("max_pages") or 1),
        "attempted_pages": int(pagination.get("attempted_pages") or 0),
        "page_size": int(pagination.get("page_size") or 0),
        "max_records": int(pagination.get("max_records") or len(records)),
        "min_records": int(pagination.get("min_records") or 0),
        "coverage_ok": len(records) >= int(pagination.get("min_records") or 0),
        "unique_cards_seen": int(pagination.get("unique_cards_seen") or len(records)),
        "returned_records": int(pagination.get("returned_records") or len(records)),
        "duplicate_cards_skipped": int(pagination.get("duplicate_cards_skipped") or 0),
        "unavailable_rows_skipped": int(pagination.get("unavailable_rows_skipped") or 0),
        "incomplete_rows_skipped": int(pagination.get("incomplete_rows_skipped") or 0),
        "km_outlier_rows_skipped": int(pagination.get("km_outlier_rows_skipped") or 0),
        "source_total_items": int(pagination.get("source_total_items") or len(records)),
        "source_total_pages": int(pagination.get("source_total_pages") or 1),
        "dealer_count": int(pagination.get("dealer_count") or 0),
        "dealer_distance_m": int(pagination.get("dealer_distance_m") or 0),
        "stop_reason": pagination.get("stop_reason", "record_cap_reached" if records else "unknown"),
    }


def _http_json(
    url: str,
    *,
    data: dict[str, Any] | None = None,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    encoded_data = None
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    if data is not None:
        encoded_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=encoded_data, headers=headers, method="POST" if data else "GET")
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _stop_reason(
    *,
    result_pages: list[dict[str, Any]],
    max_records: int,
    max_pages: int,
    min_records: int,
) -> str:
    records_seen = _unique_product_count(result_pages)
    if records_seen >= max_records:
        return "record_cap_reached"
    if records_seen >= min_records and len(result_pages) >= max_pages:
        return "min_records_met_at_page_cap"
    if result_pages and len(result_pages) >= _source_total_pages(result_pages):
        return "source_total_pages_reached"
    return "page_cap_reached"


def _source_total_items(result_pages: list[dict[str, Any]]) -> int:
    if not result_pages:
        return 0
    return int(result_pages[0].get("total_count") or 0)


def _source_total_pages(result_pages: list[dict[str, Any]]) -> int:
    if not result_pages:
        return 0
    return int((result_pages[0].get("page_info") or {}).get("total_pages") or 1)


def _unique_product_count(result_pages: list[dict[str, Any]]) -> int:
    seen_skus = set()
    for result_page in result_pages:
        for item in result_page.get("items") or []:
            product = item.get("productView") or {}
            if not _product_is_available(product):
                continue
            if not _product_has_required_listing_fields(product):
                continue
            if not _product_has_pricing_ready_km(product):
                continue
            sku = product.get("sku")
            if sku:
                seen_skus.add(str(sku))
    return len(seen_skus)


def _product_is_available(product: dict[str, Any]) -> bool:
    return product.get("inStock") is not False


def _product_has_required_listing_fields(product: dict[str, Any]) -> bool:
    attrs = _product_attrs(product)
    required_attrs = (
        "car_model",
        "car_variant",
        "make_year",
        "distance_driven",
        "fuel_type",
        "transmission_type",
        "ownership",
        "rto",
    )
    if not _first_present(product.get("sku"), product.get("externalId")):
        return False
    if _product_price_amount(product).get("value") in (None, "", [], {}):
        return False
    if not _first_present(attrs.get("dealer_location"), attrs.get("car_city")):
        return False
    return all(_first_present(attrs.get(name)) is not None for name in required_attrs)


def _product_has_pricing_ready_km(product: dict[str, Any]) -> bool:
    km_value = _product_km_value(_product_attrs(product).get("distance_driven"))
    return km_value is not None and km_value <= 300_000


def _product_km_value(value: Any) -> int | None:
    if value in (None, "", [], {}):
        return None
    normalized = str(value).lower().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:(k|thousand)\b)?", normalized)
    if not match:
        return None
    number = float(match.group(1))
    multiplier = 1000 if match.group(2) in {"k", "thousand"} else 1
    return round(number * multiplier)


def _product_attrs(product: dict[str, Any]) -> dict[str, Any]:
    return {attribute.get("name"): attribute.get("value") for attribute in product.get("attributes") or []}


def _product_price_amount(product: dict[str, Any]) -> dict[str, Any]:
    price = product.get("price") or {}
    price_amount = ((price.get("final") or {}).get("amount") or {}) or (
        (price.get("regular") or {}).get("amount") or {}
    )
    return price_amount if isinstance(price_amount, dict) else {}


def _absolute_listing_url(source_url: str, url_key: Any) -> str | None:
    if url_key in (None, ""):
        return None
    return urljoin(source_url, f"/{url_key}")


def _payload_meets_min_records(payload: dict[str, Any], min_records: int) -> bool:
    if min_records <= 0:
        return True
    records = [record for record in payload.get("records", []) if isinstance(record, dict)]
    return len(records) >= min_records


def _resolve_min_records(*, min_records: int | None) -> int:
    if min_records is None:
        return 0
    return max(0, min_records)


def _sleep_ms(delay_ms: int) -> None:
    import time

    time.sleep(max(0, delay_ms) / 1000)


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
