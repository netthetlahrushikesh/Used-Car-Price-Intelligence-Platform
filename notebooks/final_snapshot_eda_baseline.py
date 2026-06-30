# %% [markdown]
# # Used Car Price Intelligence - Final Snapshot EDA And Baseline
#
# Purpose:
# - Review the packaged dataset from `snapshot_20260627_final_spinny_mfc_try`.
# - Inspect EDA and baseline model outputs without running live scrapers.
# - Create story-friendly summary text for documentation, Medium, LinkedIn, and YouTube.

# %%
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


LOCAL_PROJECT_ROOT = Path.cwd()
LOCAL_MODELING_DIR = (
    LOCAL_PROJECT_ROOT
    / "data"
    / "gold"
    / "modeling"
    / "snapshot_20260627_final_spinny_mfc_try_modeling_v0"
)
KAGGLE_MODELING_DIR = (
    Path("/kaggle/input")
    / "used-car-price-intelligence-gold"
    / "data"
    / "gold"
    / "modeling"
    / "snapshot_20260627_final_spinny_mfc_try_modeling_v0"
)
IS_KAGGLE = Path("/kaggle/working").exists()
WORKING_ROOT = Path("/kaggle/working") if IS_KAGGLE else LOCAL_PROJECT_ROOT


# %% [markdown]
# ## Locate Packaged Artifacts

# %%
def first_existing_path(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("Run package-modeling-dataset locally or attach the Kaggle dataset first.")


MODELING_DIR = first_existing_path(LOCAL_MODELING_DIR, KAGGLE_MODELING_DIR)

dataset_csv = MODELING_DIR / "listings_modeling_dataset.csv"
manifest_json = MODELING_DIR / "dataset_manifest.json"
eda_json = MODELING_DIR / "eda_summary.json"
baseline_json = MODELING_DIR / "baseline_model.json"

print("Modeling directory:", MODELING_DIR)
print("Dataset CSV:", dataset_csv)


# %% [markdown]
# ## Load Data

# %%
def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as file_obj:
        return list(csv.DictReader(file_obj))


manifest = load_json(manifest_json)
eda_summary = load_json(eda_json)
baseline = load_json(baseline_json)
rows = load_csv_rows(dataset_csv)

print("Dataset:", manifest["dataset_id"])
print("Snapshot:", manifest["snapshot_id"])
print("Rows:", len(rows))
print("Validation:", manifest["validation"]["status"])


# %% [markdown]
# ## Source, City, And Brand Mix

# %%
def show_count_table(summary: dict[str, Any], key: str, limit: int = 15) -> None:
    print(key)
    for item in summary["counts"][key][:limit]:
        print(f"  {item['value']}: {item['count']} ({item['share_pct']:.2f}%)")


show_count_table(eda_summary, "source")
show_count_table(eda_summary, "city", limit=10)
show_count_table(eda_summary, "brand_model", limit=10)


# %% [markdown]
# ## Price And Usage Summary

# %%
for field in ["listed_price_inr", "price_lakh", "km_driven", "vehicle_age_years"]:
    stats = eda_summary["numeric_summary"][field]
    print(
        field,
        "count=", stats["count"],
        "median=", stats["median"],
        "p25=", stats["p25"],
        "p75=", stats["p75"],
    )


# %% [markdown]
# ## Baseline Model Review

# %%
metrics = baseline["metrics"]
global_metrics = baseline["global_median_metrics"]

print("Train rows:", baseline["split"]["train_rows"])
print("Test rows:", baseline["split"]["test_rows"])
print("Comparable median MAE:", metrics["mae"])
print("Comparable median MAPE:", metrics["mape"])
print("Comparable median within 20%:", metrics["within_20_pct"])
print("Global median MAE:", global_metrics["mae"])
print("Global median MAPE:", global_metrics["mape"])


# %% [markdown]
# ## Blind Spots To Mention In The Story

# %%
for warning in eda_summary["blind_spots"]["warnings"]:
    print("-", warning)
for blocker in eda_summary["blind_spots"]["blocking"]:
    print("- BLOCKING:", blocker)


# %% [markdown]
# ## Export Story Summary

# %%
def render_story_summary() -> str:
    source_counts = ", ".join(
        f"{item['value']} {item['count']}" for item in eda_summary["counts"]["source"]
    )
    lines = [
        "# Final Snapshot Story Summary",
        "",
        f"Dataset: `{manifest['dataset_id']}`",
        f"Snapshot: `{manifest['snapshot_id']}`",
        f"Rows: {manifest['records_total']:,}",
        f"Sources: {source_counts}",
        "",
        "## Baseline Result",
        "",
        f"- Train rows: {baseline['split']['train_rows']:,}",
        f"- Test rows: {baseline['split']['test_rows']:,}",
        f"- Comparable median MAE: {metrics['mae']}",
        f"- Comparable median MAPE: {metrics['mape']}",
        f"- Within 20 percent: {metrics['within_20_pct']}%",
        "",
        "## Main Caveat",
        "",
        "This is a trusted-source, pricing-ready baseline dataset, not the final 100k production model dataset.",
        "The next scale phase should collect repeated snapshots to improve source balance and temporal coverage.",
        "",
    ]
    return "\n".join(lines)


story_output = (WORKING_ROOT if IS_KAGGLE else MODELING_DIR) / "final_snapshot_story_summary.md"
story_output.write_text(render_story_summary(), encoding="utf-8")
print(story_output)
