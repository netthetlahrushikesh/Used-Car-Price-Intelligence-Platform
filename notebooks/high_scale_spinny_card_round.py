"""Run one high-scale Spinny card-only round across trusted hubs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from high_scale_collection_loop import SPINNY_HUBS


@dataclass(frozen=True)
class SpinnyRunResult:
    slug: str
    returncode: int
    stdout_path: str
    stderr_path: str
    payload_output: str
    run_id: str


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    python_executable = root / ".venv" / "Scripts" / "python.exe"
    if not python_executable.exists():
        python_executable = Path(sys.executable)

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = [
            executor.submit(
                run_hub,
                hub=hub,
                root=root,
                python_executable=python_executable,
                round_number=args.round_number,
                capture_date=args.capture_date,
            )
            for hub in SPINNY_HUBS
        ]
        results = [future.result() for future in futures]

    write_status(
        root=root,
        capture_date=args.capture_date,
        round_number=args.round_number,
        results=results,
    )
    failing = [result for result in results if result.returncode != 0]
    if failing:
        for result in failing:
            print(f"spinny round {args.round_number}: failed {result.slug} rc={result.returncode}", flush=True)
        return 1
    print(f"spinny round {args.round_number}: complete", flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Spinny card-only extraction for one high-scale round.")
    parser.add_argument("--round-number", type=int, required=True)
    parser.add_argument("--capture-date", default="2026-06-27")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--max-workers", type=int, default=3)
    return parser


def run_hub(
    *,
    hub: dict[str, str],
    root: Path,
    python_executable: Path,
    round_number: int,
    capture_date: str,
) -> SpinnyRunResult:
    run_id = f"run_20260627_spinny_{hub['slug']}_card100_high_scale_r{round_number:02d}"
    payload_output = root / "data" / "tmp" / f"{run_id}_payload.json"
    log_dir = root / "data" / "tmp" / "high_scale_loop"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"round_{round_number:02d}_spinny_{hub['slug']}.stdout.log"
    stderr_path = log_dir / f"round_{round_number:02d}_spinny_{hub['slug']}.stderr.log"
    command = [
        str(python_executable),
        "-m",
        "used_car_price_intelligence.cli",
        "spinny-live-smoke",
        "--url",
        hub["url"],
        "--payload-output",
        str(payload_output),
        "--run-id",
        run_id,
        "--capture-date",
        capture_date,
        "--output-root",
        "data",
        "--city",
        hub["city"],
        "--state",
        hub["state"],
        "--locality",
        hub["locality"],
        "--max-pages",
        "4",
        "--max-records",
        "100",
        "--min-records",
        "1",
        "--capture-attempts",
        "4",
        "--retry-delay-ms",
        "2000",
        "--page-scroll-delay-ms",
        "5000",
        "--timeout-ms",
        "60000",
        "--detail-pages",
        "0",
        "--json",
    ]
    env = dict(**os.environ)
    env["PYTHONPATH"] = "src"
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            text=True,
            stdout=stdout,
            stderr=stderr,
            check=False,
        )
    return SpinnyRunResult(
        slug=hub["slug"],
        returncode=completed.returncode,
        stdout_path=stdout_path.as_posix(),
        stderr_path=stderr_path.as_posix(),
        payload_output=payload_output.as_posix(),
        run_id=run_id,
    )


def write_status(
    *,
    root: Path,
    capture_date: str,
    round_number: int,
    results: list[SpinnyRunResult],
) -> None:
    status_dir = root / "data" / "gold" / "high_scale_runs" / f"capture_date={capture_date}"
    status_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "round_number": round_number,
        "capture_date": capture_date,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "pass" if all(result.returncode == 0 for result in results) else "fail",
        "results": [result.__dict__ for result in results],
    }
    output = status_dir / f"round_{round_number:02d}_spinny_status.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
