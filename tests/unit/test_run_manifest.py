import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.pipeline import (
    build_incremental_detail_run_manifest,
    build_run_manifest,
    default_run_manifest_path,
    write_run_manifest,
)


class RunManifestTests(unittest.TestCase):
    def test_builds_compact_manifest_from_smoke_result(self) -> None:
        smoke_result = {
            "ok": True,
            "source": "spinny",
            "source_url": "https://www.spinny.com/example/s/",
            "run_id": "run_manifest_test",
            "capture_date": "2026-06-25",
            "captured_at": "2026-06-25T06:45:00Z",
            "payload_validation": {"records_total": 60, "ok": True},
            "listing_capture": {"records_total": 60, "max_pages": 3},
            "listing_coverage": {"ok": True, "min_records": 60},
            "detail_enrichment": {
                "requested_records": 60,
                "successful_records": 60,
                "failed_records": 0,
            },
            "quality_summary": {
                "pricing_ready": 60,
                "quarantined": 0,
                "required_completeness_avg": 1.0,
            },
            "output_paths": {"smoke_report": "data/gold/report.md"},
        }

        manifest = build_run_manifest(
            smoke_result=smoke_result,
            city="Hyderabad",
            state="Telangana",
            started_at="2026-06-25T06:44:00Z",
            completed_at="2026-06-25T06:49:00Z",
            duration_seconds=300.1234,
            run_options={"max_records": 60, "detail_pages": 60},
        )

        self.assertEqual(manifest["status"], "pass")
        self.assertEqual(manifest["city"], "Hyderabad")
        self.assertEqual(manifest["record_counts"]["listing_records"], 60)
        self.assertEqual(manifest["record_counts"]["detail_successful"], 60)
        self.assertEqual(manifest["record_counts"]["pricing_ready"], 60)
        self.assertEqual(manifest["duration_seconds"], 300.123)

    def test_writes_manifest_to_gold_partition(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = default_run_manifest_path(
                output_root=tmpdir,
                capture_date="2026-06-25",
                source="spinny",
                run_id="run_manifest_test",
            )
            written = write_run_manifest(path, {"status": "pass"})

            expected = (
                Path(tmpdir)
                / "gold"
                / "acquisition_runs"
                / "capture_date=2026-06-25"
                / "spinny_run_manifest_test_manifest.json"
            )
            self.assertEqual(written, expected)
            self.assertEqual(json.loads(expected.read_text(encoding="utf-8"))["status"], "pass")

    def test_builds_incremental_detail_manifest_with_cache_metrics(self) -> None:
        manifest = build_incremental_detail_run_manifest(
            source="spinny",
            source_url="https://www.spinny.com/example/s/",
            city="Hyderabad",
            state="Telangana",
            run_id="run_spinny_incremental",
            capture_date="2026-06-27",
            captured_at="2026-06-27T03:00:00Z",
            started_at="2026-06-27T02:54:00Z",
            completed_at="2026-06-27T02:58:00Z",
            duration_seconds=None,
            run_options={"workflow": "spinny_incremental_detail", "max_new_records": 20},
            listing_capture={"records_total": 80, "min_records": 60},
            listing_coverage={"ok": True, "reason": "ok"},
            detail_plan={
                "unique_listing_urls": 80,
                "cache_hit_count": 50,
                "pending_count": 30,
                "selected_new_count": 20,
                "skipped_over_new_cap": 10,
            },
            detail_enrichment={
                "attempted_records": 70,
                "successful_records": 70,
                "failed_records": 0,
                "incremental_policy": {
                    "cache_reused_records": 50,
                    "new_records_used": 20,
                    "missing_after_merge": 10,
                },
            },
            quality_summary={
                "records_total": 80,
                "pricing_ready": 80,
                "quarantined": 0,
                "required_completeness_avg": 1.0,
            },
            output_paths={"silver": "data/silver/listings/example.json"},
        )

        self.assertEqual(manifest["status"], "pass")
        self.assertIsNone(manifest["duration_seconds"])
        self.assertEqual(manifest["record_counts"]["listing_records"], 80)
        self.assertEqual(manifest["record_counts"]["detail_successful"], 70)
        self.assertEqual(manifest["record_counts"]["detail_cache_hits"], 50)
        self.assertEqual(manifest["record_counts"]["detail_new_records_used"], 20)
        self.assertEqual(manifest["record_counts"]["detail_missing_after_merge"], 10)

    def test_incremental_detail_manifest_fails_when_quality_drops_rows(self) -> None:
        manifest = build_incremental_detail_run_manifest(
            source="spinny",
            source_url="https://www.spinny.com/example/s/",
            city="Hyderabad",
            state="Telangana",
            run_id="run_spinny_incremental",
            capture_date="2026-06-27",
            captured_at="2026-06-27T03:00:00Z",
            started_at="2026-06-27T02:54:00Z",
            completed_at="2026-06-27T02:58:00Z",
            duration_seconds=240.0,
            run_options={},
            listing_capture={"records_total": 80},
            listing_coverage={"ok": True},
            detail_plan={"unique_listing_urls": 80},
            detail_enrichment={"attempted_records": 80, "successful_records": 80, "failed_records": 0},
            quality_summary={"records_total": 80, "pricing_ready": 79, "quarantined": 1},
            output_paths={"silver": "data/silver/listings/example.json"},
        )

        self.assertEqual(manifest["status"], "fail")


if __name__ == "__main__":
    unittest.main()
