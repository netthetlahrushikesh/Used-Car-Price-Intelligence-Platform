"""Complete modeling story notebook for the Used Car Price Intelligence Platform.

This notebook is written in Jupyter percent-cell format so it can be reviewed
cleanly in GitHub and converted to `.ipynb` for Kaggle or Jupyter.
"""

# %% [markdown]
# # Used Car Price Intelligence Platform: Complete Modeling Story
#
# This is the main GitHub-facing modeling notebook.
#
# The detailed experiment notebooks already reproduce each training stage. This
# notebook is designed for readers: it loads the real modeling datasets, shows
# why the modeling problem is difficult, compares every model checkpoint, reviews
# segment weaknesses, and documents the final validation decision.
#
# The story is:
#
# 1. Raw Random Forest established the first serious baseline.
# 2. Log-price Random Forest tested whether relative error improved.
# 3. Premium-weighted gradient boosting improved high-price behavior.
# 4. Target-encoded native HGB produced the strongest overall model.
# 5. Repeated-split validation showed the model is a strong 10%-class candidate,
#    not a guaranteed sub-10% model on every split.

# %% [markdown]
# ## 0. Notebook Contract
#
# This notebook:
#
# - loads the final trusted modeling datasets
# - keeps live, external, and combined datasets conceptually separated
# - trains the selected final candidate once on a reproducible holdout split
# - uses official metrics produced by the detailed modeling notebooks for the
#   earlier checkpoints and repeated-split validation
# - creates GitHub-friendly comparison tables and visuals
# - documents source drift, rare-category risk, and premium-tail limitations
#
# This notebook intentionally does not retrain every earlier model. Full
# experiment retraining belongs to the stage-specific notebooks:
#
# - `used_car_price_intelligence_baseline_modeling.ipynb`
# - `used_car_price_intelligence_log_price_modeling.ipynb`
# - `used_car_price_intelligence_gradient_boosting_modeling.ipynb`
# - `used_car_price_intelligence_10_percent_target_modeling.ipynb`
# - `used_car_price_intelligence_model_stability_validation.ipynb`

# %%
from pathlib import Path
import json
import warnings

import matplotlib

try:
    get_ipython
except NameError:
    matplotlib.use("Agg")

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
pd.set_option("display.max_columns", 160)
pd.set_option("display.float_format", lambda value: f"{value:,.2f}")

TARGET = "listed_price_inr"
TARGET_TRANSFORM = "log1p"
RUN_FINAL_MODEL_TRAINING = True
RUN_OPTIONAL_RETRAINING = False
RANDOM_STATE = 42
TEST_SIZE = 0.20
TARGET_ENCODING_SMOOTHING = 10
TARGET_ENCODING_SPLITS = 5
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

