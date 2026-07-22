# Stage3.0 — 120–150 ms extended-horizon tail SQP and MPC-compatible POC

## 1. Purpose

Stage2.2 completed 576/576 real-TSC evaluations without runtime failure, but did not produce a trajectory that simultaneously satisfied the unchanged strict conditions:

- the final three samples inside the rectangular `|R error| <= 30 mm`, `|Z error| <= 30 mm` tube;
- terminal R/Z speed `<= 0.10 m/s`;
- late-window R/Z speed RMS `<= 0.10 m/s`;
- terminal Ip error within `10 kA`.

Its best corner remained close to the boundary: approximately `31.044 mm` final-three box error and `0.102958 m/s` late velocity RMS. The earlier 100 ms search also showed a near-opposite local position-versus-damping sensitivity. Since **100 ms is not a hard deadline** and arrival at 120–150 ms is acceptable, Stage3.0 changes the control representation and time budget instead of adding more CEM generations.

Stage3.0 has two narrowly defined jobs:

1. Find and confirm a fixed-scenario nominal trajectory that reaches, brakes, and remains inside the 30 mm tube by an accepted endpoint between 120 and 150 ms.
2. Identify a local real-TSC tail sensitivity and export an **offline MPC-compatible batch-gain POC**.

Stage3.0 is **not** the final controller. The final task remains a feedback controller that works across initial states, targets, disturbances, noise, and model variations.

---

## 2. Complete standalone package

This archive physically contains the complete source tree:

```text
configs/
scripts/
tests/
tsc_rzip_rllib/
```

It also contains the complete Stage2/Stage2.1/Stage2.2 base used by Stage3.0. It does not require:

```text
.git
GitHub
network access
an external base source tree
runtime code recovery
```

The only required external data is the **completed Stage2.2 result directory**. Preserve:

```text
stage2_2_runs/
```

The earlier `stage1_1_runs/`, `stage2_runs/`, and `stage2_1_runs/` directories may also be preserved for provenance, but Stage3.0 reads its nominal trajectories, modes, environment configuration, and initial currents directly from the completed Stage2.2 run.

---

## 3. Control representation

### 3.1 Episode and arrival window

- TSC start state: inherited from Stage2.2, normally `1100 ms`.
- Control interval: `10 ms`.
- Episode length: `15` actions / `150 ms`, producing 16 states.
- Accepted arrival endpoints: `120`, `130`, `140`, or `150 ms` after the start.

The program always runs the full 150 ms episode. An earlier arrival is accepted only when the trajectory remains safe through 150 ms.

### 3.2 Nominal and tail variables

For each source nominal:

- action steps `0–8` are inherited exactly from a real-TSC-evaluated Stage2.2 trajectory;
- steps `9–14` are six independent controls in the first three validated SVD modes;
- dimension: `6 steps × 3 modes = 18 variables`.

All twelve initial screen templates also preserve source step 9, so the screen is a clean 100-to-150 ms time-margin experiment. The later finite-difference/SLSQP phases are allowed to adjust step 9.

This removes the old five-node interpolation restriction from the final 60 ms while retaining a validated early drive.

### 3.3 Diverse source nominals

Stage3.0 enforces the following source categories before deduplication/fill:

```text
3 corner candidates
2 strict-speed-safe candidates
2 40 mm gate candidates
1 position-front candidate
---------------------------
8 source nominals
```

The category quotas are verified in code and in unit tests. This prevents all eight slots from silently collapsing to one corner family.

---

## 4. Hard gate

The 30 mm accuracy, speed, and Ip thresholds are copied from and checked against the Stage2.2 source configuration. The only task change is the allowed arrival time.

For an endpoint `e ∈ {12, 13, 14, 15}`, a precise pass requires:

