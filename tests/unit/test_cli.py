import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from used_car_price_intelligence.cli import _listing_coverage_result, main


class CliTests(unittest.TestCase):
    def test_listing_coverage_passes_when_source_total_is_below_minimum(self) -> None:
        result = _listing_coverage_result(
            {
                "records_total": 10,
                "source_total_items": 10,
            },
            min_records=40,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason"], "source_total_below_minimum")
        self.assertEqual(result["source_total_items"], 10)

    def test_run_fixture_prints_json_summary(self) -> None:
        with patch("builtins.print") as print_mock:
            exit_code = main(
                [
                    "run-fixture",
                    "--source",
                    "spinny",
                    "--fixture",
                    "tests/fixtures/spinny/listing_cards_extracted.json",
                    "--captured-at",
                    "2026-06-24T03:00:00Z",
                    "--run-id",
                    "run_20260624_spinny_fixture_cli_test",
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 0)
        printed = print_mock.call_args.args[0]
        payload = json.loads(printed)
        self.assertEqual(payload["source"], "spinny")
        self.assertEqual(payload["records_total"], 5)
        self.assertEqual(payload["pricing_ready"], 5)
        self.assertEqual(payload["quarantined"], 0)

    def test_run_mahindra_first_choice_fixture_uses_source_default_fixture(self) -> None:
        with patch("builtins.print") as print_mock:
            exit_code = main(
                [
                    "run-fixture",
                    "--source",
                    "mahindra_first_choice",
                    "--captured-at",
                    "2026-06-25T03:30:00Z",
                    "--run-id",
                    "run_20260625_mfc_fixture_cli_test",
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(print_mock.call_args.args[0])
        self.assertEqual(payload["source"], "mahindra_first_choice")
        self.assertEqual(payload["records_total"], 9)
        self.assertEqual(payload["pricing_ready"], 9)
        self.assertEqual(payload["quarantined"], 0)
        self.assertLess(payload["high_value_completeness_avg"], 1.0)

    def test_run_true_value_fixture_uses_source_default_fixture(self) -> None:
        with patch("builtins.print") as print_mock:
            exit_code = main(
                [
                    "run-fixture",
                    "--source",
                    "true_value",
                    "--captured-at",
                    "2026-06-25T11:00:00Z",
                    "--run-id",
                    "run_20260625_true_value_fixture_cli_test",
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(print_mock.call_args.args[0])
        self.assertEqual(payload["source"], "true_value")
        self.assertEqual(payload["records_total"], 8)
        self.assertEqual(payload["pricing_ready"], 8)
        self.assertEqual(payload["quarantined"], 0)
        self.assertEqual(payload["high_value_completeness_avg"], 1.0)

    def test_run_fixture_can_write_outputs(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-fixture",
                        "--source",
                        "spinny",
                        "--fixture",
                        "tests/fixtures/spinny/listing_cards_extracted.json",
                        "--captured-at",
                        "2026-06-24T03:00:00Z",
                        "--capture-date",
                        "2026-06-24",
                        "--run-id",
                        "run_20260624_spinny_fixture_cli_test",
                        "--city",
                        "Bengaluru",
                        "--state",
                        "Karnataka",
                        "--output-root",
                        tmpdir,
                        "--write",
                        "--json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(print_mock.call_args.args[0])
            self.assertIn("output_paths", payload)
            self.assertIn("quality_summary", payload["output_paths"])
            silver_rows = json.loads(Path(payload["output_paths"]["silver"]).read_text(encoding="utf-8"))
            self.assertEqual(silver_rows[0]["city"], "Bengaluru")
            self.assertEqual(silver_rows[0]["state"], "Karnataka")

    def test_quality_report_prints_markdown_summary(self) -> None:
        with TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "quality_summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "source": "spinny",
                        "records_total": 5,
                        "silver_valid": 5,
                        "pricing_ready": 5,
                        "quarantined": 0,
                        "required_completeness_avg": 1.0,
                        "high_value_completeness_avg": 0.8571,
                        "optional_completeness_avg": 0.2333,
                        "overall_completeness_avg": 0.8948,
                        "quarantine_reasons": {},
                        "warnings": {},
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(["quality-report", "--summary", str(summary_path)])

        self.assertEqual(exit_code, 0)
        report = print_mock.call_args.args[0]
        self.assertIn("Status: PASS", report)
        self.assertIn("Records: 5 total", report)

    def test_field_profile_prints_markdown_summary(self) -> None:
        with patch("builtins.print") as print_mock:
            exit_code = main(
                [
                    "field-profile",
                    "--source",
                    "spinny",
                    "--fixture",
                    "tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json",
                    "--captured-at",
                    "2026-06-24T04:00:00Z",
                    "--run-id",
                    "run_20260624_spinny_live_fixture_test",
                ]
            )

        self.assertEqual(exit_code, 0)
        report = print_mock.call_args.args[0]
        self.assertIn("# Fixture Field Profile", report)
        self.assertIn("- listed_price_inr: 20/20 (100.00%)", report)
        self.assertIn("- ownership: 0/20 (0.00%)", report)

    def test_compare_sources_writes_markdown_report(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            left_silver = root / "spinny_silver.json"
            right_silver = root / "mfc_silver.json"
            left_quality = root / "spinny_quality.json"
            right_quality = root / "mfc_quality.json"
            left_manifest = root / "spinny_manifest.json"
            right_manifest = root / "mfc_manifest.json"
            output = root / "comparison.md"

            left_silver.write_text(json.dumps([cli_comparison_record("spinny", "spinny_1", "TS07")]), encoding="utf-8")
            right_silver.write_text(
                json.dumps([cli_comparison_record("mahindra_first_choice", "mfc_1", None)]),
                encoding="utf-8",
            )
            write_cli_summary(left_quality, "spinny")
            write_cli_summary(right_quality, "mahindra_first_choice")
            write_cli_manifest(left_manifest, "spinny", "run_spinny")
            write_cli_manifest(right_manifest, "mahindra_first_choice", "run_mfc")

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "compare-sources",
                        "--left-source",
                        "spinny",
                        "--left-silver",
                        str(left_silver),
                        "--left-quality-summary",
                        str(left_quality),
                        "--left-manifest",
                        str(left_manifest),
                        "--right-source",
                        "mahindra_first_choice",
                        "--right-silver",
                        str(right_silver),
                        "--right-quality-summary",
                        str(right_quality),
                        "--right-manifest",
                        str(right_manifest),
                        "--title",
                        "Spinny vs MFC",
                        "--generated-at",
                        "2026-06-25",
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(output))
            report = output.read_text(encoding="utf-8")
            self.assertIn("# Spinny vs MFC", report)
            self.assertIn("registration_code", report)

    def test_compare_source_runs_writes_markdown_report(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            spinny_silver = root / "spinny_silver.json"
            mfc_silver = root / "mfc_silver.json"
            true_value_silver = root / "true_value_silver.json"
            spinny_quality = root / "spinny_quality.json"
            mfc_quality = root / "mfc_quality.json"
            true_value_quality = root / "true_value_quality.json"
            spinny_manifest = root / "spinny_manifest.json"
            mfc_manifest = root / "mfc_manifest.json"
            true_value_manifest = root / "true_value_manifest.json"
            output = root / "three_source_comparison.md"

            spinny_silver.write_text(json.dumps([cli_comparison_record("spinny", "spinny_1", "TS07")]), encoding="utf-8")
            mfc_silver.write_text(
                json.dumps([cli_comparison_record("mahindra_first_choice", "mfc_1", None)]),
                encoding="utf-8",
            )
            true_value_silver.write_text(
                json.dumps([cli_comparison_record("true_value", "true_value_1", "TS08")]),
                encoding="utf-8",
            )
            write_cli_summary(spinny_quality, "spinny")
            write_cli_summary(mfc_quality, "mahindra_first_choice")
            write_cli_summary(true_value_quality, "true_value")
            write_cli_manifest(spinny_manifest, "spinny", "run_spinny")
            write_cli_manifest(mfc_manifest, "mahindra_first_choice", "run_mfc")
            write_cli_manifest(true_value_manifest, "true_value", "run_true_value")

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "compare-source-runs",
                        "--source-run",
                        "spinny",
                        str(spinny_silver),
                        str(spinny_quality),
                        str(spinny_manifest),
                        "--source-run",
                        "mahindra_first_choice",
                        str(mfc_silver),
                        str(mfc_quality),
                        str(mfc_manifest),
                        "--source-run",
                        "true_value",
                        str(true_value_silver),
                        str(true_value_quality),
                        str(true_value_manifest),
                        "--title",
                        "Three Source Comparison",
                        "--generated-at",
                        "2026-06-25",
                        "--recommendation",
                        "Build the batch runner next.",
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(output))
            report = output.read_text(encoding="utf-8")
            self.assertIn("# Three Source Comparison", report)
            self.assertIn("True Value", report)
            self.assertIn("Build the batch runner next.", report)

    def test_run_batches_writes_dry_run_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manifest_output = Path(tmpdir) / "batch_manifest.json"
            summary_output = Path(tmpdir) / "batch_summary.md"
            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-batches",
                        "--batch-id",
                        "true_value_hyderabad_40",
                        "--capture-date",
                        "2026-06-25",
                        "--batch-run-id",
                        "batch_cli_test",
                        "--manifest-output",
                        str(manifest_output),
                        "--summary-output",
                        str(summary_output),
                        "--json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            result = json.loads(print_mock.call_args.args[0])
            self.assertEqual(result["status"], "planned")
            self.assertEqual(result["job_count"], 1)
            self.assertEqual(result["job_results"][0]["batch_id"], "true_value_hyderabad_40")
            self.assertIsNone(result["job_results"][0]["exit_code"])
            self.assertTrue(manifest_output.exists())
            self.assertTrue(summary_output.exists())
            manifest = json.loads(manifest_output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["manifest_output"], str(manifest_output))
            self.assertEqual(manifest["summary_output"], str(summary_output))

    def test_run_batches_can_resume_and_skip_passed_job(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            previous_manifest = root / "previous_batch_manifest.json"
            manifest_output = root / "resumed_batch_manifest.json"
            previous_manifest.write_text(
                json.dumps(
                    {
                        "job_results": [
                            {
                                "batch_id": "true_value_hyderabad_40",
                                "source": "true_value",
                                "run_id": "run_previous_true_value",
                                "status": "pass",
                                "exit_code": 0,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-batches",
                        "--batch-id",
                        "true_value_hyderabad_40",
                        "--capture-date",
                        "2026-06-25",
                        "--batch-run-id",
                        "batch_resume_cli_test",
                        "--manifest-output",
                        str(manifest_output),
                        "--resume-from-manifest",
                        str(previous_manifest),
                        "--execute",
                        "--json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            result = json.loads(print_mock.call_args.args[0])
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["jobs_executed"], 0)
            self.assertEqual(result["jobs_skipped"], 1)
            self.assertEqual(result["job_results"][0]["status"], "skipped_passed")
            self.assertEqual(result["job_results"][0]["resumed_from_run_id"], "run_previous_true_value")
            self.assertTrue(manifest_output.exists())

    def test_collection_ledger_writes_json_and_markdown_outputs(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "data"
            source_manifest = (
                output_root
                / "gold"
                / "acquisition_runs"
                / "capture_date=2026-06-25"
                / "true_value_run_true_value_manifest.json"
            )
            source_manifest.parent.mkdir(parents=True, exist_ok=True)
            source_manifest.write_text(
                json.dumps(
                    {
                        "source": "true_value",
                        "run_id": "run_true_value",
                        "status": "pass",
                        "capture_date": "2026-06-25",
                        "city": "Hyderabad",
                        "state": "Telangana",
                        "source_url": "https://example.com/true_value",
                        "quality_summary": {
                            "records_total": 40,
                            "pricing_ready": 40,
                            "quarantined": 0,
                            "required_completeness_avg": 1.0,
                            "high_value_completeness_avg": 1.0,
                        },
                        "listing_capture": {"source_total_items": 247},
                        "listing_coverage": {"reason": "ok"},
                    }
                ),
                encoding="utf-8",
            )
            output_json = root / "ledger.json"
            output_md = root / "ledger.md"

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "collection-ledger",
                        "--collection-id",
                        "trusted_collection_test",
                        "--source-manifest",
                        str(source_manifest),
                        "--output-root",
                        str(output_root),
                        "--output-json",
                        str(output_json),
                        "--output-md",
                        str(output_md),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(output_md))
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            ledger = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(ledger["totals"]["pricing_ready"], 40)

    def test_listing_lifecycle_writes_outputs_from_collection_ledger(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            silver_path = root / "silver.json"
            silver_path.write_text(
                json.dumps(
                    [
                        {
                            "source": "spinny",
                            "source_listing_id": "spinny_1",
                            "listing_url": "https://example.com/car/1/",
                            "captured_at": "2026-06-26T01:00:00Z",
                            "city": "Hyderabad",
                            "state": "Telangana",
                            "brand": "Maruti Suzuki",
                            "model": "Wagon R",
                            "variant": "VXI",
                            "model_year": 2022,
                            "fuel_type": "petrol",
                            "transmission": "manual",
                            "km_driven": 12000,
                            "ownership": 1,
                            "registration_code": "TS07",
                            "listed_price_inr": 500000,
                            "is_available": True,
                            "raw_record_hash": "hash_1",
                            "ingestion_run_id": "run_spinny",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "source": "spinny",
                        "run_id": "run_spinny",
                        "status": "pass",
                        "capture_date": "2026-06-26",
                        "captured_at": "2026-06-26T01:00:00Z",
                        "city": "Hyderabad",
                        "state": "Telangana",
                        "output_paths": {"silver": str(silver_path)},
                    }
                ),
                encoding="utf-8",
            )
            ledger_path = root / "ledger.json"
            ledger_path.write_text(
                json.dumps(
                    {
                        "collection_id": "trusted_collection_test",
                        "rows": [{"manifest_path": str(manifest_path), "status": "pass"}],
                    }
                ),
                encoding="utf-8",
            )
            output_json = root / "lifecycle.json"
            output_md = root / "lifecycle.md"

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "listing-lifecycle",
                        "--lifecycle-id",
                        "lifecycle_test",
                        "--collection-ledger",
                        str(ledger_path),
                        "--output-json",
                        str(output_json),
                        "--output-md",
                        str(output_md),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(output_md))
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            lifecycle = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(lifecycle["totals"]["records_total"], 1)

    def test_snapshot_diff_writes_outputs_from_current_lifecycle(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            current_path = root / "current_lifecycle.json"
            current_path.write_text(
                json.dumps(
                    {
                        "lifecycle_id": "lifecycle_current",
                        "collection_id": "trusted_collection_test",
                        "listing_entities": [cli_lifecycle_entity("listing_a", "spinny")],
                    }
                ),
                encoding="utf-8",
            )
            output_json = root / "snapshot.json"
            output_md = root / "snapshot.md"

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "snapshot-diff",
                        "--snapshot-id",
                        "snapshot_test",
                        "--snapshot-date",
                        "2026-06-26",
                        "--current-lifecycle",
                        str(current_path),
                        "--output-json",
                        str(output_json),
                        "--output-md",
                        str(output_md),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(output_md))
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            diff = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertTrue(diff["policy"]["baseline_mode"])
            self.assertEqual(diff["totals"]["added_count"], 1)

    def test_scale_projection_writes_outputs_from_snapshot_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "snapshot_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "snapshot_id": "snapshot_baseline",
                        "snapshot_date": "2026-06-26",
                        "totals": {
                            "pricing_ready": 909,
                            "unique_listing_keys": 909,
                            "source_runs": 15,
                            "by_source": {
                                "spinny": {"pricing_ready": 300},
                                "true_value": {"pricing_ready": 429},
                                "mahindra_first_choice": {"pricing_ready": 180},
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            output_json = root / "scale_projection.json"
            output_md = root / "scale_projection.md"

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "scale-projection",
                        "--target-id",
                        "target_100k",
                        "--target-observations",
                        "100000",
                        "--current-snapshot-manifest",
                        str(manifest_path),
                        "--recommended-rows-per-snapshot",
                        "5000",
                        "--output-json",
                        str(output_json),
                        "--output-md",
                        str(output_md),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(output_md))
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            projection = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(projection["scenarios"]["recommended"]["future_snapshots_needed"], 20)

    def test_remaining_gap_strategy_writes_outputs_from_snapshot_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "snapshot_manifest.json"
            target_config_path = root / "snapshot_targets.yml"
            manifest_path.write_text(
                json.dumps(
                    {
                        "snapshot_id": "snapshot_current",
                        "snapshot_date": "2026-06-27",
                        "totals": {
                            "pricing_ready": 3_278,
                            "target_pricing_ready": 5_000,
                            "by_source": {
                                "true_value": {"pricing_ready": 2_448},
                                "mahindra_first_choice": {"pricing_ready": 510},
                                "spinny": {"pricing_ready": 320},
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            target_config_path.write_text(
                "\n".join(
                    [
                        "recommended_5000_row_source_allocation:",
                        "  true_value:",
                        "    target_rows: 2500",
                        "    share_pct: 50",
                        "  mahindra_first_choice:",
                        "    target_rows: 1500",
                        "    share_pct: 30",
                        "  spinny:",
                        "    target_rows: 1000",
                        "    share_pct: 20",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            output_json = root / "remaining_gap_strategy.json"
            output_md = root / "remaining_gap_strategy.md"

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "remaining-gap-strategy",
                        "--snapshot-manifest",
                        str(manifest_path),
                        "--target-config",
                        str(target_config_path),
                        "--output-json",
                        str(output_json),
                        "--output-md",
                        str(output_md),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(output_md))
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            strategy = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(strategy["decision"]["name"], "balanced_gap_close_required")
            self.assertEqual(strategy["source_rows"]["true_value"]["allocation_gap"], 52)

    def test_snapshot_manifest_writes_outputs_from_collection_artifacts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ledger_path = root / "ledger.json"
            lifecycle_path = root / "lifecycle.json"
            diff_path = root / "diff.json"
            ledger_path.write_text(
                json.dumps(
                    {
                        "collection_id": "trusted_collection_test",
                        "totals": {"source_runs": 1, "pricing_ready": 1, "quarantined": 0},
                        "rows": [
                            {
                                "source": "spinny",
                                "city": "Hyderabad",
                                "status": "pass",
                                "pricing_ready": 1,
                                "quarantined": 0,
                                "source_total_items": 0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            lifecycle_path.write_text(
                json.dumps(
                    {
                        "lifecycle_id": "lifecycle_current",
                        "collection_id": "trusted_collection_test",
                        "totals": {
                            "records_total": 1,
                            "source_runs": 1,
                            "unique_listing_keys": 1,
                            "possible_vehicle_duplicate_groups": 0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            diff_path.write_text(
                json.dumps(
                    {
                        "totals": {
                            "previous_unique_listing_keys": 0,
                            "current_unique_listing_keys": 1,
                            "added_count": 1,
                            "removed_count": 0,
                            "still_active_count": 0,
                            "price_change_count": 0,
                            "km_change_count": 0,
                        }
                    }
                ),
                encoding="utf-8",
            )
            output_json = root / "snapshot_manifest.json"
            output_md = root / "snapshot_manifest.md"

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "snapshot-manifest",
                        "--snapshot-id",
                        "snapshot_current",
                        "--snapshot-date",
                        "2026-06-26",
                        "--collection-ledger",
                        str(ledger_path),
                        "--lifecycle-index",
                        str(lifecycle_path),
                        "--snapshot-diff",
                        str(diff_path),
                        "--target-pricing-ready",
                        "5",
                        "--output-json",
                        str(output_json),
                        "--output-md",
                        str(output_md),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(output_md))
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            manifest = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["totals"]["rows_under_target"], 4)
            self.assertEqual(manifest["diff_vs_previous"]["added_count"], 1)

    def test_spinny_incremental_detail_reuses_cache_and_captures_only_missing_urls(self) -> None:
        captured_urls = []

        def fake_capture(**kwargs):
            captured_urls.extend(kwargs["listing_urls"])
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": "spinny",
                "captured_at": kwargs["captured_at"],
                "policy": {
                    "max_records": kwargs["max_records"],
                    "attempted_records": len(kwargs["listing_urls"]),
                    "attempts_per_record": kwargs["attempts"],
                    "timeout_ms": kwargs["timeout_ms"],
                    "delay_ms": kwargs["delay_ms"],
                },
                "records": [
                    {
                        "listing_url": kwargs["listing_urls"][0],
                        "raw": {"ownership": "2nd Owner", "rto": "TS07"},
                        "capture_status": "ok",
                        "attempts": 1,
                    }
                ],
            }
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            listing_payload = root / "listing_payload.json"
            existing_detail = root / "existing_detail.json"
            new_detail = root / "new_detail.json"
            plan_output = root / "plan.json"
            detail_output = root / "combined_detail.json"
            merged_output = root / "merged_payload.json"
            listing_payload.write_text(
                json.dumps(
                    {
                        "source": "spinny",
                        "source_url": "https://www.spinny.com/example/s/",
                        "records": [
                            {
                                "raw": {
                                    "title": "2022 Maruti Suzuki Wagon R",
                                    "price": "5.10 Lakh",
                                    "variant": "VXI",
                                    "km": "20K km",
                                    "fuel": "Petrol",
                                    "transmission": "Manual",
                                    "registration": "TS07",
                                    "locality": "Hyderabad",
                                    "listing_url": (
                                        "https://www.spinny.com/buy-used-cars/hyderabad/"
                                        "maruti-suzuki/wagon-r/example/1/?utm=abc"
                                    ),
                                }
                            },
                            {
                                "raw": {
                                    "title": "2023 Skoda Slavia",
                                    "price": "13.29 Lakh",
                                    "variant": "Style 1.0L TSI AT",
                                    "km": "21K km",
                                    "fuel": "Petrol",
                                    "transmission": "Automatic",
                                    "registration": "TS07",
                                    "locality": "Hyderabad",
                                    "listing_url": (
                                        "https://www.spinny.com/buy-used-cars/hyderabad/"
                                        "skoda/slavia/example/2/"
                                    ),
                                }
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            existing_detail.write_text(
                json.dumps(
                    {
                        "source": "spinny",
                        "records": [
                            {
                                "listing_url": (
                                    "https://www.spinny.com/buy-used-cars/hyderabad/"
                                    "maruti-suzuki/wagon-r/example/1/"
                                ),
                                "raw": {"ownership": "1st Owner", "rto": "TS07"},
                                "capture_status": "ok",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch("used_car_price_intelligence.cli.capture_spinny_detail_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "spinny-incremental-detail",
                            "--listing-payload",
                            str(listing_payload),
                            "--existing-detail-payload",
                            str(existing_detail),
                            "--max-new-records",
                            "1",
                            "--capture-missing",
                            "--new-detail-output",
                            str(new_detail),
                            "--output-plan",
                            str(plan_output),
                            "--output-detail-payload",
                            str(detail_output),
                            "--output-merged-payload",
                            str(merged_output),
                            "--captured-at",
                            "2026-06-27T03:00:00Z",
                            "--json",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            result = json.loads(print_mock.call_args.args[0])
            self.assertEqual(result["plan"]["cache_hit_count"], 1)
            self.assertEqual(result["plan"]["pending_count"], 1)
            self.assertEqual(len(captured_urls), 1)
            self.assertTrue(captured_urls[0].endswith("/skoda/slavia/example/2"))
            self.assertTrue(plan_output.exists())
            self.assertTrue(new_detail.exists())
            self.assertTrue(detail_output.exists())
            self.assertTrue(merged_output.exists())
            combined = json.loads(detail_output.read_text(encoding="utf-8"))
            merged = json.loads(merged_output.read_text(encoding="utf-8"))
            self.assertEqual(combined["policy"]["cache_reused_records"], 1)
            self.assertEqual(combined["policy"]["new_records_used"], 1)
            self.assertEqual(merged["records"][0]["raw"]["ownership"], "1st Owner")
            self.assertEqual(merged["records"][1]["raw"]["ownership"], "2nd Owner")

    def test_spinny_incremental_manifest_writes_acquisition_run_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "data"
            listing_payload = root / "listing_payload.json"
            detail_plan = root / "detail_plan.json"
            detail_payload = root / "detail_payload.json"
            quality_summary = root / "quality_summary.json"

            listing_payload.write_text(
                json.dumps(
                    {
                        "source": "spinny",
                        "source_url": "https://www.spinny.com/example/s/",
                        "captured_at": "2026-06-27T02:54:00Z",
                        "pagination": {"min_records": 2, "max_records": 2},
                        "records": [
                            {
                                "raw": {
                                    "listing_url": (
                                        "https://www.spinny.com/buy-used-cars/hyderabad/"
                                        "maruti-suzuki/wagon-r/example/1/"
                                    )
                                }
                            },
                            {
                                "raw": {
                                    "listing_url": (
                                        "https://www.spinny.com/buy-used-cars/hyderabad/"
                                        "skoda/slavia/example/2/"
                                    )
                                }
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            detail_plan.write_text(
                json.dumps(
                    {
                        "unique_listing_urls": 2,
                        "cache_hit_count": 1,
                        "pending_count": 1,
                        "max_new_records": 1,
                        "selected_new_count": 1,
                        "skipped_over_new_cap": 0,
                    }
                ),
                encoding="utf-8",
            )
            detail_payload.write_text(
                json.dumps(
                    {
                        "source": "spinny",
                        "captured_at": "2026-06-27T02:58:00Z",
                        "policy": {
                            "attempted_records": 2,
                            "cache_reused_records": 1,
                            "new_records_used": 1,
                            "missing_after_merge": 0,
                        },
                        "records": [
                            {"listing_url": "https://www.spinny.com/1", "capture_status": "ok", "raw": {}},
                            {"listing_url": "https://www.spinny.com/2", "capture_status": "ok", "raw": {}},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            quality_summary.write_text(
                json.dumps(
                    {
                        "source": "spinny",
                        "records_total": 2,
                        "silver_valid": 2,
                        "pricing_ready": 2,
                        "quarantined": 0,
                        "required_completeness_avg": 1.0,
                        "high_value_completeness_avg": 1.0,
                        "optional_completeness_avg": 0.5,
                        "overall_completeness_avg": 0.95,
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "spinny-incremental-manifest",
                        "--listing-payload",
                        str(listing_payload),
                        "--detail-plan",
                        str(detail_plan),
                        "--detail-payload",
                        str(detail_payload),
                        "--quality-summary",
                        str(quality_summary),
                        "--run-id",
                        "run_spinny_incremental_manifest_cli",
                        "--capture-date",
                        "2026-06-27",
                        "--output-root",
                        str(output_root),
                    ]
                )

            expected_manifest = (
                output_root
                / "gold"
                / "acquisition_runs"
                / "capture_date=2026-06-27"
                / "spinny_run_spinny_incremental_manifest_cli_manifest.json"
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], str(expected_manifest))
            manifest = json.loads(expected_manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "pass")
            self.assertEqual(manifest["record_counts"]["detail_cache_hits"], 1)
            self.assertEqual(manifest["record_counts"]["detail_new_records_used"], 1)
            self.assertIn("silver", manifest["output_paths"])

    def test_validate_payload_prints_json_result(self) -> None:
        with patch("builtins.print") as print_mock:
            exit_code = main(
                [
                    "validate-payload",
                    "--source",
                    "spinny",
                    "--payload",
                    "tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json",
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 0)
        result = json.loads(print_mock.call_args.args[0])
        self.assertTrue(result["ok"])
        self.assertEqual(result["records_total"], 20)

    def test_validate_mahindra_first_choice_payload_prints_json_result(self) -> None:
        with patch("builtins.print") as print_mock:
            exit_code = main(
                [
                    "validate-payload",
                    "--source",
                    "mahindra_first_choice",
                    "--payload",
                    "tests/fixtures/mahindra_first_choice/listing_cards_extracted.json",
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 0)
        result = json.loads(print_mock.call_args.args[0])
        self.assertTrue(result["ok"])
        self.assertEqual(result["records_total"], 9)

    def test_validate_true_value_payload_prints_json_result(self) -> None:
        with patch("builtins.print") as print_mock:
            exit_code = main(
                [
                    "validate-payload",
                    "--source",
                    "true_value",
                    "--payload",
                    "tests/fixtures/true_value/listing_cards_extracted.json",
                    "--json",
                ]
            )

        self.assertEqual(exit_code, 0)
        result = json.loads(print_mock.call_args.args[0])
        self.assertTrue(result["ok"])
        self.assertEqual(result["records_total"], 8)

    def test_capture_mfc_live_prints_json_result_after_valid_capture(self) -> None:
        def fake_capture(**kwargs):
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = mfc_live_payload(captured_at=kwargs["captured_at"] or "2026-06-25T08:45:00Z")
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "mfc_payload.json"
            with patch("used_car_price_intelligence.cli.capture_mfc_listing_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "capture-mfc-live",
                            "--output",
                            str(payload_output),
                            "--captured-at",
                            "2026-06-25T08:45:00Z",
                            "--min-records",
                            "1",
                            "--json",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        result = json.loads(print_mock.call_args.args[0])
        self.assertTrue(result["ok"])
        self.assertEqual(result["records_total"], 1)
        self.assertEqual(result["listing_capture"]["pagination_type"], "next_data_plus_xhr")

    def test_capture_true_value_live_prints_json_result_after_valid_capture(self) -> None:
        def fake_capture(**kwargs):
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = true_value_live_payload(captured_at=kwargs["captured_at"] or "2026-06-25T11:30:00Z")
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "true_value_payload.json"
            with patch("used_car_price_intelligence.cli.capture_true_value_listing_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "capture-true-value-live",
                            "--output",
                            str(payload_output),
                            "--captured-at",
                            "2026-06-25T11:30:00Z",
                            "--min-records",
                            "1",
                            "--json",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        result = json.loads(print_mock.call_args.args[0])
        self.assertTrue(result["ok"])
        self.assertEqual(result["records_total"], 1)
        self.assertEqual(result["listing_capture"]["pagination_type"], "dealer_discovery_plus_graphql")

    def test_validate_payload_returns_nonzero_for_contract_failure(self) -> None:
        with TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "invalid_payload.json"
            payload_path.write_text(
                json.dumps(
                    {
                        "source": "spinny",
                        "source_url": "https://www.spinny.com/example",
                        "records": [{"raw": {"title": "2022 Kia Seltos"}}],
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "validate-payload",
                        "--source",
                        "spinny",
                        "--payload",
                        str(payload_path),
                        "--json",
                    ]
                )

        self.assertEqual(exit_code, 1)
        result = json.loads(print_mock.call_args.args[0])
        self.assertFalse(result["ok"])
        self.assertGreaterEqual(len(result["failures"]), 1)

    def test_spinny_live_smoke_writes_outputs_after_valid_capture(self) -> None:
        source_payload = json.loads(
            Path("tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json").read_text(
                encoding="utf-8"
            )
        )

        def fake_capture(**kwargs):
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = dict(source_payload)
            payload["captured_at"] = kwargs["captured_at"]
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "payload.json"
            report_output = Path(tmpdir) / "smoke_report.md"
            output_root = Path(tmpdir) / "data"
            with patch("used_car_price_intelligence.cli.capture_spinny_listing_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "spinny-live-smoke",
                            "--payload-output",
                            str(payload_output),
                            "--captured-at",
                            "2026-06-24T05:40:00Z",
                            "--run-id",
                            "run_20260624_spinny_live_smoke_test",
                            "--output-root",
                            str(output_root),
                            "--report-output",
                            str(report_output),
                            "--json",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            result = json.loads(print_mock.call_args.args[0])
            self.assertTrue(result["ok"])
            self.assertTrue(result["payload_validation"]["ok"])
            self.assertEqual(result["quality_summary"]["pricing_ready"], 20)
            self.assertIn("quality_summary", result["output_paths"])
            self.assertIn("run_manifest", result["output_paths"])
            self.assertEqual(result["output_paths"]["smoke_report"], str(report_output))
            self.assertTrue(report_output.exists())
            self.assertIn("Status: PASS", report_output.read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["output_paths"]["run_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "pass")
            self.assertEqual(manifest["city"], "Hyderabad")
            self.assertEqual(manifest["record_counts"]["pricing_ready"], 20)

    def test_mfc_live_smoke_writes_outputs_after_valid_capture(self) -> None:
        def fake_capture(**kwargs):
            self.assertEqual(kwargs["max_records"], 1)
            self.assertEqual(kwargs["min_records"], 1)
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = mfc_live_payload(captured_at=kwargs["captured_at"])
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "mfc_payload.json"
            report_output = Path(tmpdir) / "mfc_smoke_report.md"
            output_root = Path(tmpdir) / "data"
            with patch("used_car_price_intelligence.cli.capture_mfc_listing_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "mfc-live-smoke",
                            "--payload-output",
                            str(payload_output),
                            "--captured-at",
                            "2026-06-25T08:45:00Z",
                            "--run-id",
                            "run_20260625_mfc_live_smoke_test",
                            "--output-root",
                            str(output_root),
                            "--report-output",
                            str(report_output),
                            "--max-records",
                            "1",
                            "--json",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            result = json.loads(print_mock.call_args.args[0])
            self.assertTrue(result["ok"])
            self.assertTrue(result["payload_validation"]["ok"])
            self.assertEqual(result["quality_summary"]["pricing_ready"], 1)
            self.assertIn("run_manifest", result["output_paths"])
            self.assertEqual(result["output_paths"]["smoke_report"], str(report_output))
            self.assertTrue(report_output.exists())
            self.assertIn("Source: mahindra_first_choice", report_output.read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["output_paths"]["run_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["source"], "mahindra_first_choice")
            self.assertEqual(manifest["record_counts"]["pricing_ready"], 1)

    def test_true_value_live_smoke_writes_outputs_after_valid_capture(self) -> None:
        def fake_capture(**kwargs):
            self.assertEqual(kwargs["max_records"], 1)
            self.assertEqual(kwargs["min_records"], 1)
            self.assertEqual(kwargs["page_size"], 100)
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = true_value_live_payload(captured_at=kwargs["captured_at"])
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "true_value_payload.json"
            report_output = Path(tmpdir) / "true_value_smoke_report.md"
            output_root = Path(tmpdir) / "data"
            with patch("used_car_price_intelligence.cli.capture_true_value_listing_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "true-value-live-smoke",
                            "--payload-output",
                            str(payload_output),
                            "--captured-at",
                            "2026-06-25T11:30:00Z",
                            "--run-id",
                            "run_20260625_true_value_live_smoke_test",
                            "--output-root",
                            str(output_root),
                            "--report-output",
                            str(report_output),
                            "--max-records",
                            "1",
                            "--json",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            result = json.loads(print_mock.call_args.args[0])
            self.assertTrue(result["ok"])
            self.assertTrue(result["payload_validation"]["ok"])
            self.assertEqual(result["quality_summary"]["pricing_ready"], 1)
            self.assertEqual(result["listing_capture"]["source_total_items"], 247)
            self.assertEqual(result["listing_capture"]["dealer_count"], 21)
            self.assertIn("run_manifest", result["output_paths"])
            self.assertEqual(result["output_paths"]["smoke_report"], str(report_output))
            self.assertTrue(report_output.exists())
            self.assertIn("Source: true_value", report_output.read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["output_paths"]["run_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["source"], "true_value")
            self.assertEqual(manifest["record_counts"]["pricing_ready"], 1)

    def test_spinny_live_smoke_includes_paginated_listing_capture_summary(self) -> None:
        source_payload = json.loads(
            Path("tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json").read_text(
                encoding="utf-8"
            )
        )

        def fake_capture(**kwargs):
            self.assertEqual(kwargs["max_pages"], 2)
            self.assertEqual(kwargs["max_records"], 40)
            self.assertEqual(kwargs["min_records"], 40)
            self.assertEqual(kwargs["page_scroll_delay_ms"], 2500)
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.loads(json.dumps(source_payload))
            payload["records"] = payload["records"] + json.loads(json.dumps(payload["records"]))
            payload["captured_at"] = kwargs["captured_at"]
            payload["pagination"] = {
                "pagination_type": "infinite_scroll_batches",
                "max_pages": kwargs["max_pages"],
                "attempted_pages": 2,
                "max_records": kwargs["max_records"],
                "min_records": kwargs["min_records"],
                "coverage_ok": True,
                "unique_cards_seen": 42,
                "returned_records": 40,
                "duplicate_cards_skipped": 22,
                "page_scroll_delay_ms": kwargs["page_scroll_delay_ms"],
                "stop_reason": "record_cap_reached",
            }
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "payload.json"
            report_output = Path(tmpdir) / "smoke_report.md"
            output_root = Path(tmpdir) / "data"
            with patch("used_car_price_intelligence.cli.capture_spinny_listing_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "spinny-live-smoke",
                            "--payload-output",
                            str(payload_output),
                            "--captured-at",
                            "2026-06-24T08:30:00Z",
                            "--run-id",
                            "run_20260624_spinny_pagination_test",
                            "--output-root",
                            str(output_root),
                            "--max-pages",
                            "2",
                            "--max-records",
                            "40",
                            "--page-scroll-delay-ms",
                            "2500",
                            "--report-output",
                            str(report_output),
                            "--json",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            result = json.loads(print_mock.call_args.args[0])
            self.assertEqual(result["listing_capture"]["pagination_type"], "infinite_scroll_batches")
            self.assertEqual(result["listing_capture"]["max_pages"], 2)
            self.assertEqual(result["listing_capture"]["attempted_pages"], 2)
            self.assertEqual(result["listing_capture"]["unique_cards_seen"], 42)
            self.assertTrue(result["listing_coverage"]["ok"])
            self.assertIn("Listing Capture:", report_output.read_text(encoding="utf-8"))

    def test_spinny_live_smoke_fails_closed_when_min_records_not_met(self) -> None:
        source_payload = json.loads(
            Path("tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json").read_text(
                encoding="utf-8"
            )
        )

        def fake_capture(**kwargs):
            self.assertEqual(kwargs["max_records"], 40)
            self.assertEqual(kwargs["min_records"], 40)
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.loads(json.dumps(source_payload))
            payload["captured_at"] = kwargs["captured_at"]
            payload["pagination"] = {
                "pagination_type": "infinite_scroll_batches",
                "max_pages": kwargs["max_pages"],
                "attempted_pages": 2,
                "max_records": kwargs["max_records"],
                "min_records": kwargs["min_records"],
                "coverage_ok": False,
                "unique_cards_seen": 20,
                "returned_records": 20,
                "duplicate_cards_skipped": 20,
                "page_scroll_delay_ms": kwargs["page_scroll_delay_ms"],
                "stop_reason": "no_new_cards_after_scroll",
            }
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "payload.json"
            report_output = Path(tmpdir) / "smoke_report.md"
            output_root = Path(tmpdir) / "data"
            with patch("used_car_price_intelligence.cli.capture_spinny_listing_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "spinny-live-smoke",
                            "--payload-output",
                            str(payload_output),
                            "--captured-at",
                            "2026-06-24T08:40:00Z",
                            "--run-id",
                            "run_20260624_spinny_under_capture_test",
                            "--output-root",
                            str(output_root),
                            "--max-pages",
                            "2",
                            "--max-records",
                            "40",
                            "--report-output",
                            str(report_output),
                            "--json",
                        ]
                    )

            self.assertEqual(exit_code, 1)
            result = json.loads(print_mock.call_args.args[0])
            self.assertFalse(result["ok"])
            self.assertFalse(result["listing_coverage"]["ok"])
            self.assertEqual(result["listing_coverage"]["missing_records"], 20)
            self.assertEqual(result["quality_skip_reason"], "listing coverage did not meet min_records")
            self.assertTrue(report_output.exists())
            report = report_output.read_text(encoding="utf-8")
            self.assertIn("Status: FAIL", report)
            self.assertIn("Listing Coverage:", report)
            self.assertIn("run_manifest", result["output_paths"])
            manifest = json.loads(Path(result["output_paths"]["run_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "fail")
            self.assertEqual(manifest["record_counts"]["listing_records"], 20)
            self.assertFalse((output_root / "raw").exists())

    def test_spinny_live_smoke_can_merge_detail_enrichment(self) -> None:
        source_payload = json.loads(
            Path("tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json").read_text(
                encoding="utf-8"
            )
        )

        def fake_capture(**kwargs):
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = copy_payload_with_listing_url(source_payload)
            payload["captured_at"] = kwargs["captured_at"]
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        def fake_detail_capture(**kwargs):
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": "spinny",
                "captured_at": kwargs["captured_at"],
                "policy": {
                    "max_records": kwargs["max_records"],
                    "attempted_records": 1,
                    "attempts_per_record": kwargs["attempts"],
                    "timeout_ms": kwargs["timeout_ms"],
                    "delay_ms": kwargs["delay_ms"],
                },
                "records": [
                    {
                        "listing_url": kwargs["listing_urls"][0],
                        "raw": {
                            "ownership": "1st Owner",
                            "make_year": "Apr 2022",
                            "registration_year": "May 2022",
                            "rto": "TS07",
                            "inspection_status": "quality_report_available",
                            "warranty_label": "1 year warranty",
                            "return_policy_label": "5-day money back",
                        },
                        "capture_status": "ok",
                        "attempts": 1,
                    }
                ],
            }
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "payload.json"
            detail_output = Path(tmpdir) / "detail.json"
            merged_output = Path(tmpdir) / "merged.json"
            report_output = Path(tmpdir) / "smoke_report.md"
            output_root = Path(tmpdir) / "data"
            with patch("used_car_price_intelligence.cli.capture_spinny_listing_payload", fake_capture):
                with patch("used_car_price_intelligence.cli.capture_spinny_detail_payload", fake_detail_capture):
                    with patch("builtins.print") as print_mock:
                        exit_code = main(
                            [
                                "spinny-live-smoke",
                                "--payload-output",
                                str(payload_output),
                                "--captured-at",
                                "2026-06-24T06:45:00Z",
                                "--run-id",
                                "run_20260624_spinny_detail_smoke_test",
                                "--output-root",
                                str(output_root),
                                "--detail-pages",
                                "1",
                                "--detail-output",
                                str(detail_output),
                                "--merged-output",
                                str(merged_output),
                                "--report-output",
                                str(report_output),
                                "--json",
                            ]
                        )

            self.assertEqual(exit_code, 0)
            result = json.loads(print_mock.call_args.args[0])
            self.assertTrue(result["ok"])
            self.assertTrue(result["enriched_payload_validation"]["ok"])
            self.assertEqual(result["detail_enrichment"]["records_total"], 1)
            self.assertTrue(result["detail_enrichment"]["ok"])
            self.assertEqual(result["detail_enrichment"]["successful_records"], 1)
            self.assertEqual(result["detail_enrichment"]["failed_records"], 0)
            fields = {field["field_name"]: field for field in result["field_profile"]["fields"]}
            self.assertEqual(fields["ownership"]["present_count"], 1)
            self.assertEqual(result["output_paths"]["detail_payload"], str(detail_output))
            self.assertEqual(result["output_paths"]["merged_payload"], str(merged_output))
            self.assertTrue(merged_output.exists())
            self.assertIn("ownership", merged_output.read_text(encoding="utf-8"))
            raw_output = Path(result["output_paths"]["raw"])
            self.assertIn("ownership", raw_output.read_text(encoding="utf-8"))

    def test_spinny_live_smoke_fails_closed_when_detail_enrichment_fails(self) -> None:
        source_payload = json.loads(
            Path("tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json").read_text(
                encoding="utf-8"
            )
        )

        def fake_capture(**kwargs):
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = copy_payload_with_listing_url(source_payload)
            payload["captured_at"] = kwargs["captured_at"]
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        def fake_detail_capture(**kwargs):
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": "spinny",
                "captured_at": kwargs["captured_at"],
                "policy": {
                    "max_records": kwargs["max_records"],
                    "attempted_records": 1,
                    "attempts_per_record": kwargs["attempts"],
                    "timeout_ms": kwargs["timeout_ms"],
                    "delay_ms": kwargs["delay_ms"],
                },
                "records": [
                    {
                        "listing_url": kwargs["listing_urls"][0],
                        "raw": {},
                        "capture_status": "failed",
                        "failure_reason": "detail_fields_missing",
                        "attempts": kwargs["attempts"],
                    }
                ],
            }
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "payload.json"
            detail_output = Path(tmpdir) / "detail.json"
            merged_output = Path(tmpdir) / "merged.json"
            report_output = Path(tmpdir) / "smoke_report.md"
            output_root = Path(tmpdir) / "data"
            with patch("used_car_price_intelligence.cli.capture_spinny_listing_payload", fake_capture):
                with patch("used_car_price_intelligence.cli.capture_spinny_detail_payload", fake_detail_capture):
                    with patch("builtins.print") as print_mock:
                        exit_code = main(
                            [
                                "spinny-live-smoke",
                                "--payload-output",
                                str(payload_output),
                                "--captured-at",
                                "2026-06-24T06:45:00Z",
                                "--run-id",
                                "run_20260624_spinny_detail_failure_test",
                                "--output-root",
                                str(output_root),
                                "--detail-pages",
                                "1",
                                "--detail-attempts",
                                "2",
                                "--detail-output",
                                str(detail_output),
                                "--merged-output",
                                str(merged_output),
                                "--report-output",
                                str(report_output),
                                "--json",
                            ]
                        )

            self.assertEqual(exit_code, 1)
            result = json.loads(print_mock.call_args.args[0])
            self.assertFalse(result["ok"])
            self.assertFalse(result["detail_enrichment"]["ok"])
            self.assertEqual(result["detail_enrichment"]["failed_records"], 1)
            self.assertTrue(detail_output.exists())
            self.assertTrue(merged_output.exists())
            self.assertTrue(report_output.exists())
            self.assertFalse((output_root / "raw").exists())

    def test_spinny_live_smoke_stops_before_outputs_when_payload_contract_fails(self) -> None:
        invalid_payload = {
            "source": "spinny",
            "source_url": "https://www.spinny.com/example",
            "captured_at": "2026-06-24T05:45:00Z",
            "records": [{"raw": {"title": "2022 Kia Seltos"}}],
        }

        def fake_capture(**kwargs):
            output_path = Path(kwargs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(invalid_payload), encoding="utf-8")
            return invalid_payload

        with TemporaryDirectory() as tmpdir:
            payload_output = Path(tmpdir) / "payload.json"
            report_output = Path(tmpdir) / "failure_report.md"
            output_root = Path(tmpdir) / "data"
            with patch("used_car_price_intelligence.cli.capture_spinny_listing_payload", fake_capture):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "spinny-live-smoke",
                            "--payload-output",
                            str(payload_output),
                            "--captured-at",
                            "2026-06-24T05:45:00Z",
                            "--run-id",
                            "run_20260624_spinny_live_smoke_failure_test",
                            "--output-root",
                            str(output_root),
                            "--report-output",
                            str(report_output),
                            "--json",
                        ]
                    )

            self.assertEqual(exit_code, 1)
            result = json.loads(print_mock.call_args.args[0])
            self.assertFalse(result["payload_validation"]["ok"])
            self.assertEqual(result["output_paths"]["smoke_report"], str(report_output))
            self.assertIn("run_manifest", result["output_paths"])
            self.assertTrue(report_output.exists())
            self.assertIn("Status: FAIL", report_output.read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["output_paths"]["run_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "fail")
            self.assertEqual(manifest["record_counts"]["payload_records"], 1)
            self.assertFalse((output_root / "raw").exists())


def copy_payload_with_listing_url(payload: dict) -> dict:
    copied = json.loads(json.dumps(payload))
    copied["records"][0]["raw"][
        "listing_url"
    ] = "https://www.spinny.com/buy-used-cars/hyderabad/mg-motors/hector-plus/example/123/"
    return copied


def mfc_live_payload(*, captured_at: str) -> dict:
    return {
        "source": "mahindra_first_choice",
        "source_url": "https://www.mahindrafirstchoice.com/used-cars/hyderabad",
        "captured_for": "live_public_search_capture",
        "capture_method": "playwright_next_data_plus_xhr",
        "captured_at": captured_at,
        "pagination": {
            "pagination_type": "next_data_plus_xhr",
            "max_pages": 2,
            "attempted_pages": 1,
            "max_records": 1,
            "min_records": 1,
            "coverage_ok": True,
            "unique_cards_seen": 1,
            "returned_records": 1,
            "duplicate_cards_skipped": 0,
            "page_scroll_delay_ms": 2500,
            "stop_reason": "record_cap_reached",
            "source_total_items": 88,
            "source_max_page": 3,
        },
        "records": [
            {
                "raw": {
                    "id_classified": 242953,
                    "score": "8.1",
                    "title": "2022 Mahindra Scorpio",
                    "model_year": 2022,
                    "brand": "Mahindra",
                    "model": "Scorpio",
                    "variant": "S11 2WD BS IV",
                    "variant_details": "S11 2WD BS IV | 15,214 km | Diesel | Manual",
                    "km": "15,214 km",
                    "fuel": "Diesel",
                    "transmission": "Manual",
                    "price": 1950000,
                    "emi": "Rs. 52,557/month",
                    "locality": "Cyberabad, Hyderabad",
                    "owner_text": "First Owner",
                    "registration": "TS07AB1234",
                    "seller_type": "Dealer",
                    "body_type": "SUV",
                    "color": "Black",
                    "dealer_name": "Mahindra First Choice Dealer",
                    "listing_posted_at": "2026-02-22",
                    "listing_url": "https://www.mahindrafirstchoice.com/buyer/detail/hyderabad-mahindra-242953",
                    "is_certified": True,
                    "warranty_label": "1 year warranty",
                }
            }
        ],
    }


def true_value_live_payload(*, captured_at: str) -> dict:
    return {
        "source": "true_value",
        "source_url": "https://www.marutisuzukitruevalue.com/buy-car",
        "captured_for": "live_public_search_capture",
        "capture_method": "dealer_discovery_plus_graphql",
        "captured_at": captured_at,
        "city": "Hyderabad",
        "state": "Telangana",
        "dealer_discovery": {
            "dealers_total": 21,
            "dealer_ids": ["50449-HBS-VARUN"],
        },
        "pagination": {
            "pagination_type": "dealer_discovery_plus_graphql",
            "max_pages": 1,
            "attempted_pages": 1,
            "page_size": 100,
            "max_records": 1,
            "min_records": 1,
            "coverage_ok": True,
            "unique_cards_seen": 1,
            "returned_records": 1,
            "duplicate_cards_skipped": 0,
            "source_total_items": 247,
            "source_total_pages": 3,
            "dealer_count": 21,
            "dealer_distance_m": 25000,
            "stop_reason": "record_cap_reached",
        },
        "records": [
            {
                "raw": {
                    "sku": "true-value-123",
                    "title": "2024 Maruti Suzuki Baleno",
                    "model_year": 2024,
                    "brand": "Maruti Suzuki",
                    "model": "Baleno",
                    "variant": "Zeta Petrol",
                    "price": 795000,
                    "currency": "INR",
                    "km": "14,200 km",
                    "fuel": "Petrol",
                    "transmission": "Manual",
                    "ownership": "1st Owner",
                    "owner_text": "1st Owner",
                    "registration": "TS08",
                    "registration_date": "2024",
                    "locality": "Kukatpally",
                    "city": "Hyderabad",
                    "state": "Telangana",
                    "body_type": "Hatchback",
                    "color": "Nexa Blue",
                    "dealer_name": "Varun Motors True Value",
                    "dealer_location": "Kukatpally",
                    "dealer_code": "50449-HBS-VARUN",
                    "true_value_certified": "true",
                    "dms_certification_status": "CR",
                    "overall_rating": "4.4",
                    "warranty_info": "1Y",
                    "listing_url": "https://www.marutisuzukitruevalue.com/buy-car/baleno-2024-zeta-true-value-123",
                    "in_stock": True,
                    "mssf_finance": "1",
                    "fmp_emi_amount": "17200",
                }
            }
        ],
    }


def cli_comparison_record(source: str, source_listing_id: str, registration_code: str | None) -> dict:
    return {
        "source": source,
        "source_listing_id": source_listing_id,
        "listing_url": f"https://example.com/{source_listing_id}",
        "captured_at": "2026-06-25T00:00:00Z",
        "city": "Hyderabad",
        "state": "Telangana",
        "locality": "Hyderabad",
        "brand": "Maruti Suzuki",
        "model": "Swift",
        "variant": "VXI",
        "model_year": 2022,
        "fuel_type": "petrol",
        "transmission": "manual",
        "km_driven": 10000,
        "ownership": 1,
        "registration_code": registration_code,
        "listed_price_inr": 600000,
        "currency": "INR",
        "seller_type": "dealer",
        "is_certified": True,
        "is_available": True,
        "source_record_type": "listing",
        "raw_record_hash": "hash",
        "ingestion_run_id": "run",
        "parser_version": "test",
        "schema_version": "canonical_listing_v0.1",
        "parse_confidence": 1.0,
        "parse_warnings": [],
        "extra_fields": {},
    }


def cli_lifecycle_entity(listing_key: str, source: str) -> dict:
    return {
        "listing_key": listing_key,
        "source": source,
        "observation_count": 1,
        "first_seen_at": "2026-06-26T01:00:00Z",
        "last_seen_at": "2026-06-26T01:00:00Z",
        "capture_dates": ["2026-06-26"],
        "run_ids": ["run_current"],
        "latest_observation": {
            "listing_key": listing_key,
            "source": source,
            "source_listing_id": listing_key,
            "listing_url": f"https://example.com/{listing_key}",
            "run_id": "run_current",
            "capture_date": "2026-06-26",
            "captured_at": "2026-06-26T01:00:00Z",
            "city": "Hyderabad",
            "state": "Telangana",
            "brand": "Maruti Suzuki",
            "model": "Wagon R",
            "variant": "VXI",
            "model_year": 2022,
            "fuel_type": "petrol",
            "transmission": "manual",
            "km_driven": 10000,
            "ownership": 1,
            "registration_code": "TS07",
            "listed_price_inr": 500000,
            "is_available": True,
        },
    }


def write_cli_summary(path: Path, source: str) -> None:
    path.write_text(
        json.dumps(
            {
                "source": source,
                "records_total": 1,
                "silver_valid": 1,
                "pricing_ready": 1,
                "quarantined": 0,
                "required_completeness_avg": 1.0,
                "high_value_completeness_avg": 0.8571,
                "optional_completeness_avg": 0.2,
                "overall_completeness_avg": 0.9,
                "quarantine_reasons": {},
                "warnings": {},
            }
        ),
        encoding="utf-8",
    )


def write_cli_manifest(path: Path, source: str, run_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "source": source,
                "source_url": f"https://example.com/{source}",
                "run_id": run_id,
                "city": "Hyderabad",
                "duration_seconds": 1.2,
                "listing_capture": {
                    "pagination_type": "test",
                    "attempted_pages": 1,
                    "unique_cards_seen": 1,
                    "returned_records": 1,
                },
                "record_counts": {
                    "detail_requested": 0,
                    "detail_successful": 0,
                },
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