DATASET_LABELS = {
    "live": "Live Trusted Market Snapshot",
    "external_true_value": "External True Value Historical Dataset",
    "combined": "Combined Trusted Modeling Dataset",
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

if Path("/kaggle/working").exists():
    OUTPUT_ROOT = Path("/kaggle/working/used_car_price_intelligence_complete_modeling_story")
else:
    OUTPUT_ROOT = Path("notebooks") / "outputs" / "used_car_price_intelligence_complete_modeling_story"

FIGURE_DIR = OUTPUT_ROOT / "figures"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

# %% [markdown]
# ## 1. Load Trusted Modeling Datasets

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


def resolve_dataset_paths():
    kaggle_files = {
        "live": find_uploaded_csv("live_trusted_market_snapshot_3496.csv"),
        "external_true_value": find_uploaded_csv("external_true_value_historical_dataset_5614.csv"),
        "combined": find_uploaded_csv("combined_trusted_modeling_dataset_9110.csv"),
    }
    if all(kaggle_files.values()):
        return kaggle_files, "kaggle_input"

    repo_root_candidates = [Path.cwd(), Path.cwd().parent]
    upload_roots = [
        root / "kaggle_upload" / "used-car-price-intelligence-trusted-modeling-datasets"
        for root in repo_root_candidates
    ]

    return {
        "live": first_existing_path(
            [root / "live_trusted_market_snapshot_3496.csv" for root in upload_roots]
        ),
        "external_true_value": first_existing_path(
            [root / "external_true_value_historical_dataset_5614.csv" for root in upload_roots]
        ),
        "combined": first_existing_path(
            [root / "combined_trusted_modeling_dataset_9110.csv" for root in upload_roots]
        ),
    }, "local_project"


DATASETS, RUN_CONTEXT = resolve_dataset_paths()

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

dataset_shape_df = pd.DataFrame(
    [
        {"dataset": DATASET_LABELS[name], "rows": len(df), "columns": df.shape[1]}
        for name, df in datasets.items()
    ]
)
dataset_shape_df

# %% [markdown]
# ## 2. Source And Dataset Drift
#
# The external dataset is cleaner and easier, but older and narrower. The live
# dataset is newer, broader, and more expensive. This drift is why the combined
# model must keep lineage features and segment metrics.

# %%
def source_profile(df, label_col):
    rows = []
    for label, group in df.groupby(label_col, dropna=False):
        rows.append(
            {
                "segment": label,
                "rows": len(group),
                "median_price": group[TARGET].median(),
                "mean_price": group[TARGET].mean(),
                "median_km": group["km_driven"].median(),
                "median_model_year": group["model_year"].median(),
                "unique_cities": group["city"].nunique(),
                "unique_brand_models": group["brand_model"].nunique(),
            }
        )
    return pd.DataFrame(rows).sort_values("rows", ascending=False)


combined_for_profile = combined.copy()
combined_for_profile["dataset_origin_display"] = (
    combined_for_profile["dataset_origin"]
    .map(DATASET_ORIGIN_LABELS)
    .fillna(combined_for_profile["dataset_origin"])
)
combined_for_profile["source_label"] = (
    combined_for_profile["source"].map(SOURCE_LABELS).fillna(combined_for_profile["source"])
)

dataset_origin_profile_df = source_profile(combined_for_profile, "dataset_origin_display")
source_profile_df = source_profile(combined_for_profile, "source_label")

dataset_origin_profile_df

# %%
source_profile_df

# %%
plt.figure(figsize=(8, 4))
sns.barplot(
    data=dataset_origin_profile_df,
    x="median_price",
    y="segment",
    color="#356f8c",
)
plt.title("Median Listed Price By Dataset Origin")
plt.xlabel("Median Listed Price INR")
plt.ylabel("")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "median_price_by_dataset_origin.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 3. Modeling Roadmap

# %%
modeling_roadmap_df = pd.DataFrame(
    [
        {
            "stage": 1,
            "model": "Raw-Price Random Forest",
            "purpose": "Simple supervised baseline.",
            "main_learning": "Combined model started at 13.66% MAPE.",
        },
        {
            "stage": 2,
            "model": "Log-Price Random Forest",
            "purpose": "Test target transformation.",
            "main_learning": "MAPE improved slightly, but high-price tail stayed weak.",
        },
        {
            "stage": 3,
            "model": "Premium-Weighted Log-Gradient Boosting",
            "purpose": "Improve nonlinear and premium-vehicle behavior.",
            "main_learning": "Improved combined MAPE to 11.86% and remained better for high-price tail.",
        },
        {
            "stage": 4,
            "model": "Target-Encoded Native HGB",
            "purpose": "Use leakage-controlled market signal from high-cardinality fields.",
            "main_learning": "Reached the best primary combined checkpoint at 9.88% MAPE.",
        },
        {
            "stage": 5,
            "model": "Repeated-Split Validation",
            "purpose": "Check if the 9.88% result is stable.",
            "main_learning": "Seven-split mean MAPE was 10.33%; strong, but not guaranteed sub-10%.",
        },
    ]
)
modeling_roadmap_df

# %% [markdown]
# ## 4. Combined Dataset Model Results

# %%
combined_model_results_df = pd.DataFrame(
    [
        {
            "model": "Raw-Price Random Forest",
            "dataset": "Combined Trusted Modeling Dataset",
            "mae": 60_826,
            "mape": 13.66,
            "r2": 0.857,
            "role": "first serious baseline",
        },
        {
            "model": "Log-Price Random Forest",
            "dataset": "Combined Trusted Modeling Dataset",
            "mae": 61_943,
            "mape": 13.48,
            "r2": 0.847,
            "role": "target-transform benchmark",
        },
        {
            "model": "Premium-Weighted Log-Gradient Boosting",
            "dataset": "Combined Trusted Modeling Dataset",
            "mae": 56_753,
            "mape": 11.86,
            "r2": 0.876,
            "role": "premium-tail improvement track",
        },
        {
            "model": "Target-Encoded Native HGB",
            "dataset": "Combined Trusted Modeling Dataset",
            "mae": 47_389,
            "mape": 9.88,
            "r2": 0.897,
            "role": "main candidate",
        },
    ]
)

combined_model_results_df.sort_values("mape")

# %%
plt.figure(figsize=(9, 5))
sns.barplot(
    data=combined_model_results_df.sort_values("mape"),
    x="mape",
    y="model",
    color="#356f8c",
)
plt.axvline(10, color="#b33a3a", linestyle="--", linewidth=1)
plt.title("Combined Dataset MAPE By Model Stage")
plt.xlabel("MAPE %")
plt.ylabel("")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "combined_mape_by_model_stage.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 5. Single Final Model Training Run
#
# The selected model is not just reported as a static metric. This section
# trains the final candidate once using the same design as the detailed target
# modeling notebook:
#
# - combined trusted dataset only
# - log-price target
# - train-only, out-of-fold target encoding for high-cardinality market fields
# - native categorical `HistGradientBoostingRegressor`
# - fixed 80/20 stratified price split with `random_state=42`
#
# The full seven-split validation remains a separate evidence layer later in
# this notebook because it is slower and better suited to the detailed
# validation notebook.

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


def normalized_text(series):
    return series.fillna("unknown").astype(str).str.strip().str.lower()


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


def add_final_model_features(df):
    out = df.copy()

    brand_norm = normalized_text(out["brand"])
    source_norm = normalized_text(out["source"])
    city_norm = normalized_text(out["city"])
    fuel_norm = normalized_text(out["fuel_type"])
    transmission_norm = normalized_text(out["transmission"])

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
        counts = out[col].fillna("unknown").astype(str).value_counts()
        out[f"{col}_frequency"] = out[col].fillna("unknown").astype(str).map(counts).astype(float)

    brand_model_counts = out["brand_model"].fillna("unknown").astype(str).value_counts()
    rare_brand_models = set(brand_model_counts[brand_model_counts < RARE_BRAND_MODEL_MIN_ROWS].index)
    out["source_label"] = out["source"].map(SOURCE_LABELS).fillna(out["source"])
    out["dataset_origin_display"] = out["dataset_origin"].map(DATASET_ORIGIN_LABELS).fillna(
        out["dataset_origin"]
    )
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


def feature_columns_for_final_model(df):
    numeric = available_columns(df, NUMERIC_FEATURE_CANDIDATES)
    categorical = available_columns(df, CATEGORICAL_FEATURE_CANDIDATES)
    target_encoded = [f"te_{col}" for col in available_columns(df, TARGET_ENCODING_COLUMNS)]
    numeric = dedupe_preserve_order(numeric + target_encoded)
    categorical = dedupe_preserve_order(categorical)
    return numeric, categorical, dedupe_preserve_order(numeric + categorical)


def smoothed_target_mapping(series, y_log, smoothing):
    global_mean = float(y_log.mean())
    tmp = pd.DataFrame({"category": series.fillna("unknown").astype(str), "target": y_log})
    stats = tmp.groupby("category")["target"].agg(["mean", "count"])
    encoded = (stats["count"] * stats["mean"] + smoothing * global_mean) / (
        stats["count"] + smoothing
    )
    return encoded, global_mean


def add_out_of_fold_target_encoding(train_rows, test_rows, columns, seed=RANDOM_STATE):
    train_encoded = train_rows.copy()
    test_encoded = test_rows.copy()
    kfold = KFold(n_splits=TARGET_ENCODING_SPLITS, shuffle=True, random_state=seed)
    encoding_summary = []

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
            np.log1p(train_encoded[TARGET]),
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
        encoding_summary.append(
            {
                "column": col,
                "encoded_feature": f"te_{col}",
                "train_categories": int(full_mapping.shape[0]),
                "global_log_price_mean": full_global_mean,
            }
        )

    return train_encoded, test_encoded, pd.DataFrame(encoding_summary)


def prepare_native_hgb_features(train_rows, test_rows, numeric_features, categorical_features):
    train_x = train_rows[numeric_features + categorical_features].copy()
    test_x = test_rows[numeric_features + categorical_features].copy()

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

    return train_x, test_x


def make_price_stratification(y, max_bins=10):
    labels = pd.qcut(y, q=max_bins, duplicates="drop")
    counts = labels.value_counts()
    if len(counts) < 2 or counts.min() < 2:
        return None
    return labels


def regression_metrics(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    signed_error = y_pred - y_true
    abs_error = np.abs(y_true - y_pred)
    pct_error = abs_error / np.maximum(np.abs(y_true), 1) * 100
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": float(pct_error.mean()),
        "median_absolute_error": float(np.median(abs_error)),
        "mean_signed_error": float(np.mean(signed_error)),
        "median_signed_error": float(np.median(signed_error)),
        "underprediction_rate": float((signed_error < 0).mean() * 100),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else np.nan,
    }


def build_final_model(seed=RANDOM_STATE):
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


def train_single_final_model(df):
    model_df = add_final_model_features(df).dropna(subset=[TARGET]).copy()
    stratify_labels = make_price_stratification(model_df[TARGET])
    try:
        train_rows, test_rows = train_test_split(
            model_df,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=stratify_labels,
        )
    except ValueError:
        train_rows, test_rows = train_test_split(
            model_df,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=None,
        )

    target_encoding_cols = available_columns(train_rows, TARGET_ENCODING_COLUMNS)
    train_encoded, test_encoded, target_encoding_summary_df = add_out_of_fold_target_encoding(
        train_rows,
        test_rows,
        target_encoding_cols,
        seed=RANDOM_STATE,
    )

    numeric_features, categorical_features, feature_cols = feature_columns_for_final_model(train_encoded)
    train_x, test_x = prepare_native_hgb_features(
        train_encoded,
        test_encoded,
        numeric_features,
        categorical_features,
    )

    model = build_final_model(seed=RANDOM_STATE)
    y_train = train_encoded[TARGET]
    y_test = test_encoded[TARGET]
    model.fit(train_x, np.log1p(y_train))
    log_predictions = model.predict(test_x)
    predictions = np.clip(np.expm1(log_predictions), 0, None)

    metrics = regression_metrics(y_test, predictions)
    metrics_row = {
        "model": "Combined Trusted Lineage Target-Encoded Native HGB",
        "dataset": "Combined Trusted Modeling Dataset",
        "target": TARGET,
        "target_transform": TARGET_TRANSFORM,
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "train_rows": int(len(train_rows)),
        "test_rows": int(len(test_rows)),
        "feature_count": int(len(feature_cols)),
        "numeric_feature_count": int(len(numeric_features)),
        "categorical_feature_count": int(len(categorical_features)),
        "target_encoded_feature_count": int(len(target_encoding_cols)),
        "hgb_iterations": int(model.n_iter_),
        **metrics,
    }

    predictions_df = test_encoded.copy()
    predictions_df["actual_price"] = y_test.values
    predictions_df["predicted_price"] = predictions
    predictions_df["actual_log_price"] = np.log1p(y_test.values)
    predictions_df["predicted_log_price"] = log_predictions
    predictions_df["absolute_error"] = np.abs(predictions_df["actual_price"] - predictions_df["predicted_price"])
    predictions_df["absolute_percentage_error"] = (
        predictions_df["absolute_error"] / np.maximum(np.abs(predictions_df["actual_price"]), 1) * 100
    )
    predictions_df["signed_error"] = predictions_df["predicted_price"] - predictions_df["actual_price"]
    predictions_df["is_underprediction"] = predictions_df["signed_error"] < 0

    feature_metadata_df = pd.DataFrame(
        [
            {
                "model": metrics_row["model"],
                "feature_count": len(feature_cols),
                "numeric_features": ", ".join(numeric_features),
                "categorical_features": ", ".join(categorical_features),
                "target_encoding_columns": ", ".join(target_encoding_cols),
                "target_encoding_smoothing": TARGET_ENCODING_SMOOTHING,
                "target_encoding_splits": TARGET_ENCODING_SPLITS,
                "high_cardinality_top_n": HIGH_CARDINALITY_TOP_N,
            }
        ]
    )

    return (
        pd.DataFrame([metrics_row]),
        predictions_df,
        feature_metadata_df,
        target_encoding_summary_df,
    )


if RUN_FINAL_MODEL_TRAINING:
    (
        final_model_training_metrics_df,
        final_model_predictions_df,
        final_model_feature_metadata_df,
        final_model_target_encoding_summary_df,
    ) = train_single_final_model(combined)
else:
    final_model_training_metrics_df = pd.DataFrame()
    final_model_predictions_df = pd.DataFrame()
    final_model_feature_metadata_df = pd.DataFrame()
    final_model_target_encoding_summary_df = pd.DataFrame()

final_model_training_metrics_df[
    [
        "model",
        "train_rows",
        "test_rows",
        "mae",
        "rmse",
        "mape",
        "r2",
        "underprediction_rate",
        "hgb_iterations",
    ]
]

# %%
official_final_checkpoint = combined_model_results_df[
    combined_model_results_df["model"].eq("Target-Encoded Native HGB")
].iloc[0]

if len(final_model_training_metrics_df):
    notebook_final_metrics = final_model_training_metrics_df.iloc[0]
    final_model_reproduction_check_df = pd.DataFrame(
        [
            {
                "metric": "MAE",
                "notebook_run": notebook_final_metrics["mae"],
                "official_checkpoint": official_final_checkpoint["mae"],
                "difference": notebook_final_metrics["mae"] - official_final_checkpoint["mae"],
            },
            {
                "metric": "MAPE",
                "notebook_run": notebook_final_metrics["mape"],
                "official_checkpoint": official_final_checkpoint["mape"],
                "difference": notebook_final_metrics["mape"] - official_final_checkpoint["mape"],
            },
            {
                "metric": "R2",
                "notebook_run": notebook_final_metrics["r2"],
                "official_checkpoint": official_final_checkpoint["r2"],
                "difference": notebook_final_metrics["r2"] - official_final_checkpoint["r2"],
            },
        ]
    )
else:
    final_model_reproduction_check_df = pd.DataFrame()

final_model_reproduction_check_df

# %%
if len(final_model_predictions_df):
    plt.figure(figsize=(6, 6))
    sns.scatterplot(
        data=final_model_predictions_df.sample(
            min(1_500, len(final_model_predictions_df)),
            random_state=RANDOM_STATE,
        ),
        x="actual_price",
        y="predicted_price",
        hue="dataset_origin_display",
        alpha=0.55,
        linewidth=0,
    )
    price_limit = max(
        final_model_predictions_df["actual_price"].quantile(0.995),
        final_model_predictions_df["predicted_price"].quantile(0.995),
    )
    plt.plot([0, price_limit], [0, price_limit], color="#b33a3a", linestyle="--", linewidth=1)
    plt.xlim(0, price_limit)
    plt.ylim(0, price_limit)
    plt.title("Final Model Holdout: Predicted vs Actual Price")
    plt.xlabel("Actual Listed Price INR")
    plt.ylabel("Predicted Listed Price INR")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "final_model_predicted_vs_actual.png", dpi=160, bbox_inches="tight")
    plt.show()

