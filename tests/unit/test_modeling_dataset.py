import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from used_car_price_intelligence.cli import main
from used_car_price_intelligence.reporting import (
    build_modeling_dataset_package,
    render_baseline_model_markdown,
    render_eda_summary_markdown,
    write_modeling_dataset_package,
)


class ModelingDatasetTests(unittest.TestCase):
    def test_builds_modeling_dataset_package_from_snapshot_lifecycle(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "lifecycle.json"
            manifest_path = root / "snapshot_manifest.json"
            write_lifecycle(lifecycle_path)
            write_snapshot_manifest(manifest_path, lifecycle_path)

            package = build_modeling_dataset_package(
                snapshot_manifest_path=manifest_path,
                generated_at="2026-06-27T10:00:00Z",
                test_ratio=0.25,
                min_group_size=1,
            )

        self.assertEqual(package["manifest"]["dataset_id"], "snapshot_test_modeling_v0")
        self.assertEqual(package["manifest"]["validation"]["status"], "pass")
        self.assertEqual(len(package["records"]), 8)
        self.assertIn(6, {record["vehicle_age_years"] for record in package["records"]})
        self.assertEqual(package["eda_summary"]["records_total"], 8)
        self.assertEqual(package["eda_summary"]["counts"]["source"][0]["value"], "true_value")
        self.assertEqual(package["baseline_model"]["split"]["train_rows"] + package["baseline_model"]["split"]["test_rows"], 8)
        self.assertGreater(package["baseline_model"]["metrics"]["count"], 0)
        self.assertIn("listed_price_inr", {item["name"] for item in package["data_dictionary"]["columns"]})

    def test_writes_modeling_dataset_artifacts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "lifecycle.json"
            manifest_path = root / "snapshot_manifest.json"
            output_dir = root / "modeling"
            write_lifecycle(lifecycle_path)
            write_snapshot_manifest(manifest_path, lifecycle_path)
            package = build_modeling_dataset_package(snapshot_manifest_path=manifest_path, min_group_size=1)

            output_paths = write_modeling_dataset_package(output_dir=output_dir, package=package)

            self.assertTrue(Path(output_paths["dataset_csv"]).exists())
            self.assertTrue(Path(output_paths["eda_summary_markdown"]).exists())
            self.assertTrue(Path(output_paths["baseline_model_markdown"]).exists())
            self.assertTrue(Path(output_paths["dataset_manifest_json"]).exists())
            with Path(output_paths["dataset_csv"]).open(encoding="utf-8") as file_obj:
                rows = list(csv.DictReader(file_obj))
            self.assertEqual(len(rows), 8)
            written_manifest = json.loads(Path(output_paths["dataset_manifest_json"]).read_text(encoding="utf-8"))
            self.assertEqual(written_manifest["outputs"]["dataset_csv"], output_paths["dataset_csv"])

    def test_rejects_missing_required_modeling_fields(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "lifecycle.json"
            manifest_path = root / "snapshot_manifest.json"
            write_lifecycle(lifecycle_path, missing_brand=True)
            write_snapshot_manifest(manifest_path, lifecycle_path)

            with self.assertRaisesRegex(ValueError, "required_modeling_fields_complete"):
                build_modeling_dataset_package(snapshot_manifest_path=manifest_path)

    def test_renders_eda_and_baseline_markdown(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "lifecycle.json"
            manifest_path = root / "snapshot_manifest.json"
            write_lifecycle(lifecycle_path)
            write_snapshot_manifest(manifest_path, lifecycle_path)
            package = build_modeling_dataset_package(snapshot_manifest_path=manifest_path, min_group_size=1)

        eda_report = render_eda_summary_markdown(package["eda_summary"])
        baseline_report = render_baseline_model_markdown(package["baseline_model"])

        self.assertIn("# Final Snapshot EDA Summary", eda_report)
        self.assertIn("## Source Mix", eda_report)
        self.assertIn("# Baseline Pricing Model", baseline_report)
        self.assertIn("Comparable median", baseline_report)

    def test_cli_packages_modeling_dataset(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lifecycle_path = root / "lifecycle.json"
            manifest_path = root / "snapshot_manifest.json"
            output_dir = root / "modeling"
            write_lifecycle(lifecycle_path)
            write_snapshot_manifest(manifest_path, lifecycle_path)

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "package-modeling-dataset",
                        "--snapshot-manifest",
                        str(manifest_path),
                        "--output-dir",
                        str(output_dir),
                        "--min-group-size",
                        "1",
                    ]
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(print_mock.call_args.args[0], (output_dir / "dataset_manifest.md").as_posix())
            self.assertTrue((output_dir / "listings_modeling_dataset.csv").exists())


def write_snapshot_manifest(path: Path, lifecycle_path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "snapshot_id": "snapshot_test",
                "snapshot_date": "2026-06-27",
                "collection_id": "collection_test",
                "paths": {"lifecycle_index": str(lifecycle_path)},
                "totals": {
                    "pricing_ready": 8,
                    "unique_listing_keys": 8,
                    "by_source": {
                        "true_value": {"pricing_ready": 4},
                        "spinny": {"pricing_ready": 2},
                        "mahindra_first_choice": {"pricing_ready": 2},
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def write_lifecycle(path: Path, *, missing_brand: bool = False) -> None:
    records = [
        ("true_value", "Hyderabad", "Maruti Suzuki", "Swift", 2020, "petrol", "manual", 22000, 1, 650000),
        ("true_value", "Hyderabad", "Maruti Suzuki", "Swift", 2021, "petrol", "manual", 18000, 1, 700000),
        ("true_value", "Bengaluru", "Hyundai", "i20", 2019, "petrol", "manual", 35000, 1, 620000),
        ("true_value", "Bengaluru", "Hyundai", "i20", 2020, "petrol", "manual", 28000, 1, 680000),
        ("spinny", "Delhi NCR", "Tata", "Nexon", 2021, "diesel", "manual", 30000, 1, 900000),
        ("spinny", "Delhi NCR", "Tata", "Nexon", 2022, "diesel", "manual", 16000, 1, 1050000),
        ("mahindra_first_choice", "Pune", "Honda", "City", 2018, "petrol", "automatic", 45000, 2, 780000),
        ("mahindra_first_choice", "Pune", "Honda", "City", 2019, "petrol", "automatic", 39000, 1, 860000),
    ]
    entities = []
    for index, record in enumerate(records, start=1):
        source, city, brand, model, year, fuel, transmission, km, ownership, price = record
        if missing_brand and index == 1:
            brand = ""
        listing_key = f"listing_{index:03d}"
        observation = {
            "listing_key": listing_key,
            "source": source,
            "source_listing_id": f"{source}_{index}",
            "listing_url": f"https://example.com/{source}/{index}",
            "run_id": f"run_{source}",
            "capture_date": "2026-06-27",
            "captured_at": "2026-06-27T09:00:00Z",
            "city": city,
            "state": "State",
            "brand": brand,
            "model": model,
            "variant": "VX",
            "model_year": year,
            "fuel_type": fuel,
            "transmission": transmission,
            "km_driven": km,
            "ownership": ownership,
            "registration_code": "TS07",
            "listed_price_inr": price,
            "is_available": True,
        }
        entities.append(
            {
                "listing_key": listing_key,
                "source": source,
                "listing_identity_basis": "listing_url",
                "vehicle_fingerprint": f"vehicle_{index:03d}",
                "observation_count": 1,
                "first_seen_at": "2026-06-27T09:00:00Z",
                "last_seen_at": "2026-06-27T09:00:00Z",
                "run_ids": [f"run_{source}"],
                "latest_observation": observation,
            }
        )
    path.write_text(
        json.dumps(
            {
                "lifecycle_id": "lifecycle_test",
                "collection_id": "collection_test",
                "totals": {"records_total": 8, "unique_listing_keys": 8},
                "listing_entities": entities,
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
