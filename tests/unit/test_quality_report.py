import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from used_car_price_intelligence.reporting import load_quality_summary, render_quality_report


class QualityReportTests(unittest.TestCase):
    def test_renders_passing_summary(self) -> None:
        report = render_quality_report(_passing_summary())

        self.assertIn("Status: PASS", report)
        self.assertIn("Source: spinny", report)
        self.assertIn("5 pricing-ready", report)
        self.assertIn("- required: 100.00%", report)
        self.assertIn("- none", report)

    def test_renders_warning_when_some_records_are_quarantined(self) -> None:
        summary = _passing_summary()
        summary["pricing_ready"] = 4
        summary["quarantined"] = 1
        summary["quarantine_reasons"] = {"missing_fuel": 1}

        report = render_quality_report(summary)

        self.assertIn("Status: WARN", report)
        self.assertIn("- missing_fuel: 1", report)

    def test_load_quality_summary_rejects_missing_keys(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "summary.json"
            path.write_text(json.dumps({"source": "spinny"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_quality_summary(path)


def _passing_summary() -> dict[str, object]:
    return {
        "source": "spinny",
        "records_total": 5,
        "silver_valid": 5,
        "pricing_ready": 5,
        "quarantined": 0,
        "required_completeness_avg": 1.0,
        "high_value_completeness_avg": 0.8571,
        "optional_completeness_avg": 0.2333,
        "overall_completeness_avg": 0.8948,
        "quarantine_reasons": {},
        "warnings": {},
    }


if __name__ == "__main__":
    unittest.main()