# %% [markdown]
# ## 6. Improvement Against Earlier Models

# %%
target_model_improvement_df = pd.DataFrame(
    [
        {
            "dataset": "Combined Trusted Modeling Dataset",
            "baseline": "Raw-Price Random Forest",
            "baseline_mape": 13.66,
            "target_encoded_mape": 9.88,
            "mape_improvement_points": 3.77,
            "baseline_mae": 60_826,
            "target_encoded_mae": 47_389,
        },
        {
            "dataset": "Combined Trusted Modeling Dataset",
            "baseline": "Log-Price Random Forest",
            "baseline_mape": 13.48,
            "target_encoded_mape": 9.88,
            "mape_improvement_points": 3.59,
            "baseline_mae": 61_943,
            "target_encoded_mae": 47_389,
        },
        {
            "dataset": "Combined Trusted Modeling Dataset",
            "baseline": "Premium-Weighted Log-Gradient Boosting",
            "baseline_mape": 11.86,
            "target_encoded_mape": 9.88,
            "mape_improvement_points": 1.98,
            "baseline_mae": 56_753,
            "target_encoded_mae": 47_389,
        },
        {
            "dataset": "Live Trusted Market Snapshot",
            "baseline": "Raw-Price Random Forest",
            "baseline_mape": 16.94,
            "target_encoded_mape": 13.40,
            "mape_improvement_points": 3.54,
            "baseline_mae": 88_512,
            "target_encoded_mae": 73_651,
        },
        {
            "dataset": "External True Value Historical Dataset",
            "baseline": "Raw-Price Random Forest",
            "baseline_mape": 10.81,
            "target_encoded_mape": 8.32,
            "mape_improvement_points": 2.48,
            "baseline_mae": 45_505,
            "target_encoded_mae": 35_773,
        },
    ]
)
target_model_improvement_df

