import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from fastapi.testclient import TestClient

from used_car_price_intelligence.api.app import create_app
from used_car_price_intelligence.api.prediction_logging import (
    append_prediction_log,
    build_prediction_log_record,
    feature_summary,
    log_successful_prediction,
)
from used_car_price_intelligence.api.schemas import (
    HealthResponse,
    PredictionBatchResponse,
    PredictionRequest,
    PredictionResponse,
)


class PredictionLoggingHelperTests(unittest.TestCase):
    def test_feature_summary_keeps_safe_fields_only(self) -> None:
        summary = feature_summary(
            {
                "brand": "Maruti Suzuki",
                "km_driven": 45000,
                "api_key": "should-not-appear",
                "authorization": "Bearer secret",
            }
        )

        self.assertEqual(summary["brand"], "Maruti Suzuki")
        self.assertEqual(summary["km_driven"], 45000)
        self.assertNotIn("api_key", summary)
        self.assertNotIn("authorization", summary)

    def test_build_record_uses_utc_timestamp(self) -> None:
        record = build_prediction_log_record(
            features={"brand": "Honda", "model_year": 2020, "km_driven": 10000},
            predicted_price=500000,
            latency_ms=12.3456,
            timestamp=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(record["timestamp"], "2026-09-01T10:00:00.000000Z")
        self.assertEqual(record["predicted_price"], 500000)
        self.assertEqual(record["latency_ms"], 12.346)
        self.assertEqual(record["request_features"]["brand"], "Honda")

    def test_append_prediction_log_writes_jsonl(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "predictions.jsonl"
            ok = append_prediction_log(
                {
                    "timestamp": "2026-09-01T10:00:00.000000Z",
                    "request_features": {"brand": "Tata"},
                    "predicted_price": 1,
                    "latency_ms": 1.0,
                },
                log_path=path,
            )

            self.assertTrue(ok)
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["predicted_price"], 1)

    def test_append_prediction_log_is_best_effort_on_failure(self) -> None:
        with TemporaryDirectory() as tmpdir:
            # Opening a directory path for append should fail without raising.
            ok = append_prediction_log({"predicted_price": 1}, log_path=Path(tmpdir))
            self.assertFalse(ok)

    def test_log_successful_prediction_wrapper(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.jsonl"
            ok = log_successful_prediction(
                features={"brand": "Toyota", "km_driven": 10},
                predicted_price=100,
                latency_ms=2.5,
                log_path=path,
            )
            self.assertTrue(ok)
            payload = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["predicted_price"], 100)
            self.assertIn("timestamp", payload)


class PredictionLoggingApiHookTests(unittest.TestCase):
    def test_predict_appends_jsonl_on_success(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "predictions.jsonl"
            client = TestClient(create_app(_FakeService()))

            def _log(**kwargs):
                return log_successful_prediction(**kwargs, log_path=log_path)

            with mock.patch(
                "used_car_price_intelligence.api.app.log_successful_prediction",
                side_effect=_log,
            ):
                response = client.post("/predict", json=_sample_request())

            self.assertEqual(response.status_code, 200)
            self.assertTrue(log_path.exists())
            row = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(row["predicted_price"], 492808)
            self.assertEqual(row["request_features"]["brand"], "Maruti Suzuki")
            self.assertIn("latency_ms", row)


class _FakeService:
    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            artifact_path="tests/fake.joblib",
            artifact_exists=True,
            artifact_loaded=True,
        )

    def metadata(self) -> dict[str, object]:
        return {"model_version": "final_price_model_v1"}

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        return PredictionResponse(
            model_version="final_price_model_v1",
            model_name="fake",
            prediction_target="listed_price_inr",
            predicted_price_inr=492808,
            price_range_low_inr=400000,
            price_range_high_inr=550000,
            price_range_pct=12.0,
            confidence="high",
            price_band="2.5L_5L",
            warning_codes=[],
            input_normalized=request.model_dump(),
            explanation=["test"],
        )

    def predict_batch(self, request: list[PredictionRequest]) -> PredictionBatchResponse:
        return PredictionBatchResponse(
            count=len(request),
            predictions=[self.predict(item) for item in request],
        )


def _sample_request() -> dict[str, object]:
    return {
        "brand": "Maruti Suzuki",
        "model": "Swift",
        "variant": "VXI",
        "model_year": 2019,
        "km_driven": 45000,
        "fuel_type": "petrol",
        "transmission": "manual",
        "city": "Hyderabad",
        "state": "Telangana",
        "ownership": 1,
        "registration_code": "TS",
        "source_context": "market_default",
    }


if __name__ == "__main__":
    unittest.main()
