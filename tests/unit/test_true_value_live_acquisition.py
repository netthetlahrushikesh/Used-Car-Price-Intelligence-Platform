import unittest

from used_car_price_intelligence.acquisition import (
    build_true_value_payload_from_product_pages,
    summarize_true_value_listing_payload,
    true_value_dealer_ids,
    true_value_product_to_raw,
)
from used_car_price_intelligence.adapters import validate_true_value_extracted_payload


PRODUCT_VIEW = {
    "sku": "true-value-123",
    "externalId": "ext-123",
    "name": "2024 Maruti Suzuki Baleno Zeta Petrol",
    "urlKey": "buy-car/baleno-2024-zeta-true-value-123",
    "lastModifiedAt": "2026-06-25T06:00:00Z",
    "inStock": True,
    "images": [{"url": "https://example.com/image-1.jpg"}, {"url": "https://example.com/image-2.jpg"}],
    "price": {
        "regular": {"amount": {"currency": "INR", "value": 820000}},
        "final": {"amount": {"currency": "INR", "value": 795000}},
    },
    "attributes": [
        {"name": "car_city", "value": "Hyderabad"},
        {"name": "state", "value": "Telangana"},
        {"name": "car_model", "value": "Baleno"},
        {"name": "car_variant", "value": "Zeta Petrol"},
        {"name": "make_year", "value": "2024"},
        {"name": "distance_driven", "value": "14,200 km"},
        {"name": "fuel_type", "value": "Petrol"},
        {"name": "transmission_type", "value": "Manual"},
        {"name": "ownership", "value": "1st Owner"},
        {"name": "number_of_owners", "value": "1"},
        {"name": "rto", "value": "TS08"},
        {"name": "registration_date", "value": "2024"},
        {"name": "body_type", "value": "Hatchback"},
        {"name": "color", "value": "Nexa Blue"},
        {"name": "dealer_name", "value": "Varun Motors True Value"},
        {"name": "dealer_location", "value": "Kukatpally"},
        {"name": "dealer_code", "value": "50449-HBS-VARUN"},
        {"name": "dealer_map_code", "value": "50449"},
        {"name": "dealer_parent_group", "value": "VARUN"},
        {"name": "true_value_certified", "value": "true"},
        {"name": "dms_certification_status", "value": "CR"},
        {"name": "overall_rating", "value": "4.4"},
        {"name": "warranty_info", "value": "1Y"},
        {"name": "mssf_finance", "value": "1"},
        {"name": "fmp_emi_amount", "value": "17200"},
    ],
}

DEALER_PAYLOAD = {
    "data": [
        {"mapCd": "50449", "locCd": "HBS", "parentGrp": "VARUN"},
        {"mapCd": "50448", "locCd": "BGM", "parentGrp": "VARUN"},
        {"mapCd": "50449", "locCd": "HBS", "parentGrp": "VARUN"},
    ]
}


