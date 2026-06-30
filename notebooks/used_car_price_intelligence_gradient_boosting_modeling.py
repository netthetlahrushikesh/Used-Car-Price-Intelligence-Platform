"""Gradient boosting modeling notebook for the Used Car Price Intelligence Platform."""

# %% [markdown]
# # Used Car Price Intelligence Platform: Premium-Weighted Log-Gradient Boosting Modeling
#
# This notebook executes the third controlled modeling experiment after the
# raw-price and log-price Random Forest baselines.
#
# We train the same three-dataset structure using a `log1p(listed_price_inr)`
# target, a gradient boosting regressor, and premium-aware engineered features.
# Predictions are converted back to INR for evaluation.
#
# 1. **Live Trusted Market Premium-Weighted Log-Gradient Boosting**
# 2. **External True Value Historical Premium-Weighted Log-Gradient Boosting**
# 3. **Combined Trusted Lineage Premium-Weighted Log-Gradient Boosting**
#
# The goal is to improve non-linear tabular pricing behavior while preserving
# the same validation and segment reporting discipline.

# %% [markdown]
# ## 0. Notebook Contract
#
# This notebook:
#
# - loads the same three datasets used in final EDA
# - excludes leakage/id/capture columns
# - uses one shared sklearn preprocessing and model pipeline
# - adds premium-aware, source-aware, and age/km engineered features
# - trains three comparable log-target gradient boosting regressors
# - saves overall metrics, segment metrics, prediction samples, and model artifacts
# - compares gradient boosting against raw-price and log-price Random Forest baselines
#
# It intentionally uses one fixed, conservative boosting configuration so the
# modeling decision is easy to compare against earlier baselines.

# %%
from pathlib import Path
import json
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.preprocessing import OrdinalEncoder

try:
    from IPython.display import display
except ImportError:
    def display(value):
        print(value)

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
pd.set_option("display.max_columns", 120)
pd.set_option("display.float_format", lambda value: f"{value:,.2f}")

RANDOM_STATE = 42
TEST_SIZE = 0.20
TARGET = "listed_price_inr"
LOG_TARGET = "log_listed_price_inr"
RARE_BRAND_MODEL_MIN_ROWS = 10

DATASET_LABELS = {
    "live": "Live Trusted Market Snapshot",
    "external_true_value": "External True Value Historical Dataset",
    "combined": "Combined Trusted Modeling Dataset",
}

EXPERIMENT_LABELS = {
    "live_trusted_market_log_gradient_boosting": (
        "Live Trusted Market Premium-Weighted Log-Gradient Boosting"
    ),
    "external_true_value_historical_log_gradient_boosting": (
        "External True Value Historical Premium-Weighted Log-Gradient Boosting"
    ),
    "combined_trusted_lineage_log_gradient_boosting": (
        "Combined Trusted Lineage Premium-Weighted Log-Gradient Boosting"
    ),
}

SOURCE_LABELS = {
    "true_value": "True Value Live",
    "spinny": "Spinny Live",
    "mahindra_first_choice": "Mahindra First Choice Live",
    "true_value_external_kaggle": "External True Value Historical",
}

DATASET_ORIGIN_LABELS = {
    "live_scraped_100k_deduped": "Live Trusted Market Snapshot",
    "external_true_value_kaggle": "External True Value Historical Dataset",
    "Live scraped trusted deduped": "Live Trusted Market Snapshot",
    "External True Value Kaggle": "External True Value Historical Dataset",
}

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

KAGGLE_DATASET_ROOTS = [
    Path("/kaggle/input/datasets/hrushikeshnettetla/used-car-price-trusted-modeling-datasets"),
    Path("/kaggle/input/used-car-price-trusted-modeling-datasets"),
    Path("/kaggle/input/used-car-price-intelligence-trusted-modeling-datasets"),
]

# %% [markdown]
# ## 1. Load Datasets
#
# The loader supports Kaggle and local repository execution.

# %%
def first_existing_path(candidates):
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("None of these candidate paths exist:\n" + "\n".join(map(str, candidates)))


def find_uploaded_csv(file_name):
    for dataset_root in KAGGLE_DATASET_ROOTS:
        candidate = dataset_root / file_name
        if candidate.exists():
            return candidate

    kaggle_input = Path("/kaggle/input")
    if kaggle_input.exists():
        matches = sorted(kaggle_input.rglob(file_name))
        if matches:
            return matches[0]
    return None


def find_first_uploaded_csv(file_names):
    for file_name in file_names:
        match = find_uploaded_csv(file_name)
        if match is not None:
            return match
    return None


def resolve_dataset_paths():
    kaggle_files = {
        "live": find_first_uploaded_csv(
            ["live_trusted_market_snapshot_3496.csv"]
        ),
        "external_true_value": find_first_uploaded_csv(
            [
                "external_true_value_historical_dataset_5614.csv",
            ]
        ),
        "combined": find_first_uploaded_csv(
            ["combined_trusted_modeling_dataset_9110.csv"]
        ),
    }
    if all(kaggle_files.values()):
        return kaggle_files, "kaggle_input"

    repo_root_candidates = [Path.cwd(), Path.cwd().parent]
    upload_roots = [
        root / "kaggle_upload" / package_name
        for root in repo_root_candidates
        for package_name in ["used-car-price-intelligence-trusted-modeling-datasets"]
    ]

    live_candidates = [
        *(root / "live_trusted_market_snapshot_3496.csv" for root in upload_roots),
        *(
            root
            / "data"
            / "gold"
            / "modeling"
            / "snapshot_20260627_100k_observation_run_modeling_v0"
            / "listings_modeling_dataset.csv"
            for root in repo_root_candidates
        ),
    ]
    external_candidates = [
        *(root / "external_true_value_historical_dataset_5614.csv" for root in upload_roots),
        *(
            root
            / "data"
            / "gold"
            / "external"
            / "true_value_kaggle_focusedmonk"
            / "listings_modeling_dataset.csv"
            for root in repo_root_candidates
        ),
    ]
    combined_candidates = [
        *(root / "combined_trusted_modeling_dataset_9110.csv" for root in upload_roots),
        *(
            root
            / "data"
            / "gold"
            / "modeling_experiments"
            / "three_model_phase_20260628"
            / "combined_modeling_dataset.csv"
            for root in repo_root_candidates
        ),
    ]

    return {
        "live": first_existing_path(live_candidates),
        "external_true_value": first_existing_path(external_candidates),
        "combined": first_existing_path(combined_candidates),
    }, "local_project"


