"""Kaggle notebook starter for three-model EDA comparison.

Paste this into a Kaggle notebook after adding the Kaggle dataset:
`hrushikeshnettetla/used-car-price-intelligence-three-model-phase`.
"""

# %% [markdown]
# # Used Car Price Intelligence: Three Model EDA Comparison
#
# This notebook compares three modeling candidates:
#
# 1. Live trusted deduped dataset: 3,496 rows
# 2. External True Value Kaggle dataset: 5,614 rows
# 3. Combined live + external experiment dataset: 9,110 rows
#
# The goal is not to prove the final model yet. The goal is to understand data quality,
# source bias, city/model coverage, outliers, and feature readiness before modeling.

# %%
from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
pd.set_option("display.max_columns", 80)
pd.set_option("display.float_format", lambda value: f"{value:,.2f}")

OUTPUT_ROOT = Path("/kaggle/working/three_model_eda_outputs")
FIGURE_DIR = OUTPUT_ROOT / "figures"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

combined_matches = sorted(Path("/kaggle/input").rglob("combined_live_external_9110.csv"))
if not combined_matches:
    raise FileNotFoundError("Could not find combined_live_external_9110.csv under /kaggle/input")

INPUT_ROOT = combined_matches[0].parent
DATASETS = {
    "live": INPUT_ROOT / "live_trusted_deduped_3496.csv",
    "external_true_value": INPUT_ROOT / "external_true_value_kaggle_5614.csv",
    "combined": INPUT_ROOT / "combined_live_external_9110.csv",
}

print("Using INPUT_ROOT:", INPUT_ROOT)
for name, path in DATASETS.items():
    print(name, path, path.exists())

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
    print(f"{name}: {df.shape[0]:,} rows x {df.shape[1]:,} columns")

# %% [markdown]
# ## 1. Row Counts And Source Mix

# %%
summary_rows = []
for name, df in datasets.items():
    summary_rows.append(
        {
            "dataset": name,
            "rows": len(df),
            "columns": df.shape[1],
            "unique_listing_keys": df["listing_key"].nunique(),
            "duplicate_listing_keys": len(df) - df["listing_key"].nunique(),
            "median_price": df["listed_price_inr"].median(),
            "median_km": df["km_driven"].median(),
        }
    )

summary = pd.DataFrame(summary_rows)
summary

# %%
def count_table(df, column, top_n=15):
    out = (
        df[column]
        .fillna("missing")
        .astype(str)
        .value_counts()
        .head(top_n)
        .rename_axis(column)
        .reset_index(name="rows")
    )
    out["share_pct"] = out["rows"] / len(df) * 100
    return out


count_table(combined, "source")

# %%
plt.figure(figsize=(10, 5))
source_counts = count_table(combined, "source")
sns.barplot(data=source_counts, x="rows", y="source", color="#2f6f9f")
plt.title("Combined Dataset: Source Mix")
plt.xlabel("Rows")
plt.ylabel("Source")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "combined_source_mix.png", dpi=160)
plt.show()

# %% [markdown]
# ## 2. Missing Values

# %%
required_cols = [
    "source",
    "city",
    "brand",
    "model",
    "model_year",
    "fuel_type",
    "transmission",
    "km_driven",
    "listed_price_inr",
]

def missing_report(df):
    report = df.isna().sum().to_frame("missing").reset_index()
    report = report.rename(columns={"index": "column"})
    report["missing_pct"] = report["missing"] / len(df) * 100
    return report.sort_values(["missing_pct", "missing"], ascending=False)


missing_report(combined).head(20)

# %%
pd.DataFrame(
    {
        name: df[required_cols].isna().sum()
        for name, df in datasets.items()
    }
)

# %% [markdown]
# ## 3. Price Distribution

# %%
for name, df in datasets.items():
    print(
        name,
        {
            "min": int(df["listed_price_inr"].min()),
            "p25": int(df["listed_price_inr"].quantile(0.25)),
            "median": int(df["listed_price_inr"].median()),
            "p75": int(df["listed_price_inr"].quantile(0.75)),
            "p95": int(df["listed_price_inr"].quantile(0.95)),
            "max": int(df["listed_price_inr"].max()),
        },
    )

# %%
plot_df = pd.concat(
    [
        live.assign(dataset="live"),
        external.assign(dataset="external_true_value"),
    ],
    ignore_index=True,
)

