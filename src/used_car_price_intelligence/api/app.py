"""FastAPI app for the used-car price prediction service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from used_car_price_intelligence import __version__
from used_car_price_intelligence.api.schemas import (
    ErrorResponse,
    HealthResponse,
    PredictionBatchRequest,
    PredictionBatchResponse,
    PredictionRequest,
    PredictionResponse,
)
from used_car_price_intelligence.api.service import ModelArtifactNotFound, PredictionService


STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


def create_app(service: PredictionService | None = None) -> FastAPI:
    """Create the API app, allowing tests to inject a fake service."""

    prediction_service = service or PredictionService.from_env()
    app = FastAPI(
        title="Used Car Price Intelligence API",
        version=__version__,
        description=(
            "Prediction API for trusted-source used-car listed-price estimates. "
            "Responses include a price range, confidence level, and warning codes."
        ),
    )
    app.state.prediction_service = prediction_service
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=FileResponse, tags=["web"])
    def web_app() -> FileResponse:
        return FileResponse(INDEX_HTML)

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        return prediction_service.health()

    @app.get(
        "/model/metadata",
        response_model=dict[str, Any],
        responses={503: {"model": ErrorResponse}},
        tags=["model"],
    )
    def model_metadata() -> dict[str, Any]:
        try:
            return prediction_service.metadata()
        except ModelArtifactNotFound as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    @app.post(
        "/predict",
        response_model=PredictionResponse,
        responses={503: {"model": ErrorResponse}},
        tags=["prediction"],
    )
    def predict(request: PredictionRequest) -> PredictionResponse:
        try:
            return prediction_service.predict(request)
        except ModelArtifactNotFound as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    @app.post(
        "/predict/batch",
        response_model=PredictionBatchResponse,
        responses={503: {"model": ErrorResponse}},
        tags=["prediction"],
    )
    def predict_batch(request: PredictionBatchRequest) -> PredictionBatchResponse:
        try:
            return prediction_service.predict_batch(request.records)
        except ModelArtifactNotFound as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return app


app = create_app()
