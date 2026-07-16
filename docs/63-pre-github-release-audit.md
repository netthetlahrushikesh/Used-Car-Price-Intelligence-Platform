# Pre-GitHub Release Audit

Date: 2026-06-30

## Goal

Recheck the project before GitHub publication for technical, documentation,
data-governance, and storytelling blind spots.

## Audit Scope

Checked:

- Git publish surface and ignored files
- generated data and notebook outputs
- large files accidentally visible to Git
- local absolute paths
- credential-like strings
- Markdown links
- notebook output cleanliness
- notebook script execution
- package install metadata
- Python compileability
- unit tests
- final model claims and caveats
- dataset license and redistribution caveats
- explicit code license and data-use separation

## Blind Spots Found And Fixed

### 1. Generated External Profile Was Visible To Git

Finding:

`data/external/profile/...` was still visible as an untracked publish candidate
even though it is generated profiling output.

Fix:

Added `data/external/**` to `.gitignore`.

Decision:

Keep generated external raw/profile/gold data out of Git. Promote only
summaries and decisions into `docs/`.

### 2. Local Absolute Paths In Kaggle Package Manifest

Finding:

`kaggle_upload/used-car-price-intelligence-trusted-modeling-datasets/combined_dataset_manifest.md`
contained local machine-specific Windows paths.

Fix:

Replaced those entries with repository-relative paths under
`data/gold/modeling_experiments/three_model_phase_20260628/`.

Decision:

Public docs and upload package metadata should avoid local machine-specific
paths.

### 3. Final EDA Notebook Hung In Script Mode

Finding:

`python notebooks/used_car_price_intelligence_final_eda.py` did not terminate
within 10 minutes and left a Python process running.

Fix:

Added the same script-safe matplotlib backend guard used by the modeling
notebooks:

```python
import matplotlib

try:
    get_ipython
except NameError:
    matplotlib.use("Agg")
```

Regenerated the clean `.ipynb` version.

Result:

The EDA script now completes locally in about 24 seconds.

### 4. Dataset Redistribution Wording Needed Tightening

Finding:

The external Kaggle dataset license is tracked as `CC0-1.0`, while live scraped
CSV redistribution remains a separate caution.

Fix:

Updated `kaggle_upload/README.md` to state:

- external True Value Kaggle source is recorded as `CC0-1.0`
- live scraped CSVs should stay outside Git and should not be redistributed
  publicly unless source terms permit it

### 5. Code License Was Missing

Finding:

The repository had no explicit code license, which makes GitHub reuse rights
ambiguous even when the work is intended as a public portfolio project.

Fix:

Added `LICENSE` with MIT terms for project code and documentation, and added a
README section clarifying that dataset rights are separate from the code
license.

## Verification Results

Latest checks:

```text
python -m compileall -q src tests notebooks                  pass
python -m pip install -e . --dry-run                         pass
python -m pytest                                             177 passed
notebook output/exec-count check                             pass
markdown local link check                                    pass
large unignored publish-candidate file check                 pass
credential/local-path release-surface scan                   pass
git ignore checks for generated data and CSV datasets         pass
final EDA script execution                                   pass
complete modeling story script execution                     pass
model interpretation script execution                        pass
```

Public notebook script timings from this audit:

| Notebook script | Result |
| --- | --- |
| `used_car_price_intelligence_final_eda.py` | completed |
| `used_car_price_intelligence_complete_modeling_story.py` | completed |
| `used_car_price_intelligence_model_interpretation.py` | completed |

## Remaining Non-Blocking Risks

- Git has not been staged or committed yet; the repo is still a first-commit
  workspace.
- CSV datasets are intentionally ignored, so GitHub readers need the Kaggle
  dataset package to rerun notebooks.
- Live scraped data redistribution should remain conservative unless source
  terms are reviewed.
- The model remains `usable_with_warning`, not production valuation ready.
- Premium/high-price and rare brand-model segments remain future work.

## Go/No-Go

Status: `go_with_cautions`

The repository is ready for a careful first GitHub commit if staging excludes
ignored generated files and follows `docs/62-github-release-checklist.md`.
