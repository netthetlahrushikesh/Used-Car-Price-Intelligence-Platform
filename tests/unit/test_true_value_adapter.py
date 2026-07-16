import unittest

from used_car_price_intelligence.adapters import (
    AdapterRunContext,
    TrueValueFixtureAdapter,
    validate_true_value_extracted_payload,
)
from used_car_price_intelligence.quality import evaluate_listing, load_source_registry


TRUE_VALUE_FIXTURE = "tests/fixtures/true_value/listing_cards_extracted.json"


class TrueValueAdapterTests(unittest.TestCase):
    def test_validates_true_value_extracted_payload(self) -> None:
        adapter = TrueValueFixtureAdapter(TRUE_VALUE_FIXTURE)
        result = validate_true_value_extracted_payload(adapter.load_payload())

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.records_total, 8)

    def test_converts_true_value_fixture_to_pricing_ready_records(self) -> None:
        adapter = TrueValueFixtureAdapter(TRUE_VALUE_FIXTURE)
        records = adapter.to_canonical_records(
            AdapterRunContext(
                captured_at="2026-06-25T11:00:00Z",
                ingestion_run_id="run_20260625_true_value_fixture_test",
            )
        )
        registry = load_source_registry()
        results = [evaluate_listing(record, registry) for record in records]

        self.assertEqual(len(records), 8)
        self.assertTrue(all(result.pricing_ready for result in results))
        self.assertTrue(all(result.completeness.required == 1.0 for result in results))
        self.assertTrue(all(record.source == "true_value" for record in records))
        self.assertEqual(records[0].seller_type, "oem_dealer")
        self.assertEqual(records[0].registration_code, "TG08")
        self.assertEqual(records[0].inspection_status, "true_value_certified")
        self.assertEqual(records[1].warranty_label, None)
        self.assertEqual(records[3].model, "Swift Dzire")
        self.assertIn("true_value", records[0].extra_fields)


if __name__ == "__main__":
    unittest.main()
