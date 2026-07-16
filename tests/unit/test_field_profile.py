import unittest

from used_car_price_intelligence.pipeline import run_fixture_pipeline
from used_car_price_intelligence.reporting import (
    profile_field_completeness,
    render_field_profile,
)


class FieldProfileTests(unittest.TestCase):
    def test_profiles_live_spinny_fixture_field_completeness(self) -> None:
        records, _, _ = run_fixture_pipeline(
            source="spinny",
            fixture_path="tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json",
            captured_at="2026-06-24T04:00:00Z",
            ingestion_run_id="run_20260624_spinny_live_fixture_test",
        )

        report = profile_field_completeness(source="spinny", records=records)
        fields = {field.field_name: field for field in report.fields}

        self.assertEqual(report.records_total, 20)
        self.assertEqual(fields["listed_price_inr"].present_count, 20)
        self.assertEqual(fields["fuel_type"].completeness, 1.0)
        self.assertEqual(fields["variant"].present_count, 20)
        self.assertEqual(fields["ownership"].present_count, 0)

    def test_renders_field_profile(self) -> None:
        records, _, _ = run_fixture_pipeline(
            source="spinny",
            fixture_path="tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json",
            captured_at="2026-06-24T04:00:00Z",
            ingestion_run_id="run_20260624_spinny_live_fixture_test",
        )

        report = profile_field_completeness(source="spinny", records=records)
        rendered = render_field_profile(report)

        self.assertIn("# Fixture Field Profile", rendered)
        self.assertIn("- listed_price_inr: 20/20 (100.00%)", rendered)
        self.assertIn("- ownership: 0/20 (0.00%)", rendered)


if __name__ == "__main__":
    unittest.main()
