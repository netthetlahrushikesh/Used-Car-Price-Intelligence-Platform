"""10 percent MAPE target modeling notebook for the Used Car Price Intelligence Platform."""

# %% [markdown]
# # Used Car Price Intelligence Platform: 10 Percent Target Modeling
#
# This notebook runs the next modeling experiment after the Random Forest and
# premium-weighted gradient boosting checkpoints.
#
# Goal: push the combined trusted model toward **10% MAPE** without deleting
# genuine market-tail rows.
#
# Method:
#
# - keep the same three-dataset structure
# - use a `log1p(listed_price_inr)` target
# - use native categorical `HistGradientBoostingRegressor`
# - add train-only, out-of-fold target encoding for high-cardinality market fields
# - keep source, rare/common, and price-tail diagnostics

# %% [markdown]
# ## 0. Notebook Contract
#
# This notebook:
#
# - loads the trusted live, external, and combined modeling datasets
# - adds premium, usage, frequency, and interaction features
# - applies leakage-controlled out-of-fold target encoding
# - trains three comparable target-encoded native HGB models
# - compares against prior raw RF, log RF, and premium-weighted gradient baselines
# - saves metrics, predictions, segment diagnostics, and model artifacts
#
# Target encoding is fitted only from training folds. Test rows never contribute
# to their own encoded values.

# %%
from pathlib import Path
import json
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split

try:
    from IPython.display import display
except ImportError:
    def display(value):
        print(value)


warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
pd.set_option("display.max_columns", 140)
pd.set_option("display.float_format", lambda value: f"{value:,.2f}")

RANDOM_STATE = 42
TEST_SIZE = 0.20
TARGET = "listed_price_inr"
TARGET_TRANSFORM = "log1p"
RARE_BRAND_MODEL_MIN_ROWS = 10
TARGET_ENCODING_SMOOTHING = 10
TARGET_ENCODING_SPLITS = 5
HIGH_CARDINALITY_TOP_N = 180

DATASET_LABELS = {
    "live": "Live Trusted Market Snapshot",
    "external_true_value": "External True Value Historical Dataset",
    "combined": "Combined Trusted Modeling Dataset",
}

EXPERIMENT_LABELS = {
    "live_trusted_market_target_encoded_hgb": (
        "Live Trusted Market Target-Encoded Native HGB"
    ),
    "external_true_value_historical_target_encoded_hgb": (
        "External True Value Historical Target-Encoded Native HGB"
    ),
    "combined_trusted_lineage_target_encoded_hgb": (
        "Combined Trusted Lineage Target-Encoded Native HGB"
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
    ]
    external_candidates = [
        *(root / "external_true_value_historical_dataset_5614.csv" for root in upload_roots),
    ]
    combined_candidates = [
        *(root / "combined_trusted_modeling_dataset_9110.csv" for root in upload_roots),
    ]

    return {
        "live": first_existing_path(live_candidates),
        "external_true_value": first_existing_path(external_candidates),
        "combined": first_existing_path(combined_candidates),
    }, "local_project"


DATASETS, RUN_CONTEXT = resolve_dataset_paths()

if Path("/kaggle/working").exists():
    OUTPUT_ROOT = Path("/kaggle/working/used_car_price_intelligence_10_percent_target_modeling")
else:
    OUTPUT_ROOT = Path("notebooks") / "outputs" / "used_car_price_intelligence_10_percent_target_modeling"

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
    out["luxury_transmission"] = out["is_luxury_brand"].map({1: "luxury", 0: "non_luxury"}) + "__" + transmission_norm

    for col in ["brand_model", "model", "brand", "variant", "city_brand"]:
        if col in out.columns:
            counts = out[col].fillna("unknown").astype(str).value_counts()
            out[f"{col}_frequency"] = out[col].fillna("unknown").astype(str).map(counts).astype(float)

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
# ## 2. Feature Rules

# %%
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
]