# %% [markdown]
# ## 7. Final Candidate Segment Metrics
#
# The final candidate is strong on common/normal-market rows. It is still weaker
# on rare brand-model groups and live premium-heavy sources.

# %%
final_candidate_segment_metrics_df = pd.DataFrame(
    [
        {
            "segment": "Common brand-model",
            "rows": 1_737,
            "mae": 40_917,
            "mape": 9.39,
            "underprediction_rate": 50.89,
        },
        {
            "segment": "Rare brand-model",
            "rows": 85,
            "mae": 179_635,
            "mape": 19.88,
            "underprediction_rate": 51.76,
        },
        {
            "segment": "Normal price range",
            "rows": 1_819,
            "mae": 45_678,
            "mape": 9.80,
            "underprediction_rate": 50.91,
        },
        {
            "segment": "Spinny Live",
            "rows": 93,
            "mae": 124_530,
            "mape": 12.62,
            "underprediction_rate": 51.61,
        },
        {
            "segment": "Mahindra First Choice Live",
            "rows": 110,
            "mae": 149_896,
            "mape": 16.97,
            "underprediction_rate": 50.91,
        },
        {
            "segment": "True Value Live",
            "rows": 476,
            "mae": 40_579,
            "mape": 12.68,
            "underprediction_rate": 53.78,
        },
        {
            "segment": "External True Value Historical",
            "rows": 1_143,
            "mae": 34_083,
            "mape": 7.81,
            "underprediction_rate": 49.69,
        },
    ]
)
final_candidate_segment_metrics_df.sort_values("mape", ascending=False)

