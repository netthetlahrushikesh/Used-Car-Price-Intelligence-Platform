"""Log-price baseline modeling notebook for the Used Car Price Intelligence Platform."""

# %% [markdown]
# # Used Car Price Intelligence Platform: Log-Price Baseline Modeling
#
# This notebook executes the second controlled modeling experiment after the
# raw-price Random Forest baseline.
#
# We train the same three-dataset structure using a `log1p(listed_price_inr)`
# target and evaluate predictions after converting them back to INR.
#
# 1. **Live Trusted Market Log-Price Baseline**
# 2. **External True Value Historical Log-Price Baseline**
# 3. **Combined Trusted Lineage Log-Price Baseline**
#
# The goal is to reduce relative error and high-price underprediction without
# changing the feature set or validation structure.

# %% [markdown]
# ## 0. Notebook Contract
#
# This notebook:
#
# - loads the same three datasets used in final EDA
# - excludes leakage/id/capture columns
# - uses one shared sklearn preprocessing and model pipeline
# - trains three comparable log-target baseline regressors
# - saves overall metrics, segment metrics, prediction samples, and model artifacts
# - compares log-price results against the raw-price baseline when those outputs exist
#
# It intentionally avoids hyperparameter tuning so the effect of the target
# transformation is visible.

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
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.preprocessing import OneHotEncoder

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
    "live_trusted_market_log_price_baseline": "Live Trusted Market Log-Price Baseline",
    "external_true_value_historical_log_price_baseline": (
        "External True Value Historical Log-Price Baseline"
    ),
    "combined_trusted_lineage_log_price_baseline": "Combined Trusted Lineage Log-Price Baseline",
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
    OUTPUT_ROOT = Path("/kaggle/working/used_car_price_intelligence_log_price_modeling")
else:
    OUTPUT_ROOT = Path("notebooks") / "outputs" / "used_car_price_intelligence_log_price_modeling"

MODEL_DIR = OUTPUT_ROOT / "models"
FIGURE_DIR = OUTPUT_ROOT / "figures"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

print("Run context:", RUN_CONTEXT)
print("Output root:", OUTPUT_ROOT)
for name, path in DATASETS.items():
    print(f"{DATASET_LABELS[name]}: {path} | exists={path.exists()}")

# %%
live = pd.read_csv(DATASETS["live"])
external = pd.read_csv(DATASETS["external_true_value"])
combined = pd.read_csv(DATASETS["combined"])

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
]


def available_columns(df, columns):
    return [col for col in columns if col in df.columns]


def feature_columns_for_experiment(df, include_lineage=False):
    features = available_columns(df, CORE_FEATURE_CANDIDATES)
    if include_lineage:
        features += available_columns(df, COMBINED_ONLY_FEATURES)
    return features


live_external_features = feature_columns_for_experiment(combined, include_lineage=False)
combined_features = feature_columns_for_experiment(combined, include_lineage=True)

feature_plan = {
    "target": TARGET,
    "excluded_columns": available_columns(combined, LEAKAGE_OR_ID_COLS),
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
def make_one_hot_encoder():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


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
            ("onehot", make_one_hot_encoder()),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )

    model = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
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
# ## 6. Train Log-Price Baseline Experiments

# %%
EXPERIMENTS = [
    {
        "experiment": "live_trusted_market_log_price_baseline",
        "experiment_name": EXPERIMENT_LABELS["live_trusted_market_log_price_baseline"],
        "dataset_name": "live",
        "dataset_label": DATASET_LABELS["live"],
        "df": live_labeled,
        "feature_cols": feature_columns_for_experiment(live_labeled, include_lineage=False),
        "include_lineage": False,
    },
    {
        "experiment": "external_true_value_historical_log_price_baseline",
        "experiment_name": EXPERIMENT_LABELS[
            "external_true_value_historical_log_price_baseline"
        ],
        "dataset_name": "external_true_value",
        "dataset_label": DATASET_LABELS["external_true_value"],
        "df": external_labeled,
        "feature_cols": feature_columns_for_experiment(external_labeled, include_lineage=False),
        "include_lineage": False,
    },
    {
        "experiment": "combined_trusted_lineage_log_price_baseline",
        "experiment_name": EXPERIMENT_LABELS["combined_trusted_lineage_log_price_baseline"],
        "dataset_name": "combined",
        "dataset_label": DATASET_LABELS["combined"],
        "df": combined_labeled,
        "feature_cols": feature_columns_for_experiment(combined_labeled, include_lineage=True),
        "include_lineage": True,
    },
]

