import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.reporting import (
    build_scale_projection,
    render_scale_projection_markdown,
    write_scale_projection_json,
    write_scale_projection_markdown,
)


class ScaleProjectionTests(unittest.TestCase):
    def test_projects_100k_target_from_current_snapshot_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "snapshot_manifest.json"
            write_snapshot_manifest(manifest_path, pricing_ready=909)

            projection = build_scale_projection(
                target_id="target_100k",
                target_observations=100_000,
                current_snapshot_manifest_path=manifest_path,
                recommended_rows_per_snapshot=5_000,
                generated_at="2026-06-26T00:00:00Z",
            )

        self.assertEqual(projection["current"]["trusted_observations"], 909)
        self.assertEqual(projection["remaining_observations"], 99_091)
        self.assertEqual(projection["scenarios"]["current_checkpoint_size"]["rows_per_snapshot"], 909)
        self.assertEqual(projection["scenarios"]["original_baseline_scope"]["rows_per_snapshot"], 909)
        self.assertEqual(projection["scenarios"]["recommended"]["rows_per_snapshot"], 5_000)
        self.assertEqual(projection["scenarios"]["recommended"]["future_snapshots_needed"], 20)
        self.assertEqual(projection["scenarios"]["recommended"]["total_snapshots_including_current"], 21)
        self.assertEqual(projection["recommended_allocation"]["true_value"]["target_rows"], 2_500)
        self.assertEqual(projection["recommended_allocation"]["mahindra_first_choice"]["target_rows"], 1_500)
        self.assertEqual(projection["recommended_allocation"]["spinny"]["target_rows"], 1_000)

    def test_renders_and_writes_projection_outputs(self) -> None:
        projection = {
            "target_id": "target_100k",
            "generated_at": "2026-06-26T00:00:00Z",
            "target_observations": 100_000,
            "remaining_observations": 99_091,
            "current": {
                "snapshot_id": "snapshot_baseline",
                "trusted_observations": 909,
            },
            "scenarios": {
                "recommended": {
                    "name": "recommended",
                    "rows_per_snapshot": 5_000,
                    "future_snapshots_needed": 20,
                    "total_snapshots_including_current": 21,
                }
            },
            "recommended_allocation": {
                "true_value": {
                    "target_rows": 2_500,
                    "share_pct": 50,
                    "reason": "Structured source.",
                }
            },
            "readiness_gates": ["Repeat baseline once."],
        }

        report = render_scale_projection_markdown(projection)

        self.assertIn("# Snapshot Scale Projection", report)
        self.assertIn("Current snapshot: `snapshot_baseline`", report)
        self.assertIn("| recommended | 5,000 | 20 | 21 |", report)
        self.assertIn("| true_value | 2,500 | 50% | Structured source. |", report)

        with TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "projection.json"
            md_path = Path(tmpdir) / "projection.md"

            self.assertEqual(write_scale_projection_json(json_path, projection), json_path)
            self.assertEqual(write_scale_projection_markdown(md_path, projection), md_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())


def write_snapshot_manifest(path: Path, *, pricing_ready: int) -> None:
    path.write_text(
        json.dumps(
            {
                "snapshot_id": "snapshot_baseline",
                "snapshot_date": "2026-06-26",
                "totals": {
                    "pricing_ready": pricing_ready,
                    "unique_listing_keys": pricing_ready,
                    "source_runs": 15,
                    "by_source": {
                        "spinny": {"pricing_ready": 300},
                        "true_value": {"pricing_ready": 429},
                        "mahindra_first_choice": {"pricing_ready": 180},
                    },
                },
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
