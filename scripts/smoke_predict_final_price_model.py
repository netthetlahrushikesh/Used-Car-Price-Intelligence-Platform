"""Smoke-test the exported final model artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from used_car_price_intelligence.modeling import load_artifact  # noqa: E402


DEFAULT_ARTIFACT = ROOT / "artifacts" / "model" / "final_price_model_v1" / "final_price_model_v1.joblib"
DEFAULT_REQUEST = ROOT / "artifacts" / "model" / "final_price_model_v1" / "sample_request.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact = load_artifact(args.artifact)
    payload = json.loads(args.request.read_text(encoding="utf-8"))
    response = artifact.predict_one(payload)
    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