[(exp["experiment_name"], exp["dataset_label"], len(exp["df"]), exp["feature_cols"]) for exp in EXPERIMENTS]

# %%
def train_experiment(config):
    experiment_name = config["experiment"]
    df = config["df"]
    feature_cols = config["feature_cols"]

    X_train, X_test, y_train, y_test, train_rows, test_rows = split_train_test(df, feature_cols)
    pipeline, numeric_features, categorical_features = build_pipeline(feature_cols)
    y_train_log = np.log1p(y_train)
    pipeline.fit(X_train, y_train_log)
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
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "feature_count": len(feature_cols),
        "numeric_feature_count": len(numeric_features),
        "categorical_feature_count": len(categorical_features),
        "target_transform": "log1p",
        **metrics,
    }

    pred_df = test_rows.copy()
    pred_df["experiment"] = experiment_name
    pred_df["experiment_name"] = config["experiment_name"]
    pred_df["dataset_label"] = config["dataset_label"]
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
        "feature_cols": feature_cols,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "target_transform": "log1p",
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
# ## 8. Raw-vs-Log Baseline Comparison

# %%
RAW_BASELINE_OUTPUT_ROOT = OUTPUT_ROOT.parent / "used_car_price_intelligence_baseline_modeling"
RAW_BASELINE_METRICS_PATH = RAW_BASELINE_OUTPUT_ROOT / "modeling_experiment_metrics.csv"
RAW_BASELINE_PREDICTIONS_PATH = RAW_BASELINE_OUTPUT_ROOT / "baseline_predictions.csv"


def load_raw_baseline_metrics():
    if not RAW_BASELINE_METRICS_PATH.exists():
        print("Raw-price baseline metrics not found:", RAW_BASELINE_METRICS_PATH)
        return pd.DataFrame()

    raw = pd.read_csv(RAW_BASELINE_METRICS_PATH)
    raw = raw.copy()
    raw["target_transform"] = raw.get("target_transform", "raw_price")
    return raw


def load_raw_baseline_predictions():
    if not RAW_BASELINE_PREDICTIONS_PATH.exists():
        print("Raw-price baseline predictions not found:", RAW_BASELINE_PREDICTIONS_PATH)
        return pd.DataFrame()

    raw = pd.read_csv(RAW_BASELINE_PREDICTIONS_PATH)
    return raw.copy()


raw_metrics_df = load_raw_baseline_metrics()
raw_predictions_df = load_raw_baseline_predictions()

if len(raw_metrics_df):
    raw_compare = raw_metrics_df[
        ["dataset_label", "experiment_name", "mae", "rmse", "mape", "r2"]
    ].rename(
        columns={
            "experiment_name": "raw_experiment_name",
            "mae": "raw_mae",
            "rmse": "raw_rmse",
            "mape": "raw_mape",
            "r2": "raw_r2",
        }
    )
    log_compare = metrics_df[
        [
            "dataset_label",
            "experiment_name",
            "mae",
            "rmse",
            "mape",
            "r2",
            "underprediction_rate",
            "log_mae",
        ]
    ].rename(
        columns={
            "experiment_name": "log_experiment_name",
            "mae": "log_mae_inr",
            "rmse": "log_rmse",
            "mape": "log_mape",
            "r2": "log_r2",
            "underprediction_rate": "log_underprediction_rate",
            "log_mae": "log_target_mae",
        }
    )
    raw_vs_log_comparison_df = raw_compare.merge(log_compare, on="dataset_label", how="inner")
    raw_vs_log_comparison_df["mae_improvement_inr"] = (
        raw_vs_log_comparison_df["raw_mae"] - raw_vs_log_comparison_df["log_mae_inr"]
    )
    raw_vs_log_comparison_df["mae_improvement_pct"] = (
        raw_vs_log_comparison_df["mae_improvement_inr"]
        / raw_vs_log_comparison_df["raw_mae"]
        * 100
    )
    raw_vs_log_comparison_df["mape_improvement_points"] = (
        raw_vs_log_comparison_df["raw_mape"] - raw_vs_log_comparison_df["log_mape"]
    )
    raw_vs_log_comparison_df["r2_delta"] = (
        raw_vs_log_comparison_df["log_r2"] - raw_vs_log_comparison_df["raw_r2"]
    )
