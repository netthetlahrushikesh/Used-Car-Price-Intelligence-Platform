import unittest

from used_car_price_intelligence.acquisition import (
    build_mfc_payload_from_result_pages,
    mfc_structured_listing_to_raw,
    summarize_mfc_listing_payload,
)
from used_car_price_intelligence.adapters import validate_mahindra_first_choice_extracted_payload


STRUCTURED_LISTING = {
    "id_classified": 242953,
    "manufacturer_name": "Mahindra",
    "model_name": "Scorpio",
    "variant_name": "S11 2WD BS IV",
    "variant_chunk": "S11 2WD BS IV",
    "classified_name": "2022 Mahindra Scorpio S11 2WD BS IV",
    "year": "2022",
    "fuel": "Diesel",
    "class": "SUV",
    "price": 1950000,
    "price_value": 1950000,
    "registration_number": "TS07AB1234",
    "owner": "First Owner",
    "seller": "Dealer",
    "odometer": "15,214 km",
    "color": "Black",
    "mileage": "15.40",
    "transmission": "Manual",
    "location": "Cyberabad, Hyderabad",
    "city": "Hyderabad",
    "state": "Telangana",
    "rating": "8.1",
    "photo_count": 14,
    "posted_on": "2026-02-22",
    "is_certified": True,
    "warranty_txt": "1 year warranty",
    "url": "/buyer/detail/hyderabad-mahindra-242953",
    "emi_text": "Rs. 52,557/month",
    "stock_id": "649172",
    "dealer_name": "Mahindra First Choice Dealer",
}


class MahindraFirstChoiceLiveAcquisitionTests(unittest.TestCase):
    def test_maps_structured_listing_to_payload_raw_record(self) -> None:
        raw = mfc_structured_listing_to_raw(
            STRUCTURED_LISTING,
            source_url="https://www.mahindrafirstchoice.com/used-cars/hyderabad",
        )

        self.assertEqual(raw["id_classified"], 242953)
        self.assertEqual(raw["title"], "2022 Mahindra Scorpio")
        self.assertEqual(raw["model_year"], 2022)
        self.assertEqual(raw["brand"], "Mahindra")
        self.assertEqual(raw["model"], "Scorpio")
        self.assertEqual(raw["variant_details"], "S11 2WD BS IV | 15,214 km | Diesel | Manual")
        self.assertEqual(raw["owner_text"], "First Owner")
        self.assertEqual(raw["registration"], "TS07AB1234")
        self.assertEqual(raw["seller_type"], "Dealer")
        self.assertEqual(raw["body_type"], "SUV")
        self.assertEqual(raw["color"], "Black")
        self.assertTrue(raw["listing_url"].endswith("/buyer/detail/hyderabad-mahindra-242953"))

    def test_builds_contract_valid_payload_from_result_pages(self) -> None:
        payload = build_mfc_payload_from_result_pages(
            source_url="https://www.mahindrafirstchoice.com/used-cars/hyderabad",
            result_pages=[
                {
                    "current_page": 1,
                    "data": [STRUCTURED_LISTING],
                    "total_items": 88,
                    "max_page": 3,
                    "page_size": 30,
                }
            ],
            captured_at="2026-06-25T08:45:00Z",
            max_records=40,
            pagination={
                "pagination_type": "next_data_plus_xhr",
                "max_pages": 2,
                "attempted_pages": 1,
                "max_records": 40,
                "min_records": 1,
                "coverage_ok": True,
                "unique_cards_seen": 1,
                "returned_records": 1,
                "duplicate_cards_skipped": 0,
                "page_scroll_delay_ms": 2500,
                "stop_reason": "record_cap_reached",
                "source_total_items": 88,
                "source_max_page": 3,
            },
        )

        result = validate_mahindra_first_choice_extracted_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.records_total, 1)
        self.assertEqual(payload["records"][0]["raw"]["owner_text"], "First Owner")

    def test_summarizes_mfc_listing_payload(self) -> None:
        payload = build_mfc_payload_from_result_pages(
            source_url="https://www.mahindrafirstchoice.com/used-cars/hyderabad",
            result_pages=[{"current_page": 1, "data": [STRUCTURED_LISTING]}],
            captured_at="2026-06-25T08:45:00Z",
            max_records=40,
            pagination={
                "pagination_type": "next_data_plus_xhr",
                "max_pages": 2,
                "attempted_pages": 1,
                "max_records": 40,
                "min_records": 1,
                "coverage_ok": True,
                "unique_cards_seen": 1,
                "returned_records": 1,
                "duplicate_cards_skipped": 0,
                "page_scroll_delay_ms": 2500,
                "stop_reason": "record_cap_reached",
                "source_total_items": 88,
                "source_max_page": 3,
            },
        )

        summary = summarize_mfc_listing_payload(payload)

        self.assertEqual(summary["records_total"], 1)
        self.assertEqual(summary["unique_listing_urls"], 1)
        self.assertEqual(summary["pagination_type"], "next_data_plus_xhr")
        self.assertEqual(summary["source_total_items"], 88)
        self.assertTrue(summary["coverage_ok"])


if __name__ == "__main__":
    unittest.main()
