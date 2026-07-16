import unittest
from tempfile import TemporaryDirectory

from used_car_price_intelligence.pipeline import run_fixture_pipeline, write_fixture_outputs


class FixtureRunnerTests(unittest.TestCase):
    def test_spinny_fixture_runner_returns_quality_summary(self) -> None:
        records, results, summary = run_fixture_pipeline(
            source="spinny",
            fixture_path="tests/fixtures/spinny/listing_cards_extracted.json",
            captured_at="2026-06-24T03:00:00Z",
            ingestion_run_id="run_20260624_spinny_fixture_test",
        )

        self.assertEqual(len(records), 5)
        self.assertEqual(len(results), 5)
        self.assertEqual(summary.records_total, 5)
        self.assertEqual(summary.silver_valid, 5)
        self.assertEqual(summary.pricing_ready, 5)
        self.assertEqual(summary.quarantined, 0)
        self.assertEqual(summary.required_completeness_avg, 1.0)
        self.assertEqual(summary.quarantine_reasons, {})

    def test_mahindra_first_choice_fixture_runner_returns_quality_summary(self) -> None:
        records, results, summary = run_fixture_pipeline(
            source="mahindra_first_choice",
            fixture_path="tests/fixtures/mahindra_first_choice/listing_cards_extracted.json",
            captured_at="2026-06-25T03:30:00Z",
            ingestion_run_id="run_20260625_mfc_fixture_test",
        )

        self.assertEqual(len(records), 9)
        self.assertEqual(len(results), 9)
        self.assertEqual(summary.records_total, 9)
        self.assertEqual(summary.silver_valid, 9)
        self.assertEqual(summary.pricing_ready, 9)
        self.assertEqual(summary.quarantined, 0)
        self.assertEqual(summary.required_completeness_avg, 1.0)
        self.assertLess(summary.high_value_completeness_avg, 1.0)
        self.assertEqual(summary.quarantine_reasons, {})

    def test_true_value_fixture_runner_returns_quality_summary(self) -> None:
        records, results, summary = run_fixture_pipeline(
            source="true_value",
            fixture_path="tests/fixtures/true_value/listing_cards_extracted.json",
            captured_at="2026-06-25T11:00:00Z",
            ingestion_run_id="run_20260625_true_value_fixture_test",
        )

        self.assertEqual(len(records), 8)
        self.assertEqual(len(results), 8)
        self.assertEqual(summary.records_total, 8)
        self.assertEqual(summary.silver_valid, 8)
        self.assertEqual(summary.pricing_ready, 8)
        self.assertEqual(summary.quarantined, 0)
        self.assertEqual(summary.required_completeness_avg, 1.0)
        self.assertEqual(summary.high_value_completeness_avg, 1.0)
        self.assertEqual(summary.quarantine_reasons, {})

    def test_rejects_unsupported_fixture_source(self) -> None:
        with self.assertRaises(ValueError):
            run_fixture_pipeline(
                source="olx",
                fixture_path="tests/fixtures/olx/listing_cards_extracted.json",
                captured_at="2026-06-24T03:00:00Z",
                ingestion_run_id="run_20260624_olx_fixture_test",
            )

    def test_spinny_live_fixture_snapshot_is_pricing_ready(self) -> None:
        records, results, summary = run_fixture_pipeline(
            source="spinny",
            fixture_path="tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json",
            captured_at="2026-06-24T04:00:00Z",
            ingestion_run_id="run_20260624_spinny_live_fixture_test",
        )

        self.assertEqual(len(records), 20)
        self.assertEqual(len(results), 20)
        self.assertEqual(summary.records_total, 20)
        self.assertEqual(summary.silver_valid, 20)
        self.assertEqual(summary.pricing_ready, 20)
        self.assertEqual(summary.quarantined, 0)
        self.assertEqual(summary.warnings, {"multiple_price_candidates": 2})

    def test_writes_fixture_outputs(self) -> None:
        records, results, summary = run_fixture_pipeline(
            source="spinny",
            fixture_path="tests/fixtures/spinny/listing_cards_extracted.json",
            captured_at="2026-06-24T03:00:00Z",
            ingestion_run_id="run_20260624_spinny_fixture_test",
        )

        with TemporaryDirectory() as tmpdir:
            paths = write_fixture_outputs(
                records=records,
                results=results,
                summary=summary,
                fixture_path="tests/fixtures/spinny/listing_cards_extracted.json",
                output_root=tmpdir,
                capture_date="2026-06-24",
                run_id="run_20260624_spinny_fixture_test",
            )

            self.assertTrue(paths.raw.exists())
            self.assertTrue(paths.silver.exists())
            self.assertTrue(paths.quarantine.exists())
            self.assertTrue(paths.quality_summary.exists())
            self.assertIn("source=spinny", str(paths.raw))
            self.assertIn("quality_summary", str(paths.quality_summary))


if __name__ == "__main__":
    unittest.main()
