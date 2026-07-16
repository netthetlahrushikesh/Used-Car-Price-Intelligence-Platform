import unittest

from used_car_price_intelligence.parsers import (
    is_price_like_text,
    normalize_null,
    parse_fuel_type,
    parse_km_driven,
    parse_ownership,
    parse_price_inr,
    parse_registration,
    parse_spinny_variant_from_listing_url,
    parse_title,
    parse_transmission,
)


class NormalizeNullTests(unittest.TestCase):
    def test_normalizes_known_empty_tokens(self) -> None:
        self.assertIsNone(normalize_null(None))
        self.assertIsNone(normalize_null(" NA "))
        self.assertIsNone(normalize_null("--"))
        self.assertEqual(normalize_null("  Hyundai Creta  "), "Hyundai Creta")


class PriceParserTests(unittest.TestCase):
    def test_parses_lakh_price(self) -> None:
        result = parse_price_inr("Rs 5.75L")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, 575000)

    def test_parses_comma_price(self) -> None:
        result = parse_price_inr("5,75,000")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, 575000)

    def test_parses_crore_price(self) -> None:
        result = parse_price_inr("1.02 Cr")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, 10200000)

    def test_warns_on_emi_text(self) -> None:
        result = parse_price_inr("EMI Rs 12,000")
        self.assertIn("price_text_contains_emi", result.warnings)

    def test_prefers_first_price_when_discount_card_has_multiple_prices(self) -> None:
        result = parse_price_inr("8.98 Lakh Rs 9.25 Lakh")

        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, 898000)
        self.assertIn("multiple_price_candidates", result.warnings)

    def test_identifies_price_like_variant_text_without_flagging_engine_text(self) -> None:
        self.assertTrue(is_price_like_text("Rs 7.27 Lakh"))
        self.assertTrue(is_price_like_text("\u20b97.27 Lakh"))
        self.assertFalse(is_price_like_text("Style 1.0L TSI AT"))


class SpinnyUrlParserTests(unittest.TestCase):
    def test_recovers_variant_from_listing_url_slug(self) -> None:
        variant = parse_spinny_variant_from_listing_url(
            "https://www.spinny.com/buy-used-cars/bangalore/hyundai/venue/"
            "sx-10-petrol-2019/29589252/"
        )

        self.assertEqual(variant, "SX 10 Petrol")

    def test_removes_spinny_hub_suffix_from_variant_slug(self) -> None:
        variant = parse_spinny_variant_from_listing_url(
            "https://www.spinny.com/buy-used-cars/bangalore/hyundai/grand-i10/"
            "sportz-o-12-kappa-vtvt-btm-layout-2018/30084370/"
        )

        self.assertEqual(variant, "Sportz (O) 12 Kappa VTVT")


class KilometerParserTests(unittest.TestCase):
    def test_parses_k_suffix(self) -> None:
        result = parse_km_driven("64K km")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, 64000)

    def test_parses_decimal_k_suffix(self) -> None:
        result = parse_km_driven("143.5K km")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, 143500)

    def test_parses_comma_kilometers(self) -> None:
        result = parse_km_driven("Driven 42,300 km")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, 42300)


class OwnershipParserTests(unittest.TestCase):
    def test_parses_first_owner(self) -> None:
        result = parse_ownership("First Owner")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, 1)

    def test_does_not_treat_direct_owner_as_count(self) -> None:
        result = parse_ownership("Direct Owner")
        self.assertFalse(result.ok)
        self.assertIn("owner_text_is_seller_type_not_owner_count", result.warnings)


class FuelParserTests(unittest.TestCase):
    def test_parses_petrol_cng(self) -> None:
        result = parse_fuel_type("Petrol + CNG")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, "petrol_cng")

    def test_parses_petrol_lpg(self) -> None:
        result = parse_fuel_type("Petrol+LPG")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, "petrol_lpg")

    def test_parses_ev(self) -> None:
        result = parse_fuel_type("EV")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, "electric")