plt.figure(figsize=(11, 5))
sns.histplot(
    data=plot_df,
    x="listed_price_inr",
    hue="dataset",
    bins=60,
    element="step",
    stat="density",
    common_norm=False,
)
plt.xlim(0, plot_df["listed_price_inr"].quantile(0.99))
plt.title("Price Distribution: Live vs External")
plt.xlabel("Listed Price INR")
plt.ylabel("Density")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "price_distribution_live_vs_external.png", dpi=160)
plt.show()

# %% [markdown]
# ## 4. Kilometers, Year, And Age

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

plt.tight_layout()
plt.savefig(FIGURE_DIR / "km_and_year_live_vs_external.png", dpi=160)
plt.show()

# %% [markdown]
# ## 5. City And Brand-Model Coverage

# %%
count_table(combined, "city", top_n=20)

# %%
top_brand_models = count_table(combined, "brand_model", top_n=25)
top_brand_models

# %%
plt.figure(figsize=(10, 8))
sns.barplot(data=top_brand_models, x="rows", y="brand_model", color="#496f5d")
plt.title("Top Brand-Model Groups In Combined Dataset")
plt.xlabel("Rows")
plt.ylabel("Brand Model")
plt.tight_layout()
plt.savefig(FIGURE_DIR / "top_brand_models_combined.png", dpi=160)
plt.show()

# %% [markdown]
# ## 6. Price By Important Segments

# %%
def median_price_table(df, group_col, min_rows=20, top_n=20):
    out = (
        df.groupby(group_col)
        .agg(rows=("listed_price_inr", "size"), median_price=("listed_price_inr", "median"), median_km=("km_driven", "median"))
        .query("rows >= @min_rows")
        .sort_values("rows", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return out


median_price_table(combined, "brand_model", min_rows=30, top_n=20)

# %%
segment_cols = ["dataset_origin", "source", "fuel_type", "transmission", "ownership"]
for col in segment_cols:
    if col in combined.columns:
        display(median_price_table(combined, col, min_rows=10, top_n=20))

# %% [markdown]
# ## 7. Outlier Review

# %%
outlier_cols = [
    "dataset_origin" if "dataset_origin" in combined.columns else "source",
    "source",
    "city",
    "brand",
    "model",
    "variant",
    "model_year",
    "fuel_type",
    "transmission",
    "km_driven",
    "listed_price_inr",
    "listing_url",
]

high_price = combined.sort_values("listed_price_inr", ascending=False)[outlier_cols].head(20)
high_km = combined.sort_values("km_driven", ascending=False)[outlier_cols].head(20)

display(high_price)
display(high_km)

# %% [markdown]
# ## 8. Dataset Origin Bias
#
# This is the most important combined-dataset check. The combined model has more rows,
# but it mixes 2021 historical external data with 2026 scraped market data.

# %%
if "dataset_origin" in combined.columns:
    origin_summary = (
        combined.groupby("dataset_origin")
        .agg(
            rows=("listed_price_inr", "size"),
            median_price=("listed_price_inr", "median"),
            median_km=("km_driven", "median"),
            median_model_year=("model_year", "median"),
            unique_cities=("city", "nunique"),
            unique_brand_models=("brand_model", "nunique"),
        )
        .reset_index()
    )
    display(origin_summary)

# %%
if "dataset_origin" in combined.columns:
    plt.figure(figsize=(11, 5))
    sns.boxplot(data=combined, x="dataset_origin", y="listed_price_inr")
    plt.ylim(0, combined["listed_price_inr"].quantile(0.99))
    plt.title("Price Distribution By Dataset Origin")
    plt.xlabel("")
    plt.ylabel("Listed Price INR")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "price_by_dataset_origin.png", dpi=160)
    plt.show()

# %% [markdown]
# ## 9. EDA Decision Summary

# %%
eda_decision = {
    "live_rows": len(live),
    "external_true_value_rows": len(external),
    "combined_rows": len(combined),
    "live_duplicate_keys": len(live) - live["listing_key"].nunique(),
    "external_duplicate_keys": len(external) - external["listing_key"].nunique(),
    "combined_duplicate_keys": len(combined) - combined["listing_key"].nunique(),
    "combined_has_lineage_columns": all(
        col in combined.columns
        for col in ["dataset_origin", "market_snapshot_year", "original_listing_key"]
    ),
    "recommended_next_step": (
        "Train the same baseline ML pipeline on all three datasets and compare metrics by "
        "dataset_origin, source, city, brand_model, fuel_type, and model_year."
    ),
}

eda_decision

# %%
pd.DataFrame([eda_decision]).to_csv(OUTPUT_ROOT / "eda_decision_summary.csv", index=False)
summary.to_csv(OUTPUT_ROOT / "dataset_summary.csv", index=False)
print(f"Saved outputs to: {OUTPUT_ROOT}")
