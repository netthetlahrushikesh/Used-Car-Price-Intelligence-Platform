# Remaining 5k Gap Strategy

Date: 2026-06-27

Purpose: convert the post-v8 source-mix question into a reproducible decision artifact before collecting more rows.

Status: superseded by [Final Spinny/MFC Try and Phase-Final Snapshot](47-final-spinny-mfc-try-and-phase-final-snapshot.md). This document remains the decision record that led to the final balanced attempt, but it is no longer the active next step.

## Decision

Do not close the remaining 1,722-row gap with a large True Value run.

True Value is now 2,448 rows against a 2,500-row allocation. That leaves only 52 allocation-safe True Value rows. The next collection work should prioritize underrepresented sources first:

1. Spinny incremental expansion pack.
2. Mahindra First Choice source-path discovery.
3. True Value final capped buffer only after the first two lanes are attempted.

## Generated Strategy Artifact

Command:

```powershell
$env:PYTHONPATH='src'; .venv\Scripts\python -m used_car_price_intelligence.cli remaining-gap-strategy --snapshot-manifest data/gold/snapshots/snapshot_20260627_true_value_buffer_manifest.json --target-config config/snapshot_targets.yml --output-json data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.json --output-md data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.md --json
```

Outputs:

```text
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.json
data/gold/gap_strategy/remaining_5k_gap_strategy_from_true_value_buffer.md
```

## Source Allocation Result

| Source | Current Rows | Target Rows | Gap | Status | Next Action |
| --- | ---: | ---: | ---: | --- | --- |
| True Value | 2,448 | 2,500 | 52 | near allocation | Use only as final capped buffer |
| Mahindra First Choice | 510 | 1,500 | 990 | capacity constrained | Research source paths before assuming public city pages can fill the gap |
| Spinny | 320 | 1,000 | 680 | incremental expansion needed | Use manifest-backed incremental detail expansion |

## Recommended Sequence

| Order | Step | Source | Target Rows |
| ---: | --- | --- | ---: |
| 1 | `spinny_incremental_expansion_pack` | Spinny | 200 |
| 2 | `mfc_source_path_discovery` | Mahindra First Choice | 300 |
| 3 | `true_value_final_buffer` | True Value | 52 |
| 4 | `repeat_snapshot_observations` | All trusted sources | 0 |

The first number is intentionally small. A 200-row Spinny pack is enough to prove the incremental workflow beyond Hyderabad without turning the next step into a long unbounded scrape.

## Stop Conditions

- Do not add large True Value batches while True Value is at or above 95% of its allocation.
- Do not promote a source run if required completeness drops below 100%.
- Do not promote a source run with quarantined pricing rows until parser or adapter gaps are fixed.
- Do not double-count a deeper same-source same-city run; replace the older shallower run in the ledger.
- Do not interpret removed listings unless the source-city scope is equivalent to the previous snapshot.

## Next Engineering Step

Completed in [Final Spinny/MFC Try and Phase-Final Snapshot](47-final-spinny-mfc-try-and-phase-final-snapshot.md).

The final attempt replaced the five Spinny hub manifests, added one final MFC capacity batch, kept True Value unchanged, fixed Spinny variant/city-state quality blind spots, and produced `snapshot_20260627_final_spinny_mfc_try` with 3,492 pricing-ready rows and 0 quarantine.