DATASETS, RUN_CONTEXT = resolve_dataset_paths()

if Path("/kaggle/working").exists():
    OUTPUT_ROOT = Path("/kaggle/working/used_car_price_intelligence_gradient_boosting_modeling")
else:
    OUTPUT_ROOT = Path("notebooks") / "outputs" / "used_car_price_intelligence_gradient_boosting_modeling"

MODEL_DIR = OUTPUT_ROOT / "models"
FIGURE_DIR = OUTPUT_ROOT / "figures"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

print("Run context:", RUN_CONTEXT)
print("Output root:", OUTPUT_ROOT)
for name, path in DATASETS.items():
    print(f"{DATASET_LABELS[name]}: {path} | exists={path.exists()}")

# %%
def normalized_text(series):
    return series.fillna("unknown").astype(str).str.strip().str.lower()


def add_engineered_features(df):
    out = df.copy()

    brand_norm = normalized_text(out["brand"]) if "brand" in out.columns else pd.Series("", index=out.index)
    source_norm = normalized_text(out["source"]) if "source" in out.columns else pd.Series("", index=out.index)
    city_norm = normalized_text(out["city"]) if "city" in out.columns else pd.Series("", index=out.index)
    fuel_norm = normalized_text(out["fuel_type"]) if "fuel_type" in out.columns else pd.Series("", index=out.index)
    transmission_norm = (
        normalized_text(out["transmission"]) if "transmission" in out.columns else pd.Series("", index=out.index)
    )

    if "vehicle_age_years" in out.columns:
        age = pd.to_numeric(out["vehicle_age_years"], errors="coerce")
    elif "model_year" in out.columns:
        age = 2026 - pd.to_numeric(out["model_year"], errors="coerce")
    else:
        age = pd.Series(np.nan, index=out.index)

    km = (
        pd.to_numeric(out["km_driven"], errors="coerce")
        if "km_driven" in out.columns
        else pd.Series(np.nan, index=out.index)
    )

    out["is_luxury_brand"] = brand_norm.isin(LUXURY_BRANDS).astype(int)
    out["vehicle_age_bucket"] = pd.cut(
        age,
        bins=[-1, 2, 5, 8, 12, 30],
        labels=["0_2_years", "3_5_years", "6_8_years", "9_12_years", "13_plus_years"],
    ).astype("object")
    out["vehicle_age_bucket"] = out["vehicle_age_bucket"].fillna("unknown")

    out["km_bucket"] = pd.cut(
        km,
        bins=[-1, 20_000, 50_000, 80_000, 120_000, 300_000],
        labels=["0_20k", "20k_50k", "50k_80k", "80k_120k", "120k_plus"],
    ).astype("object")
    out["km_bucket"] = out["km_bucket"].fillna("unknown")

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
    out["luxury_transmission"] = out["is_luxury_brand"].map({1: "luxury", 0: "non_luxury"}) + "__" + transmission_norm

    return out


live = add_engineered_features(pd.read_csv(DATASETS["live"]))
external = add_engineered_features(pd.read_csv(DATASETS["external_true_value"]))
combined = add_engineered_features(pd.read_csv(DATASETS["combined"]))

datasets = {
    "live": live,
    "external_true_value": external,
    "combined": combined,
}

for name, df in datasets.items():
    print(f"{DATASET_LABELS[name]}: {df.shape[0]:,} rows x {df.shape[1]:,} columns")

# %% [markdown]
# ## 2. Feature Rules From EDA

# %%
LEAKAGE_OR_ID_COLS = [
    "listing_key",
    "source_listing_id",
    "listing_url",
    "capture_date",
    "captured_at",
    "vehicle_fingerprint",
    "registration_code",
    "is_available",
    "original_listing_key",
    "original_baseline_split",
]

CORE_FEATURE_CANDIDATES = [
    "source",
    "city",
    "state",
    "brand",
    "model",
    "variant",
    "brand_model",
    "model_year",
    "vehicle_age_years",
    "fuel_type",
    "transmission",
    "ownership",
    "km_driven",
]

ENGINEERED_FEATURE_CANDIDATES = [
    "is_luxury_brand",
    "vehicle_age_bucket",
    "km_bucket",
    "km_per_year",
    "log_km_driven",
    "age_km_interaction",
    "is_low_km_for_age",
    "is_high_km_for_age",
    "source_city",
    "source_brand",
    "city_brand",
    "brand_fuel_type",
    "brand_transmission",
    "luxury_transmission",
]

COMBINED_ONLY_FEATURES = [
    "dataset_origin",
    "data_freshness",
    "market_snapshot_year",
]

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
]


def available_columns(df, columns):
    return [col for col in columns if col in df.columns]