else:
    raw_vs_log_comparison_df = pd.DataFrame()

raw_vs_log_comparison_df

# %%
raw_price_tail_metrics_df = pd.DataFrame()
raw_vs_log_price_tail_comparison_df = pd.DataFrame()

if len(raw_predictions_df) and "price_tail_group" in raw_predictions_df.columns:
    raw_price_tail_tables = []
    for experiment_name, group in raw_predictions_df.groupby("experiment"):
        table = segment_metrics(group, "price_tail_group", min_rows=1)
        if len(table):
            table.insert(0, "experiment", experiment_name)
            table.insert(1, "experiment_name", group["experiment_name"].iloc[0])
            table.insert(2, "dataset_label", group["dataset_label"].iloc[0])
            raw_price_tail_tables.append(table)

    raw_price_tail_metrics_df = (
        pd.concat(raw_price_tail_tables, ignore_index=True)
        if raw_price_tail_tables
        else pd.DataFrame()
    )

if len(raw_price_tail_metrics_df) and len(price_tail_metrics_df):
    tail_compare_cols = [
        "dataset_label",
        "segment_value",
        "rows",
        "mae",
        "mape",
        "mean_signed_error",
        "median_signed_error",
        "underprediction_rate",
    ]
    raw_tail_compare = raw_price_tail_metrics_df[tail_compare_cols].rename(
        columns={
            "rows": "raw_rows",
            "mae": "raw_mae",
            "mape": "raw_mape",
            "mean_signed_error": "raw_mean_signed_error",
            "median_signed_error": "raw_median_signed_error",
            "underprediction_rate": "raw_underprediction_rate",
        }
    )
    log_tail_compare = price_tail_metrics_df[tail_compare_cols].rename(
        columns={
            "rows": "log_rows",
            "mae": "log_mae",
            "mape": "log_mape",
            "mean_signed_error": "log_mean_signed_error",
            "median_signed_error": "log_median_signed_error",
            "underprediction_rate": "log_underprediction_rate",
        }
    )
    raw_vs_log_price_tail_comparison_df = raw_tail_compare.merge(
        log_tail_compare, on=["dataset_label", "segment_value"], how="inner"
    )
    raw_vs_log_price_tail_comparison_df["mae_improvement_inr"] = (
        raw_vs_log_price_tail_comparison_df["raw_mae"]
        - raw_vs_log_price_tail_comparison_df["log_mae"]
    )
    raw_vs_log_price_tail_comparison_df["mape_improvement_points"] = (
        raw_vs_log_price_tail_comparison_df["raw_mape"]
        - raw_vs_log_price_tail_comparison_df["log_mape"]
    )
    raw_vs_log_price_tail_comparison_df["signed_error_shift_inr"] = (
        raw_vs_log_price_tail_comparison_df["log_mean_signed_error"]
        - raw_vs_log_price_tail_comparison_df["raw_mean_signed_error"]
    )

raw_vs_log_price_tail_comparison_df.sort_values(
    ["dataset_label", "segment_value"]
)

# %% [markdown]
# ## 9. Prediction Diagnostics

# %%
plt.figure(figsize=(9, 6))
sns.barplot(data=metrics_df, x="mae", y="experiment_name", color="#356f8c")
plt.title("Log-Price Baseline MAE By Experiment")
plt.xlabel("MAE INR")
plt.ylabel("")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "log_price_mae_by_experiment.png", dpi=160, bbox_inches="tight")
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
plt.title("Log-Price Baseline: Predicted vs Actual Price")
plt.xlabel("Actual Price INR")
plt.ylabel("Predicted Price INR")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "log_price_predicted_vs_actual_price.png", dpi=160, bbox_inches="tight")
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
# ## 10. Log-Price Baseline Decision Summary

# %%
best_by_mae = metrics_df.sort_values("mae").iloc[0]
best_by_mape = metrics_df.sort_values("mape").iloc[0]
combined_log_row = metrics_df[metrics_df["dataset_name"].eq("combined")].iloc[0]

if len(raw_vs_log_comparison_df):
    combined_comparison = raw_vs_log_comparison_df[
        raw_vs_log_comparison_df["dataset_label"].eq(DATASET_LABELS["combined"])
    ]
    combined_mae_improvement_pct = (
        float(combined_comparison.iloc[0]["mae_improvement_pct"])
        if len(combined_comparison)
        else np.nan
    )
    combined_mape_improvement_points = (
        float(combined_comparison.iloc[0]["mape_improvement_points"])
        if len(combined_comparison)
        else np.nan
    )
    comparison_status = "raw_baseline_comparison_available"
