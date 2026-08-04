# Stage4.2R3c3T13S24D1R14R8 partitioned broad response identification design

Frozen prospectively after the final R7R2 result and its explicitly labelled
forensic diagnostics, but before R8 implementation, new task construction,
new TSC execution, model fitting on any R8 response, calibration, holdout, or
route evaluation.

## Purpose

R7R2 proved that the fixed action-conditioned full-history kernel cannot pass
whole-pair response validation when trained on only three of four physical
pairs. It did not prove a runtime, restart, plant, authority, point-error,
tube-cap, or global-observability failure.

R8 is a new-identity, authentic, phased response-identification campaign. It
adds the remaining fixed pairs from the immutable D1R11 20-pair context table,
without consuming or reinterpreting D1R11's failed sequential-response model.
The R7R2 model architecture, candidate grid, response gates, formal timing,
causal input restrictions, and expert-data prohibition remain unchanged.

## Immutable source boundary

R8 must authenticate the complete R2/R4/R6 source contracts from R7R2 and the
following D1R11 artifacts in place:

```text
D1R11 run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r11_runs/
  stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_20260804_571b932_v1/
  stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification

context_table.json
  31,279 bytes
  ba793593490e20c95e5618eaad7eebb80e86435c19c77360a21ae36e863461ab
all_specs.json
  11,743,103 bytes
  ff5644b667773ea2d79ffe4aa48ab951bbfacb4b34fbc62dfbcc4b4a69e4038a
stage_state.json
  732 bytes
  24728eccb317d60c20b29886320455c10b474ca9717663c62d7530dd7c8422fd
stage_manifest.json
  108,582 bytes
  d109f0a16098eed45f8a7c837d9f3b00e5dfa3e299eee8a4651f1a6787b75b43
```

The authenticated D1R11 state must remain:

```text
phase_status                         training_model_failed
training raw                                       600/600
calibration raw                                      0/200
holdout raw                                          0/200
heldout_outcomes_opened                              false
training_model_sha256                                empty
calibrated_tube_sha256                               empty
route                    FULL_REPLACEMENT_TRANSITION_TRAINING_MODEL_FAIL
```

D1R11 raw outcomes are not R8 model data. The 600 training raw are
authentication/development-lineage evidence only; the absent D1R11
calibration/holdout outcomes remain absent. R8 uses the fixed context table,
source snapshot/spec fields, and exact causal source prefix only as a fresh
restart blueprint.

## Fixed pairs and partitions

The four already consumed R2/R4/R6 development pairs are:

```text
p5_q1_a0p750_gap2_settle4
p5_q1_a0p900_gap4_settle4
p9_q2_a0p750_gap4_settle4
p9_q2_a0p900_gap3_settle4
```

They are not rerun. Their exact 304 responses remain training-only.

R8 adds the other eight D1R11 training pairs:

```text
p5_q1_a0p750_gap3_settle4
p5_q2_a0p750_gap2_settle4
p5_q2_a0p750_gap4_settle4
p5_q2_a0p900_gap3_settle4
p9_q1_a0p750_gap3_settle4
p9_q1_a0p900_gap2_settle4
p9_q1_a0p900_gap4_settle4
p9_q2_a0p900_gap2_settle4
```

The fixed calibration pairs are:

```text
p5_q1_a0p900_gap3_settle4
p5_q2_a0p750_gap3_settle4
p9_q1_a0p900_gap3_settle4
p9_q2_a0p750_gap3_settle4
```

The fixed fresh holdout pairs are:

```text
p5_q1_a0p750_gap4_settle4
p5_q2_a0p900_gap4_settle4
p9_q1_a0p750_gap4_settle4
p9_q2_a0p900_gap4_settle4
```

Every pair has exactly `plus_first` and `minus_first` members. Pair, history,
partition, prefix, target ID, regime, delay, and slew labels are orchestration
and audit fields only. They may never enter the controller or model.

## Fixed action matrix and rollout counts

Each newly executed context has exactly one zero baseline and 38 signed probe
rollouts:

```text
issue state 10
  canonical matrix, four directions, two signs                    8

issue states 14, 18, 22, each
  canonical matrix, four directions, two signs                    8
  replacement 1.5x direction zero, two signs                      2

per context
  baseline                                                         1
  responses                                                       38
  total                                                           39
```

