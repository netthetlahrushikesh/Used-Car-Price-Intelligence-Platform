from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.reporting import (
    default_smoke_report_path,
    render_smoke_report,
    write_smoke_report,
)


class SmokeReportTests(unittest.TestCase):
    def test_renders_passing_smoke_report_with_field_gaps(self) -> None:
        report = render_smoke_report(_passing_smoke_result())

        self.assertIn("Status: PASS", report)
        self.assertIn("Source: spinny", report)
        self.assertIn("- records: 20 total | 20 silver-valid | 20 pricing-ready | 0 quarantined", report)
        self.assertIn("Required fields below 100%:\n- none", report)
        self.assertIn("- ownership: 0/20 (0.00%)", report)

    def test_renders_failed_contract_report_without_quality_gates(self) -> None:
        smoke_result = {
            "source": "spinny",
            "source_url": "https://www.spinny.com/example",
            "run_id": "run_failure_test",
            "captured_at": "2026-06-24T05:45:00Z",
            "payload_output": "data/tmp/failure.json",
            "payload_validation": {
                "source": "spinny",
                "records_total": 1,
                "ok": False,
                "failures": [
                    {
                        "record_index": 1,
                        "field_name": "price",
                        "reason": "missing_required_raw_field",
                    }
                ],
            },
            "ok": False,
        }

        report = render_smoke_report(smoke_result)

        self.assertIn("Status: FAIL", report)
        self.assertIn("- record=1 field=price reason=missing_required_raw_field", report)
        self.assertIn("- skipped: payload contract did not pass", report)

    def test_renders_detail_enrichment_counts(self) -> None:
        smoke_result = _passing_smoke_result()
        smoke_result["detail_enrichment"] = {
            "ok": True,
            "requested_records": 3,
            "attempted_records": 3,
            "records_total": 3,
            "successful_records": 3,
            "failed_records": 0,
            "ownership_records": 3,
            "retries_used": 1,
            "timeout_count": 0,
            "empty_raw_count": 0,
        }

        report = render_smoke_report(smoke_result)

        self.assertIn("Detail Enrichment:", report)
        self.assertIn("- ok: True", report)
        self.assertIn("- requested_records: 3", report)
        self.assertIn("- successful_records: 3", report)
        self.assertIn("- failed_records: 0", report)
        self.assertIn("- ownership_records: 3", report)
        self.assertIn("- records_total: 3", report)

    def test_renders_listing_capture_summary(self) -> None:
        smoke_result = _passing_smoke_result()
        smoke_result["listing_capture"] = {
            "pagination_type": "infinite_scroll_batches",
            "max_pages": 2,
            "attempted_pages": 2,
            "max_records": 40,
            "min_records": 40,
            "coverage_ok": True,
            "records_total": 40,
            "unique_cards_seen": 42,
            "duplicate_cards_skipped": 22,
            "stop_reason": "record_cap_reached",
        }

        report = render_smoke_report(smoke_result)

        self.assertIn("Listing Capture:", report)
        self.assertIn("- pagination_type: infinite_scroll_batches", report)
        self.assertIn("- max_pages: 2", report)
        self.assertIn("- min_records: 40", report)
        self.assertIn("- coverage_ok: True", report)
        self.assertIn("- records_total: 40", report)
        self.assertIn("- stop_reason: record_cap_reached", report)

    def test_renders_listing_coverage_failure(self) -> None:
        smoke_result = _passing_smoke_result()
        smoke_result["ok"] = False
        smoke_result["quality_summary"] = None
        smoke_result["quality_skip_reason"] = "listing coverage did not meet min_records"
        smoke_result["listing_coverage"] = {
            "ok": False,
            "min_records": 40,
            "records_total": 22,
            "missing_records": 18,
            "reason": "records_below_minimum",
        }

        report = render_smoke_report(smoke_result)

        self.assertIn("Status: FAIL", report)
        self.assertIn("Listing Coverage:", report)
        self.assertIn("- ok: False", report)
        self.assertIn("- missing_records: 18", report)
        self.assertIn("- skipped: listing coverage did not meet min_records", report)

    def test_writes_report_to_default_path(self) -> None:
        with TemporaryDirectory() as tmpdir:
            report_path = default_smoke_report_path(
                output_root=tmpdir,
                capture_date="2026-06-24",
                source="spinny",
                run_id="run_smoke_test",
            )
            written_path = write_smoke_report(report_path, _passing_smoke_result())
            expected_path = (
                Path(tmpdir)
                / "gold"
                / "smoke_reports"
                / "capture_date=2026-06-24"
                / "spinny_run_smoke_test_smoke_report.md"
            )

            self.assertEqual(str(written_path), str(expected_path))
            self.assertTrue(expected_path.exists())
            self.assertIn("Status: PASS", expected_path.read_text(encoding="utf-8"))


def _passing_smoke_result() -> dict[str, object]:
    return {
        "source": "spinny",
        "source_url": "https://www.spinny.com/example",
        "run_id": "run_smoke_test",
        "capture_date": "2026-06-24",
        "captured_at": "2026-06-24T05:45:00Z",
        "payload_output": "data/tmp/payload.json",
        "payload_validation": {
            "source": "spinny",
            "records_total": 20,
            "ok": True,
            "failures": [],
        },
        "quality_summary": {
            "source": "spinny",
            "records_total": 20,
            "silver_valid": 20,
            "pricing_ready": 20,
            "quarantined": 0,
            "required_completeness_avg": 1.0,
            "high_value_completeness_avg": 0.8571,
            "optional_completeness_avg": 0.2333,
            "overall_completeness_avg": 0.8948,
            "quarantine_reasons": {},
            "warnings": {},
        },
        "field_profile": {
            "source": "spinny",
            "records_total": 20,
            "fields": [
                {
                    "field_name": "listed_price_inr",
                    "field_group": "required",
                    "present_count": 20,
                    "total_count": 20,
                    "completeness": 1.0,
                },
                {
                    "field_name": "ownership",
                    "field_group": "high_value",
                    "present_count": 0,
                    "total_count": 20,
                    "completeness": 0.0,
                },
            ],
        },
        "output_paths": {
            "raw": "data/raw/source=spinny/capture_date=2026-06-24/run_id=run_smoke_test/fixture_source_payload.json",
            "silver": "data/silver/listings/capture_date=2026-06-24/spinny_run_smoke_test_silver.json",
            "quarantine": "data/silver/quarantine/source=spinny/capture_date=2026-06-24/run_smoke_test_quarantine.json",
            "quality_summary": "data/gold/quality_summary/capture_date=2026-06-24/spinny_run_smoke_test_quality_summary.json",
            "smoke_report": "data/gold/smoke_reports/capture_date=2026-06-24/spinny_run_smoke_test_smoke_report.md",
        },
        "ok": True,
    }


if __name__ == "__main__":
    unittest.main()
