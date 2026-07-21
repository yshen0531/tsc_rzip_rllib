# Stage2.1 — complete standalone dual-archive tail optimizer

## What this package is

This archive is a **complete, directly runnable source tree** built from the exact `stage2.zip` code that produced the completed Stage2 run, plus the Stage2.1 update.

It physically contains:

- the Stage1.1 loader and metrics used by Stage2;
- the Stage2 SVD decoder, linear model, real-TSC evaluator, Ray workers, cleanup code, tests and configuration;
- the complete Stage2.1 optimizer, configuration, launchers, tests and documentation.

It does **not** use or require:

- `.git`;
- `feat2-cem` checkout recovery;
- `STAGE2_1_BASE_TREE`;
- an online download;
- an older `configs/`, `scripts/`, `tests/` or `tsc_rzip_rllib/` directory.

The supported installation workflow is therefore exactly:

```bash
rm -rf configs scripts tests tsc_rzip_rllib
unzip -o stage2_1_complete_standalone_jsonsafe.zip -d /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

## JSON-safety correction in this release

An earlier Stage2.1 build completed all eight 192-candidate generations, then
failed at the first confirmation write because three optional linear-prediction
fields were absent from the historical generation row.  The confirmation code
converted each missing value to `NaN`; the validated Stage1 writer correctly
uses `allow_nan=False`, so the raw result could not be serialized.

This release fixes the root cause and adds defense in depth:

- confirmation recomputes finite linear predictions directly from the selected
  parameter vector;
- generation rows now retain those predictions explicitly;
- unavailable surrogate predictions are stored as JSON `null`, never `NaN`;
- all Stage2.1 JSON/checkpoint writers use strict standards-compliant JSON;
- evaluation specs are validated before Ray/TSC starts;
- non-finite TSC state values are converted into a candidate failure, rather
  than crashing the full evaluation wave;
- an unexpected non-serializable worker result is saved as a diagnostic failure
  record and the remaining candidates continue;
- legacy Stage2.1 JSON files containing Python `NaN` tokens can be read and
  normalized, allowing the failed completed run to proceed directly to
  confirmation;
- failed atomic writes remove their temporary files.

The 30 mm/velocity/Ip gate and the Stage2.1 search objective are unchanged by
this correction.

## Scientific position of Stage2.1

Stage2 found reproducible damping inside the ±40 mm box but did not satisfy the unchanged strict gate. Stage2.1 remains in the low-dimensional, real-TSC trajectory-optimization phase. It does not start behavior cloning, DAgger or residual RL.

The strict success definition is unchanged:

- final three samples inside the ±30 mm R/Z box;
- terminal velocity no greater than 0.10 m/s;
- late-window velocity RMS no greater than 0.10 m/s;
- terminal Ip error within ±10 kA.

## What is unchanged from the successful Stage2 code

- exact Stage1.1/TSC runtime loading path;
- 100 ms horizon, ten 10 ms control steps;
- first three validated SVD modes;
- five nodes at steps `[0, 2, 4, 6, 9]`;
- 15 optimization variables;
- mode decoding into the 14 physical CSPF channels;
- current limits, slew realization and action repair;
- deterministic real-TSC evaluation;
- Stage2 hard-gate tiers;
- candidate-result atomic files and resume behavior;
- Ray evaluation and prompt cleanup below `/tmp/tsc_workspace`.

## Stage2.1 changes

### Smooth 30 mm boundary objective

The hard gate remains discrete and unchanged. Within each hard-gate tier, the continuous objective now measures the mean, maximum and terminal squared excess outside the ±30 mm box over the final five samples. Thus 31 mm ranks continuously ahead of 32 mm, which ranks ahead of 39 mm.

### Two independently retained solution families

- **Damped archive:** candidates that satisfy the actual terminal and late velocity limits, remain close to the target, and satisfy Ip safety.
- **Precise archive:** candidates that reach the 30 mm position box, including underdamped candidates.

The damped archive now uses the exact 0.10 m/s limits; it no longer admits a 5% speed margin. The precise archive score also penalizes terminal and late velocity so that near-damped precise trajectories are ranked ahead of equally precise but strongly underdamped ones.

### Explicit precise-front / damped-tail bridges

Bridge candidates combine early drive from a precise candidate with late braking from a damped candidate. Several crossover layouts are sampled instead of relying on one Gaussian distribution to discover this compromise accidentally.

### Tail-focused local search

Most perturbation is applied to nodes 4, 6 and 9:

```text
3 modes × 3 final nodes = 9 primary local variables
```

Each generation includes 18 real-TSC finite-difference probes: positive and negative perturbations for all nine tail variables. The probe center is the **truly speed-safe candidate closest to the 30 mm boundary**, not merely the first archive row.

### Protected anchors

Every generation explicitly preserves:

- the original Stage2 winner;
- the speed-safe candidate closest to the strict boundary;
- the leading damped candidate;
- the leading precise candidate;
- the current Stage2.1 winner once one exists;
- additional diverse archive members and SVD3 reference seeds.

### Conditional velocity surrogate

A pure-NumPy ridge model predicts terminal velocity and late velocity RMS for proposal ordering only. It is activated only after leave-one-generation-out validation passes configured R² and MAE thresholds. It never determines a hard gate and automatically disables itself if validation becomes inadequate.

### More unranked proposals

Half of most proposal families bypass position-model ranking; the random-tail family is completely unranked. This directly addresses Stage2's observed bias toward position-accurate but underdamped candidates.

## Candidate composition per generation

```text
anchors          12
sensitivity      18
damped_tail      36
precise_tail     24
bridge           48
global           18
random_tail      36
-------------------
total           192
```

The default run performs up to eight generations, followed by three confirmation repeats for each of the top five unique candidates.

## Installation

Run these commands from the repository/project directory:

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib

./run_stop_stage2_1_now.sh 2>/dev/null || true
./run_stop_stage2_now.sh 2>/dev/null || true
ray stop --force 2>/dev/null || true

rm -rf configs scripts tests tsc_rzip_rllib

unzip -o /path/to/stage2_1_complete_standalone_jsonsafe.zip \
  -d /home/yangshen0711/tsc_all/tsc_rzip_rllib

chmod +x \
  run_stage2_1_svd3_dual_archive_native.sh \
  run_stage2_1_svd3_dual_archive_nohup.sh \
  run_stage2_1_one_generation_native.sh \
  run_stage2_1_confirm_only.sh \
  run_stage2_1_analyze_only.sh \
  run_stage2_1_self_test.sh \
  run_stage2_1_verify_package.sh \
  run_stop_stage2_1_now.sh
```

