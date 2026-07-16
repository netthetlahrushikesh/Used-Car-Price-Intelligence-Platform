# Documentation Index

This directory is the project decision log. The latest and most important project status is near the end of the sequence.

## Recommended Review Path

For GitHub, portfolio, or interview review, read these first:

1. [Final GitHub Package](60-final-github-package.md)
2. [Three Model Phase Readiness](53-three-model-phase-readiness.md)
3. [Baseline Modeling Plan](54-baseline-modeling-plan.md)
4. [Baseline Segment Metrics And Source Drift Review](55-baseline-segment-metrics-and-source-drift-review.md)
5. [Log-Price Baseline Review](56-log-price-baseline-review.md)
6. [Gradient Boosting Modeling Review](57-gradient-boosting-modeling-review.md)
7. [10 Percent Target Modeling Review](58-10-percent-target-modeling-review.md)
8. [Model Stability Validation](59-model-stability-validation.md)
9. [Final Model Card](61-final-model-card.md)
10. [GitHub Release Checklist](62-github-release-checklist.md)
11. [Pre-GitHub Release Audit](63-pre-github-release-audit.md)
12. [Stage 2 Model Artifact And API Schema](64-stage2-model-artifact-and-api-schema.md)
13. [Stage 2 Prediction API](65-stage2-prediction-api.md)
14. [Stage 2 Web Prediction Workspace](66-stage2-web-prediction-screen.md)
15. [Stage 2 Web Redesign Review](67-stage2-web-redesign.md)
16. [Vercel Deployment](68-vercel-deployment.md)

## Documentation Map

| Range | Theme | Purpose |
| --- | --- | --- |
| `00`-`13` | Project foundation | Data strategy, architecture, schema design, source selection, parser rules, and risk review |
| `14`-`29` | Live acquisition foundation | Source adapters, smoke workflows, field comparisons, and batch-runner design |
| `30`-`47` | Collection execution | Trusted-source collection runs, dedupe, snapshots, expansion attempts, and final live snapshot |
| `48`-`53` | Dataset packaging | EDA start, high-scale scrape review, identity recheck, external dataset integration, and three-dataset readiness |
| `54`-`63` | Modeling and final package | Baselines, source drift, log-price models, gradient boosting, 10%-class model, stability validation, final GitHub summary, model card, release checklist, and pre-GitHub audit |
| `64`-`68` | Stage 2 product boundary | Model artifact, API schema, prediction service, verified pricing workspace, and Vercel deployment |

## Current Truth

Use [Final GitHub Package](60-final-github-package.md) as the current project
summary and [Final Model Card](61-final-model-card.md) as the current model
trust summary.

The correct final model claim is:

> Built a trusted-source used-car price intelligence pipeline and trained a 10%-class price model, reaching 9.88% MAPE on the primary combined split and 10.33% mean MAPE across repeated validation splits.

The current Stage 2 product boundary is documented in
[Stage 2 Web Redesign Review](67-stage2-web-redesign.md). The earlier files
remain useful because they show how the project decisions changed as data
quality, deduplication, source trust, modeling evidence, and product constraints
improved.
