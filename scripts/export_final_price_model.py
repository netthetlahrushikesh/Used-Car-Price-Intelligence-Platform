"""Export the Stage 2 final model artifact and API examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from used_car_price_intelligence.modeling import save_artifact, train_artifact_from_csv  # noqa: E402


DEFAULT_DATASET = (
    ROOT
    / "kaggle_upload"
    / "used-car-price-intelligence-trusted-modeling-datasets"
    / "combined_trusted_modeling_dataset_9110.csv"
)
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "model" / "final_price_model_v1"

SAMPLE_REQUEST = {
    "brand": "Maruti Suzuki",
    "model": "Swift",
    "variant": "VXI",
    "model_year": 2019,
    "km_driven": 45000,
    "fuel_type": "petrol",
    "transmission": "manual",
    "city": "Hyderabad",
    "state": "Telangana",
    "ownership": 1,
    "registration_code": "TS",
    "source_context": "market_default",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact = train_artifact_from_csv(args.dataset)
    saved_paths = save_artifact(artifact, args.output_dir)

    sample_response = artifact.predict_one(SAMPLE_REQUEST)
    (args.output_dir / "sample_request.json").write_text(
        json.dumps(SAMPLE_REQUEST, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "sample_response.json").write_text(
        json.dumps(sample_response, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "artifact_dir": str(args.output_dir),
                "dataset": str(args.dataset),
                "saved_paths": {key: str(path) for key, path in saved_paths.items()},
                "sample_prediction": sample_response,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Exported model artifact:")
    for key, path in saved_paths.items():
        print(f"- {key}: {path}")
    print(f"- sample_request: {args.output_dir / 'sample_request.json'}")
    print(f"- sample_response: {args.output_dir / 'sample_response.json'}")
    print(f"Sample predicted price: {sample_response['predicted_price_inr']:,} INR")
    print(f"Confidence: {sample_response['confidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
