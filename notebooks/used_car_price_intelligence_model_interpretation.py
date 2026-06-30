"""Final model interpretation notebook for the Used Car Price Intelligence Platform.

This notebook is written in Jupyter percent-cell format so it can be reviewed
cleanly in GitHub and converted to `.ipynb` for Kaggle or Jupyter.
"""

# %% [markdown]
# # Used Car Price Intelligence Platform: Final Model Interpretation
#
# This notebook answers a different question from the modeling story notebook:
#
# > The model works, but why should a reviewer trust it?
#
# It retrains the selected final candidate once, then reviews feature importance,
# segment error, price-band behavior, and concrete prediction examples. The goal
# is not more tuning. The goal is model trust, transparency, and honest
# limitations.
#
# Final candidate:
#
# - `Combined Trusted Lineage Target-Encoded Native HGB`
# - target: `listed_price_inr`
# - target transform: `log1p`
# - primary checkpoint: `9.88%` MAPE
# - repeated-split mean: `10.33%` MAPE

# %% [markdown]
# ## 0. Notebook Contract
#
# This notebook:
#
# - loads the final combined trusted modeling dataset
# - retrains the selected final model on the same reproducible holdout split
# - uses leakage-controlled target encoding inside the training split only
# - computes permutation importance on the holdout set
# - reviews model reliability by source, dataset origin, price band, age band,
#   fuel type, transmission, and rare-category group
# - shows best and worst holdout examples for human review
#
# Important interpretation rule:
#
# Feature importance here is predictive importance, not causal explanation.
# For example, `brand_model` can be highly predictive because the market prices
# similar vehicles similarly. That does not mean changing only the text value
# would cause the price to change.

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
RANDOM_STATE = 42
TEST_SIZE = 0.20
TARGET_ENCODING_SMOOTHING = 10
TARGET_ENCODING_SPLITS = 5
HIGH_CARDINALITY_TOP_N = 180
RARE_BRAND_MODEL_MIN_ROWS = 10
PERMUTATION_SAMPLE_ROWS = 1_200
PERMUTATION_REPEATS = 3

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
    OUTPUT_ROOT = Path("/kaggle/working/used_car_price_intelligence_model_interpretation")
else:
    OUTPUT_ROOT = Path("notebooks") / "outputs" / "used_car_price_intelligence_model_interpretation"

FIGURE_DIR = OUTPUT_ROOT / "figures"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

# %% [markdown]
# ## 1. Load Dataset

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


def resolve_combined_dataset_path():
    kaggle_path = find_uploaded_csv("combined_trusted_modeling_dataset_9110.csv")
    if kaggle_path is not None:
        return kaggle_path, "kaggle_input"

    repo_root_candidates = [Path.cwd(), Path.cwd().parent]
    local_candidates = [
        root
        / "kaggle_upload"
        / "used-car-price-intelligence-trusted-modeling-datasets"
        / "combined_trusted_modeling_dataset_9110.csv"
        for root in repo_root_candidates
    ]
    return first_existing_path(local_candidates), "local_project"


COMBINED_DATASET_PATH, RUN_CONTEXT = resolve_combined_dataset_path()
raw_combined = pd.read_csv(COMBINED_DATASET_PATH)

print("Run context:", RUN_CONTEXT)
print("Dataset path:", COMBINED_DATASET_PATH)
print("Output root:", OUTPUT_ROOT)
print("Rows x columns:", raw_combined.shape)

raw_combined.head()

# %% [markdown]
# ## 2. Feature Engineering

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
    out["age_band"] = pd.cut(
        age,
        bins=[-1, 3, 6, 10, 30],
        labels=["0_3_years", "4_6_years", "7_10_years", "11_plus_years"],
    ).astype("object").fillna("unknown")
    out["price_band"] = pd.cut(
        out[TARGET],
        bins=[0, 250_000, 500_000, 750_000, 1_000_000, 2_000_000, np.inf],
        labels=["0_2.5L", "2.5L_5L", "5L_7.5L", "7.5L_10L", "10L_20L", "20L_plus"],
    ).astype("object").fillna("unknown")

    return out


def feature_columns_for_final_model(df):
    numeric = available_columns(df, NUMERIC_FEATURE_CANDIDATES)
    categorical = available_columns(df, CATEGORICAL_FEATURE_CANDIDATES)
    target_encoded = [f"te_{col}" for col in available_columns(df, TARGET_ENCODING_COLUMNS)]
    numeric = dedupe_preserve_order(numeric + target_encoded)
    categorical = dedupe_preserve_order(categorical)
    return numeric, categorical, dedupe_preserve_order(numeric + categorical)


combined = add_final_model_features(raw_combined)
combined.shape

# %% [markdown]
# ## 3. Train Final Candidate