def feature_columns_for_experiment(df, include_lineage=False):
    features = available_columns(df, CORE_FEATURE_CANDIDATES)
    features += available_columns(df, ENGINEERED_FEATURE_CANDIDATES)
    if include_lineage:
        features += available_columns(df, COMBINED_ONLY_FEATURES)
    return features


live_external_features = feature_columns_for_experiment(combined, include_lineage=False)
combined_features = feature_columns_for_experiment(combined, include_lineage=True)

feature_plan = {
    "target": TARGET,
    "target_transform": "log1p",
    "model_family": "hist_gradient_boosting",
    "categorical_encoding": "ordinal_unknown_minus_one",
    "sample_weighting": "premium_rare_high_price_rows_weighted_during_training",
    "excluded_columns": available_columns(combined, LEAKAGE_OR_ID_COLS),
    "engineered_features": available_columns(combined, ENGINEERED_FEATURE_CANDIDATES),
    "live_external_features": live_external_features,
    "combined_features": combined_features,
}

feature_plan

# %% [markdown]
# ## 3. Rare Category Labels
#
# Rare categories are kept. We add an evaluation label so that model quality can
# be measured separately for common and rare `brand_model` groups.

# %%
combined_brand_model_counts = combined["brand_model"].fillna("unknown").astype(str).value_counts()
rare_brand_models = set(
    combined_brand_model_counts[combined_brand_model_counts < RARE_BRAND_MODEL_MIN_ROWS].index
)


def add_eval_labels(df):
    out = df.copy()
    if "source" in out.columns:
        out["source_label"] = out["source"].map(SOURCE_LABELS).fillna(out["source"])

    if "dataset_origin" in out.columns:
        out["dataset_origin_display"] = (
            out["dataset_origin"].map(DATASET_ORIGIN_LABELS).fillna(out["dataset_origin"])
        )
    elif "dataset_origin_label" in out.columns:
        out["dataset_origin_display"] = (
            out["dataset_origin_label"].map(DATASET_ORIGIN_LABELS).fillna(out["dataset_origin_label"])
        )
    else:
        out["dataset_origin_display"] = np.nan

    out["brand_model_eval_group"] = np.where(
        out["brand_model"].fillna("unknown").astype(str).isin(rare_brand_models),
        "rare_brand_model",
        "common_brand_model",
    )
    out["price_tail_group"] = np.select(
        [
            out[TARGET] < 50_000,
            out[TARGET] > 3_000_000,
        ],
        [
            "low_price_tail",
            "high_price_tail",
        ],
        default="normal_price_range",
    )
    return out


live_labeled = add_eval_labels(live)
external_labeled = add_eval_labels(external)
combined_labeled = add_eval_labels(combined)

print("Rare brand-model groups:", len(rare_brand_models))
combined_labeled["brand_model_eval_group"].value_counts(normalize=True).mul(100).round(2)

# %% [markdown]
# ## 4. Preprocessing And Model Pipeline

# %%
def make_ordinal_encoder():
    return OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
    )


def as_string_array(values):
    return values.astype(str)


def build_pipeline(feature_cols):
    numeric_features = [col for col in feature_cols if col in NUMERIC_FEATURE_CANDIDATES]
    categorical_features = [col for col in feature_cols if col not in numeric_features]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("to_string", FunctionTransformer(as_string_array, validate=False)),
            ("ordinal", make_ordinal_encoder()),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )

    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.06,
        max_iter=250,
        max_leaf_nodes=31,
        min_samples_leaf=20,
        l2_regularization=0.05,
        early_stopping=True,
        validation_fraction=0.10,
        n_iter_no_change=20,
        random_state=RANDOM_STATE,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline, numeric_features, categorical_features

# %% [markdown]
# ## 5. Split And Metric Helpers

# %%
def prepare_model_frame(df, feature_cols):
    model_df = df.dropna(subset=[TARGET]).copy()
    numeric_features = [col for col in feature_cols if col in NUMERIC_FEATURE_CANDIDATES]
    categorical_features = [col for col in feature_cols if col not in numeric_features]

    for col in numeric_features:
        model_df[col] = pd.to_numeric(model_df[col], errors="coerce")

    for col in categorical_features:
        model_df[col] = model_df[col].astype("object")

    return model_df


def make_price_stratification(y, max_bins=10):
    labels = pd.qcut(y, q=max_bins, duplicates="drop")
    counts = labels.value_counts()
    if len(counts) < 2 or counts.min() < 2:
        return None
    return labels


def split_train_test(df, feature_cols):
    model_df = prepare_model_frame(df, feature_cols)
    X = model_df[feature_cols]
    y = model_df[TARGET]
    stratify_labels = make_price_stratification(y)

    try:
        return train_test_split(
            X,
            y,
            model_df,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=stratify_labels,
        )
    except ValueError:
        return train_test_split(
            X,
            y,
            model_df,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=None,
        )


def regression_metrics(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    signed_error = y_pred - y_true
    abs_error = np.abs(y_true - y_pred)
    pct_error = abs_error / np.maximum(np.abs(y_true), 1) * 100
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": pct_error.mean(),
        "median_absolute_error": float(np.median(abs_error)),
        "mean_signed_error": float(np.mean(signed_error)),
        "median_signed_error": float(np.median(signed_error)),
        "underprediction_rate": float((signed_error < 0).mean() * 100),
        "r2": r2_score(y_true, y_pred),
    }


def log_target_metrics(y_true, log_pred):
    y_true_log = np.log1p(np.asarray(y_true))
    abs_log_error = np.abs(y_true_log - np.asarray(log_pred))
    return {
        "log_mae": float(abs_log_error.mean()),
        "log_median_absolute_error": float(np.median(abs_log_error)),
    }