# %%
plt.figure(figsize=(8, 5))
sns.barplot(
    data=final_candidate_segment_metrics_df.sort_values("mape", ascending=False),
    x="mape",
    y="segment",
    color="#4b735f",
)
plt.title("Final Candidate MAPE By Key Segment")
plt.xlabel("MAPE %")
plt.ylabel("")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "final_candidate_mape_by_segment.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 8. Premium-Tail Limitation
#
# The target-encoded model is the best overall model, but it is not the best
# high-price-tail model. This is why premium-tail modeling remains a future
# improvement track instead of being hidden.

# %%
high_price_tail_comparison_df = pd.DataFrame(
    [
        {
            "model": "Premium-Weighted Log-Gradient Boosting",
            "high_tail_mae": 1_330_252,
            "high_tail_mape": 34.82,
        },
        {
            "model": "Raw-Price Random Forest",
            "high_tail_mae": 1_528_035,
            "high_tail_mape": 37.49,
        },
        {
            "model": "Target-Encoded Native HGB",
            "high_tail_mae": 1_612_623,
            "high_tail_mape": 41.51,
        },
        {
            "model": "Log-Price Random Forest",
            "high_tail_mae": 1_820_215,
            "high_tail_mape": 45.90,
        },
    ]
)
high_price_tail_comparison_df