class TransmissionParserTests(unittest.TestCase):
    def test_parses_amt_before_automatic(self) -> None:
        result = parse_transmission("AMT")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, "amt")

    def test_parses_at_as_automatic(self) -> None:
        result = parse_transmission("AT")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, "automatic")

    def test_parses_dsg_as_dct(self) -> None:
        result = parse_transmission("DSG")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value, "dct")

    def test_parses_imt_and_ivt_as_distinct_transmissions(self) -> None:
        imt = parse_transmission("IMT")
        ivt = parse_transmission("IVT")

        self.assertTrue(imt.ok)
        self.assertEqual(imt.normalized_value, "imt")
        self.assertTrue(ivt.ok)
        self.assertEqual(ivt.normalized_value, "ivt")


class RegistrationParserTests(unittest.TestCase):
    def test_parses_registration_code_and_state(self) -> None:
        result = parse_registration("TS-07")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["registration_code"], "TS07")
        self.assertEqual(result.normalized_value["registration_state"], "Telangana")

    def test_parses_full_registration_number_prefix(self) -> None:
        result = parse_registration("TS07AB1234")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["registration_code"], "TS07")
        self.assertEqual(result.normalized_value["registration_state"], "Telangana")

    def test_parses_state_only(self) -> None:
        result = parse_registration("Telangana")
        self.assertTrue(result.ok)
        self.assertIsNone(result.normalized_value["registration_code"])
        self.assertEqual(result.normalized_value["registration_state"], "Telangana")
        self.assertIn("registration_state_only", result.warnings)

    def test_parses_bharat_series_registration(self) -> None:
        result = parse_registration("22 BH 1234 AA")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["registration_code"], "BH")
        self.assertIsNone(result.normalized_value["registration_state"])
        self.assertEqual(result.normalized_value["registration_type"], "bharat_series")
        self.assertEqual(result.normalized_value["registration_year"], 2022)
        self.assertIn("bharat_series_registration", result.warnings)

    def test_parses_known_rto_location_alias(self) -> None:
        result = parse_registration("PORT BLAIR")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["registration_code"], "AN01")
        self.assertEqual(result.normalized_value["registration_state"], "Andaman and Nicobar Islands")
        self.assertEqual(result.normalized_value["registration_type"], "state_rto")
        self.assertIn("rto_location_alias", result.warnings)

    def test_parses_legacy_odisha_registration_prefix(self) -> None:
        result = parse_registration("OR18")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["registration_code"], "OD18")
        self.assertEqual(result.normalized_value["registration_state"], "Odisha")
        self.assertEqual(result.normalized_value["registration_type"], "state_rto")
        self.assertIn("legacy_registration_prefix", result.warnings)

    def test_parses_legacy_uttarakhand_registration_prefix(self) -> None:
        result = parse_registration("UA07")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["registration_code"], "UK07")
        self.assertEqual(result.normalized_value["registration_state"], "Uttarakhand")
        self.assertEqual(result.normalized_value["registration_type"], "state_rto")
        self.assertIn("legacy_registration_prefix", result.warnings)


