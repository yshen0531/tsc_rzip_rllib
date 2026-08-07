# Stage4.2R3c3T13S24D1R14R8R5 context-robust observer holdout design

Frozen prospectively after final R8R4 primary/independent agreement, but
before any R8R5 fit, residual recomputation, tube value, prediction metric,
artifact, route, new TSC trajectory, or blind-holdout outcome is produced.

## Purpose and scientific boundary

R8R4 established that its causal observer point family is practically
accurate on the consumed development envelope: all 480 outer origins passed
the frozen point gate and the maximum scaled point error was 0.12738.  Its
single aggregate-quantile tube contained 457/480 origins, but five of 32
history contexts fell below their prospectively fixed 90% containment floor.
The tube widths were well below every finite exclusion cap.  R8R4 therefore
remains a development FAIL; its blind holdout was not opened.

R8R5 is a new identity that treats all R8R4 development outcomes as consumed
development data.  It fixes the already selected point model, replaces only
the development tube calibration with a context-robust global construction,
and, if all development and independent gates pass, evaluates that frozen
model and tube on the eight still-unopened baseline histories.  It does not
retune R8R4, relabel its result, add a predictor, or use a heldout outcome.

R8R5 is an observer qualification stage.  It is not an action-response
experiment, innovation adapter, controller, MPC, formal tracking PASS,
Gate A result, expert-data campaign, BC, DAgger, or residual RL result.

## Immutable source authentication

R8R5 must authenticate at least the following R8R4 evidence before doing any
fit or metric work:

```text
R8R4 required route
  FRESH_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT
R8R4 stage manifest SHA-256
  630d749fc9956e60cf751a8248550c9be5b3d5608a9c012c3c9f05b27a98a9a4
R8R4 final state SHA-256
  617c6ea2e2ae81d5d1ad9f0de2f331a1b0d19caa3031dc76e4714ecc4c417015
R8R4 development raw count / bytes / digest
  8 / 245279
  8d0d6c2c8f7e4e8436f9ef958fb30e4276823a8004fbab97b8c50d71b1ed3f66
R8R4 primary raw / independent raw SHA-256
  8d967ef68ea13e2ae42fc3afe6f566b976f26b633976049e8e7c1a4c0092487c
  b720bffd19039c339b57e0a596802991bbe3e17d24d15408b6244733dfa490ee
R8R4 primary detailed / summary / independent model SHA-256
  af8cb6d75a435ecd96948b4c15a2e1929c98527edd5483c8f29c0c6394125dac
  bde614d6ac34535d5f22f187925723969921e8333b41d429a32e0719cb8b3bfd
  12ee920fb0d49d46285bba31a443a24e09a5b6b9b3b1d0b5ddc61560a20fa86b
R8R4 holdout raw count
  0
R8R4 model/tube file count
  0
```

The exact R8 and R8R3 sources transitively authenticated by R8R4 remain
immutable.  R8R5 may read R8 training baseline evidence and R8R4 development
raw but may not modify any source raw, snapshot, manifest, state, or audit.

## Consumed development and fixed point model

The R8R5 development bank is exactly the sixteen physical pairs already used
by R8R4 development: twelve authenticated R8 training pairs plus the four
R8R4 development pairs.  There is no new development TSC.

The 353-dimensional causal input, origin eligibility, visible-state
reconstruction, twelve-state target, and exact R/Z kinematic integration are
unchanged from R8R4.  Forbidden predictor inputs remain forbidden, including
pair/history/source/regime labels, experiment IDs, hidden or wire current,
matched future, future measurement, future action/current, and outcomes.

R8R5 fixes the point candidate before recomputation to the R8R4 consumed-
development selection:

```text
family                    linear
PCA rank                       32
ridge                       1e-6
bandwidth multiplier           0
```

There is no R8R5 candidate bank or post-result selection.  Each development
outer fold holds both histories and every origin of one complete physical
pair, fits the fixed candidate on the other fifteen pairs, and predicts only
the held pair.  A development point PASS requires the unchanged R8R4 gates:

```text
point caps [R,Z,vR,vZ,Ip] = [0.003 m, 0.003 m, 0.02 m/s, 0.02 m/s, 1000 A]
finite exclusion caps     = [0.01 m, 0.01 m, 0.05 m/s, 0.05 m/s, 3000 A]
at least 95% of all origins pass every point cap
at least 95% of prescribed issue origins pass every point cap
at least 90% per history context
at least 3/4 prescribed issue origins per history context
zero finite-exclusion violation
```

After this outer validation, the same fixed candidate is fitted once on all
sixteen development pairs.  That all-development fit is not validation.

## Prospectively fixed context-robust global tube

The tube is calibrated only from the fixed candidate's sixteen whole-pair
out-of-fold residual sets.  For each of twelve future lags and five physical
components, compute:

```text
base = NumPy quantile(abs residual, 0.95, method="higher") + floor
floor [R,Z,vR,vZ,Ip] = [1e-9 m, 1e-9 m, 1e-7 m/s, 1e-7 m/s, 1e-4 A]
```