class TrueValueLiveAcquisitionTests(unittest.TestCase):
    def test_extracts_unique_dealer_ids(self) -> None:
        self.assertEqual(
            true_value_dealer_ids(DEALER_PAYLOAD),
            ["50449-HBS-VARUN", "50448-BGM-VARUN"],
        )

    def test_maps_graphql_product_to_payload_raw_record(self) -> None:
        raw = true_value_product_to_raw(
            PRODUCT_VIEW,
            source_url="https://www.marutisuzukitruevalue.com/buy-car",
        )

        self.assertEqual(raw["sku"], "true-value-123")
        self.assertEqual(raw["title"], "2024 Maruti Suzuki Baleno")
        self.assertEqual(raw["model_year"], 2024)
        self.assertEqual(raw["brand"], "Maruti Suzuki")
        self.assertEqual(raw["model"], "Baleno")
        self.assertEqual(raw["variant"], "Zeta Petrol")
        self.assertEqual(raw["price"], 795000)
        self.assertEqual(raw["km"], "14,200 km")
        self.assertEqual(raw["registration"], "TS08")
        self.assertEqual(raw["locality"], "Kukatpally")
        self.assertEqual(raw["dealer_code"], "50449-HBS-VARUN")
        self.assertEqual(raw["true_value_certified"], "true")
        self.assertEqual(raw["image_count"], 2)
        self.assertTrue(raw["listing_url"].endswith("/buy-car/baleno-2024-zeta-true-value-123"))

    def test_builds_contract_valid_payload_from_graphql_pages(self) -> None:
        payload = build_true_value_payload_from_product_pages(
            source_url="https://www.marutisuzukitruevalue.com/buy-car",
            result_pages=[
                {
                    "items": [{"productView": PRODUCT_VIEW}],
                    "page_info": {"current_page": 1, "page_size": 100, "total_pages": 3},
                    "total_count": 247,
                }
            ],
            dealer_payload=DEALER_PAYLOAD,
            captured_at="2026-06-25T11:30:00Z",
            city="Hyderabad",
            state="Telangana",
            max_records=40,
            pagination={
                "pagination_type": "dealer_discovery_plus_graphql",
                "max_pages": 1,
                "attempted_pages": 1,
                "page_size": 100,
                "max_records": 40,
                "min_records": 1,
                "coverage_ok": True,
                "unique_cards_seen": 1,
                "returned_records": 1,
                "duplicate_cards_skipped": 0,
                "source_total_items": 247,
                "source_total_pages": 3,
                "dealer_count": 2,
                "dealer_distance_m": 25000,
                "stop_reason": "record_cap_reached",
            },
        )

        result = validate_true_value_extracted_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.records_total, 1)
        self.assertEqual(payload["dealer_discovery"]["dealer_ids"], ["50449-HBS-VARUN", "50448-BGM-VARUN"])
        self.assertEqual(payload["records"][0]["raw"]["warranty_info"], "1Y")

    def test_summarizes_true_value_listing_payload(self) -> None:
        payload = build_true_value_payload_from_product_pages(
            source_url="https://www.marutisuzukitruevalue.com/buy-car",
            result_pages=[{"items": [{"productView": PRODUCT_VIEW}]}],
            dealer_payload=DEALER_PAYLOAD,
            captured_at="2026-06-25T11:30:00Z",
            city="Hyderabad",
            state="Telangana",
            max_records=40,
            pagination={
                "pagination_type": "dealer_discovery_plus_graphql",
                "max_pages": 1,
                "attempted_pages": 1,
                "page_size": 100,
                "max_records": 40,
                "min_records": 1,
                "coverage_ok": True,
                "unique_cards_seen": 1,
                "returned_records": 1,
                "duplicate_cards_skipped": 0,
                "source_total_items": 247,
                "source_total_pages": 3,
                "dealer_count": 2,
                "dealer_distance_m": 25000,
                "stop_reason": "record_cap_reached",
            },
        )

        summary = summarize_true_value_listing_payload(payload)

        self.assertEqual(summary["records_total"], 1)
        self.assertEqual(summary["unique_listing_urls"], 1)
        self.assertEqual(summary["pagination_type"], "dealer_discovery_plus_graphql")
        self.assertEqual(summary["source_total_items"], 247)
        self.assertEqual(summary["source_total_pages"], 3)
        self.assertEqual(summary["dealer_count"], 2)
        self.assertTrue(summary["coverage_ok"])

    def test_skips_unavailable_inventory_before_canonical_conversion(self) -> None:
        unavailable = dict(PRODUCT_VIEW)
        unavailable["sku"] = "true-value-unavailable"
        unavailable["inStock"] = False
        payload = build_true_value_payload_from_product_pages(
            source_url="https://www.marutisuzukitruevalue.com/buy-car",
            result_pages=[
                {
                    "items": [{"productView": unavailable}, {"productView": PRODUCT_VIEW}],
                    "page_info": {"current_page": 1, "page_size": 100, "total_pages": 1},
                    "total_count": 2,
                }
            ],
            dealer_payload=DEALER_PAYLOAD,
            captured_at="2026-06-25T11:30:00Z",
            city="Hyderabad",
            state="Telangana",
            max_records=40,
            pagination={
                "pagination_type": "dealer_discovery_plus_graphql",
                "max_pages": 1,
                "attempted_pages": 1,
                "page_size": 100,
                "max_records": 40,
                "min_records": 1,
                "coverage_ok": True,
                "unique_cards_seen": 1,
                "returned_records": 1,
                "duplicate_cards_skipped": 0,
                "source_total_items": 2,
                "source_total_pages": 1,
                "dealer_count": 2,
                "dealer_distance_m": 25000,
                "stop_reason": "source_total_pages_reached",
            },
        )

        result = validate_true_value_extracted_payload(payload)
        summary = summarize_true_value_listing_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.records_total, 1)
        self.assertEqual(payload["records"][0]["raw"]["sku"], "true-value-123")
        self.assertEqual(summary["unavailable_rows_skipped"], 1)

    def test_skips_incomplete_inventory_before_contract_validation(self) -> None:
        incomplete = dict(PRODUCT_VIEW)
        incomplete["sku"] = "true-value-incomplete"
        incomplete["attributes"] = [
            attribute for attribute in PRODUCT_VIEW["attributes"] if attribute["name"] != "car_variant"
        ]
        payload = build_true_value_payload_from_product_pages(
            source_url="https://www.marutisuzukitruevalue.com/buy-car",
            result_pages=[
                {
                    "items": [{"productView": incomplete}, {"productView": PRODUCT_VIEW}],
                    "page_info": {"current_page": 1, "page_size": 100, "total_pages": 1},
                    "total_count": 2,
                }
            ],
            dealer_payload=DEALER_PAYLOAD,
            captured_at="2026-06-25T11:30:00Z",
            city="Hyderabad",
            state="Telangana",
            max_records=40,
            pagination={
                "pagination_type": "dealer_discovery_plus_graphql",
                "max_pages": 1,
                "attempted_pages": 1,
                "page_size": 100,
                "max_records": 40,
                "min_records": 1,
                "coverage_ok": True,
                "unique_cards_seen": 1,
                "returned_records": 1,
                "duplicate_cards_skipped": 0,
                "source_total_items": 2,
                "source_total_pages": 1,
                "dealer_count": 2,
                "dealer_distance_m": 25000,
                "stop_reason": "source_total_pages_reached",
            },
        )

        result = validate_true_value_extracted_payload(payload)
        summary = summarize_true_value_listing_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.records_total, 1)
        self.assertEqual(payload["records"][0]["raw"]["sku"], "true-value-123")
        self.assertEqual(summary["incomplete_rows_skipped"], 1)

    def test_skips_km_outlier_inventory_before_gold_quality(self) -> None:
        outlier = dict(PRODUCT_VIEW)
        outlier["sku"] = "true-value-km-outlier"
        outlier["attributes"] = [
            {**attribute, "value": "908653"}
            if attribute["name"] == "distance_driven"
            else attribute
            for attribute in PRODUCT_VIEW["attributes"]
        ]
        payload = build_true_value_payload_from_product_pages(
            source_url="https://www.marutisuzukitruevalue.com/buy-car",
            result_pages=[
                {
                    "items": [{"productView": outlier}, {"productView": PRODUCT_VIEW}],
                    "page_info": {"current_page": 1, "page_size": 100, "total_pages": 1},
                    "total_count": 2,
                }
            ],
            dealer_payload=DEALER_PAYLOAD,
            captured_at="2026-06-25T11:30:00Z",
            city="Hyderabad",
            state="Telangana",
            max_records=40,
            pagination={
                "pagination_type": "dealer_discovery_plus_graphql",
                "max_pages": 1,
                "attempted_pages": 1,
                "page_size": 100,
                "max_records": 40,
                "min_records": 1,
                "coverage_ok": True,
                "unique_cards_seen": 1,
                "returned_records": 1,
                "duplicate_cards_skipped": 0,
                "source_total_items": 2,
                "source_total_pages": 1,
                "dealer_count": 2,
                "dealer_distance_m": 25000,
                "stop_reason": "source_total_pages_reached",
            },
        )

        result = validate_true_value_extracted_payload(payload)
        summary = summarize_true_value_listing_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.records_total, 1)
        self.assertEqual(payload["records"][0]["raw"]["km"], "14,200 km")
        self.assertEqual(summary["km_outlier_rows_skipped"], 1)


if __name__ == "__main__":
    unittest.main()
