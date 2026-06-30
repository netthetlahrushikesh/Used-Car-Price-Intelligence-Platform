"""Repeated-split stability validation for the Used Car Price Intelligence Platform."""

# %% [markdown]
# # Used Car Price Intelligence Platform: Model Stability Validation
#
# This notebook validates whether the 10% MAPE candidate is stable or just a
# lucky split.
#
# Candidate being validated:
#
# - Combined Trusted Lineage Target-Encoded Native HGB
# - target: `log1p(listed_price_inr)`
# - previous single-split combined MAPE: `9.88%`
#
# Validation approach:
#
# - run the same model across multiple train/test split seeds
# - keep out-of-fold target encoding inside each training split
# - report mean, standard deviation, best, worst, and segment behavior

# %%
from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 140)
pd.set_option("display.float_format", lambda value: f"{value:,.3f}")

TARGET = "listed_price_inr"
TEST_SIZE = 0.20
RARE_BRAND_MODEL_MIN_ROWS = 10
TARGET_ENCODING_SMOOTHING = 10
TARGET_ENCODING_SPLITS = 5
HIGH_CARDINALITY_TOP_N = 180
VALIDATION_SEEDS = [7, 13, 21, 42, 67, 101, 202]

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

OUTPUT_ROOT = Path("notebooks") / "outputs" / "used_car_price_intelligence_model_stability_validation"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

KAGGLE_DATASET_ROOTS = [
    Path("/kaggle/input/datasets/hrushikeshnettetla/used-car-price-trusted-modeling-datasets"),
    Path("/kaggle/input/used-car-price-trusted-modeling-datasets"),
    Path("/kaggle/input/used-car-price-intelligence-trusted-modeling-datasets"),
]

# %% [markdown]
# ## 1. Load Combined Dataset

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
        return kaggle_path

    repo_root_candidates = [Path.cwd(), Path.cwd().parent]
    local_candidates = [
        root
        / "kaggle_upload"
        / "used-car-price-intelligence-trusted-modeling-datasets"
        / "combined_trusted_modeling_dataset_9110.csv"
        for root in repo_root_candidates
    ]
    return first_existing_path(local_candidates)


COMBINED_DATASET_PATH = resolve_combined_dataset_path()

raw_combined = pd.read_csv(COMBINED_DATASET_PATH)
print(COMBINED_DATASET_PATH)
print(raw_combined.shape)

# %% [markdown]
# ## 2. Feature Engineering

# %%
def normalized_text(series):
    return series.fillna("unknown").astype(str).str.strip().str.lower()


def add_engineered_features(df):
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
    out["luxury_transmission"] = out["is_luxury_brand"].map({1: "luxury", 0: "non_luxury"}) + "__" + transmission_norm

    for col in ["brand_model", "model", "brand", "variant", "city_brand"]:
        counts = out[col].fillna("unknown").astype(str).value_counts()
        out[f"{col}_frequency"] = out[col].fillna("unknown").astype(str).map(counts).astype(float)

    return out


