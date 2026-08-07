# Stage4.2R3c3T13S24D1R14R8R7 fresh multipulse static-observer interaction sentinel design

Frozen prospectively on 2026-08-07 after R8R6 primary/independent agreement
and before any R8R7 implementation, derived metric, model/tube artifact, raw
result, or TSC trajectory was created or inspected.

## 1. Question and boundary

R8R6 qualified the fixed causal no-action observer and found no measurable
benefit from its frozen one-step innovation correction. It selected the static
observer and disabled adaptation. R8R1 had already shown that its fixed
PCA4/RBF-median-times-two/ridge-0.1 response candidate at 40 ms was useful but
did not satisfy the original all-row response and geometry gates:

```text
40 ms response rows passing              832/912
maximum scaled point error               0.03469142898416007
response tube precursor cap              PASS
predicted canonical/operational geometry 192/192, 192/192
actual canonical/operational condition   190/192, 191/192
```

Those are immutable development results; R8R7 does not relabel R8R1 as a
PASS. R8R7 asks whether the qualified static observer plus that fixed 40 ms
action-response candidate can predict authentic, fresh, non-overlapping
multipulse interactions accurately enough to justify a separately designed
receding-horizon controller.

R8R7 is a safety and interaction-model sentinel. It is not an MPC, formal
control, robustness qualification, Gate A, expert-data, BC, DAgger, or RL
stage. A PASS can authorize only a separately frozen MPC design.

## 2. Immutable source authentication

Before specifications or model artifacts are created, primary and independent
paths must authenticate:

1. the exact R8 configuration and immutable 912-row, 12-pair response bank;
2. R8R1's fixed candidate, 20 whole-pair folds, 40 ms metrics, source/raw
   contracts, and primary/independent hashes;
3. the exact final R8R6 route
   `CAUSAL_ONE_STEP_INNOVATION_NO_MEASURABLE_GAIN_STATIC_ROBUST_OBSERVER_SENTINEL_REQUIRED`;
4. the R8R6 static model SHA-256
   `3ba16449086097a42513987df97c95ec6d6d0d35d572e73992fa5eafdfc15519`;
5. the R8R6 static tube SHA-256
   `747a6c24f9abed8a4ec6784e4699c7ebe557a049bb11e10ea9a1d5ca0254b8ea`;
6. the R8R6 innovation-contract SHA-256
   `272c5979f0b806f228e335bbbb8db1f57df623822d8a8ffe3c797ca96b4203f5`,
   which must disable adaptation; and
7. every source snapshot, restart state, prefix, current/action trace, raw
   inventory, stage manifest, and state needed for the 16 contexts.

Any mismatch is a source/deployment failure and authorizes zero R8R7 TSC. No
implementation may repair, rewrite, or substitute a source artifact.

## 3. Frozen fresh contexts

The action-response outcomes for these eight former R8 calibration/holdout
physical pairs have never been run:

```text
p5_q1_a0p900_gap3_settle4
p5_q2_a0p750_gap3_settle4
p9_q1_a0p900_gap3_settle4
p9_q2_a0p750_gap3_settle4
p5_q1_a0p750_gap4_settle4
p5_q2_a0p900_gap4_settle4
p9_q1_a0p750_gap4_settle4
p9_q2_a0p900_gap4_settle4
```

Both authenticated R3c1 history members are used for every pair, producing 16
contexts. Pair ID, history member, prefix, target ID, delay/slew labels, and
partition are evaluator-only strata and forbidden predictor inputs.

## 4. Fixed real-TSC matrix

R8R7 may create at most 48 new authentic trajectories in two irreversible
phases:

```text
phase 1: fresh zero-future-action baselines    16 contexts * 1 = 16
phase 2: fresh fixed multipulse interactions  16 contexts * 2 = 32
maximum total                                             48
```

Phase 1 must complete and pass primary and independent restart/raw and frozen
observer gates before phase 2 is authorized. Failure leaves all multipulse
outcomes unopened.