# %%
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


def train_final_model(df):
    model_df = df.dropna(subset=[TARGET]).copy()
    stratify_labels = make_price_stratification(model_df[TARGET])
    train_rows, test_rows = train_test_split(
        model_df,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=stratify_labels,
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

    y_train = train_encoded[TARGET]
    y_test = test_encoded[TARGET]
    model = build_final_model(seed=RANDOM_STATE)
    model.fit(train_x, np.log1p(y_train))
    log_predictions = model.predict(test_x)
    predictions = np.clip(np.expm1(log_predictions), 0, None)

    predictions_df = test_encoded.copy()
    predictions_df["actual_price"] = y_test.values
    predictions_df["predicted_price"] = predictions
    predictions_df["signed_error"] = predictions_df["predicted_price"] - predictions_df["actual_price"]
    predictions_df["absolute_error"] = predictions_df["signed_error"].abs()
    predictions_df["absolute_percentage_error"] = (
        predictions_df["absolute_error"] / np.maximum(predictions_df["actual_price"].abs(), 1) * 100
    )
    predictions_df["is_underprediction"] = predictions_df["signed_error"] < 0

    metrics_row = {
        "model": "Combined Trusted Lineage Target-Encoded Native HGB",
        "target": TARGET,
        "target_transform": TARGET_TRANSFORM,
        "random_state": RANDOM_STATE,
        "train_rows": int(len(train_rows)),
        "test_rows": int(len(test_rows)),
        "feature_count": int(len(feature_cols)),
        "numeric_feature_count": int(len(numeric_features)),
        "categorical_feature_count": int(len(categorical_features)),
        "target_encoded_feature_count": int(len(target_encoding_cols)),
        "hgb_iterations": int(model.n_iter_),
        **regression_metrics(y_test, predictions),
    }

    feature_metadata_df = pd.DataFrame(
        [
            {
                "feature": feature,
                "feature_type": (
                    "target_encoded"
                    if feature.startswith("te_")
                    else "numeric"
                    if feature in numeric_features
                    else "categorical"
                ),
            }
            for feature in feature_cols
        ]
    )

    return {
        "model": model,
        "train_rows": train_encoded,
        "test_rows": test_encoded,
        "train_x": train_x,
        "test_x": test_x,
        "y_test": y_test,
        "predictions": predictions_df,
        "metrics": pd.DataFrame([metrics_row]),
        "features": feature_metadata_df,
        "target_encoding_summary": target_encoding_summary_df,
    }


final_run = train_final_model(combined)
final_model_metrics_df = final_run["metrics"]
final_model_metrics_df

# %% [markdown]
# ## 4. Holdout Prediction Shape

# %%
predictions_df = final_run["predictions"]

plt.figure(figsize=(6, 6))
plot_sample = predictions_df.sample(min(1_500, len(predictions_df)), random_state=RANDOM_STATE)
sns.scatterplot(
    data=plot_sample,
    x="actual_price",
    y="predicted_price",
    hue="dataset_origin_display",
    alpha=0.55,
    linewidth=0,
)
price_limit = max(
    predictions_df["actual_price"].quantile(0.995),
    predictions_df["predicted_price"].quantile(0.995),
)
plt.plot([0, price_limit], [0, price_limit], color="#b33a3a", linestyle="--", linewidth=1)
plt.xlim(0, price_limit)
plt.ylim(0, price_limit)
plt.title("Final Model Holdout: Predicted vs Actual Price")
plt.xlabel("Actual Listed Price INR")
plt.ylabel("Predicted Listed Price INR")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "holdout_predicted_vs_actual.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 5. Permutation Importance
#
# This checks how much holdout MAPE gets worse when one feature is shuffled.
# A larger MAPE increase means the model depends more on that feature.

# %%
def predict_price(model, x):
    return np.clip(np.expm1(model.predict(x)), 0, None)


def mape_score(y_true, y_pred):
    return float((np.abs(np.asarray(y_true) - np.asarray(y_pred)) / np.maximum(np.abs(y_true), 1) * 100).mean())


def permute_feature_column(frame, column, seed):
    rng = np.random.default_rng(seed)
    permuted = frame[column].to_numpy().copy()
    rng.shuffle(permuted)
    result = frame.copy()
    if str(frame[column].dtype) == "category":
        result[column] = pd.Categorical(permuted, categories=frame[column].cat.categories)
    else:
        result[column] = permuted
    return result


def manual_permutation_importance(model, x, y, features, repeats=PERMUTATION_REPEATS):
    if len(x) > PERMUTATION_SAMPLE_ROWS:
        sample_index = x.sample(PERMUTATION_SAMPLE_ROWS, random_state=RANDOM_STATE).index
        base_x = x.loc[sample_index].copy()
        base_y = y.loc[sample_index].copy()
    else:
        base_x = x.copy()
        base_y = y.copy()

    baseline_mape = mape_score(base_y, predict_price(model, base_x))
    rows = []
    for feature in features:
        repeat_scores = []
        for repeat in range(repeats):
            permuted_x = permute_feature_column(
                base_x,
                feature,
                seed=RANDOM_STATE + repeat + (abs(hash(feature)) % 10_000),
            )
            permuted_mape = mape_score(base_y, predict_price(model, permuted_x))
            repeat_scores.append(permuted_mape)
        rows.append(
            {
                "feature": feature,
                "baseline_mape": baseline_mape,
                "permuted_mape_mean": float(np.mean(repeat_scores)),
                "permuted_mape_std": float(np.std(repeat_scores, ddof=0)),
                "mape_increase": float(np.mean(repeat_scores) - baseline_mape),
            }
        )
    return pd.DataFrame(rows).sort_values("mape_increase", ascending=False)


permutation_importance_df = manual_permutation_importance(
    final_run["model"],
    final_run["test_x"],
    final_run["y_test"],
    final_run["features"]["feature"].tolist(),
)

permutation_importance_with_type_df = permutation_importance_df.merge(
    final_run["features"],
    on="feature",
    how="left",
)
permutation_importance_with_type_df.head(20)

# %%
plt.figure(figsize=(9, 6))
top_importance = permutation_importance_with_type_df.head(18).sort_values("mape_increase")
sns.barplot(
    data=top_importance,
    x="mape_increase",
    y="feature",
    hue="feature_type",
    dodge=False,
)
plt.title("Final Model: Top Permutation Importance Features")
plt.xlabel("Holdout MAPE Increase After Shuffling")
plt.ylabel("")
plt.legend(title="Feature type", loc="lower right")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "top_permutation_importance.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 6. Segment Error Review

# %%
def segment_metrics(predictions, segment_col, min_rows=20):
    rows = []
    for segment_value, group in predictions.groupby(segment_col, dropna=False):
        if len(group) < min_rows:
            continue
        metrics = regression_metrics(group["actual_price"], group["predicted_price"])
        rows.append(
            {
                "segment_column": segment_col,
                "segment_value": segment_value,
                "rows": len(group),
                "median_actual_price": float(group["actual_price"].median()),
                **metrics,
            }
        )
    return pd.DataFrame(rows).sort_values(["mape", "mae"], ascending=False)


segment_columns = [
    "dataset_origin_display",
    "source_label",
    "price_band",
    "price_tail_group",
    "brand_model_eval_group",
    "fuel_type",
    "transmission",
    "age_band",
    "city",
]

segment_metric_tables = []
for segment_col in segment_columns:
    table = segment_metrics(predictions_df, segment_col, min_rows=20)
    if len(table):
        segment_metric_tables.append(table)

segment_metrics_df = pd.concat(segment_metric_tables, ignore_index=True)
segment_metrics_df.head(30)

# %%
key_segment_view_df = segment_metrics_df[
    segment_metrics_df["segment_column"].isin(
        [
            "dataset_origin_display",
            "source_label",
            "price_band",
            "price_tail_group",
            "brand_model_eval_group",
        ]
    )
].sort_values(["segment_column", "mape"], ascending=[True, False])

key_segment_view_df

# %%
plot_segments = key_segment_view_df[
    key_segment_view_df["segment_column"].isin(["source_label", "price_band", "brand_model_eval_group"])
].copy()
plot_segments["segment"] = plot_segments["segment_column"] + ": " + plot_segments["segment_value"].astype(str)

plt.figure(figsize=(9, 7))
sns.barplot(
    data=plot_segments.sort_values("mape", ascending=False),
    x="mape",
    y="segment",
    color="#4b735f",
)
plt.axvline(final_model_metrics_df.loc[0, "mape"], color="#b33a3a", linestyle="--", linewidth=1)
plt.title("Final Model MAPE By Key Segment")
plt.xlabel("MAPE %")
plt.ylabel("")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "mape_by_key_segment.png", dpi=160, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 7. Error Distribution

# %%
plt.figure(figsize=(9, 4))
sns.histplot(
    data=predictions_df[predictions_df["absolute_percentage_error"] <= 80],
    x="absolute_percentage_error",
    bins=40,
    color="#356f8c",
)
plt.axvline(final_model_metrics_df.loc[0, "mape"], color="#b33a3a", linestyle="--", linewidth=1)
plt.title("Holdout Absolute Percentage Error Distribution")
plt.xlabel("Absolute Percentage Error %")
plt.ylabel("Rows")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "absolute_percentage_error_distribution.png", dpi=160, bbox_inches="tight")
plt.show()

