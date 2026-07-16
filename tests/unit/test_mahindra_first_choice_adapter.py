import copy
import json
from pathlib import Path
import unittest

from used_car_price_intelligence.adapters import AdapterRunContext
from used_car_price_intelligence.adapters.mahindra_first_choice import (
    MahindraFirstChoiceExtractedPayloadAdapter,
    MahindraFirstChoiceFixtureAdapter,
    parse_mfc_variant_details,
    validate_mahindra_first_choice_extracted_payload,
)
from used_car_price_intelligence.quality import evaluate_listing, load_source_registry


class MahindraFirstChoiceFixtureAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_path = Path("tests/fixtures/mahindra_first_choice/listing_cards_extracted.json")
        cls.adapter = MahindraFirstChoiceFixtureAdapter(cls.fixture_path)
        cls.registry = load_source_registry()

    def test_variant_details_parser_extracts_card_segments(self) -> None:
        result = parse_mfc_variant_details("VXI AGS | 38,281 km | Petrol | AMT")

        self.assertEqual(result["variant"], "VXI AGS")
        self.assertEqual(result["km"], "38,281 km")
        self.assertEqual(result["fuel"], "Petrol")
        self.assertEqual(result["transmission"], "AMT")

    def test_adapter_converts_fixture_records_to_canonical_listings(self) -> None:
        records = self.adapter.to_canonical_records(
            AdapterRunContext(
                captured_at="2026-06-25T03:30:00Z",
                ingestion_run_id="run_20260625_mfc_fixture_001",
            )
        )

        self.assertEqual(len(records), 9)
        first = records[0]
        self.assertEqual(first.source, "mahindra_first_choice")
        self.assertEqual(first.brand, "Mahindra")
        self.assertEqual(first.model, "Scorpio")
        self.assertEqual(first.variant, "S11 2WD BS IV")
        self.assertEqual(first.listed_price_inr, 1950000)
        self.assertEqual(first.km_driven, 15214)
        self.assertEqual(first.fuel_type, "diesel")
        self.assertEqual(first.transmission, "manual")
        self.assertEqual(first.seller_type, "dealer")
        self.assertTrue(first.is_certified)
        self.assertEqual(first.extra_fields["mahindra_first_choice"]["rating_score"], 8.1)

        automatic_xuv700 = records[6]
        self.assertEqual(automatic_xuv700.brand, "Mahindra")
        self.assertEqual(automatic_xuv700.model, "XUV700")
        self.assertEqual(automatic_xuv700.transmission, "automatic")

    def test_fixture_records_are_pricing_ready_with_known_high_value_gap(self) -> None:
        records = self.adapter.to_canonical_records(
            AdapterRunContext(
                captured_at="2026-06-25T03:30:00Z",
                ingestion_run_id="run_20260625_mfc_fixture_001",
            )
        )

        results = [evaluate_listing(record, self.registry) for record in records]

        self.assertTrue(all(result.silver_valid for result in results))
        self.assertTrue(all(result.pricing_ready for result in results))
        self.assertTrue(all(result.completeness.required == 1.0 for result in results))
        self.assertTrue(all(result.completeness.high_value < 1.0 for result in results))
        self.assertTrue(all(record.ownership is None for record in records))
        self.assertTrue(all(record.registration_code is None for record in records))

    def test_structured_live_payload_maps_enrichment_fields(self) -> None:
        payload = {
            "source": "mahindra_first_choice",
            "source_url": "https://www.mahindrafirstchoice.com/used-cars/hyderabad",
            "records": [
                {
                    "raw": {
                        "id_classified": 242953,
                        "stock_id": "649172",
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
        adapter = MahindraFirstChoiceExtractedPayloadAdapter(payload)

        records = adapter.to_canonical_records(
            AdapterRunContext(
                captured_at="2026-06-25T08:45:00Z",
                ingestion_run_id="run_20260625_mfc_structured_adapter_test",
            )
        )

        record = records[0]
        self.assertEqual(record.source_listing_id, "mfc_242953")
        self.assertEqual(record.ownership, 1)
        self.assertEqual(record.registration_code, "TS07")
        self.assertEqual(record.registration_state, "Telangana")
        self.assertEqual(record.body_type, "SUV")
        self.assertEqual(record.color, "Black")
        self.assertEqual(record.dealer_name, "Mahindra First Choice Dealer")
        self.assertEqual(record.warranty_label, "1 year warranty")
        self.assertEqual(record.listing_posted_at, "2026-02-22")
        self.assertEqual(record.extra_fields["mahindra_first_choice"]["stock_id"], "649172")

    def test_extracted_payload_contract_rejects_missing_variant_detail_segment(self) -> None:
        payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        invalid_payload = copy.deepcopy(payload)
        invalid_payload["records"][0]["raw"]["variant_details"] = "S11 2WD BS IV | 15,214 km"

        result = validate_mahindra_first_choice_extracted_payload(invalid_payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.failures[0].record_index, 1)
        self.assertEqual(result.failures[0].field_name, "variant_details.fuel")
        self.assertEqual(result.failures[0].reason, "missing_variant_detail_segment")

    def test_extracted_payload_adapter_fails_closed_on_invalid_payload(self) -> None:
        payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        invalid_payload = copy.deepcopy(payload)
        invalid_payload["records"][0]["raw"].pop("score")
        adapter = MahindraFirstChoiceExtractedPayloadAdapter(invalid_payload)

        with self.assertRaises(ValueError):
            adapter.to_canonical_records(
                AdapterRunContext(
                    captured_at="2026-06-25T03:45:00Z",
                    ingestion_run_id="run_20260625_mfc_contract_failure_test",
                )
            )


if __name__ == "__main__":
    unittest.main()