def segment_metrics(predictions, segment_col, min_rows=20):
    rows = []
    if segment_col not in predictions.columns:
        return pd.DataFrame()

    for segment_value, group in predictions.groupby(segment_col, dropna=False):
        if len(group) < min_rows:
            continue
        metrics = regression_metrics(group["actual_price"], group["predicted_price"])
        rows.append(
            {
                "segment_column": segment_col,
                "segment_value": segment_value,
                "rows": len(group),
                **metrics,
            }
        )
    return pd.DataFrame(rows).sort_values("mae", ascending=False)

# %% [markdown]
# ## 6. Train Log-Gradient Boosting Experiments

# %%
EXPERIMENTS = [
    {
        "experiment": "live_trusted_market_log_gradient_boosting",
        "experiment_name": EXPERIMENT_LABELS["live_trusted_market_log_gradient_boosting"],
        "dataset_name": "live",
        "dataset_label": DATASET_LABELS["live"],
        "df": live_labeled,
        "feature_cols": feature_columns_for_experiment(live_labeled, include_lineage=False),
        "include_lineage": False,
    },
    {
        "experiment": "external_true_value_historical_log_gradient_boosting",
        "experiment_name": EXPERIMENT_LABELS[
            "external_true_value_historical_log_gradient_boosting"
        ],
        "dataset_name": "external_true_value",
        "dataset_label": DATASET_LABELS["external_true_value"],
        "df": external_labeled,
        "feature_cols": feature_columns_for_experiment(external_labeled, include_lineage=False),
        "include_lineage": False,
    },
    {
        "experiment": "combined_trusted_lineage_log_gradient_boosting",
        "experiment_name": EXPERIMENT_LABELS["combined_trusted_lineage_log_gradient_boosting"],
        "dataset_name": "combined",
        "dataset_label": DATASET_LABELS["combined"],
        "df": combined_labeled,
        "feature_cols": feature_columns_for_experiment(combined_labeled, include_lineage=True),
        "include_lineage": True,
    },
]

[(exp["experiment_name"], exp["dataset_label"], len(exp["df"]), exp["feature_cols"]) for exp in EXPERIMENTS]

# %%
def make_training_sample_weights(train_rows, y_train):
    weights = pd.Series(1.0, index=train_rows.index, dtype="float64")

    if "brand" in train_rows.columns:
        brand_norm = normalized_text(train_rows["brand"])
        weights += brand_norm.isin(LUXURY_BRANDS).astype(float) * 0.45

    if "brand_model_eval_group" in train_rows.columns:
        rare_mask = train_rows["brand_model_eval_group"].eq("rare_brand_model")
        weights += rare_mask.astype(float) * 0.35

    if "source" in train_rows.columns:
        source_norm = normalized_text(train_rows["source"])
        live_premium_source_mask = source_norm.isin(["spinny", "mahindra_first_choice"])
        weights += live_premium_source_mask.astype(float) * 0.20

    y_train = pd.Series(y_train, index=train_rows.index)
    weights += (y_train >= 1_000_000).astype(float) * 0.30
    weights += (y_train >= 2_000_000).astype(float) * 0.60
    weights += (y_train >= 3_000_000).astype(float) * 1.00

    weights = weights.clip(lower=1.0, upper=3.5)
    return weights / weights.mean()


def train_experiment(config):
    experiment_name = config["experiment"]
    df = config["df"]
    feature_cols = config["feature_cols"]

    X_train, X_test, y_train, y_test, train_rows, test_rows = split_train_test(df, feature_cols)
    pipeline, numeric_features, categorical_features = build_pipeline(feature_cols)
    y_train_log = np.log1p(y_train)
    sample_weights = make_training_sample_weights(train_rows, y_train)
    pipeline.fit(X_train, y_train_log, model__sample_weight=sample_weights)
    log_predictions = pipeline.predict(X_test)
    predictions = np.expm1(log_predictions)
    predictions = np.clip(predictions, a_min=0, a_max=None)
    metrics = regression_metrics(y_test, predictions)
    metrics.update(log_target_metrics(y_test, log_predictions))

    metrics_row = {
        "experiment": experiment_name,
        "experiment_name": config["experiment_name"],
        "dataset_name": config["dataset_name"],
        "dataset_label": config["dataset_label"],
        "model_family": "hist_gradient_boosting",
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "feature_count": len(feature_cols),
        "numeric_feature_count": len(numeric_features),
        "categorical_feature_count": len(categorical_features),
        "engineered_feature_count": len(available_columns(config["df"], ENGINEERED_FEATURE_CANDIDATES)),
        "target_transform": "log1p",
        "sample_weighting": "premium_rare_high_price_rows",
        "sample_weight_min": float(sample_weights.min()),
        "sample_weight_max": float(sample_weights.max()),
        **metrics,
    }

    pred_df = test_rows.copy()
    pred_df["experiment"] = experiment_name
    pred_df["experiment_name"] = config["experiment_name"]
    pred_df["dataset_label"] = config["dataset_label"]
    pred_df["model_family"] = "hist_gradient_boosting"
    pred_df["sample_weighting"] = "premium_rare_high_price_rows"
    pred_df["actual_price"] = y_test.values
    pred_df["predicted_price"] = predictions
    pred_df["actual_log_price"] = np.log1p(y_test.values)
    pred_df["predicted_log_price"] = log_predictions
    pred_df["absolute_error"] = np.abs(pred_df["actual_price"] - pred_df["predicted_price"])
    pred_df["absolute_percentage_error"] = (
        pred_df["absolute_error"] / np.maximum(np.abs(pred_df["actual_price"]), 1) * 100
    )
    pred_df["signed_error"] = pred_df["predicted_price"] - pred_df["actual_price"]
    pred_df["is_underprediction"] = pred_df["signed_error"] < 0

    model_path = MODEL_DIR / f"{experiment_name}.joblib"
    joblib.dump(pipeline, model_path)

    feature_metadata = {
        "experiment": experiment_name,
        "experiment_name": config["experiment_name"],
        "dataset_label": config["dataset_label"],
        "model_family": "hist_gradient_boosting",
        "feature_cols": feature_cols,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "engineered_features": available_columns(config["df"], ENGINEERED_FEATURE_CANDIDATES),
        "target_transform": "log1p",
        "sample_weighting": "premium_rare_high_price_rows",
        "model_path": str(model_path),
    }

    return metrics_row, pred_df, feature_metadata


