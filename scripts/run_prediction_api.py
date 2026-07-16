"""Run the local FastAPI prediction service."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--artifact",
        type=Path,
        help="Optional path to final_price_model_v1.joblib. Defaults to artifacts/model/...",
    )
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload for local work.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.artifact:
        os.environ["USED_CAR_MODEL_ARTIFACT"] = str(args.artifact)

    uvicorn.run(
        "used_car_price_intelligence.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