# %% [markdown]
# ## 9. Repeated-Split Stability Validation
#
# The final model achieved 9.88% MAPE on the primary split. Repeated-split
# validation is stricter: it reruns the same candidate across seven train/test
# split seeds.

# %%
stability_metrics_by_seed_df = pd.DataFrame(
    [
        {"seed": 7, "mae": 45_119, "rmse": 82_554, "mape": 10.07, "r2": 0.925, "underprediction_rate": 51.04},
        {"seed": 13, "mae": 48_501, "rmse": 112_605, "mape": 10.73, "r2": 0.882, "underprediction_rate": 52.85},
        {"seed": 21, "mae": 46_280, "rmse": 88_424, "mape": 10.00, "r2": 0.930, "underprediction_rate": 49.23},
        {"seed": 42, "mae": 47_389, "rmse": 104_458, "mape": 9.88, "r2": 0.897, "underprediction_rate": 50.93},
        {"seed": 67, "mae": 48_997, "rmse": 108_933, "mape": 10.48, "r2": 0.897, "underprediction_rate": 49.29},
        {"seed": 101, "mae": 48_309, "rmse": 92_322, "mape": 10.47, "r2": 0.923, "underprediction_rate": 50.16},
        {"seed": 202, "mae": 48_528, "rmse": 115_562, "mape": 10.66, "r2": 0.884, "underprediction_rate": 50.99},
    ]
)
stability_metrics_by_seed_df

