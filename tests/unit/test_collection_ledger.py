import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.reporting import (
    build_collection_ledger,
    render_collection_ledger_markdown,
    write_collection_ledger_json,
    write_collection_ledger_markdown,
)


class CollectionLedgerTests(unittest.TestCase):
    def test_builds_ledger_from_batch_and_standalone_source_manifests(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "data"
            batch_manifest = root / "batch_manifest.json"
            source_manifest = write_source_manifest(
                output_root=output_root,
                capture_date="2026-06-26",
                source="mahindra_first_choice",
                run_id="run_mfc_bengaluru",
                city="Bengaluru",
                pricing_ready=80,
                source_total_items=126,
            )
            spinny_manifest = root / "spinny_manifest.json"
            write_source_manifest_file(
                spinny_manifest,
                source="spinny",
                run_id="run_spinny_hyderabad",
                capture_date="2026-06-25",
                city="Hyderabad",
                pricing_ready=60,
                source_total_items=0,
            )
            batch_manifest.write_text(
                json.dumps(
                    {
                        "batch_run_id": "batch_mfc",
                        "capture_date": "2026-06-26",
                        "job_results": [
                            {
                                "batch_id": "mfc_bengaluru_80",
                                "source": "mahindra_first_choice",
                                "run_id": "run_mfc_bengaluru",
                                "status": "pass",
                                "exit_code": 0,
                            },
                            {
                                "batch_id": "mfc_vadodara_80_probe",
                                "source": "mahindra_first_choice",
                                "run_id": "run_mfc_vadodara",
                                "status": "no_inventory",
                                "exit_code": 0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            write_zero_inventory_manifest(
                output_root=output_root,
                capture_date="2026-06-26",
                source="mahindra_first_choice",
                run_id="run_mfc_vadodara",
                city="Vadodara",
            )

            ledger = build_collection_ledger(
                collection_id="trusted_collection_test",
                batch_manifest_paths=[batch_manifest],
                source_manifest_paths=[spinny_manifest, source_manifest],
                output_root=output_root,
                generated_at="2026-06-26T00:00:00Z",
            )

        self.assertEqual(ledger["totals"]["pricing_ready"], 140)
        self.assertEqual(ledger["totals"]["source_runs"], 3)
        self.assertEqual(ledger["totals"]["by_source"]["spinny"]["pricing_ready"], 60)
        self.assertEqual(ledger["totals"]["by_source"]["mahindra_first_choice"]["pricing_ready"], 80)
        self.assertEqual(ledger["totals"]["by_source"]["mahindra_first_choice"]["source_runs"], 2)
        self.assertTrue(
            any(row["city"] == "Vadodara" and row["status"] == "no_inventory" for row in ledger["rows"])
        )

    def test_renders_and_writes_collection_ledger(self) -> None:
        ledger = {
            "collection_id": "trusted_collection_test",
            "generated_at": "2026-06-26T00:00:00Z",
            "totals": {
                "pricing_ready": 40,
                "quarantined": 0,
                "source_runs": 1,
                "by_source": {
                    "true_value": {
                        "source_runs": 1,
                        "pricing_ready": 40,
                        "quarantined": 0,
                        "source_total_signal": 247,
                    }
                },
            },
            "rows": [
                {
                    "source": "true_value",
                    "city": "Hyderabad",
                    "capture_date": "2026-06-25",
                    "status": "pass",
                    "pricing_ready": 40,
                    "quarantined": 0,
                    "source_total_items": 247,
                    "coverage_reason": "ok",
                    "required_completeness_avg": 1.0,
                    "high_value_completeness_avg": 1.0,
                    "run_id": "run_true_value_hyderabad",
                }
            ],
        }
        report = render_collection_ledger_markdown(ledger)

        self.assertIn("# Collection Ledger", report)
        self.assertIn("| true_value | 1 | 40 | 0 | 247 |", report)
        self.assertIn("| true_value | Hyderabad | 2026-06-25 | pass | 40 | 0 | 247 |", report)

        with TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "ledger.json"
            md_path = Path(tmpdir) / "ledger.md"

            self.assertEqual(write_collection_ledger_json(json_path, ledger), json_path)
            self.assertEqual(write_collection_ledger_markdown(md_path, ledger), md_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())


def write_source_manifest(
    *,
    output_root: Path,
    capture_date: str,
    source: str,
    run_id: str,
    city: str,
    pricing_ready: int,
    source_total_items: int,
) -> Path:
    path = (
        output_root
        / "gold"
        / "acquisition_runs"
        / f"capture_date={capture_date}"
        / f"{source}_{run_id}_manifest.json"
    )
    write_source_manifest_file(
        path,
        source=source,
        run_id=run_id,
        capture_date=capture_date,
        city=city,
        pricing_ready=pricing_ready,
        source_total_items=source_total_items,
    )
    return path


def write_source_manifest_file(
    path: Path,
    *,
    source: str,
    run_id: str,
    capture_date: str,
    city: str,
    pricing_ready: int,
    source_total_items: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "source": source,
                "run_id": run_id,
                "status": "pass",
                "capture_date": capture_date,
                "city": city,
                "state": "State",
                "source_url": f"https://example.com/{source}",
                "duration_seconds": 1.2,
                "quality_summary": {
                    "records_total": pricing_ready,
                    "pricing_ready": pricing_ready,
                    "quarantined": 0,
                    "required_completeness_avg": 1.0,
                    "high_value_completeness_avg": 0.9,
                    "optional_completeness_avg": 0.4,
                    "overall_completeness_avg": 0.93,
                },
                "listing_capture": {
                    "source_total_items": source_total_items,
                },
                "listing_coverage": {
                    "reason": "ok",
                },
            }
        ),
        encoding="utf-8",
    )


def write_zero_inventory_manifest(
    *,
    output_root: Path,
    capture_date: str,
    source: str,
    run_id: str,
    city: str,
) -> Path:
    path = (
        output_root
        / "gold"
        / "acquisition_runs"
        / f"capture_date={capture_date}"
        / f"{source}_{run_id}_manifest.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "source": source,
                "run_id": run_id,
                "status": "fail",
                "capture_date": capture_date,
                "city": city,
                "state": "State",
                "source_url": f"https://example.com/{source}/{city}",
                "duration_seconds": 1.2,
                "listing_capture": {
                    "records_total": 0,
                    "source_total_items": 0,
                    "stop_reason": "source_max_page_reached",
                },
                "listing_coverage": {
                    "reason": "records_below_minimum",
                },
            }
        ),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    unittest.main()