The exact matrices remain:

```text
canonical digest
  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
replacement digest
  69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8
replacement change
  direction zero only, exactly 1.5x canonical
```

The maximum new campaign is:

```text
training extension   8 pairs / 16 contexts x 39          624 raw
calibration          4 pairs /  8 contexts x 39          312 raw
fresh holdout        4 pairs /  8 contexts x 39          312 raw
maximum new total                                      1,248 raw
```

The training response bank after the training extension is:

```text
existing consumed development responses                         304
fresh training-extension responses                 16 x 38 = 608
training responses                                               912
training pairs / contexts                                    12 / 24
```

Calibration and holdout each contain `304` responses over four whole pairs.
All new identities, controller instances, TSC processes, raw, and snapshots
must be fresh.

## Controller and physical action semantics

For each rollout the controller must reproduce the exact source physical
state, action, and controller-trace prefix through task step 9. The future R17
controller is forbidden.

After the prefix:

1. Baselines command exact zero normalized increment through the unchanged
   horizon.
2. Probes command exact zero until their fixed issue step.
3. The issue coordinate is authenticated against its fixed matrix, direction,
   sign, and scale, then converted through the exact Card15 boundary.
4. The controller stores the causal pre-issue center and restores that exact
   center at the next task step.
5. It commands exact zero increment thereafter.

Every issue and cancellation must pass both the `0.24` online cancellation
margin and original `0.25` normalized incremental cap. Total normalized action
must remain within `[-1,1]`, desired/applied current cosine at least `0.98`,
relative off-basis residual at most `0.10`, and measured current utilization
at most `0.55`. Saturation, clipping, solver failure, nonfinite output, or an
unreproduced Card15 target is a hard safety failure.

The normal horizon remains state 35 and the weak horizon state 37. A longer
arrival deadline is forbidden.

## Causal response model

The R7R2 causal descriptor and model are unchanged:

- normalized visible `[R,Z,vR,vZ,Ip]` history at offsets `0..22`, left padded
  only with already observed state zero;
- the 23-element availability mask;
- numeric target offsets and normalized issue clock;
- only the already revealed scalar request scale `1.0` or `1.5`;
- eight sign/direction heads;
- training-only standardization and PCA;
- per-lag RBF kernel ridge heads;
- the fixed last-eight-point degree-two lag-26/27 tail;
- exact 10 ms R/Z integration.

The candidate grid remains:

```text
PCA rank                    [4, 8, 12]
RBF median multiplier       [0.5, 1.0, 2.0]
kernel ridge                [1e-6, 1e-3, 1e-1]
total candidates            27
```

Pair, history, partition, prefix, target ID, regime, delay/slew labels,
source/current coil or wire currents, source outcomes/actions, hidden state,
future actions, and future measurements are forbidden. The controller and
model must expose explicit zero counts for all forbidden inputs.

## Mandatory phase ordering

### Phase 0: zero-TSC source and full-spec gate

Before a plant step, both implementations must authenticate the package,
R2/R4/R6 source closure, D1R11 table/spec/state/manifest, exact pair split,
all 1,248 prospective identities, source snapshots, issue/cancel schedules,
matrix coordinates, static Card15 algorithm/configuration representability,
declared safety thresholds, horizons, and formal timing. The physical
issue-time centers at states 14/18/22 do not exist before each fresh zero
baseline is run; their actual issue and cancellation margins are therefore
hard-gated row by row in the corresponding execution phase, not claimed by
Phase 0. Any Phase-0 failure stops with zero new TSC.

### Phase 1: training extension and model hash

Execute exactly the 624 training-extension tasks. Both raw audits must pass
all runtime, restart, prefix, causality, action, current, snapshot, inventory,
and corruption gates.

Combine their 608 responses with the immutable 304-response development bank.
Nested candidate selection and outer prediction are by whole physical pair
over all 12 training pairs. Every one of the 912 outer predictions must pass:

```text
relative L2 error                              <= 0.75
response cosine                                >= 0.80
predicted/actual peak ratio              within [0.50, 1.50]
maximum scaled point error                      <= 0.1
```