def add_eval_labels(df):
    out = df.copy()
    brand_model_counts = out["brand_model"].fillna("unknown").astype(str).value_counts()
    rare_brand_models = set(
        brand_model_counts[brand_model_counts < RARE_BRAND_MODEL_MIN_ROWS].index
    )

    out["source_label"] = out["source"].map(SOURCE_LABELS).fillna(out["source"])
    out["dataset_origin_display"] = (
        out["dataset_origin"].map(DATASET_ORIGIN_LABELS).fillna(out["dataset_origin"])
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


combined = add_eval_labels(add_engineered_features(raw_combined))
combined.shape

# %% [markdown]
# ## 3. Model Configuration

# %%
NUMERIC_FEATURES = [
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

CATEGORICAL_FEATURES = [
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

TARGET_ENCODED_FEATURES = [f"te_{col}" for col in TARGET_ENCODING_COLUMNS]


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


NUMERIC_FEATURES = dedupe_preserve_order(available_columns(combined, NUMERIC_FEATURES) + TARGET_ENCODED_FEATURES)
CATEGORICAL_FEATURES = dedupe_preserve_order(available_columns(combined, CATEGORICAL_FEATURES))
FEATURE_COLUMNS = dedupe_preserve_order(NUMERIC_FEATURES + CATEGORICAL_FEATURES)

print(len(NUMERIC_FEATURES), len(CATEGORICAL_FEATURES), len(FEATURE_COLUMNS))

# %% [markdown]
# ## 4. Training Helpers

# %%
def smoothed_target_mapping(series, y_log, smoothing):
    global_mean = float(y_log.mean())
    tmp = pd.DataFrame({"category": series.fillna("unknown").astype(str), "target": y_log})
    stats = tmp.groupby("category")["target"].agg(["mean", "count"])
    encoded = (stats["count"] * stats["mean"] + smoothing * global_mean) / (
        stats["count"] + smoothing
    )
    return encoded, global_mean


def add_out_of_fold_target_encoding(train_rows, test_rows, columns, seed):
    train_encoded = train_rows.copy()
    test_encoded = test_rows.copy()
    kfold = KFold(n_splits=TARGET_ENCODING_SPLITS, shuffle=True, random_state=seed)

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

    return train_encoded, test_encoded


def prepare_native_hgb_features(train_rows, test_rows):
    train_x = train_rows[FEATURE_COLUMNS].copy()
    test_x = test_rows[FEATURE_COLUMNS].copy()

    for col in NUMERIC_FEATURES:
        train_x[col] = pd.to_numeric(train_x[col], errors="coerce")
        test_x[col] = pd.to_numeric(test_x[col], errors="coerce")

    for col in CATEGORICAL_FEATURES:
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


def build_model(seed):
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


def make_price_stratification(y):
    labels = pd.qcut(y, q=10, duplicates="drop")
    counts = labels.value_counts()
    if len(counts) < 2 or counts.min() < 2:
        return None
    return labels

# %% [markdown]
# ## 5. Repeated-Split Validation

# %%
def run_seed(seed):
    model_df = combined.dropna(subset=[TARGET]).copy()
    stratify_labels = make_price_stratification(model_df[TARGET])
    train_rows, test_rows = train_test_split(
        model_df,
        test_size=TEST_SIZE,
        random_state=seed,
        stratify=stratify_labels,
    )

    train_encoded, test_encoded = add_out_of_fold_target_encoding(
        train_rows,
        test_rows,
        TARGET_ENCODING_COLUMNS,
        seed,
    )
    train_x, test_x = prepare_native_hgb_features(train_encoded, test_encoded)
    y_train = train_encoded[TARGET]
    y_test = test_encoded[TARGET]

    model = build_model(seed)
    model.fit(train_x, np.log1p(y_train))
    predictions = np.clip(np.expm1(model.predict(test_x)), 0, None)
    metrics = regression_metrics(y_test, predictions)

    pred_df = test_encoded.copy()
    pred_df["validation_seed"] = seed
    pred_df["actual_price"] = y_test.values
    pred_df["predicted_price"] = predictions
    pred_df["signed_error"] = pred_df["predicted_price"] - pred_df["actual_price"]
    pred_df["absolute_error"] = np.abs(pred_df["signed_error"])
    pred_df["absolute_percentage_error"] = (
        pred_df["absolute_error"] / np.maximum(np.abs(pred_df["actual_price"]), 1) * 100
    )
    pred_df["is_underprediction"] = pred_df["signed_error"] < 0

    metrics_row = {
        "validation_seed": seed,
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "hgb_iterations": int(model.n_iter_),
        **metrics,
    }
    return metrics_row, pred_df


all_metrics = []
all_predictions = []
for seed in VALIDATION_SEEDS:
    print("Running validation seed:", seed)
    metrics_row, pred_df = run_seed(seed)
    all_metrics.append(metrics_row)
    all_predictions.append(pred_df)
    print(metrics_row)

stability_metrics_df = pd.DataFrame(all_metrics)
stability_predictions_df = pd.concat(all_predictions, ignore_index=True)

stability_metrics_df

# %% [markdown]
# ## 6. Stability Summary

# %%
metric_columns = ["mae", "rmse", "mape", "r2", "underprediction_rate", "hgb_iterations"]
summary_rows = []
for metric in metric_columns:
    values = stability_metrics_df[metric]
    summary_rows.append(
        {
            "metric": metric,
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)),
            "min": float(values.min()),
            "p25": float(values.quantile(0.25)),
            "median": float(values.median()),
            "p75": float(values.quantile(0.75)),
            "max": float(values.max()),
        }
    )

stability_summary_df = pd.DataFrame(summary_rows)
stability_summary_df

# %%
def segment_metrics(predictions, segment_col, min_rows=1):
    rows = []
    for (seed, segment_value), group in predictions.groupby(["validation_seed", segment_col], dropna=False):
        if len(group) < min_rows:
            continue
        metrics = regression_metrics(group["actual_price"], group["predicted_price"])
        rows.append(
            {
                "validation_seed": seed,
                "segment_column": segment_col,
                "segment_value": segment_value,
                "rows": len(group),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


segment_metric_tables = []
for segment_col in ["dataset_origin_display", "source_label", "brand_model_eval_group", "price_tail_group"]:
    table = segment_metrics(stability_predictions_df, segment_col, min_rows=1)
    if len(table):
        segment_metric_tables.append(table)

stability_segment_metrics_df = pd.concat(segment_metric_tables, ignore_index=True)
stability_segment_summary_df = (
    stability_segment_metrics_df
    .groupby(["segment_column", "segment_value"], dropna=False)
    .agg(
        runs=("validation_seed", "nunique"),
        mean_rows=("rows", "mean"),
        mean_mae=("mae", "mean"),
        mean_mape=("mape", "mean"),
        min_mape=("mape", "min"),
        max_mape=("mape", "max"),
        mean_r2=("r2", "mean"),
        mean_underprediction_rate=("underprediction_rate", "mean"),
    )
    .reset_index()
    .sort_values(["segment_column", "mean_mape"], ascending=[True, False])
)

stability_segment_summary_df

# %% [markdown]
# ## 7. Validation Decision

# %%
mean_mape = float(stability_metrics_df["mape"].mean())
max_mape = float(stability_metrics_df["mape"].max())
std_mape = float(stability_metrics_df["mape"].std(ddof=1))
target_hit_rate = float((stability_metrics_df["mape"] <= 10.0).mean() * 100)

if mean_mape <= 10.25 and max_mape <= 10.75:
    validation_status = "stable_enough_for_candidate_v1"
elif mean_mape <= 10.5 and max_mape <= 11.0:
    validation_status = "usable_with_warning"
else:
    validation_status = "unstable_needs_more_work"

decision = {
    "validated_model": "Combined Trusted Lineage Target-Encoded Native HGB",
    "validation_runs": len(stability_metrics_df),
    "mean_mape": mean_mape,
    "std_mape": std_mape,
    "min_mape": float(stability_metrics_df["mape"].min()),
    "max_mape": max_mape,
    "target_hit_rate_pct": target_hit_rate,
    "mean_mae": float(stability_metrics_df["mae"].mean()),
    "mean_r2": float(stability_metrics_df["r2"].mean()),
    "validation_status": validation_status,
    "decision": (
        "Freeze as main model candidate v1 if stable_enough; keep premium-tail "
        "modeling as separate improvement track."
    ),
}

stability_decision_df = pd.DataFrame([decision])
stability_decision_df

# %% [markdown]
# ## 8. Save Validation Outputs

# %%
stability_metrics_df.to_csv(OUTPUT_ROOT / "stability_metrics_by_seed.csv", index=False)
stability_predictions_df.to_csv(OUTPUT_ROOT / "stability_predictions_by_seed.csv", index=False)
stability_summary_df.to_csv(OUTPUT_ROOT / "stability_summary.csv", index=False)
stability_segment_metrics_df.to_csv(OUTPUT_ROOT / "stability_segment_metrics_by_seed.csv", index=False)
stability_segment_summary_df.to_csv(OUTPUT_ROOT / "stability_segment_summary.csv", index=False)
stability_decision_df.to_csv(OUTPUT_ROOT / "stability_decision_summary.csv", index=False)

validation_config = {
    "validated_model": "Combined Trusted Lineage Target-Encoded Native HGB",
    "validation_seeds": VALIDATION_SEEDS,
    "test_size": TEST_SIZE,
    "target": TARGET,
    "target_transform": "log1p",
    "target_encoding_smoothing": TARGET_ENCODING_SMOOTHING,
    "target_encoding_splits": TARGET_ENCODING_SPLITS,
    "high_cardinality_top_n": HIGH_CARDINALITY_TOP_N,
    "numeric_features": NUMERIC_FEATURES,
    "categorical_features": CATEGORICAL_FEATURES,
    "target_encoded_features": TARGET_ENCODED_FEATURES,
}
with (OUTPUT_ROOT / "validation_config.json").open("w", encoding="utf-8") as f:
    json.dump(validation_config, f, indent=2)

print(f"Saved validation outputs to: {OUTPUT_ROOT}")
stability_decision_df

# %% [markdown]
# ## 9. Final Validation Statement
#
# If the repeated-split MAPE distribution remains close to the original 9.88%
# checkpoint, the model can be frozen as Candidate v1. If not, the next work
# should improve validation stability before model storytelling or deployment.
