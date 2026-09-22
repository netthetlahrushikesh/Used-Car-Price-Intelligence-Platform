import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "drift_report.py"
FIXTURE = ROOT / "tests" / "fixtures" / "mlops" / "sample_predictions.jsonl"


class DriftReportScriptTests(unittest.TestCase):
    def test_script_writes_report_from_fixture(self) -> None:
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reference = tmp / "reference_feature_stats.json"
            report = tmp / "drift_report.md"
            # Point log at missing file so script falls back to fixture.
            missing_log = tmp / "empty" / "predictions.jsonl"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--reference",
                    str(reference),
                    "--log",
                    str(missing_log),
                    "--fixture",
                    str(FIXTURE),
                    "--report",
                    str(report),
                    "--min-rows",
                    "5",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertTrue(report.exists())
            text = report.read_text(encoding="utf-8")
            self.assertIn("# Feature Drift Report", text)
            self.assertIn("model_year", text)
            self.assertIn("km_driven", text)
            self.assertTrue(reference.exists())
            stats = json.loads(reference.read_text(encoding="utf-8"))
            self.assertIn("features", stats)
            self.assertIn("model_year", stats["features"])

    def test_insufficient_data_is_honest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            tiny = tmp / "tiny.jsonl"
            tiny.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-09-01T00:00:00.000000Z",
                        "request_features": {"model_year": 2019, "km_driven": 1, "ownership": 1},
                        "predicted_price": 1,
                        "latency_ms": 1.0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            reference = tmp / "reference_feature_stats.json"
            reference.write_text(
                json.dumps(
                    {
                        "source": "unit-test",
                        "n_rows": 1,
                        "features": {
                            "model_year": {"count": 1, "mean": 2019.0, "std": 0.0, "values": [2019.0]},
                            "km_driven": {"count": 1, "mean": 1.0, "std": 0.0, "values": [1.0]},
                            "ownership": {"count": 1, "mean": 1.0, "std": 0.0, "values": [1.0]},
                            "market_snapshot_year": {
                                "count": 1,
                                "mean": 2026.0,
                                "std": 0.0,
                                "values": [2026.0],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = tmp / "drift_report.md"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--reference",
                    str(reference),
                    "--log",
                    str(tiny),
                    "--fixture",
                    str(FIXTURE),
                    "--report",
                    str(report),
                    "--min-rows",
                    "5",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            text = report.read_text(encoding="utf-8")
            self.assertIn("Insufficient data", text)
            self.assertIn("No drift claim is made", text)


if __name__ == "__main__":
    unittest.main()
