import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.experiments.three_model_phase import (
    EXTERNAL_ORIGIN,
    LIVE_ORIGIN,
    build_three_model_phase_package,
)
from used_car_price_intelligence.reporting import build_baseline_model_report
from used_car_price_intelligence.reporting.modeling_dataset import MODELING_COLUMNS


class ThreeModelPhaseTests(unittest.TestCase):
    def test_builds_combined_package_with_lineage_columns(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            live_dir = root / "live"
            external_dir = root / "external"
            output_dir = root / "experiment"
            live_dir.mkdir()
            external_dir.mkdir()
            live_rows = [
                _row("live_1", source="true_value", city="Hyderabad", brand="Maruti Suzuki", model="Swift", price=650000),
                _row("live_2", source="spinny", city="Pune", brand="Hyundai", model="i20", price=700000),
            ]
            external_rows = [
                _row("ext_1", source="true_value_external_kaggle", city="Hyderabad", brand="Maruti Suzuki", model="Swift", price=420000, capture_date="2021-05-30"),
                _row("ext_2", source="true_value_external_kaggle", city="Mumbai", brand="Honda", model="City", price=850000, capture_date="2021-05-30"),
            ]
            _write_dataset(live_dir, live_rows)
            _write_dataset(external_dir, external_rows)

            result = build_three_model_phase_package(
                live_dataset_csv=live_dir / "listings_modeling_dataset.csv",
                external_dataset_csv=external_dir / "listings_modeling_dataset.csv",
                output_dir=output_dir,
                generated_at="2026-06-28T04:00:00Z",
                min_group_size=1,
                test_ratio=0.5,
            )

            self.assertEqual(result["manifest"]["records_total"], 4)
            self.assertEqual(result["manifest"]["validation"]["status"], "pass")
            self.assertEqual({item["rows"] for item in result["registry"]["model_candidates"]}, {2, 4})

            with (output_dir / "combined_modeling_dataset.csv").open(encoding="utf-8") as file_obj:
                rows = list(csv.DictReader(file_obj))
            self.assertEqual(len(rows), 4)
            self.assertEqual({row["dataset_origin"] for row in rows}, {LIVE_ORIGIN, EXTERNAL_ORIGIN})
            self.assertEqual(len({row["listing_key"] for row in rows}), 4)
            self.assertTrue(all(row["original_listing_key"] for row in rows))
            self.assertTrue((output_dir / "experiment_registry.md").exists())


def _write_dataset(path: Path, rows: list[dict[str, object]]) -> None:
    dataset_csv = path / "listings_modeling_dataset.csv"
    with dataset_csv.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=MODELING_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    baseline = build_baseline_model_report(records=rows, min_group_size=1, test_ratio=0.5)
    (path / "baseline_model.json").write_text(json.dumps(baseline), encoding="utf-8")


def _row(
    listing_key: str,
    *,
    source: str,
    city: str,
    brand: str,
    model: str,
    price: int,
    capture_date: str = "2026-06-27",
) -> dict[str, object]:
    year = 2020
    return {
        "listing_key": listing_key,
        "source": source,
        "source_listing_id": f"{source}_{listing_key}",
        "listing_url": f"https://example.test/{source}/{listing_key}",
        "capture_date": capture_date,
        "captured_at": f"{capture_date}T09:00:00Z",
        "city": city,
        "state": "State",
        "brand": brand,
        "model": model,
        "variant": "VX",
        "brand_model": f"{brand} {model}",
        "model_year": year,
        "vehicle_age_years": 2026 - year,
        "fuel_type": "petrol",
        "transmission": "manual",
        "km_driven": 22000,
        "km_bucket_10000": 20000,
        "ownership": 1,
        "registration_code": "TS07",
        "listed_price_inr": price,
        "price_lakh": price / 100000,
        "is_available": "true",
        "observation_count": 1,
        "first_seen_at": f"{capture_date}T09:00:00Z",
        "last_seen_at": f"{capture_date}T09:00:00Z",
        "listing_identity_basis": "listing_url",
        "vehicle_fingerprint": f"vehicle_{listing_key}",
        "run_id": f"run_{source}",
        "baseline_split": "train",
    }


if __name__ == "__main__":
    unittest.main()
