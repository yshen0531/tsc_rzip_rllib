# Stage3.2 changelog

## Ray-capacity scheduler hotfix

- Fixed a deterministic Ray resource under-sizing bug in variable-size evaluation campaigns.
- Ray is now initialized with the configured campaign capacity, not the first wave's candidate count.
- A first 84-candidate wave with `workers=96` now creates an 84-actor wave on a 96-CPU Ray cluster; a later 120-candidate wave correctly creates 96 actors.
- Resume with 12 missing candidates still initializes a 96-CPU cluster, so following 24-, 120-, 150-, and 99-candidate waves retain full parallelism.
- An already-initialized cluster exposing fewer CPUs than requested now fails immediately instead of silently leaving actors unschedulable.
- Added common Ray capacity planning to Stage1 scan/validation, Stage2 shared evaluation, Stage3.1 feedback, and Stage3.2 feedback.
- Added seven regression tests reproducing the 84→120 and 12→24→150 wave sequences.
- No scientific objective, hard gate, trajectory parameterization, TSC result, or saved run state is changed.

## Motivation

Stage3.1 produced the first confirmed real-TSC fixed-scenario 30 mm strict trajectory, but its positive-Z position margin was only about 0.063 mm for the reported best candidate.  The limited causal feedback POC did not recover the failing negative-Z target shift, and its zero-clipped violation score could not reward additional margin for already-passing scenarios.

## Changes from Stage3.1

### 1. Signed-margin optimization

- Reuses all saved Stage3.1 raw real-TSC trajectories.
- Recomputes hard and internal signed margins from raw trajectories.
- Continues optimization after the first strict crossing.
- Uses a 27.5 mm / 0.07 m/s internal target while keeping the official hard gate unchanged.
- Optimizes steps 8–14 with two real-TSC Jacobian centers.
- Allows finite-difference probes themselves to become best candidates.

### 2. Long-hold horizon

- Extends the episode from 150 ms to 250 ms.
- Arrival must still complete by 150 ms.
- The trajectory must remain position-, speed-, and Ip-safe through 250 ms.
- Adds 48 deterministic tail-screen runs.
- Adds ten independent tail actions at steps 15–24.
- Adds up to two 30-variable real-TSC long-hold SQP rounds.

### 3. Full-horizon identification

- Expands controller identification from steps 8–14 to steps 0–24.
- Uses 75 modal variables and 125 measured outputs.
- Generates a 125×75 real-TSC Jacobian.
- Uses dimensionless output scales, truncated SVD, ridge regularization, and causal time-indexed gains.
- Allows one optional real-TSC recenter identification pass.

### 4. Feedback campaign

- Expands from 8 limited scenarios to 33 scenarios.
- Tests R, Z, R/Z quadrant, and Ip target shifts.
- Tests Mode 1/2/3 disturbances at multiple times.
- Tests global controller scales 0.0, 0.5, and 1.0.
- Selects one global positive scale; never selects a different scale per scenario.
- Replaces zero-clipped violation comparisons with signed margin, preservation, recovery, and loss counts.
- Disqualifies a scale that loses a baseline-strict scenario under the default validation settings.

### 5. Confirmation

- Adds 12 open-loop long-hold confirmation runs.
- Adds 16 feedback confirmation runs.
- Preserves the distinction between deterministic reproducibility and robustness.

### 6. Integrity and runtime safety

- Strict JSON serialization remains mandatory; NaN and Infinity are rejected.
- Source results are fingerprinted by logical path plus SHA256.
- Resume refuses changed source content.
- Bound variables use inward secant probes.
- Missing Jacobian directions remain unavailable and cannot be moved by the optimizer.
- Runtime workspaces remain under `/tmp` and are cleaned after candidates/waves.

## Unchanged scientific boundaries

- Three validated SVD modes.
- 10 ms control period.
- 30 mm rectangular R/Z precise gate.
- 0.10 m/s velocity limits.
- 10 kA Ip limit.
- Arrival completed by 150 ms.
- Real TSC is the only source of pass/fail truth.
- Initial-state, plant-parameter, noise, and delay robustness are not claimed.

## Runtime patch — variable-wave Ray capacity deadlock

The first Stage3.2 server run exposed a deterministic Ray scheduling deadlock:

```text
first open-loop wave       84 candidates
Ray initialized CPUs       84
later hold-probe wave     120 candidates
configured workers         96
completed results         108
permanently pending        12
```

The old evaluator initialized Ray with `min(configured_workers, first_wave_pending)`.  Later waves created up to the configured actor count even though the local Ray cluster had fewer logical CPUs.  The last 12 actors could never be scheduled.

This patch:

- adds `tsc_rzip_rllib/utils/ray_runtime.py`;
- initializes Ray with the configured campaign capacity, independent of wave size;
- caps each wave's actor count by pending work and actual cluster resources;
- rejects an undersized pre-existing Ray cluster immediately;
- prints requested workers, cluster CPUs, pending tasks, actor count, and whether Ray was initialized in the current call;
- applies the fix to the shared open-loop evaluator, Stage3.1/3.2 feedback evaluators, and Stage1 scan/validation evaluators;
- adds regression tests for `84 -> 120` and resume `12 -> 24 -> 150` wave sequences.

No scientific objective, hard gate, control vector, SQP proposal, TSC environment, saved-result schema, or resume state was changed.
