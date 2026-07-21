# Stage2.1 standalone changelog

## JSON-safe confirmation correction

The prior build could finish all optimization generations and then fail at the
first confirmation result write with:

```text
ValueError: Out of range float values are not JSON compliant: nan
```

Root cause: generation summaries did not copy the linear predicted terminal
R/Z/Ip fields, while confirmation used `_as_float(missing)` and inserted NaN
into the rollout spec.  The spec was embedded in the returned TSC result and
rejected by the strict Stage1 gzip JSON writer.

Corrections:

1. recompute finite linear diagnostics from the selected vector when building
   every confirmation spec;
2. preserve predicted terminal R/Z/Ip in generation summaries;
3. represent unavailable surrogate predictions as `null`, not NaN;
4. make every Stage2.1 JSON writer strict (`allow_nan=False` through the shared
   serializer);
5. preflight all generation and confirmation specs before Ray/TSC launch;
6. validate every recorded environment scalar, current vector and action for
   finiteness;
7. persist an unexpected non-serializable worker result as a failed candidate
   instead of terminating the entire wave;
8. normalize legacy NaN tokens to null when reading old Stage2.1 files so a
   completed failed run can continue directly with confirmation;
9. use null for empty confirmation statistics;
10. remove temporary atomic-write files after errors and at evaluation start.

No search parameter, hard-gate threshold or scientific ranking weight changed.

## Packaging correction

This release replaces the earlier incomplete overlay and Git-dependent installer. It is built from the uploaded `stage2.zip` that produced the completed Stage2 results and physically includes every Stage2/Stage1/environment module Stage2.1 imports.

There is no `.git`, online-download or `STAGE2_1_BASE_TREE` dependency.

## Included Stage2 base

- `configs/stage2_svd3_real_tsc_cem_100ms.json`
- `scripts/stage2_trajectory_optimization.py`
- `tests/test_stage2_trajectory_optimization.py`
- `tsc_rzip_rllib/core/*`
- `tsc_rzip_rllib/envs/*`
- `tsc_rzip_rllib/utils/*`
- `tsc_rzip_rllib/diagnostics/stage1_controllability.py`
- `tsc_rzip_rllib/diagnostics/stage2_trajectory_optimization.py`
- all original Stage2 launchers and documentation.

## New Stage2.1 files

- `configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json`
- `scripts/stage2_1_trajectory_optimization.py`
- `scripts/stage2_1_shell_common.sh`
- `tsc_rzip_rllib/diagnostics/stage2_1_trajectory_optimization.py`
- `tests/test_stage2_1_trajectory_optimization.py`
- `run_stage2_1_svd3_dual_archive_native.sh`
- `run_stage2_1_svd3_dual_archive_nohup.sh`
- `run_stage2_1_one_generation_native.sh`
- `run_stage2_1_confirm_only.sh`
- `run_stage2_1_analyze_only.sh`
- `run_stage2_1_self_test.sh`
- `run_stage2_1_verify_package.sh`
- `run_stop_stage2_1_now.sh`

## Search and objective changes

1. Preserve the original Stage2 hard gate exactly.
2. Add smooth final-window mean/max/terminal excess outside the 30 mm box.
3. Maintain damped and precise-but-underdamped archives independently.
4. Require the damped archive to obey the exact 0.10 m/s speed limits; no margin is used.
5. Rank precise candidates with explicit terminal- and late-velocity penalties.
6. Preserve the original Stage2 winner and the closest speed-safe strict-boundary candidate as explicit anchors.
7. Generate precise-front/damped-tail bridge candidates.
8. Concentrate local variance on nodes 4, 6 and 9.
9. Add 18 real-TSC ± finite-difference tail probes per generation.
10. Center those probes on the truly speed-safe candidate closest to the strict boundary.
11. Retain more candidates without position-model ranking.
12. Use a cross-validated pure-NumPy velocity surrogate for ranking only.
13. Confirm five candidates three times and require all repeats for strict confirmation.

## Runtime and safety changes

- launchers discover complete Stage2 and Stage1.1 sources locally;
- explicit source paths remain supported;
- new runs refuse non-empty output directories unless resume is explicit;
- nohup uses a separate process group and stores its leader PID;
- the stop script terminates the process group and guards every cleanup path below `/tmp`;
- project result directories are never deleted by runtime cleanup.
