"""Best-effort JSONL logging for successful /predict calls.

Never raises into the request path. Does not log secrets or auth material.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Mapping

DEFAULT_LOG_RELATIVE = Path("logs") / "predictions.jsonl"
LOG_PATH_ENV = "USED_CAR_PREDICTION_LOG"

# Request fields safe to summarize for monitoring / drift.
FEATURE_SUMMARY_KEYS = (
    "brand",
    "model",
    "variant",
    "model_year",
    "km_driven",
    "fuel_type",
    "transmission",
    "city",
    "state",
    "ownership",
    "registration_code",
    "source_context",
    "market_snapshot_year",
)


def resolve_log_path(log_path: Path | str | None = None) -> Path:
    """Resolve the prediction log path from an override or environment."""

    if log_path is not None:
        return Path(log_path)
    configured = os.environ.get(LOG_PATH_ENV)
    if configured:
        return Path(configured)
    # Prefer repo-root logs/ when running from the package tree.
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / DEFAULT_LOG_RELATIVE


def feature_summary(features: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a compact, non-secret subset of request features."""

    if not features:
        return {}
    summary: dict[str, Any] = {}
    for key in FEATURE_SUMMARY_KEYS:
        if key in features:
            summary[key] = features[key]
    return summary


def build_prediction_log_record(
    *,
    features: Mapping[str, Any] | None,
    predicted_price: int | float | None,
    latency_ms: float,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Build one JSON-serializable prediction log record."""

    ts = timestamp or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "request_features": feature_summary(features),
        "predicted_price": predicted_price,
        "latency_ms": round(float(latency_ms), 3),
    }


def append_prediction_log(
    record: Mapping[str, Any],
    *,
    log_path: Path | str | None = None,
) -> bool:
    """Append one JSONL line. Returns False on any failure; never raises."""

    try:
        path = resolve_log_path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(dict(record), ensure_ascii=True, default=str)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return True
    except Exception:
        return False


def log_successful_prediction(
    *,
    features: Mapping[str, Any] | None,
    predicted_price: int | float | None,
    latency_ms: float,
    log_path: Path | str | None = None,
) -> bool:
    """Convenience wrapper used by the API hook."""

    record = build_prediction_log_record(
        features=features,
        predicted_price=predicted_price,
        latency_ms=latency_ms,
    )
    return append_prediction_log(record, log_path=log_path)