1. Starting at `e - 2`, every R/Z state through step 15 stays inside the rectangular 30 mm tube. This supplies the required three-sample arrival streak and persistence through 150 ms.
2. R/Z speed at endpoint `e` is no greater than `0.10 m/s`.
3. R/Z speed RMS over the endpoint late window is no greater than `0.10 m/s`.
4. R/Z speed RMS from endpoint `e` through step 15 is no greater than `0.10 m/s`.
5. Final R/Z speed is no greater than `0.10 m/s`.
6. Ip error remains within `10 kA` from the arrival-window start through step 15.

A 40 mm relaxed gate is computed separately. It never counts as precise success.

For candidates without a precise pass, Stage3.0 minimizes the maximum normalized violation over the four permitted endpoints, followed by violation sum, L2 norm, and a smaller quality term. Any real precise pass outranks every non-pass.

---

## 5. Optimization sequence

### Phase A — 96-candidate time-margin screen

```text
8 source nominals × 12 deterministic tail templates = 96 real-TSC runs
```

Templates include:

- hold final 100 ms action;
- zero after 100 ms;
- fast, linear, and slow ramps to zero;
- decaying continuation of the final source slope;
- positive/negative Mode-1 and Mode-2 pulses;
- two coupled cross-mode pulses.

This phase answers the cheap question first: does extending the horizon already produce a strict trajectory without local optimization?

The program refuses to fit a local controller unless at least 48/96 screen trajectories succeed and at least four of the eight nominal families produce a successful 150 ms rollout. This is a scientific/runtime validity threshold, not an extra diagnostic loop: a tiny survivor set would not support a trustworthy finite-difference model.

### Phase B — up to three real-TSC SQP rounds

Each round selects two real-TSC centers:

- the current minimax corner;
- a distinct speed-safe or otherwise complementary center.

For each center:

```text
18 variables × positive/negative perturbation = 36 probes
2 centers × 36 = 72 real-TSC finite-difference runs
```

The probes identify a local Jacobian for 30 outputs:

```text
R error at states 10–15       6
Z error at states 10–15       6
R velocity at states 10–15    6
Z velocity at states 10–15    6
Ip error at states 10–15      6
--------------------------------
                               30
```

The program then solves box-constrained SLSQP subproblems using balanced, position-heavy, and damping-heavy profiles at candidate endpoints 120–150 ms. It evaluates 12 proposals per center:

```text
2 centers × 12 = 24 real-TSC SQP proposals
```

Therefore each full SQP round costs:

```text
72 probes + 24 proposals = 96 real-TSC evaluations
```

Finite differences are adaptive at coefficient bounds. If a center lies at a global bound, the program uses two inward secant points rather than aborting with a zero perturbation.

### Phase C — controller identification

After optimization, Stage3.0 runs one final 36-probe real-TSC identification around the best candidate and exports:

```text
stage3_0_controller/mpc_poc_bundle.json
stage3_0_controller/mpc_poc_bundle.npz
```

The bundle contains:

- the final 30×18 local tail Jacobian;
- selected position/velocity/Ip features;
- a regularized 18×N batch correction gain;
- the nominal linear correction and trust-clipped correction.

This is explicitly marked:

```text
online_feedback_validated = false
deployment_status = OFFLINE_MPC_COMPATIBLE_POC_ONLY
```

It maps a batch of future nominal-output errors to six tail controls. It is not yet a causal online observer/controller.

### Phase D — deterministic confirmation

Up to eight unique candidates are selected across strict, minimax, speed-safe, relaxed, and earliest-arrival categories. Each is replayed three times.

A confirmed strict verdict requires one candidate to pass the precise gate in all three repeats:

```text
PASS_PRECISE_HOLD_30MM_120_150MS_CONFIRMED
```

Repeated identical rollouts establish deterministic reproducibility only. They do not establish robustness.

---

## 6. Maximum real-TSC workload

With the default configuration and no early strict stop:

```text
screen                         96
3 SQP rounds × 96             288
controller identification      36
confirmation: 8 × 3            24
---------------------------------
maximum                        444 real-TSC runs
```

