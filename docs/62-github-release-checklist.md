# GitHub Release Checklist

Date: 2026-06-29

Use this checklist before publishing the repository.

## Required Files

- [x] `README.md` is portfolio-facing and concise.
- [x] `docs/60-final-github-package.md` records final project status.
- [x] `docs/61-final-model-card.md` records final model trust boundaries.
- [x] `docs/63-pre-github-release-audit.md` records final blind-spot review.
- [x] `notebooks/README.md` gives the notebook reading path.
- [x] final EDA notebook is present.
- [x] complete modeling story notebook is present.
- [x] model interpretation notebook is present.
- [x] repeated-split validation notebook is present.
- [x] README figures are stored under `docs/assets/`.
- [x] `LICENSE` is present for code and documentation.

## Required Claims

- [x] Claim 9.88% MAPE only as the primary split checkpoint.
- [x] Claim 10.33% MAPE as the repeated-split mean.
- [x] Describe the model as a 10%-class model.
- [x] Mention `usable_with_warning` status.
- [x] Mention premium/high-price and rare brand-model limitations.
- [x] Do not claim guaranteed sub-10% MAPE across all splits.
- [x] Do not describe the model as a finished commercial valuation system.

## Git Hygiene

- [x] `.gitignore` excludes generated data, model artifacts, and notebook outputs.
- [x] CSV datasets are kept out of Git and handled through Kaggle upload.
- [x] Notebook `.ipynb` files are clean and output-free.
- [x] Public notebook scripts execute without hanging.
- [x] Small README images are committed because they support project review.
- [x] Run ignore checks and verify generated folders/datasets are ignored.
- [x] Data-use wording separates the code license from dataset redistribution.
- [ ] Stage only code, docs, configs, clean notebooks, tests, and README assets.
- [ ] Do not stage `.venv/`, `data/`, `memory/`, `notebooks/outputs/`, `__pycache__/`, or CSV datasets.

## Verification Commands

```powershell
python -m py_compile notebooks/used_car_price_intelligence_complete_modeling_story.py notebooks/used_car_price_intelligence_model_interpretation.py
python notebooks/used_car_price_intelligence_complete_modeling_story.py
python notebooks/used_car_price_intelligence_model_interpretation.py
python -m pytest
```

Latest local verification:

```text
pytest: 177 passed
final model MAPE reproduced: 9.8827%
interpretation notebook executed successfully
```

## Suggested Commit Message

```text
Finalize used car price intelligence portfolio package
```

## Suggested GitHub Description

```text
Trusted-source used-car price intelligence platform with data acquisition,
quality gates, EDA, baseline modeling, 10%-class price model, stability
validation, and model interpretation.
```
