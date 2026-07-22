# Stage3.1 complete standalone release

## 1. Purpose

Stage3.1 continues from the completed Stage3.0 run. It does **not** repeat the
96-trajectory Stage3.0 tail screen. The Stage3.0 evidence showed that:

- the real-TSC finite-difference model was locally accurate;
- each accepted SQP step improved the real system;
- the three Stage3.0 SQP solutions hit the trust-region boundary;
- nevertheless the implementation shrank the trust region after every
  improvement and stopped after only three rounds;
- the final open-loop trajectory was reproducible inside the 40 mm tube but did
  not enter and remain inside the strict 30 mm tube.

Stage3.1 therefore finishes the fixed-scenario nominal search more faithfully
and then performs a **limited causal-feedback proof of concept**. It is still not
the final controller.

The final project task remains:

> Build a causal and robust feedback controller that reaches, decelerates, and
> holds R/Z/Ip across multiple initial states and targets, under real TSC
> current, slew, delay, and hidden-dynamic constraints.

The intended eventual structure remains:

```text
u = nominal trajectory + causal MPC/feedback + bounded residual RL
```

A single fixed-state open-loop success is only an expert/nominal entry point.
The Stage3.1 feedback experiment is only a small proof of concept and does not
establish robustness or deployment readiness.

---

## 2. What is unchanged

Stage3.1 preserves the validated physical and evaluation setup:

- 10 ms control interval;
- 150 ms episode, 15 actions and 16 states;
- first three Stage1.1 SVD actuator modes;
- 14-channel real coil decoding;
- existing current and slew constraints;
- real TSC as the only authority for strict/relaxed gates;
- arrival may be at 120, 130, 140, or 150 ms;
- arrival must persist safely through 150 ms;
- strict position tube: `|R error| <= 30 mm` and `|Z error| <= 30 mm`;
- endpoint speed, endpoint late RMS, post-arrival RMS, and final speed limits:
  `0.10 m/s`;
- sustained Ip error limit: `10 kA`;
- relaxed reference tube: 40 mm.

The hard scientific gate is not relaxed or renamed to manufacture a success.

---

## 3. Source data and integrity checks

Stage3.1 requires the completed Stage3.0 run, normally:

```text
stage3_0_runs/stage3_0_svd3_tail_sqp_150ms_20260721_121352
```

It also reconstructs the validated physical context through the Stage2.2 run
referenced by the Stage3.0 manifest. Preserve the existing result directories,
especially:

```text
stage1_1_runs/
stage2_runs/
stage2_1_runs/
stage2_2_runs/
stage3_0_runs/
```

Only source-code directories are replaced during installation.

At prepare/resume time the program:

1. loads all 420 successful Stage3.0 optimization/identification rows;
2. resolves every referenced compressed real-TSC result;
3. reconstructs the exact Stage3.0/Stage2.2 mode and current context;
4. fingerprints every referenced Stage3.0 result plus key Stage3.0 and Stage2.2
   files by SHA256;
5. stores the inventory in the new run;
6. refuses to resume if the source content changes.

This prevents a resumed Stage3.1 run from silently mixing Jacobians and control
vectors from different source histories.

---

## 4. Control parameterization

Stage3.0 froze actions 0-8 and optimized steps 9-14, giving 18 variables.
Stage3.1 freezes only steps 0-7 and optimizes:

```text
steps 8, 9, 10, 11, 12, 13, 14
x 3 validated SVD modes
= 21 variables
```

The earlier turn at step 8 is included because the Stage3.0 trajectory had
already accumulated a positive-Z bias by the time the old tail controller
started. Exposing step 8 provides one extra 10 ms interval to shift the eventual
stopping location without discarding the validated early drive.

For every Stage3.0 source row, Stage3.1 reconstructs the corresponding 21-vector
and verifies the same mode/action/current decoder. The physical action remains
subject to per-step action normalization and absolute-current room.

---

## 5. Adaptive real-TSC SQP

### 5.1 Two centers

Each round uses two real-TSC centers:

- primary: current minimax/strict-best candidate;
- secondary: a complementary candidate.

For the first two rounds, the secondary center must come from a different
Stage3.0 nominal family. This prevents the multi-nominal design from immediately
collapsing back to the single `nominal_05` family that dominated Stage3.0.

### 5.2 Real finite differences

For each center:

```text
21 variables x positive/negative perturbation = 42 real-TSC probes
```

With two centers:

```text
84 real-TSC probes per round
```

At coefficient bounds, the program generates two inward secant points instead
of a zero perturbation. A local Jacobian is accepted only with enough reliable
columns. Missing columns are written as JSON `null` in diagnostics and fixed at
zero in the SQP solver.

The local output vector has 35 entries:

```text
R error   at states 9-15  = 7
Z error   at states 9-15  = 7
R speed   at states 9-15  = 7
Z speed   at states 9-15  = 7
Ip error  at states 9-15  = 7
--------------------------------
                              35
```

Thus each center produces a measured `35 x 21` real-TSC Jacobian.

### 5.3 SQP proposals

For each center, Stage3.1 solves endpoint-specific local problems for arrival at
120-150 ms using three profiles:

- balanced;
- position-heavy;
- damping-heavy.

The real-TSC wave tests 15 proposals per center, including step multipliers:

```text
0.5 x, 1.0 x, and 1.5 x
```

With two centers this is 30 real-TSC SQP proposals per round.

Each full round costs:

```text
84 finite-difference probes + 30 SQP proposals = 114 real-TSC runs
```

### 5.4 Trust-region update

Stage3.0 always reduced trust scale after improvement. Stage3.1 instead computes
real agreement:

```text
rho = actual reduction / predicted reduction
```

The comparison is made at the **same requested endpoint** for the center,
linear prediction, and real-TSC proposal. It no longer compares an endpoint-
140 prediction with a rollout's unrelated best endpoint.

Rules:

- accepted, `rho >= 0.75`, and solution near the trust boundary:
  expand by `1.35`;
- accepted with adequate agreement:
  hold;
- accepted but poor agreement:
  shrink by `0.65`;
- rejected:
  shrink by `0.50`.

Trust scales are tracked by center slot and nominal family. This avoids both
problems seen in earlier prototypes: two same-nominal centers overwriting each
other, and a newly selected nominal blindly inheriting an unrelated center's
radius.

Optimization stops on the first of:

- strict gate found;
- six SQP rounds completed;
- two rounds without meaningful global improvement.

---

## 6. Final real-TSC identification and dimensionless MPC bundle

After optimization, the best candidate is re-identified using 42 smaller
positive/negative probes. If a probe itself produces a meaningful new best, the
program may recenter once and run one more 42-probe identification wave.

Unlike the Stage3.0 POC, Stage3.1 normalizes outputs before regularization:

```text
R error  / 0.03 m
Z error  / 0.03 m
R speed  / 0.10 m/s
Z speed  / 0.10 m/s
Ip error / 10000 A
```

It then uses truncated SVD and ridge regularization. Ip no longer dominates the
controller merely because it is expressed in amperes.

The controller bundle contains:

- physical and normalized `35 x 21` Jacobians;
- retained singular directions;
- dimensionless batch correction gain;
- time-indexed causal gains for current steps 8-14;
- only the first currently executable three-mode command at each step;
- explicit warnings:
  `online_feedback_validated = false` and `robustness_validated = false`.

The time-indexed gains use a modest constant-velocity bias projection. They are
not presented as a full nonlinear receding-horizon optimizer.

---

## 7. Limited causal-feedback POC

The generated causal gains are tested in 24 real-TSC rollouts:

```text
8 scenarios x controller scales [0.0, 0.5, 1.0]
```

Scenarios:

```text
nominal
R target +2 mm
R target -2 mm
Z target +2 mm
Z target -2 mm
R/Z targets +2 mm
Mode-1 disturbance +0.04 at step 10
Mode-1 disturbance -0.04 at step 10
```