For every origin row, define its ratio as the maximum of its 60 absolute
residual values divided by the corresponding base width.  Compute the
`method="higher"` 95th percentile of all row ratios and, separately, the
`method="higher"` 90th percentile in each evaluator-only history context.
The one global scalar and final global tube are fixed as:

```text
calibration_ratio = max(global_q95, every_context_q90)
scalar            = max(1.0, 1.25 * calibration_ratio)
tube              = scalar * base
```

The factor 1.25 is a prospectively fixed blind-holdout reserve.  It cannot be
changed after a development or holdout value is produced.  Context labels
are used only to calibrate the one shared global scalar; they are neither
model inputs nor deployment-time tube selectors.

Development containment is a calibration audit, not independent evidence.
It must still reproduce at least 95% aggregate and 90% per-context
containment, retain every miss, remain finite, and keep all 60 widths inside
the unchanged finite exclusion caps.  A cap failure stops before holdout.

## Still-blind holdout

Only after primary and structurally independent development recomputations
agree exactly may R8R5 freeze model and tube SHA-256 values and authorize the
following four unopened physical pairs, both histories each:

```text
p5_q1_a0p750_gap4_settle4
p5_q2_a0p900_gap4_settle4
p9_q1_a0p750_gap4_settle4
p9_q2_a0p900_gap4_settle4
```

These eight specifications run under a new R8R5 identity and new raw paths.
They inherit the exact authenticated prefix through task step 9, command
zero normalized incremental action thereafter, retain constant commanded
current from state 10 onward, and use the unchanged formal 370 ms envelope.
No probe or nonzero post-prefix action is added.

The frozen model and tube are applied without refit, recentering,
recalibration, scalar expansion, candidate selection, row deletion, or
threshold change.  Holdout PASS requires the exact point, exclusion, 95%
aggregate, 90% per-context, and 3/4 issue gates above, plus at least 95%
aggregate and 90% per-context frozen-tube containment.

## Hard execution and integrity gates

Every attempted holdout trajectory must be recorded.  These gates remain
all-or-nothing:

```text
fresh authentic restart and exact source physical prefix
causal trace and action prefix
exact zero future incremental action
constant future commanded applied-current target
Card15 representability and exact actuator boundary
finite full-horizon solver/plant execution
no saturation, abnormal state, or forbidden input
maximum total normalized action <= 1.0
maximum current utilization <= 0.55
strict raw parse, complete snapshot/manifest authentication
no later plant advance after a structured stop
model and tube hashes unchanged before and after holdout
```

Runtime or integrity failures are classified separately from point/tube
failures.  Formal tracking remains diagnostic only and cannot change the
observer route.

## Independent recomputation and strict order

A structurally independent implementation must separately rebuild source
authentication, the fixed-candidate whole-pair fits, causal features,
kinematic outputs, context-robust tube, point/tube metrics, raw inventories,
hashes, and route.  It may share only immutable low-level parsing and visible-
state helpers, not primary model, prediction, tube, gate, or routing code.
Numerical agreement uses relative tolerance `1e-10` and absolute tolerance
`1e-12`; identities, counts, booleans, hashes, and routes agree exactly.

The only permitted order is:

1. authenticate immutable sources and confirm R8R4 holdout raw is zero;
2. recompute development with the fixed candidate and new tube, zero TSC;
3. serialize and hash the all-development model and tube only after PASS;
4. independently reproduce development and artifact hashes;
5. authorize exactly eight new-identity holdout baselines;
6. independently audit holdout raw and snapshots;
7. score the unchanged frozen model and tube; and
8. independently reproduce the final route.

No blind holdout may run after a development or independent failure.

## Frozen routes

```text
source/authentication/development reconstruction failure
  CONTEXT_ROBUST_CAUSAL_OBSERVER_SOURCE_FAIL_NO_TSC

fixed point or context-robust tube development failure
  CONTEXT_ROBUST_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT

holdout runtime/restart/causality/Card15/current/raw/snapshot failure
  CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_EXECUTION_FAIL_STOP

blind-holdout point or frozen-tube failure
  CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN_REQUIRED

all development, blind-holdout, and independent gates pass
  CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_PASS_COMBINED_ADAPTATION_FREEZE_REQUIRED
```

## Formal timing and downstream boundary

The immutable arrival deadlines, 350/370 ms formal hold endpoints, 30 mm
R/Z tolerance, 0.1 m/s speed threshold, 10 kA Ip threshold, and arrival
streak remain unchanged.  The 120 ms observer prediction window never moves
a formal deadline.

Every R8R5 trajectory and every R8/R8R4 source trajectory used here is
forbidden from expert, BC, DAgger, and RL datasets.  Even a blind-holdout
PASS authorizes only a separately prospectively frozen combined causal
observer/innovation-adaptation validation.  It does not authorize a
controller, MPC, Gate A, expert data, BC, DAgger, or residual RL.
