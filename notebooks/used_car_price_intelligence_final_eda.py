"""Final EDA notebook for the Used Car Price Intelligence Platform.

This file is written in Jupyter percent-cell format so it can be reviewed cleanly
in GitHub and converted to `.ipynb` for Kaggle/Jupyter.
"""

# %% [markdown]
# # Used Car Price Intelligence Platform: Final EDA And Model Readiness
#
# This notebook is the clean EDA checkpoint for the three-model phase of the
# Used Car Price Intelligence Platform.
#
# It compares:
#
# 1. **Live Trusted Market Snapshot**: 3,496 deduped trusted listings
# 2. **External True Value Historical Dataset**: 5,614 processed historical listings
# 3. **Combined Trusted Modeling Dataset**: 9,110 listings with lineage columns
#
# The objective is not final model training. The objective is to confirm that
# the data is ready for baseline modeling, identify source bias, document
# outlier decisions, and define a safe feature set.

# %% [markdown]
# ## 0. Notebook Contract
#
# This notebook intentionally does four things:
#
# - Loads the three modeling datasets from Kaggle input or local project files.
# - Checks row counts, duplicates, missingness, coverage, drift, and sanity ranges.
# - Documents the decision to keep genuine price-tail listings.
# - Produces model-readiness outputs for the next notebook.
#
# It intentionally does not train models. Modeling belongs in the next phase.

# %%
from pathlib import Path
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

try:
    from IPython.display import display
except ImportError:
    def display(value):
        print(value)

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
pd.set_option("display.max_columns", 100)
pd.set_option("display.float_format", lambda value: f"{value:,.2f}")

TARGET = "listed_price_inr"

DATASET_LABELS = {
    "live": "Live Trusted Market Snapshot",
    "external_true_value": "External True Value Historical Dataset",
    "combined": "Combined Trusted Modeling Dataset",
}

KAGGLE_DATASET_ROOTS = [
    Path("/kaggle/input/datasets/hrushikeshnettetla/used-car-price-trusted-modeling-datasets"),
    Path("/kaggle/input/used-car-price-trusted-modeling-datasets"),
    Path("/kaggle/input/used-car-price-intelligence-trusted-modeling-datasets"),
]

# %% [markdown]
# ## 1. Load Datasets
#
# The loader supports both Kaggle and local repository execution:
#
# - On Kaggle, it recursively searches `/kaggle/input` for the uploaded CSVs.
# - Locally, it searches the project package/data locations.

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
    OUTPUT_ROOT = Path("/kaggle/working/used_car_price_intelligence_final_eda")
else:
    OUTPUT_ROOT = Path("notebooks") / "outputs" / "used_car_price_intelligence_final_eda"

FIGURE_DIR = OUTPUT_ROOT / "figures"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
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
# ## 2. Helper Functions

# %%
def count_table(df, column, top_n=15):
    counts = df[column].fillna("missing").astype(str).value_counts().head(top_n)
    out = pd.DataFrame({column: counts.index, "rows": counts.values})
    out["share_pct"] = out["rows"] / len(df) * 100
    return out


def missing_report(df):
    missing = df.isna().sum()
    report = pd.DataFrame({"column": missing.index, "missing": missing.values})
    report["missing_pct"] = report["missing"] / len(df) * 100
    return report.sort_values(["missing_pct", "missing"], ascending=[False, False])


