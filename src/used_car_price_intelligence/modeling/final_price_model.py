"""Reusable final price model artifact for Stage 2 product/API work.

The notebook metrics remain the validation source of truth. This module trains
the deployable artifact on the full combined trusted modeling dataset so the
future API can load one object and make repeatable predictions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


TARGET = "listed_price_inr"
MODEL_VERSION = "final_price_model_v1"
MODEL_NAME = "Combined Trusted Lineage Target-Encoded Native HGB"
DATASET_ID = "combined_live_trusted_plus_external_true_value_20260628"
DEFAULT_MARKET_SNAPSHOT_YEAR = 2026
TARGET_ENCODING_SMOOTHING = 10
HIGH_CARDINALITY_TOP_N = 180
RARE_BRAND_MODEL_MIN_ROWS = 10

LUXURY_BRANDS = {
    "audi",
    "bmw",
    "byd",
    "jaguar",
    "jeep",
    "land rover",
    "lexus",
    "mercedes-benz",
    "mercedes benz",
    "mini",
    "porsche",
    "volvo",
}

SOURCE_DEFAULTS = {
    "market_default": "true_value",
    "true_value": "true_value",
    "spinny": "spinny",
    "mahindra_first_choice": "mahindra_first_choice",
}

NUMERIC_FEATURE_CANDIDATES = [
    "model_year",
    "vehicle_age_years",
    "km_driven",
    "market_snapshot_year",
    "is_luxury_brand",
    "km_per_year",
    "log_km_driven",
    "age_km_interaction",
    "is_low_km_for_age",
    "is_high_km_for_age",
    "brand_model_frequency",
    "model_frequency",
    "brand_frequency",
    "variant_frequency",
    "city_brand_frequency",
]

CATEGORICAL_FEATURE_CANDIDATES = [
    "source",
    "city",
    "state",
    "brand",
    "model",
    "variant",
    "brand_model",
    "fuel_type",
    "transmission",
    "ownership",
    "registration_code",
    "vehicle_age_bucket",
    "km_bucket",
    "source_city",
    "source_brand",
    "city_brand",
    "brand_fuel_type",
    "brand_transmission",
    "luxury_transmission",
    "dataset_origin",
    "data_freshness",
]

TARGET_ENCODING_COLUMNS = [
    "brand",
    "model",
    "variant",
    "brand_model",
    "source_city",
    "source_brand",
    "city_brand",
    "registration_code",
    "brand_fuel_type",
    "brand_transmission",
]

PUBLIC_REQUIRED_FIELDS = [
    "brand",
    "model",
    "model_year",
    "km_driven",
    "fuel_type",
    "transmission",
    "city",
]

PUBLIC_OPTIONAL_FIELDS = [
    "variant",
    "ownership",
    "registration_code",
    "state",
    "source_context",
    "market_snapshot_year",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalized_text(series: pd.Series) -> pd.Series:
    return series.fillna("unknown").astype(str).str.strip().str.lower()


def _available_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [col for col in columns if col in df.columns]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _clean_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return value


def _canonical_key(value: Any) -> str:
    cleaned = _clean_scalar(value)
    if cleaned is None:
        return "unknown"
    return str(cleaned).strip().lower()


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    number = _safe_float(value)
    if number is None:
        return default
    return int(round(number))


def _price_band(price: float) -> str:
    if price < 250_000:
        return "0_2.5L"
    if price < 500_000:
        return "2.5L_5L"
    if price < 750_000:
        return "5L_7.5L"
    if price < 1_000_000:
        return "7.5L_10L"
    if price < 2_000_000:
        return "10L_20L"
    return "20L_plus"


@dataclass
class FinalPriceModelArtifact:
    """Serializable model object used by the future prediction API."""

    model_version: str
    model_name: str
    dataset_id: str
    trained_at_utc: str
    training_rows: int
    model: HistGradientBoostingRegressor
    numeric_features: list[str]
    categorical_features: list[str]
    target_encoding_columns: list[str]
    target_encoding_mappings: dict[str, dict[str, float]]
    target_encoding_lower_mappings: dict[str, dict[str, float]]
    target_encoding_global_means: dict[str, float]
    categorical_levels: dict[str, list[str]]
    categorical_keep_values: dict[str, list[str]]
    frequency_maps: dict[str, dict[str, float]]
    canonical_value_maps: dict[str, dict[str, str]]
    training_category_counts: dict[str, dict[str, int]]
    config: dict[str, Any] = field(default_factory=dict)
    validation_metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_columns(self) -> list[str]:
        return self.numeric_features + self.categorical_features

    def metadata(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "model_name": self.model_name,
            "dataset_id": self.dataset_id,
            "trained_at_utc": self.trained_at_utc,
            "training_rows": self.training_rows,
            "target": TARGET,
            "target_transform": "log1p",
            "numeric_features": self.numeric_features,
            "categorical_features": self.categorical_features,
            "target_encoding_columns": self.target_encoding_columns,
            "feature_count": len(self.feature_columns),
            "config": self.config,
            "validation_metrics": self.validation_metrics,
            "api_required_fields": PUBLIC_REQUIRED_FIELDS,
            "api_optional_fields": PUBLIC_OPTIONAL_FIELDS,
        }

    def predict_one(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.predict_records([payload])[0]

    def predict_records(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not payloads:
            return []

        raw = pd.DataFrame([_normalize_api_payload(payload) for payload in payloads])
        warnings_by_row = [_input_warning_codes(payload) for payload in raw.to_dict("records")]
        features = self._prepare_prediction_features(raw)
        predicted_log_prices = self.model.predict(features)
        predicted_prices = np.clip(np.expm1(predicted_log_prices), 0, None)

        responses: list[dict[str, Any]] = []
        engineered = self._add_features(raw)
        for index, predicted_price in enumerate(predicted_prices):
            row = engineered.iloc[index]
            warning_codes = set(warnings_by_row[index])
            warning_codes.update(self._segment_warning_codes(row, float(predicted_price)))
            confidence, interval_pct = self._confidence_and_interval(row, warning_codes, float(predicted_price))
            low = max(0, float(predicted_price) * (1 - interval_pct))
            high = float(predicted_price) * (1 + interval_pct)
            responses.append(
                {
                    "model_version": self.model_version,
                    "model_name": self.model_name,
                    "prediction_target": "listed_price_inr",
                    "predicted_price_inr": int(round(float(predicted_price))),
                    "price_range_low_inr": int(round(low)),
                    "price_range_high_inr": int(round(high)),
                    "price_range_pct": round(interval_pct * 100, 2),
                    "confidence": confidence,
                    "price_band": _price_band(float(predicted_price)),
                    "warning_codes": sorted(warning_codes),
                    "input_normalized": {
                        key: _clean_scalar(value)
                        for key, value in raw.iloc[index].to_dict().items()
                        if key in PUBLIC_REQUIRED_FIELDS + PUBLIC_OPTIONAL_FIELDS
                    },
                    "explanation": [
                        "Prediction is a listed-price estimate, not a final transaction price.",
                        "Confidence is based on training coverage, segment risk, and known model limitations.",
                    ],
                }
            )
        return responses

    def _prepare_prediction_features(self, raw: pd.DataFrame) -> pd.DataFrame:
        engineered = self._add_features(raw)
        self._add_target_encoded_features(engineered)
        features = engineered[self.feature_columns].copy()

        for col in self.numeric_features:
            features[col] = pd.to_numeric(features[col], errors="coerce")

        for col in self.categorical_features:
            series = features[col].fillna("unknown").astype(str)
            keep = set(self.categorical_keep_values.get(col, []))
            if keep:
                series = series.where(series.isin(keep), "__other__")
            categories = self.categorical_levels[col]
            features[col] = pd.Categorical(series, categories=categories)

        return features

    def _add_features(self, raw: pd.DataFrame) -> pd.DataFrame:
        out = raw.copy()
        for col in ["brand", "model", "variant", "city", "state", "fuel_type", "transmission"]:
            if col not in out:
                out[col] = "unknown"

        out["source"] = out.get("source_context", "market_default").map(SOURCE_DEFAULTS).fillna("true_value")
        out["dataset_origin"] = "live_scraped_100k_deduped"
        out["data_freshness"] = "current_market"
        out["market_snapshot_year"] = pd.to_numeric(
            out.get("market_snapshot_year", DEFAULT_MARKET_SNAPSHOT_YEAR),
            errors="coerce",
        ).fillna(DEFAULT_MARKET_SNAPSHOT_YEAR)

        for col in ["brand", "model", "variant", "city", "state", "fuel_type", "transmission", "registration_code"]:
            if col in out:
                out[col] = self._canonicalize_series(col, out[col])

        if "ownership" not in out:
            out["ownership"] = "unknown"
        out["ownership"] = out["ownership"].fillna("unknown").astype(str)

        out["model_year"] = pd.to_numeric(out["model_year"], errors="coerce")
        out["km_driven"] = pd.to_numeric(out["km_driven"], errors="coerce")
        out["vehicle_age_years"] = out["market_snapshot_year"] - out["model_year"]
        out["brand_model"] = self._canonicalize_brand_model(out)

        brand_norm = _normalized_text(out["brand"])
        source_norm = _normalized_text(out["source"])
        city_norm = _normalized_text(out["city"])
        fuel_norm = _normalized_text(out["fuel_type"])
        transmission_norm = _normalized_text(out["transmission"])

        age = pd.to_numeric(out["vehicle_age_years"], errors="coerce")
        km = pd.to_numeric(out["km_driven"], errors="coerce")

        out["is_luxury_brand"] = brand_norm.isin(LUXURY_BRANDS).astype(int)
        out["vehicle_age_bucket"] = pd.cut(
            age,
            bins=[-1, 2, 5, 8, 12, 30],
            labels=["0_2_years", "3_5_years", "6_8_years", "9_12_years", "13_plus_years"],
        ).astype("object").fillna("unknown")
        out["km_bucket"] = pd.cut(
            km,
            bins=[-1, 20_000, 50_000, 80_000, 120_000, 300_000],
            labels=["0_20k", "20k_50k", "50k_80k", "80k_120k", "120k_plus"],
        ).astype("object").fillna("unknown")

        safe_age = age.clip(lower=1)
        out["km_per_year"] = km / safe_age
        out["log_km_driven"] = np.log1p(km.clip(lower=0))
        out["age_km_interaction"] = age * out["log_km_driven"]
        out["is_low_km_for_age"] = (out["km_per_year"] <= 8_000).fillna(False).astype(int)
        out["is_high_km_for_age"] = (out["km_per_year"] >= 20_000).fillna(False).astype(int)

        out["source_city"] = source_norm + "__" + city_norm
        out["source_brand"] = source_norm + "__" + brand_norm
        out["city_brand"] = city_norm + "__" + brand_norm
        out["brand_fuel_type"] = brand_norm + "__" + fuel_norm
        out["brand_transmission"] = brand_norm + "__" + transmission_norm
        out["luxury_transmission"] = (
            out["is_luxury_brand"].map({1: "luxury", 0: "non_luxury"}) + "__" + transmission_norm
        )

        for col in ["brand_model", "model", "brand", "variant", "city_brand"]:
            map_name = f"{col}_frequency"
            value_map = self.frequency_maps.get(map_name, {})
            out[map_name] = out[col].fillna("unknown").astype(str).map(value_map).fillna(0).astype(float)

        return out

    def _add_target_encoded_features(self, frame: pd.DataFrame) -> None:
        for col in self.target_encoding_columns:
            mapping = self.target_encoding_mappings[col]
            lower_mapping = self.target_encoding_lower_mappings[col]
            global_mean = self.target_encoding_global_means[col]
            values = frame[col].fillna("unknown").astype(str)
            encoded = values.map(mapping)
            lower_encoded = values.str.strip().str.lower().map(lower_mapping)
            frame[f"te_{col}"] = encoded.fillna(lower_encoded).fillna(global_mean).astype(float)

    def _canonicalize_series(self, column: str, series: pd.Series) -> pd.Series:
        canonical_map = self.canonical_value_maps.get(column, {})
        cleaned = series.fillna("unknown").astype(str).str.strip()
        lower = cleaned.str.lower()
        return lower.map(canonical_map).fillna(cleaned.where(cleaned.ne(""), "unknown"))

    def _canonicalize_brand_model(self, out: pd.DataFrame) -> pd.Series:
        if "brand_model" in out.columns:
            provided = out["brand_model"].fillna("").astype(str).str.strip()
        else:
            provided = pd.Series([""] * len(out), index=out.index)
        generated = (out["brand"].fillna("").astype(str).str.strip() + " " + out["model"].fillna("").astype(str).str.strip()).str.strip()
        result = provided.where(provided.ne(""), generated)
        return self._canonicalize_series("brand_model", result)

    def _segment_warning_codes(self, row: pd.Series, predicted_price: float) -> list[str]:
        warnings: list[str] = []
        brand_model = str(row.get("brand_model", "unknown"))
        brand = str(row.get("brand", "unknown"))
        model = str(row.get("model", "unknown"))
        city = str(row.get("city", "unknown"))

        if self.training_category_counts.get("brand_model", {}).get(brand_model, 0) < RARE_BRAND_MODEL_MIN_ROWS:
            warnings.append("rare_or_unseen_brand_model")
        if brand not in self.training_category_counts.get("brand", {}):
            warnings.append("unseen_brand")
        if model not in self.training_category_counts.get("model", {}):
            warnings.append("unseen_model")
        if city not in self.training_category_counts.get("city", {}):
            warnings.append("unseen_city")
        if int(row.get("is_luxury_brand", 0)) == 1 or predicted_price >= 1_000_000:
            warnings.append("premium_or_high_price_segment")

        km = _safe_float(row.get("km_driven"))
        year = _safe_int(row.get("model_year"))
        if km is not None and km > 300_000:
            warnings.append("km_outside_training_policy")
        if year is not None and (year < 2000 or year > DEFAULT_MARKET_SNAPSHOT_YEAR):
            warnings.append("model_year_outside_training_policy")
        return warnings

    def _confidence_and_interval(
        self,
        row: pd.Series,
        warning_codes: set[str],
        predicted_price: float,
    ) -> tuple[str, float]:
        brand_model = str(row.get("brand_model", "unknown"))
        brand_model_count = self.training_category_counts.get("brand_model", {}).get(brand_model, 0)

        if (
            "rare_or_unseen_brand_model" in warning_codes
            or "unseen_model" in warning_codes
            or "model_year_outside_training_policy" in warning_codes
            or "km_outside_training_policy" in warning_codes
        ):
            return "low", 0.28
        if "premium_or_high_price_segment" in warning_codes or brand_model_count < 30:
            return "medium", 0.18
        if predicted_price < 250_000:
            return "medium", 0.18
        return "high", 0.12


def _normalize_api_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: _clean_scalar(value) for key, value in payload.items()}
    normalized.setdefault("variant", "unknown")
    normalized.setdefault("state", "unknown")
    normalized.setdefault("registration_code", "unknown")
    normalized.setdefault("ownership", "unknown")
    normalized.setdefault("source_context", "market_default")
    normalized.setdefault("market_snapshot_year", DEFAULT_MARKET_SNAPSHOT_YEAR)
    return normalized


def _input_warning_codes(payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for field_name in PUBLIC_REQUIRED_FIELDS:
        if _clean_scalar(payload.get(field_name)) is None:
            warnings.append(f"missing_{field_name}")
    return warnings


def _add_training_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["market_snapshot_year"] = pd.to_numeric(
        out.get("market_snapshot_year", DEFAULT_MARKET_SNAPSHOT_YEAR),
        errors="coerce",
    ).fillna(DEFAULT_MARKET_SNAPSHOT_YEAR)
    out["model_year"] = pd.to_numeric(out["model_year"], errors="coerce")
    out["km_driven"] = pd.to_numeric(out["km_driven"], errors="coerce")
    if "vehicle_age_years" not in out:
        out["vehicle_age_years"] = out["market_snapshot_year"] - out["model_year"]

    if "brand_model" not in out:
        out["brand_model"] = (
            out["brand"].fillna("").astype(str).str.strip()
            + " "
            + out["model"].fillna("").astype(str).str.strip()
        ).str.strip()

    for column in ["source", "city", "state", "brand", "model", "variant", "fuel_type", "transmission"]:
        if column not in out:
            out[column] = "unknown"
    if "ownership" not in out:
        out["ownership"] = "unknown"
    if "registration_code" not in out:
        out["registration_code"] = "unknown"
    if "dataset_origin" not in out:
        out["dataset_origin"] = "live_scraped_100k_deduped"
    if "data_freshness" not in out:
        out["data_freshness"] = "current_market"

    brand_norm = _normalized_text(out["brand"])
    source_norm = _normalized_text(out["source"])
    city_norm = _normalized_text(out["city"])
    fuel_norm = _normalized_text(out["fuel_type"])
    transmission_norm = _normalized_text(out["transmission"])

    age = pd.to_numeric(out["vehicle_age_years"], errors="coerce")
    km = pd.to_numeric(out["km_driven"], errors="coerce")

    out["is_luxury_brand"] = brand_norm.isin(LUXURY_BRANDS).astype(int)
    out["vehicle_age_bucket"] = pd.cut(
        age,
        bins=[-1, 2, 5, 8, 12, 30],
        labels=["0_2_years", "3_5_years", "6_8_years", "9_12_years", "13_plus_years"],
    ).astype("object").fillna("unknown")
    out["km_bucket"] = pd.cut(
        km,
        bins=[-1, 20_000, 50_000, 80_000, 120_000, 300_000],
        labels=["0_20k", "20k_50k", "50k_80k", "80k_120k", "120k_plus"],
    ).astype("object").fillna("unknown")

    safe_age = age.clip(lower=1)
    out["km_per_year"] = km / safe_age
    out["log_km_driven"] = np.log1p(km.clip(lower=0))
    out["age_km_interaction"] = age * out["log_km_driven"]
    out["is_low_km_for_age"] = (out["km_per_year"] <= 8_000).fillna(False).astype(int)
    out["is_high_km_for_age"] = (out["km_per_year"] >= 20_000).fillna(False).astype(int)

    out["source_city"] = source_norm + "__" + city_norm
    out["source_brand"] = source_norm + "__" + brand_norm
    out["city_brand"] = city_norm + "__" + brand_norm
    out["brand_fuel_type"] = brand_norm + "__" + fuel_norm
    out["brand_transmission"] = brand_norm + "__" + transmission_norm
    out["luxury_transmission"] = (
        out["is_luxury_brand"].map({1: "luxury", 0: "non_luxury"}) + "__" + transmission_norm
    )
    return out


def _frequency_maps(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    maps: dict[str, dict[str, float]] = {}
    for col in ["brand_model", "model", "brand", "variant", "city_brand"]:
        map_name = f"{col}_frequency"
        maps[map_name] = (
            frame[col].fillna("unknown").astype(str).value_counts().astype(float).to_dict()
        )
    return maps


def _apply_frequency_maps(frame: pd.DataFrame, maps: dict[str, dict[str, float]]) -> pd.DataFrame:
    out = frame.copy()
    for col in ["brand_model", "model", "brand", "variant", "city_brand"]:
        map_name = f"{col}_frequency"
        out[map_name] = out[col].fillna("unknown").astype(str).map(maps[map_name]).fillna(0).astype(float)
    return out


def _fit_target_encoding(frame: pd.DataFrame, columns: list[str]) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], dict[str, float]]:
    mappings: dict[str, dict[str, float]] = {}
    lower_mappings: dict[str, dict[str, float]] = {}
    global_means: dict[str, float] = {}
    y_log = np.log1p(frame[TARGET])
    global_mean = float(y_log.mean())
    for col in columns:
        tmp = pd.DataFrame({"category": frame[col].fillna("unknown").astype(str), "target": y_log})
        stats = tmp.groupby("category")["target"].agg(["mean", "count"])
        encoded = (stats["count"] * stats["mean"] + TARGET_ENCODING_SMOOTHING * global_mean) / (
            stats["count"] + TARGET_ENCODING_SMOOTHING
        )
        mapping = {str(key): float(value) for key, value in encoded.to_dict().items()}
        mappings[col] = mapping
        lower_mappings[col] = {}
        for key, value in mapping.items():
            lower_mappings[col].setdefault(key.strip().lower(), value)
        global_means[col] = global_mean
    return mappings, lower_mappings, global_means


def _add_target_encoded_columns(
    frame: pd.DataFrame,
    mappings: dict[str, dict[str, float]],
    lower_mappings: dict[str, dict[str, float]],
    global_means: dict[str, float],
) -> pd.DataFrame:
    out = frame.copy()
    for col, mapping in mappings.items():
        values = out[col].fillna("unknown").astype(str)
        encoded = values.map(mapping)
        lower_encoded = values.str.strip().str.lower().map(lower_mappings[col])
        out[f"te_{col}"] = encoded.fillna(lower_encoded).fillna(global_means[col]).astype(float)
    return out


def _feature_columns_for_final_model(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    numeric = _available_columns(df, NUMERIC_FEATURE_CANDIDATES)
    categorical = _available_columns(df, CATEGORICAL_FEATURE_CANDIDATES)
    target_encoded = [f"te_{col}" for col in _available_columns(df, TARGET_ENCODING_COLUMNS)]
    numeric = _dedupe_preserve_order(numeric + target_encoded)
    categorical = _dedupe_preserve_order(categorical)
    return numeric, categorical, _dedupe_preserve_order(numeric + categorical)


def _prepare_training_matrix(
    frame: pd.DataFrame,
    numeric_features: list[str],
    categorical_features: list[str],
) -> tuple[pd.DataFrame, dict[str, list[str]], dict[str, list[str]]]:
    matrix = frame[numeric_features + categorical_features].copy()
    categorical_levels: dict[str, list[str]] = {}
    categorical_keep_values: dict[str, list[str]] = {}

    for col in numeric_features:
        matrix[col] = pd.to_numeric(matrix[col], errors="coerce")

    for col in categorical_features:
        series = matrix[col].fillna("unknown").astype(str)
        value_counts = series.value_counts()
        if len(value_counts) > 250:
            keep = set(value_counts.head(HIGH_CARDINALITY_TOP_N).index)
            series = series.where(series.isin(keep), "__other__")
        else:
            keep = set(value_counts.index)
        categories = sorted(set(series.unique()).union({"__other__"}))
        matrix[col] = pd.Categorical(series, categories=categories)
        categorical_levels[col] = categories
        categorical_keep_values[col] = sorted(keep)

    return matrix, categorical_levels, categorical_keep_values


def _fit_model(seed: int = 42) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.04,
        max_iter=650,
        max_leaf_nodes=45,
        min_samples_leaf=15,
        l2_regularization=0.01,
        early_stopping=True,
        validation_fraction=0.10,
        n_iter_no_change=35,
        categorical_features="from_dtype",
        random_state=seed,
    )


def _canonical_value_maps(frame: pd.DataFrame, columns: list[str]) -> dict[str, dict[str, str]]:
    maps: dict[str, dict[str, str]] = {}
    for col in columns:
        counts = frame[col].fillna("unknown").astype(str).value_counts()
        col_map: dict[str, str] = {}
        for value in counts.index:
            col_map.setdefault(value.strip().lower(), str(value))
        maps[col] = col_map
    return maps


def _training_category_counts(frame: pd.DataFrame, columns: list[str]) -> dict[str, dict[str, int]]:
    return {
        col: {str(key): int(value) for key, value in frame[col].fillna("unknown").astype(str).value_counts().to_dict().items()}
        for col in columns
    }


def train_final_price_model_artifact(df: pd.DataFrame) -> FinalPriceModelArtifact:
    """Train the full-data deployable model artifact."""

    model_df = df.dropna(subset=[TARGET]).copy()
    model_df = _add_training_features(model_df)
    freq_maps = _frequency_maps(model_df)
    model_df = _apply_frequency_maps(model_df, freq_maps)

    target_encoding_cols = _available_columns(model_df, TARGET_ENCODING_COLUMNS)
    mappings, lower_mappings, global_means = _fit_target_encoding(model_df, target_encoding_cols)
    model_df = _add_target_encoded_columns(model_df, mappings, lower_mappings, global_means)

    numeric_features, categorical_features, _ = _feature_columns_for_final_model(model_df)
    train_x, categorical_levels, categorical_keep_values = _prepare_training_matrix(
        model_df,
        numeric_features,
        categorical_features,
    )

    model = _fit_model(seed=42)
    model.fit(train_x, np.log1p(model_df[TARGET]))

    validation_metrics = {
        "primary_split_mae": 47389,
        "primary_split_mape": 9.88,
        "primary_split_r2": 0.897,
        "repeated_split_mean_mae": 47589,
        "repeated_split_mean_mape": 10.33,
        "repeated_split_mape_range": "9.88% to 10.73%",
        "status": "usable_with_warning",
        "metric_source": "notebooks/used_car_price_intelligence_complete_modeling_story.ipynb",
    }

    return FinalPriceModelArtifact(
        model_version=MODEL_VERSION,
        model_name=MODEL_NAME,
        dataset_id=DATASET_ID,
        trained_at_utc=_utc_now_iso(),
        training_rows=int(len(model_df)),
        model=model,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        target_encoding_columns=target_encoding_cols,
        target_encoding_mappings=mappings,
        target_encoding_lower_mappings=lower_mappings,
        target_encoding_global_means=global_means,
        categorical_levels=categorical_levels,
        categorical_keep_values=categorical_keep_values,
        frequency_maps=freq_maps,
        canonical_value_maps=_canonical_value_maps(
            model_df,
            ["brand", "model", "variant", "brand_model", "city", "state", "fuel_type", "transmission", "registration_code"],
        ),
        training_category_counts=_training_category_counts(
            model_df,
            ["brand", "model", "variant", "brand_model", "city", "fuel_type", "transmission"],
        ),
        config={
            "default_market_snapshot_year": DEFAULT_MARKET_SNAPSHOT_YEAR,
            "default_source_context": "market_default",
            "default_source_mapping": SOURCE_DEFAULTS["market_default"],
            "target_encoding_smoothing": TARGET_ENCODING_SMOOTHING,
            "high_cardinality_top_n": HIGH_CARDINALITY_TOP_N,
            "rare_brand_model_min_rows": RARE_BRAND_MODEL_MIN_ROWS,
            "model_fit_scope": "full_combined_dataset_after_validation",
        },
        validation_metrics=validation_metrics,
    )


def save_artifact(artifact: FinalPriceModelArtifact, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "final_price_model_v1.joblib"
    metadata_path = output_dir / "metadata.json"
    feature_schema_path = output_dir / "feature_schema.json"

    joblib.dump(artifact, artifact_path)
    metadata_path.write_text(json.dumps(artifact.metadata(), indent=2), encoding="utf-8")
    feature_schema_path.write_text(
        json.dumps(
            {
                "numeric_features": artifact.numeric_features,
                "categorical_features": artifact.categorical_features,
                "target_encoding_columns": artifact.target_encoding_columns,
                "categorical_levels": artifact.categorical_levels,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "artifact": artifact_path,
        "metadata": metadata_path,
        "feature_schema": feature_schema_path,
    }


def load_artifact(path: Path) -> FinalPriceModelArtifact:
    return joblib.load(path)


def train_artifact_from_csv(csv_path: Path) -> FinalPriceModelArtifact:
    return train_final_price_model_artifact(pd.read_csv(csv_path))
