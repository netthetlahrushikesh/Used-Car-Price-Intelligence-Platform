"""Common helpers shared by source adapters."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


@dataclass(frozen=True)
class AdapterRunContext:
    """Metadata applied to all records in one adapter run."""

    captured_at: str
    ingestion_run_id: str
    parser_version: str | None = None
    schema_version: str = "canonical_listing_v0.1"
    city: str = "Hyderabad"
    state: str = "Telangana"


@dataclass(frozen=True)
class PayloadContractFailure:
    record_index: int | None
    field_name: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_index": self.record_index,
            "field_name": self.field_name,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PayloadContractResult:
    source: str
    records_total: int
    failures: tuple[PayloadContractFailure, ...]

    @property
    def ok(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "records_total": self.records_total,
            "ok": self.ok,
            "failures": [failure.to_dict() for failure in self.failures],
        }


def stable_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", str(value))
    if match is None:
        return None
    return int(match.group(0))


def format_contract_error(source_display_name: str, result: PayloadContractResult) -> str:
    failures = "; ".join(
        f"record={failure.record_index or 'payload'} field={failure.field_name} reason={failure.reason}"
        for failure in result.failures
    )
    return f"{source_display_name} extracted payload failed contract validation: {failures}"