def median_price_table(df, group_col, min_rows=20, top_n=20):
    out = (
        df.groupby(group_col, dropna=False)
        .agg(
            rows=(TARGET, "size"),
            median_price=(TARGET, "median"),
            mean_price=(TARGET, "mean"),
            median_km=("km_driven", "median"),
            median_model_year=("model_year", "median"),
        )
        .query("rows >= @min_rows")
        .sort_values("rows", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return out


def save_table(df, name):
    path = OUTPUT_ROOT / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"Saved: {path}")


def save_current_figure(file_name):
    path = FIGURE_DIR / file_name
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    print(f"Saved figure: {path}")

# %% [markdown]
# ## 3. Dataset Integrity Summary
#
# This validates the base sizes, duplicate keys, and high-level price/km profile.

# %%
summary_rows = []
for name, df in datasets.items():
    summary_rows.append(
        {
            "dataset": name,
            "dataset_name": DATASET_LABELS[name],
            "rows": len(df),
            "columns": df.shape[1],
            "unique_listing_keys": df["listing_key"].nunique(),
            "duplicate_listing_keys": len(df) - df["listing_key"].nunique(),
            "median_price": df[TARGET].median(),
            "median_km": df["km_driven"].median(),
            "median_model_year": df["model_year"].median(),
        }
    )

dataset_summary = pd.DataFrame(summary_rows)[
    [
        "dataset_name",
        "dataset",
        "rows",
        "columns",
        "unique_listing_keys",
        "duplicate_listing_keys",
        "median_price",
        "median_km",
        "median_model_year",
    ]
]
dataset_summary

# %%
source_mix = count_table(combined, "source", top_n=20)
source_mix

# %%
plt.figure(figsize=(10, 5))
sns.barplot(data=source_mix, x="rows", y="source", color="#2f6f9f")
plt.title("Combined Dataset: Source Mix")
plt.xlabel("Rows")
plt.ylabel("Source")
save_current_figure("combined_source_mix.png")
plt.show()

# %% [markdown]
# ## 4. Missing Values And Core Completeness
#
# Core modeling fields are expected to be complete or nearly complete. Optional
# fields such as `ownership`, `registration_code`, and `vehicle_fingerprint` may
# have missingness and should be handled carefully in modeling.

# %%
required_cols = [
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
    "km_driven",
    TARGET,
]
required_cols = [col for col in required_cols if col in combined.columns]

combined_missing = missing_report(combined)
combined_missing.head(25)

# %%
required_missing = pd.DataFrame(
    {name: df[required_cols].isna().sum() for name, df in datasets.items()}
)
required_missing = required_missing.rename(columns=DATASET_LABELS)
required_missing

# %% [markdown]
# ## 5. Price, Kilometers, And Year Distributions

# %%
price_summary_rows = []
for name, df in datasets.items():
    price_summary_rows.append(
        {
            "dataset": name,
            "dataset_name": DATASET_LABELS[name],
            "min": df[TARGET].min(),
            "p25": df[TARGET].quantile(0.25),
            "median": df[TARGET].median(),
            "p75": df[TARGET].quantile(0.75),
            "p95": df[TARGET].quantile(0.95),
            "p99": df[TARGET].quantile(0.99),
            "max": df[TARGET].max(),
        }
    )

price_summary = pd.DataFrame(price_summary_rows)[
    ["dataset_name", "dataset", "min", "p25", "median", "p75", "p95", "p99", "max"]
]
price_summary

# %%
plot_df = pd.concat(
    [
        live.assign(dataset=DATASET_LABELS["live"]),
        external.assign(dataset=DATASET_LABELS["external_true_value"]),
    ],
    ignore_index=True,
)

plt.figure(figsize=(11, 5))
sns.histplot(
    data=plot_df,
    x=TARGET,
    hue="dataset",
    bins=60,
    element="step",
    stat="density",
    common_norm=False,
)
plt.xlim(0, plot_df[TARGET].quantile(0.99))
plt.title("Price Distribution: Live vs External")
plt.xlabel("Listed Price INR")
plt.ylabel("Density")
save_current_figure("price_distribution_live_vs_external.png")
plt.show()

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.boxplot(data=plot_df, x="dataset", y="km_driven", ax=axes[0])
axes[0].set_ylim(0, plot_df["km_driven"].quantile(0.99))
axes[0].set_title("Kilometers Driven")
axes[0].set_xlabel("")
axes[0].set_ylabel("KM")

sns.boxplot(data=plot_df, x="dataset", y="model_year", ax=axes[1])
axes[1].set_title("Model Year")
axes[1].set_xlabel("")
axes[1].set_ylabel("Year")

save_current_figure("km_and_year_live_vs_external.png")
plt.show()

# %% [markdown]
# ## 6. Coverage: Cities, Brands, Models, And Variants
#
# This section checks whether the dataset is concentrated in a few popular
# Indian used-car models and whether rare groups may need special evaluation.

# %%
city_coverage = count_table(combined, "city", top_n=25)
city_coverage

# %%
top_brand_models = count_table(combined, "brand_model", top_n=25)
top_brand_models

# %%
plt.figure(figsize=(10, 8))
sns.barplot(data=top_brand_models, x="rows", y="brand_model", color="#496f5d")
plt.title("Top Brand-Model Groups In Combined Dataset")
plt.xlabel("Rows")
plt.ylabel("Brand Model")
save_current_figure("top_brand_models_combined.png")
plt.show()

# %%
def category_coverage(df, column, min_rows=10):
    counts = df[column].fillna("missing").astype(str).value_counts()
    low_sample = counts[counts < min_rows]
    return pd.DataFrame(
        {
            "column": [column],
            "unique_values": [len(counts)],
            f"groups_under_{min_rows}_rows": [int((counts < min_rows).sum())],
            f"rows_in_groups_under_{min_rows}_rows": [int(low_sample.sum())],
            f"row_pct_in_groups_under_{min_rows}_rows": [low_sample.sum() / len(df) * 100],
            "top_group": [counts.index[0]],
            "top_group_rows": [int(counts.iloc[0])],
        }
    )


coverage_cols = [
    "city",
    "brand",
    "model",
    "brand_model",
    "variant",
    "fuel_type",
    "transmission",
    "ownership",
]
coverage_cols = [col for col in coverage_cols if col in combined.columns]

coverage_report = pd.concat(
    [category_coverage(combined, col, min_rows=10) for col in coverage_cols],
    ignore_index=True,
)
coverage_report

# %%
brand_model_counts = count_table(combined, "brand_model", top_n=10_000)
low_sample_brand_models = brand_model_counts.query("rows < 10")

print("Brand-model groups with >= 30 rows:", int((brand_model_counts["rows"] >= 30).sum()))
print(
    "Rows covered by brand-model groups with >= 30 rows:",
    int(brand_model_counts.query("rows >= 30")["rows"].sum()),
)
print(
    "Coverage pct:",
    round(brand_model_counts.query("rows >= 30")["rows"].sum() / len(combined) * 100, 2),
)

low_sample_brand_models.head(50)

# %% [markdown]
# ### Rare Category Coverage Decision
#
# Rare categories are not data-quality failures. They are model-risk signals.
# The modeling notebook should keep them, but it should evaluate error by common
# vs rare `brand_model` groups and use preprocessing that can handle unknown or
# infrequent categories.

# %%
RARE_CATEGORY_MIN_ROWS = 10


def rare_category_detail(df, column, min_rows=RARE_CATEGORY_MIN_ROWS):
    counts = df[column].fillna("missing").astype(str).value_counts()
    rare_counts = counts[counts < min_rows]
    out = pd.DataFrame(
        {
            "column": column,
            "category_value": rare_counts.index,
            "rows": rare_counts.values,
        }
    )
    out["row_pct"] = out["rows"] / len(df) * 100
    return out


rare_category_detail_table = pd.concat(
    [rare_category_detail(combined, col) for col in coverage_cols],
    ignore_index=True,
)

rare_category_summary = coverage_report.copy()
rare_pct_col = f"row_pct_in_groups_under_{RARE_CATEGORY_MIN_ROWS}_rows"
rare_category_summary["modeling_action"] = np.where(
    rare_category_summary[rare_pct_col] >= 5,
    "Track segment error and use infrequent-category handling",
    "Track segment error; standard categorical encoding is acceptable",
)

rare_category_summary

# %%
rare_category_detail_table.sort_values(["column", "rows"], ascending=[True, False]).head(100)

# %% [markdown]
# ## 7. Segment-Level Price Tables

# %%
median_price_table(combined, "brand_model", min_rows=30, top_n=25)

# %%
segment_cols = [
    "dataset_origin_label" if "dataset_origin_label" in combined.columns else "dataset_origin",
    "source",
    "city",
    "fuel_type",
    "transmission",
    "ownership",
]
segment_price_tables = {}

for col in segment_cols:
    if col in combined.columns:
        segment_price_tables[col] = median_price_table(combined, col, min_rows=10, top_n=30)
        print(f"\nSegment: {col}")
        display(segment_price_tables[col])

# %% [markdown]
# ## 8. Dataset Origin Drift
#
# The combined dataset mixes live 2026 market data with external historical True
# Value data. This is useful for coverage, but it creates distribution shift.
# The combined model must keep lineage features and segment metrics.

# %%
origin_group_col = (
    "dataset_origin_label"
    if "dataset_origin_label" in combined.columns
    else "dataset_origin"
    if "dataset_origin" in combined.columns
    else "source"
)

origin_drift = (
    combined.groupby(origin_group_col, dropna=False)
    .agg(
        rows=(TARGET, "size"),
        median_price=(TARGET, "median"),
        mean_price=(TARGET, "mean"),
        median_km=("km_driven", "median"),
        median_model_year=("model_year", "median"),
        unique_cities=("city", "nunique"),
        unique_brand_models=("brand_model", "nunique"),
    )
    .reset_index()
)

origin_drift

# %%
plt.figure(figsize=(11, 5))
sns.boxplot(data=combined, x=origin_group_col, y=TARGET)
plt.ylim(0, combined[TARGET].quantile(0.99))
plt.title("Price Distribution By Dataset Origin")
plt.xlabel("")
plt.ylabel("Listed Price INR")
save_current_figure("price_by_dataset_origin.png")
plt.show()

# %% [markdown]
# ## 9. Range Sanity Checks
#
# These checks catch obvious parsing errors before modeling. Small genuine market
# tails should be reviewed and documented, not automatically removed.

# %%
def range_sanity_report(df, dataset_name):
    checks = []

    def add_check(check_name, mask):
        checks.append(
            {
                "dataset": dataset_name,
                "check": check_name,
                "bad_rows": int(mask.sum()),
                "bad_pct": float(mask.mean() * 100),
            }
        )

    add_check("price <= 0", df[TARGET].fillna(0) <= 0)
    add_check("price < 50,000", df[TARGET].fillna(0) < 50_000)
    add_check("price > 30,00,000", df[TARGET].fillna(0) > 3_000_000)
    add_check("km < 0", df["km_driven"].fillna(0) < 0)
    add_check("km > 3,00,000", df["km_driven"].fillna(0) > 300_000)
    add_check("model_year < 2000", df["model_year"].fillna(0) < 2000)
    add_check("model_year > 2026", df["model_year"].fillna(9999) > 2026)

    if "vehicle_age_years" in df.columns:
        add_check("vehicle_age_years < 0", df["vehicle_age_years"].fillna(0) < 0)
        add_check("vehicle_age_years > 30", df["vehicle_age_years"].fillna(0) > 30)

    return pd.DataFrame(checks)


range_checks = pd.concat(
    [range_sanity_report(df, DATASET_LABELS[name]) for name, df in datasets.items()],
    ignore_index=True,
)
range_checks

# %%
review_cols = [
    "dataset_origin_label",
    "dataset_origin",
    "source",
    "city",
    "brand",
    "model",
    "variant",
    "model_year",
    "fuel_type",
    "transmission",
    "ownership",
    "km_driven",
    TARGET,
    "listing_url",
]
review_cols = [col for col in review_cols if col in combined.columns]

edge_price_rows = combined.query(f"{TARGET} < 50000 or {TARGET} > 3000000")
edge_price_rows[review_cols].sort_values(TARGET)

# %% [markdown]
# ### Price Outlier Decision
#
# The low-price and high-price rows were manually reviewed during EDA and look
# like genuine market listings, not parsing errors. We keep them in the baseline
# dataset.

# %%
price_outlier_decision = {
    "low_price_rows_under_50000": int((combined[TARGET] < 50_000).sum()),
    "high_price_rows_over_3000000": int((combined[TARGET] > 3_000_000).sum()),
    "decision": "keep",
    "reason": (
        "Manual review indicates these rows are genuine listings, not parsing errors. "
        "They represent valid market tail cases and should remain in the baseline dataset."
    ),
}

price_outlier_decision

# %% [markdown]
# ## 10. Leakage Columns And Modeling Feature Plan
#
# We should not train on IDs, URLs, capture metadata, registration code, or
# fingerprints. These columns can leak listing identity or collection mechanics
# rather than reusable market behavior.

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

model_feature_cols = [col for col in CORE_FEATURE_CANDIDATES if col in combined.columns]
combined_model_feature_cols = model_feature_cols + [
    col for col in COMBINED_ONLY_FEATURES if col in combined.columns
]
excluded_cols = [col for col in LEAKAGE_OR_ID_COLS if col in combined.columns]

feature_plan = {
    "target": TARGET,
    "excluded_leakage_or_id_columns": excluded_cols,
    "live_external_feature_columns": model_feature_cols,
    "combined_feature_columns": combined_model_feature_cols,
    "missing_value_rule": "Fill categorical missing values such as ownership with 'unknown'.",
    "lineage_rule": "Use dataset_origin/data_freshness only for the combined model.",
}

feature_plan

# %%
def model_missingness(df, feature_cols, dataset_name):
    cols = feature_cols + [TARGET]
    missing = df[cols].isna().sum()
    report = pd.DataFrame({"column": missing.index, "missing": missing.values})
    report["dataset"] = dataset_name
    report["missing_pct"] = report["missing"] / len(df) * 100
    return report[["dataset", "column", "missing", "missing_pct"]]


model_missing_report = pd.concat(
    [
        model_missingness(live, model_feature_cols, DATASET_LABELS["live"]),
        model_missingness(external, model_feature_cols, DATASET_LABELS["external_true_value"]),
        model_missingness(combined, combined_model_feature_cols, DATASET_LABELS["combined"]),
    ],
    ignore_index=True,
)

model_missing_report.sort_values(["missing_pct", "missing"], ascending=[False, False]).head(40)

# %% [markdown]
# ## 11. Model-Readiness Checklist
#
# This checklist converts the EDA into a simple decision: whether the data can
# move to baseline modeling and what modeling caveats must be carried forward.

# %%
non_price_tail_bad_rows = range_checks[
    (~range_checks["check"].isin(["price < 50,000", "price > 30,00,000"]))
    & (range_checks["bad_rows"] > 0)
]

required_missing_total = int(required_missing.sum().sum())
model_feature_missing_max_pct = float(model_missing_report["missing_pct"].max())
rare_brand_model_row_pct = float(
    low_sample_brand_models["rows"].sum() / len(combined) * 100
    if len(low_sample_brand_models)
    else 0
)
combined_duplicate_keys = int(len(combined) - combined["listing_key"].nunique())

readiness_checks = pd.DataFrame(
    [
        {
            "check": "no duplicate listing keys in combined dataset",
            "status": "pass" if combined_duplicate_keys == 0 else "fail",
            "value": combined_duplicate_keys,
            "decision": "required for modeling identity integrity",
        },
        {
            "check": "required modeling columns are complete",
            "status": "pass" if required_missing_total == 0 else "warn",
            "value": required_missing_total,
            "decision": "core feature columns should be complete before baseline modeling",
        },
        {
            "check": "no invalid non-price range checks",
            "status": "pass" if non_price_tail_bad_rows.empty else "fail",
            "value": int(non_price_tail_bad_rows["bad_rows"].sum()),
            "decision": "invalid km/year/age rows should be fixed before modeling",
        },
        {
            "check": "price-tail rows manually reviewed",
            "status": "pass",
            "value": int((combined[TARGET] < 50_000).sum() + (combined[TARGET] > 3_000_000).sum()),
            "decision": "keep genuine low/high price market-tail listings",
        },
        {
            "check": "lineage columns available for combined model",
            "status": "pass"
            if all(col in combined.columns for col in ["dataset_origin", "market_snapshot_year"])
            else "warn",
            "value": ", ".join([col for col in ["dataset_origin", "market_snapshot_year"] if col in combined.columns]),
            "decision": "combined model must include lineage and segment evaluation",
        },
        {
            "check": "rare brand-model groups identified",
            "status": "warn" if len(low_sample_brand_models) else "pass",
            "value": f"{len(low_sample_brand_models)} groups, {rare_brand_model_row_pct:.2f}% rows",
            "decision": "not a blocker; evaluate metrics separately for rare groups",
        },
    ]
)

model_readiness_status = (
    "ready_with_warnings"
    if readiness_checks["status"].isin(["fail"]).sum() == 0
    and readiness_checks["status"].isin(["warn"]).sum() > 0
    else "ready"
    if readiness_checks["status"].isin(["fail", "warn"]).sum() == 0
    else "not_ready"
)

print("Model readiness status:", model_readiness_status)
readiness_checks

# %% [markdown]
# ## 12. Final EDA Decision Summary

# %%
modeling_decision = {
    "target": TARGET,
    "live_dataset_name": DATASET_LABELS["live"],
    "external_dataset_name": DATASET_LABELS["external_true_value"],
    "combined_dataset_name": DATASET_LABELS["combined"],
    "live_rows": len(live),
    "external_true_value_rows": len(external),
    "combined_rows": len(combined),
    "live_duplicate_keys": int(len(live) - live["listing_key"].nunique()),
    "external_duplicate_keys": int(len(external) - external["listing_key"].nunique()),
    "combined_duplicate_keys": int(len(combined) - combined["listing_key"].nunique()),
    "combined_has_lineage_columns": all(
        col in combined.columns
        for col in ["dataset_origin", "market_snapshot_year", "original_listing_key"]
    ),
    "model_readiness_status": model_readiness_status,
    "range_checks_bad_rows_total": int(range_checks["bad_rows"].sum()),
    "non_price_tail_bad_rows": int(non_price_tail_bad_rows["bad_rows"].sum()),
    "price_outlier_decision": "keep manually reviewed genuine price-tail rows",
    "rare_category_min_rows": RARE_CATEGORY_MIN_ROWS,
    "rare_brand_model_groups": int(len(low_sample_brand_models)),
    "rare_brand_model_row_pct": rare_brand_model_row_pct,
    "max_model_feature_missing_pct": model_feature_missing_max_pct,
    "core_feature_count": len(model_feature_cols),
    "combined_feature_count": len(combined_model_feature_cols),
    "recommended_modeling_plan": (
        "Train three baselines: live-only, external-only, and combined. "
        "Use the same preprocessing pipeline. Include lineage features only in the combined model. "
        "Evaluate overall metrics and segment metrics by dataset_origin, source, city, "
        "brand_model, fuel_type, and model_year."
    ),
}

modeling_decision_df = pd.DataFrame([modeling_decision])
modeling_decision_df

# %% [markdown]
# ## 13. Save Final EDA Outputs

# %%
save_table(dataset_summary, "dataset_summary")
save_table(source_mix, "source_mix")
save_table(combined_missing, "combined_missing_values")
save_table(required_missing.reset_index().rename(columns={"index": "column"}), "required_column_missingness")
save_table(price_summary, "price_summary")
save_table(city_coverage, "city_coverage")
save_table(top_brand_models, "top_brand_models")
save_table(coverage_report, "category_coverage_report")
save_table(rare_category_summary, "rare_category_summary")
save_table(rare_category_detail_table, "rare_category_detail")
save_table(brand_model_counts, "brand_model_counts")
save_table(low_sample_brand_models, "low_sample_brand_models")
save_table(origin_drift, "dataset_origin_drift")
save_table(range_checks, "range_sanity_checks")
save_table(edge_price_rows[review_cols].sort_values(TARGET), "reviewed_edge_price_rows")
save_table(model_missing_report, "model_feature_missingness")
save_table(readiness_checks, "model_readiness_checks")
save_table(modeling_decision_df, "modeling_decision_summary")

pd.DataFrame([price_outlier_decision]).to_csv(
    OUTPUT_ROOT / "price_outlier_decision.csv",
    index=False,
)

print(f"Final EDA outputs saved to: {OUTPUT_ROOT}")
print(f"Figures saved to: {FIGURE_DIR}")

# %% [markdown]
# ## 14. Final Readiness Statement
#
# The dataset is ready for baseline modeling.
#
# Modeling should proceed with three experiments:
#
# 1. **Live-only model**: best view of the current trusted market snapshot.
# 2. **External-only True Value model**: useful historical trusted baseline.
# 3. **Combined model with lineage**: broader coverage, but must include origin
#    features and segment-level error review.
#
# The next notebook should build a shared sklearn preprocessing/training pipeline
# and compare MAE, RMSE, MAPE, R2, and segment errors.
