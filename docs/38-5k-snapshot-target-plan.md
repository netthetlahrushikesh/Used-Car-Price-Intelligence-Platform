# 5k Snapshot Target Plan

Date: 2026-06-26

Status: historical planning document. The active checkpoint is now [Final Spinny/MFC Try and Phase-Final Snapshot](47-final-spinny-mfc-try-and-phase-final-snapshot.md): `snapshot_20260627_final_spinny_mfc_try`, 3,492 pricing-ready rows, 0 quarantine, final for this acquisition phase.

## Decision

Use 5,000 trusted rows per snapshot as the first production-scale target.

Do not jump directly to 10,000 rows per snapshot. Treat 10,000 as a stretch target after the 5,000-row plan is stable.

## Current Baseline

| Metric | Count |
| --- | ---: |
| Original baseline snapshot | `snapshot_20260626_trusted_v2_baseline` |
| Original baseline trusted observations | 909 |
| Current anchor snapshot | `snapshot_20260626_2500_target_met` |
| Current trusted observations | 2,796 |
| Latest 5k progress snapshot | `snapshot_20260627_true_value_buffer` |
| Latest trusted observations | 3,278 |
| Target observations | 100,000 |
| Remaining observations | 96,722 |
| Gap to first 5k snapshot | 1,722 |

## Snapshot Size Projection

| Scenario | Rows Per Future Snapshot | Future Snapshots Needed | Total Snapshots Including Current |
| --- | ---: | ---: | ---: |
| Current checkpoint size | 3,278 | 30 | 31 |
| Original baseline scope | 909 | 107 | 108 |
| Small scale | 2,500 | 39 | 40 |
| Recommended | 5,000 | 20 | 21 |
| Stretch | 10,000 | 10 | 11 |

## Recommended 5k Source Allocation

| Source | Target Rows Per Snapshot | Share | Role |
| --- | ---: | ---: | --- |
| True Value | 2,500 | 50% | First expansion lane |
| Mahindra First Choice | 1,500 | 30% | Multi-brand expansion lane |
| Spinny | 1,000 | 20% | Quality anchor |

This allocation is a target, not a guarantee. Actual rows depend on source inventory, city coverage, and quality gates.

Current source gap from `snapshot_20260626_2500_target_met`:

| Source | Current Rows | Allocation Gap | Current Decision |
| --- | ---: | ---: | --- |
| True Value | 2,448 | 52 | Near allocation; reserve only for final capped buffer after Spinny and MFC attempts. |
| Mahindra First Choice | 179 | 1,321 | Probe more cities first. |
| Spinny | 320 | 680 | Incremental-detail probe is manifest-backed; use this path for future targeted expansion. |

Historical update: the True Value buffer checkpoint `snapshot_20260627_true_value_buffer` moved the total to 3,278 pricing-ready rows. True Value increased to 2,448 rows after five new capped city runs, leaving a 1,722-row total gap to 5k.

Final update: the final Spinny/MFC attempt moved the phase-final checkpoint to `snapshot_20260627_final_spinny_mfc_try` with 3,492 pricing-ready rows and 0 quarantine. The current phase stops there and moves to dataset packaging, EDA, and baseline modeling.

## Why 5k Is The Right First Production Target

5,000 rows per snapshot is large enough to make the 100k goal practical while still small enough to debug quality and lifecycle problems.

At 5,000 rows per future snapshot:

- remaining target needs about 20 future snapshots,
- source pressure stays reasonable,
- True Value can carry more volume,
- Mahindra First Choice adds multi-brand coverage,
- Spinny stays valuable without letting detail-page latency dominate the whole pipeline.

## Required Path

Completed:

1. Repeated the 909-row source-city baseline.
2. Generated the repeat collection ledger.
3. Generated the repeat lifecycle index.
4. Diffed repeat snapshot against baseline.
5. Expanded to the 2,500-row target.
6. Reached 2,796 pricing-ready rows with 0 quarantined rows.

Current path:

1. Use the manifest-backed Spinny incremental path for future targeted Spinny expansion.
2. Decide whether any additional MFC path exists beyond current public city pages.
3. Avoid large additional True Value batches; the generated strategy reserves True Value for a final capped 52-row buffer.
4. Rebuild collection ledger, lifecycle, diff, and manifest after the next expansion pass.
5. Only after multiple stable 5,000-row snapshots should 10,000 rows per snapshot be attempted.

## Generated Projection Artifact

Historical command from the original 909-row baseline:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli scale-projection --target-id target_100k_trusted_observations_v0 --target-observations 100000 --current-snapshot-manifest data/gold/snapshots/snapshot_20260626_trusted_v2_manifest.json --recommended-rows-per-snapshot 5000 --output-json data/gold/scale_projection/target_100k_5k_snapshot_projection.json --output-md data/gold/scale_projection/target_100k_5k_snapshot_projection.md
```

Current final-for-phase command:

```powershell
$env:PYTHONPATH='src'; python -m used_car_price_intelligence.cli scale-projection --target-id target_100k_trusted_observations_v0 --target-observations 100000 --current-snapshot-manifest data/gold/snapshots/snapshot_20260627_final_spinny_mfc_try_manifest.json --recommended-rows-per-snapshot 5000 --output-json data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.json --output-md data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.md
```

Outputs:

```text
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.json
data/gold/scale_projection/target_100k_5k_snapshot_projection_from_final_spinny_mfc_try.md
```

## Next Engineering Step

Completed next: [5k Target Execution Plan](41-5k-target-execution-plan.md), [Remaining 5k Gap Strategy](46-remaining-5k-gap-strategy.md), and [Final Spinny/MFC Try and Phase-Final Snapshot](47-final-spinny-mfc-try-and-phase-final-snapshot.md).

Immediate next action: package the final trusted dataset for EDA and baseline modeling.
