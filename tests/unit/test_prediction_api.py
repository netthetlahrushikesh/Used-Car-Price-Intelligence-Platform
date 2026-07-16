import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from used_car_price_intelligence.api.app import create_app
from used_car_price_intelligence.api.schemas import (
    HealthResponse,
    PredictionBatchResponse,
    PredictionRequest,
    PredictionResponse,
)
from used_car_price_intelligence.api.service import PredictionService


class PredictionApiTests(unittest.TestCase):
    def test_web_entrypoint_and_static_assets(self) -> None:
        client = TestClient(create_app(FakePredictionService()))

        root_response = client.get("/")
        css_response = client.get("/static/styles.css")
        js_response = client.get("/static/app.js")

        self.assertEqual(root_response.status_code, 200)
        self.assertIn("Used Car Price Intelligence", root_response.text)
        self.assertEqual(css_response.status_code, 200)
        self.assertIn(".workspace", css_response.text)
        self.assertEqual(js_response.status_code, 200)
        self.assertIn("/predict", js_response.text)

    def test_health_and_metadata(self) -> None:
        client = TestClient(create_app(FakePredictionService()))

        health = client.get("/health")
        metadata = client.get("/model/metadata")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(metadata.status_code, 200)
        self.assertEqual(metadata.json()["model_version"], "final_price_model_v1")

    def test_predict_returns_model_response(self) -> None:
        client = TestClient(create_app(FakePredictionService()))

        response = client.post("/predict", json=sample_request())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["prediction_target"], "listed_price_inr")
        self.assertEqual(body["predicted_price_inr"], 492808)
        self.assertEqual(body["confidence"], "high")
        self.assertEqual(body["warning_codes"], [])

    def test_predict_batch_returns_multiple_responses(self) -> None:
        client = TestClient(create_app(FakePredictionService()))

        response = client.post(
            "/predict/batch",
            json={"records": [sample_request(), {**sample_request(), "model": "X1", "brand": "BMW"}]},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(len(body["predictions"]), 2)

    def test_invalid_request_is_rejected_before_model_call(self) -> None:
        service = FakePredictionService()
        client = TestClient(create_app(service))
        payload = {**sample_request(), "model_year": 1998, "unexpected": "field"}

        response = client.post("/predict", json=payload)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(service.predict_calls, 0)

    def test_common_user_input_labels_are_normalized(self) -> None:
        request = PredictionRequest.model_validate(
            {
                **sample_request(),
                "fuel_type": "Petrol CNG",
                "transmission": "Auto",
                "source_context": "MFC",
            }
        )

        self.assertEqual(request.fuel_type, "petrol_cng")
        self.assertEqual(request.transmission, "automatic")
        self.assertEqual(request.source_context, "mahindra_first_choice")

    def test_health_reports_missing_artifact_without_loading(self) -> None:
        with TemporaryDirectory() as tmpdir:
            service = PredictionService(Path(tmpdir) / "missing.joblib")

            response = service.health()

        self.assertEqual(response.status, "missing_artifact")
        self.assertFalse(response.artifact_exists)
        self.assertFalse(response.artifact_loaded)


class FakePredictionService:
    def __init__(self) -> None:
        self.predict_calls = 0

    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            artifact_path="tests/fake/final_price_model_v1.joblib",
            artifact_exists=True,
            artifact_loaded=True,
        )

    def metadata(self) -> dict[str, object]:
        return {
            "model_version": "final_price_model_v1",
            "model_name": "Combined Trusted Lineage Target-Encoded Native HGB",
            "training_rows": 9110,
        }

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        self.predict_calls += 1
        return _fake_response(request)

    def predict_batch(self, request: list[PredictionRequest]) -> PredictionBatchResponse:
        predictions = [_fake_response(record) for record in request]
        return PredictionBatchResponse(count=len(predictions), predictions=predictions)


def sample_request() -> dict[str, object]:
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


def _fake_response(request: PredictionRequest) -> PredictionResponse:
    warning_codes = ["premium_or_high_price_segment"] if request.brand == "BMW" else []
    return PredictionResponse(
        model_version="final_price_model_v1",
        model_name="Combined Trusted Lineage Target-Encoded Native HGB",
        prediction_target="listed_price_inr",
        predicted_price_inr=3250788 if request.brand == "BMW" else 492808,
        price_range_low_inr=2665646 if request.brand == "BMW" else 433671,
        price_range_high_inr=3835930 if request.brand == "BMW" else 551945,
        price_range_pct=18.0 if request.brand == "BMW" else 12.0,
        confidence="medium" if request.brand == "BMW" else "high",
        price_band="20L_plus" if request.brand == "BMW" else "2.5L_5L",
        warning_codes=warning_codes,
        input_normalized=request.model_dump(),
        explanation=[
            "Prediction is a listed-price estimate, not a final transaction price.",
            "Confidence is based on training coverage, segment risk, and known model limitations.",
        ],
    )


if __name__ == "__main__":
    unittest.main()
