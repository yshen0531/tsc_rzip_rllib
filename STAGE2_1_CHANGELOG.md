# Stage2.1 changelog

## New files

- `configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json`
- `tsc_rzip_rllib/diagnostics/stage2_1_trajectory_optimization.py`
- `scripts/stage2_1_trajectory_optimization.py`
- `run_stage2_1_svd3_dual_archive_native.sh`
- `run_stage2_1_svd3_dual_archive_nohup.sh`
- `run_stage2_1_one_generation_native.sh`
- `run_stage2_1_analyze_only.sh`
- `run_stage2_1_self_test.sh`
- `run_stop_stage2_1_now.sh`
- `tests/test_stage2_1_trajectory_optimization.py`

## Algorithm changes

1. Warm-starts from the completed Stage2 population and CEM state without modifying the source run.
2. Preserves the Stage2 hard gate exactly.
3. Replaces the plateau-like strict-boundary ranking with smooth mean/max/terminal 30 mm tube excess.
4. Maintains damped and precise-but-underdamped archives independently.
5. Generates explicit precise-front/damped-tail crossover candidates.
6. Concentrates local variation on the final three time nodes while keeping small early-node exploration.
7. Adds eighteen real-TSC finite-difference probes per generation for the nine tail variables.
8. Raises unranked proposal coverage to avoid repeating the Stage2 linear-prefilter bias.
9. Adds an optional, cross-validated pure-NumPy velocity surrogate used only for proposal ordering.
10. Confirms five candidates three times; strict confirmation requires all repeats to pass.

## Runtime/storage behavior

- `/tmp/tsc_workspace` remains the temporary runtime root.
- Candidate episode directories are cleaned by the inherited Stage2 evaluator.
- Ray actors are closed before forced termination through the inherited evaluator.
- New optimization results remain under `stage2_1_runs/` and are not removed by temporary cleanup.
