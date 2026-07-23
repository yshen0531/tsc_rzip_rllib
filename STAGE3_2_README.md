# Stage3.2 — signed-margin nominal, 250 ms long hold, and full-horizon causal MPC validation

## Ray-capacity hotfix release

This package supersedes the earlier Stage3.2 archive that could initialize the local Ray cluster from the size of the first evaluation wave.  In the affected run, the first open-loop wave contained 84 candidates, so Ray exposed only 84 CPU resources even though the campaign requested 96 workers.  The later 120-probe long-hold wave then created 96 one-CPU actors; actors 84–95 could never be scheduled, producing the permanent `108/120` stall.

The corrected runtime now enforces these invariants:

```text
Ray cluster capacity = configured campaign worker count (96 by default)
current wave actor count = min(configured workers, pending candidates, cluster CPUs)
existing Ray cluster smaller than requested = immediate explicit error
resume with only 12 missing probes still initializes Ray at 96 CPUs
later 24/120/150/99-candidate waves may therefore use full parallel capacity
```

The scientific configuration, hard gate, candidate vectors, saved results, SQP logic, and feedback logic are unchanged.  The fix is purely in Ray resource planning and applies to the shared open-loop evaluator, Stage3.1/Stage3.2 feedback evaluators, and inherited Stage1 scan/validation paths.

For the interrupted run, preserve the run directory and resume it after installing this package.  The 108 completed long-hold probes are reused and only the 12 missing probes are rerun.

## 1. Purpose

Stage3.1 established the first repeatable real-TSC 30 mm strict trajectory for the fixed initial state and fixed target.  It also exposed two limitations that Stage3.2 addresses directly:

1. the best strict trajectory crossed the 30 mm rectangular boundary with only a very small positive-Z margin;
2. the limited Stage3.1 feedback POC was safe, but it did not recover the failing negative-Z target shift and its zero-clipped violation score could not reward additional safety margin inside the gate.

Stage3.2 therefore **does not move the hard gate**.  It reuses the completed Stage3.1 run and performs four distinct jobs:

- increase the signed safety margin of the 150 ms nominal instead of stopping at the first strict pass;
- extend the real-TSC episode from 150 ms to 250 ms and require the trajectory to remain safe;
- identify a full-horizon local model over all 25 control steps and build dimensionless causal gains;
- test one globally fixed feedback scale over a larger target/disturbance campaign using signed margins, preservation, and recovery.

Stage3.2 is still not the final project result.  It does not validate different initial states, plant-parameter uncertainty, measurement noise, actuation delay, eddy/vessel-state variation, or discharge-scale hold.  Residual RL remains a later bounded correction layer, not the primary controller.


## 2. Runtime hotfix: fixed Ray capacity across variable-size waves

This build includes the Stage3.2 Ray-capacity fix documented in `STAGE3_2_RAY_CAPACITY_FIX.md`.  The interrupted campaign proved that the old evaluator initialized Ray from the first wave size (84) and later created 96 actors for a 120-candidate wave, leaving actors 84–95 permanently unschedulable.

The fixed runtime always initializes the local Ray cluster at the configured campaign capacity, normally 96 CPUs, while creating only as many actors as the current wave needs.  Every wave now prints a line such as:

```text
[Stage2 evaluation] ray_capacity requested=96 cluster_cpus=96 pending=12 actors=12 initialized_now=1
```

An undersized pre-existing Ray cluster is rejected immediately instead of silently running or deadlocking.  This change does not alter any scientific control logic or saved result schema.

## 3. Complete standalone package

This package physically contains the complete source tree required by Stage3.2:

```text
configs/
scripts/
tests/
tsc_rzip_rllib/
```

It also includes the inherited Stage2, Stage2.1, Stage2.2, Stage3.0, and Stage3.1 implementations used by the new code.

It does **not** require:

```text
.git
GitHub or other network access
an external base source tree
runtime source recovery
STAGE3_2_BASE_TREE
```

The only external data dependency is a completed Stage3.1 results directory.

## 4. Scientific contract

### 3.1 Unchanged hard gate

The 30 mm / speed / Ip limits remain unchanged:

```text
|R error| <= 30 mm
|Z error| <= 30 mm
endpoint R/Z speed <= 0.10 m/s
endpoint late-window R/Z speed RMS <= 0.10 m/s
post-arrival R/Z speed RMS <= 0.10 m/s
final R/Z speed <= 0.10 m/s
sustained |Ip error| <= 10000 A
```