# %%
stability_summary_df = pd.DataFrame(
    [
        {"metric": "MAE", "mean": 47_589, "std": 1_418, "min": 45_119, "median": 48_309, "max": 48_997},
        {"metric": "MAPE", "mean": 10.33, "std": 0.34, "min": 9.88, "median": 10.47, "max": 10.73},
        {"metric": "R2", "mean": 0.906, "std": 0.020, "min": 0.882, "median": 0.897, "max": 0.930},
        {
            "metric": "Underprediction rate",
            "mean": 50.64,
            "std": 1.25,
            "min": 49.23,
            "median": 50.93,
            "max": 52.85,
        },
    ]
)
stability_summary_df

# %%
plt.figure(figsize=(8, 4))
sns.lineplot(data=stability_metrics_by_seed_df, x="seed", y="mape", marker="o", color="#356f8c")
plt.axhline(10, color="#b33a3a", linestyle="--", linewidth=1)
plt.title("Repeated-Split MAPE By Validation Seed")
plt.xlabel("Validation Seed")
plt.ylabel("MAPE %")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "repeated_split_mape_by_seed.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 10. Segment Stability

# %%
stability_segment_summary_df = pd.DataFrame(
    [
        {"segment": "Common brand-model", "mean_rows": 1_726, "mean_mae": 41_268, "mean_mape": 9.61, "max_mape": 10.02},
        {"segment": "Rare brand-model", "mean_rows": 96, "mean_mae": 161_094, "mean_mape": 23.19, "max_mape": 30.41},
        {"segment": "Normal price range", "mean_rows": 1_820, "mean_mae": 46_218, "mean_mape": 10.18, "max_mape": 10.44},
        {"segment": "High price tail", "mean_rows": 2, "mean_mae": 1_738_146, "mean_mape": 43.83, "max_mape": 53.74},
        {"segment": "Spinny Live", "mean_rows": 95, "mean_mae": 133_099, "mean_mape": 13.21, "max_mape": 14.73},
        {"segment": "Mahindra First Choice Live", "mean_rows": 115, "mean_mae": 122_944, "mean_mape": 17.96, "max_mape": 24.20},
        {"segment": "True Value Live", "mean_rows": 484, "mean_mae": 43_129, "mean_mape": 13.08, "max_mape": 14.30},
        {
            "segment": "External True Value Historical",
            "mean_rows": 1_128,
            "mean_mae": 34_747,
            "mean_mape": 8.14,
            "max_mape": 8.51,
        },
    ]
)
stability_segment_summary_df.sort_values("mean_mape", ascending=False)

# %% [markdown]
# ## 11. Final Modeling Decision

# %%
notebook_final_model_metrics = (
    final_model_training_metrics_df.iloc[0].to_dict()
    if len(final_model_training_metrics_df)
    else {}
)

