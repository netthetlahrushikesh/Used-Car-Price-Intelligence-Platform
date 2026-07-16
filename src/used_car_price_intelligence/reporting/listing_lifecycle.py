"""Listing identity, dedupe, and lifecycle reports."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit


LIFECYCLE_POLICY_VERSION = "listing_lifecycle_policy_v0.1"
KM_BUCKET_SIZE = 5_000
PRICE_BUCKET_SIZE = 50_000


def build_listing_lifecycle_index(
    *,
    lifecycle_id: str,
    collection_ledger_path: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ledger_path = Path(collection_ledger_path)
    ledger = _load_json(ledger_path)
    rows = [
        row
        for row in ledger.get("rows", [])
        if isinstance(row, dict) and str(row.get("status") or "") == "pass"
    ]

    observations: list[dict[str, Any]] = []
    run_inputs: list[dict[str, Any]] = []
    for row in rows:
        manifest_path = _resolve_path(row.get("manifest_path"), bases=[ledger_path.parent])
        if manifest_path is None:
            continue
        manifest = _load_json(manifest_path)
        silver_path = _silver_path_from_manifest(manifest, manifest_path=manifest_path)
        silver_records = _load_json(silver_path)
        if not isinstance(silver_records, list):
            raise ValueError(f"Expected silver records list at {silver_path}")

        run_inputs.append(
            {
                "source": str(manifest.get("source") or row.get("source") or ""),
                "city": str(manifest.get("city") or row.get("city") or ""),
                "capture_date": str(manifest.get("capture_date") or row.get("capture_date") or ""),
                "run_id": str(manifest.get("run_id") or row.get("run_id") or ""),
                "manifest_path": str(manifest_path),
                "silver_path": str(silver_path),
                "records_total": len(silver_records),
            }
        )
        for index, record in enumerate(silver_records):
            if isinstance(record, dict):
                observations.append(
                    _observation_from_record(
                        record,
                        record_index=index,
                        manifest=manifest,
                        silver_path=silver_path,
                    )
                )

    listing_entities = _build_listing_entities(observations)
    possible_vehicle_duplicate_groups = _possible_vehicle_duplicate_groups(observations)
    by_source = _totals_by_source(observations)
    reobserved_listing_groups = [
        _entity_group_summary(entity)
        for entity in listing_entities
        if int(entity.get("observation_count") or 0) > 1
    ]

    return {
        "lifecycle_id": lifecycle_id,
        "collection_id": str(ledger.get("collection_id") or ""),
        "generated_at": generated_at or _utc_now(),
        "policy": {
            "version": LIFECYCLE_POLICY_VERSION,
            "listing_key": "source plus normalized listing URL, falling back to source listing id, raw hash, then core fields",
            "vehicle_fingerprint": (
                "conservative possible-duplicate key using city, brand, model, variant, year, fuel, "
                "transmission, ownership, registration code, km bucket, and price bucket"
            ),
            "km_bucket_size": KM_BUCKET_SIZE,
            "price_bucket_size": PRICE_BUCKET_SIZE,
            "note": "Vehicle fingerprints are review signals, not automatic merge keys.",
        },
        "run_inputs": sorted(run_inputs, key=lambda item: (item["source"], item["city"], item["run_id"])),
        "totals": {
            "records_total": len(observations),
            "source_runs": len(run_inputs),
            "unique_listing_keys": len(listing_entities),
            "reobserved_listing_groups": len(reobserved_listing_groups),
            "reobserved_observations": sum(
                int(group.get("observation_count") or 0) for group in reobserved_listing_groups
            ),
            "vehicle_fingerprint_groups": len(
                {observation["vehicle_fingerprint"] for observation in observations if observation["vehicle_fingerprint"]}
            ),
            "possible_vehicle_duplicate_groups": len(possible_vehicle_duplicate_groups),
            "possible_vehicle_duplicate_observations": sum(
                int(group.get("observation_count") or 0) for group in possible_vehicle_duplicate_groups
            ),
            "by_source": by_source,
        },
        "listing_entities": listing_entities,
        "reobserved_listing_groups": reobserved_listing_groups,
        "possible_vehicle_duplicate_groups": possible_vehicle_duplicate_groups,
    }


def render_listing_lifecycle_markdown(index: dict[str, Any], *, duplicate_group_limit: int = 25) -> str:
    totals = dict(index.get("totals") or {})
    policy = dict(index.get("policy") or {})
    lines = [
        "# Listing Lifecycle Index",
        "",
        f"Lifecycle id: `{index.get('lifecycle_id', '')}`",
        f"Collection id: `{index.get('collection_id', '')}`",
        f"Generated at: `{index.get('generated_at', '')}`",
        "",
        "## Totals",
        "",
        f"- Records processed: {totals.get('records_total', 0)}",
        f"- Source runs: {totals.get('source_runs', 0)}",
        f"- Unique listing keys: {totals.get('unique_listing_keys', 0)}",
        f"- Reobserved listing groups: {totals.get('reobserved_listing_groups', 0)}",
        f"- Possible vehicle duplicate groups: {totals.get('possible_vehicle_duplicate_groups', 0)}",
        "",
        "## Identity Policy",
        "",
        f"- Policy version: `{policy.get('version', '')}`",
        f"- Listing key: {policy.get('listing_key', '')}",
        f"- Vehicle fingerprint: {policy.get('vehicle_fingerprint', '')}",
        f"- Km bucket size: {policy.get('km_bucket_size', 0)}",
        f"- Price bucket size: {policy.get('price_bucket_size', 0)}",
        f"- Note: {policy.get('note', '')}",
        "",
        "## By Source",
        "",
        "| Source | Records | Unique Listing Keys | Reobserved Groups | Possible Vehicle Duplicate Groups |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for source, source_total in sorted(dict(totals.get("by_source") or {}).items()):
        lines.append(
            "| {source} | {records} | {unique_listing_keys} | {reobserved_listing_groups} | "
            "{possible_vehicle_duplicate_groups} |".format(
                source=source,
                records=source_total.get("records", 0),
                unique_listing_keys=source_total.get("unique_listing_keys", 0),
                reobserved_listing_groups=source_total.get("reobserved_listing_groups", 0),
                possible_vehicle_duplicate_groups=source_total.get("possible_vehicle_duplicate_groups", 0),
            )
        )

    lines.extend(["", "## Reobserved Listing Keys", ""])
    reobserved = list(index.get("reobserved_listing_groups") or [])
    if not reobserved:
        lines.append("No repeated source listing keys were found in this selected collection.")
    else:
        lines.extend(
            [
                "| Listing Key | Source | Observations | First Seen | Last Seen |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for group in reobserved[:duplicate_group_limit]:
            lines.append(
                "| `{listing_key}` | {source} | {observation_count} | {first_seen_at} | {last_seen_at} |".format(
                    listing_key=group.get("listing_key", ""),
                    source=group.get("source", ""),
                    observation_count=group.get("observation_count", 0),
                    first_seen_at=group.get("first_seen_at", ""),
                    last_seen_at=group.get("last_seen_at", ""),
                )
            )

    lines.extend(["", "## Possible Vehicle Duplicate Groups", ""])
    groups = list(index.get("possible_vehicle_duplicate_groups") or [])
    if not groups:
        lines.append("No conservative vehicle duplicate groups were found.")
    else:
        lines.extend(
            [
                "| Fingerprint | Observations | Sources | Cities | Sample Listings |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for group in groups[:duplicate_group_limit]:
            sample = "; ".join(
                "{source} {city} {year} {brand} {model} {price}".format(
                    source=item.get("source", ""),
                    city=item.get("city", ""),
                    year=item.get("model_year", ""),
                    brand=item.get("brand", ""),
                    model=item.get("model", ""),
                    price=item.get("listed_price_inr", ""),
                )
                for item in list(group.get("observations") or [])[:3]
            )
            lines.append(
                "| `{fingerprint}` | {observation_count} | {sources} | {cities} | {sample} |".format(
                    fingerprint=group.get("vehicle_fingerprint", ""),
                    observation_count=group.get("observation_count", 0),
                    sources=", ".join(group.get("sources") or []),
                    cities=", ".join(group.get("cities") or []),
                    sample=sample,
                )
            )
        if len(groups) > duplicate_group_limit:
            lines.append("")
            lines.append(f"Showing first {duplicate_group_limit} of {len(groups)} possible duplicate groups.")

    lines.append("")
    return "\n".join(lines)


def write_listing_lifecycle_json(path: str | Path, index: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def write_listing_lifecycle_markdown(path: str | Path, index: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_listing_lifecycle_markdown(index), encoding="utf-8")
    return output_path


def _observation_from_record(
    record: dict[str, Any],
    *,
    record_index: int,
    manifest: dict[str, Any],
    silver_path: Path,
) -> dict[str, Any]:
    listing_identity = _listing_identity(record)
    vehicle = _vehicle_fingerprint(record)
    captured_at = str(record.get("captured_at") or manifest.get("captured_at") or "")
    capture_date = str(manifest.get("capture_date") or "")
    return {
        "listing_key": listing_identity["listing_key"],
        "listing_identity_basis": listing_identity["basis"],
        "listing_identity_value": listing_identity["value"],
        "vehicle_fingerprint": vehicle["fingerprint"],
        "vehicle_fingerprint_components": vehicle["components"],
        "source": str(record.get("source") or manifest.get("source") or ""),
        "source_listing_id": _string(record.get("source_listing_id")),
        "listing_url": _string(record.get("listing_url")),
        "run_id": str(record.get("ingestion_run_id") or manifest.get("run_id") or ""),
        "capture_date": capture_date,
        "captured_at": captured_at,
        "record_index": record_index,
        "silver_path": str(silver_path),
        "city": _string(record.get("city") or manifest.get("city")),
        "state": _string(record.get("state") or manifest.get("state")),
        "brand": _string(record.get("brand")),
        "model": _string(record.get("model")),
        "variant": _string(record.get("variant")),
        "model_year": record.get("model_year") or record.get("manufacture_year"),
        "fuel_type": _string(record.get("fuel_type")),
        "transmission": _string(record.get("transmission")),
        "km_driven": record.get("km_driven"),
        "ownership": record.get("ownership"),
        "registration_code": _string(record.get("registration_code")),
        "listed_price_inr": record.get("listed_price_inr"),
        "is_available": record.get("is_available"),
        "raw_record_hash": _string(record.get("raw_record_hash")),
    }


def _listing_identity(record: dict[str, Any]) -> dict[str, str]:
    source = _normalize_token(record.get("source"))
    listing_url = _normalize_url(record.get("listing_url"))
    if listing_url:
        basis = "listing_url"
        value = listing_url
    elif _string(record.get("source_listing_id")):
        basis = "source_listing_id"
        value = _normalize_token(record.get("source_listing_id"))
    elif _string(record.get("raw_record_hash")):
        basis = "raw_record_hash"
        value = _normalize_token(record.get("raw_record_hash"))
    else:
        basis = "core_fields"
        value = "|".join(
            [
                _normalize_token(record.get("city")),
                _normalize_token(record.get("brand")),
                _normalize_token(record.get("model")),
                _normalize_token(record.get("variant")),
                _normalize_token(record.get("model_year") or record.get("manufacture_year")),
                _normalize_token(record.get("listed_price_inr")),
                _normalize_token(record.get("km_driven")),
            ]
        )
    material = f"{source}|{basis}|{value}"
    return {
        "listing_key": f"listing_{_short_hash(material)}",
        "basis": basis,
        "value": value,
    }


def _vehicle_fingerprint(record: dict[str, Any]) -> dict[str, Any]:
    year = record.get("model_year") or record.get("manufacture_year")
    km_bucket = _bucket(record.get("km_driven"), KM_BUCKET_SIZE)
    price_bucket = _bucket(record.get("listed_price_inr"), PRICE_BUCKET_SIZE)
    components = {
        "city": _normalize_token(record.get("city")),
        "brand": _normalize_token(record.get("brand")),
        "model": _normalize_token(record.get("model")),
        "variant": _normalize_token(record.get("variant")),
        "year": _normalize_token(year),
        "fuel_type": _normalize_token(record.get("fuel_type")),
        "transmission": _normalize_token(record.get("transmission")),
        "ownership": _normalize_token(record.get("ownership")),
        "registration_code": _normalize_token(record.get("registration_code")),
        "km_bucket": str(km_bucket) if km_bucket is not None else "",
        "price_bucket": str(price_bucket) if price_bucket is not None else "",
    }
    if not all(components.values()):
        return {"fingerprint": "", "components": components}
    material = "|".join(components[key] for key in sorted(components))
    return {
        "fingerprint": f"vehicle_{_short_hash(material)}",
        "components": components,
    }


def _build_listing_entities(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        grouped[observation["listing_key"]].append(observation)

    entities = []
    for listing_key, items in grouped.items():
        sorted_items = sorted(items, key=_observation_sort_key)
        latest = sorted_items[-1]
        entities.append(
            {
                "listing_key": listing_key,
                "source": latest["source"],
                "listing_identity_basis": latest["listing_identity_basis"],
                "listing_identity_value": latest["listing_identity_value"],
                "vehicle_fingerprint": latest["vehicle_fingerprint"],
                "observation_count": len(sorted_items),
                "first_seen_at": sorted_items[0]["captured_at"],
                "last_seen_at": sorted_items[-1]["captured_at"],
                "capture_dates": sorted({item["capture_date"] for item in sorted_items if item["capture_date"]}),
                "run_ids": sorted({item["run_id"] for item in sorted_items if item["run_id"]}),
                "latest_observation": _public_observation(latest),
            }
        )
    return sorted(entities, key=lambda item: (item["source"], item["listing_key"]))


def _possible_vehicle_duplicate_groups(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        fingerprint = observation.get("vehicle_fingerprint")
        if fingerprint:
            grouped[str(fingerprint)].append(observation)

    groups = []
    for fingerprint, items in grouped.items():
        listing_keys = sorted({item["listing_key"] for item in items})
        if len(listing_keys) <= 1:
            continue
        groups.append(
            {
                "vehicle_fingerprint": fingerprint,
                "observation_count": len(items),
                "listing_key_count": len(listing_keys),
                "sources": sorted({item["source"] for item in items if item["source"]}),
                "cities": sorted({item["city"] for item in items if item["city"]}),
                "listing_keys": listing_keys,
                "observations": [_public_observation(item) for item in sorted(items, key=_observation_sort_key)],
            }
        )
    return sorted(groups, key=lambda group: (-int(group["observation_count"]), group["vehicle_fingerprint"]))


def _totals_by_source(observations: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    source_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        source_records[observation["source"]].append(observation)

    duplicate_groups = _possible_vehicle_duplicate_groups(observations)
    duplicate_group_count_by_source: dict[str, int] = defaultdict(int)
    for group in duplicate_groups:
        for source in group.get("sources") or []:
            duplicate_group_count_by_source[str(source)] += 1

    totals = {}
    for source, records in source_records.items():
        listing_keys = {record["listing_key"] for record in records}
        reobserved = {
            listing_key
            for listing_key in listing_keys
            if sum(1 for record in records if record["listing_key"] == listing_key) > 1
        }
        totals[source] = {
            "records": len(records),
            "unique_listing_keys": len(listing_keys),
            "reobserved_listing_groups": len(reobserved),
            "possible_vehicle_duplicate_groups": duplicate_group_count_by_source[source],
        }
    return totals


def _entity_group_summary(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "listing_key": entity.get("listing_key", ""),
        "source": entity.get("source", ""),
        "observation_count": entity.get("observation_count", 0),
        "first_seen_at": entity.get("first_seen_at", ""),
        "last_seen_at": entity.get("last_seen_at", ""),
        "run_ids": entity.get("run_ids", []),
    }


def _public_observation(observation: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "listing_key",
        "source",
        "source_listing_id",
        "listing_url",
        "run_id",
        "capture_date",
        "captured_at",
        "city",
        "state",
        "brand",
        "model",
        "variant",
        "model_year",
        "fuel_type",
        "transmission",
        "km_driven",
        "ownership",
        "registration_code",
        "listed_price_inr",
        "is_available",
    ]
    return {key: observation.get(key) for key in keys}


def _silver_path_from_manifest(manifest: dict[str, Any], *, manifest_path: Path) -> Path:
    output_paths = manifest.get("output_paths")
    if not isinstance(output_paths, dict) or not output_paths.get("silver"):
        raise ValueError(f"Manifest does not include output_paths.silver: {manifest_path}")
    silver_path = _resolve_path(output_paths["silver"], bases=[manifest_path.parent])
    if silver_path is None:
        raise FileNotFoundError(f"Silver output not found for manifest {manifest_path}: {output_paths['silver']}")
    return silver_path


def _resolve_path(value: Any, *, bases: list[Path]) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    candidates = [path] if path.is_absolute() else [path] + [base / path for base in bases]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _normalize_url(value: Any) -> str:
    text = _string(value)
    if not text:
        return ""
    parts = urlsplit(text.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = re.sub(r"/+", "/", parts.path).rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def _normalize_token(value: Any) -> str:
    text = _string(value)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _bucket(value: Any, size: int) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return (number // size) * size


def _short_hash(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _observation_sort_key(observation: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(observation.get("captured_at") or ""),
        str(observation.get("run_id") or ""),
        int(observation.get("record_index") or 0),
    )


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