The waves are executed with up to 96 Ray workers. Every candidate is written atomically and can be resumed. Candidate episode directories and actor-private TSC workspaces are cleaned under `/tmp`.

---

## 7. Installation

Enter the project root:

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Stop old Stage2/Stage3 and Ray processes:

```bash
./run_stop_stage3_0_now.sh 2>/dev/null || true
./run_stop_stage2_2_now.sh 2>/dev/null || true
./run_stop_stage2_1_now.sh 2>/dev/null || true
./run_stop_stage2_now.sh 2>/dev/null || true
ray stop --force 2>/dev/null || true
```

Delete the old code directories, as in your normal deployment workflow:

```bash
rm -rf configs scripts tests tsc_rzip_rllib
```

Do **not** delete the completed Stage2.2 result directory:

```text
stage2_2_runs/
```

Extract the archive directly at the project root:

```bash
unzip -o /path/to/stage3_0_complete_standalone.zip \
  -d /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Restore executable bits defensively:

```bash
chmod +x \
  run_stage3_0_svd3_tail_sqp_native.sh \
  run_stage3_0_svd3_tail_sqp_nohup.sh \
  run_stage3_0_prepare_only.sh \
  run_stage3_0_screen_only.sh \
  run_stage3_0_one_round_native.sh \
  run_stage3_0_identify_only.sh \
  run_stage3_0_confirm_only.sh \
  run_stage3_0_analyze_only.sh \
  run_stage3_0_self_test.sh \
  run_stage3_0_verify_package.sh \
  run_stop_stage3_0_now.sh
```

---

## 8. Verify before using real TSC

```bash
./run_stage3_0_verify_package.sh
```

This performs no gotsc rollout. It checks:

- package SHA256 files;
- complete standalone tree;
- Python compilation;
- all JSON configurations;
- all shell scripts with `bash -n`;
- Stage2, Stage2.1, Stage2.2, and Stage3.0 self-tests;
- the complete unit-test suite;
- strict JSON/NaN protections;
- no Git, network, or external base-tree dependency.

---

## 9. Select the completed Stage2.2 source

Recommended explicit setting:

```bash
export SOURCE_STAGE2_2_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_2_runs/stage2_2_svd3_corner_feasibility_100ms_20260721_085327
```

Without the variable, the launchers try:

1. `stage2_2_runs/latest_stage2_2_run.txt`;
2. the newest complete `stage2_2_svd3_corner_feasibility_100ms_*` directory.

The source is rejected unless it contains the complete Stage2.2 configuration, Hall-of-Fame files, evaluation tree, environment/train configurations, and copied three-mode matrix.

---

## 10. Optional prepare-only audit

```bash
./run_stage3_0_prepare_only.sh
```

This does not call gotsc. It creates a Stage3.0 run and verifies:

- Stage2.2 target/horizon/mode/gate compatibility;
- the exact eight-nominal category composition;
- 15-step environment materialization;
- 18-variable tail bounds;
- source-file content fingerprints.

Inspect:

```bash
RUN_DIR=$(cat stage3_0_runs/latest_stage3_0_run.txt)
cat "$RUN_DIR/stage3_0_nominal_catalog.json"
cat "$RUN_DIR/stage3_0_manifest.json"
```

A later full launch creates a fresh run unless `STAGE3_0_RUN_DIR` and `STAGE3_0_RESUME=1` are explicitly set. Prepare-only is therefore an audit, not a required precursor.

---

## 11. Full background run

```bash
./run_stage3_0_svd3_tail_sqp_nohup.sh
```

Follow the log:

```bash
tail -f "$(cat logs/nohup/latest_stage3_0_svd3_tail_sqp.log)"
```

Read the active run directory:

```bash
cat stage3_0_runs/latest_stage3_0_run.txt
```

The full command performs:

```text
screen → up to 3 SQP rounds → controller identification → confirmation → analysis
```

---

## 12. Individual commands

```bash
./run_stage3_0_screen_only.sh
./run_stage3_0_one_round_native.sh
./run_stage3_0_identify_only.sh
./run_stage3_0_confirm_only.sh
./run_stage3_0_analyze_only.sh
```

The identify/confirm/analyze wrappers use the latest prepared Stage3.0 run unless `STAGE3_0_RUN_DIR` is set.

---

## 13. Resume after interruption

```bash
export STAGE3_0_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_0_runs/<specific-run>
export STAGE3_0_RESUME=1
./run_stage3_0_svd3_tail_sqp_nohup.sh
```

Completed successful candidate JSON files are reused. Missing or incomplete candidates are rerun. The stored manifest prevents resuming against a different Stage2.2 source.

---

## 14. Stop immediately

```bash
./run_stop_stage3_0_now.sh
```

The script:

- validates that the saved PID belongs to Stage3.0;
- terminates the process group;
- stops Ray;
- removes Stage3/Stage2-named runtime workspaces and episode directories under the configured `/tmp` roots;
- preserves all files under `stage3_0_runs/`.

`SIGKILL` cannot be intercepted, so an immediate external kill may leave temporary directories until this stop script is run.

---

## 15. Main outputs

```text
stage3_0_runs/stage3_0_svd3_tail_sqp_150ms_<timestamp>/
```

Important files:

```text
stage3_0_manifest.json
stage3_0_nominal_catalog.json
stage3_0_state.json

