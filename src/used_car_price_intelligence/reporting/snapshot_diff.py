"""Snapshot diff reports for trusted listing lifecycle indexes."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


SNAPSHOT_DIFF_POLICY_VERSION = "snapshot_diff_policy_v0.1"


def build_snapshot_diff(
    *,
    snapshot_id: str,
    current_lifecycle_path: str | Path,
    previous_lifecycle_path: str | Path | None = None,
    snapshot_date: str = "",
    generated_at: str | None = None,
) -> dict[str, Any]:
    current_path = Path(current_lifecycle_path)
    current_lifecycle = _load_json(current_path)
    previous_path = Path(previous_lifecycle_path) if previous_lifecycle_path else None
    previous_lifecycle = _load_json(previous_path) if previous_path else None

    current_entities = _entities_by_key(current_lifecycle)
    previous_entities = _entities_by_key(previous_lifecycle) if previous_lifecycle else {}

    current_keys = set(current_entities)
    previous_keys = set(previous_entities)
    added_keys = _sort_keys(current_keys - previous_keys, current_entities)
    removed_keys = _sort_keys(previous_keys - current_keys, previous_entities)
    still_active_keys = _sort_keys(current_keys & previous_keys, current_entities)

    added_listings = [_listing_snapshot(current_entities[key]) for key in added_keys]
    removed_listings = [_listing_snapshot(previous_entities[key]) for key in removed_keys]
    still_active_listings = [
        _still_active_snapshot(previous_entities[key], current_entities[key]) for key in still_active_keys
    ]

    price_changes = []
    km_changes = []
    changed_listings_by_key: dict[str, dict[str, Any]] = {}
    for listing_key in still_active_keys:
        previous_entity = previous_entities[listing_key]
        current_entity = current_entities[listing_key]
        previous_observation = _latest_observation(previous_entity)
        current_observation = _latest_observation(current_entity)

        previous_price = _int_or_none(previous_observation.get("listed_price_inr"))
        current_price = _int_or_none(current_observation.get("listed_price_inr"))
        if previous_price is not None and current_price is not None and previous_price != current_price:
            change = _change_snapshot(previous_entity, current_entity)
            price_changes.append(change)
            changed_listings_by_key[listing_key] = change

        previous_km = _int_or_none(previous_observation.get("km_driven"))
        current_km = _int_or_none(current_observation.get("km_driven"))
        if previous_km is not None and current_km is not None and previous_km != current_km:
            change = changed_listings_by_key.get(listing_key) or _change_snapshot(previous_entity, current_entity)
            km_changes.append(change)
            changed_listings_by_key[listing_key] = change

    price_changes.sort(key=lambda item: (-abs(int(item.get("price_delta_inr") or 0)), item["listing_key"]))
    km_changes.sort(key=lambda item: (-abs(int(item.get("km_delta") or 0)), item["listing_key"]))
    changed_listings = sorted(
        changed_listings_by_key.values(),
        key=lambda item: (item.get("source", ""), item.get("city", ""), item["listing_key"]),
    )

    return {
        "snapshot_id": snapshot_id,
        "snapshot_date": snapshot_date,
        "generated_at": generated_at or _utc_now(),
        "policy": {
            "version": SNAPSHOT_DIFF_POLICY_VERSION,
            "baseline_mode": previous_lifecycle is None,
            "identity_key": "Lifecycle listing_key. No cross-source or fuzzy vehicle merges are applied here.",
            "added_definition": "A listing_key present in current lifecycle and absent from previous lifecycle.",
            "removed_definition": (
                "A listing_key present in previous lifecycle and absent from current lifecycle. This means not observed "
                "in the selected current collection, not automatically sold, unless source-city coverage is equivalent."
            ),
            "still_active_definition": "A listing_key present in both previous and current lifecycle indexes.",
            "change_detection": (
                "Price and km changes compare numeric values from latest_observation for still-active listing keys only."
            ),
        },
        "inputs": {
            "previous_lifecycle_path": str(previous_path) if previous_path else "",
            "current_lifecycle_path": str(current_path),
            "previous_lifecycle_id": str(previous_lifecycle.get("lifecycle_id") or "") if previous_lifecycle else "",
            "current_lifecycle_id": str(current_lifecycle.get("lifecycle_id") or ""),
            "previous_collection_id": str(previous_lifecycle.get("collection_id") or "") if previous_lifecycle else "",
            "current_collection_id": str(current_lifecycle.get("collection_id") or ""),
        },
        "totals": {
            "previous_unique_listing_keys": len(previous_keys),
            "current_unique_listing_keys": len(current_keys),
            "added_count": len(added_keys),
            "removed_count": len(removed_keys),
            "still_active_count": len(still_active_keys),
            "price_change_count": len(price_changes),
            "km_change_count": len(km_changes),
            "changed_listing_count": len(changed_listings),
            "by_source": _by_source_totals(
                previous_entities=previous_entities,
                current_entities=current_entities,
                added_keys=added_keys,
                removed_keys=removed_keys,
                still_active_keys=still_active_keys,
                price_changes=price_changes,
                km_changes=km_changes,
            ),
        },
        "added_listings": added_listings,
        "removed_listings": removed_listings,
        "still_active_listings": still_active_listings,
        "price_changes": price_changes,
        "km_changes": km_changes,
        "changed_listings": changed_listings,
    }


def render_snapshot_diff_markdown(diff: dict[str, Any], *, row_limit: int = 25) -> str:
    totals = dict(diff.get("totals") or {})
    inputs = dict(diff.get("inputs") or {})
    policy = dict(diff.get("policy") or {})
    baseline_mode = bool(policy.get("baseline_mode"))
    lines = [
        "# Snapshot Diff Report",
        "",
        f"Snapshot id: `{diff.get('snapshot_id', '')}`",
        f"Snapshot date: `{diff.get('snapshot_date', '')}`",
        f"Generated at: `{diff.get('generated_at', '')}`",
        f"Previous lifecycle id: `{inputs.get('previous_lifecycle_id', '')}`",
        f"Current lifecycle id: `{inputs.get('current_lifecycle_id', '')}`",
        "",
        "## Totals",
        "",
        f"- Baseline mode: {'yes' if baseline_mode else 'no'}",
        f"- Previous unique listing keys: {totals.get('previous_unique_listing_keys', 0)}",
        f"- Current unique listing keys: {totals.get('current_unique_listing_keys', 0)}",
        f"- Added listings: {totals.get('added_count', 0)}",
        f"- Removed listings: {totals.get('removed_count', 0)}",
        f"- Still-active listings: {totals.get('still_active_count', 0)}",
        f"- Price changes: {totals.get('price_change_count', 0)}",
        f"- Km changes: {totals.get('km_change_count', 0)}",
        "",
        "## Policy Notes",
        "",
        f"- Identity key: {policy.get('identity_key', '')}",
        f"- Removed definition: {policy.get('removed_definition', '')}",
        f"- Change detection: {policy.get('change_detection', '')}",
        "",
    ]
    if baseline_mode:
        lines.extend(
            [
                "This is a baseline snapshot. All current listings are marked as added because no previous lifecycle "
                "index was provided.",
                "",
            ]
        )

    lines.extend(
        [
            "## By Source",
            "",
            "| Source | Previous | Current | Added | Removed | Still Active | Price Changes | Km Changes |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for source, source_totals in sorted(dict(totals.get("by_source") or {}).items()):
        lines.append(
            "| {source} | {previous} | {current} | {added} | {removed} | {still_active} | "
            "{price_changes} | {km_changes} |".format(
                source=source,
                previous=source_totals.get("previous", 0),
                current=source_totals.get("current", 0),
                added=source_totals.get("added", 0),
                removed=source_totals.get("removed", 0),
                still_active=source_totals.get("still_active", 0),
                price_changes=source_totals.get("price_changes", 0),
                km_changes=source_totals.get("km_changes", 0),
            )
        )

    _append_listing_section(lines, "Added Listings", diff.get("added_listings") or [], row_limit=row_limit)
    _append_listing_section(lines, "Removed Listings", diff.get("removed_listings") or [], row_limit=row_limit)
    _append_change_section(lines, "Price Changes", diff.get("price_changes") or [], row_limit=row_limit)
    _append_change_section(lines, "Km Changes", diff.get("km_changes") or [], row_limit=row_limit)
    lines.append("")
    return "\n".join(lines)


def write_snapshot_diff_json(path: str | Path, diff: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(diff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def write_snapshot_diff_markdown(path: str | Path, diff: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_snapshot_diff_markdown(diff), encoding="utf-8")
    return output_path


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected lifecycle JSON object at {path}")
    return data


def _entities_by_key(lifecycle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entities = {}
    for entity in lifecycle.get("listing_entities") or []:
        if not isinstance(entity, dict):
            continue
        listing_key = str(entity.get("listing_key") or "")
        if listing_key:
            entities[listing_key] = entity
    return entities


def _sort_keys(keys: set[str], entities: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(keys, key=lambda key: _entity_sort_key(entities[key]))


def _entity_sort_key(entity: dict[str, Any]) -> tuple[str, str, str, str, str]:
    observation = _latest_observation(entity)
    return (
        _source(entity),
        str(observation.get("city") or ""),
        str(observation.get("brand") or ""),
        str(observation.get("model") or ""),
        str(entity.get("listing_key") or ""),
    )


def _latest_observation(entity: dict[str, Any]) -> dict[str, Any]:
    observation = entity.get("latest_observation")
    return observation if isinstance(observation, dict) else {}


def _listing_snapshot(entity: dict[str, Any]) -> dict[str, Any]:
    observation = _latest_observation(entity)
    return {
        "listing_key": str(entity.get("listing_key") or ""),
        "source": _source(entity),
        "city": _string(observation.get("city")),
        "state": _string(observation.get("state")),
        "brand": _string(observation.get("brand")),
        "model": _string(observation.get("model")),
        "variant": _string(observation.get("variant")),
        "model_year": observation.get("model_year"),
        "fuel_type": _string(observation.get("fuel_type")),
        "transmission": _string(observation.get("transmission")),
        "km_driven": observation.get("km_driven"),
        "ownership": observation.get("ownership"),
        "registration_code": _string(observation.get("registration_code")),
        "listed_price_inr": observation.get("listed_price_inr"),
        "listing_url": _string(observation.get("listing_url")),
        "source_listing_id": _string(observation.get("source_listing_id")),
        "is_available": observation.get("is_available"),
        "observation_count": entity.get("observation_count", 0),
        "first_seen_at": _string(entity.get("first_seen_at")),
        "last_seen_at": _string(entity.get("last_seen_at")),
        "capture_dates": list(entity.get("capture_dates") or []),
        "run_ids": list(entity.get("run_ids") or []),
    }


def _still_active_snapshot(previous_entity: dict[str, Any], current_entity: dict[str, Any]) -> dict[str, Any]:
    previous = _listing_snapshot(previous_entity)
    current = _listing_snapshot(current_entity)
    return {
        "listing_key": current["listing_key"],
        "source": current["source"],
        "city": current["city"],
        "brand": current["brand"],
        "model": current["model"],
        "variant": current["variant"],
        "model_year": current["model_year"],
        "listing_url": current["listing_url"],
        "previous_price_inr": previous["listed_price_inr"],
        "current_price_inr": current["listed_price_inr"],
        "previous_km_driven": previous["km_driven"],
        "current_km_driven": current["km_driven"],
        "previous_last_seen_at": previous["last_seen_at"],
        "current_last_seen_at": current["last_seen_at"],
        "previous_run_ids": previous["run_ids"],
        "current_run_ids": current["run_ids"],
    }


def _change_snapshot(previous_entity: dict[str, Any], current_entity: dict[str, Any]) -> dict[str, Any]:
    previous = _listing_snapshot(previous_entity)
    current = _listing_snapshot(current_entity)
    previous_price = _int_or_none(previous["listed_price_inr"])
    current_price = _int_or_none(current["listed_price_inr"])
    previous_km = _int_or_none(previous["km_driven"])
    current_km = _int_or_none(current["km_driven"])
    price_delta = current_price - previous_price if previous_price is not None and current_price is not None else None
    km_delta = current_km - previous_km if previous_km is not None and current_km is not None else None
    return {
        "listing_key": current["listing_key"],
        "source": current["source"],
        "city": current["city"],
        "brand": current["brand"],
        "model": current["model"],
        "variant": current["variant"],
        "model_year": current["model_year"],
        "listing_url": current["listing_url"],
        "previous_price_inr": previous_price,
        "current_price_inr": current_price,
        "price_delta_inr": price_delta,
        "price_delta_pct": _pct_delta(previous_price, current_price),
        "previous_km_driven": previous_km,
        "current_km_driven": current_km,
        "km_delta": km_delta,
        "previous_last_seen_at": previous["last_seen_at"],
        "current_last_seen_at": current["last_seen_at"],
        "previous_run_ids": previous["run_ids"],
        "current_run_ids": current["run_ids"],
    }


def _by_source_totals(
    *,
    previous_entities: dict[str, dict[str, Any]],
    current_entities: dict[str, dict[str, Any]],
    added_keys: list[str],
    removed_keys: list[str],
    still_active_keys: list[str],
    price_changes: list[dict[str, Any]],
    km_changes: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "previous": 0,
            "current": 0,
            "added": 0,
            "removed": 0,
            "still_active": 0,
            "price_changes": 0,
            "km_changes": 0,
        }
    )
    for entity in previous_entities.values():
        totals[_source(entity)]["previous"] += 1
    for entity in current_entities.values():
        totals[_source(entity)]["current"] += 1
    for listing_key in added_keys:
        totals[_source(current_entities[listing_key])]["added"] += 1
    for listing_key in removed_keys:
        totals[_source(previous_entities[listing_key])]["removed"] += 1
    for listing_key in still_active_keys:
        totals[_source(current_entities[listing_key])]["still_active"] += 1
    for change in price_changes:
        totals[str(change.get("source") or "")]["price_changes"] += 1
    for change in km_changes:
        totals[str(change.get("source") or "")]["km_changes"] += 1
    return {source: dict(source_totals) for source, source_totals in sorted(totals.items())}


def _append_listing_section(
    lines: list[str],
    title: str,
    listings: list[dict[str, Any]],
    *,
    row_limit: int,
) -> None:
    lines.extend(["", f"## {title}", ""])
    if not listings:
        lines.append("No listings in this category.")
        return
    lines.extend(
        [
            f"Showing first {min(row_limit, len(listings))} of {len(listings)} listings.",
            "",
            "| Listing Key | Source | City | Vehicle | Price | Km | Last Seen | URL |",
            "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for listing in listings[:row_limit]:
        lines.append(
            "| `{listing_key}` | {source} | {city} | {vehicle} | {price} | {km} | {last_seen} | {url} |".format(
                listing_key=listing.get("listing_key", ""),
                source=listing.get("source", ""),
                city=listing.get("city", ""),
                vehicle=_vehicle_label(listing),
                price=_display_number(listing.get("listed_price_inr")),
                km=_display_number(listing.get("km_driven")),
                last_seen=listing.get("last_seen_at", ""),
                url=_markdown_url(listing.get("listing_url")),
            )
        )


def _append_change_section(
    lines: list[str],
    title: str,
    changes: list[dict[str, Any]],
    *,
    row_limit: int,
) -> None:
    lines.extend(["", f"## {title}", ""])
    if not changes:
        lines.append("No numeric changes were detected.")
        return
    lines.extend(
        [
            f"Showing first {min(row_limit, len(changes))} of {len(changes)} changes.",
            "",
            "| Listing Key | Source | City | Vehicle | Previous Price | Current Price | Price Delta | Previous Km | Current Km | Km Delta |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for change in changes[:row_limit]:
        lines.append(
            "| `{listing_key}` | {source} | {city} | {vehicle} | {previous_price} | {current_price} | "
            "{price_delta} | {previous_km} | {current_km} | {km_delta} |".format(
                listing_key=change.get("listing_key", ""),
                source=change.get("source", ""),
                city=change.get("city", ""),
                vehicle=_vehicle_label(change),
                previous_price=_display_number(change.get("previous_price_inr")),
                current_price=_display_number(change.get("current_price_inr")),
                price_delta=_display_number(change.get("price_delta_inr")),
                previous_km=_display_number(change.get("previous_km_driven")),
                current_km=_display_number(change.get("current_km_driven")),
                km_delta=_display_number(change.get("km_delta")),
            )
        )


def _vehicle_label(row: dict[str, Any]) -> str:
    parts = [
        _string(row.get("model_year")),
        _string(row.get("brand")),
        _string(row.get("model")),
        _string(row.get("variant")),
    ]
    return " ".join(part for part in parts if part)


def _markdown_url(url: Any) -> str:
    text = _string(url)
    return f"[open]({text})" if text else ""


def _source(entity: dict[str, Any]) -> str:
    observation = _latest_observation(entity)
    return _string(entity.get("source") or observation.get("source"))


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _pct_delta(previous: int | None, current: int | None) -> float | None:
    if previous in (None, 0) or current is None:
        return None
    return round(((current - previous) / previous) * 100, 2)


def _display_number(value: Any) -> str:
    parsed = _int_or_none(value)
    return f"{parsed:,}" if parsed is not None else ""


def _string(value: Any) -> str:
    return "" if value is None else str(value)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
