"""Bounded Mahindra First Choice public listing capture."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from used_car_price_intelligence.adapters import validate_mahindra_first_choice_extracted_payload


DEFAULT_MFC_HYDERABAD_URL = "https://www.mahindrafirstchoice.com/used-cars/hyderabad"
MFC_LISTING_API_URL_FRAGMENT = "/api/product/used-car/get-pretty-filter-result-data"


def capture_mfc_listing_payload(
    *,
    source_url: str = DEFAULT_MFC_HYDERABAD_URL,
    output_path: str | Path,
    captured_at: str | None = None,
    max_records: int = 40,
    min_records: int | None = None,
    max_pages: int = 2,
    timeout_ms: int = 60_000,
    capture_attempts: int = 3,
    retry_delay_ms: int = 2_000,
    page_scroll_delay_ms: int = 2_500,
    headless: bool = True,
) -> dict[str, Any]:
    """Capture public Mahindra First Choice listing data into the extracted payload contract."""

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for live capture. Install with "
            "`python -m pip install -e .[acquisition]` and then "
            "`python -m playwright install chromium`."
        ) from exc

    captured_at = captured_at or _utc_now()
    required_records = _resolve_min_records(max_records=max_records, min_records=min_records)
    last_payload: dict[str, Any] | None = None
    capture_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, args=["--disable-ipv6"])
        try:
            for attempt in range(max(1, capture_attempts)):
                page = browser.new_page(viewport={"width": 1440, "height": 1400})
                try:
                    try:
                        payload = _capture_mfc_listing_payload_once(
                            page=page,
                            source_url=source_url,
                            captured_at=captured_at,
                            max_records=max_records,
                            max_pages=max_pages,
                            min_records=required_records,
                            timeout_ms=timeout_ms,
                            page_scroll_delay_ms=page_scroll_delay_ms,
                        )
                    except (PlaywrightError, PlaywrightTimeoutError) as exc:
                        capture_errors.append(f"attempt_{attempt + 1}: {exc}")
                        payload = build_mfc_payload_from_result_pages(
                            source_url=source_url,
                            result_pages=[],
                            captured_at=captured_at,
                            max_records=max_records,
                            pagination={
                                "pagination_type": "next_data_plus_xhr",
                                "max_pages": max_pages,
                                "attempted_pages": 0,
                                "max_records": max_records,
                                "min_records": required_records,
                                "coverage_ok": False,
                                "unique_cards_seen": 0,
                                "returned_records": 0,
                                "duplicate_cards_skipped": 0,
                                "page_scroll_delay_ms": page_scroll_delay_ms,
                                "stop_reason": "capture_attempt_failed",
                                "capture_error": str(exc),
                            },
                        )
                finally:
                    page.close()

                last_payload = payload
                if validate_mahindra_first_choice_extracted_payload(payload).ok and _payload_meets_min_records(
                    payload,
                    required_records,
                ):
                    break
                if attempt < capture_attempts - 1:
                    retry_page = browser.new_page()
                    try:
                        retry_page.wait_for_timeout(retry_delay_ms)
                    finally:
                        retry_page.close()
        finally:
            browser.close()

    payload = last_payload or build_mfc_payload_from_result_pages(
        source_url=source_url,
        result_pages=[],
        captured_at=captured_at,
        max_records=max_records,
        pagination={
            "pagination_type": "next_data_plus_xhr",
            "max_pages": max_pages,
            "attempted_pages": 0,
            "max_records": max_records,
            "min_records": required_records,
            "coverage_ok": False,
            "unique_cards_seen": 0,
            "returned_records": 0,
            "duplicate_cards_skipped": 0,
            "page_scroll_delay_ms": page_scroll_delay_ms,
            "stop_reason": "capture_not_attempted",
        },
    )
    if capture_errors:
        payload["capture_errors"] = capture_errors

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def build_mfc_payload_from_result_pages(
    *,
    source_url: str,
    result_pages: list[dict[str, Any]],
    captured_at: str,
    max_records: int,
    pagination: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records = []
    seen_ids: set[str] = set()
    duplicate_rows = 0
    for result_page in sorted(result_pages, key=lambda page: int(page.get("current_page") or 0)):
        for listing in result_page.get("data") or []:
            raw = mfc_structured_listing_to_raw(listing, source_url=source_url)
            source_id = str(raw.get("id_classified") or raw.get("stock_id") or "")
            if source_id and source_id in seen_ids:
                duplicate_rows += 1
                continue
            if source_id:
                seen_ids.add(source_id)
            records.append({"raw": raw})
            if len(records) >= max(0, max_records):
                break
        if len(records) >= max(0, max_records):
            break

    payload = {
        "source": "mahindra_first_choice",
        "source_url": source_url,
        "captured_for": "live_public_search_capture",
        "capture_method": "playwright_next_data_plus_xhr",
        "captured_at": captured_at,
        "records": records,
    }
    if pagination:
        payload["pagination"] = {**pagination, "duplicate_cards_skipped": duplicate_rows}
    return payload


def mfc_structured_listing_to_raw(
    listing: dict[str, Any],
    *,
    source_url: str = DEFAULT_MFC_HYDERABAD_URL,
) -> dict[str, Any]:
    title = _title_from_structured_listing(listing)
    variant = _first_present(listing.get("variant_chunk"), listing.get("variant_name"))
    km = _first_present(listing.get("odometer"), _km_text(listing.get("kilometers")))
    fuel = _first_present(listing.get("fuel"))
    transmission = _first_present(listing.get("transmission"))
    price = _first_present(listing.get("price_value"), listing.get("price"))

    return {
        "id_classified": listing.get("id_classified"),
        "stock_id": listing.get("stock_id"),
        "score": str(_first_present(listing.get("rating"), listing.get("score"), 0)),
        "title": title,
        "model_year": _safe_int(listing.get("year")),
        "brand": _first_present(listing.get("manufacturer_name")),
        "model": _first_present(listing.get("model_name")),
        "variant": variant,
        "variant_details": f"{variant} | {km} | {fuel} | {transmission}",
        "km": km,
        "fuel": fuel,
        "transmission": transmission,
        "price": price,
        "emi": _first_present(listing.get("emi_text"), listing.get("emi")),
        "locality": _first_present(listing.get("location"), listing.get("city")),
        "owner_text": _first_present(listing.get("owner")),
        "registration": _first_present(listing.get("registration_number")),
        "seller_type": _first_present(listing.get("seller")),
        "body_type": _first_present(listing.get("class")),
        "color": _first_present(listing.get("color")),
        "dealer_name": _first_present(listing.get("dealer_name")),
        "listing_posted_at": _first_present(listing.get("posted_on"), listing.get("datetime")),
        "listing_url": _absolute_listing_url(source_url, listing.get("url")),
        "is_certified": listing.get("is_certified"),
        "warranty_label": _first_present(listing.get("warranty_txt")),
        "photo_count": listing.get("photo_count"),
        "mileage": _first_present(listing.get("mileage")),
        "source_price_value": listing.get("price_value"),
        "source_city": _first_present(listing.get("city")),
        "source_state": _first_present(listing.get("state")),
    }


def summarize_mfc_listing_payload(listing_payload: dict[str, Any]) -> dict[str, Any]:
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
        "pagination_type": pagination.get("pagination_type", "next_data_plus_xhr"),
        "max_pages": int(pagination.get("max_pages") or 1),
        "attempted_pages": int(pagination.get("attempted_pages") or 1),
        "max_records": int(pagination.get("max_records") or len(records)),
        "min_records": int(pagination.get("min_records") or 0),
        "coverage_ok": len(records) >= int(pagination.get("min_records") or 0),
        "unique_cards_seen": int(pagination.get("unique_cards_seen") or len(records)),
        "returned_records": int(pagination.get("returned_records") or len(records)),
        "duplicate_cards_skipped": int(pagination.get("duplicate_cards_skipped") or 0),
        "page_scroll_delay_ms": int(pagination.get("page_scroll_delay_ms") or 0),
        "stop_reason": pagination.get("stop_reason", "record_cap_reached" if records else "unknown"),
        "source_total_items": int(pagination.get("source_total_items") or len(records)),
        "source_max_page": int(pagination.get("source_max_page") or 1),
    }


def _capture_mfc_listing_payload_once(
    *,
    page: Any,
    source_url: str,
    captured_at: str,
    max_records: int,
    max_pages: int,
    min_records: int,
    timeout_ms: int,
    page_scroll_delay_ms: int,
) -> dict[str, Any]:
    response_result_pages: dict[int, dict[str, Any]] = {}

    def collect_response(response: Any) -> None:
        if MFC_LISTING_API_URL_FRAGMENT not in response.url:
            return
        if response.status != 200:
            return
        try:
            result_data = _extract_result_data_from_api_payload(_loads_first_json_object(response.text()))
        except Exception:
            return
        current_page = int(result_data.get("current_page") or 0)
        if current_page:
            response_result_pages[current_page] = result_data

    page.on("response", collect_response)
    page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_selector(".usedCarCard", timeout=timeout_ms)
    page.wait_for_timeout(1_000)
    initial_result_data = _extract_initial_result_data(page)
    result_pages: dict[int, dict[str, Any]] = {
        int(initial_result_data.get("current_page") or 1): initial_result_data
    }
    source_max_page = int(initial_result_data.get("max_page") or 1)
    source_total_items = int(initial_result_data.get("total_items") or 0)

    stop_reason = "page_cap_reached"
    page_metrics = []
    for page_number in range(1, max(1, max_pages) + 1):
        result_pages.update(response_result_pages)
        records_seen = _unique_listing_count(list(result_pages.values()))
        page_metrics.append(
            {
                "page_number": page_number,
                "structured_pages_seen": len(result_pages),
                "unique_records_total": records_seen,
                "rendered_cards": page.locator(".usedCarCard").count(),
            }
        )
        if records_seen >= max_records:
            stop_reason = "record_cap_reached"
            break
        if records_seen >= min_records and page_number >= max_pages:
            stop_reason = "min_records_met_at_page_cap"
            break
        if len(result_pages) >= source_max_page:
            stop_reason = "source_max_page_reached"
            break
        if page_number == max_pages:
            break

        _scroll_to_next_mfc_batch(page, page_scroll_delay_ms=page_scroll_delay_ms)
        result_pages.update(response_result_pages)

    result_page_list = list(result_pages.values())
    unique_rows_seen = _unique_listing_count(result_page_list)
    returned_records = min(unique_rows_seen, max(0, max_records))
    pagination = {
        "pagination_type": "next_data_plus_xhr",
        "max_pages": max_pages,
        "attempted_pages": len(page_metrics),
        "max_records": max_records,
        "min_records": min_records,
        "coverage_ok": returned_records >= min_records,
        "unique_cards_seen": unique_rows_seen,
        "returned_records": returned_records,
        "duplicate_cards_skipped": 0,
        "page_scroll_delay_ms": page_scroll_delay_ms,
        "stop_reason": stop_reason,
        "source_total_items": source_total_items,
        "source_max_page": source_max_page,
        "pages": page_metrics,
    }
    return build_mfc_payload_from_result_pages(
        source_url=source_url,
        result_pages=result_page_list,
        captured_at=captured_at,
        max_records=max_records,
        pagination=pagination,
    )


def _extract_initial_result_data(page: Any) -> dict[str, Any]:
    next_data = json.loads(page.locator("script#__NEXT_DATA__").text_content(timeout=10_000))
    sections = next_data["props"]["pageProps"]["section"]
    for section in sections:
        for section_data in section.get("data") or []:
            for item in section_data.get("data") or []:
                if item.get("key") == "result" and item.get("result_data"):
                    return item["result_data"]
    raise ValueError("MFC initial listing result_data not found")


def _extract_result_data_from_api_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for item in payload.get("data") or []:
        if item.get("key") == "result" and item.get("result_data"):
            return item["result_data"]
    raise ValueError("MFC API result_data not found")


def _scroll_to_next_mfc_batch(page: Any, *, page_scroll_delay_ms: int) -> None:
    wait_step_ms = 500
    max_wait_ms = max(page_scroll_delay_ms, 1_000)
    scroll_actions = max(2, min(8, max_wait_ms // wait_step_ms))
    for _ in range(scroll_actions):
        page.evaluate("window.scrollBy(0, Math.max(window.innerHeight, 1800))")
        page.mouse.wheel(0, 2200)
        page.wait_for_timeout(wait_step_ms)
    remaining_wait = max(0, max_wait_ms - (scroll_actions * wait_step_ms))
    if remaining_wait:
        page.wait_for_timeout(remaining_wait)


def _loads_first_json_object(value: str) -> dict[str, Any]:
    start = value.find("{")
    if start < 0:
        raise ValueError("No JSON object found")
    decoder = json.JSONDecoder()
    payload, _ = decoder.raw_decode(value[start:])
    if not isinstance(payload, dict):
        raise ValueError("Decoded JSON payload is not an object")
    return payload


def _unique_listing_count(result_pages: list[dict[str, Any]]) -> int:
    seen_ids = set()
    for result_page in result_pages:
        for listing in result_page.get("data") or []:
            source_id = listing.get("id_classified") or listing.get("stock_id")
            if source_id is not None:
                seen_ids.add(str(source_id))
    return len(seen_ids)


def _resolve_min_records(*, max_records: int, min_records: int | None) -> int:
    if min_records is None:
        return 0
    return max(0, min_records)


def _payload_meets_min_records(payload: dict[str, Any], min_records: int) -> bool:
    if min_records <= 0:
        return True
    records = [record for record in payload.get("records", []) if isinstance(record, dict)]
    return len(records) >= min_records


def _title_from_structured_listing(listing: dict[str, Any]) -> str:
    return " ".join(
        str(part)
        for part in [
            listing.get("year"),
            listing.get("manufacturer_name"),
            listing.get("model_name"),
        ]
        if _first_present(part) is not None
    )


def _km_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return f"{value} km"


def _absolute_listing_url(source_url: str, listing_url: Any) -> str | None:
    if listing_url in (None, ""):
        return None
    return urljoin(source_url, str(listing_url))


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