The training OOF residual precursor uses the unchanged physical floor plus
two times the componentwise maximum residual and must fit within
`[0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]`.

Actual and predicted signal must pass `912/912` at `>=0.0025`. Canonical and
operational predicted four-direction geometry must each pass all 192 fixed
context/issue/sign branches at rank four and condition at most 20. The same
actual-response geometry is audited independently.

Only a complete pass fits the selected candidate on all 12 training pairs and
hash-freezes the model. Calibration raw must not exist before that hash.

### Phase 2: calibration and tube hash

Execute exactly 312 calibration tasks only after the model hash. The model
and preprocessing remain byte-identical. All 304 frozen-center predictions
must pass the same response gates, signal gate, and 64 canonical plus 64
operational geometry branches.

The calibrated componentwise tube is the physical floor plus twice the
maximum absolute residual over training OOF and calibration predictions. It
must remain within the unchanged caps. The model and tube are hash-frozen
before any holdout raw exists.

### Phase 3: fresh holdout

Execute exactly 312 holdout tasks only after both hashes. All raw/safety gates
precede scientific evaluation. Every one of the 304 holdout predictions must
pass the unchanged center gates and lie inside the frozen calibrated tube.
Actual and predicted signal and both 64-branch geometry families must pass.
Neither model nor tube may be refit, rescaled, or selected after a holdout
value is opened.

## Raw, snapshot, and independent audit gates

For every executed phase require:

- expected raw count and byte inventory with a canonical digest;
- strict JSON.GZ parse and finite complete trajectory;
- real `gotsc`/TSC execution evidence;
- exact authentic restart snapshot and source physical state;
- exact source state/action/controller-trace prefix;
- causal issue and stored-center cancellation trace;
- exact requested coordinate, Card15 target, applied current, and readback;
- zero forbidden controller/model fields;
- no runtime, plant, solver, saturation, clipping, action, current, raw,
  snapshot, or reporting error;
- primary and structurally independent raw-to-route agreement.

Large raw and row-level model outputs remain server-side. Only compact
manifests, summaries, audits, and complete logs may be copied locally.

## Formal timing and scientific boundaries

The immutable contract remains:

```text
normal slew: arrive by state 25, evaluate through state 35
weak slew:   arrive by state 27, evaluate through state 37
R/Z tolerance 0.03 m; speed 0.1 m/s; Ip 10,000 A; streak 3
```

Formal tracking in R8 is diagnostic only. R8 is identification, not a control
or long-hold experiment. Cross-sign symmetry and matched hidden-history
response are reported but are not substituted for sign-split center and
whole-pair holdout gates.

All R2/R4/R6/R8 probes are forbidden from expert datasets.

## Frozen routes

```text
source/package/spec/offline mismatch
  PARTITIONED_BROAD_RESPONSE_SOURCE_FAIL_NO_TSC

training runtime/restart/action/raw failure
  PARTITIONED_BROAD_RESPONSE_TRAINING_EXECUTION_FAIL_STOP

training response/model/geometry failure
  PARTITIONED_BROAD_RESPONSE_TRAINING_MODEL_FAIL_STOP

calibration runtime/restart/action/raw failure
  PARTITIONED_BROAD_RESPONSE_CALIBRATION_EXECUTION_FAIL_STOP

calibration center/tube/geometry failure
  PARTITIONED_BROAD_RESPONSE_CALIBRATION_MODEL_FAIL_STOP

holdout runtime/restart/action/raw failure
  PARTITIONED_BROAD_RESPONSE_HOLDOUT_EXECUTION_FAIL_STOP

holdout center/tube/geometry failure
  PARTITIONED_BROAD_RESPONSE_HOLDOUT_MODEL_FAIL_REDESIGN

all gates pass
  PARTITIONED_BROAD_RESPONSE_HOLDOUT_PASS_MULTIPULSE_DESIGN_REQUIRED
```

A pass authorizes only a separately preregistered fresh authentic multipulse
superposition/interaction sentinel. It does not authorize real MPC, expert
data, BC, DAgger, bounded residual RL, unseen targets, continuous actuator or
plant variation, measurement noise, disturbance recovery, or long hold.
