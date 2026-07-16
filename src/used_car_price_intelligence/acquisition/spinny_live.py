"""Bounded one-page Spinny public listing capture."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from used_car_price_intelligence.adapters import validate_spinny_extracted_payload
from used_car_price_intelligence.acquisition.spinny_incremental import normalize_spinny_listing_url
from used_car_price_intelligence.parsers import is_price_like_text, parse_spinny_variant_from_listing_url


DEFAULT_SPINNY_HYDERABAD_HUB_URL = (
    "https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/"
)
DEFAULT_SPINNY_HYDERABAD_HUB_LOCALITY = "Nexus Sujana Mall, Kukatpally"
SPINNY_CARD_SELECTOR = "[class*='CarListingCardV2__carListingCardV2Root']"

FUEL_LABELS = {"petrol", "diesel", "cng", "electric", "hybrid", "petrol + cng", "petrol/cng"}
TRANSMISSION_LABELS = {"automatic", "manual", "amt", "cvt", "dct"}


def capture_spinny_listing_payload(
    *,
    source_url: str = DEFAULT_SPINNY_HYDERABAD_HUB_URL,
    output_path: str | Path,
    captured_at: str | None = None,
    max_records: int = 20,
    min_records: int | None = None,
    max_pages: int = 1,
    locality_fallback: str = DEFAULT_SPINNY_HYDERABAD_HUB_LOCALITY,
    timeout_ms: int = 30_000,
    capture_attempts: int = 3,
    retry_delay_ms: int = 1_500,
    page_scroll_delay_ms: int = 2_500,
    headless: bool = True,
) -> dict[str, Any]:
    """Capture one public Spinny listing page into the extracted payload contract."""

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

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, args=["--disable-ipv6"])
        try:
            for attempt in range(max(1, capture_attempts)):
                page = browser.new_page(viewport={"width": 1440, "height": 1200})
                try:
                    try:
                        page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
                        page.wait_for_selector(SPINNY_CARD_SELECTOR, timeout=timeout_ms)
                        payload = _capture_until_contract_ready(
                            page=page,
                            source_url=source_url,
                            captured_at=captured_at,
                            max_records=max_records,
                            min_records=min_records,
                            max_pages=max_pages,
                            locality_fallback=locality_fallback,
                            timeout_ms=timeout_ms,
                            attempts=1,
                            retry_delay_ms=retry_delay_ms,
                            page_scroll_delay_ms=page_scroll_delay_ms,
                        )
                    except (PlaywrightError, PlaywrightTimeoutError) as exc:
                        payload = _failed_spinny_listing_payload(
                            source_url=source_url,
                            captured_at=captured_at,
                            max_records=max_records,
                            min_records=required_records,
                            max_pages=max_pages,
                            page_scroll_delay_ms=page_scroll_delay_ms,
                            error=str(exc),
                        )
                finally:
                    page.close()

                last_payload = payload
                if validate_spinny_extracted_payload(payload).ok and _payload_meets_min_records(
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

    payload = last_payload or _failed_spinny_listing_payload(
        source_url=source_url,
        captured_at=captured_at,
        max_records=max_records,
        min_records=required_records,
        max_pages=max_pages,
        page_scroll_delay_ms=page_scroll_delay_ms,
        error="no_capture_attempt_completed",
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def build_spinny_payload_from_card_texts(
    *,
    source_url: str,
    card_texts: list[str],
    captured_at: str,
    locality_fallback: str = DEFAULT_SPINNY_HYDERABAD_HUB_LOCALITY,
) -> dict[str, Any]:
    return build_spinny_payload_from_card_snapshots(
        source_url=source_url,
        card_snapshots=[{"text": card_text} for card_text in card_texts],
        captured_at=captured_at,
        locality_fallback=locality_fallback,
    )


def build_spinny_payload_from_card_snapshots(
    *,
    source_url: str,
    card_snapshots: list[dict[str, Any]],
    captured_at: str,
    locality_fallback: str = DEFAULT_SPINNY_HYDERABAD_HUB_LOCALITY,
    pagination: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records = []
    for snapshot in card_snapshots:
        card_text = str(snapshot.get("text") or "")
        raw = parse_spinny_card_text(card_text, locality_fallback=locality_fallback)
        if raw is not None:
            listing_url = snapshot.get("listing_url")
            if listing_url:
                raw["listing_url"] = str(listing_url)
                if not raw.get("variant") or is_price_like_text(raw.get("variant")):
                    url_variant = parse_spinny_variant_from_listing_url(listing_url)
                    if url_variant:
                        raw["variant"] = url_variant
            records.append({"raw": raw})

    payload = {
        "source": "spinny",
        "source_url": source_url,
        "captured_for": "live_public_search_capture",
        "capture_method": "playwright_dom_text",
        "captured_at": captured_at,
        "records": records,
    }
    if pagination:
        payload["pagination"] = pagination
    return payload


def _failed_spinny_listing_payload(
    *,
    source_url: str,
    captured_at: str,
    max_records: int,
    min_records: int,
    max_pages: int,
    page_scroll_delay_ms: int,
    error: str,
) -> dict[str, Any]:
    return build_spinny_payload_from_card_snapshots(
        source_url=source_url,
        card_snapshots=[],
        captured_at=captured_at,
        pagination={
            "pagination_type": "infinite_scroll_batches",
            "max_pages": max_pages,
            "attempted_pages": 0,
            "max_records": max_records,
            "min_records": min_records,
            "coverage_ok": False,
            "unique_cards_seen": 0,
            "returned_records": 0,
            "duplicate_cards_skipped": 0,
            "page_scroll_delay_ms": page_scroll_delay_ms,
            "stop_reason": "capture_attempt_failed",
            "capture_error": error,
        },
    )


def _capture_until_contract_ready(
    *,
    page: Any,
    source_url: str,
    captured_at: str,
    max_records: int,
    min_records: int | None,
    max_pages: int,
    locality_fallback: str,
    timeout_ms: int,
    attempts: int,
    retry_delay_ms: int,
    page_scroll_delay_ms: int,
) -> dict[str, Any]:
    last_payload: dict[str, Any] | None = None
    required_records = _resolve_min_records(max_records=max_records, min_records=min_records)
    snapshot_max_records = _snapshot_capture_limit(max_records=max_records, min_records=required_records)
    for attempt in range(max(1, attempts)):
        card_snapshots, pagination = _capture_card_snapshots_by_scroll_batch(
            page=page,
            max_records=snapshot_max_records,
            min_records=required_records,
            max_pages=max_pages,
            page_scroll_delay_ms=page_scroll_delay_ms,
        )
        last_payload = build_spinny_payload_from_card_snapshots(
            source_url=source_url,
            card_snapshots=card_snapshots,
            captured_at=captured_at,
            locality_fallback=locality_fallback,
            pagination=pagination,
        )
        _cap_listing_payload_records(
            last_payload,
            max_records=max_records,
            min_records=required_records,
            snapshot_max_records=snapshot_max_records,
        )
        if validate_spinny_extracted_payload(last_payload).ok and _payload_meets_min_records(
            last_payload,
            required_records,
        ):
            return last_payload
        if attempt < attempts - 1:
            page.wait_for_timeout(retry_delay_ms)
            page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector(SPINNY_CARD_SELECTOR, timeout=timeout_ms)

    return last_payload or build_spinny_payload_from_card_texts(
        source_url=source_url,
        card_texts=[],
        captured_at=captured_at,
        locality_fallback=locality_fallback,
    )


def summarize_spinny_listing_payload(listing_payload: dict[str, Any]) -> dict[str, Any]:
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
        "pagination_type": pagination.get("pagination_type", "single_page"),
        "max_pages": int(pagination.get("max_pages") or 1),
        "attempted_pages": int(pagination.get("attempted_pages") or 1),
        "max_records": int(pagination.get("max_records") or len(records)),
        "snapshot_max_records": int(
            pagination.get("snapshot_max_records") or pagination.get("max_records") or len(records)
        ),
        "min_records": int(pagination.get("min_records") or 0),
        "coverage_ok": len(records) >= int(pagination.get("min_records") or 0),
        "unique_cards_seen": int(pagination.get("unique_cards_seen") or len(records)),
        "raw_cards_returned": int(pagination.get("raw_cards_returned") or pagination.get("returned_records") or len(records)),
        "parsed_records_before_cap": int(pagination.get("parsed_records_before_cap") or len(records)),
        "returned_records": int(pagination.get("returned_records") or len(records)),
        "duplicate_cards_skipped": int(pagination.get("duplicate_cards_skipped") or 0),
        "page_scroll_delay_ms": int(pagination.get("page_scroll_delay_ms") or 0),
        "stop_reason": pagination.get("stop_reason", "record_cap_reached" if records else "unknown"),
    }


def parse_spinny_card_text(
    card_text: str,
    *,
    locality_fallback: str = DEFAULT_SPINNY_HYDERABAD_HUB_LOCALITY,
) -> dict[str, str] | None:
    lines = [line.strip() for line in card_text.splitlines() if line.strip()]
    if not lines:
        return None

    title_index = _first_index(lines, lambda line: re.match(r"^(19|20)\d{2}\s+\S+", line) is not None)
    if title_index is None:
        return None

    price_index = _first_index(lines[title_index + 1 :], _looks_like_price)
    if price_index is None:
        return None
    price_index += title_index + 1

    km_index = _first_index(lines[price_index + 1 :], _looks_like_km)
    if km_index is None:
        return None
    km_index += price_index + 1

    fuel_index = _first_index(lines[km_index + 1 :], _looks_like_fuel)
    if fuel_index is None:
        return None
    fuel_index += km_index + 1

    transmission_index = _first_index(lines[fuel_index + 1 :], _looks_like_transmission)
    if transmission_index is None:
        return None
    transmission_index += fuel_index + 1

    registration_index = _first_index(lines[transmission_index + 1 :], _looks_like_registration)
    if registration_index is None:
        return None
    registration_index += transmission_index + 1

    variant = _extract_variant(lines, price_index=price_index, km_index=km_index)
    emi = _first_value(lines[price_index + 1 : km_index], lambda line: line.lower().startswith("emi"))
    locality = _extract_locality(lines, registration_index, locality_fallback)

    return {
        "title": lines[title_index],
        "price": lines[price_index],
        "variant": variant or "",
        "emi": emi or "",
        "km": lines[km_index],
        "fuel": lines[fuel_index].lower(),
        "transmission": lines[transmission_index].lower(),
        "registration": lines[registration_index],
        "locality": locality,
    }


def _capture_card_snapshots_by_scroll_batch(
    *,
    page: Any,
    max_records: int,
    min_records: int,
    max_pages: int,
    page_scroll_delay_ms: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    max_pages = max(1, max_pages)
    max_records = max(0, max_records)
    min_records = max(0, min_records)
    unique_snapshots: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    page_metrics: list[dict[str, int | bool]] = []
    duplicate_cards_skipped = 0
    stop_reason = "page_cap_reached"

    for page_number in range(1, max_pages + 1):
        snapshots = _current_card_snapshots(page)
        new_cards = 0
        duplicate_cards = 0
        for snapshot in snapshots:
            key = _card_snapshot_key(snapshot)
            if key in seen_keys:
                duplicate_cards += 1
                continue
            seen_keys.add(key)
            unique_snapshots.append(snapshot)
            new_cards += 1
            if len(unique_snapshots) >= max_records:
                stop_reason = "record_cap_reached"
                break

        duplicate_cards_skipped += duplicate_cards
        page_metrics.append(
            {
                "page_number": page_number,
                "observed_cards": len(snapshots),
                "new_cards": new_cards,
                "unique_cards_total": len(unique_snapshots),
                "duplicate_cards": duplicate_cards,
            }
        )

        if len(unique_snapshots) >= max_records:
            break
        if page_number > 1 and new_cards == 0:
            stop_reason = "no_new_cards_after_scroll"
            break
        if page_number == max_pages:
            break

        page_metrics[-1].update(_scroll_to_next_card_batch(page, page_scroll_delay_ms=page_scroll_delay_ms))

    pagination = {
        "pagination_type": "infinite_scroll_batches",
        "max_pages": max_pages,
        "attempted_pages": len(page_metrics),
        "max_records": max_records,
        "min_records": min_records,
        "coverage_ok": len(unique_snapshots) >= min_records,
        "unique_cards_seen": len(unique_snapshots),
        "returned_records": min(len(unique_snapshots), max_records),
        "duplicate_cards_skipped": duplicate_cards_skipped,
        "page_scroll_delay_ms": page_scroll_delay_ms,
        "stop_reason": stop_reason,
        "pages": page_metrics,
    }
    return unique_snapshots[:max_records], pagination


def _current_card_snapshots(page: Any) -> list[dict[str, str]]:
    return page.locator(SPINNY_CARD_SELECTOR).evaluate_all(
        """
        (cards) => cards.map((card) => {
          const link = card.querySelector('a[href]');
          return {
            text: card.innerText,
            listing_url: link ? link.href : ''
          };
        })
        """
    )


def _scroll_to_next_card_batch(page: Any, *, page_scroll_delay_ms: int) -> dict[str, int | bool]:
    previous_count = page.locator(SPINNY_CARD_SELECTOR).count()
    wait_step_ms = 500
    waited_ms = 0
    max_wait_ms = max(page_scroll_delay_ms, 1_000)
    scroll_actions = max(3, min(10, max_wait_ms // wait_step_ms))

    for action_number in range(1, scroll_actions + 1):
        page.evaluate(
            """
            (selector) => {
              const cards = Array.from(document.querySelectorAll(selector));
              const lastCard = cards[cards.length - 1];
              if (lastCard) {
                lastCard.scrollIntoView({block: 'end'});
              }
              window.scrollBy(0, Math.max(window.innerHeight, 900));
              window.scrollTo(0, document.body.scrollHeight);
            }
            """,
            SPINNY_CARD_SELECTOR,
        )
        page.mouse.wheel(0, 1800)
        page.wait_for_timeout(wait_step_ms)
        waited_ms += wait_step_ms
        current_count = page.locator(SPINNY_CARD_SELECTOR).count()
        if current_count > previous_count:
            page.wait_for_timeout(wait_step_ms)
            return {
                "scroll_actions": action_number,
                "cards_before_scroll": previous_count,
                "cards_after_scroll": current_count,
                "loaded_new_cards": True,
            }

    while waited_ms < max_wait_ms:
        page.wait_for_timeout(wait_step_ms)
        waited_ms += wait_step_ms
        current_count = page.locator(SPINNY_CARD_SELECTOR).count()
        if current_count > previous_count:
            page.wait_for_timeout(wait_step_ms)
            return {
                "scroll_actions": scroll_actions,
                "cards_before_scroll": previous_count,
                "cards_after_scroll": current_count,
                "loaded_new_cards": True,
            }

    current_count = page.locator(SPINNY_CARD_SELECTOR).count()
    return {
        "scroll_actions": scroll_actions,
        "cards_before_scroll": previous_count,
        "cards_after_scroll": current_count,
        "loaded_new_cards": current_count > previous_count,
    }


def _card_snapshot_key(snapshot: dict[str, Any]) -> str:
    listing_url = str(snapshot.get("listing_url") or "").strip()
    if listing_url:
        return listing_url.split("?")[0].rstrip("/")
    return str(snapshot.get("text") or "").strip()


def _resolve_min_records(*, max_records: int, min_records: int | None) -> int:
    if min_records is None:
        return 0
    return max(0, min_records)


def _snapshot_capture_limit(*, max_records: int, min_records: int) -> int:
    """Capture extra DOM cards so parser losses do not reduce clean rows."""

    max_records = max(0, max_records)
    min_records = max(0, min_records)
    if max_records == 0:
        return 0
    if min_records <= 0 or min_records < max_records:
        return max_records
    headroom = min(25, max(5, min_records // 5))
    return max_records + headroom


def _cap_listing_payload_records(
    payload: dict[str, Any],
    *,
    max_records: int,
    min_records: int,
    snapshot_max_records: int,
) -> None:
    records = [record for record in payload.get("records", []) if isinstance(record, dict)]
    parsed_records_before_cap = len(records)
    capped_records = records[: max(0, max_records)]
    payload["records"] = capped_records

    pagination = payload.get("pagination")
    if not isinstance(pagination, dict):
        return

    raw_cards_returned = int(pagination.get("returned_records") or len(records))
    pagination.update(
        {
            "max_records": max(0, max_records),
            "snapshot_max_records": max(0, snapshot_max_records),
            "raw_cards_returned": raw_cards_returned,
            "parsed_records_before_cap": parsed_records_before_cap,
            "returned_records": len(capped_records),
            "coverage_ok": len(capped_records) >= max(0, min_records),
        }
    )


def _payload_meets_min_records(payload: dict[str, Any], min_records: int) -> bool:
    if min_records <= 0:
        return True
    records = [record for record in payload.get("records", []) if isinstance(record, dict)]
    return len(records) >= min_records


def capture_spinny_detail_payload(
    *,
    listing_urls: list[str],
    output_path: str | Path,
    captured_at: str | None = None,
    max_records: int = 5,
    timeout_ms: int = 30_000,
    delay_ms: int = 1_000,
    attempts: int = 2,
    headless: bool = True,
) -> dict[str, Any]:
    """Capture visible detail-page fields for a bounded set of public listing URLs."""

    try:
        from playwright.sync_api import TimeoutError, sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for live detail capture. Install with "
            "`python -m pip install -e .[acquisition]` and then "
            "`python -m playwright install chromium`."
        ) from exc

    captured_at = captured_at or _utc_now()
    valid_urls = [url for url in listing_urls if _is_spinny_listing_url(url)]
    bounded_urls = valid_urls[: max(0, max_records)]
    records: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1600})
            for listing_url in bounded_urls:
                records.append(
                    _capture_spinny_detail_record(
                        page=page,
                        listing_url=listing_url,
                        timeout_ms=timeout_ms,
                        delay_ms=delay_ms,
                        attempts=attempts,
                        timeout_error_type=TimeoutError,
                    )
                )
        finally:
            browser.close()

    payload = {
        "source": "spinny",
        "captured_for": "live_public_detail_enrichment",
        "capture_method": "playwright_visible_detail_text",
        "captured_at": captured_at,
        "policy": {
            "requested_urls": len(listing_urls),
            "valid_urls": len(valid_urls),
            "max_records": max_records,
            "attempted_records": len(bounded_urls),
            "skipped_invalid_urls": len(listing_urls) - len(valid_urls),
            "skipped_over_cap": max(0, len(valid_urls) - max(0, max_records)),
            "attempts_per_record": max(1, attempts),
            "timeout_ms": timeout_ms,
            "delay_ms": delay_ms,
        },
        "records": records,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def summarize_spinny_detail_payload(detail_payload: dict[str, Any]) -> dict[str, Any]:
    records = [record for record in detail_payload.get("records", []) if isinstance(record, dict)]
    policy = dict(detail_payload.get("policy") or {})
    records_total = len(records)
    successful_records = sum(1 for record in records if record.get("capture_status") == "ok")
    failed_records = records_total - successful_records
    timeout_count = sum(1 for record in records if record.get("failure_reason") == "timeout")
    empty_raw_count = sum(1 for record in records if not record.get("raw"))
    ownership_records = sum(
        1
        for record in records
        if isinstance(record.get("raw"), dict) and bool(record["raw"].get("ownership"))
    )
    attempts_total = sum(int(record.get("attempts") or 0) for record in records)
    retries_used = sum(max(0, int(record.get("attempts") or 0) - 1) for record in records)

    return {
        "ok": records_total > 0 and failed_records == 0,
        "requested_records": int(policy.get("max_records") or records_total),
        "attempted_records": int(policy.get("attempted_records") or records_total),
        "records_total": records_total,
        "successful_records": successful_records,
        "failed_records": failed_records,
        "timeout_count": timeout_count,
        "empty_raw_count": empty_raw_count,
        "ownership_records": ownership_records,
        "attempts_total": attempts_total,
        "retries_used": retries_used,
        "attempts_per_record": int(policy.get("attempts_per_record") or 1),
        "skipped_invalid_urls": int(policy.get("skipped_invalid_urls") or 0),
        "skipped_over_cap": int(policy.get("skipped_over_cap") or 0),
        "timeout_ms": int(policy.get("timeout_ms") or 0),
        "delay_ms": int(policy.get("delay_ms") or 0),
    }


def parse_spinny_detail_text(detail_text: str) -> dict[str, Any]:
    lines = [line.strip() for line in detail_text.splitlines() if line.strip()]
    values = {
        "make_year": _value_after_label(lines, "Make Year"),
        "registration_year": _value_after_label(lines, "Registration Year"),
        "fuel": _value_after_label(lines, "Fuel Type"),
        "km": _value_after_label(lines, "Km driven"),
        "transmission": _value_after_label(lines, "Transmission"),
        "ownership": _value_after_label(lines, "No. of Owner"),
        "insurance_validity": _value_after_label(lines, "Insurance Validity"),
        "insurance_type": _value_after_label(lines, "Insurance Type"),
        "rto": _value_after_label(lines, "RTO"),
        "detail_locality": _value_after_label(lines, "Car Location"),
    }
    quality_index = _line_index(lines, "Quality report")
    if quality_index is not None:
        values["inspection_status"] = "quality_report_available"
        values["inspection_summary"] = _first_matching_line(
            lines[quality_index + 1 : quality_index + 6],
            r"\bparts evaluated\b",
        )
        values["quality_scores"] = _extract_quality_scores(lines[quality_index:])

    service_due = _first_matching_line(lines, r"^Next service due\b")
    if service_due:
        values["service_due_text"] = service_due

    warranty_label = _extract_warranty_label(lines)
    if warranty_label:
        values["warranty_label"] = warranty_label

    return_policy_label = _extract_return_policy_label(lines)
    if return_policy_label:
        values["return_policy_label"] = return_policy_label

    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


def merge_spinny_detail_payload_into_listing_payload(
    *,
    listing_payload: dict[str, Any],
    detail_payload: dict[str, Any],
) -> dict[str, Any]:
    """Merge detail-page enrichment fields into listing-card raw records by URL."""

    detail_by_url = {
        normalize_spinny_listing_url(record.get("listing_url")): dict(record.get("raw") or {})
        for record in detail_payload.get("records", [])
        if isinstance(record, dict) and normalize_spinny_listing_url(record.get("listing_url"))
    }

    merged_payload = dict(listing_payload)
    merged_payload["captured_for"] = "live_public_search_with_detail_enrichment"
    merged_payload["detail_enrichment"] = {
        "source": "spinny",
        "captured_at": detail_payload.get("captured_at"),
        "records_total": len(detail_by_url),
        "summary": summarize_spinny_detail_payload(detail_payload),
    }
    merged_records = []
    for record in listing_payload.get("records", []):
        merged_record = dict(record)
        raw = dict(record.get("raw") or {})
        listing_url = normalize_spinny_listing_url(raw.get("listing_url"))
        detail_raw = detail_by_url.get(listing_url)
        if detail_raw:
            _merge_detail_fields(raw, detail_raw)
        merged_record["raw"] = raw
        merged_records.append(merged_record)
    merged_payload["records"] = merged_records
    return merged_payload


def _extract_variant(lines: list[str], *, price_index: int, km_index: int) -> str | None:
    for line in lines[price_index + 1 : km_index]:
        lowered = line.lower()
        if lowered.startswith("emi"):
            continue
        if _looks_like_price(line) or _looks_like_km(line):
            continue
        return line
    return None


def _extract_locality(lines: list[str], registration_index: int, fallback: str) -> str:
    for line in lines[registration_index + 1 : registration_index + 4]:
        if "," in line and not re.search(r"\b(reason|rating|benefit|quality|luxury)\b", line, re.I):
            return line
    return fallback


def _capture_spinny_detail_record(
    *,
    page: Any,
    listing_url: str,
    timeout_ms: int,
    delay_ms: int,
    attempts: int,
    timeout_error_type: type[Exception],
) -> dict[str, Any]:
    max_attempts = max(1, attempts)
    last_raw: dict[str, Any] = {}
    last_failure = "detail_fields_missing"
    for attempt in range(1, max_attempts + 1):
        try:
            page.goto(listing_url, wait_until="commit", timeout=timeout_ms)
            page.wait_for_timeout(delay_ms)
            detail_text = _wait_for_detail_text(page, timeout_ms=timeout_ms)
            last_raw = parse_spinny_detail_text(detail_text)
        except timeout_error_type as exc:
            last_failure = "timeout"
            if attempt == max_attempts:
                return {
                    "listing_url": listing_url,
                    "raw": {},
                    "capture_status": "failed",
                    "failure_reason": last_failure,
                    "capture_error": f"timeout: {exc}",
                    "attempts": attempt,
                }
            continue

        if _detail_raw_has_required_enrichment(last_raw):
            return {
                "listing_url": listing_url,
                "raw": last_raw,
                "capture_status": "ok",
                "attempts": attempt,
            }
        last_failure = "detail_fields_missing"

    return {
        "listing_url": listing_url,
        "raw": last_raw,
        "capture_status": "failed",
        "failure_reason": last_failure,
        "attempts": max_attempts,
    }


def _detail_raw_has_required_enrichment(raw: dict[str, Any]) -> bool:
    return bool(raw.get("ownership"))


def _value_after_label(lines: list[str], label: str) -> str | None:
    index = _line_index(lines, label)
    if index is None or index + 1 >= len(lines):
        return None
    return lines[index + 1]


def _line_index(lines: list[str], label: str) -> int | None:
    for index, line in enumerate(lines):
        if line.lower() == label.lower():
            return index
    return None


def _first_matching_line(lines: list[str], pattern: str) -> str | None:
    for line in lines:
        if re.search(pattern, line, flags=re.I):
            return line
    return None


def _extract_quality_scores(lines: list[str]) -> dict[str, dict[str, str]]:
    scores: dict[str, dict[str, str]] = {}
    score_labels = {
        "Core systems": "core_systems",
        "Supporting systems": "supporting_systems",
        "Interiors & AC": "interiors_ac",
        "Exteriors & lights": "exteriors_lights",
        "Wear & tear parts": "wear_tear_parts",
    }
    for index, line in enumerate(lines):
        key = score_labels.get(line)
        if key is None:
            continue
        window = lines[index + 1 : index + 5]
        score = _first_matching_line(window, r"^\d+(?:\.\d+)?$")
        grade = _first_matching_line(window, r"^(excellent|good|fair|poor)$")
        if score or grade:
            scores[key] = {}
            if score:
                scores[key]["score"] = score
            if grade:
                scores[key]["grade"] = grade
    return scores


def _extract_warranty_label(lines: list[str]) -> str | None:
    for index, line in enumerate(lines):
        if line.lower() == "warranty" and index > 0:
            return f"{lines[index - 1]} warranty"
        match = re.search(r"\b\d+\s*-\s*year warranty\b|\b\d+\s*year warranty\b", line, flags=re.I)
        if match:
            return match.group(0)
    return None


def _extract_return_policy_label(lines: list[str]) -> str | None:
    for index, line in enumerate(lines):
        if line.lower() == "money back" and index > 0:
            return f"{lines[index - 1]} money back"
        match = re.search(r"\b\d+\s*-\s*day money back\b|\b\d+\s*day money back\b", line, flags=re.I)
        if match:
            return match.group(0)
    return None


def _merge_detail_fields(raw: dict[str, Any], detail_raw: dict[str, Any]) -> None:
    direct_fields = [
        "ownership",
        "make_year",
        "registration_year",
        "insurance_validity",
        "insurance_type",
        "rto",
        "detail_locality",
        "inspection_status",
        "inspection_summary",
        "service_due_text",
        "warranty_label",
        "return_policy_label",
    ]
    for field_name in direct_fields:
        if detail_raw.get(field_name) and not raw.get(field_name):
            raw[field_name] = detail_raw[field_name]

    if detail_raw.get("quality_scores"):
        raw["quality_scores"] = detail_raw["quality_scores"]


def _is_spinny_listing_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.netloc.endswith("spinny.com") and parsed.path.startswith("/buy-used-cars/")


def _wait_for_detail_text(page: Any, *, timeout_ms: int) -> str:
    attempts = max(1, timeout_ms // 1_000)
    last_text = ""
    for _ in range(attempts):
        last_text = page.locator("body").inner_text(timeout=timeout_ms)
        if "Car Overview" in last_text and "No. of Owner" in last_text:
            return last_text
        page.wait_for_timeout(1_000)
    return last_text


def _first_index(lines: list[str], predicate: Callable[[str], bool]) -> int | None:
    for index, line in enumerate(lines):
        if predicate(line):
            return index
    return None


def _first_value(lines: list[str], predicate: Callable[[str], bool]) -> str | None:
    index = _first_index(lines, predicate)
    if index is None:
        return None
    return lines[index]


def _looks_like_price(line: str) -> bool:
    normalized = line.strip().replace("\u20b9", "Rs ")
    return (
        re.search(
            r"^(?:rs\.?\s*|inr\s*)?\d+(?:\.\d+)?\s*(?:lakh|lac|cr|crore)\b",
            normalized,
            flags=re.I,
        )
        is not None
    )


def _looks_like_km(line: str) -> bool:
    return re.search(r"\b\d+(?:\.\d+)?K?\s*km\b", line, flags=re.I) is not None


def _looks_like_fuel(line: str) -> bool:
    return line.strip().lower() in FUEL_LABELS


def _looks_like_transmission(line: str) -> bool:
    return line.strip().lower() in TRANSMISSION_LABELS


def _looks_like_registration(line: str) -> bool:
    return re.match(r"^(?:[A-Z]{2}\s*\d{1,2}[A-Z]{0,2}|\d{2}\s*BH\b)", line.strip(), flags=re.I) is not None


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
