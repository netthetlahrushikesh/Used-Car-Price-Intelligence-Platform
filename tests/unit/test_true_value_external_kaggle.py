import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.external.true_value_kaggle import (
    EXPECTED_COLUMNS,
    TRUE_VALUE_KAGGLE_SOURCE,
    build_true_value_kaggle_package,
)


class TrueValueExternalKaggleTests(unittest.TestCase):
    def test_builds_separated_external_package_with_trusted_policy(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_dir = root / "raw"
            output_dir = root / "gold_external"
            profile_dir = root / "profile"
            input_dir.mkdir()
            _write_csv(
                input_dir / "train.csv",
                [
                    _row(
                        id="1",
                        car_name="maruti wagon r",
                        make="maruti",
                        model="wagon-r-1-0",
                        variant="vxi 1.0",
                        city="hyderabad",
                        rto="ts07",
                        sale_price="450000",
                    ),
                    _row(
                        id="2",
                        car_name="hyundai i20",
                        make="hyundai",
                        model="i20",
                        variant="sportz",
                        city="bengaluru",
                        rto="ka03",
                        sale_price="650000",
                    ),
                    _row(
                        id="3",
                        car_name="maruti swift",
                        make="maruti",
                        model="swift",
                        variant="vxi",
                        city="pune",
                        rto="mh12",
                        sale_price="520000",
                        assured_buy="False",
                        source="customer_to_customer",
                    ),
                ],
            )
            _write_csv(
                input_dir / "test.csv",
                [
                    _row(
                        id="1",
                        car_name="honda city",
                        make="honda",
                        model="city",
                        variant="vx",
                        city="mumbai",
                        rto="mh02",
                        sale_price="850000",
                    )
                ],
            )

            result = build_true_value_kaggle_package(
                input_dir=input_dir,
                output_dir=output_dir,
                profile_output_dir=profile_dir,
                generated_at="2026-06-28T03:00:00Z",
                min_group_size=1,
            )

            self.assertEqual(result["quality_summary"]["raw_rows"], 4)
            self.assertEqual(result["quality_summary"]["pricing_ready_rows"], 3)
            self.assertEqual(result["quality_summary"]["quarantine_rows"], 1)
            self.assertEqual(result["raw_profile"]["duplicate_checks"]["duplicate_id_count"], 1)
            self.assertEqual(result["dataset_manifest"]["source"], TRUE_VALUE_KAGGLE_SOURCE)

            with (output_dir / "listings_modeling_dataset.csv").open(encoding="utf-8") as file_obj:
                modeling_rows = list(csv.DictReader(file_obj))
            self.assertEqual(len(modeling_rows), 3)
            self.assertEqual({row["source"] for row in modeling_rows}, {TRUE_VALUE_KAGGLE_SOURCE})
            self.assertIn("Wagon R", {row["model"] for row in modeling_rows})

            quarantine = [
                json.loads(line)
                for line in (output_dir / "true_value_external_kaggle_quarantine.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(quarantine[0]["quarantine_reasons"], [
                "external_untrusted_customer_to_customer_channel",
                "external_assured_buy_false",
            ])


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "id": "1",
        "car_name": "maruti swift",
        "yr_mfr": "2018",
        "fuel_type": "petrol",
        "kms_run": "22000",
        "sale_price": "500000",
        "city": "hyderabad",
        "times_viewed": "100",
        "body_type": "hatchback",
        "transmission": "manual",
        "variant": "vxi",
        "assured_buy": "True",
        "registered_city": "hyderabad",
        "registered_state": "telangana",
        "is_hot": "False",
        "rto": "ts07",
        "source": "inperson_sale",
        "make": "maruti",
        "model": "swift",
        "car_availability": "in_stock",
        "total_owners": "1",
        "broker_quote": "490000",
        "original_price": "510000.0",
        "car_rating": "great",
        "ad_created_on": "2021-03-16T05:00:49.555",
        "fitness_certificate": "True",
        "emi_starts_from": "9000",
        "booking_down_pymnt": "50000",
        "reserved": "False",
        "warranty_avail": "False",
    }
    row.update(overrides)
    return row


if __name__ == "__main__":
    unittest.main()
