"""Incremental Spinny detail enrichment planning and cache reuse."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def build_spinny_incremental_detail_plan(
    *,
    listing_payload: dict[str, Any],
    existing_detail_payloads: list[dict[str, Any]] | None = None,
    max_new_records: int = 0,
) -> dict[str, Any]:
    listing_urls = spinny_listing_urls_from_payload(listing_payload)
    cache = spinny_detail_cache_index(existing_detail_payloads or [])
    pending_urls = [url for url in listing_urls if url not in cache]
    selected_new_urls = pending_urls[: max(0, max_new_records)]
    return {
        "source": "spinny",
        "listing_records": len([record for record in listing_payload.get("records", []) if isinstance(record, dict)]),
        "unique_listing_urls": len(listing_urls),
        "existing_detail_payloads": len(existing_detail_payloads or []),
        "cache_records": len(cache),
        "cache_hit_urls": [url for url in listing_urls if url in cache],
        "cache_hit_count": sum(1 for url in listing_urls if url in cache),
        "pending_urls": pending_urls,
        "pending_count": len(pending_urls),
        "max_new_records": max(0, max_new_records),
        "selected_new_urls": selected_new_urls,
        "selected_new_count": len(selected_new_urls),
        "skipped_over_new_cap": max(0, len(pending_urls) - len(selected_new_urls)),
        "detail_coverage_before_capture": _coverage_ratio(
            numerator=sum(1 for url in listing_urls if url in cache),
            denominator=len(listing_urls),
        ),
    }


def build_spinny_incremental_detail_payload(
    *,
    listing_payload: dict[str, Any],
    existing_detail_payloads: list[dict[str, Any]] | None = None,
    new_detail_payload: dict[str, Any] | None = None,
    captured_at: str | None = None,
    max_new_records: int = 0,
) -> dict[str, Any]:
    existing_detail_payloads = existing_detail_payloads or []
    plan = build_spinny_incremental_detail_plan(
        listing_payload=listing_payload,
        existing_detail_payloads=existing_detail_payloads,
        max_new_records=max_new_records,
    )
    cache = spinny_detail_cache_index(existing_detail_payloads)
    new_records = spinny_detail_cache_index([new_detail_payload] if new_detail_payload else [])

    records = []
    cache_reused = 0
    new_used = 0
    still_missing = []
    for url in spinny_listing_urls_from_payload(listing_payload):
        source_record = new_records.get(url) or cache.get(url)
        if source_record is None:
            still_missing.append(url)
            continue
        record = dict(source_record)
        record["listing_url"] = url
        if url in new_records:
            record["detail_record_source"] = "new_capture"
            new_used += 1
        else:
            record["detail_record_source"] = "cache"
            cache_reused += 1
        records.append(record)

    policy = {
        "requested_urls": plan["unique_listing_urls"],
        "valid_urls": plan["unique_listing_urls"],
        "max_records": len(records),
        "attempted_records": len(records),
        "max_new_records": max(0, max_new_records),
        "cache_hit_count": plan["cache_hit_count"],
        "cache_reused_records": cache_reused,
        "new_records_used": new_used,
        "missing_after_merge": len(still_missing),
        "skipped_over_new_cap": plan["skipped_over_new_cap"],
        "selected_new_count": plan["selected_new_count"],
        "selected_new_urls": plan["selected_new_urls"],
        "still_missing_urls": still_missing,
    }
    return {
        "source": "spinny",
        "captured_for": "incremental_public_detail_enrichment",
        "capture_method": "detail_cache_reuse_plus_optional_capture",
        "captured_at": captured_at or _utc_now(),
        "policy": policy,
        "records": records,
    }


def spinny_listing_urls_from_payload(listing_payload: dict[str, Any]) -> list[str]:
    urls = []
    for record in listing_payload.get("records") or []:
        if not isinstance(record, dict):
            continue
        raw = record.get("raw")
        if not isinstance(raw, dict):
            continue
        url = normalize_spinny_listing_url(raw.get("listing_url"))
        if url:
            urls.append(url)
    return list(dict.fromkeys(urls))


def spinny_detail_cache_index(detail_payloads: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    for payload in detail_payloads:
        if not isinstance(payload, dict):
            continue
        for record in payload.get("records") or []:
            if not isinstance(record, dict):
                continue
            url = normalize_spinny_listing_url(record.get("listing_url"))
            if not url:
                continue
            candidate = dict(record)
            candidate["listing_url"] = url
            existing = cache.get(url)
            cache[url] = _preferred_detail_record(existing, candidate)
    return cache


def normalize_spinny_listing_url(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        parts = urlsplit(text)
    except ValueError:
        return ""
    if not parts.netloc.endswith("spinny.com") or not parts.path.startswith("/buy-used-cars/"):
        return ""
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = "/" + "/".join(part for part in parts.path.split("/") if part)
    return urlunsplit((scheme, netloc, path, "", ""))


def load_spinny_detail_payloads(paths: list[str | Path] | None) -> list[dict[str, Any]]:
    payloads = []
    for path in paths or []:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected Spinny detail payload JSON object: {path}")
        payloads.append(payload)
    return payloads


def _preferred_detail_record(existing: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return candidate
    candidate_ok = candidate.get("capture_status") == "ok"
    existing_ok = existing.get("capture_status") == "ok"
    if candidate_ok and not existing_ok:
        return candidate
    if existing_ok and not candidate_ok:
        return existing
    candidate_has_raw = bool(candidate.get("raw"))
    existing_has_raw = bool(existing.get("raw"))
    if candidate_has_raw and not existing_has_raw:
        return candidate
    return existing


def _coverage_ratio(*, numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
