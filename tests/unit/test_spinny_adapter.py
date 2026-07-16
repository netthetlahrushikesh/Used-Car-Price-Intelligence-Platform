import copy
import json
from pathlib import Path
import unittest

from used_car_price_intelligence.adapters.spinny import (
    AdapterRunContext,
    SpinnyExtractedPayloadAdapter,
    SpinnyFixtureAdapter,
    validate_spinny_extracted_payload,
)
from used_car_price_intelligence.quality import evaluate_listing, load_source_registry


class SpinnyFixtureAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = SpinnyFixtureAdapter("tests/fixtures/spinny/listing_cards_extracted.json")
        cls.registry = load_source_registry()

    def test_adapter_converts_fixture_records_to_canonical_listings(self) -> None:
        records = self.adapter.to_canonical_records(
            AdapterRunContext(
                captured_at="2026-06-24T03:00:00Z",
                ingestion_run_id="run_20260624_spinny_fixture_001",
            )
        )

        self.assertEqual(len(records), 5)
        first = records[0]
        self.assertEqual(first.source, "spinny")
        self.assertEqual(first.brand, "Honda")
        self.assertEqual(first.model, "Jazz")
        self.assertEqual(first.variant, "V AT Petrol")
        self.assertEqual(first.listed_price_inr, 403000)
        self.assertEqual(first.km_driven, 145500)
        self.assertEqual(first.fuel_type, "petrol")
        self.assertEqual(first.transmission, "automatic")
        self.assertEqual(first.registration_code, "TS12")
        self.assertEqual(first.seller_type, "platform")
        self.assertTrue(first.is_certified)
        self.assertTrue(first.raw_record_hash)

    def test_spinny_fixture_records_pass_quality_gate(self) -> None:
        records = self.adapter.to_canonical_records(
            AdapterRunContext(
                captured_at="2026-06-24T03:00:00Z",
                ingestion_run_id="run_20260624_spinny_fixture_001",
            )
        )

        results = [evaluate_listing(record, self.registry) for record in records]
        self.assertTrue(all(result.silver_valid for result in results))
        self.assertTrue(all(result.pricing_ready for result in results))
        self.assertTrue(all(result.completeness.required == 1.0 for result in results))

    def test_extracted_payload_contract_accepts_live_fixture(self) -> None:
        payload = json.loads(
            Path("tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json").read_text(
                encoding="utf-8"
            )
        )

        result = validate_spinny_extracted_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.records_total, 20)

    def test_extracted_payload_contract_rejects_missing_required_raw_field(self) -> None:
        payload = json.loads(
            Path("tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json").read_text(
                encoding="utf-8"
            )
        )
        invalid_payload = copy.deepcopy(payload)
        invalid_payload["records"][0]["raw"]["fuel"] = ""

        result = validate_spinny_extracted_payload(invalid_payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.failures[0].record_index, 1)
        self.assertEqual(result.failures[0].field_name, "fuel")
        self.assertEqual(result.failures[0].reason, "missing_required_raw_field")

    def test_extracted_payload_adapter_fails_closed_on_invalid_payload(self) -> None:
        payload = json.loads(
            Path("tests/fixtures/spinny/live_hyderabad_hub_2026-06-24_extracted.json").read_text(
                encoding="utf-8"
            )
        )
        invalid_payload = copy.deepcopy(payload)
        invalid_payload["records"][0]["raw"].pop("price")
        adapter = SpinnyExtractedPayloadAdapter(invalid_payload)

        with self.assertRaises(ValueError):
            adapter.to_canonical_records(
                AdapterRunContext(
                    captured_at="2026-06-24T04:00:00Z",
                    ingestion_run_id="run_20260624_spinny_contract_failure_test",
                )
            )

    def test_extracted_payload_adapter_maps_detail_enrichment_fields(self) -> None:
        payload = {
            "source": "spinny",
            "source_url": "https://www.spinny.com/example/s/",
            "records": [
                {
                    "raw": {
                        "title": "2022 MG Hector Plus",
                        "price": "18.46 Lakh",
                        "variant": "Sharp 1.5 Petrol Turbo CVT 6STR",
                        "emi": "EMI Rs 31,915/m*",
                        "km": "24K km",
                        "fuel": "petrol",
                        "transmission": "automatic",
                        "registration": "TS07",
                        "locality": "Nexus Sujana Mall, Kukatpally",
                        "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mg-motors/hector-plus/example/123/",
                        "make_year": "Apr 2022",
                        "registration_year": "May 2022",
                        "ownership": "1st Owner",
                        "insurance_validity": "May 2027",
                        "insurance_type": "Comprehensive",
                        "rto": "TS07",
                        "detail_locality": "Kukatpally, Hyderabad",
                        "inspection_status": "quality_report_available",
                        "inspection_summary": "1452 parts evaluated by 5 automotive experts",
                        "quality_scores": {"core_systems": {"score": "9.8", "grade": "Excellent"}},
                        "warranty_label": "1 year warranty",
                        "return_policy_label": "5-day money back",
                    }
                }
            ],
        }
        adapter = SpinnyExtractedPayloadAdapter(payload)

        records = adapter.to_canonical_records(
            AdapterRunContext(
                captured_at="2026-06-24T06:30:00Z",
                ingestion_run_id="run_20260624_spinny_detail_enrichment_test",
            )
        )

        record = records[0]
        self.assertEqual(record.ownership, 1)
        self.assertEqual(record.manufacture_year, 2022)
        self.assertEqual(record.registration_year, 2022)
        self.assertEqual(record.registration_code, "TS07")
        self.assertEqual(record.locality, "Kukatpally, Hyderabad")
        self.assertEqual(record.inspection_status, "quality_report_available")
        self.assertEqual(record.warranty_label, "1 year warranty")
        self.assertEqual(record.return_policy_label, "5-day money back")
        self.assertEqual(record.extra_fields["spinny_detail"]["insurance_type"], "Comprehensive")

    def test_extracted_payload_adapter_recovers_price_like_variant_from_listing_url(self) -> None:
        payload = {
            "source": "spinny",
            "source_url": "https://www.spinny.com/example/s/",
            "records": [
                {
                    "raw": {
                        "title": "2019 Hyundai Venue",
                        "price": "7.16 Lakh",
                        "variant": "\u20b97.27 Lakh",
                        "emi": "EMI \u20b912,448/m*",
                        "km": "35K km",
                        "fuel": "petrol",
                        "transmission": "manual",
                        "registration": "KA01",
                        "locality": "Vega City Mall, BTM Layout",
                        "listing_url": (
                            "https://www.spinny.com/buy-used-cars/bangalore/hyundai/venue/"
                            "sx-10-petrol-2019/29589252/"
                        ),
                    }
                }
            ],
        }
        adapter = SpinnyExtractedPayloadAdapter(payload)

        records = adapter.to_canonical_records(
            AdapterRunContext(
                captured_at="2026-06-24T06:30:00Z",
                ingestion_run_id="run_20260624_spinny_variant_recovery_test",
            )
        )

        record = records[0]
        self.assertEqual(record.variant, "SX 10 Petrol")
        self.assertEqual(record.source_variant_text, "SX 10 Petrol")
        self.assertIn("variant_price_text_rejected", record.parse_warnings)
        self.assertIn("variant_recovered_from_listing_url", record.parse_warnings)


if __name__ == "__main__":
    unittest.main()