Each rollout uses a fresh controller and TSC process, authentic restart, the
exact inherited physical prefix through task step 9, and the unchanged episode
endpoint. Baselines issue zero future action from task step 10.

Multipulse issue task steps are `[10, 14, 18, 22]`; exact stored-center
cancellation occurs at `issue + 1` and zero action at `issue + 2`. Pulses never
overlap. Only the R8 canonical-scale matrix is allowed:

```text
canonical matrix SHA-256  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
canonical scale           1.0
replacement direction     forbidden
```

The two schedules are fixed as:

```text
schedule A directions [0, 1, 2, 3], signs [+1, -1, +1, -1]
schedule B directions [3, 2, 1, 0], signs [+1, -1, +1, -1]
```

Every context therefore has eight issue windows and every direction appears
once with each sign. Phase 2 has 128 issue windows, 32 per direction and 64 per
sign.

## 5. Fail-closed action and safety contract

Before every issue and cancellation, R8R7 reconstructs the exact Card15 target
and readback and checks:

```text
maximum incremental normalized action L-infinity       0.25
maximum online cancellation incremental L-infinity     0.24
maximum total normalized action absolute value          1.0
maximum current utilization                             0.55
minimum desired/applied current cosine                  0.98
maximum relative off-basis residual                     0.10
exact stored-center cancellation                        required
exact zero target-jump net                              required
exact inherited physical prefix                         required
fresh controller and fresh TSC process                  required
future R17 execution after task step 9                  forbidden
```

An unsafe or non-representable candidate is rejected before plant advance and
no later plant step may occur. That is an execution/schedule failure, not a
model error or plant-control conclusion.

## 6. Frozen predictors

### 6.1 Static causal observer

The no-action center is exactly the byte-authenticated R8R6 selected static
observer. Feature normalization, causal history offsets, integration, and tube
are unchanged. Innovation and all online adaptation are disabled. No R8R7 raw
may refit it. At each origin it receives only allowed actually available
visible history, past actions, applied-current history, desired target, and
causal clock fields. Only forecast lags 1..4 are used.

### 6.2 Fixed 40 ms response model

Before phase 1 and without any R8R7 outcome, exactly one all-data deployment
artifact is fit on the immutable R8 912-row bank:

```text
horizon                  relative lags 1..4 (40 ms)
PCA rank                 4
RBF bandwidth            2.0 * median distance
ridge                    0.1
action heads             direction and sign only
candidate selection      forbidden
R8R7 data in fit         forbidden
validation claim         false
```

Primary and structurally independent implementations must first reproduce the
R8R1 20-fold 40 ms predictions and metrics, then independently serialize the
same deployment model and hash. The full-data fit is not validation.

At an issue origin, the response descriptor is the exact R8 causal descriptor
rebuilt from the observed prefix: visible history offsets 0..22, availability
mask, desired target, and relative issue clock. The only action conditioning is
the already proposed and safety-checked canonical direction/sign. Future
measurement, future TSC readback, matched-baseline future, pair/history label,
and post-result choice are forbidden.

### 6.3 Combined causal forecast

For each issue origin, the four-step absolute forecast is:

```text
static R8R6 absolute forecast from the actual causal prefix
+ fixed R8 response prediction for the new exact issue/cancel pulse
```

Prior pulses enter only through the observed causal prefix. There is no
interaction correction, oracle baseline substitution, post-result scale
change, model selection, or online innovation.

## 7. Frozen uncertainty tube

Before phase 1, the response half-width is recomputed from immutable R8R1
20-fold out-of-pair 40 ms residuals. For each lag/component:

```text
response half-width = response physical floor
                      + 2.0 * maximum absolute OOF residual
combined half-width = R8R6 static half-width + response half-width
```

The combined tube is frozen before R8R7 raw and must stay within:

```text
[R, Z, vR, vZ, Ip] = [0.01 m, 0.01 m, 0.05 m/s, 0.05 m/s, 3000 A]
```

