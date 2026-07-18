# Stage1.1 — failed-scan recovery and strict SVD2/SVD3/SVD4 validation

Stage1.1 is a small supplement to an existing Stage1 run. It does **not** repeat all 563 identification experiments and it does **not** modify the source Stage1 directory.

It performs four focused tasks:

1. Copies the existing Stage1 raw experiment files into a new Stage1.1 run.
2. Retries only failed or missing identification experiments at reduced concurrency.
3. Rebuilds the response tensor and generates only three candidates:
   - `svd02_target1p00`
   - `svd03_target1p00`
   - `svd04_target1p00`
4. Replays each candidate in real TSC at sequence scales `0.75`, `0.85`, and `1.00` and applies corrected hold metrics.

The original full14/SVD5/SVD6/SVD8 results are copied as read-only references and rescored with the same strict metrics.

## Corrected evaluation rules

The original Stage1 `±80 mm` Gate A was too loose because the 1100 ms initial state was already inside that tube. Stage1.1 therefore:

- excludes step 0 from all reach and consecutive-stay calculations;
- reports `±20`, `±30`, `±40`, and `±80 mm` boxes;
- compares every candidate directly with the zero-action terminal drift;
- requires consecutive terminal residence, not a single transient entry;
- includes terminal velocity and late-window velocity RMS.

Primary success gate:

- at least the last 3 post-initial samples inside the `±30 mm` R/Z box;
- terminal Ip within `±10 kA`;
- terminal R/Z velocity no greater than `0.10 m/s`;
- late-window R/Z velocity RMS no greater than `0.10 m/s`.

Relaxed gate uses `±40 mm` with the same damping requirements.

## Retry strategy

The source run contained 21 failed experiments caused by 120 s TSC timeouts. Stage1.1 retries only incomplete experiments with:

1. 12 Ray workers;
2. then 4 Ray workers for any remaining failures;
3. then serial execution for stubborn failures.

The TSC timeout is increased from 120 s to 180 s. This is an operational retry setting only; start state, coil actions, slew, target, state definition, and physics are unchanged.

## Installation

Unzip the package into the existing project root:

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/stage1_1_svd234_strict_validation_runtime_only_clean.zip -d .

chmod +x \
  run_stage1_1_supplement_native.sh \
  run_stage1_1_supplement_nohup.sh \
  run_resume_stage1_1_supplement_native.sh \
  run_resume_stage1_1_supplement_nohup.sh \
  run_stage1_1_retry_only.sh \
  run_stage1_1_analyze_only.sh \
  run_stage1_1_validate_only.sh \
  run_stage1_1_self_test.sh \
  run_stop_stage1_1_now.sh
```

## Self-test

```bash
./run_stage1_1_self_test.sh
```

The self-test does not call TSC. It checks response reconstruction, constrained optimization, step-0 exclusion, trailing-streak metrics, and the strict verdict logic.

## Full Stage1.1 run

Set the completed Stage1 source directory explicitly:

```bash
export SOURCE_STAGE1_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage1_runs/stage1_controllability_100ms_20260718_011455
./run_stage1_1_supplement_nohup.sh
```

Monitor:

```bash
tail -f logs/nohup/latest_stage1_1_supplement.log
```

The Stage1.1 output directory is recorded in:

```bash
cat stage1_1_runs/latest_stage1_1_run.txt
```

## Immediate stop and resume

Immediate stop is preserved:

```bash
./run_stop_stage1_1_now.sh
```

No graceful shutdown handler is installed. Completed per-experiment JSON files remain atomic and resumable. The currently running TSC experiment can be lost.

Resume:

```bash
./run_resume_stage1_1_supplement_nohup.sh
```

The resume script reads the original Stage1 source directory from `stage1_1_manifest.json`; it does not depend on the current `stage1_runs/latest_stage1_run.txt` value.

## Individual phases

Retry failed scans only:

```bash
export STAGE1_1_RUN_DIR=$(cat stage1_1_runs/latest_stage1_1_run.txt)
./run_stage1_1_retry_only.sh
```

Rebuild analysis and SVD2/3/4 candidates without new TSC scans:

```bash
./run_stage1_1_analyze_only.sh
```

Run or resume only the nine real-TSC validation trajectories:

```bash
./run_stage1_1_validate_only.sh
```

## Main outputs

```text
stage1_1_manifest.json
stage1_1_retry_summary.json
failed_experiments_current.csv

analysis/analysis_summary.json
analysis/response_tensor_dy_per_a.npy
analysis/coil_modes.csv
analysis/mode_bootstrap_samples.csv
analysis/mode_bootstrap_robustness_summary.csv
analysis/candidate_summary_linear.csv

candidate_sequences/svd02_target1p00.json
candidate_sequences/svd03_target1p00.json
candidate_sequences/svd04_target1p00.json

validation/validation_summary.csv
validation/gate_a_verdict.json
validation/stage1_1_accuracy_damping_tradeoff.png
validation/stage1_1_error_by_mode.png
validation/stage1_1_velocity_by_mode.png

source_reference/validation_summary_strict.csv
source_reference/gate_verdict_strict.json

STAGE1_1_REPORT.md
```

## Interpretation

A pass means a real-TSC low-dimensional sequence satisfies both position residence and damping. A strong terminal-position improvement with excessive velocity is not called a hold success.

If SVD3 matches SVD4 within a few millimetres and comparable damping, SVD3 is the preferred Stage2 action space because the first three modes are physically interpretable and robust. If SVD4 materially outperforms SVD3 after all failed scans are recovered, the fourth mode must be inspected carefully because the original data showed much weaker bootstrap stability beyond the first three modes.