stage3_0_phases/
  screen/
  round_000_probes/
  round_000_jacobians/
  round_000_steps/
  ...
  controller_identification_999_probes/

stage3_0_evaluations/
stage3_0_best/
stage3_0_controller/
stage3_0_confirmations/
stage3_0_analysis/
STAGE3_0_REPORT.md
```

The analysis keeps separate Hall-of-Fame files for:

```text
strict
minimax
speed_safe
relaxed
earliest_arrival
```

---

## 16. Interpretation and next gate

### If Stage3.0 confirms a 30 mm trajectory

Do not jump directly to residual RL. The next engineering gate is:

1. perturb initial R/Z/Ip and, where available, vessel/eddy-current state;
2. perturb targets within the intended operating neighborhood;
3. test the nominal trajectory open-loop;
4. convert the identified model into a causal receding-horizon controller;
5. validate feedback in real TSC;
6. generate expert trajectories for behavior cloning/DAgger;
7. only then add a bounded residual-RL term.

### If Stage3.0 still does not pass

The result distinguishes two cases:

- substantial improvement from the extra 20–50 ms: time budget was the dominant Stage2 bottleneck;
- little improvement despite independent tail controls: the first-nine-action freeze, three-mode subspace, or fixed open-loop architecture must be relaxed before more local search.

Do not report a relaxed 40 mm result as precise success, and do not treat the offline batch gain as a deployed feedback controller.

---

## 17. Validation boundary

The final standalone tree passes Python compilation, JSON parsing, shell syntax checks, and **43 unit tests** in total, including **16 Stage3.0-specific tests**. It has been exercised against the uploaded completed Stage2.2 result tree for source loading, exact 3/2/2/1 nominal-category recovery, and generation of 96 unique 15-step × 14-coil screen specifications. A deterministic no-gotsc mock evaluator completed the full program path through 96-candidate screen, 72 finite-difference probes, 24 SLSQP proposals, 36 controller-identification probes, confirmation, analysis, and strict JSON/gzip readback.

The Jacobian path also has an explicit partial-data regression: unavailable finite-difference columns are represented with JSON `null`, and the SLSQP trust region freezes those variables instead of moving an unmeasured direction through the smoothness regularizer.

The package has **not** been executed here with your gotsc binary or as a real 96-worker 150 ms wave. The first server run remains the final runtime and control-result validation; no strict 120–150 ms success or online-feedback performance is claimed in advance.