all_metrics = []
all_predictions = []
feature_metadata_rows = []

for experiment_config in EXPERIMENTS:
    print("Training:", experiment_config["experiment_name"])
    metrics_row, pred_df, feature_metadata = train_experiment(experiment_config)
    all_metrics.append(metrics_row)
    all_predictions.append(pred_df)
    feature_metadata_rows.append(feature_metadata)
    print(metrics_row)

metrics_df = pd.DataFrame(all_metrics).sort_values("mae")
predictions_df = pd.concat(all_predictions, ignore_index=True)
feature_metadata_df = pd.DataFrame(feature_metadata_rows)

metrics_df

# %% [markdown]
# ## 7. Segment Evaluation

# %%
segment_columns = [
    "dataset_origin_display",
    "source_label",
    "city",
    "brand_model",
    "fuel_type",
    "transmission",
    "model_year",
    "brand_model_eval_group",
    "price_tail_group",
]

segment_metric_tables = []
for experiment_name, group in predictions_df.groupby("experiment"):
    for segment_col in segment_columns:
        table = segment_metrics(group, segment_col, min_rows=20)
        if len(table):
            table.insert(0, "experiment", experiment_name)
            table.insert(1, "experiment_name", EXPERIMENT_LABELS[experiment_name])
            table.insert(2, "dataset_label", group["dataset_label"].iloc[0])
            segment_metric_tables.append(table)

segment_metrics_df = (
    pd.concat(segment_metric_tables, ignore_index=True)
    if segment_metric_tables
    else pd.DataFrame()
)

segment_metrics_df.head(30)

# %%
key_segment_view = segment_metrics_df[
    segment_metrics_df["segment_column"].isin(
        ["brand_model_eval_group", "price_tail_group", "source_label", "dataset_origin_display"]
    )
].sort_values(["experiment", "segment_column", "mae"], ascending=[True, True, False])

key_segment_view

# %%
price_tail_metric_tables = []
for experiment_name, group in predictions_df.groupby("experiment"):
    table = segment_metrics(group, "price_tail_group", min_rows=1)
    if len(table):
        table.insert(0, "experiment", experiment_name)
        table.insert(1, "experiment_name", EXPERIMENT_LABELS[experiment_name])
        table.insert(2, "dataset_label", group["dataset_label"].iloc[0])
        price_tail_metric_tables.append(table)

price_tail_metrics_df = (
    pd.concat(price_tail_metric_tables, ignore_index=True)
    if price_tail_metric_tables
    else pd.DataFrame()
)

price_tail_metrics_df.sort_values(
    ["experiment", "segment_value"], ascending=[True, True]
)

# %%
def underprediction_summary(predictions, segment_col, min_rows=1):
    rows = []
    if segment_col not in predictions.columns:
        return pd.DataFrame()

    for segment_value, group in predictions.groupby(segment_col, dropna=False):
        if len(group) < min_rows:
            continue
        metrics = regression_metrics(group["actual_price"], group["predicted_price"])
        rows.append(
            {
                "segment_column": segment_col,
                "segment_value": segment_value,
                "rows": len(group),
                "underpredicted_rows": int(group["is_underprediction"].sum()),
                "underprediction_rate": metrics["underprediction_rate"],
                "median_actual_price": float(group["actual_price"].median()),
                "median_predicted_price": float(group["predicted_price"].median()),
                "mean_signed_error": metrics["mean_signed_error"],
                "median_signed_error": metrics["median_signed_error"],
                "mae": metrics["mae"],
                "mape": metrics["mape"],
                "r2": metrics["r2"] if len(group) > 1 else np.nan,
            }
        )
    return pd.DataFrame(rows)


underprediction_segment_columns = [
    "dataset_origin_display",
    "source_label",
    "brand_model_eval_group",
    "price_tail_group",
    "fuel_type",
    "transmission",
]

underprediction_tables = []
for experiment_name, group in predictions_df.groupby("experiment"):
    for segment_col in underprediction_segment_columns:
        table = underprediction_summary(group, segment_col, min_rows=1)
        if len(table):
            table.insert(0, "experiment", experiment_name)
            table.insert(1, "experiment_name", EXPERIMENT_LABELS[experiment_name])
            table.insert(2, "dataset_label", group["dataset_label"].iloc[0])
            underprediction_tables.append(table)

underprediction_diagnostics_df = (
    pd.concat(underprediction_tables, ignore_index=True)
    if underprediction_tables
    else pd.DataFrame()
)

underprediction_diagnostics_df.sort_values(
    ["experiment", "underprediction_rate", "mae"],
    ascending=[True, False, False],
).head(40)

# %% [markdown]
# ## 8. Baseline-vs-Gradient Boosting Comparison