Arrival must be completed at one of the relative endpoints:

```text
120 ms, 130 ms, 140 ms, or 150 ms
```

The three-sample arrival window and all later samples must remain safe through 250 ms.  In the current 1100 ms restart convention, the episode therefore runs to 1350 ms.

The relaxed 40 mm gate is retained only for diagnosis.  It cannot produce a precise-success verdict.

### 3.2 Internal optimization goal

The optimizer aims inside the hard boundary:

```text
internal R/Z box = 27.5 mm
internal speed = 0.07 m/s
minimum hard signed margin target = 0.075
```

These are optimization targets only.  The official pass/fail gate remains 30 mm / 0.10 m/s / 10 kA.

### 3.3 Signed margin

For each active hard constraint, Stage3.2 computes a signed normalized margin.  Examples:

```text
position margin = 1 - sustained_box_error / 0.030
speed margin    = 1 - measured_speed / 0.10
Ip margin       = 1 - sustained_abs_Ip_error / 10000
```

Positive values are safe; negative values are violations.  The minimum across all constraints is the candidate's hard signed margin.

Unlike a zero-clipped violation score, this quantity distinguishes a barely passing trajectory from one with useful interior margin.

## 5. Workflow

### Phase A — 150 ms signed-margin SQP

Stage3.2 loads all successful Stage3.1 records and recomputes their metrics from the saved raw trajectories.  It starts from confirmed strict candidates and optimizes steps 8–14:

```text
7 control steps × 3 SVD modes = 21 variables
```

Each round uses two centers:

```text
21 variables × +/- perturbation × 2 centers = 84 real-TSC probes
12 SQP requests × 2 centers                 = 24 real-TSC proposals
---------------------------------------------------------------
108 real-TSC runs per margin round
```

There are at most three margin rounds.  Finite-difference probes themselves are eligible to become the best candidate; they are not discarded after identification.

The trust region expands, holds, or shrinks from measured prediction agreement.  Variables at coefficient bounds use inward secant samples rather than zero-length perturbations.

### Phase B — deterministic 250 ms extension screen

The best four margin candidates are extended with twelve deterministic tail templates each:

```text
4 candidates × 12 tails = 48 real-TSC runs
```

The templates include hold, zero, several ramps, slope continuation, and small modal tail pulses.  The screen is a real-TSC check that the restart chain can run reliably to 250 ms and that at least two source families have usable extensions.

### Phase C — 250 ms long-hold SQP

The long-hold optimizer independently adjusts steps 15–24:

```text
10 control steps × 3 SVD modes = 30 variables
```

Each round uses:

```text
30 variables × +/- perturbation × 2 centers = 120 real-TSC probes
12 SQP requests × 2 centers                 = 24 real-TSC proposals
----------------------------------------------------------------
144 real-TSC runs per hold round
```

There are at most two hold rounds.  The objective preserves arrival by 150 ms while maximizing the signed margin through 250 ms.

### Phase D — full-horizon real-TSC identification

The best 250 ms nominal is identified over every control step:

```text
steps 0–24 × 3 modes = 75 variables
states 1–25 × [R, Z, vR, vZ, Ip] = 125 outputs
real-TSC Jacobian shape = 125 × 75
```

A normal identification pass uses 150 real-TSC probes.  At most one optional recenter pass is allowed when a probe discovers a materially better nominal.

The controller uses:

```text
dimensionless output normalization
truncated SVD
ridge regularization
per-step modal feedback limits
causal time-indexed gains
```

The exported controller bundle remains a POC until the feedback campaign passes and is confirmed.

### Phase E — target/disturbance feedback campaign

The campaign contains 33 scenarios:

- nominal;
- R target shifts of ±5 and ±10 mm;
- Z target shifts of ±1, ±2, ±5, and ±10 mm;
- four R/Z ±5 mm quadrants;
- Ip target shifts of ±500 and ±1000 A;
- Mode 1 disturbances at steps 4, 8, and 12;
- Mode 2 disturbances at steps 8 and 12;
- Mode 3 disturbances at step 8.

Each scenario is tested with one of three globally fixed scales:

```text
0.0, 0.5, 1.0
```

Total:

```text
33 scenarios × 3 scales = 99 real-TSC rollouts
```

The positive scale is selected globally, never per scenario.  Selection uses:

- number of baseline-strict scenarios preserved;
- number of failed baseline scenarios recovered;
- number of strict feedback scenarios;
- median signed-margin gain;
- worst scenario-by-scenario signed-margin gain;
- nominal strict preservation.

