import unittest

from used_car_price_intelligence.quality import evaluate_listing, load_source_registry


def trusted_complete_record(**overrides):
    record = {
        "source": "spinny",
        "listing_url": "https://www.spinny.com/example-listing",
        "captured_at": "2026-06-24T03:00:00Z",
        "city": "Hyderabad",
        "brand": "Renault",
        "model": "Kiger",
        "variant": "RXT Turbo CVT",
        "model_year": 2021,
        "listed_price_inr": 550000,
        "km_driven": 64000,
        "fuel_type": "petrol",
        "transmission": "automatic",
        "currency": "INR",
        "raw_record_hash": "sha256_example",
        "ingestion_run_id": "run_20260624_spinny_001",
        "parser_version": "parser_v0.1",
        "schema_version": "canonical_listing_v0.1",
        "parse_confidence": 0.96,
        "parse_warnings": [],
        "is_available": True,
        "source_record_type": "listing",
        "is_certified": True,
        "seller_type": "platform",
        "locality": "Uppal",
        "registration_code": "TS12",
    }
    record.update(overrides)
    return record


class QualityEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_source_registry()

    def test_trusted_complete_record_is_pricing_ready(self) -> None:
        result = evaluate_listing(trusted_complete_record(), self.registry)
        self.assertTrue(result.silver_valid)
        self.assertTrue(result.pricing_ready)
        self.assertEqual(result.quarantine_reasons, [])
        self.assertEqual(result.completeness.required, 1.0)

    def test_olx_record_is_not_mvp_eligible_even_if_otherwise_complete(self) -> None:
        record = trusted_complete_record(
            source="olx",
            listing_url="https://www.olx.in/item/example",
            seller_type="individual",
            is_certified=False,
        )
        result = evaluate_listing(record, self.registry)
        self.assertTrue(result.silver_valid)
        self.assertFalse(result.pricing_ready)
        self.assertIn("source_not_mvp_eligible", result.quarantine_reasons)
        self.assertIn("classified_source", result.warnings)

    def test_missing_fuel_and_transmission_blocks_pricing_ready(self) -> None:
        record = trusted_complete_record(fuel_type=None, transmission=None)
        result = evaluate_listing(record, self.registry)
        self.assertFalse(result.pricing_ready)
        self.assertIn("missing_fuel_type", result.quarantine_reasons)
        self.assertIn("missing_transmission", result.quarantine_reasons)
        self.assertLess(result.completeness.required, 1.0)

    def test_unknown_fuel_blocks_pricing_ready(self) -> None:
        record = trusted_complete_record(fuel_type="unknown")
        result = evaluate_listing(record, self.registry)
        self.assertFalse(result.pricing_ready)
        self.assertIn("missing_fuel_type", result.quarantine_reasons)
        self.assertIn("unknown_fuel_type", result.quarantine_reasons)

    def test_unavailable_listing_is_quarantined_from_gold(self) -> None:
        result = evaluate_listing(trusted_complete_record(is_available=False), self.registry)
        self.assertFalse(result.pricing_ready)
        self.assertIn("listing_unavailable", result.quarantine_reasons)

    def test_non_listing_record_is_not_silver_valid(self) -> None:
        result = evaluate_listing(trusted_complete_record(source_record_type="ad"), self.registry)
        self.assertFalse(result.silver_valid)
        self.assertFalse(result.pricing_ready)
        self.assertIn("non_listing_record", result.quarantine_reasons)

    def test_model_with_engine_detail_is_quarantined(self) -> None:
        result = evaluate_listing(trusted_complete_record(model="Wagon R 1.0"), self.registry)
        self.assertFalse(result.pricing_ready)
        self.assertIn("model_contains_engine_or_displacement", result.quarantine_reasons)

    def test_price_like_variant_is_quarantined(self) -> None:
        result = evaluate_listing(trusted_complete_record(variant="Rs 7.27 Lakh"), self.registry)
        self.assertFalse(result.pricing_ready)
        self.assertIn("variant_contains_price_text", result.quarantine_reasons)

    def test_low_parse_confidence_blocks_pricing_ready(self) -> None:
        result = evaluate_listing(trusted_complete_record(parse_confidence=0.72), self.registry)
        self.assertFalse(result.pricing_ready)
        self.assertIn("parse_confidence_below_gold_threshold", result.quarantine_reasons)

    def test_invalid_price_blocks_silver_and_gold(self) -> None:
        result = evaluate_listing(trusted_complete_record(listed_price_inr=0), self.registry)
        self.assertFalse(result.silver_valid)
        self.assertFalse(result.pricing_ready)
        self.assertIn("invalid_price", result.quarantine_reasons)


if __name__ == "__main__":
    unittest.main()