# %%
RAW_RF_OUTPUT_ROOT = OUTPUT_ROOT.parent / "used_car_price_intelligence_baseline_modeling"
LOG_RF_OUTPUT_ROOT = OUTPUT_ROOT.parent / "used_car_price_intelligence_log_price_modeling"


def load_baseline_metrics(output_root, comparison_model, model_family, target_transform):
    metrics_path = output_root / "modeling_experiment_metrics.csv"
    if not metrics_path.exists():
        print(f"{comparison_model} metrics not found:", metrics_path)
        return pd.DataFrame()

    metrics = pd.read_csv(metrics_path).copy()
    metrics["comparison_model"] = comparison_model
    metrics["model_family"] = metrics.get("model_family", model_family)
    metrics["target_transform"] = metrics.get("target_transform", target_transform)
    return metrics


def load_baseline_predictions(output_root, comparison_model, model_family, target_transform):
    prediction_path = output_root / "baseline_predictions.csv"
    if not prediction_path.exists():
        print(f"{comparison_model} predictions not found:", prediction_path)
        return pd.DataFrame()

    predictions = pd.read_csv(prediction_path).copy()
    predictions["comparison_model"] = comparison_model
    predictions["model_family"] = model_family
    predictions["target_transform"] = target_transform
    if "signed_error" not in predictions.columns:
        predictions["signed_error"] = predictions["predicted_price"] - predictions["actual_price"]
    if "is_underprediction" not in predictions.columns:
        predictions["is_underprediction"] = predictions["signed_error"] < 0
    return predictions


raw_rf_metrics_df = load_baseline_metrics(
    RAW_RF_OUTPUT_ROOT,
    comparison_model="Raw-Price Random Forest",
    model_family="random_forest",
    target_transform="none",
)
log_rf_metrics_df = load_baseline_metrics(
    LOG_RF_OUTPUT_ROOT,
    comparison_model="Log-Price Random Forest",
    model_family="random_forest",
    target_transform="log1p",
)

gradient_metrics_df = metrics_df.copy()
gradient_metrics_df["comparison_model"] = "Premium-Weighted Log-Gradient Boosting"
gradient_metrics_df["model_family"] = "hist_gradient_boosting"

comparison_metric_cols = [
    "comparison_model",
    "experiment",
    "experiment_name",
    "dataset_name",
    "dataset_label",
    "model_family",
    "target_transform",
    "train_rows",
    "test_rows",
    "feature_count",
    "mae",
    "rmse",
    "mape",
    "r2",
    "underprediction_rate",
]

for frame in [raw_rf_metrics_df, log_rf_metrics_df, gradient_metrics_df]:
    for col in comparison_metric_cols:
        if col not in frame.columns:
            frame[col] = np.nan

model_comparison_long_df = pd.concat(
    [
        raw_rf_metrics_df[comparison_metric_cols],
        log_rf_metrics_df[comparison_metric_cols],
        gradient_metrics_df[comparison_metric_cols],
    ],
    ignore_index=True,
)

baseline_rows = model_comparison_long_df[
    model_comparison_long_df["comparison_model"].isin(
        ["Raw-Price Random Forest", "Log-Price Random Forest"]
    )
].copy()
gradient_rows = model_comparison_long_df[
    model_comparison_long_df["comparison_model"].eq("Premium-Weighted Log-Gradient Boosting")
].copy()

baseline_vs_gradient_comparison_df = baseline_rows.merge(
    gradient_rows,
    on="dataset_label",
    how="inner",
    suffixes=("_baseline", "_gradient"),
)
baseline_vs_gradient_comparison_df["mae_improvement_inr"] = (
    baseline_vs_gradient_comparison_df["mae_baseline"]
    - baseline_vs_gradient_comparison_df["mae_gradient"]
)
baseline_vs_gradient_comparison_df["mae_improvement_pct"] = (
    baseline_vs_gradient_comparison_df["mae_improvement_inr"]
    / baseline_vs_gradient_comparison_df["mae_baseline"]
    * 100
)
baseline_vs_gradient_comparison_df["mape_improvement_points"] = (
    baseline_vs_gradient_comparison_df["mape_baseline"]
    - baseline_vs_gradient_comparison_df["mape_gradient"]
)
baseline_vs_gradient_comparison_df["r2_delta"] = (
    baseline_vs_gradient_comparison_df["r2_gradient"]
    - baseline_vs_gradient_comparison_df["r2_baseline"]
)

model_comparison_long_df.sort_values(["dataset_label", "mae"])

# %%
raw_rf_predictions_df = load_baseline_predictions(
    RAW_RF_OUTPUT_ROOT,
    comparison_model="Raw-Price Random Forest",
    model_family="random_forest",
    target_transform="none",
)
log_rf_predictions_df = load_baseline_predictions(
    LOG_RF_OUTPUT_ROOT,
    comparison_model="Log-Price Random Forest",
    model_family="random_forest",
    target_transform="log1p",
)


def price_tail_metrics_for_predictions(predictions, comparison_model):
    if not len(predictions) or "price_tail_group" not in predictions.columns:
        return pd.DataFrame()

    tables = []
    for experiment_name, group in predictions.groupby("experiment"):
        table = segment_metrics(group, "price_tail_group", min_rows=1)
        if len(table):
            table.insert(0, "experiment", experiment_name)
            table.insert(1, "experiment_name", group["experiment_name"].iloc[0])
            table.insert(2, "dataset_label", group["dataset_label"].iloc[0])
            table.insert(3, "comparison_model", comparison_model)
            tables.append(table)

    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


raw_rf_price_tail_metrics_df = price_tail_metrics_for_predictions(
    raw_rf_predictions_df, "Raw-Price Random Forest"
)
log_rf_price_tail_metrics_df = price_tail_metrics_for_predictions(
    log_rf_predictions_df, "Log-Price Random Forest"
)

