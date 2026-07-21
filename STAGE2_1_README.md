# Stage2.1 — Dual-archive tail optimization

## Purpose

Stage2 found a reproducible, strongly damped trajectory that remained inside the ±40 mm box, but it did not satisfy the unchanged strict gate:

- final three samples inside the ±30 mm R/Z box;
- terminal velocity ≤ 0.10 m/s;
- late-window velocity RMS ≤ 0.10 m/s;
- terminal Ip error within ±10 kA.

Stage2.1 remains in the **low-dimensional real-TSC trajectory-optimization stage**. It does not start behavior cloning or residual RL.

## What is unchanged

- exact Stage1.1 TSC/RZIP runtime and start state;
- 100 ms horizon, 10 steps, 10 ms per step;
- first three validated SVD control modes;
- five nodes at steps `[0, 2, 4, 6, 9]`;
- current limits, ±3 A per 10 ms slew realization and action repair;
- deterministic real-TSC evaluation;
- strict/relaxed hard gates;
- 192-way Ray execution and prompt temporary-workspace cleanup.

## What changes

### 1. Smooth strict-boundary objective

The hard gate is not relaxed. The continuous ranking objective now measures, over the final five samples:

- mean squared excess outside the ±30 mm box;
- maximum squared excess outside the ±30 mm box;
- terminal squared excess outside the ±30 mm box.

Consequently, a 31 mm terminal coordinate is continuously better than 32 mm, which is continuously better than 39 mm. The discrete trailing-streak deficit remains, but its weight is much smaller.

### 2. Two independent archives

Stage2.1 keeps two solution families independently:

- **damped archive**: speed-safe candidates close to or inside the 40 mm box;
- **precise archive**: candidates reaching the 30 mm position box even if they are underdamped.

Tier spacing can no longer delete the precise-but-underdamped family from the search distribution.

### 3. Explicit front/tail bridges

Bridge proposals combine:

- the early drive from a precise candidate;
- the late braking nodes from a damped candidate.

Several crossover forms are used. This directly searches for the missing position–damping compromise rather than hoping a single Gaussian discovers it.

### 4. Final-nine-variable emphasis

The first two nodes receive only small perturbations. Most variation is placed on nodes 4, 6 and 9:

```text
3 modes × 3 final nodes = 9 primary local-search variables
```

Each generation also includes 18 exact ± finite-difference probes: two signs for each of those nine variables.

### 5. Velocity surrogate is conditional and non-authoritative

A pure-NumPy ridge model is fitted from the completed Stage2 real-TSC data. It predicts terminal velocity and late velocity RMS only for proposal ranking.

It is activated only if leave-one-generation-out validation satisfies the configured R² and MAE thresholds. If validation fails, Stage2.1 automatically falls back to the linear position prefilter plus unranked sampling. The surrogate never declares a gate pass.

### 6. More unranked real-TSC proposals

Half of most proposal families are retained without position-model ranking; the random-tail family is completely unranked. This addresses Stage2's observation that the linear position prefilter systematically favored accurate but underdamped trajectories.

## Package relationship to the repository

This zip is a **complete Stage2.1 overlay** for the existing `feat2-cem` branch. It intentionally imports and reuses the unchanged, validated Stage2 environment loader, decoder and real-TSC evaluator:

```python
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
```

Do not apply it to an old B99-only checkout. First use the repository state containing the `feat2-cem` Stage2 implementation.

## Installation

From the repository root:

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib

./run_stop_stage2_now.sh 2>/dev/null || true
ray stop --force 2>/dev/null || true

unzip -o /path/to/stage2_1_dual_archive_tail_optimization.zip \
  -d /home/yangshen0711/tsc_all/tsc_rzip_rllib

chmod +x \
  run_stage2_1_svd3_dual_archive_native.sh \
  run_stage2_1_svd3_dual_archive_nohup.sh \
  run_stage2_1_one_generation_native.sh \
  run_stage2_1_analyze_only.sh \
  run_stage2_1_self_test.sh \
  run_stop_stage2_1_now.sh
```

## Required source runs

Use the completed Stage1.1 and Stage2 runs:

```bash
export SOURCE_STAGE1_1_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage1_1_runs/stage1_1_svd234_strict_validation_100ms_20260718_025916

export SOURCE_STAGE2_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_runs/stage2_svd3_real_tsc_cem_100ms_20260720_114614
```

Stage2.1 validates that target, horizon, node layout, mode count and every hard-gate threshold match the source Stage2 run.

## Run

Start one completely new Stage2.1 optimization:

```bash
./run_stage2_1_svd3_dual_archive_nohup.sh
```

Watch the log:

```bash
LOG_FILE=$(cat logs/nohup/latest_stage2_1_svd3_dual_archive.log)
tail -f "$LOG_FILE"
```

Find the new run directory:

```bash
cat stage2_1_runs/latest_stage2_1_run.txt
```

The default run performs:

1. up to eight generations of 192 real-TSC candidates;
2. three repeat confirmations of the top five unique candidates;
3. final analysis and report generation.

## Optional self-test before the expensive run

```bash
./run_stage2_1_self_test.sh
```

This checks Python syntax, JSON syntax, smooth-tube monotonicity, bridge semantics and surrogate feature construction. It does not run gotsc.

## Stop immediately

```bash
./run_stop_stage2_1_now.sh
```

This stops the Stage2.1 driver, stops Ray, and clears Stage2/Stage2.1 temporary runtime directories below `/tmp/tsc_workspace`. A SIGKILL cannot be intercepted, but already completed candidate JSON files are not corrupted or deleted from the project run directory.

## Output structure

```text
stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_<timestamp>/
├── stage2_1_manifest.json
├── stage2_1_state.json
├── stage2_1_generations/
├── stage2_1_evaluations/
├── stage2_1_confirmations/
├── stage2_1_analysis/
├── stage2_1_best/
├── source_stage2_reference/
└── STAGE2_1_REPORT.md
```

Important outputs:

- `stage2_1_state.json`: distributions, archives, current generation and stop state;
- `stage2_1_analysis/all_generation_results.csv`: all Stage2.1 candidates;
- `stage2_1_analysis/hall_of_fame.csv`: unique candidates ranked by the unchanged gate tiers and new continuous objective;
- `stage2_1_confirmations/stage2_1_verdict.json`: confirmed strict/relaxed verdict;
- `stage2_1_best/best_candidate.json`: current best candidate;
- `STAGE2_1_REPORT.md`: final summary.

## Verdict meanings

- `PASS_PRECISE_HOLD_30MM_CONFIRMED`: every repeat of at least one candidate passes the unchanged strict gate;
- `PASS_DAMPED_HOLD_40MM_CONFIRMED_ONLY`: no strict candidate is confirmed, but at least one candidate repeats the 40 mm damped hold;
- `NO_CONFIRMED_HOLD`: neither condition is reproduced.

## Honest validation boundary

The package has been checked with:

- Python compilation;
- shell syntax checks;
- JSON parsing;
- unit tests for dual archives, bridge semantics and smooth boundary ranking;
- a manifest-generation integration test using all 1536 uploaded Stage2 rows, producing exactly 192 unique candidates with the configured family quotas;
- leave-one-generation-out surrogate validation on the uploaded Stage2 results.

It has **not** been run here against your gotsc executable or through a full 192-worker real-TSC generation. That final runtime validation must occur on your server.
