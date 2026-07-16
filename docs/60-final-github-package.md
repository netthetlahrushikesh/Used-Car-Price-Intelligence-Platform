# Final GitHub Package

Date: 2026-06-29

## Project Status

The project is ready to package as a GitHub portfolio project.

Current final model position:

- Main candidate: Combined Trusted Lineage Target-Encoded Native HGB
- Primary checkpoint MAPE: 9.88%
- Repeated-split mean MAPE: 10.33%
- Repeated-split MAPE range: 9.88% to 10.73%
- Status: usable with warning

The correct project claim is:

> Built a trusted-source used-car price intelligence pipeline and trained a 10%-class price model, reaching 9.88% MAPE on the primary combined split and 10.33% mean MAPE across repeated validation splits.

Do not claim:

> Guaranteed 9.88% MAPE across all splits.

## Final Dataset Position

The final modeling phase uses three separated datasets:

| Dataset | Rows | Role |
| --- | ---: | --- |
| Live Trusted Market Snapshot | 3,496 | Current-market trusted benchmark |
| External True Value Historical Dataset | 5,614 | Larger historical True Value benchmark |
| Combined Trusted Modeling Dataset | 9,110 | Main experimental dataset with lineage features |

The 103,719-row observation CSV is not the modeling dataset. It is an observation-level scrape history with repeated listing observations. The deduped modeling dataset is the correct supervised-learning dataset.

## GitHub-Facing Notebook Order

| Order | Notebook | Why it matters |
| ---: | --- | --- |
| 1 | `notebooks/used_car_price_intelligence_final_eda.ipynb` | Establishes data quality and model readiness |
| 2 | `notebooks/used_car_price_intelligence_complete_modeling_story.ipynb` | Single reader-friendly modeling narrative that retrains the selected final model once and summarizes stability validation |
| 3 | `notebooks/used_car_price_intelligence_model_interpretation.ipynb` | Final trust layer: feature importance, segment error, price-band error, and example predictions |
| 4 | `notebooks/used_car_price_intelligence_baseline_modeling.ipynb` | Detailed raw-price Random Forest checkpoint |
| 5 | `notebooks/used_car_price_intelligence_log_price_modeling.ipynb` | Detailed target transformation and underprediction checkpoint |
| 6 | `notebooks/used_car_price_intelligence_gradient_boosting_modeling.ipynb` | Detailed premium/high-price-tail checkpoint |
| 7 | `notebooks/used_car_price_intelligence_10_percent_target_modeling.ipynb` | Detailed 9.88% MAPE model candidate checkpoint |
| 8 | `notebooks/used_car_price_intelligence_model_stability_validation.ipynb` | Detailed repeated-split validation checkpoint |

## Final Modeling Results

| Model / Dataset | MAE | MAPE | R2 | Notes |
| --- | ---: | ---: | ---: | --- |
| Raw RF / Combined | 60,826 | 13.66% | 0.857 | First serious baseline |
| Log RF / Combined | 61,943 | 13.48% | 0.847 | Slight MAPE improvement, high-price tail still weak |
| Premium-Weighted HGB / Combined | 56,753 | 11.86% | 0.876 | Better high-price tail model |
| Target-Encoded Native HGB / Combined | 47,389 | 9.88% | 0.897 | Main candidate |
| Target-Encoded Native HGB / Repeated splits | 47,589 mean | 10.33% mean | 0.906 mean | Stability result |

## Known Limitations

The final package should clearly mention these limitations:

- High-price and premium vehicles remain difficult.
- Rare brand-model rows have materially higher error than common rows.
- External True Value rows are easier than live Spinny/MFC rows.
- The model is strongest on normal-market/common-brand-model vehicles.
- Target encoding is powerful and must remain leakage-controlled.
- The project uses trusted/evaluated listing sources only; it intentionally excludes self-listed marketplaces like OLX from the first model.

## Recommended README Story

Use this order:

1. Problem: trustworthy used-car price intelligence needs reliable data first.
2. Data strategy: trusted evaluated sources, no unverified customer listings.
3. Dataset: live, external, and combined datasets kept separated with lineage.
4. Data quality: required modeling fields complete, duplicates controlled.
5. Modeling journey: baseline -> log target -> gradient boosting -> target encoding.
6. Final result: 9.88% primary MAPE, 10.33% repeated-split mean MAPE.
7. Limitations: premium/rare segments still need a separate improvement track.

For GitHub readers, use the complete modeling story notebook as the primary
modeling artifact. It includes one real final-model training run; keep the
stage-specific notebooks as supporting evidence for each experiment stage and
the full repeated-split validation.

Use `docs/61-final-model-card.md` as the final model trust summary. It records
the intended use, inappropriate use, segment limitations, and interpretation
findings.

Use `docs/62-github-release-checklist.md` for the final publish checklist.
Use `docs/63-pre-github-release-audit.md` for the final pre-GitHub blind-spot
review.

## Repository Hygiene

Git should include:

- source code under `src/`
- tests under `tests/`
- configs under `config/`
- clean notebooks under `notebooks/`
- documentation under `docs/`
- dataset upload metadata under `kaggle_upload/`

Git should not include:

- large CSV datasets
- raw scrape payloads
- generated model files
- `notebooks/outputs/`
- local virtual environments

The `.gitignore` already excludes generated data and model artifacts.

## Next Production Step

Move from model development to interpretation and presentation:

1. Create final README visuals/tables from the saved metrics.
2. Prepare a Medium/LinkedIn/YouTube narrative around the data-first process.
3. Keep premium-tail modeling as future work, not as a blocker for the current portfolio release.
