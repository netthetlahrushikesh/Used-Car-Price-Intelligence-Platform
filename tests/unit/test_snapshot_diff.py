import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.reporting import (
    build_snapshot_diff,
    render_snapshot_diff_markdown,
    write_snapshot_diff_json,
    write_snapshot_diff_markdown,
)


class SnapshotDiffTests(unittest.TestCase):
    def test_builds_baseline_snapshot_without_previous_lifecycle(self) -> None:
        with TemporaryDirectory() as tmpdir:
            current_path = Path(tmpdir) / "current_lifecycle.json"
            write_lifecycle(
                current_path,
                lifecycle_id="lifecycle_current",
                entities=[
                    lifecycle_entity("listing_a", source="spinny", price=500000, km=10000),
                    lifecycle_entity("listing_b", source="true_value", price=600000, km=12000),
                ],
            )

            diff = build_snapshot_diff(
                snapshot_id="snapshot_baseline",
                snapshot_date="2026-06-26",
                current_lifecycle_path=current_path,
                generated_at="2026-06-26T00:00:00Z",
            )

        self.assertTrue(diff["policy"]["baseline_mode"])
        self.assertEqual(diff["totals"]["previous_unique_listing_keys"], 0)
        self.assertEqual(diff["totals"]["current_unique_listing_keys"], 2)
        self.assertEqual(diff["totals"]["added_count"], 2)
        self.assertEqual(diff["totals"]["removed_count"], 0)
        self.assertEqual(diff["totals"]["still_active_count"], 0)
        self.assertEqual(diff["totals"]["by_source"]["spinny"]["added"], 1)
        self.assertEqual(diff["totals"]["by_source"]["true_value"]["added"], 1)

    def test_builds_added_removed_still_active_and_numeric_changes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            previous_path = Path(tmpdir) / "previous_lifecycle.json"
            current_path = Path(tmpdir) / "current_lifecycle.json"
            write_lifecycle(
                previous_path,
                lifecycle_id="lifecycle_previous",
                entities=[
                    lifecycle_entity(
                        "listing_a",
                        source="spinny",
                        price=500000,
                        km=10000,
                        captured_at="2026-06-26T01:00:00Z",
                        run_id="run_previous_a",
                    ),
                    lifecycle_entity("listing_b", source="mahindra_first_choice", price=650000, km=20000),
                ],
            )
            write_lifecycle(
                current_path,
                lifecycle_id="lifecycle_current",
                entities=[
                    lifecycle_entity(
                        "listing_a",
                        source="spinny",
                        price=475000,
                        km=12500,
                        captured_at="2026-06-27T01:00:00Z",
                        run_id="run_current_a",
                    ),
                    lifecycle_entity("listing_c", source="true_value", price=700000, km=9000),
                ],
            )

            diff = build_snapshot_diff(
                snapshot_id="snapshot_current",
                current_lifecycle_path=current_path,
                previous_lifecycle_path=previous_path,
            )

        self.assertFalse(diff["policy"]["baseline_mode"])
        self.assertEqual(diff["totals"]["added_count"], 1)
        self.assertEqual(diff["totals"]["removed_count"], 1)
        self.assertEqual(diff["totals"]["still_active_count"], 1)
        self.assertEqual(diff["totals"]["price_change_count"], 1)
        self.assertEqual(diff["totals"]["km_change_count"], 1)
        self.assertEqual(diff["added_listings"][0]["listing_key"], "listing_c")
        self.assertEqual(diff["removed_listings"][0]["listing_key"], "listing_b")
        self.assertEqual(diff["still_active_listings"][0]["listing_key"], "listing_a")
        self.assertEqual(diff["price_changes"][0]["price_delta_inr"], -25000)
        self.assertEqual(diff["price_changes"][0]["price_delta_pct"], -5.0)
        self.assertEqual(diff["km_changes"][0]["km_delta"], 2500)
        self.assertEqual(diff["totals"]["by_source"]["spinny"]["price_changes"], 1)
        self.assertEqual(diff["totals"]["by_source"]["mahindra_first_choice"]["removed"], 1)
        self.assertEqual(diff["totals"]["by_source"]["true_value"]["added"], 1)

    def test_renders_and_writes_snapshot_outputs(self) -> None:
        diff = {
            "snapshot_id": "snapshot_test",
            "snapshot_date": "2026-06-26",
            "generated_at": "2026-06-26T00:00:00Z",
            "policy": {
                "baseline_mode": True,
                "identity_key": "Lifecycle listing_key.",
                "removed_definition": "Absent from current lifecycle.",
                "change_detection": "Compare latest observations.",
            },
            "inputs": {
                "previous_lifecycle_id": "",
                "current_lifecycle_id": "lifecycle_current",
            },
            "totals": {
                "previous_unique_listing_keys": 0,
                "current_unique_listing_keys": 1,
                "added_count": 1,
                "removed_count": 0,
                "still_active_count": 0,
                "price_change_count": 0,
                "km_change_count": 0,
                "by_source": {
                    "spinny": {
                        "previous": 0,
                        "current": 1,
                        "added": 1,
                        "removed": 0,
                        "still_active": 0,
                        "price_changes": 0,
                        "km_changes": 0,
                    }
                },
            },
            "added_listings": [lifecycle_listing_snapshot()],
            "removed_listings": [],
            "price_changes": [],
            "km_changes": [],
        }

        report = render_snapshot_diff_markdown(diff)

        self.assertIn("# Snapshot Diff Report", report)
        self.assertIn("Baseline mode: yes", report)
        self.assertIn("| spinny | 0 | 1 | 1 | 0 | 0 | 0 | 0 |", report)

        with TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "snapshot.json"
            md_path = Path(tmpdir) / "snapshot.md"

            self.assertEqual(write_snapshot_diff_json(json_path, diff), json_path)
            self.assertEqual(write_snapshot_diff_markdown(md_path, diff), md_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())