COMBINED_ONLY_FEATURES = [
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


def available_columns(df, columns):
    return [col for col in columns if col in df.columns]


def dedupe_preserve_order(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def feature_columns_for_experiment(df, include_lineage=False):
    numeric = available_columns(df, NUMERIC_FEATURE_CANDIDATES)
    categorical = available_columns(df, CATEGORICAL_FEATURE_CANDIDATES)
    if include_lineage:
        categorical += available_columns(df, COMBINED_ONLY_FEATURES)
        numeric += available_columns(df, ["market_snapshot_year"])

    target_encoded = [f"te_{col}" for col in available_columns(df, TARGET_ENCODING_COLUMNS)]
    numeric += target_encoded
    numeric = dedupe_preserve_order(numeric)
    categorical = dedupe_preserve_order(categorical)
    return numeric, categorical, dedupe_preserve_order(numeric + categorical)


feature_plan = {
    "target": TARGET,
    "target_transform": TARGET_TRANSFORM,
    "model_family": "native_hist_gradient_boosting",
    "categorical_handling": "native_category_dtype",
    "target_encoding": {
        "columns": TARGET_ENCODING_COLUMNS,
        "smoothing": TARGET_ENCODING_SMOOTHING,
        "folds": TARGET_ENCODING_SPLITS,
        "train_strategy": "out_of_fold",
    },
    "high_cardinality_top_n": HIGH_CARDINALITY_TOP_N,
    "combined_numeric_features": feature_columns_for_experiment(combined, include_lineage=True)[0],
    "combined_categorical_features": feature_columns_for_experiment(combined, include_lineage=True)[1],
}

feature_plan

# %% [markdown]
# ## 3. Evaluation Labels

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
        [out[TARGET] < 50_000, out[TARGET] > 3_000_000],
        ["low_price_tail", "high_price_tail"],
        default="normal_price_range",
    )
    return out


live_labeled = add_eval_labels(live)
external_labeled = add_eval_labels(external)
combined_labeled = add_eval_labels(combined)

print("Rare brand-model groups:", len(rare_brand_models))
combined_labeled["brand_model_eval_group"].value_counts(normalize=True).mul(100).round(2)

# %% [markdown]
# ## 4. Target Encoding And Native Categorical Preparation

# %%
def smoothed_target_mapping(series, y_log, smoothing):
    global_mean = float(y_log.mean())
    tmp = pd.DataFrame(
        {
            "category": series.fillna("unknown").astype(str),
            "target": y_log,
        }
    )
    stats = tmp.groupby("category")["target"].agg(["mean", "count"])
    encoded = (stats["count"] * stats["mean"] + smoothing * global_mean) / (
        stats["count"] + smoothing
    )
    return encoded, global_mean


def add_out_of_fold_target_encoding(train_rows, test_rows, columns):
    train_encoded = train_rows.copy()
    test_encoded = test_rows.copy()
    y_log = np.log1p(train_encoded[TARGET])
    kfold = KFold(n_splits=TARGET_ENCODING_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    encoding_artifacts = {}

    for col in columns:
        if col not in train_encoded.columns:
            continue

        oof_values = pd.Series(index=train_encoded.index, dtype=float)
        for train_pos, valid_pos in kfold.split(train_encoded):
            fold_train = train_encoded.iloc[train_pos]
            fold_valid = train_encoded.iloc[valid_pos]
            mapping, global_mean = smoothed_target_mapping(
                fold_train[col],
                np.log1p(fold_train[TARGET]),
                TARGET_ENCODING_SMOOTHING,
            )
            oof_values.iloc[valid_pos] = (
                fold_valid[col]
                .fillna("unknown")
                .astype(str)
                .map(mapping)
                .fillna(global_mean)
                .to_numpy()
            )

        full_mapping, full_global_mean = smoothed_target_mapping(
            train_encoded[col],
            y_log,
            TARGET_ENCODING_SMOOTHING,
        )
        train_encoded[f"te_{col}"] = oof_values
        test_encoded[f"te_{col}"] = (
            test_encoded[col]
            .fillna("unknown")
            .astype(str)
            .map(full_mapping)
            .fillna(full_global_mean)
            .to_numpy()
        )
        encoding_artifacts[col] = {
            "mapping": full_mapping.to_dict(),
            "global_mean": full_global_mean,
            "smoothing": TARGET_ENCODING_SMOOTHING,
        }

    return train_encoded, test_encoded, encoding_artifacts


def prepare_native_hgb_features(train_rows, test_rows, numeric_features, categorical_features):
    train_x = train_rows[numeric_features + categorical_features].copy()
    test_x = test_rows[numeric_features + categorical_features].copy()
    category_levels = {}

    for col in numeric_features:
        train_x[col] = pd.to_numeric(train_x[col], errors="coerce")
        test_x[col] = pd.to_numeric(test_x[col], errors="coerce")

    for col in categorical_features:
        train_series = train_x[col].fillna("unknown").astype(str)
        test_series = test_x[col].fillna("unknown").astype(str)
        value_counts = train_series.value_counts()
        if len(value_counts) > 250:
            keep = set(value_counts.head(HIGH_CARDINALITY_TOP_N).index)
            train_series = train_series.where(train_series.isin(keep), "__other__")
            test_series = test_series.where(test_series.isin(keep), "__other__")
        else:
            keep = set(value_counts.index)
            test_series = test_series.where(test_series.isin(keep), "__other__")

        categories = sorted(set(train_series.unique()).union({"__other__"}))
        train_x[col] = pd.Categorical(train_series, categories=categories)
        test_x[col] = pd.Categorical(test_series, categories=categories)
        category_levels[col] = categories

    return train_x, test_x, category_levels

# %% [markdown]
# ## 5. Split And Metric Helpers

# %%
def make_price_stratification(y, max_bins=10):
    labels = pd.qcut(y, q=max_bins, duplicates="drop")
    counts = labels.value_counts()
    if len(counts) < 2 or counts.min() < 2:
        return None
    return labels


def split_train_test(df):
    model_df = df.dropna(subset=[TARGET]).copy()
    y = model_df[TARGET]
    stratify_labels = make_price_stratification(y)
    try:
        return train_test_split(
            model_df,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=stratify_labels,
        )
    except ValueError:
        return train_test_split(
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
        "r2": r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan,
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


def build_model():
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
        random_state=RANDOM_STATE,
    )

# %% [markdown]
# ## 6. Train 10 Percent Target Experiments

# %%
EXPERIMENTS = [
    {
        "experiment": "live_trusted_market_target_encoded_hgb",
        "experiment_name": EXPERIMENT_LABELS["live_trusted_market_target_encoded_hgb"],
        "dataset_name": "live",
        "dataset_label": DATASET_LABELS["live"],
        "df": live_labeled,
        "include_lineage": False,
    },
    {
        "experiment": "external_true_value_historical_target_encoded_hgb",
        "experiment_name": EXPERIMENT_LABELS[
            "external_true_value_historical_target_encoded_hgb"
        ],
        "dataset_name": "external_true_value",
        "dataset_label": DATASET_LABELS["external_true_value"],
        "df": external_labeled,
        "include_lineage": False,
    },
    {
        "experiment": "combined_trusted_lineage_target_encoded_hgb",
        "experiment_name": EXPERIMENT_LABELS["combined_trusted_lineage_target_encoded_hgb"],
        "dataset_name": "combined",
        "dataset_label": DATASET_LABELS["combined"],
        "df": combined_labeled,
        "include_lineage": True,
    },
]

[(exp["experiment_name"], exp["dataset_label"], len(exp["df"])) for exp in EXPERIMENTS]

# %%
def train_experiment(config):
    train_rows, test_rows = split_train_test(config["df"])
    target_encoding_cols = available_columns(train_rows, TARGET_ENCODING_COLUMNS)
    train_encoded, test_encoded, encoding_artifacts = add_out_of_fold_target_encoding(
        train_rows,
        test_rows,
        target_encoding_cols,
    )

    numeric_features, categorical_features, feature_cols = feature_columns_for_experiment(
        train_encoded,
        include_lineage=config["include_lineage"],
    )
    train_x, test_x, category_levels = prepare_native_hgb_features(
        train_encoded,
        test_encoded,
        numeric_features,
        categorical_features,
    )

    y_train = train_encoded[TARGET]
    y_test = test_encoded[TARGET]
    y_train_log = np.log1p(y_train)

    model = build_model()
    model.fit(train_x, y_train_log)
    log_predictions = model.predict(test_x)
    predictions = np.clip(np.expm1(log_predictions), 0, None)
    metrics = regression_metrics(y_test, predictions)
    metrics.update(log_target_metrics(y_test, log_predictions))

    metrics_row = {
        "experiment": config["experiment"],
        "experiment_name": config["experiment_name"],
        "dataset_name": config["dataset_name"],
        "dataset_label": config["dataset_label"],
        "model_family": "native_hist_gradient_boosting",
        "target_transform": TARGET_TRANSFORM,
        "target_encoding_smoothing": TARGET_ENCODING_SMOOTHING,
        "target_encoding_splits": TARGET_ENCODING_SPLITS,
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "feature_count": len(feature_cols),
        "numeric_feature_count": len(numeric_features),
        "categorical_feature_count": len(categorical_features),
        "target_encoded_feature_count": len(target_encoding_cols),
        "hgb_iterations": int(model.n_iter_),
        **metrics,
    }

    pred_df = test_encoded.copy()
    pred_df["experiment"] = config["experiment"]
    pred_df["experiment_name"] = config["experiment_name"]
    pred_df["dataset_label"] = config["dataset_label"]
    pred_df["model_family"] = "native_hist_gradient_boosting"
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

    model_path = MODEL_DIR / f"{config['experiment']}.joblib"
    artifact = {
        "model": model,
        "feature_cols": feature_cols,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "target_encoding_columns": target_encoding_cols,
        "target_encoding_artifacts": encoding_artifacts,
        "category_levels": category_levels,
        "target_transform": TARGET_TRANSFORM,
        "high_cardinality_top_n": HIGH_CARDINALITY_TOP_N,
    }
    joblib.dump(artifact, model_path)

    feature_metadata = {
        "experiment": config["experiment"],
        "experiment_name": config["experiment_name"],
        "dataset_label": config["dataset_label"],
        "model_family": "native_hist_gradient_boosting",
        "feature_cols": feature_cols,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "target_encoding_columns": target_encoding_cols,
        "target_transform": TARGET_TRANSFORM,
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

price_tail_metrics_df.sort_values(["experiment", "segment_value"])

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
# ## 8. Baseline Comparison

# %%
BASELINE_OUTPUTS = [
    (
        "Raw-Price Random Forest",
        OUTPUT_ROOT.parent / "used_car_price_intelligence_baseline_modeling",
        "random_forest",
        "none",
    ),
    (
        "Log-Price Random Forest",
        OUTPUT_ROOT.parent / "used_car_price_intelligence_log_price_modeling",
        "random_forest",
        "log1p",
    ),
    (
        "Premium-Weighted Log-Gradient Boosting",
        OUTPUT_ROOT.parent / "used_car_price_intelligence_gradient_boosting_modeling",
        "hist_gradient_boosting",
        "log1p",
    ),
]


def load_baseline_metrics(label, output_root, model_family, target_transform):
    metrics_path = output_root / "modeling_experiment_metrics.csv"
    if not metrics_path.exists():
        print(f"{label} metrics not found:", metrics_path)
        return pd.DataFrame()
    metrics = pd.read_csv(metrics_path).copy()
    metrics["comparison_model"] = label
    metrics["model_family"] = metrics.get("model_family", model_family)
    metrics["target_transform"] = metrics.get("target_transform", target_transform)
    return metrics


def load_baseline_predictions(label, output_root, model_family, target_transform):
    prediction_path = output_root / "baseline_predictions.csv"
    if not prediction_path.exists():
        print(f"{label} predictions not found:", prediction_path)
        return pd.DataFrame()
    predictions = pd.read_csv(prediction_path).copy()
    predictions["comparison_model"] = label
    predictions["model_family"] = model_family
    predictions["target_transform"] = target_transform
    if "signed_error" not in predictions.columns:
        predictions["signed_error"] = predictions["predicted_price"] - predictions["actual_price"]
    if "is_underprediction" not in predictions.columns:
        predictions["is_underprediction"] = predictions["signed_error"] < 0
    return predictions


baseline_metrics = [
    load_baseline_metrics(label, root, family, transform)
    for label, root, family, transform in BASELINE_OUTPUTS
]

target_metrics = metrics_df.copy()
target_metrics["comparison_model"] = "Target-Encoded Native HGB"

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

for frame in [*baseline_metrics, target_metrics]:
    for col in comparison_metric_cols:
        if col not in frame.columns:
            frame[col] = np.nan

model_comparison_long_df = pd.concat(
    [*(frame[comparison_metric_cols] for frame in baseline_metrics), target_metrics[comparison_metric_cols]],
    ignore_index=True,
)

baseline_rows = model_comparison_long_df[
    ~model_comparison_long_df["comparison_model"].eq("Target-Encoded Native HGB")
].copy()
target_rows = model_comparison_long_df[
    model_comparison_long_df["comparison_model"].eq("Target-Encoded Native HGB")
].copy()

baseline_vs_target_comparison_df = baseline_rows.merge(
    target_rows,
    on="dataset_label",
    how="inner",
    suffixes=("_baseline", "_target_encoded"),
)
baseline_vs_target_comparison_df["mae_improvement_inr"] = (
    baseline_vs_target_comparison_df["mae_baseline"]
    - baseline_vs_target_comparison_df["mae_target_encoded"]
)
baseline_vs_target_comparison_df["mae_improvement_pct"] = (
    baseline_vs_target_comparison_df["mae_improvement_inr"]
    / baseline_vs_target_comparison_df["mae_baseline"]
    * 100
)
baseline_vs_target_comparison_df["mape_improvement_points"] = (
    baseline_vs_target_comparison_df["mape_baseline"]
    - baseline_vs_target_comparison_df["mape_target_encoded"]
)
baseline_vs_target_comparison_df["r2_delta"] = (
    baseline_vs_target_comparison_df["r2_target_encoded"]
    - baseline_vs_target_comparison_df["r2_baseline"]
)

model_comparison_long_df.sort_values(["dataset_label", "mape"])

# %%
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


baseline_prediction_frames = [
    load_baseline_predictions(label, root, family, transform)
    for label, root, family, transform in BASELINE_OUTPUTS
]

baseline_price_tail_metrics = [
    price_tail_metrics_for_predictions(frame, label)
    for frame, (label, _, _, _) in zip(baseline_prediction_frames, BASELINE_OUTPUTS)
]

target_price_tail_metrics = price_tail_metrics_df.copy()
target_price_tail_metrics["comparison_model"] = "Target-Encoded Native HGB"

price_tail_comparison_long_df = pd.concat(
    [*baseline_price_tail_metrics, target_price_tail_metrics],
    ignore_index=True,
)

tail_baseline_rows = price_tail_comparison_long_df[
    ~price_tail_comparison_long_df["comparison_model"].eq("Target-Encoded Native HGB")
].copy()
tail_target_rows = price_tail_comparison_long_df[
    price_tail_comparison_long_df["comparison_model"].eq("Target-Encoded Native HGB")
].copy()

baseline_vs_target_price_tail_comparison_df = tail_baseline_rows.merge(
    tail_target_rows,
    on=["dataset_label", "segment_value"],
    how="inner",
    suffixes=("_baseline", "_target_encoded"),
)
baseline_vs_target_price_tail_comparison_df["mae_improvement_inr"] = (
    baseline_vs_target_price_tail_comparison_df["mae_baseline"]
    - baseline_vs_target_price_tail_comparison_df["mae_target_encoded"]
)
baseline_vs_target_price_tail_comparison_df["mape_improvement_points"] = (
    baseline_vs_target_price_tail_comparison_df["mape_baseline"]
    - baseline_vs_target_price_tail_comparison_df["mape_target_encoded"]
)
baseline_vs_target_price_tail_comparison_df["signed_error_shift_inr"] = (
    baseline_vs_target_price_tail_comparison_df["mean_signed_error_target_encoded"]
    - baseline_vs_target_price_tail_comparison_df["mean_signed_error_baseline"]
)

baseline_vs_target_price_tail_comparison_df.sort_values(
    ["dataset_label", "segment_value", "comparison_model_baseline"]
)

# %% [markdown]
# ## 9. Prediction Diagnostics

# %%
plt.figure(figsize=(9, 6))
sns.barplot(data=metrics_df, x="mape", y="experiment_name", color="#356f8c")
plt.title("Target-Encoded Native HGB MAPE By Experiment")
plt.xlabel("MAPE %")
plt.ylabel("")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "target_encoded_hgb_mape_by_experiment.png", dpi=160, bbox_inches="tight")
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
plt.title("Target-Encoded Native HGB: Predicted vs Actual Price")
plt.xlabel("Actual Price INR")
plt.ylabel("Predicted Price INR")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "target_encoded_hgb_predicted_vs_actual_price.png", dpi=160, bbox_inches="tight")
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
# ## 10. Decision Summary

# %%
best_by_mape = metrics_df.sort_values("mape").iloc[0]
combined_target_row = metrics_df[metrics_df["dataset_name"].eq("combined")].iloc[0]


def first_float(df, column):
    if len(df) and column in df.columns:
        return float(df.iloc[0][column])
    return np.nan


combined_vs_raw = baseline_vs_target_comparison_df[
    baseline_vs_target_comparison_df["dataset_label"].eq(DATASET_LABELS["combined"])
    & baseline_vs_target_comparison_df["comparison_model_baseline"].eq("Raw-Price Random Forest")
]
combined_vs_premium_gradient = baseline_vs_target_comparison_df[
    baseline_vs_target_comparison_df["dataset_label"].eq(DATASET_LABELS["combined"])
    & baseline_vs_target_comparison_df["comparison_model_baseline"].eq(
        "Premium-Weighted Log-Gradient Boosting"
    )
]
combined_high_tail_vs_premium_gradient = baseline_vs_target_price_tail_comparison_df[
    baseline_vs_target_price_tail_comparison_df["dataset_label"].eq(DATASET_LABELS["combined"])
    & baseline_vs_target_price_tail_comparison_df["segment_value"].eq("high_price_tail")
    & baseline_vs_target_price_tail_comparison_df["comparison_model_baseline"].eq(
        "Premium-Weighted Log-Gradient Boosting"
    )
]

modeling_decision = {
    "target_achieved": bool(combined_target_row["mape"] <= 10.0),
    "best_experiment_id_by_mape": best_by_mape["experiment"],
    "best_experiment_name_by_mape": best_by_mape["experiment_name"],
    "best_dataset_name_by_mape": best_by_mape["dataset_label"],
    "best_mape": float(best_by_mape["mape"]),
    "combined_target_mape": float(combined_target_row["mape"]),
    "combined_target_mae": float(combined_target_row["mae"]),
    "combined_target_r2": float(combined_target_row["r2"]),
    "combined_underprediction_rate": float(combined_target_row["underprediction_rate"]),
    "combined_mape_improvement_points_vs_raw_rf": first_float(
        combined_vs_raw,
        "mape_improvement_points",
    ),
    "combined_mape_improvement_points_vs_premium_gradient": first_float(
        combined_vs_premium_gradient,
        "mape_improvement_points",
    ),
    "combined_high_tail_mae_improvement_vs_premium_gradient": first_float(
        combined_high_tail_vs_premium_gradient,
        "mae_improvement_inr",
    ),
    "recommended_next_step": (
        "Use this as the 10 percent MAPE candidate for the main combined model, "
        "but keep a separate premium-tail improvement track because high-price "
        "rows remain underpredicted."
    ),
    "decision_warning": (
        "Target encoding improves overall MAPE, but it must remain leakage-controlled. "
        "Do not remove genuine market-tail rows to improve headline metrics."
    ),
}

modeling_decision_df = pd.DataFrame([modeling_decision])
modeling_decision_df

# %% [markdown]
# ## 11. Save Outputs

# %%
metrics_df.to_csv(OUTPUT_ROOT / "modeling_experiment_metrics.csv", index=False)
predictions_df.to_csv(OUTPUT_ROOT / "baseline_predictions.csv", index=False)
predictions_df.to_csv(OUTPUT_ROOT / "target_encoded_hgb_predictions.csv", index=False)
segment_metrics_df.to_csv(OUTPUT_ROOT / "segment_metrics.csv", index=False)
key_segment_view.to_csv(OUTPUT_ROOT / "key_segment_metrics.csv", index=False)
price_tail_metrics_df.to_csv(OUTPUT_ROOT / "price_tail_metrics_min_rows_1.csv", index=False)
underprediction_diagnostics_df.to_csv(OUTPUT_ROOT / "underprediction_diagnostics.csv", index=False)
feature_metadata_df.to_csv(OUTPUT_ROOT / "feature_metadata.csv", index=False)
modeling_decision_df.to_csv(OUTPUT_ROOT / "modeling_decision_summary.csv", index=False)
model_comparison_long_df.to_csv(OUTPUT_ROOT / "model_comparison_long.csv", index=False)
baseline_vs_target_comparison_df.to_csv(
    OUTPUT_ROOT / "baseline_vs_target_encoded_hgb_comparison.csv",
    index=False,
)
price_tail_comparison_long_df.to_csv(OUTPUT_ROOT / "price_tail_comparison_long.csv", index=False)
baseline_vs_target_price_tail_comparison_df.to_csv(
    OUTPUT_ROOT / "baseline_vs_target_encoded_hgb_price_tail_comparison.csv",
    index=False,
)

with (OUTPUT_ROOT / "feature_plan.json").open("w", encoding="utf-8") as f:
    json.dump(feature_plan, f, indent=2)

print(f"Saved modeling outputs to: {OUTPUT_ROOT}")
print(f"Saved model artifacts to: {MODEL_DIR}")
print(f"Saved figures to: {FIGURE_DIR}")

# %% [markdown]
# ## 12. Final Statement
#
# The 10 percent target experiment is complete when the notebook runs end to end
# and the combined model achieves MAPE at or below 10%. If achieved, this becomes
# the main headline model candidate, while premium-tail underprediction remains a
# separate improvement track.
