# %% [markdown]
# # Used Car Price Intelligence - Kaggle Bridge
#
# Purpose:
# - Use Kaggle for EDA, feature checks, model experiments, and report generation.
# - Keep live scraping in the project worker environment unless a small source-specific test is intentional.
#
# Recommended Kaggle workflow:
# 1. Upload selected project artifacts as a Kaggle Dataset.
# 2. Attach that Dataset to this notebook.
# 3. Run analysis and modeling on gold/snapshot artifacts.
# 4. Export reports or model metrics back into the project repository.

# %%
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


KAGGLE_INPUT_ROOT = Path("/kaggle/input")
KAGGLE_WORKING_ROOT = Path("/kaggle/working")

# Change this when you create a Kaggle Dataset for the project artifacts.
PROJECT_DATASET_DIR = KAGGLE_INPUT_ROOT / "used-car-price-intelligence-gold"

# Change this after the new GitHub repository exists.
PROJECT_REPO_URL = "https://github.com/<your-github-user>/<your-repo-name>.git"


# %% [markdown]
# ## Locate Project Artifacts
#
# Expected attached dataset layout:
#
# ```text
# /kaggle/input/used-car-price-intelligence-gold/
#   data/gold/collection_ledger/...
#   data/gold/listing_lifecycle/...
#   data/gold/snapshot_diffs/...
#   data/gold/snapshots/...
# ```

# %%
def find_first(root: Path, pattern: str) -> Path:
    matches = sorted(root.rglob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files matched {pattern!r} under {root}")
    return matches[0]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if PROJECT_DATASET_DIR.exists():
    lifecycle_path = find_first(PROJECT_DATASET_DIR, "listing_lifecycle_v0_20260626.json")
    snapshot_diff_path = find_first(PROJECT_DATASET_DIR, "snapshot_20260626_trusted_v2_baseline_diff.json")
    snapshot_manifest_path = find_first(PROJECT_DATASET_DIR, "snapshot_20260626_trusted_v2_manifest.json")
else:
    lifecycle_path = None
    snapshot_diff_path = None
    snapshot_manifest_path = None

print("Dataset found:", PROJECT_DATASET_DIR.exists())
print("Lifecycle:", lifecycle_path)
print("Snapshot diff:", snapshot_diff_path)
print("Snapshot manifest:", snapshot_manifest_path)


# %% [markdown]
# ## Baseline Snapshot Summary

# %%
if lifecycle_path and snapshot_diff_path and snapshot_manifest_path:
    lifecycle = load_json(lifecycle_path)
    snapshot_diff = load_json(snapshot_diff_path)
    snapshot_manifest = load_json(snapshot_manifest_path)

    print("Snapshot:", snapshot_manifest["snapshot_id"])
    print("Lifecycle:", lifecycle["lifecycle_id"])
    print("Unique listing keys:", lifecycle["totals"]["unique_listing_keys"])
    print("Pricing-ready rows:", snapshot_manifest["totals"]["pricing_ready"])
    print("Quarantined rows:", snapshot_manifest["totals"]["quarantined"])
    print("Diff totals:")
    print(json.dumps(snapshot_diff["totals"], indent=2, sort_keys=True))
else:
    print("Attach the project gold artifact dataset before running the analysis cells.")


# %% [markdown]
# ## Source And City Distribution

# %%
def listing_entities_by_source_and_city(lifecycle: dict[str, Any]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for entity in lifecycle.get("listing_entities", []):
        observation = entity.get("latest_observation") or {}
        source = str(entity.get("source") or observation.get("source") or "unknown")
        city = str(observation.get("city") or "unknown")
        counts.setdefault(source, {})
        counts[source][city] = counts[source].get(city, 0) + 1
    return counts


if lifecycle_path:
    source_city_counts = listing_entities_by_source_and_city(lifecycle)
    print(json.dumps(source_city_counts, indent=2, sort_keys=True))


# %% [markdown]
# ## Export A Small Analysis Report
#
# This creates a Kaggle output file that can be downloaded and copied back into the project
# if it is useful for the Medium/LinkedIn/YouTube story.

# %%
def render_kaggle_summary(lifecycle: dict[str, Any], snapshot_manifest: dict[str, Any]) -> str:
    totals = lifecycle.get("totals", {})
    manifest_totals = snapshot_manifest.get("totals", {})
    lines = [
        "# Kaggle Artifact Review",
        "",
        f"Snapshot id: `{snapshot_manifest.get('snapshot_id', '')}`",
        f"Lifecycle id: `{lifecycle.get('lifecycle_id', '')}`",
        f"Pricing-ready rows: {manifest_totals.get('pricing_ready', 0)}",
        f"Quarantined rows: {manifest_totals.get('quarantined', 0)}",
        f"Unique listing keys: {totals.get('unique_listing_keys', 0)}",
        "",
        "## By Source And City",
        "",
        "| Source | City | Listing Keys |",
        "| --- | --- | ---: |",
    ]
    for source, city_counts in sorted(listing_entities_by_source_and_city(lifecycle).items()):
        for city, count in sorted(city_counts.items()):
            lines.append(f"| {source} | {city} | {count} |")
    lines.append("")
    return "\n".join(lines)


if lifecycle_path and snapshot_manifest_path:
    report = render_kaggle_summary(lifecycle, snapshot_manifest)
    output_path = KAGGLE_WORKING_ROOT / "used_car_price_intelligence_kaggle_summary.md"
    output_path.write_text(report, encoding="utf-8")
    print(output_path)


# %% [markdown]
# ## Optional Repo Install Cell
#
# Use this only after the GitHub repository exists and you want to run project code in Kaggle.
# Keep live scraping disabled by default. Use this notebook primarily for analysis and modeling.
#
# ```python
# !git clone {PROJECT_REPO_URL} /kaggle/working/used-car-price-intelligence
# %cd /kaggle/working/used-car-price-intelligence
# !pip install -q -e .
# ```
