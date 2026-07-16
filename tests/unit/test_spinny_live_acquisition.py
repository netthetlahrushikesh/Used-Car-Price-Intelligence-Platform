import unittest

from used_car_price_intelligence.acquisition import (
    build_spinny_incremental_detail_payload,
    build_spinny_incremental_detail_plan,
    build_spinny_payload_from_card_snapshots,
    build_spinny_payload_from_card_texts,
    merge_spinny_detail_payload_into_listing_payload,
    normalize_spinny_listing_url,
    parse_spinny_card_text,
    parse_spinny_detail_text,
    spinny_detail_cache_index,
    summarize_spinny_listing_payload,
    summarize_spinny_detail_payload,
)
from used_car_price_intelligence.acquisition.spinny_live import (
    _cap_listing_payload_records,
    _snapshot_capture_limit,
)
from used_car_price_intelligence.adapters import validate_spinny_extracted_payload


LIVE_CARD_TEXT = """2025 Mahindra XUV700
20.44 Lakh
AX 7 Luxury Pack Petrol AT 7 STR
EMI Rs 35,385/m*
26.5K km
Petrol
Automatic
TG07

5-star NCAP rating"""

LIVE_CARD_TEXT_WITH_ENGINE_SIZE_VARIANT = """2023 Skoda Slavia
13.29 Lakh
Style 1.0L TSI AT
EMI Rs 22,972/m*
21K km
Petrol
Automatic
TS07
Nexus Sujana Mall, Kukatpally

Performance & 2 more reasons to buy"""

DELHI_CARD_TEXT_WITH_RTO_SUFFIX = """2022 Kia Carens
11.81 Lakh
Luxury Plus 1.4 Petrol DCT 7 STR
EMI Rs 20,452/m*
42.5K km
Petrol
Automatic
DL3C
Dwarka, Delhi

Rare price & 1 more reason to buy"""