A scale that loses a baseline-strict scenario is disqualified by the default configuration.

### Phase F — confirmation

Open-loop confirmation:

```text
4 candidates × 3 repeats = 12 real-TSC runs
```

Feedback confirmation:

```text
8 scenarios × 2 repeats = 16 real-TSC runs
```

Repeated deterministic runs establish reproducibility only.  They are not stochastic robustness tests.

## 6. Maximum real-TSC workload

If every optimization round is used:

```text
150 ms margin SQP:   3 × 108 = 324
250 ms screen:                  48
250 ms hold SQP:     2 × 144 = 288
full identification:           150
feedback campaign:              99
open-loop confirmation:         12
feedback confirmation:          16
-----------------------------------
without recenter:               937
optional ID recenter:          +150
maximum:                       1087
```

The default worker count is 96.  Early internal-margin success can reduce the number of SQP rounds.

## 7. Installation

Enter the project root:

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Stop any previous task:

```bash
./run_stop_stage3_2_now.sh 2>/dev/null || true
./run_stop_stage3_1_now.sh 2>/dev/null || true
./run_stop_stage3_0_now.sh 2>/dev/null || true
ray stop --force 2>/dev/null || true
```

Delete the old code directories, as in the established deployment workflow:

```bash
rm -rf configs scripts tests tsc_rzip_rllib
```

Do not delete result directories, especially:

```text
stage3_1_runs/
```

Extract the package directly into the project root:

```bash
unzip -o /path/to/stage3_2_complete_standalone_rayfix.zip \
  -d /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Set executable bits:

```bash
chmod +x \
  run_stage3_2_svd3_margin_long_hold_mpc_native.sh \
  run_stage3_2_svd3_margin_long_hold_mpc_nohup.sh \
  run_stage3_2_prepare_only.sh \
  run_stage3_2_one_margin_round_native.sh \
  run_stage3_2_extension_only.sh \
  run_stage3_2_one_hold_round_native.sh \
  run_stage3_2_identify_only.sh \
  run_stage3_2_feedback_only.sh \
  run_stage3_2_confirm_only.sh \
  run_stage3_2_analyze_only.sh \
  run_stage3_2_self_test.sh \
  run_stage3_2_verify_package.sh \
  run_stop_stage3_2_now.sh
```

## 8. Package verification

Run before real TSC work:

```bash
./run_stage3_2_verify_package.sh
```

This does not call gotsc.  It verifies:

- packaged SHA256 checksums;
- the complete inherited source tree;
- Python compilation;
- all JSON configs;
- all shell scripts with `bash -n`;
- inherited Stage2/2.1/2.2/3.0/3.1 self-tests;
- Stage3.2 synthetic checks;
- the complete unit-test suite;
- absence of Git/network/external-tree dependencies;
- package-manifest guardrails.

## 9. Source selection and prepare-only audit

Set the completed Stage3.1 run explicitly:

```bash
export SOURCE_STAGE3_1_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_1_runs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms_20260722_013158
```

Prepare without running gotsc:

```bash
./run_stage3_2_prepare_only.sh
```

The known Stage3.1 result should yield approximately:

```text
source catalog rows             = 918
successful Stage3.1 rows        = 498
strict source candidates        = 46
best hard signed margin         = 0.0285157367
best internal signed margin     = -0.0598010145
margin variables                = 21
long-hold variables             = 30
full-feedback variables         = 75
```

Prepare creates a run directory.  Continue that exact run with:

```bash
export STAGE3_2_RUN_DIR="$(cat stage3_2_runs/latest_stage3_2_run.txt)"
export STAGE3_2_RESUME=1
./run_stage3_2_svd3_margin_long_hold_mpc_nohup.sh
```

## 10. Direct full run

To create a fresh run directly:

```bash
unset STAGE3_2_RUN_DIR
unset STAGE3_2_RESUME
export SOURCE_STAGE3_1_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_1_runs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms_20260722_013158
./run_stage3_2_svd3_margin_long_hold_mpc_nohup.sh
```

Read the log:

```bash
tail -f "$(cat logs/nohup/latest_stage3_2_margin_long_hold_mpc.log)"
```

Read the run directory:

```bash
cat stage3_2_runs/latest_stage3_2_run.txt
```


## 11. Resume the interrupted 20260722_073932 run at full speed

Keep the existing result directory and use the normal 96-worker launcher:

```bash
export STAGE3_2_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_2_runs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms_20260722_073932
export STAGE3_2_RESUME=1
export STAGE3_2_WORKERS=96