At every step from 8 onward, the controller observes current R/Z/Ip and finite-
difference R/Z velocity, compares them with the nominal reference, and applies
only the current three-mode correction. Corrections are bounded by mode.

The two positive gains are scored as **global controller choices**. The program
selects one fixed scale for the whole POC; it does not choose a different scale
after seeing each scenario. A limited pass requires that this one scale improves
most nonnominal scenarios and does not materially degrade nominal behavior. Even
then:

```text
online_feedback_validated = false
robustness_validated = false
```

It does not cover initial-state distributions, long hold, plant uncertainty,
noise, delay uncertainty, or eddy/vessel-state mismatch.

---

## 8. Deterministic confirmation

The confirmation set is category-aware and can include:

- strict candidates;
- minimax/corner candidates;
- speed-safe candidates;
- relaxed candidates;
- candidates from another nominal family.

Up to eight unique candidates are replayed three times. A strict verdict is
issued only when at least one candidate passes the unchanged strict gate in all
three replays:

```text
PASS_PRECISE_HOLD_30MM_120_150MS_CONFIRMED
```

Other possible final verdicts are:

```text
PASS_DAMPED_HOLD_40MM_120_150MS_CONFIRMED_ONLY
NO_CONFIRMED_HOLD_120_150MS
```

Repeated deterministic trajectories establish reproducibility only, not
robustness.

---

## 9. Maximum real-TSC cost

If no strict candidate appears and the optional re-identification is required:

```text
6 SQP rounds x 114                      = 684
final identification 42 + recenter 42   = 84
limited feedback POC                     = 24
confirmation, up to 8 x 3                = 24
------------------------------------------------
maximum                                 = 816 real-TSC runs
```

The Stage3.0 96-run screen is reused and not repeated. Default Ray worker count
is 96.

---

## 10. Complete standalone package

This archive physically includes:

```text
configs/
scripts/
tests/
tsc_rzip_rllib/
```

It also contains all inherited Stage2, Stage2.1, Stage2.2, and Stage3.0 base
files required by Stage3.1.

It does not require:

```text
.git
GitHub
network access
an external source-code tree
runtime code restoration
```

The historical result directories remain external data inputs and must be
preserved.

---

## 11. Installation

Enter the project root:

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Stop prior jobs:

```bash
./run_stop_stage3_1_now.sh 2>/dev/null || true
./run_stop_stage3_0_now.sh 2>/dev/null || true
./run_stop_stage2_2_now.sh 2>/dev/null || true
ray stop --force 2>/dev/null || true
```

Delete only the old source-code directories:

```bash
rm -rf configs scripts tests tsc_rzip_rllib
```

Do **not** delete the historical result directories listed in Section 3.

Extract the archive at the project root:

```bash
unzip -o /path/to/stage3_1_complete_standalone.zip \
  -d /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Set permissions:

```bash
chmod +x \
  run_stage3_1_svd3_adaptive_sqp_mpc_native.sh \
  run_stage3_1_svd3_adaptive_sqp_mpc_nohup.sh \
  run_stage3_1_prepare_only.sh \
  run_stage3_1_one_round_native.sh \
  run_stage3_1_identify_only.sh \
  run_stage3_1_feedback_only.sh \
  run_stage3_1_confirm_only.sh \
  run_stage3_1_analyze_only.sh \
  run_stage3_1_self_test.sh \
  run_stage3_1_verify_package.sh \
  run_stop_stage3_1_now.sh
```

---

## 12. Package verification

Run:

```bash
./run_stage3_1_verify_package.sh
```

This does not call gotsc. It checks:

- package SHA256 files;
- complete source tree;
- Python compilation;
- all JSON configurations;
- all shell syntax;
- inherited Stage2/2.1/2.2/3.0 self-tests;
- Stage3.1 self-test;
- the full unit-test suite;
- absence of Git/network/external-tree installation dependencies;
- package manifest guardrails.

---

## 13. Select the source run

Recommended explicit paths:

```bash
export SOURCE_STAGE3_0_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_0_runs/stage3_0_svd3_tail_sqp_150ms_20260721_121352