final_model_decision = {
    "main_candidate": "Combined Trusted Lineage Target-Encoded Native HGB",
    "primary_split_mae": 47_389,
    "primary_split_mape": 9.88,
    "primary_split_r2": 0.897,
    "notebook_final_model_run_mae": notebook_final_model_metrics.get("mae"),
    "notebook_final_model_run_mape": notebook_final_model_metrics.get("mape"),
    "notebook_final_model_run_r2": notebook_final_model_metrics.get("r2"),
    "seven_split_mean_mae": 47_589,
    "seven_split_mean_mape": 10.33,
    "seven_split_mape_range": "9.88% to 10.73%",
    "seven_split_mean_r2": 0.906,
    "status": "usable_with_warning",
    "recommended_claim": (
        "Trusted-source used-car price model with 10%-class performance: "
        "9.88% MAPE on the primary combined split and 10.33% mean MAPE across "
        "seven repeated validation splits."
    ),
    "warning": (
        "Do not claim guaranteed sub-10% MAPE on every split. Premium and rare "
        "brand-model rows remain the main improvement track."
    ),
}

final_model_decision_df = pd.DataFrame([final_model_decision])
final_model_decision_df

# %% [markdown]
# ## 12. Save Notebook Outputs

# %%
dataset_shape_df.to_csv(OUTPUT_ROOT / "dataset_shape_summary.csv", index=False)
dataset_origin_profile_df.to_csv(OUTPUT_ROOT / "dataset_origin_profile.csv", index=False)
source_profile_df.to_csv(OUTPUT_ROOT / "source_profile.csv", index=False)
combined_model_results_df.to_csv(OUTPUT_ROOT / "combined_model_results.csv", index=False)
final_model_training_metrics_df.to_csv(OUTPUT_ROOT / "final_model_training_metrics.csv", index=False)
final_model_reproduction_check_df.to_csv(OUTPUT_ROOT / "final_model_reproduction_check.csv", index=False)
final_model_feature_metadata_df.to_csv(OUTPUT_ROOT / "final_model_feature_metadata.csv", index=False)
final_model_target_encoding_summary_df.to_csv(
    OUTPUT_ROOT / "final_model_target_encoding_summary.csv",
    index=False,
)
final_model_predictions_df.to_csv(OUTPUT_ROOT / "final_model_holdout_predictions.csv", index=False)
target_model_improvement_df.to_csv(OUTPUT_ROOT / "target_model_improvement.csv", index=False)
final_candidate_segment_metrics_df.to_csv(OUTPUT_ROOT / "final_candidate_segment_metrics.csv", index=False)
high_price_tail_comparison_df.to_csv(OUTPUT_ROOT / "high_price_tail_comparison.csv", index=False)
stability_metrics_by_seed_df.to_csv(OUTPUT_ROOT / "stability_metrics_by_seed.csv", index=False)
stability_summary_df.to_csv(OUTPUT_ROOT / "stability_summary.csv", index=False)
stability_segment_summary_df.to_csv(OUTPUT_ROOT / "stability_segment_summary.csv", index=False)
final_model_decision_df.to_csv(OUTPUT_ROOT / "final_model_decision.csv", index=False)

with (OUTPUT_ROOT / "final_model_decision.json").open("w", encoding="utf-8") as f:
    json.dump(final_model_decision, f, indent=2)

print(f"Saved complete modeling story outputs to: {OUTPUT_ROOT}")
print(f"Saved figures to: {FIGURE_DIR}")

# %% [markdown]
# ## 13. Optional Full Retraining
#
# This notebook already trains the selected final model once. Keep
# `RUN_OPTIONAL_RETRAINING = False` for GitHub/Kaggle reading. Use the
# stage-specific notebooks when you intentionally want to rerun every historical
# experiment, compare all intermediate checkpoints, or regenerate detailed
# diagnostics.

# %%
if RUN_OPTIONAL_RETRAINING:
    raise NotImplementedError(
        "Use the stage-specific modeling notebooks for full experiment retraining. "
        "This notebook trains the final candidate once and summarizes the full evidence trail."
    )

# %% [markdown]
# ## 14. Final Statement
#
# The final model is a strong candidate, not a finished pricing product.
#
# Correct wording:
#
# > Built a trusted-source used-car price intelligence pipeline and trained a
# > 10%-class price model, reaching 9.88% MAPE on the primary combined split and
# > 10.33% mean MAPE across seven repeated validation splits.
#
# Remaining work:
#
# - premium/high-price-tail modeling
# - rare brand-model improvement
# - model interpretation
# - deployment-oriented monitoring and retraining design
