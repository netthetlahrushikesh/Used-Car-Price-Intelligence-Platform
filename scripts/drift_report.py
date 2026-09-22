"""Compare recent prediction-request features to a reference distribution.

Reads:
  - artifacts/monitoring/reference_feature_stats.json (mean/std or histogram bins)
  - logs/predictions.jsonl (or a fixture sample when logs are empty)

Writes:
  - reports/drift_report.md

Honest about insufficient data. Does not invent MAPE or drift claims.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT / "artifacts" / "monitoring" / "reference_feature_stats.json"
DEFAULT_LOG = ROOT / "logs" / "predictions.jsonl"
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "mlops" / "sample_predictions.jsonl"
DEFAULT_REPORT = ROOT / "reports" / "drift_report.md"

# Numeric request fields we can compare without model-internal encodings.
NUMERIC_FEATURES = ("model_year", "km_driven", "market_snapshot_year", "ownership")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--min-rows",
        type=int,
        default=5,
        help="Minimum recent rows required before reporting numeric shifts.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def extract_feature_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for record in records:
        payload = record.get("request_features") or record.get("features") or record
        if isinstance(payload, dict):
            features.append(payload)
    return features


def numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        raw = row.get(key)
        if raw is None or raw == "unknown":
            continue
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
    return values


def mean_std(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    mean = sum(values) / len(values)
    if len(values) == 1:
        return mean, 0.0
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return mean, math.sqrt(var)


def psi(reference: list[float], current: list[float], bins: int = 10) -> float | None:
    """Population Stability Index over equal-width bins of the reference range."""

    if len(reference) < 2 or len(current) < 2:
        return None
    lo = min(reference)
    hi = max(reference)
    if hi <= lo:
        return 0.0
    width = (hi - lo) / bins
    edges = [lo + i * width for i in range(bins + 1)]
    edges[-1] = hi + 1e-9

    def proportions(values: list[float]) -> list[float]:
        counts = [0] * bins
        for value in values:
            if value < edges[0]:
                idx = 0
            elif value >= edges[-1]:
                idx = bins - 1
            else:
                idx = min(bins - 1, int((value - edges[0]) / width))
            counts[idx] += 1
        total = len(values)
        # Floor to avoid divide-by-zero; classic PSI smoothing.
        return [max(c / total, 1e-4) for c in counts]

    ref_p = proportions(reference)
    cur_p = proportions(current)
    score = 0.0
    for r, c in zip(ref_p, cur_p):
        score += (c - r) * math.log(c / r)
    return score


def load_or_bootstrap_reference(path: Path, fixture_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    features = extract_feature_rows(fixture_rows)
    stats: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "bootstrap_from_fixture",
        "note": (
            "Auto-created from tests/fixtures/mlops because no gold/training stats "
            "were present. Replace by computing mean/std (and optional histogram) "
            "from gold modeling data, e.g. data/gold or the training parquet used "
            "for final_price_model_v1. Do not treat fixture bootstrap as production drift."
        ),
        "n_rows": len(features),
        "features": {},
    }
    for key in NUMERIC_FEATURES:
        values = numeric_values(features, key)
        mean, std = mean_std(values)
        stats["features"][key] = {
            "count": len(values),
            "mean": mean,
            "std": std,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "values": values,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
        handle.write("\n")
    return stats


def reference_values(stats: dict[str, Any], key: str) -> list[float]:
    feature = (stats.get("features") or {}).get(key) or {}
    if isinstance(feature.get("values"), list) and feature["values"]:
        return [float(v) for v in feature["values"]]
    # Reconstruct a tiny synthetic sample from mean/std when only summaries exist.
    mean = feature.get("mean")
    std = feature.get("std")
    count = int(feature.get("count") or 0)
    if mean is None or count <= 0:
        return []
    std = float(std or 0.0)
    # Deterministic stand-in sample for PSI when raw values were not stored.
    return [float(mean) + ((i % 3) - 1) * std for i in range(max(count, 5))]


def build_report(
    *,
    reference: dict[str, Any],
    current_rows: list[dict[str, Any]],
    current_source: str,
    min_rows: int,
) -> str:
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append("# Feature Drift Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{now}`")
    lines.append(f"- Reference source: `{reference.get('source', 'unknown')}`")
    lines.append(f"- Reference rows: `{reference.get('n_rows', 'n/a')}`")
    lines.append(f"- Current source: `{current_source}`")
    lines.append(f"- Current rows: `{len(current_rows)}`")
    lines.append("")

    if reference.get("note"):
        lines.append("## Notes")
        lines.append("")
        lines.append(str(reference["note"]))
        lines.append("")

    if len(current_rows) < min_rows:
        lines.append("## Insufficient data")
        lines.append("")
        lines.append(
            f"Need at least `{min_rows}` current feature rows to compute shifts. "
            f"Found `{len(current_rows)}`. No drift claim is made."
        )
        lines.append("")
        lines.append(
            "Populate `logs/predictions.jsonl` via the API, or pass a larger sample "
            "JSONL. To refresh the reference from gold data, compute per-feature "
            "`count/mean/std/min/max` (and optionally keep `values`) into "
            "`artifacts/monitoring/reference_feature_stats.json`."
        )
        lines.append("")
        return "\n".join(lines)

    lines.append("## Numeric mean / std shift")
    lines.append("")
    lines.append(
        "| feature | ref_mean | ref_std | cur_mean | cur_std | mean_delta | std_ratio | PSI |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")

    any_shift = False
    for key in NUMERIC_FEATURES:
        ref_vals = reference_values(reference, key)
        cur_vals = numeric_values(current_rows, key)
        ref_mean, ref_std = mean_std(ref_vals)
        cur_mean, cur_std = mean_std(cur_vals)
        if ref_mean is None or cur_mean is None:
            lines.append(f"| `{key}` | — | — | — | — | — | — | insufficient |")
            continue
        any_shift = True
        mean_delta = cur_mean - ref_mean
        std_ratio = (cur_std / ref_std) if ref_std and ref_std > 0 else None
        psi_score = psi(ref_vals, cur_vals)
        lines.append(
            "| `{key}` | {rm:.3f} | {rs:.3f} | {cm:.3f} | {cs:.3f} | {md:.3f} | {sr} | {psi} |".format(
                key=key,
                rm=ref_mean,
                rs=ref_std or 0.0,
                cm=cur_mean,
                cs=cur_std or 0.0,
                md=mean_delta,
                sr=f"{std_ratio:.3f}" if std_ratio is not None else "—",
                psi=f"{psi_score:.4f}" if psi_score is not None else "—",
            )
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if not any_shift:
        lines.append("No overlapping numeric features with enough values to compare.")
    else:
        lines.append(
            "- PSI guide (rule of thumb only): `<0.1` stable, `0.1–0.25` mild shift, "
            "`>0.25` larger shift — investigate, do not auto-retrain."
        )
        lines.append(
            "- This report compares **request feature summaries**, not training "
            "engineered columns (target encodings, frequencies)."
        )
        lines.append(
            "- Fixture or bootstrap references are for plumbing checks only; "
            "replace with gold-data stats before trusting production alerts."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    log_records = load_jsonl(args.log)
    fixture_records = load_jsonl(args.fixture)

    if log_records:
        current_records = log_records
        current_source = str(args.log)
    elif fixture_records:
        current_records = fixture_records
        current_source = f"fixture:{args.fixture}"
    else:
        current_records = []
        current_source = "none"

    reference = load_or_bootstrap_reference(args.reference, fixture_records or current_records)
    current_features = extract_feature_rows(current_records)
    report = build_report(
        reference=reference,
        current_rows=current_features,
        current_source=current_source,
        min_rows=args.min_rows,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