A pre-TSC cap failure stops with zero new TSC. R8R7 raw may neither widen nor
recenter the tube.

## 8. Phase-1 baseline gate

The 16 baselines contribute four 40 ms windows at origins `[10, 14, 18, 22]`,
exactly 64 windows. The static forecast/tube are used without refit. A window
point-passes only when all 20 values are within:

```text
[R, Z, vR, vZ, Ip] = [0.003 m, 0.003 m, 0.02 m/s, 0.02 m/s, 1000 A]
```

Required:

```text
complete authentic baseline execution                   16/16
restart/source prefix/causality/raw/snapshot integrity   16/16
finite-exclusion violations                               0
aggregate point-pass windows                         >= 61/64
point-pass windows in every context                    >= 3/4
aggregate static-tube containment                     >= 61/64
static-tube containment in every context                >= 3/4
static tube within frozen caps                             true
primary/independent numerical and outcome agreement        true
```

Finite-exclusion caps are `[0.01, 0.01, 0.05, 0.05, 3000]`. Phase-1 raw is
sentinel evidence, not training data.

## 9. Phase-2 multipulse gate

The 32 multipulse rollouts contribute 128 issue-origin windows. Point-pass
uses the phase-1 practical caps; containment requires every value inside the
already frozen combined tube.

Required:

```text
complete authentic multipulse execution                 32/32
restart/source prefix/causality/raw/snapshot integrity   32/32
safe exact issues                                       128/128
safe exact cancellations                                128/128
rejected applied candidates                                   0
forbidden-input use                                           0
finite-exclusion violations                                   0
aggregate point-pass windows                         >= 116/128
point-pass windows in every context                    >= 7/8
point-pass windows for every direction                >= 28/32
point-pass windows for each sign                      >= 56/64
aggregate combined-tube containment                   >= 116/128
tube containment in every context                       >= 7/8
tube containment for every direction                  >= 28/32
tube containment for each sign                        >= 56/64
combined tube within frozen caps                           true
primary/independent numerical and outcome agreement        true
```

Every miss is retained. These finite thresholds do not claim zero error,
global optimality, or unlimited robustness.

## 10. Formal timing and interpretation

Every trajectory is scored under the unchanged 250/270 ms arrival and 350/370
ms hold endpoints, 30 mm R/Z tolerance, 0.1 m/s speed threshold, unchanged Ip
threshold, and unchanged arrival streak. Formal tracking is diagnostic because
fixed pulses are not an MPC. The 40 ms predictor does not alter any deadline.

Independent code must reconstruct specs, authenticate sources/raw, rebuild
descriptors, fit the fixed response model, derive the tube, recompute every
prediction/count, and derive the route without importing the primary
scientific evaluation. All material artifacts and inventories are hashed;
large raw/detailed evidence stays on the server.

## 11. Routes and stopping rules

```text
source/offline/tube failure before phase 1:
  FRESH_MULTIPULSE_INTERACTION_SOURCE_FAIL_NO_TSC
phase-1 execution or integrity failure:
  FRESH_MULTIPULSE_BASELINE_EXECUTION_FAIL_STOP
phase-1 observer scientific failure:
  FRESH_MULTIPULSE_BASELINE_OBSERVER_FAIL_STOP
phase-2 execution, safety, or integrity failure:
  FRESH_MULTIPULSE_ACTION_EXECUTION_FAIL_STOP
phase-2 predictor scientific failure:
  FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_FAIL_ACTION_MODEL_REDESIGN_REQUIRED
all frozen gates pass:
  FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_PASS_MPC_DESIGN_REQUIRED
```

No failed or partial phase may resume under changed semantics. Changed
schedules, amplitudes, features, models, tubes, gates, or action semantics need
a new identity and prospective design. All R8R7 trajectories are forbidden
from expert datasets, BC, DAgger, residual fitting, and RL. MPC, Gate A, and
learning remain blocked until their own prospective stages pass.
