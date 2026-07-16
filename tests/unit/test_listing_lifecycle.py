import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.reporting import (
    build_listing_lifecycle_index,
    render_listing_lifecycle_markdown,
    write_listing_lifecycle_json,
    write_listing_lifecycle_markdown,
)


class ListingLifecycleTests(unittest.TestCase):
    def test_builds_lifecycle_index_from_collection_ledger(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            spinny_first = write_run_with_silver(
                root,
                source="spinny",
                run_id="run_spinny_first",
                capture_date="2026-06-26",
                captured_at="2026-06-26T01:00:00Z",
                listing_url="https://example.com/car/123/?utm=abc",
                source_listing_id="spinny_123",
            )
            spinny_second = write_run_with_silver(
                root,
                source="spinny",
                run_id="run_spinny_second",
                capture_date="2026-06-27",
                captured_at="2026-06-27T01:00:00Z",
                listing_url="https://example.com/car/123/",
                source_listing_id="spinny_123",
            )
            true_value = write_run_with_silver(
                root,
                source="true_value",
                run_id="run_true_value",
                capture_date="2026-06-27",
                captured_at="2026-06-27T02:00:00Z",
                listing_url="https://truevalue.example/car/999",
                source_listing_id="tv_999",
            )
            ledger_path = root / "ledger.json"
            ledger_path.write_text(
                json.dumps(
                    {
                        "collection_id": "trusted_collection_test",
                        "rows": [
                            {"manifest_path": str(spinny_first), "status": "pass"},
                            {"manifest_path": str(spinny_second), "status": "pass"},
                            {"manifest_path": str(true_value), "status": "pass"},
                            {"manifest_path": str(root / "missing_no_inventory_manifest.json"), "status": "no_inventory"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            index = build_listing_lifecycle_index(
                lifecycle_id="lifecycle_test",
                collection_ledger_path=ledger_path,
                generated_at="2026-06-28T00:00:00Z",
            )

        self.assertEqual(index["collection_id"], "trusted_collection_test")
        self.assertEqual(index["totals"]["records_total"], 3)
        self.assertEqual(index["totals"]["unique_listing_keys"], 2)
        self.assertEqual(index["totals"]["reobserved_listing_groups"], 1)
        self.assertEqual(index["totals"]["possible_vehicle_duplicate_groups"], 1)
        self.assertEqual(index["totals"]["by_source"]["spinny"]["records"], 2)
        self.assertEqual(index["totals"]["by_source"]["spinny"]["unique_listing_keys"], 1)
        self.assertEqual(index["listing_entities"][0]["observation_count"], 2)
        self.assertEqual(index["possible_vehicle_duplicate_groups"][0]["listing_key_count"], 2)

    def test_renders_and_writes_lifecycle_outputs(self) -> None:
        index = {
            "lifecycle_id": "lifecycle_test",
            "collection_id": "trusted_collection_test",
            "generated_at": "2026-06-28T00:00:00Z",
            "policy": {
                "version": "listing_lifecycle_policy_v0.1",
                "listing_key": "source plus normalized listing URL",
                "vehicle_fingerprint": "conservative possible duplicate key",
                "km_bucket_size": 5000,
                "price_bucket_size": 50000,
                "note": "Vehicle fingerprints are review signals, not automatic merge keys.",
            },
            "totals": {
                "records_total": 3,
                "source_runs": 3,
                "unique_listing_keys": 2,
                "reobserved_listing_groups": 1,
                "possible_vehicle_duplicate_groups": 1,
                "by_source": {
                    "spinny": {
                        "records": 2,
                        "unique_listing_keys": 1,
                        "reobserved_listing_groups": 1,
                        "possible_vehicle_duplicate_groups": 1,
                    }
                },
            },
            "reobserved_listing_groups": [
                {
                    "listing_key": "listing_abc",
                    "source": "spinny",
                    "observation_count": 2,
                    "first_seen_at": "2026-06-26T01:00:00Z",
                    "last_seen_at": "2026-06-27T01:00:00Z",
                }
            ],
            "possible_vehicle_duplicate_groups": [
                {
                    "vehicle_fingerprint": "vehicle_abc",
                    "observation_count": 2,
                    "sources": ["spinny", "true_value"],
                    "cities": ["Hyderabad"],
                    "observations": [
                        {
                            "source": "spinny",
                            "city": "Hyderabad",
                            "model_year": 2022,
                            "brand": "Maruti Suzuki",
                            "model": "Wagon R",
                            "listed_price_inr": 500000,
                        }
                    ],
                }
            ],
        }

        report = render_listing_lifecycle_markdown(index)

        self.assertIn("# Listing Lifecycle Index", report)
        self.assertIn("Possible vehicle duplicate groups: 1", report)
        self.assertIn("| spinny | 2 | 1 | 1 | 1 |", report)

        with TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "lifecycle.json"
            md_path = Path(tmpdir) / "lifecycle.md"

            self.assertEqual(write_listing_lifecycle_json(json_path, index), json_path)
            self.assertEqual(write_listing_lifecycle_markdown(md_path, index), md_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())


def write_run_with_silver(
    root: Path,
    *,
    source: str,
    run_id: str,
    capture_date: str,
    captured_at: str,
    listing_url: str,
    source_listing_id: str,
) -> Path:
    silver_path = root / "silver" / f"{source}_{run_id}_silver.json"
    silver_path.parent.mkdir(parents=True, exist_ok=True)
    silver_path.write_text(
        json.dumps(
            [
                {
                    "source": source,
                    "source_listing_id": source_listing_id,
                    "listing_url": listing_url,
                    "captured_at": captured_at,
                    "city": "Hyderabad",
                    "state": "Telangana",
                    "brand": "Maruti Suzuki",
                    "model": "Wagon R",
                    "variant": "VXI",
                    "model_year": 2022,
                    "fuel_type": "petrol",
                    "transmission": "manual",
                    "km_driven": 12345,
                    "ownership": 1,
                    "registration_code": "TS07",
                    "listed_price_inr": 500000,
                    "is_available": True,
                    "raw_record_hash": f"hash_{source}_{run_id}",
                    "ingestion_run_id": run_id,
                }
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = root / "manifests" / f"{source}_{run_id}_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "source": source,
                "run_id": run_id,
                "status": "pass",
                "capture_date": capture_date,
                "captured_at": captured_at,
                "city": "Hyderabad",
                "state": "Telangana",
                "output_paths": {
                    "silver": str(silver_path),
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


if __name__ == "__main__":
    unittest.main()