# %%
error_band_summary_df = pd.DataFrame(
    [
        {
            "error_band": "<= 5%",
            "rows": int((predictions_df["absolute_percentage_error"] <= 5).sum()),
        },
        {
            "error_band": "<= 10%",
            "rows": int((predictions_df["absolute_percentage_error"] <= 10).sum()),
        },
        {
            "error_band": "<= 15%",
            "rows": int((predictions_df["absolute_percentage_error"] <= 15).sum()),
        },
        {
            "error_band": "> 25%",
            "rows": int((predictions_df["absolute_percentage_error"] > 25).sum()),
        },
    ]
)
error_band_summary_df["row_pct"] = error_band_summary_df["rows"] / len(predictions_df) * 100
error_band_summary_df

# %% [markdown]
# ## 8. Best And Worst Holdout Examples

# %%
example_columns = [
    "dataset_origin_display",
    "source_label",
    "city",
    "brand",
    "model",
    "variant",
    "model_year",
    "fuel_type",
    "transmission",
    "km_driven",
    "actual_price",
    "predicted_price",
    "signed_error",
    "absolute_percentage_error",
    "listing_url",
]

best_predictions_df = predictions_df.sort_values("absolute_percentage_error").head(15)[example_columns]
worst_predictions_df = predictions_df.sort_values("absolute_percentage_error", ascending=False).head(15)[
    example_columns
]

