"""Service layer for loading the final model artifact and producing predictions."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from used_car_price_intelligence.api.schemas import (
    HealthResponse,
    PredictionBatchResponse,
    PredictionRequest,
    PredictionResponse,
)
from used_car_price_intelligence.modeling import FinalPriceModelArtifact, load_artifact


ROOT = Path(__file__).resolve().parents[3]
MODEL_ARTIFACT_ENV = "USED_CAR_MODEL_ARTIFACT"
DEFAULT_ARTIFACT_PATH = (
    ROOT / "artifacts" / "model" / "final_price_model_v1" / "final_price_model_v1.joblib"
)


class ModelArtifactNotFound(RuntimeError):
    """Raised when the API cannot find the configured model artifact."""


@dataclass
class PredictionService:
    """Thin service around the persisted final model artifact."""

    artifact_path: Path = DEFAULT_ARTIFACT_PATH
    _artifact: FinalPriceModelArtifact | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_env(cls) -> "PredictionService":
        configured_path = os.environ.get(MODEL_ARTIFACT_ENV)
        return cls(Path(configured_path) if configured_path else DEFAULT_ARTIFACT_PATH)

    def health(self) -> HealthResponse:
        artifact_exists = self.artifact_path.exists()
        return HealthResponse(
            status="ok" if artifact_exists else "missing_artifact",
            artifact_path=str(self.artifact_path),
            artifact_exists=artifact_exists,
            artifact_loaded=self._artifact is not None,
        )

    def metadata(self) -> dict[str, object]:
        return self.artifact.metadata()

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        response = self.artifact.predict_one(request.to_artifact_payload())
        return PredictionResponse.model_validate(response)

    def predict_batch(self, request: list[PredictionRequest]) -> PredictionBatchResponse:
        payloads = [record.to_artifact_payload() for record in request]
        predictions = [
            PredictionResponse.model_validate(response)
            for response in self.artifact.predict_records(payloads)
        ]
        return PredictionBatchResponse(count=len(predictions), predictions=predictions)

    @property
    def artifact(self) -> FinalPriceModelArtifact:
        if self._artifact is None:
            if not self.artifact_path.exists():
                raise ModelArtifactNotFound(
                    f"Model artifact not found at {self.artifact_path}. "
                    "Run scripts/export_final_price_model.py or set USED_CAR_MODEL_ARTIFACT."
                )
            self._artifact = load_artifact(self.artifact_path)
        return self._artifact
