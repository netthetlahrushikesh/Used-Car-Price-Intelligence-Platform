"""Pydantic schemas for the prediction API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from used_car_price_intelligence.modeling.final_price_model import DEFAULT_MARKET_SNAPSHOT_YEAR


FuelType = Literal["petrol", "diesel", "cng", "petrol_cng", "petrol_lpg", "electric", "hybrid"]
TransmissionType = Literal["manual", "automatic", "amt"]
SourceContext = Literal["market_default", "true_value", "spinny", "mahindra_first_choice"]
Confidence = Literal["high", "medium", "low"]

FUEL_ALIASES = {
    "petrol": "petrol",
    "diesel": "diesel",
    "cng": "cng",
    "petrol_cng": "petrol_cng",
    "petrol+cng": "petrol_cng",
    "petrol cng": "petrol_cng",
    "petrol_lpg": "petrol_lpg",
    "petrol+lpg": "petrol_lpg",
    "petrol lpg": "petrol_lpg",
    "electric": "electric",
    "ev": "electric",
    "hybrid": "hybrid",
}
TRANSMISSION_ALIASES = {
    "manual": "manual",
    "mt": "manual",
    "automatic": "automatic",
    "auto": "automatic",
    "at": "automatic",
    "amt": "amt",
}
SOURCE_CONTEXT_ALIASES = {
    "market_default": "market_default",
    "market default": "market_default",
    "true_value": "true_value",
    "true value": "true_value",
    "spinny": "spinny",
    "mahindra_first_choice": "mahindra_first_choice",
    "mahindra first choice": "mahindra_first_choice",
    "mfc": "mahindra_first_choice",
}


class PredictionRequest(BaseModel):
    """User-facing request for one price estimate."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
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
        },
    )

    brand: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    model_year: int = Field(..., ge=2000, le=DEFAULT_MARKET_SNAPSHOT_YEAR)
    km_driven: int = Field(..., ge=0, le=300_000)
    fuel_type: FuelType
    transmission: TransmissionType
    city: str = Field(..., min_length=1)
    variant: str = Field(default="unknown")
    ownership: int | str = Field(default="unknown")
    registration_code: str = Field(default="unknown")
    state: str = Field(default="unknown")
    source_context: SourceContext = Field(default="market_default")
    market_snapshot_year: int = Field(default=DEFAULT_MARKET_SNAPSHOT_YEAR, ge=2020, le=2035)

    @field_validator("brand", "model", "city", "variant", "registration_code", "state")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        cleaned = value.strip()
        return cleaned if cleaned else "unknown"

    @field_validator("fuel_type", mode="before")
    @classmethod
    def normalize_fuel_type(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return FUEL_ALIASES.get(value.strip().lower().replace("-", "_"), value)

    @field_validator("transmission", mode="before")
    @classmethod
    def normalize_transmission(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return TRANSMISSION_ALIASES.get(value.strip().lower().replace("-", "_"), value)

    @field_validator("source_context", mode="before")
    @classmethod
    def normalize_source_context(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return SOURCE_CONTEXT_ALIASES.get(value.strip().lower().replace("-", "_"), value)

    @field_validator("ownership")
    @classmethod
    def validate_ownership(cls, value: int | str) -> int | str:
        if isinstance(value, int):
            if 1 <= value <= 5:
                return value
            raise ValueError("ownership must be between 1 and 5 when numeric")
        cleaned = value.strip()
        return cleaned if cleaned else "unknown"

    def to_artifact_payload(self) -> dict[str, Any]:
        """Return a plain dict accepted by the model artifact."""

        return self.model_dump()


class PredictionBatchRequest(BaseModel):
    """Batch prediction request for offline checks and future bulk APIs."""

    model_config = ConfigDict(extra="forbid")

    records: list[PredictionRequest] = Field(..., min_length=1, max_length=50)


class PredictionResponse(BaseModel):
    """API response returned by the final model artifact."""

    model_config = ConfigDict(extra="forbid")

    model_version: str
    model_name: str
    prediction_target: Literal["listed_price_inr"]
    predicted_price_inr: int = Field(..., ge=0)
    price_range_low_inr: int = Field(..., ge=0)
    price_range_high_inr: int = Field(..., ge=0)
    price_range_pct: float = Field(..., ge=0)
    confidence: Confidence
    price_band: str
    warning_codes: list[str]
    input_normalized: dict[str, Any]
    explanation: list[str]


class PredictionBatchResponse(BaseModel):
    """Response for batch predictions."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(..., ge=1)
    predictions: list[PredictionResponse]


class HealthResponse(BaseModel):
    """Operational health response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "missing_artifact"]
    artifact_path: str
    artifact_exists: bool
    artifact_loaded: bool


class ErrorResponse(BaseModel):
    """Error response shape used by API docs."""

    detail: str
