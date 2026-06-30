"""Run repeated trusted-source high-scale collection rounds.

This is intentionally a notebook-style operational script, not a library API.
It uses the existing CLI/batch runner so every source run still writes the same
raw, silver, quality, smoke, manifest, ledger, lifecycle, and modeling artifacts.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterable


TRUE_VALUE_BATCH_IDS = [
    "true_value_hyderabad_40",
    "true_value_bengaluru_100",
    "true_value_delhi_ncr_100",
    "true_value_mumbai_100",
    "true_value_chennai_100",
    "true_value_hyderabad_250_expansion",
    "true_value_bengaluru_250_expansion",
    "true_value_delhi_ncr_700_expansion",
    "true_value_mumbai_350_expansion",
    "true_value_chennai_120_expansion",
    "true_value_pune_150_expansion",
    "true_value_ahmedabad_150_expansion",
    "true_value_kolkata_150_expansion",
    "true_value_jaipur_150_expansion",
    "true_value_lucknow_150_expansion",
    "true_value_surat_150_gap_close",
    "true_value_vadodara_150_gap_close",
    "true_value_nashik_150_gap_close",
    "true_value_nagpur_150_gap_close",
    "true_value_indore_150_gap_close",
    "true_value_bhopal_150_gap_close",
    "true_value_chandigarh_150_gap_close",
    "true_value_ludhiana_150_gap_close",
    "true_value_kochi_150_gap_close",
    "true_value_coimbatore_150_gap_close",
    "true_value_visakhapatnam_150_gap_close",
    "true_value_bhubaneswar_150_gap_close",
    "true_value_patna_150_gap_close",
    "true_value_guwahati_150_gap_close",
    "true_value_mysuru_40_5k_buffer",
    "true_value_mangaluru_40_5k_buffer",
    "true_value_madurai_40_5k_buffer",
    "true_value_vijayawada_40_5k_buffer",
    "true_value_rajkot_40_5k_buffer",
]

MFC_BATCH_IDS = [
    "mfc_hyderabad_40",
    "mfc_bengaluru_80",
    "mfc_delhi_ncr_80",
    "mfc_mumbai_80",
    "mfc_chennai_80",
    "mfc_pune_80_probe",
    "mfc_ahmedabad_80_probe",
    "mfc_kolkata_80_probe",
    "mfc_jaipur_80_probe",
    "mfc_lucknow_80_probe",
    "mfc_chandigarh_80_probe",
    "mfc_kochi_80_probe",
    "mfc_coimbatore_80_probe",
    "mfc_indore_80_probe",
    "mfc_surat_80_probe",
    "mfc_vadodara_80_probe",
    "mfc_nagpur_80_probe",
]

SPINNY_HUBS = [
    {
        "slug": "hyderabad",
        "city": "Hyderabad",
        "state": "Telangana",
        "locality": "Hyderabad",
        "url": "https://www.spinny.com/used-cars-at-hyderabad-forum-sujana-hub-in-hyderabad/s/",
    },
    {
        "slug": "bengaluru",
        "city": "Bengaluru",
        "state": "Karnataka",
        "locality": "Vega City Mall, Bengaluru",
        "url": "https://www.spinny.com/used-cars-at-bangalore-vega-mall-hub-in-bangalore/s/",
    },
    {
        "slug": "delhi_ncr",
        "city": "Delhi NCR",
        "state": "Delhi NCR",
        "locality": "Dwarka Sector 21, Delhi NCR",
        "url": "https://www.spinny.com/used-cars-at-delhi-dwarka-sector-21-taj-vivanta-hub-in-delhi-ncr/s/",
    },
    {
        "slug": "mumbai",
        "city": "Mumbai",
        "state": "Maharashtra",
        "locality": "Dadar, Mumbai",
        "url": "https://www.spinny.com/used-cars-at-mumbai-dadar-hub-in-mumbai/s/",
    },
    {
        "slug": "chennai",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "locality": "Nexus Vijaya Mall, Chennai",
        "url": "https://www.spinny.com/used-cars-at-chennai-nexus-vijaya-mall-in-chennai/s/",
    },
]


@dataclass(frozen=True)
class CommandResult:
    name: str
    returncode: int
    stdout_path: str
    stderr_path: str


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    python_executable = root / ".venv" / "Scripts" / "python.exe"
    if not python_executable.exists():
        python_executable = Path(sys.executable)

    for round_number in range(args.start_round, args.end_round + 1):
        print(f"round {round_number}: start", flush=True)
        results = run_round(
            round_number=round_number,
            capture_date=args.capture_date,
            root=root,
            python_executable=python_executable,
            max_workers=args.max_workers,
        )
        write_round_status(root=root, round_number=round_number, capture_date=args.capture_date, results=results)
        failing = [result for result in results if result.returncode != 0]
        if failing:
            for result in failing:
                print(f"round {round_number}: failed {result.name} rc={result.returncode}", flush=True)
            if not args.continue_on_source_fail:
                return 1
            print(f"round {round_number}: continuing after source failure", flush=True)
        print(f"round {round_number}: complete", flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run repeated trusted high-scale extraction rounds.")
    parser.add_argument("--start-round", type=int, required=True)
    parser.add_argument("--end-round", type=int, required=True)
    parser.add_argument("--capture-date", default="2026-06-27")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument(
        "--continue-on-source-fail",
        action="store_true",
        help="Continue later rounds even if one source command fails; status JSON still records the failure.",
    )
    return parser


def run_round(
    *,
    round_number: int,
    capture_date: str,
    root: Path,
    python_executable: Path,
    max_workers: int,
) -> list[CommandResult]:
    commands = [
        (
            "true_value",
            build_batch_command(
                python_executable=python_executable,
                source_label="true_value",
                round_number=round_number,
                capture_date=capture_date,
                batch_ids=TRUE_VALUE_BATCH_IDS,
            ),
        ),
        (
            "mfc",
            build_batch_command(
                python_executable=python_executable,
                source_label="mfc",
                round_number=round_number,
                capture_date=capture_date,
                batch_ids=MFC_BATCH_IDS,
            ),
        ),
        (
            "spinny_card",
            build_spinny_round_command(
                python_executable=python_executable,
                round_number=round_number,
                capture_date=capture_date,
            ),
        ),
    ]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(run_command_with_retry, name=name, command=command, root=root, round_number=round_number)
            for name, command in commands
        ]
        return [future.result() for future in futures]


def build_batch_command(
    *,
    python_executable: Path,
    source_label: str,
    round_number: int,
    capture_date: str,
    batch_ids: Iterable[str],
) -> list[str]:
    batch_run_id = f"batch_20260627_high_scale_r{round_number:02d}_{source_label}"
    command = [
        str(python_executable),
        "-m",
        "used_car_price_intelligence.cli",
        "run-batches",
        "--capture-date",
        capture_date,
        "--batch-run-id",
        batch_run_id,
        "--manifest-output",
        f"data/gold/batch_runs/capture_date={capture_date}/{batch_run_id}_batch_manifest.json",
        "--summary-output",
        f"data/gold/batch_runs/capture_date={capture_date}/{batch_run_id}_batch_summary.md",
        "--execute",
        "--json",
    ]
    for batch_id in batch_ids:
        command.extend(["--batch-id", batch_id])
    return command


def build_spinny_round_command(
    *,
    python_executable: Path,
    round_number: int,
    capture_date: str,
) -> list[str]:
    return [
        str(python_executable),
        "notebooks/high_scale_spinny_card_round.py",
        "--round-number",
        str(round_number),
        "--capture-date",
        capture_date,
    ]


def run_command_with_retry(
    *,
    name: str,
    command: list[str],
    root: Path,
    round_number: int,
) -> CommandResult:
    result = run_command(name=name, command=command, root=root, round_number=round_number, suffix="attempt1")
    if result.returncode == 0 or name == "spinny_card":
        return result

    retry_command = build_retry_command(command)
    if retry_command is None:
        return result
    return run_command(name=name, command=retry_command, root=root, round_number=round_number, suffix="retry1")


def build_retry_command(command: list[str]) -> list[str] | None:
    if "run-batches" not in command or "--manifest-output" not in command:
        return None
    manifest_path = command[command.index("--manifest-output") + 1]
    retry = list(command)
    batch_run_id_index = retry.index("--batch-run-id") + 1
    retry[batch_run_id_index] = f"{retry[batch_run_id_index]}_retry1"
    manifest_index = retry.index("--manifest-output") + 1
    summary_index = retry.index("--summary-output") + 1
    retry[manifest_index] = retry[manifest_index].replace("_batch_manifest.json", "_retry1_batch_manifest.json")
    retry[summary_index] = retry[summary_index].replace("_batch_summary.md", "_retry1_batch_summary.md")
    retry.extend(["--resume-from-manifest", manifest_path, "--skip-passed"])
    return retry


def run_command(
    *,
    name: str,
    command: list[str],
    root: Path,
    round_number: int,
    suffix: str,
) -> CommandResult:
    log_dir = root / "data" / "tmp" / "high_scale_loop"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"round_{round_number:02d}_{name}_{suffix}.stdout.log"
    stderr_path = log_dir / f"round_{round_number:02d}_{name}_{suffix}.stderr.log"
    env = dict(**__import__("os").environ)
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
    return CommandResult(
        name=name,
        returncode=completed.returncode,
        stdout_path=stdout_path.as_posix(),
        stderr_path=stderr_path.as_posix(),
    )


def write_round_status(
    *,
    root: Path,
    round_number: int,
    capture_date: str,
    results: list[CommandResult],
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
    output = status_dir / f"round_{round_number:02d}_status.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
