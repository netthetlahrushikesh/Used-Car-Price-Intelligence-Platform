import json
from pathlib import Path
import unittest

from used_car_price_intelligence.parsers import (
    parse_fuel_type,
    parse_km_driven,
    parse_ownership,
    parse_price_inr,
    parse_registration,
    parse_title,
    parse_transmission,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


class SourceFixtureParserTests(unittest.TestCase):
    def test_listing_card_fixtures_match_expected_parser_outputs(self) -> None:
        fixture_paths = sorted(FIXTURE_ROOT.glob("*/*_extracted.json"))
        self.assertGreaterEqual(len(fixture_paths), 4)

        for fixture_path in fixture_paths:
            with self.subTest(fixture=fixture_path.parent.name):
                payload = json.loads(fixture_path.read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(payload["records"]), 5)
                for record in payload["records"]:
                    raw = record["raw"]
                    expected = record["expected"]

                    title = parse_title(raw["title"])
                    self.assertTrue(title.ok, title)
                    self.assertEqual(title.normalized_value["model_year"], expected["model_year"])
                    self.assertEqual(title.normalized_value["brand"], expected["brand"])
                    self.assertEqual(title.normalized_value["model"], expected["model"])
                    if "variant" in expected:
                        self.assertEqual(title.normalized_value["variant"], expected["variant"])

                    price = parse_price_inr(raw["price"])
                    self.assertTrue(price.ok, price)
                    self.assertEqual(price.normalized_value, expected["listed_price_inr"])

                    km = parse_km_driven(raw["km"])
                    self.assertTrue(km.ok, km)
                    self.assertEqual(km.normalized_value, expected["km_driven"])

                    if raw.get("fuel") is not None:
                        fuel = parse_fuel_type(raw["fuel"])
                        self.assertTrue(fuel.ok, fuel)
                        self.assertEqual(fuel.normalized_value, expected["fuel_type"])

                    if raw.get("transmission") is not None:
                        transmission = parse_transmission(raw["transmission"])
                        self.assertTrue(transmission.ok, transmission)
                        self.assertEqual(transmission.normalized_value, expected["transmission"])

                    if raw.get("registration") is not None:
                        registration = parse_registration(raw["registration"])
                        self.assertTrue(registration.ok, registration)
                        self.assertEqual(
                            registration.normalized_value["registration_code"],
                            expected["registration_code"],
                        )
                        self.assertEqual(
                            registration.normalized_value["registration_state"],
                            expected["registration_state"],
                        )

                    if raw.get("owner_text") is not None:
                        ownership = parse_ownership(raw["owner_text"])
                        self.assertTrue(ownership.ok, ownership)
                        self.assertEqual(ownership.normalized_value, expected["ownership"])


if __name__ == "__main__":
    unittest.main()