class SpinnyLiveAcquisitionTests(unittest.TestCase):
    def test_parses_spinny_live_card_text(self) -> None:
        raw = parse_spinny_card_text(LIVE_CARD_TEXT)

        self.assertIsNotNone(raw)
        self.assertEqual(raw["title"], "2025 Mahindra XUV700")
        self.assertEqual(raw["price"], "20.44 Lakh")
        self.assertEqual(raw["variant"], "AX 7 Luxury Pack Petrol AT 7 STR")
        self.assertEqual(raw["emi"], "EMI Rs 35,385/m*")
        self.assertEqual(raw["km"], "26.5K km")
        self.assertEqual(raw["fuel"], "petrol")
        self.assertEqual(raw["transmission"], "automatic")
        self.assertEqual(raw["registration"], "TG07")
        self.assertEqual(raw["locality"], "Nexus Sujana Mall, Kukatpally")

    def test_builds_contract_valid_payload_from_card_texts(self) -> None:
        payload = build_spinny_payload_from_card_texts(
            source_url="https://www.spinny.com/example/s/",
            card_texts=[LIVE_CARD_TEXT],
            captured_at="2026-06-24T04:30:00Z",
        )

        result = validate_spinny_extracted_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.records_total, 1)

    def test_builds_payload_from_card_snapshots_with_listing_url(self) -> None:
        payload = build_spinny_payload_from_card_snapshots(
            source_url="https://www.spinny.com/example/s/",
            card_snapshots=[
                {
                    "text": LIVE_CARD_TEXT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/123/",
                }
            ],
            captured_at="2026-06-24T04:30:00Z",
        )

        result = validate_spinny_extracted_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(
            payload["records"][0]["raw"]["listing_url"],
            "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/123/",
        )

    def test_repairs_price_like_variant_from_listing_url(self) -> None:
        card_text = """2019 Hyundai Venue
7.16 Lakh
\u20b97.27 Lakh
EMI \u20b912,448/m*
35K km
Petrol
Manual
KA01
Vega City Mall, BTM Layout"""

        payload = build_spinny_payload_from_card_snapshots(
            source_url="https://www.spinny.com/example/s/",
            card_snapshots=[
                {
                    "text": card_text,
                    "listing_url": (
                        "https://www.spinny.com/buy-used-cars/bangalore/hyundai/venue/"
                        "sx-10-petrol-2019/29589252/"
                    ),
                }
            ],
            captured_at="2026-06-24T04:30:00Z",
        )

        result = validate_spinny_extracted_payload(payload)

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(payload["records"][0]["raw"]["variant"], "SX 10 Petrol")

    def test_summarizes_paginated_listing_payload(self) -> None:
        payload = build_spinny_payload_from_card_snapshots(
            source_url="https://www.spinny.com/example/s/",
            card_snapshots=[
                {
                    "text": LIVE_CARD_TEXT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/123/",
                }
            ],
            captured_at="2026-06-24T04:30:00Z",
            pagination={
                "pagination_type": "infinite_scroll_batches",
                "max_pages": 2,
                "attempted_pages": 2,
                "max_records": 40,
                "min_records": 1,
                "coverage_ok": True,
                "unique_cards_seen": 42,
                "returned_records": 40,
                "duplicate_cards_skipped": 22,
                "page_scroll_delay_ms": 2500,
                "stop_reason": "record_cap_reached",
            },
        )

        summary = summarize_spinny_listing_payload(payload)

        self.assertEqual(summary["pagination_type"], "infinite_scroll_batches")
        self.assertEqual(summary["max_pages"], 2)
        self.assertEqual(summary["attempted_pages"], 2)
        self.assertEqual(summary["records_total"], 1)
        self.assertEqual(summary["min_records"], 1)
        self.assertTrue(summary["coverage_ok"])
        self.assertEqual(summary["unique_cards_seen"], 42)
        self.assertEqual(summary["duplicate_cards_skipped"], 22)

    def test_caps_clean_records_after_raw_card_headroom(self) -> None:
        payload = build_spinny_payload_from_card_snapshots(
            source_url="https://www.spinny.com/example/s/",
            card_snapshots=[
                {
                    "text": LIVE_CARD_TEXT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/1/",
                },
                {"text": "Sponsored inventory card without vehicle fields", "listing_url": ""},
                {
                    "text": LIVE_CARD_TEXT_WITH_ENGINE_SIZE_VARIANT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/skoda/slavia/example/2/",
                },
                {
                    "text": LIVE_CARD_TEXT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/3/",
                },
            ],
            captured_at="2026-06-24T04:30:00Z",
            pagination={
                "pagination_type": "infinite_scroll_batches",
                "max_pages": 1,
                "attempted_pages": 1,
                "max_records": 4,
                "min_records": 2,
                "coverage_ok": True,
                "unique_cards_seen": 4,
                "returned_records": 4,
                "duplicate_cards_skipped": 0,
                "page_scroll_delay_ms": 2500,
                "stop_reason": "record_cap_reached",
            },
        )

        _cap_listing_payload_records(payload, max_records=2, min_records=2, snapshot_max_records=4)
        summary = summarize_spinny_listing_payload(payload)

        self.assertEqual(_snapshot_capture_limit(max_records=2, min_records=2), 7)
        self.assertEqual(len(payload["records"]), 2)
        self.assertEqual(summary["max_records"], 2)
        self.assertEqual(summary["snapshot_max_records"], 4)
        self.assertEqual(summary["raw_cards_returned"], 4)
        self.assertEqual(summary["parsed_records_before_cap"], 3)
        self.assertEqual(summary["returned_records"], 2)
        self.assertTrue(summary["coverage_ok"])

    def test_variant_with_engine_size_is_not_mistaken_for_price(self) -> None:
        raw = parse_spinny_card_text(LIVE_CARD_TEXT_WITH_ENGINE_SIZE_VARIANT)

        self.assertIsNotNone(raw)
        self.assertEqual(raw["variant"], "Style 1.0L TSI AT")

    def test_parses_delhi_rto_code_with_suffix_letter(self) -> None:
        raw = parse_spinny_card_text(DELHI_CARD_TEXT_WITH_RTO_SUFFIX)

        self.assertIsNotNone(raw)
        self.assertEqual(raw["registration"], "DL3C")
        self.assertEqual(raw["variant"], "Luxury Plus 1.4 Petrol DCT 7 STR")
        self.assertEqual(raw["locality"], "Dwarka, Delhi")

    def test_missing_variant_remains_contract_failure(self) -> None:
        card_without_variant = """2025 Mahindra XUV700
20.44 Lakh
EMI Rs 35,385/m*
26.5K km
Petrol
Automatic
TG07"""

        payload = build_spinny_payload_from_card_texts(
            source_url="https://www.spinny.com/example/s/",
            card_texts=[card_without_variant],
            captured_at="2026-06-24T04:30:00Z",
        )
        result = validate_spinny_extracted_payload(payload)

        self.assertFalse(result.ok)
        self.assertEqual(result.failures[0].field_name, "variant")

    def test_parses_spinny_detail_text(self) -> None:
        raw = parse_spinny_detail_text(DETAIL_PAGE_TEXT)

        self.assertEqual(raw["make_year"], "Apr 2022")
        self.assertEqual(raw["registration_year"], "May 2022")
        self.assertEqual(raw["ownership"], "1st Owner")
        self.assertEqual(raw["insurance_validity"], "May 2027")
        self.assertEqual(raw["insurance_type"], "Comprehensive")
        self.assertEqual(raw["rto"], "TS07")
        self.assertEqual(raw["detail_locality"], "Kukatpally, Hyderabad")
        self.assertEqual(raw["inspection_status"], "quality_report_available")
        self.assertEqual(raw["quality_scores"]["core_systems"]["score"], "9.8")
        self.assertEqual(raw["warranty_label"], "1 year warranty")
        self.assertEqual(raw["return_policy_label"], "5-day money back")

    def test_merges_detail_payload_into_listing_payload_by_url(self) -> None:
        listing_url = "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/123/"
        listing_payload = build_spinny_payload_from_card_snapshots(
            source_url="https://www.spinny.com/example/s/",
            card_snapshots=[{"text": LIVE_CARD_TEXT, "listing_url": listing_url}],
            captured_at="2026-06-24T04:30:00Z",
        )
        detail_payload = {
            "source": "spinny",
            "captured_at": "2026-06-24T04:35:00Z",
            "records": [
                {
                    "listing_url": listing_url,
                    "raw": parse_spinny_detail_text(DETAIL_PAGE_TEXT),
                }
            ],
        }

        merged = merge_spinny_detail_payload_into_listing_payload(
            listing_payload=listing_payload,
            detail_payload=detail_payload,
        )

        raw = merged["records"][0]["raw"]
        self.assertEqual(raw["ownership"], "1st Owner")
        self.assertEqual(raw["rto"], "TS07")
        self.assertEqual(raw["inspection_status"], "quality_report_available")

    def test_merges_detail_payload_by_normalized_listing_url(self) -> None:
        listing_url = "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/123/?utm=abc"
        listing_payload = build_spinny_payload_from_card_snapshots(
            source_url="https://www.spinny.com/example/s/",
            card_snapshots=[{"text": LIVE_CARD_TEXT, "listing_url": listing_url}],
            captured_at="2026-06-24T04:30:00Z",
        )
        detail_payload = {
            "source": "spinny",
            "captured_at": "2026-06-24T04:35:00Z",
            "records": [
                {
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/123",
                    "raw": parse_spinny_detail_text(DETAIL_PAGE_TEXT),
                }
            ],
        }

        merged = merge_spinny_detail_payload_into_listing_payload(
            listing_payload=listing_payload,
            detail_payload=detail_payload,
        )

        self.assertEqual(
            normalize_spinny_listing_url(listing_url),
            "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/123",
        )
        self.assertEqual(merged["records"][0]["raw"]["ownership"], "1st Owner")

    def test_plans_incremental_detail_from_existing_cache(self) -> None:
        listing_payload = build_spinny_payload_from_card_snapshots(
            source_url="https://www.spinny.com/example/s/",
            card_snapshots=[
                {
                    "text": LIVE_CARD_TEXT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/1/",
                },
                {
                    "text": LIVE_CARD_TEXT_WITH_ENGINE_SIZE_VARIANT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/skoda/slavia/example/2/",
                },
                {
                    "text": DELHI_CARD_TEXT_WITH_RTO_SUFFIX,
                    "listing_url": "https://www.spinny.com/buy-used-cars/delhi-ncr/kia/carens/example/3/",
                },
            ],
            captured_at="2026-06-24T04:30:00Z",
        )
        existing_detail_payload = {
            "source": "spinny",
            "records": [
                {
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/1/?utm=abc",
                    "raw": parse_spinny_detail_text(DETAIL_PAGE_TEXT),
                    "capture_status": "ok",
                }
            ],
        }

        plan = build_spinny_incremental_detail_plan(
            listing_payload=listing_payload,
            existing_detail_payloads=[existing_detail_payload],
            max_new_records=1,
        )

        self.assertEqual(plan["unique_listing_urls"], 3)
        self.assertEqual(plan["cache_hit_count"], 1)
        self.assertEqual(plan["pending_count"], 2)
        self.assertEqual(plan["selected_new_count"], 1)
        self.assertEqual(plan["skipped_over_new_cap"], 1)
        self.assertEqual(plan["detail_coverage_before_capture"], 0.3333)

    def test_builds_incremental_detail_payload_from_cache_and_new_records(self) -> None:
        listing_payload = build_spinny_payload_from_card_snapshots(
            source_url="https://www.spinny.com/example/s/",
            card_snapshots=[
                {
                    "text": LIVE_CARD_TEXT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/1/",
                },
                {
                    "text": LIVE_CARD_TEXT_WITH_ENGINE_SIZE_VARIANT,
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/skoda/slavia/example/2/",
                },
            ],
            captured_at="2026-06-24T04:30:00Z",
        )
        cached = {
            "source": "spinny",
            "records": [
                {
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/mahindra/xuv700/example/1/",
                    "raw": parse_spinny_detail_text(DETAIL_PAGE_TEXT),
                    "capture_status": "ok",
                }
            ],
        }
        new = {
            "source": "spinny",
            "records": [
                {
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/skoda/slavia/example/2/",
                    "raw": {"ownership": "2nd Owner", "rto": "TS07"},
                    "capture_status": "ok",
                    "attempts": 1,
                }
            ],
        }

        detail_payload = build_spinny_incremental_detail_payload(
            listing_payload=listing_payload,
            existing_detail_payloads=[cached],
            new_detail_payload=new,
            captured_at="2026-06-24T04:40:00Z",
            max_new_records=1,
        )
        merged = merge_spinny_detail_payload_into_listing_payload(
            listing_payload=listing_payload,
            detail_payload=detail_payload,
        )

        self.assertEqual(len(spinny_detail_cache_index([detail_payload])), 2)
        self.assertEqual(detail_payload["policy"]["cache_reused_records"], 1)
        self.assertEqual(detail_payload["policy"]["new_records_used"], 1)
        self.assertEqual(detail_payload["policy"]["missing_after_merge"], 0)
        self.assertEqual(merged["records"][0]["raw"]["ownership"], "1st Owner")
        self.assertEqual(merged["records"][1]["raw"]["ownership"], "2nd Owner")

    def test_summarizes_detail_payload_health(self) -> None:
        detail_payload = {
            "source": "spinny",
            "policy": {
                "max_records": 2,
                "attempted_records": 2,
                "attempts_per_record": 2,
                "timeout_ms": 60000,
                "delay_ms": 3000,
            },
            "records": [
                {
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/a/1/",
                    "raw": {"ownership": "1st Owner"},
                    "capture_status": "ok",
                    "attempts": 1,
                },
                {
                    "listing_url": "https://www.spinny.com/buy-used-cars/hyderabad/b/2/",
                    "raw": {},
                    "capture_status": "failed",
                    "failure_reason": "timeout",
                    "attempts": 2,
                },
            ],
        }

        summary = summarize_spinny_detail_payload(detail_payload)

        self.assertFalse(summary["ok"])
        self.assertEqual(summary["successful_records"], 1)
        self.assertEqual(summary["failed_records"], 1)
        self.assertEqual(summary["ownership_records"], 1)
        self.assertEqual(summary["timeout_count"], 1)
        self.assertEqual(summary["retries_used"], 1)


DETAIL_PAGE_TEXT = """Select city
HOME
USED CARS IN HYDERABAD
Car Overview
Make Year
Apr 2022
Registration Year
May 2022
Fuel Type
Petrol (BSVI)
Km driven
24K km
Transmission
Automatic (DCT)
No. of Owner
1st Owner
Insurance Validity
May 2027
Insurance Type
Comprehensive
RTO
TS07
Car Location
Kukatpally, Hyderabad
Quality report
1452 parts evaluated by 5 automotive experts
Meter not tampered
Non-flooded
Core structure intact
Core systems
Engine, transmission & chassis
9.8
Excellent
Supporting systems
Fuel supply, ignition & other systems
9.8
Excellent
Next service due after 12 months or 10,000 km
1 year
warranty
5-day
money back"""


if __name__ == "__main__":
    unittest.main()
