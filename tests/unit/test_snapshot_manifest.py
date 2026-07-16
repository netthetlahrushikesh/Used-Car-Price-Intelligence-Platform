import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.reporting import (
    build_snapshot_manifest,
    render_snapshot_manifest_markdown,
    write_snapshot_manifest_json,
    write_snapshot_manifest_markdown,
)


class SnapshotManifestTests(unittest.TestCase):
    def test_builds_manifest_from_ledger_lifecycle_and_diff(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ledger_path = root / "ledger.json"
            lifecycle_path = root / "lifecycle.json"
            diff_path = root / "diff.json"
            write_ledger(ledger_path)
            write_lifecycle(lifecycle_path)
            write_diff(diff_path)

            manifest = build_snapshot_manifest(
                snapshot_id="snapshot_current",
                snapshot_date="2026-06-26",
                collection_ledger_path=ledger_path,
                lifecycle_index_path=lifecycle_path,
                snapshot_diff_path=diff_path,
                target_pricing_ready=10,
                previous_snapshot_id="snapshot_previous",
                previous_lifecycle_id="lifecycle_previous",
                scope_change_vs_previous="Added MFC probe city.",
                generated_at="2026-06-27T00:00:00Z",
            )

        self.assertEqual(manifest["collection_id"], "trusted_collection_test")
        self.assertEqual(manifest["lifecycle_id"], "lifecycle_current")
        self.assertEqual(manifest["totals"]["pricing_ready"], 5)
        self.assertEqual(manifest["totals"]["unique_listing_keys"], 4)
        self.assertEqual(manifest["totals"]["source_runs"], 3)
        self.assertEqual(manifest["totals"]["listing_source_runs"], 2)
        self.assertEqual(manifest["totals"]["no_inventory_source_runs"], 1)
        self.assertEqual(manifest["totals"]["rows_under_target"], 5)
        self.assertEqual(manifest["totals"]["by_source"]["mahindra_first_choice"]["no_inventory_source_runs"], 1)
        self.assertEqual(manifest["diff_vs_previous"]["added_count"], 2)
        self.assertEqual(manifest["scope"]["cities"], ["Hyderabad", "Vadodara"])
        self.assertEqual(manifest["validation"]["status"], "pass")

    def test_rejects_mismatched_ledger_and_lifecycle_counts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ledger_path = root / "ledger.json"
            lifecycle_path = root / "lifecycle.json"
            write_ledger(ledger_path)
            write_lifecycle(lifecycle_path, records_total=4)

            with self.assertRaisesRegex(ValueError, "ledger_pricing_ready_matches_lifecycle_records"):
                build_snapshot_manifest(
                    snapshot_id="snapshot_bad",
                    snapshot_date="2026-06-26",
                    collection_ledger_path=ledger_path,
                    lifecycle_index_path=lifecycle_path,
                )

    def test_renders_and_writes_snapshot_manifest_outputs(self) -> None:
        manifest = {
            "snapshot_id": "snapshot_current",
            "snapshot_date": "2026-06-26",
            "status": "pass",
            "collection_id": "trusted_collection_test",
            "lifecycle_id": "lifecycle_current",
            "totals": {
                "pricing_ready": 5,
                "quarantined": 0,
                "unique_listing_keys": 4,
                "source_runs": 3,
                "listing_source_runs": 2,
                "no_inventory_source_runs": 1,
                "by_source": {
                    "spinny": {
                        "source_runs": 1,
                        "listing_source_runs": 1,
                        "no_inventory_source_runs": 0,
                        "pricing_ready": 2,
                        "quarantined": 0,
                        "source_total_signal": 0,
                    }
                },
            },
            "scope": {"sources": ["spinny"], "cities": ["Hyderabad"]},
            "validation": {"status": "pass", "checks": [{"name": "counts", "status": "pass"}]},
        }

        report = render_snapshot_manifest_markdown(manifest)

        self.assertIn("# Snapshot Manifest", report)
        self.assertIn("Pricing-ready rows: 5", report)
        self.assertIn("| spinny | 1 | 1 | 0 | 2 | 0 | 0 |", report)

        with TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "manifest.json"
            md_path = Path(tmpdir) / "manifest.md"

            self.assertEqual(write_snapshot_manifest_json(json_path, manifest), json_path)
            self.assertEqual(write_snapshot_manifest_markdown(md_path, manifest), md_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())


def write_ledger(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "collection_id": "trusted_collection_test",
                "totals": {
                    "source_runs": 3,
                    "pricing_ready": 5,
                    "quarantined": 0,
                    "source_total_signal": 7,
                },
                "rows": [
                    {
                        "source": "spinny",
                        "city": "Hyderabad",
                        "status": "pass",
                        "pricing_ready": 2,
                        "quarantined": 0,
                        "source_total_items": 0,
                    },
                    {
                        "source": "mahindra_first_choice",
                        "city": "Hyderabad",
                        "status": "pass",
                        "pricing_ready": 3,
                        "quarantined": 0,
                        "source_total_items": 7,
                    },
                    {
                        "source": "mahindra_first_choice",
                        "city": "Vadodara",
                        "status": "no_inventory",
                        "pricing_ready": 0,
                        "quarantined": 0,
                        "source_total_items": 0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def write_lifecycle(path: Path, *, records_total: int = 5) -> None:
    path.write_text(
        json.dumps(
            {
                "lifecycle_id": "lifecycle_current",
                "collection_id": "trusted_collection_test",
                "totals": {
                    "records_total": records_total,
                    "source_runs": 2,
                    "unique_listing_keys": 4,
                    "possible_vehicle_duplicate_groups": 1,
                },
            }
        ),
        encoding="utf-8",
    )


def write_diff(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "totals": {
                    "previous_unique_listing_keys": 2,
                    "current_unique_listing_keys": 4,
                    "added_count": 2,
                    "removed_count": 0,
                    "still_active_count": 2,
                    "price_change_count": 0,
                    "km_change_count": 0,
                    "changed_listing_count": 0,
                    "by_source": {
                        "spinny": {
                            "previous": 1,
                            "current": 2,
                            "added": 1,
                            "removed": 0,
                            "still_active": 1,
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