The zip preserves executable bits, but the `chmod` command is harmless and avoids differences between unzip implementations.

## Source-run selection

The launcher can run directly without exports. It searches in this order.

For Stage2:

1. `SOURCE_STAGE2_RUN`;
2. `stage2_runs/latest_stage2_run.txt`;
3. the newest complete `stage2_runs/stage2_svd3_real_tsc_cem_100ms_*` directory.

For Stage1.1:

1. `SOURCE_STAGE1_1_RUN`;
2. `source_stage1_1_run` in the selected Stage2 manifest;
3. `stage1_1_runs/latest_stage1_1_run.txt`;
4. the newest complete Stage1.1 run directory.

For an unambiguous production run, the explicit paths are still recommended:

```bash
export SOURCE_STAGE1_1_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage1_1_runs/stage1_1_svd234_strict_validation_100ms_20260718_025916

export SOURCE_STAGE2_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_runs/stage2_svd3_real_tsc_cem_100ms_20260720_114614
```

The launcher checks all required source files before creating the optimization state. Stage2.1 also verifies target, horizon, SVD count, node layout, coefficient bounds and every hard-gate threshold against the source Stage2 configuration.

## Static verification before the expensive run

```bash
./run_stage2_1_verify_package.sh
```

This performs no gotsc evaluation. On an untouched extraction it first verifies `SHA256SUMS`, then checks the complete source tree, both Stage2 and Stage2.1 synthetic tests, Python compilation, JSON parsing, Stage2.1 unit tests, shell syntax and the absence of any Git/external-base dependency.

## Start a new full run

```bash
./run_stage2_1_svd3_dual_archive_nohup.sh
```

The default is always a new run. Its directory is written to:

```text
stage2_1_runs/latest_stage2_1_run.txt
```

Its log path is written to:

```text
logs/nohup/latest_stage2_1_svd3_dual_archive.log
```

Follow it with:

```bash
tail -f "$(cat logs/nohup/latest_stage2_1_svd3_dual_archive.log)"
```