def write_lifecycle(path: Path, *, lifecycle_id: str, entities: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "lifecycle_id": lifecycle_id,
                "collection_id": f"collection_{lifecycle_id}",
                "listing_entities": entities,
            }
        ),
        encoding="utf-8",
    )


def lifecycle_entity(
    listing_key: str,
    *,
    source: str,
    price: int,
    km: int,
    captured_at: str = "2026-06-26T01:00:00Z",
    run_id: str = "run_current",
) -> dict:
    return {
        "listing_key": listing_key,
        "source": source,
        "observation_count": 1,
        "first_seen_at": captured_at,
        "last_seen_at": captured_at,
        "capture_dates": [captured_at[:10]],
        "run_ids": [run_id],
        "latest_observation": {
            "listing_key": listing_key,
            "source": source,
            "source_listing_id": listing_key,
            "listing_url": f"https://example.com/{listing_key}",
            "run_id": run_id,
            "capture_date": captured_at[:10],
            "captured_at": captured_at,
            "city": "Hyderabad",
            "state": "Telangana",
            "brand": "Maruti Suzuki",
            "model": "Wagon R",
            "variant": "VXI",
            "model_year": 2022,
            "fuel_type": "petrol",
            "transmission": "manual",
            "km_driven": km,
            "ownership": 1,
            "registration_code": "TS07",
            "listed_price_inr": price,
            "is_available": True,
        },
    }


def lifecycle_listing_snapshot() -> dict:
    return {
        "listing_key": "listing_a",
        "source": "spinny",
        "city": "Hyderabad",
        "state": "Telangana",
        "brand": "Maruti Suzuki",
        "model": "Wagon R",
        "variant": "VXI",
        "model_year": 2022,
        "fuel_type": "petrol",
        "transmission": "manual",
        "km_driven": 10000,
        "ownership": 1,
        "registration_code": "TS07",
        "listed_price_inr": 500000,
        "listing_url": "https://example.com/listing_a",
        "source_listing_id": "listing_a",
        "is_available": True,
        "observation_count": 1,
        "first_seen_at": "2026-06-26T01:00:00Z",
        "last_seen_at": "2026-06-26T01:00:00Z",
        "capture_dates": ["2026-06-26"],
        "run_ids": ["run_current"],
    }


if __name__ == "__main__":
    unittest.main()
