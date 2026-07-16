import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from used_car_price_intelligence.reporting import (
    build_remaining_gap_strategy,
    render_remaining_gap_strategy_markdown,
    write_remaining_gap_strategy_json,
    write_remaining_gap_strategy_markdown,
)


class RemainingGapStrategyTests(unittest.TestCase):
    def test_builds_source_aware_strategy_from_snapshot_and_allocation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "snapshot.json"
            config_path = root / "targets.yml"
            write_snapshot_manifest(manifest_path)
            write_target_config(config_path)

            strategy = build_remaining_gap_strategy(
                snapshot_manifest_path=manifest_path,
                target_config_path=config_path,
                generated_at="2026-06-27T00:00:00Z",
            )

        self.assertEqual(strategy["target"]["current_pricing_ready"], 3_278)
        self.assertEqual(strategy["target"]["target_pricing_ready"], 5_000)
        self.assertEqual(strategy["target"]["rows_under_target"], 1_722)
        self.assertEqual(strategy["target"]["allocation_gap_total"], 1_722)
        self.assertEqual(strategy["decision"]["name"], "balanced_gap_close_required")
        self.assertEqual(strategy["source_rows"]["true_value"]["allocation_gap"], 52)
        self.assertEqual(strategy["source_rows"]["true_value"]["status"], "near_allocation")
        self.assertEqual(strategy["source_rows"]["mahindra_first_choice"]["allocation_gap"], 990)
        self.assertEqual(strategy["source_rows"]["mahindra_first_choice"]["status"], "capacity_constrained")
        self.assertEqual(strategy["source_rows"]["spinny"]["allocation_gap"], 680)
        self.assertEqual(strategy["source_rows"]["spinny"]["status"], "incremental_expansion_needed")
        self.assertEqual(strategy["recommended_sequence"][0]["name"], "spinny_incremental_expansion_pack")
        self.assertEqual(strategy["recommended_sequence"][2]["target_rows"], 52)

    def test_renders_and_writes_strategy_outputs(self) -> None:
        strategy = {
            "strategy_id": "remaining_gap_strategy_from_snapshot",
            "generated_at": "2026-06-27T00:00:00Z",
            "snapshot": {"snapshot_id": "snapshot_current"},
            "target": {
                "current_pricing_ready": 3_278,
                "target_pricing_ready": 5_000,
                "rows_under_target": 1_722,
            },
            "source_rows": {
                "true_value": {
                    "current_rows": 2_448,
                    "target_rows": 2_500,
                    "allocation_gap": 52,
                    "current_share_pct": 48.96,
                    "target_share_pct": 50,
                    "status": "near_allocation",
                    "next_action": "Use only as a final capped buffer.",
                }
            },
            "decision": {
                "name": "balanced_gap_close_required",
                "reason": "Do not close the whole gap with one source.",
            },
            "recommended_sequence": [
                {
                    "name": "true_value_final_buffer",
                    "source": "true_value",
                    "target_rows": 52,
                    "rationale": "Use only the remaining allocation gap.",
                }
            ],
            "stop_conditions": ["Stop on quarantine."],
        }

        report = render_remaining_gap_strategy_markdown(strategy)

        self.assertIn("# Remaining 5k Gap Strategy", report)
        self.assertIn("Rows under target: 1,722", report)
        self.assertIn("| true_value | 2448 | 2500 | 52 | 48.96% | 50.00% | near_allocation |", report)
        self.assertIn("Decision: `balanced_gap_close_required`", report)

        with TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "strategy.json"
            md_path = Path(tmpdir) / "strategy.md"

            self.assertEqual(write_remaining_gap_strategy_json(json_path, strategy), json_path)
            self.assertEqual(write_remaining_gap_strategy_markdown(md_path, strategy), md_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())


def write_snapshot_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "snapshot_id": "snapshot_20260627_true_value_buffer",
                "snapshot_date": "2026-06-27",
                "totals": {
                    "pricing_ready": 3_278,
                    "target_pricing_ready": 5_000,
                    "rows_under_target": 1_722,
                    "by_source": {
                        "true_value": {"pricing_ready": 2_448},
                        "mahindra_first_choice": {"pricing_ready": 510},
                        "spinny": {"pricing_ready": 320},
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def write_target_config(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "recommended_5000_row_source_allocation": {
                    "true_value": {
                        "target_rows": 2_500,
                        "share_pct": 50,
                        "role": "volume_lane_near_allocation",
                    },
                    "mahindra_first_choice": {
                        "target_rows": 1_500,
                        "share_pct": 30,
                        "role": "multi_brand_expansion_lane",
                    },
                    "spinny": {
                        "target_rows": 1_000,
                        "share_pct": 20,
                        "role": "quality_anchor",
                    },
                }
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