best_predictions_df

# %%
worst_predictions_df

# %% [markdown]
# ## 9. Interpretation Summary

# %%
top_feature_summary = (
    permutation_importance_with_type_df.head(10)[["feature", "feature_type", "mape_increase"]]
    .round({"mape_increase": 3})
    .to_dict(orient="records")
)

source_segment_summary = (
    key_segment_view_df[key_segment_view_df["segment_column"].eq("source_label")]
    .sort_values("mape", ascending=False)
    [["segment_value", "rows", "mae", "mape", "underprediction_rate"]]
    .round({"mae": 0, "mape": 2, "underprediction_rate": 2})
)

interpretation_summary = {
    "model": final_model_metrics_df.loc[0, "model"],
    "holdout_rows": int(final_model_metrics_df.loc[0, "test_rows"]),
    "holdout_mae": float(final_model_metrics_df.loc[0, "mae"]),
    "holdout_mape": float(final_model_metrics_df.loc[0, "mape"]),
    "holdout_r2": float(final_model_metrics_df.loc[0, "r2"]),
    "top_permutation_features": top_feature_summary,
    "main_trust_statement": (
        "The final model learns strong market signal from brand/model identity, "
        "vehicle age, kilometers, city/source context, and lineage features."
    ),
    "main_limitation": (
        "Premium/high-price and rare brand-model rows remain materially harder "
        "than normal-market/common-brand-model rows."
    ),
}

source_segment_summary

# %%
interpretation_summary

# %% [markdown]
# ## 10. Save Interpretation Outputs

# %%
final_model_metrics_df.to_csv(OUTPUT_ROOT / "final_model_interpretation_metrics.csv", index=False)
permutation_importance_with_type_df.to_csv(OUTPUT_ROOT / "permutation_importance.csv", index=False)
segment_metrics_df.to_csv(OUTPUT_ROOT / "segment_metrics.csv", index=False)
key_segment_view_df.to_csv(OUTPUT_ROOT / "key_segment_metrics.csv", index=False)
error_band_summary_df.to_csv(OUTPUT_ROOT / "error_band_summary.csv", index=False)
best_predictions_df.to_csv(OUTPUT_ROOT / "best_holdout_predictions.csv", index=False)
worst_predictions_df.to_csv(OUTPUT_ROOT / "worst_holdout_predictions.csv", index=False)
final_run["target_encoding_summary"].to_csv(OUTPUT_ROOT / "target_encoding_summary.csv", index=False)

with (OUTPUT_ROOT / "interpretation_summary.json").open("w", encoding="utf-8") as f:
    json.dump(interpretation_summary, f, indent=2)

print(f"Saved interpretation outputs to: {OUTPUT_ROOT}")
print(f"Saved figures to: {FIGURE_DIR}")

# %% [markdown]
# ## 11. Final Interpretation Position
#
# The model is credible as a portfolio-grade, trusted-source pricing model
# because:
#
# - the holdout split reproduces the 9.88% MAPE checkpoint
# - the strongest predictive signals are market-relevant vehicle attributes
# - source and dataset lineage are explicitly measured instead of hidden
# - weaknesses are visible in the segment metrics
#
# Correct wording:
#
# > The final model is a strong 10%-class used-car price model on trusted-source
# > data. It is most reliable for common, normal-market vehicles and should be
# > improved separately for rare and premium-tail vehicles.
