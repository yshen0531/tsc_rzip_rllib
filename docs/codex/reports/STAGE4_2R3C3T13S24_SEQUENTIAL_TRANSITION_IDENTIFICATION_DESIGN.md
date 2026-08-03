# Stage4.2R3c3T13S24 sequential transition identification design

## Status and purpose

This design is frozen after the final S23R1 forensics and before S24
implementation, deployment, plant advance, or response access.  S24 is a new
controller and experiment identity.  It does not resume, overwrite, or
relabel S21, S23, S23D1, or S23R1.

S24 asks whether a causal, state-conditioned closed-loop transition model can
recursively predict the response of the authenticated R3c1 base controller
plus bounded four-coordinate corrections from task state 10 through the
unchanged formal horizon.  It is identification only.  It is not a real MPC,
expert data, BC, DAgger, or RL stage, and it is not a global open-loop plant
model.

## Immutable sources and identities

Offline preparation must authenticate in place:

- all 360 S21 raw JSON.GZ, their 21,083,271-byte inventory and digest
  `8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4`;
- the exact S21 state, manifest, final result, independent postprocess,
  compact model, tube, source snapshots, and controller/package identities;
- the final S22, S23, S23D1, and S23R1 detailed/summary/manifest hashes;
- S23R1 route
  `AMPLITUDE_CODED_HADAMARD_PREFLIGHT_PASS_FREEZE_S24_REQUIRED` and detailed
  SHA-256
  `2fe49067ea49551eda1341f6aff74ad6d9c3a5abc2b05e26453aae12bddc0e79`.

S24 uses new constants for stage, campaign identity, controller revision,
package revision, experiment IDs, run directory, Ray directory, state,
manifest, logs, and raw files.  No prior raw may satisfy an S24 experiment
ID.  Source outcomes may be used only for authentication and prospective
model design; they may not enter an online action.

```text
stage
  Stage4.2R3c3T13S24
run name
  stage4_2r3c3t13s24_sequential_transition_identification
campaign identity
  sequential_amplitude_coded_transition_identification_v1
controller revision
  sequential_amplitude_coded_card15_probe_v42r3c3t13s24_v1
package revision
  r42r3c3t13s24_sequential_transition_identification_v1
```

## Frozen 1,000-rollout matrix

The S21 twenty-pair whole-pair split and its two hidden-history members are
unchanged.  A pair and both of its history members stay in one partition.

```text
partition     pairs  contexts  fresh baselines  sequences/context  rollouts
training         12        24               24                 24       600
calibration       4         8                8                 24       200
fresh holdout     4         8                8                 24       200
total            20        40               40                  -      1000
```

Every context retains its frozen target, authentic restart snapshot, and
finite clean actuator regime.  The controller never receives the pair,
history, partition, regime, target-ID, delay, slew, prefix, or amplitude
label.  Numerical target offsets are allowed because a feedback controller
must know its requested R/Z/Ip setpoint.  Delay and slew labels are not model
features; their consequences must be inferred from causal visible history.

## Fixed online excitation

Every rollout first executes S21's causal visible-state controller and exact
cumulative Card15 calibration at task steps 0 through 7, followed by settling
steps 8 and 9.  A fresh baseline then receives no sequential correction.

Each nonbaseline rollout uses exactly one of the 24 S23R1 rows.  The four
issue/cancel pairs are:

```text
slot              0       1       2       3
issue task step   10      13      15      17
cancel task step  11      14      16      18
issue effect      11      14      16      18
cancel effect     12      15      17      19
```

Rows 0--15 are the unpermuted Sylvester H16 rows, with column
`4 * slot + direction`; rows 16--23 are exact global negatives of rows 0--7.
The ordered directions remain `mode0_without_coil8`,
`mode0_coil8_component`, `mode1`, and `mode2`.  Canonical four-sign blocks
use amplitudes `++++:0.25`, `+-+-:0.25`, `++--:0.50`, and `+--+:0.50`.

At each issue, after the underlying action is computed from current causal
state, S24 constructs the nearest exact Card15 target around that current
center with search radius 16.  At the adjacent cancel it returns exactly to
the stored pre-issue Card15 center.  The controller stores only its own
issued target and causal memory.  Later issues are constructed from their
actual current-run centers; no baseline or source future is replayed.

Every event must pass the unchanged S23R1 exact-field, coordinate-error,
active-sign, cosine, off-basis, action, current, no-clip, no-saturation,
exact-cancel, and exact-zero-target-jump gates.  A runtime action that cannot
meet the frozen gate is a failed S24 raw result, not permission to search a
different action.

## Frozen causal transition family

The modeled visible vector is:

```text
[R error, Z error, vR, vZ, Ip error]
scales = [0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A]
```

For transition from state `k` to `k+1`, `k >= 10`, the feature builder may
use only:

1. the ten most recent visible vectors ending at state `k`, left padded only
   with authentic states already observed in the same rollout;
2. numerical target R/Z/Ip offsets;
3. Legendre task-clock terms of degrees 1 through 3;
4. requested four-coordinate correction vectors for task steps `k`, `k-1`,
   and `k-2`, where unissued steps are exactly zero;
5. deterministic polynomial terms selected from the newest visible vector,
   the three causal requested-action vectors, and their state-action
   interactions.