export SOURCE_STAGE2_2_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_2_runs/stage2_2_svd3_corner_feasibility_100ms_20260721_085327
```

The Stage2.2 path can normally be recovered from the Stage3.0 manifest, but the
explicit variable is useful if the project directory was moved.

---

## 14. Prepare-only audit

```bash
./run_stage3_1_prepare_only.sh
```

This does not call gotsc. It loads and fingerprints the source history,
constructs the initial 21-variable catalog, and prints the Stage3.0 best source
candidate.

Prepare-only creates a run directory. To continue that exact run:

```bash
export STAGE3_1_RUN_DIR="$(cat stage3_1_runs/latest_stage3_1_run.txt)"
export STAGE3_1_RESUME=1
./run_stage3_1_svd3_adaptive_sqp_mpc_nohup.sh
```

Without those two variables, the full launcher intentionally creates a fresh
run and prepares it again.

---

## 15. Full background run

```bash
unset STAGE3_1_RUN_DIR
unset STAGE3_1_RESUME
./run_stage3_1_svd3_adaptive_sqp_mpc_nohup.sh
```

The default `all` command runs:

```text
adaptive SQP optimization
-> final identification
-> limited causal-feedback POC
-> deterministic confirmation
-> analysis/report
```

Follow the log:

```bash
tail -f "$(cat logs/nohup/latest_stage3_1_adaptive_sqp_mpc.log)"
```

Show the run directory:

```bash
cat stage3_1_runs/latest_stage3_1_run.txt
```

---

## 16. Resume and phase-specific commands

Resume an interrupted run:

```bash
export STAGE3_1_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_1_runs/<run-name>
export STAGE3_1_RESUME=1
./run_stage3_1_svd3_adaptive_sqp_mpc_nohup.sh
```

Completed successful compressed results are reused. The source content
fingerprint is checked before resume.

Phase-specific commands:

```bash
./run_stage3_1_one_round_native.sh
./run_stage3_1_identify_only.sh
./run_stage3_1_feedback_only.sh
./run_stage3_1_confirm_only.sh
./run_stage3_1_analyze_only.sh
```

They require `STAGE3_1_RUN_DIR` to identify an existing prepared run.

Immediate stop:

```bash
./run_stop_stage3_1_now.sh
```

It stops the Stage3.1 process group and Ray and cleans temporary `/tmp` runtime
workspaces. It does not delete completed run results.

---

## 17. Main output files

A run is stored under:

```text
stage3_1_runs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms_<timestamp>/
```

Important files:

```text
stage3_1_manifest.json
stage3_1_state.json
source_stage3_0_catalog.json
source_stage3_0_reference/source_content_inventory.json

stage3_1_phases/
stage3_1_evaluations/
stage3_1_best/

stage3_1_controller/mpc_poc_bundle.json
stage3_1_controller/mpc_poc_bundle.npz

stage3_1_feedback_poc/feedback_poc_results.csv
stage3_1_feedback_poc/feedback_poc_summary.json

stage3_1_confirmations/stage3_1_verdict.json
stage3_1_analysis/stage3_1_analysis_summary.json
STAGE3_1_REPORT.md
```

`mpc_poc_bundle` is an offline/limited POC artifact. It is not an approved
online controller.

---

## 18. Honest validation boundary

The package has been validated by compilation, complete unit tests, source-run
reconstruction, exact Stage3.0 action reproduction, real-history manifest
construction, source fingerprinting, synthetic no-gotsc round execution, and
fresh-directory standalone verification.

It has **not** been run here against the user's gotsc binary as a full real
Stage3.1 96-worker campaign. Therefore this release does not claim in advance:

- a 30 mm strict trajectory;
- successful adaptive trust expansion in the real system;
- a passing causal-feedback POC;
- online MPC validation;
- robustness across initial states or targets;
- readiness for behavior cloning, DAgger, or residual RL.

Those claims must be made only from the user's returned real-TSC results.