gradient_price_tail_metrics_df = price_tail_metrics_df.copy()
gradient_price_tail_metrics_df["comparison_model"] = "Premium-Weighted Log-Gradient Boosting"

price_tail_comparison_long_df = pd.concat(
    [
        raw_rf_price_tail_metrics_df,
        log_rf_price_tail_metrics_df,
        gradient_price_tail_metrics_df,
    ],
    ignore_index=True,
)

tail_baseline_rows = price_tail_comparison_long_df[
    price_tail_comparison_long_df["comparison_model"].isin(
        ["Raw-Price Random Forest", "Log-Price Random Forest"]
    )
].copy()
tail_gradient_rows = price_tail_comparison_long_df[
    price_tail_comparison_long_df["comparison_model"].eq(
        "Premium-Weighted Log-Gradient Boosting"
    )
].copy()

baseline_vs_gradient_price_tail_comparison_df = tail_baseline_rows.merge(
    tail_gradient_rows,
    on=["dataset_label", "segment_value"],
    how="inner",
    suffixes=("_baseline", "_gradient"),
)
baseline_vs_gradient_price_tail_comparison_df["mae_improvement_inr"] = (
    baseline_vs_gradient_price_tail_comparison_df["mae_baseline"]
    - baseline_vs_gradient_price_tail_comparison_df["mae_gradient"]
)
baseline_vs_gradient_price_tail_comparison_df["mape_improvement_points"] = (
    baseline_vs_gradient_price_tail_comparison_df["mape_baseline"]
    - baseline_vs_gradient_price_tail_comparison_df["mape_gradient"]
)
baseline_vs_gradient_price_tail_comparison_df["signed_error_shift_inr"] = (
    baseline_vs_gradient_price_tail_comparison_df["mean_signed_error_gradient"]
    - baseline_vs_gradient_price_tail_comparison_df["mean_signed_error_baseline"]
)

baseline_vs_gradient_price_tail_comparison_df.sort_values(
    ["dataset_label", "segment_value", "comparison_model_baseline"]
)

# %% [markdown]
# ## 9. Prediction Diagnostics

# %%
plt.figure(figsize=(9, 6))
sns.barplot(data=metrics_df, x="mae", y="experiment_name", color="#356f8c")
plt.title("Premium-Weighted Log-Gradient Boosting MAE By Experiment")
plt.xlabel("MAE INR")
plt.ylabel("")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "gradient_boosting_mae_by_experiment.png", dpi=160, bbox_inches="tight")
plt.show()

# %%
plt.figure(figsize=(8, 6))
sample_plot = predictions_df.sample(min(len(predictions_df), 2000), random_state=RANDOM_STATE)
sns.scatterplot(
    data=sample_plot,
    x="actual_price",
    y="predicted_price",
    hue="experiment_name",
    alpha=0.55,
)
limit = max(sample_plot["actual_price"].max(), sample_plot["predicted_price"].max())
plt.plot([0, limit], [0, limit], color="black", linestyle="--", linewidth=1)
plt.title("Premium-Weighted Log-Gradient Boosting: Predicted vs Actual Price")
plt.xlabel("Actual Price INR")
plt.ylabel("Predicted Price INR")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "gradient_boosting_predicted_vs_actual_price.png", dpi=160, bbox_inches="tight")
plt.show()

# %%
prediction_sample_cols = [
    "experiment",
    "experiment_name",
    "dataset_label",
    "listing_key",
    "dataset_origin_display",
    "source_label",
    "source",
    "city",
    "brand",
    "model",
    "variant",
    "brand_model",
    "model_year",
    "fuel_type",
    "transmission",
    "km_driven",
    "actual_price",
    "predicted_price",
    "absolute_error",
    "absolute_percentage_error",
    "signed_error",
    "is_underprediction",
    "brand_model_eval_group",
    "price_tail_group",
]
prediction_sample_cols = [col for col in prediction_sample_cols if col in predictions_df.columns]

predictions_df[prediction_sample_cols].sort_values("absolute_error", ascending=False).head(30)

# %% [markdown]
# ## 10. Gradient Boosting Decision Summary

# %%
best_by_mae = metrics_df.sort_values("mae").iloc[0]
best_by_mape = metrics_df.sort_values("mape").iloc[0]
combined_gradient_row = metrics_df[metrics_df["dataset_name"].eq("combined")].iloc[0]


def first_float(df, column):
    if len(df) and column in df.columns:
        return float(df.iloc[0][column])
    return np.nan


combined_vs_raw = baseline_vs_gradient_comparison_df[
    baseline_vs_gradient_comparison_df["dataset_label"].eq(DATASET_LABELS["combined"])
    & baseline_vs_gradient_comparison_df["comparison_model_baseline"].eq("Raw-Price Random Forest")
]
combined_vs_log_rf = baseline_vs_gradient_comparison_df[
    baseline_vs_gradient_comparison_df["dataset_label"].eq(DATASET_LABELS["combined"])
    & baseline_vs_gradient_comparison_df["comparison_model_baseline"].eq("Log-Price Random Forest")
]
combined_high_tail_vs_raw = baseline_vs_gradient_price_tail_comparison_df[
    baseline_vs_gradient_price_tail_comparison_df["dataset_label"].eq(DATASET_LABELS["combined"])
    & baseline_vs_gradient_price_tail_comparison_df["segment_value"].eq("high_price_tail")
    & baseline_vs_gradient_price_tail_comparison_df["comparison_model_baseline"].eq("Raw-Price Random Forest")
]
combined_high_tail_vs_log_rf = baseline_vs_gradient_price_tail_comparison_df[
    baseline_vs_gradient_price_tail_comparison_df["dataset_label"].eq(DATASET_LABELS["combined"])
    & baseline_vs_gradient_price_tail_comparison_df["segment_value"].eq("high_price_tail")
    & baseline_vs_gradient_price_tail_comparison_df["comparison_model_baseline"].eq("Log-Price Random Forest")
]

