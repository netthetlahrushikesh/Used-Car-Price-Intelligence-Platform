import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.reporting import (
    load_source_run_profile,
    render_multi_source_comparison_report,
    render_source_comparison_report,
    write_source_comparison_report,
)


class SourceComparisonTests(unittest.TestCase):
    def test_renders_source_comparison_from_silver_artifacts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            left = write_artifacts(
                root=root,
                source="spinny",
                run_id="run_spinny",
                record=base_record(
                    source="spinny",
                    source_listing_id="spinny_1",
                    registration_code="TS07",
                    ownership=1,
                    body_type=None,
                    dealer_name=None,
                    extra_fields={"spinny_detail": {"inspection_summary": "1452 parts evaluated"}},
                ),
            )
            right = write_artifacts(
                root=root,
                source="mahindra_first_choice",
                run_id="run_mfc",
                record=base_record(
                    source="mahindra_first_choice",
                    source_listing_id="mfc_1",
                    registration_code=None,
                    ownership=1,
                    body_type="SUV",
                    dealer_name="MFC Dealer",
                    extra_fields={"mahindra_first_choice": {"rating_score": 8.1}},
                ),
            )

            left_profile = load_source_run_profile(source="spinny", **left)
            right_profile = load_source_run_profile(source="mahindra_first_choice", **right)
            report = render_source_comparison_report(
                left_profile,
                right_profile,
                title="Spinny vs MFC",
                generated_at="2026-06-25",
                recommendation="Add True Value as the third source contract before large-scale scraping.",
            )

        self.assertIn("# Spinny vs MFC", report)
        self.assertIn("| `registration_code` | 1/1 (100.00%) | 0/1 (0.00%) | source-specific gap |", report)
        self.assertIn("| `body_type` | 0/1 (0.00%) | 1/1 (100.00%) | source-specific gap |", report)
        self.assertIn("| `spinny_detail.inspection_summary` | 1/1 (100.00%) | n/a |", report)
        self.assertIn("Add True Value as the third source contract", report)

    def test_renders_multi_source_comparison_from_silver_artifacts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            spinny = write_artifacts(
                root=root,
                source="spinny",
                run_id="run_spinny",
                record=base_record(
                    source="spinny",
                    source_listing_id="spinny_1",
                    registration_code="TS07",
                    ownership=1,
                    body_type=None,
                    dealer_name=None,
                    extra_fields={"spinny_detail": {"inspection_summary": "1452 parts evaluated"}},
                ),
            )
            mfc = write_artifacts(
                root=root,
                source="mahindra_first_choice",
                run_id="run_mfc",
                record=base_record(
                    source="mahindra_first_choice",
                    source_listing_id="mfc_1",
                    registration_code=None,
                    ownership=1,
                    body_type="SUV",
                    dealer_name="MFC Dealer",
                    extra_fields={"mahindra_first_choice": {"rating_score": 8.1}},
                ),
            )
            true_value = write_artifacts(
                root=root,
                source="true_value",
                run_id="run_true_value",
                record=base_record(
                    source="true_value",
                    source_listing_id="true_value_1",
                    registration_code="TS08",
                    ownership=1,
                    body_type="Hatchback",
                    dealer_name="True Value Dealer",
                    extra_fields={"true_value": {"overall_rating": "4.4"}},
                ),
            )

            profiles = [
                load_source_run_profile(source="spinny", **spinny),
                load_source_run_profile(source="mahindra_first_choice", **mfc),
                load_source_run_profile(source="true_value", **true_value),
            ]
            report = render_multi_source_comparison_report(
                profiles,
                title="Three Source Comparison",
                generated_at="2026-06-25",
                recommendation="Build the batch runner next.",
            )

        self.assertIn("# Three Source Comparison", report)
        self.assertIn("| Metric | Spinny | Mahindra First Choice | True Value |", report)
        self.assertIn("| `registration_code` | 1/1 (100.00%) | 0/1 (0.00%) | 1/1 (100.00%) | source-specific gap |", report)
        self.assertIn("| `true_value.overall_rating` | n/a | n/a | 1/1 (100.00%) |", report)
        self.assertIn("Build the batch runner next.", report)

    def test_writes_source_comparison_report(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.md"
            written = write_source_comparison_report(path, "# Report\n")

            self.assertEqual(written, path)
            self.assertEqual(path.read_text(encoding="utf-8"), "# Report\n")


def write_artifacts(*, root: Path, source: str, run_id: str, record: dict) -> dict:
    silver_path = root / f"{source}_silver.json"
    quality_summary_path = root / f"{source}_quality.json"
    manifest_path = root / f"{source}_manifest.json"
    silver_path.write_text(json.dumps([record]), encoding="utf-8")
    quality_summary_path.write_text(
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
    manifest_path.write_text(
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
    return {
        "silver_path": silver_path,
        "quality_summary_path": quality_summary_path,
        "manifest_path": manifest_path,
    }


def base_record(
    *,
    source: str,
    source_listing_id: str,
    registration_code: str | None,
    ownership: int | None,
    body_type: str | None,
    dealer_name: str | None,
    extra_fields: dict,
) -> dict:
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
        "ownership": ownership,
        "registration_code": registration_code,
        "body_type": body_type,
        "listed_price_inr": 600000,
        "currency": "INR",
        "seller_type": "dealer",
        "dealer_name": dealer_name,
        "is_certified": True,
        "is_available": True,
        "source_record_type": "listing",
        "raw_record_hash": "hash",
        "ingestion_run_id": "run",
        "parser_version": "test",
        "schema_version": "canonical_listing_v0.1",
        "parse_confidence": 1.0,
        "parse_warnings": [],
        "extra_fields": extra_fields,
    }


if __name__ == "__main__":
    unittest.main()
