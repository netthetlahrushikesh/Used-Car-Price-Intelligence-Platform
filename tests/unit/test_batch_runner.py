import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.pipeline import (
    BatchJob,
    BatchRunPlan,
    build_batch_run_plan,
    default_batch_manifest_path,
    load_batch_manifest,
    passed_jobs_from_manifest,
    render_batch_summary_report,
    run_batch_plan,
    write_batch_manifest,
)


class BatchRunnerTests(unittest.TestCase):
    def test_builds_validated_batch_plan_from_config(self) -> None:
        plan = build_batch_run_plan(
            config_path="config/acquisition_batches.yml",
            capture_date="2026-06-25",
            batch_run_id="batch_test",
            output_root="data",
            statuses=["validated"],
            python_executable="python",
        )

        self.assertEqual(plan.batch_run_id, "batch_test")
        self.assertEqual([job.batch_id for job in plan.jobs], [
            "spinny_hyderabad_60_detail60",
            "mfc_hyderabad_40",
            "true_value_hyderabad_40",
            "spinny_bengaluru_60_detail60",
            "spinny_delhi_ncr_60_detail60",
            "spinny_mumbai_60_detail60",
            "spinny_chennai_60_detail60",
            "mfc_bengaluru_80",
            "mfc_delhi_ncr_80",
            "mfc_mumbai_80",
            "mfc_chennai_80",
            "true_value_bengaluru_100",
            "true_value_delhi_ncr_100",
            "true_value_mumbai_100",
            "true_value_chennai_100",
        ])
        self.assertEqual(plan.jobs[0].source, "spinny")
        self.assertIn("spinny-live-smoke", plan.jobs[0].command)
        self.assertIn("--locality", plan.jobs[0].command)
        self.assertIn("Hyderabad", plan.jobs[0].command)
        self.assertIn("mfc-live-smoke", plan.jobs[1].command)
        self.assertIn("true-value-live-smoke", plan.jobs[2].command)
        self.assertTrue(plan.jobs[2].payload_output.endswith("_payload.json"))

    def test_builds_specific_true_value_batch_plan(self) -> None:
        plan = build_batch_run_plan(
            config_path="config/acquisition_batches.yml",
            capture_date="2026-06-25",
            batch_run_id="batch_test",
            output_root="data",
            batch_ids=["true_value_hyderabad_40"],
            python_executable="python",
        )

        self.assertEqual(len(plan.jobs), 1)
        command = plan.jobs[0].command
        self.assertEqual(plan.jobs[0].source, "true_value")
        self.assertIn("--dealer-distance-m", command)
        self.assertIn("25000", command)
        self.assertIn("--page-size", command)
        self.assertIn("100", command)

    def test_builds_mfc_5k_probe_plan_from_status(self) -> None:
        plan = build_batch_run_plan(
            config_path="config/acquisition_batches.yml",
            capture_date="2026-06-26",
            batch_run_id="batch_5k_probe_test",
            output_root="data",
            statuses=["mfc_5k_probe"],
            python_executable="python",
        )

        self.assertEqual(len(plan.jobs), 12)
        self.assertEqual(plan.jobs[0].batch_id, "mfc_pune_80_probe")
        self.assertTrue(all(job.source == "mahindra_first_choice" for job in plan.jobs))
        self.assertTrue(all("mfc-live-smoke" in job.command for job in plan.jobs))
        self.assertTrue(all("--min-records" in job.command for job in plan.jobs))

    def test_builds_true_value_5k_buffer_plan_from_status(self) -> None:
        plan = build_batch_run_plan(
            config_path="config/acquisition_batches.yml",
            capture_date="2026-06-27",
            batch_run_id="batch_true_value_buffer_test",
            output_root="data",
            statuses=["true_value_5k_buffer"],
            python_executable="python",
        )

        self.assertEqual(
            [job.batch_id for job in plan.jobs],
            [
                "true_value_mysuru_40_5k_buffer",
                "true_value_mangaluru_40_5k_buffer",
                "true_value_madurai_40_5k_buffer",
                "true_value_vijayawada_40_5k_buffer",
                "true_value_rajkot_40_5k_buffer",
            ],
        )
        self.assertTrue(all(job.source == "true_value" for job in plan.jobs))
        self.assertTrue(all(job.allow_zero_inventory for job in plan.jobs))
        self.assertTrue(all("true-value-live-smoke" in job.command for job in plan.jobs))
        self.assertTrue(all("--max-records" in job.command for job in plan.jobs))

    def test_dry_run_batch_plan_writes_planned_manifest(self) -> None:
        plan = build_batch_run_plan(
            config_path="config/acquisition_batches.yml",
            capture_date="2026-06-25",
            batch_run_id="batch_test",
            output_root="data",
            batch_ids=["mfc_hyderabad_40"],
            python_executable="python",
        )
        manifest = run_batch_plan(plan, execute=False)

        self.assertEqual(manifest["status"], "planned")
        self.assertEqual(manifest["job_count"], 1)
        self.assertEqual(manifest["job_results"][0]["status"], "planned")
        self.assertIsNone(manifest["job_results"][0]["exit_code"])

        with TemporaryDirectory() as tmpdir:
            path = default_batch_manifest_path(
                output_root=tmpdir,
                capture_date="2026-06-25",
                batch_run_id="batch_test",
            )
            written = write_batch_manifest(path, manifest)

            self.assertEqual(written, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "planned")

    def test_execute_can_skip_previously_passed_batch_jobs(self) -> None:
        plan = build_batch_run_plan(
            config_path="config/acquisition_batches.yml",
            capture_date="2026-06-25",
            batch_run_id="batch_resume_test",
            output_root="data",
            batch_ids=["mfc_hyderabad_40"],
            python_executable="python",
        )
        manifest = run_batch_plan(
            plan,
            execute=True,
            skip_passed_jobs={
                "mfc_hyderabad_40": {
                    "batch_id": "mfc_hyderabad_40",
                    "run_id": "run_previous_mfc",
                    "status": "pass",
                    "exit_code": 0,
                }
            },
            resume_manifest_path="previous_batch_manifest.json",
        )

        self.assertEqual(manifest["status"], "pass")
        self.assertEqual(manifest["jobs_executed"], 0)
        self.assertEqual(manifest["jobs_skipped"], 1)
        self.assertEqual(manifest["job_results"][0]["status"], "skipped_passed")
        self.assertEqual(manifest["job_results"][0]["resumed_from_run_id"], "run_previous_mfc")

    def test_execute_can_continue_after_allowed_zero_inventory_job(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "data"
            run_id = "run_zero_inventory"
            source_manifest = (
                output_root
                / "gold"
                / "acquisition_runs"
                / "capture_date=2026-06-26"
                / f"mahindra_first_choice_{run_id}_manifest.json"
            )
            source_manifest.parent.mkdir(parents=True, exist_ok=True)
            source_manifest.write_text(
                json.dumps(
                    {
                        "status": "fail",
                        "source": "mahindra_first_choice",
                        "run_id": run_id,
                        "capture_date": "2026-06-26",
                        "city": "Vadodara",
                        "listing_capture": {
                            "records_total": 0,
                            "source_total_items": 0,
                            "stop_reason": "source_max_page_reached",
                        },
                        "listing_coverage": {
                            "ok": False,
                            "reason": "records_below_minimum",
                        },
                    }
                ),
                encoding="utf-8",
            )
            plan = BatchRunPlan(
                batch_run_id="batch_zero_inventory",
                capture_date="2026-06-26",
                config_path="config/acquisition_batches.yml",
                jobs=[
                    BatchJob(
                        batch_id="mfc_vadodara_80_probe",
                        source="mahindra_first_choice",
                        status="mfc_5k_probe",
                        city="Vadodara",
                        state="Gujarat",
                        url="https://www.mahindrafirstchoice.com/used-cars/vadodara",
                        run_id=run_id,
                        capture_date="2026-06-26",
                        payload_output=str(output_root / "tmp" / "payload.json"),
                        command=[sys.executable, "-c", "import sys; sys.exit(1)"],
                        output_root=str(output_root),
                        allow_zero_inventory=True,
                    )
                ],
            )

            manifest = run_batch_plan(plan, execute=True, cwd=root)

        self.assertEqual(manifest["status"], "pass")
        self.assertEqual(manifest["jobs_executed"], 1)
        self.assertEqual(manifest["job_results"][0]["status"], "no_inventory")
        self.assertEqual(manifest["job_results"][0]["exit_code"], 0)

    def test_extracts_passed_jobs_from_manifest(self) -> None:
        manifest = {
            "job_results": [
                {
                    "batch_id": "spinny_hyderabad_60_detail60",
                    "run_id": "run_spinny",
                    "status": "pass",
                    "exit_code": 0,
                },
                {
                    "batch_id": "mfc_hyderabad_40",
                    "run_id": "run_mfc",
                    "status": "fail",
                    "exit_code": 1,
                },
                {
                    "batch_id": "mfc_vadodara_80_probe",
                    "run_id": "run_zero_inventory",
                    "status": "no_inventory",
                    "exit_code": 0,
                },
            ]
        }

        passed = passed_jobs_from_manifest(manifest)

        self.assertEqual(list(passed), ["spinny_hyderabad_60_detail60", "mfc_vadodara_80_probe"])
        self.assertEqual(passed["spinny_hyderabad_60_detail60"]["run_id"], "run_spinny")
        self.assertEqual(passed["mfc_vadodara_80_probe"]["run_id"], "run_zero_inventory")

    def test_loads_batch_manifest_from_disk(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.json"
            path.write_text(json.dumps({"job_results": []}), encoding="utf-8")

            self.assertEqual(load_batch_manifest(path), {"job_results": []})

    def test_renders_batch_summary_with_nested_source_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir) / "data"
            source_manifest = (
                output_root
                / "gold"
                / "acquisition_runs"
                / "capture_date=2026-06-25"
                / "true_value_run_true_value_test_manifest.json"
            )
            source_manifest.parent.mkdir(parents=True, exist_ok=True)
            source_manifest.write_text(
                json.dumps(
                    {
                        "city": "Hyderabad",
                        "duration_seconds": 3.2,
                        "quality_summary": {
                            "pricing_ready": 40,
                            "quarantined": 0,
                            "required_completeness_avg": 1.0,
                            "high_value_completeness_avg": 1.0,
                        },
                        "listing_capture": {"source_total_items": 247},
                    }
                ),
                encoding="utf-8",
            )
            report = render_batch_summary_report(
                {
                    "batch_run_id": "batch_summary_test",
                    "capture_date": "2026-06-25",
                    "status": "pass",
                    "execute": True,
                    "job_count": 1,
                    "jobs_executed": 1,
                    "jobs_skipped": 0,
                    "jobs_planned": [
                        {
                            "batch_id": "true_value_hyderabad_40",
                            "source": "true_value",
                            "city": "Hyderabad",
                        }
                    ],
                    "job_results": [
                        {
                            "batch_id": "true_value_hyderabad_40",
                            "source": "true_value",
                            "run_id": "run_true_value_test",
                            "status": "pass",
                            "exit_code": 0,
                        }
                    ],
                },
                output_root=output_root,
            )

        self.assertIn("# Batch Run Summary", report)
        self.assertIn("| true_value_hyderabad_40 | true_value | Hyderabad | pass | 40 | 0 | 100.00%", report)
        self.assertIn("| true_value | 40 | 0 |", report)


if __name__ == "__main__":
    unittest.main()