./run_stage3_2_svd3_margin_long_hold_mpc_nohup.sh
```

The first resumed Ray log should report approximately:

```text
requested=96 cluster_cpus=96 pending=12 actors=12 initialized_now=1
```

After those 12 probes finish, the next 24-candidate wave should report:

```text
requested=96 cluster_cpus=96 pending=24 actors=24 initialized_now=0
```

The 108 already completed hold probes, all margin results, and all extension-screen results are reused.  Do not delete the run directory.

## 12. Phase-specific commands

The phase commands operate on an existing prepared run selected by `STAGE3_2_RUN_DIR` or `latest_stage3_2_run.txt`:

```bash
./run_stage3_2_one_margin_round_native.sh
./run_stage3_2_extension_only.sh
./run_stage3_2_one_hold_round_native.sh
./run_stage3_2_identify_only.sh
./run_stage3_2_feedback_only.sh
./run_stage3_2_confirm_only.sh
./run_stage3_2_analyze_only.sh
```

The full native launcher also accepts:

```bash
export STAGE3_2_COMMAND=margin
export STAGE3_2_COMMAND=hold
export STAGE3_2_COMMAND=all
```

## 13. Interruption and resume

Stop immediately:

```bash
./run_stop_stage3_2_now.sh
```

The stop script terminates the Stage3.2 process group and Ray, then cleans runtime directories below `/tmp`.  It does not delete saved Stage3.2 results.

Resume a run at full configured parallelism:

```bash
export STAGE3_2_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_2_runs/<run-directory>
export STAGE3_2_RESUME=1
export STAGE3_2_WORKERS=96
./run_stage3_2_svd3_margin_long_hold_mpc_nohup.sh
```

For the interrupted `20260722_073932` run, the corrected first resume wave has 12 pending probes but initializes Ray with 96 CPUs.  The expected capacity line is:

```text
[Stage2 evaluation] ray_capacity requested=96 cluster_cpus=96 pending=12 actors=12 initialized_now=1
```

The following 24-proposal wave should report the same 96-CPU cluster with 24 actors, and later 120/150/99-candidate waves can use up to 96 actors.

Completed strict-JSON `.json.gz` results are reused.  Source content is fingerprinted by logical path plus SHA256; changed source results are rejected rather than silently mixed with an existing run.

## 14. Main output files

```text
stage3_2_runs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms_<timestamp>/
```

Key outputs:

```text
stage3_2_manifest.json
stage3_2_state.json
source_stage3_1_catalog.json
source_stage3_1_reference/source_content_inventory.json

stage3_2_margin_phases/
stage3_2_margin_evaluations/
stage3_2_extension_screen/
stage3_2_hold_phases/
stage3_2_hold_evaluations/

stage3_2_controller/mpc_poc_bundle.json
stage3_2_controller/mpc_poc_bundle.npz

stage3_2_feedback_validation/feedback_validation_results.csv
stage3_2_feedback_validation/feedback_validation_summary.json

stage3_2_confirmations/open_loop_confirmation_summary.json
stage3_2_confirmations/feedback_confirmation_summary.json
stage3_2_confirmations/stage3_2_verdict.json

stage3_2_analysis/stage3_2_analysis_summary.json
STAGE3_2_REPORT.md
```

## 15. Verdict meanings

Possible final verdicts include:

```text
PASS_30MM_LONG_HOLD_250MS_AND_TARGET_DISTURBANCE_FEEDBACK_CONFIRMED
PASS_PRECISE_HOLD_30MM_250MS_OPEN_LOOP_CONFIRMED_FEEDBACK_NOT_VALIDATED
NO_CONFIRMED_30MM_LONG_HOLD_250MS
```

Even the strongest Stage3.2 verdict covers only the tested fixed initial state, configured target shifts, and injected modal disturbances.  It must not be relabeled as full robustness.

## 16. Final-task boundary

The project objective remains:

```text
a causal, robust feedback controller that reaches, damps, and holds R/Z/Ip
across initial states, targets, plant uncertainty, vessel/eddy state, noise,
and delay.
```

The intended eventual architecture remains:

```text
u = nominal trajectory + causal MPC/feedback + bounded RL residual
```

Stage3.2 strengthens and lengthens the nominal, and tests a much broader causal-feedback envelope.  It does not yet justify Behavior Cloning from a single fixed trajectory, nor does it justify making residual RL responsible for the primary control task.