The model predicts the next scaled visible vector.  Its finite, prospectively
frozen feature candidates are:

```text
L  linear ten-state history + target + clock + three-action history
SA L plus newest-state squares and newest-state/action interactions
Q  SA plus the upper-triangular quadratic terms of the three-action history
```

Each candidate is a standardized multi-output ridge regression.  The ridge
grid is fixed at:

```text
0, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2, 1, 100
```

Training selection uses twelve leave-one-whole-pair-out folds.  Within a
fold, both hidden-history members and all 25 trajectories of the held pair
are excluded from fitting.  Candidate selection lexicographically minimizes:

```text
recursive formal-verdict mismatch count
maximum absolute recursively scaled state error
mean squared recursively scaled state error
candidate complexity order L, SA, Q
ridge value
```

No one-step teacher-forced score can substitute for the recursive score.
After selecting the family and ridge, one model is refit on all training
pairs and hashed before any calibration response is opened.

The model and its evaluator must reject access to pair/history/partition,
prefix/amplitude/regime/target-ID/delay/slew labels, source or matched
baseline results/actions, coil or wire currents, actual future Card15
coordinates, post-effect currents, future measurements, and future executed
actions.  The fixed planned requested coordinate at the current transition
is a legal MPC input; a later requested coordinate may enter only when the
recursive clock reaches that transition.

## Recursive prediction and uncertainty gates

Every recursive evaluation starts from the authentic causal visible prefix
through state 10.  From state 10 onward it replaces measurements with its own
predictions, advances the ten-state window, and reveals requested actions one
transition at a time.  It predicts through state 35 for normal-slew contexts
and state 37 for weak-slew contexts.  It may not reset to a measured future
state.

The componentwise residual tube is frozen after calibration as:

```text
response floor [1e-9, 1e-9, 1e-7, 1e-7, 1e-4]
+ 2 * max(training whole-pair OOF recursive absolute residual,
          calibration recursive absolute residual)
```

The immutable halfwidth caps are:

```text
[0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]
```

For every predicted state in every trajectory, each opened partition must
pass:

```text
finite recursive prediction                                all / all
maximum absolute scaled point error                           <= 0.10
componentwise residual containment                          all / all
componentwise tube cap                                      all / all
```

Using the unchanged 30 mm, 0.1 m/s, 10 kA and arrival-streak rules, predicted
and raw formal arrival/hold verdicts must match for every trajectory.  The
actual raw formal metrics are evaluation targets only; they never enter
model features, action selection, split selection, thresholds, or route
selection.

Training requires every leave-pair-out recursive row, trajectory verdict,
and tube-cap precursor to pass.  Calibration requires every recursive row
and verdict to pass before the fixed residual tube is written and hashed.
Fresh holdout requires every recursive row to pass point, containment, cap,
and formal-verdict reproduction.  Independent server-side recomputation must
rebuild the selected model, training OOF predictions, calibrated tube, and
final summaries exactly from raw.

## Phase boundaries and resume policy

```text
offline source/snapshot/package authentication and zero-plant spec preflight
-> training baselines (24)
-> training sequences (576)
-> whole-pair recursive OOF gate and training-model hash
-> calibration baselines (8)
-> calibration sequences (192)
-> recursive calibration gate and tube hash
-> fresh holdout baselines (8)
-> fresh holdout sequences (192)
-> final and independent server raw recomputation
```

Each opened real-TSC phase runs its complete fixed task set, then stops at the
boundary if any runtime, restart, causality, action, raw, model, or reporting
gate fails.  Later outcomes remain unopened.  Parallel completion order may
not change the phase boundary or split.

Resume may reuse only complete successful raw with exact experiment ID,
controller identity, spec, source fingerprints, code/config hashes, and
trajectory length.  A semantics-neutral runtime/reporting fix may resume the
same campaign only after explicit compatibility verification.  Changing an
online action, transition feature, model grid, statistical gate, split,
formal metric, or controller semantics requires a new stage identity.

## Routes and interpretation

Runtime, action-construction, training-model, calibration-tube, and fresh
holdout failures have separate terminal routes:

```text
offline/source/preflight failure
  SEQUENTIAL_IDENTIFICATION_PREFLIGHT_FAIL
runtime/restart/action/raw failure
  SEQUENTIAL_IDENTIFICATION_RUNTIME_FAIL
training recursive-model failure
  SEQUENTIAL_TRANSITION_TRAINING_RECURSIVE_FAIL
calibration recursive/tube failure
  SEQUENTIAL_TRANSITION_CALIBRATION_FAIL
fresh holdout failure
  SEQUENTIAL_TRANSITION_HOLDOUT_FAIL_REDESIGN
```

The only pass route is:

```text
SEQUENTIAL_CAUSAL_TRANSITION_HOLDOUT_PASS_MODEL_ONLY
```

A pass certifies only this finite clean, same-source, two-target, discrete
delay/slew closed-loop transition envelope.  It authorizes a separately
preregistered zero-TSC robust finite-horizon feasibility/MPC design.  It does
not authorize a real MPC run, expert data, BC, DAgger, or RL.

Even after an S24 pass, independent hidden histories and initial states, new
targets, continuous delay/gain/slew, plant/Jacobian mismatch, noisy sensing,
disturbance recovery, and independent long hold remain mandatory before an
MPC expert can be declared reliable.