class TitleParserTests(unittest.TestCase):
    def test_parses_year_brand_model_and_variant(self) -> None:
        result = parse_title("2021 Renault Kiger RXZ Turbo CVT")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["model_year"], 2021)
        self.assertEqual(result.normalized_value["brand"], "Renault")
        self.assertEqual(result.normalized_value["model"], "Kiger")
        self.assertEqual(result.normalized_value["variant"], "RXZ Turbo CVT")

    def test_parses_brand_alias_and_multi_word_model(self) -> None:
        result = parse_title("2022 Maruti Vitara Brezza ZXI Plus Dual Tone")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["brand"], "Maruti Suzuki")
        self.assertEqual(result.normalized_value["model"], "Vitara Brezza")
        self.assertEqual(result.normalized_value["variant"], "ZXI Plus Dual Tone")

    def test_parses_live_spinny_model_families(self) -> None:
        examples = {
            "2022 Maruti Brezza VXI": ("Maruti Suzuki", "Brezza"),
            "2022 Mahindra XUV700 AX5": ("Mahindra", "XUV700"),
            "2022 Tata Nexon XM": ("Tata", "Nexon"),
            "2024 Volkswagen Taigun GT": ("Volkswagen", "Taigun"),
            "2023 Skoda Slavia Style": ("Skoda", "Slavia"),
            "2021 Kia Sonet HTX": ("Kia", "Sonet"),
            "2021 Toyota Innova Hycross VX Hybrid": ("Toyota", "Innova Hycross"),
            "2017 Audi A4 Premium Plus": ("Audi", "A4"),
            "2023 Mercedes GLA Class 200": ("Mercedes-Benz", "GLA Class"),
            "2019 Jeep Compass Limited Plus": ("Jeep", "Compass"),
            "2022 Tata Harrier XZA": ("Tata", "Harrier"),
            "2017 Skoda Octavia Style": ("Skoda", "Octavia"),
            "2023 Mahindra Scorpio N Z8": ("Mahindra", "Scorpio N"),
            "2024 BYD Seal Premium": ("BYD", "Seal"),
            "2023 BMW X1 sDrive18d": ("BMW", "X1"),
            "2021 Mercedes GLC 200": ("Mercedes-Benz", "GLC"),
            "2023 Audi Q3 Premium Plus": ("Audi", "Q3"),
            "2018 Jaguar XE Prestige Diesel": ("Jaguar", "XE"),
            "2020 Lexus NX 300h Luxury": ("Lexus", "NX"),
            "2014 Mini Countryman One": ("Mini", "Countryman"),
            "2022 Toyota Urban Cruiser Hyryder V AWD": ("Toyota", "Urban Cruiser Hyryder"),
            "2021 Hyundai Grand i10 Nios Asta": ("Hyundai", "Grand i10 Nios"),
            "2016 Hyundai Fluidic Verna 4S SX": ("Hyundai", "Fluidic Verna 4S"),
            "2023 Skoda Kushaq Style": ("Skoda", "Kushaq"),
            "2022 Tata Nexon EV XZ Plus": ("Tata", "Nexon EV"),
            "2023 Volkswagen Virtus Topline": ("Volkswagen", "Virtus"),
            "2018 Ford EcoSport Titanium": ("Ford", "EcoSport"),
            "2024 Honda Elevate ZX": ("Honda", "Elevate"),
        }

        for title, expected in examples.items():
            with self.subTest(title=title):
                result = parse_title(title)
                self.assertTrue(result.ok, result)
                self.assertEqual(result.normalized_value["brand"], expected[0])
                self.assertEqual(result.normalized_value["model"], expected[1])

    def test_parses_longest_model_match_first(self) -> None:
        result = parse_title("2021 MG Hector Plus")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["brand"], "MG")
        self.assertEqual(result.normalized_value["model"], "Hector Plus")

    def test_keeps_ev_model_family_when_ev_is_part_of_model_name(self) -> None:
        result = parse_title("2021 Tata Tigor EV")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["brand"], "Tata")
        self.assertEqual(result.normalized_value["model"], "Tigor EV")
        self.assertIsNone(result.normalized_value["variant"])

    def test_keeps_engine_suffix_out_of_model_family(self) -> None:
        result = parse_title("2022 Maruti Suzuki Wagon-R-1-0")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["brand"], "Maruti Suzuki")
        self.assertEqual(result.normalized_value["model"], "Wagon R")
        self.assertIsNone(result.normalized_value["variant"])

    def test_handles_hyphenated_family_model(self) -> None:
        result = parse_title("2019 Maruti Suzuki Vitara-Brezza")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["model"], "Vitara Brezza")
        self.assertIsNone(result.normalized_value["variant"])

    def test_handles_multi_word_model_without_variant(self) -> None:
        result = parse_title("2017 Nissan Micra Active")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["model"], "Micra Active")
        self.assertIsNone(result.normalized_value["variant"])

    def test_parses_year_at_end(self) -> None:
        result = parse_title("Maruti Suzuki Baleno Delta 2019")
        self.assertTrue(result.ok)
        self.assertEqual(result.normalized_value["model_year"], 2019)
        self.assertEqual(result.normalized_value["brand"], "Maruti Suzuki")
        self.assertEqual(result.normalized_value["model"], "Baleno")
        self.assertEqual(result.normalized_value["variant"], "Delta")

    def test_missing_year_is_not_gold_ready(self) -> None:
        result = parse_title("Honda City VX CVT Petrol")
        self.assertFalse(result.ok)
        self.assertIn("missing_model_year", result.warnings)


if __name__ == "__main__":
    unittest.main()
