"""Build the three-model experiment package.

Run from the repository root:

    .venv\\Scripts\\python.exe notebooks\\build_three_model_phase_package.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from used_car_price_intelligence.experiments import build_three_model_phase_package  # noqa: E402


DEFAULT_LIVE_DATASET = (
    REPO_ROOT
    / "data"
    / "gold"
    / "modeling"
    / "snapshot_20260627_100k_observation_run_modeling_v0"
    / "listings_modeling_dataset.csv"
)
DEFAULT_EXTERNAL_DATASET = (
    REPO_ROOT
    / "data"
    / "gold"
    / "external"
    / "true_value_kaggle_focusedmonk"
    / "listings_modeling_dataset.csv"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "gold" / "modeling_experiments" / "three_model_phase_20260628"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-dataset-csv", type=Path, default=DEFAULT_LIVE_DATASET)
    parser.add_argument("--external-dataset-csv", type=Path, default=DEFAULT_EXTERNAL_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--min-group-size", type=int, default=3)
    args = parser.parse_args()

    result = build_three_model_phase_package(
        live_dataset_csv=args.live_dataset_csv,
        external_dataset_csv=args.external_dataset_csv,
        output_dir=args.output_dir,
        generated_at=args.generated_at,
        test_ratio=args.test_ratio,
        min_group_size=args.min_group_size,
    )
    registry = result["registry"]
    summary = {
        "experiment_id": registry["experiment_id"],
        "model_candidates": [
            {
                "id": candidate["id"],
                "rows": candidate["rows"],
                "mae": candidate["baseline_metrics"].get("mae"),
                "mape": candidate["baseline_metrics"].get("mape"),
            }
            for candidate in registry["model_candidates"]
        ],
        "combined_dataset": result["output_paths"]["combined_dataset_csv"],
        "experiment_registry": result["output_paths"]["experiment_registry_markdown"],
        "combined_manifest": result["output_paths"]["combined_manifest_markdown"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