else:
    combined_mae_improvement_pct = np.nan
    combined_mape_improvement_points = np.nan
    comparison_status = "raw_baseline_comparison_not_available"

modeling_decision = {
    "best_experiment_id_by_mae": best_by_mae["experiment"],
    "best_experiment_name_by_mae": best_by_mae["experiment_name"],
    "best_dataset_name_by_mae": best_by_mae["dataset_label"],
    "best_mae": float(best_by_mae["mae"]),
    "best_mape": float(best_by_mae["mape"]),
    "best_r2": float(best_by_mae["r2"]),
    "best_experiment_id_by_mape": best_by_mape["experiment"],
    "best_experiment_name_by_mape": best_by_mape["experiment_name"],
    "combined_log_mae": float(combined_log_row["mae"]),
    "combined_log_mape": float(combined_log_row["mape"]),
    "combined_log_r2": float(combined_log_row["r2"]),
    "combined_log_underprediction_rate": float(combined_log_row["underprediction_rate"]),
    "comparison_status": comparison_status,
    "combined_mae_improvement_pct_vs_raw": combined_mae_improvement_pct,
    "combined_mape_improvement_points_vs_raw": combined_mape_improvement_points,
    "recommended_next_step": (
        "Use this log-price run as the second baseline checkpoint. If it reduces "
        "high-price underprediction or MAPE without damaging current-market live "
        "segments, move next to gradient boosting on the same log target."
    ),
    "decision_warning": (
        "Do not promote the log-price model from overall MAE alone. Review raw-vs-log "
        "comparison, source drift, rare brand-model error, and price-tail signed error."
    ),
}

modeling_decision_df = pd.DataFrame([modeling_decision])
modeling_decision_df

# %% [markdown]
# ## 11. Save Modeling Outputs

# %%
metrics_df.to_csv(OUTPUT_ROOT / "modeling_experiment_metrics.csv", index=False)
predictions_df.to_csv(OUTPUT_ROOT / "baseline_predictions.csv", index=False)
predictions_df.to_csv(OUTPUT_ROOT / "log_price_predictions.csv", index=False)
segment_metrics_df.to_csv(OUTPUT_ROOT / "segment_metrics.csv", index=False)
key_segment_view.to_csv(OUTPUT_ROOT / "key_segment_metrics.csv", index=False)
price_tail_metrics_df.to_csv(OUTPUT_ROOT / "price_tail_metrics_min_rows_1.csv", index=False)
underprediction_diagnostics_df.to_csv(OUTPUT_ROOT / "underprediction_diagnostics.csv", index=False)
feature_metadata_df.to_csv(OUTPUT_ROOT / "feature_metadata.csv", index=False)
modeling_decision_df.to_csv(OUTPUT_ROOT / "modeling_decision_summary.csv", index=False)

if len(raw_vs_log_comparison_df):
    raw_vs_log_comparison_df.to_csv(
        OUTPUT_ROOT / "raw_vs_log_price_comparison.csv", index=False
    )

if len(raw_price_tail_metrics_df):
    raw_price_tail_metrics_df.to_csv(
        OUTPUT_ROOT / "raw_price_tail_metrics_min_rows_1.csv", index=False
    )

if len(raw_vs_log_price_tail_comparison_df):
    raw_vs_log_price_tail_comparison_df.to_csv(
        OUTPUT_ROOT / "raw_vs_log_price_tail_comparison.csv", index=False
    )

with (OUTPUT_ROOT / "feature_plan.json").open("w", encoding="utf-8") as f:
    json.dump(feature_plan, f, indent=2)

print(f"Saved modeling outputs to: {OUTPUT_ROOT}")
print(f"Saved model artifacts to: {MODEL_DIR}")
print(f"Saved figures to: {FIGURE_DIR}")

# %% [markdown]
# ## 12. Final Baseline Statement
#
# Log-price baseline modeling is complete when this notebook runs end to end and
# the raw-vs-log comparison plus segment diagnostics are reviewed. The next phase
# should keep the same three-model structure and test a stronger log-target
# gradient boosting model with source-aware and price-tail reporting.
