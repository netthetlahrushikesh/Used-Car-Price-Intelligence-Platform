"""Build the separated True Value Kaggle external modeling package.

Run from the repository root:

    .venv\\Scripts\\python.exe notebooks\\build_true_value_external_kaggle_package.py
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

from used_car_price_intelligence.external import build_true_value_kaggle_package  # noqa: E402


DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "external" / "raw" / "true_value_kaggle_focusedmonk"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "gold" / "external" / "true_value_kaggle_focusedmonk"
DEFAULT_PROFILE_DIR = REPO_ROOT / "data" / "external" / "profile" / "true_value_kaggle_focusedmonk"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--profile-output-dir", type=Path, default=DEFAULT_PROFILE_DIR)
    parser.add_argument("--min-group-size", type=int, default=3)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args()

    result = build_true_value_kaggle_package(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        profile_output_dir=args.profile_output_dir,
        generated_at=args.generated_at,
        min_group_size=args.min_group_size,
        test_ratio=args.test_ratio,
    )
    summary = {
        "dataset_id": result["dataset_manifest"]["dataset_id"],
        "source": result["dataset_manifest"]["source"],
        "raw_rows": result["quality_summary"]["raw_rows"],
        "pricing_ready_rows": result["quality_summary"]["pricing_ready_rows"],
        "quarantine_rows": result["quality_summary"]["quarantine_rows"],
        "dataset_manifest": result["output_paths"]["dataset_manifest_markdown"],
        "dataset_csv": result["output_paths"]["dataset_csv"],
        "quality_summary": result["output_paths"]["quality_summary_markdown"],
        "raw_profile": result["output_paths"]["raw_profile_markdown"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