comparison_status = (
    "baseline_comparison_available"
    if len(baseline_vs_gradient_comparison_df)
    else "baseline_comparison_not_available"
)

modeling_decision = {
    "best_experiment_id_by_mae": best_by_mae["experiment"],
    "best_experiment_name_by_mae": best_by_mae["experiment_name"],
    "best_dataset_name_by_mae": best_by_mae["dataset_label"],
    "best_mae": float(best_by_mae["mae"]),
    "best_mape": float(best_by_mae["mape"]),
    "best_r2": float(best_by_mae["r2"]),
    "best_experiment_id_by_mape": best_by_mape["experiment"],
    "best_experiment_name_by_mape": best_by_mape["experiment_name"],
    "combined_gradient_mae": float(combined_gradient_row["mae"]),
    "combined_gradient_mape": float(combined_gradient_row["mape"]),
    "combined_gradient_r2": float(combined_gradient_row["r2"]),
    "combined_gradient_underprediction_rate": float(combined_gradient_row["underprediction_rate"]),
    "comparison_status": comparison_status,
    "combined_mae_improvement_pct_vs_raw_rf": first_float(combined_vs_raw, "mae_improvement_pct"),
    "combined_mape_improvement_points_vs_raw_rf": first_float(
        combined_vs_raw, "mape_improvement_points"
    ),
    "combined_r2_delta_vs_raw_rf": first_float(combined_vs_raw, "r2_delta"),
    "combined_mae_improvement_pct_vs_log_rf": first_float(combined_vs_log_rf, "mae_improvement_pct"),
    "combined_mape_improvement_points_vs_log_rf": first_float(
        combined_vs_log_rf, "mape_improvement_points"
    ),
    "combined_r2_delta_vs_log_rf": first_float(combined_vs_log_rf, "r2_delta"),
    "combined_high_tail_mae_improvement_vs_raw_rf": first_float(
        combined_high_tail_vs_raw, "mae_improvement_inr"
    ),
    "combined_high_tail_mae_improvement_vs_log_rf": first_float(
        combined_high_tail_vs_log_rf, "mae_improvement_inr"
    ),
    "recommended_next_step": (
        "Review this gradient boosting run against both Random Forest checkpoints. "
        "Promote only if it improves combined/live rows and does not worsen the "
        "high-price tail; otherwise move to premium-segment targeted modeling."
    ),
    "decision_warning": (
        "Do not promote from overall MAE alone. Check source drift, rare brand-model "
        "error, high-price signed error, and live-market segment behavior."
    ),
}

modeling_decision_df = pd.DataFrame([modeling_decision])
modeling_decision_df

# %% [markdown]
# ## 11. Save Modeling Outputs

# %%
metrics_df.to_csv(OUTPUT_ROOT / "modeling_experiment_metrics.csv", index=False)
predictions_df.to_csv(OUTPUT_ROOT / "baseline_predictions.csv", index=False)
predictions_df.to_csv(OUTPUT_ROOT / "gradient_boosting_predictions.csv", index=False)
segment_metrics_df.to_csv(OUTPUT_ROOT / "segment_metrics.csv", index=False)
key_segment_view.to_csv(OUTPUT_ROOT / "key_segment_metrics.csv", index=False)
price_tail_metrics_df.to_csv(OUTPUT_ROOT / "price_tail_metrics_min_rows_1.csv", index=False)
underprediction_diagnostics_df.to_csv(OUTPUT_ROOT / "underprediction_diagnostics.csv", index=False)
feature_metadata_df.to_csv(OUTPUT_ROOT / "feature_metadata.csv", index=False)
modeling_decision_df.to_csv(OUTPUT_ROOT / "modeling_decision_summary.csv", index=False)

if len(model_comparison_long_df):
    model_comparison_long_df.to_csv(
        OUTPUT_ROOT / "model_comparison_long.csv", index=False
    )

if len(baseline_vs_gradient_comparison_df):
    baseline_vs_gradient_comparison_df.to_csv(
        OUTPUT_ROOT / "baseline_vs_gradient_boosting_comparison.csv", index=False
    )

if len(price_tail_comparison_long_df):
    price_tail_comparison_long_df.to_csv(
        OUTPUT_ROOT / "price_tail_comparison_long.csv", index=False
    )

if len(baseline_vs_gradient_price_tail_comparison_df):
    baseline_vs_gradient_price_tail_comparison_df.to_csv(
        OUTPUT_ROOT / "baseline_vs_gradient_boosting_price_tail_comparison.csv",
        index=False,
    )

with (OUTPUT_ROOT / "feature_plan.json").open("w", encoding="utf-8") as f:
    json.dump(feature_plan, f, indent=2)

print(f"Saved modeling outputs to: {OUTPUT_ROOT}")
print(f"Saved model artifacts to: {MODEL_DIR}")
print(f"Saved figures to: {FIGURE_DIR}")

# %% [markdown]
# ## 12. Final Baseline Statement
#
# Gradient boosting modeling is complete when this notebook runs end to end and
# the baseline-vs-gradient comparison plus segment diagnostics are reviewed. The
# next phase should either promote this model as the stronger baseline or move
# into premium-segment targeted modeling if high-price underprediction remains.