## One generation, confirmation and analysis

Run one generation on the latest prepared run:

```bash
./run_stage2_1_one_generation_native.sh
```

Repeat confirmation and regenerate analysis:

```bash
./run_stage2_1_confirm_only.sh
./run_stage2_1_analyze_only.sh
```

To resume a specifically interrupted Stage2.1 run:

```bash
export STAGE2_1_RUN_DIR=/absolute/path/to/the/stage2_1_run
export STAGE2_1_RESUME=1
./run_stage2_1_svd3_dual_archive_native.sh
```

### Recover a run that already completed eight generations and failed only in confirmation

Do **not** rerun the 1536 optimization evaluations.  After installing this
release, point to the existing run and execute confirmation only:

```bash
export STAGE2_1_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_20260720_151221

./run_stage2_1_confirm_only.sh
```

The script reuses all completed generation files, performs the 15 confirmation
rollouts and regenerates analysis.  Stale `*.json.gz.tmp.*` files left by the
old failed write are ignored and removed when that confirmation directory is
opened.

A fresh run refuses to write into a non-empty run directory. Resume must be requested explicitly.

## Stop immediately

```bash
./run_stop_stage2_1_now.sh
```

The stop script terminates the saved process group, Stage2.1 Python processes and Ray, then clears only guarded paths below `/tmp`. It does not delete project results under `stage2_1_runs/`.

## Output structure

```text
stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_<timestamp>/
├── stage2_1_manifest.json
├── stage2_1_config.resolved.json
├── stage2_1_state.json
├── stage2_1_generations/
├── stage2_1_evaluations/
├── stage2_1_confirmations/
├── stage2_1_analysis/
├── stage2_1_best/
├── source_stage2_reference/
└── STAGE2_1_REPORT.md
```

Important outputs include:

- `stage2_1_state.json`: distributions, both archives, generation and stop state;
- `stage2_1_analysis/all_generation_results.csv`: all Stage2.1 evaluations;
- `stage2_1_analysis/hall_of_fame.csv`: unique candidates under the unchanged tiers and new continuous objective;
- `stage2_1_analysis/velocity_surrogate.json`: cross-validation and model activation decision;
- `stage2_1_confirmations/stage2_1_verdict.json`: repeated strict/relaxed verdict;
- `stage2_1_best/best_candidate.json`: current best candidate.

## Verdict meanings

- `PASS_PRECISE_HOLD_30MM_CONFIRMED`: every repeat of at least one candidate passes the unchanged strict gate;
- `PASS_DAMPED_HOLD_40MM_CONFIRMED_ONLY`: no strict candidate is confirmed, but a 40 mm damped hold repeats;
- `NO_CONFIRMED_HOLD`: neither condition repeats.

## Validation performed before packaging

Using the uploaded completed Stage2 output:

- all 1536 successful source candidates were loaded;
- the revised archives contained 64 exactly speed-safe damped candidates and 32 precise candidates;
- the selected finite-difference center was `g007_dba2ecfbb033bd66`, with 31.081 mm box error, 0.0429 m/s terminal velocity and 0.09975 m/s late RMS;
- the original Stage2 winner was explicitly retained as an anchor;
- leave-one-generation-out velocity-surrogate validation produced approximately:
  - terminal velocity R² 0.715, MAE 0.0220 m/s;
  - late velocity RMS R² 0.572, MAE 0.0152 m/s;
- a generation manifest contained exactly 192 unique candidates with the configured family quotas;
- every decoded candidate had 15 parameters, ten time steps and 14 physical actions;
- the native shell launcher was tested in an empty standalone tree with no `.git`, no source exports and automatic source discovery.

Also completed:

- Python compilation;
- JSON parsing;
- shell `bash -n` checks;
- Stage2 base synthetic test;
- Stage2.1 synthetic test;
- 14 Stage2.1 unit/regression tests, including the exact missing-prediction
  confirmation failure, disabled-surrogate JSON, all-repeat failure summaries,
  non-finite environment states and atomic temporary-file cleanup;
- 18 total pytest tests across Stage2 and Stage2.1;
- clean extract-and-run verification.

## Honest runtime boundary

This package has not been executed here against your gotsc binary or through a complete 192-worker real-TSC generation. The full TSC runtime remains the final server-side validation. No claim in this README should be read as evidence that the strict 30 mm gate will necessarily be found.
