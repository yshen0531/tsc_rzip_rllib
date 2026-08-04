# Stage4.2R3c3T13S24D1R14 zero-baseline signed-excitation sentinel design

## Frozen status and narrow question

This design is frozen after the final D1R13 result and before D1R14 code,
package, output, Ray task, `gotsc`, TSC, controller, or plant execution.

D1R14 asks one narrow question: about the authenticated D1R13 zero-increment
post-calibration trajectory, can four exact-Card15 signed single-step
directions be issued and immediately cancelled safely, and do their measured
odd responses provide a non-vacuous, rank-four, reasonably conditioned local
response geometry across all eight contexts?

It is an excitation safety/geometry sentinel. It is not a transition model,
time-distributed identification campaign, MPC, closed-loop-control,
robustness, long-hold, expert-data, BC, DAgger, or RL experiment.

## Immutable sources

Authenticate the exact final D1R13 run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r13_runs/
stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_20260804_df3910f_v1

raw count / bytes
  8 / 241,738

raw inventory digest
  f9b4dd9259736ebe2d26f9fcfd06bb0497be69a886de7ecc8d359009992f1c0a

execution-package / independent-audit checkpoints
  df3910f / 23148e9

final-result / independent-audit hashes
  f8570641d5dd4e41962660712790bcd60c4ce8bf6a33e1f360235ffc8c69b9ca
  bd778f42d8755e8b45d572e895cefb171acad8f0fa688b238fd1acb3402e5ee4
```

Also authenticate the complete D1R11 training inventory and the original
eight selected D1R11 baseline sources solely to reproduce task steps 0--9.
D1R11 calibration and holdout remain unopened. Old D1R11 signed trajectories
may be read for source authentication and retrospective design evidence but
may not be treated as D1R14 zero-baseline responses.

## Why fresh zero-baseline trajectories are mandatory

The accepted server-side retrospective evidence used only existing D1R11 and
D1R13 raw. It found a maximum old-feedback even/odd ratio of `14.0321503`, a
maximum matched-history relative odd difference of `0.5221102`, a maximum
zero-versus-R17 divergence of `2.6781085`, and post-state-10 R17 actions up to
`0.3652533`. D1R11 signed paths therefore combine the requested excitation,
continuing R17 feedback, evolving Card15 centers, and plant response. They are
not a valid signed perturbation about D1R13's zero baseline.

D1R14 creates a fresh zero baseline and fresh signed trajectories under one
shared, explicitly zero post-calibration action policy.

## Frozen task matrix

Use the same eight D1R13 contexts. For each context execute exactly:

```text
one fresh zero-increment baseline
four direction coordinates x two signs = eight fresh signed probes
total per context = 9
total authentic trajectories = 8 x 9 = 72
```

Every trajectory has a fresh experiment identity, controller, TSC process,
raw file, and authenticated restart. Ray campaign capacity is fixed at 72
before launch; batching may limit concurrently live actors without changing
the fixed total capacity or task identities.

The four physical directions are frozen as:

```text
direction 0  D1R11 mode 0 with coil 8 component removed
direction 1  isolated D1R11 mode 0 coil 8 component
direction 2  D1R11 mode 1
direction 3  D1R11 mode 2
```

Each direction uses requested coordinate amplitude `0.25` with signs `+1`
and `-1`. The exact mode arrays and all exact-Card15 calculations must come
from the authenticated D1R11 controller implementation; rounded or copied
arrays are forbidden.

## Controller and action contract

For task steps 0 through 9, every D1R14 controller must execute the unchanged
D1R11/D1R13 prefix. Physical state, action, and controller trace through
state 10 must reproduce the matching source baseline, excluding only
non-semantic runtime timing fields.

After that prefix:

```text
baseline role
  task step 10 onward: exactly [0.0] * 14

signed-probe role
  task step 10: issue one exact-Card15 signed coordinate relative to the
                current zero-increment center
  task step 11: restore the exact stored pre-issue center
  task step 12 onward: exactly [0.0] * 14
```

The issue and cancellation are single task-step commands. There is no R17
solve/reference advance, future source action, terminal regulator, additional
probe, or adaptive direction/sign choice after task step 9. Direction and
sign are fixed in each fresh controller at construction, not selected from
online state or outcome.

The online controller may use only the current task-step index, its fixed
direction/sign coordinate, causal current action center required by the exact
Card15 issue/cancel operation, and its own completed prefix history. It may
not read pair/history/prefix/target/delay/slew/partition labels, source or
current result objects, source/current coil or wire-current measurements,
hidden plant state, future measurements/actions, phase/manifold labels, or
another trajectory.

Every issue and cancellation must retain the unchanged incremental-action,
total-action, exact-Card15/current, saturation/clipping, and current-
utilization gates. A candidate that would violate them must be rejected
before plant advance and causes the frozen safety-fail route.

## Immutable timing

The timing contract remains:

```text
slew 1.0  arrive by state 25; evaluate through state 35
slew 0.9  arrive by state 27; evaluate through state 37
R/Z tolerance 30 mm; speed threshold 0.1 m/s
Ip threshold and arrival streak unchanged
```

The D1R14 horizon is exactly the existing 35/37-state formal horizon. Formal
tracking is recomputed and reported as a diagnostic only. There is no early
success exit and no timing expansion or long-hold reinterpretation.

## Offline and execution gates

Before TSC:

- authenticate the D1R13 run, eight raw inventory entries, stage state,
  manifest, final result, independent audit, and eight snapshot manifests;
- authenticate the complete D1R11 training inventory and eight source
  baseline raw/prefix identities;
- require exactly 72 unique specs: eight baselines and 64 signed probes;
- require nine roles for each of eight contexts and four cases per horizon
  for every role;
- require exact source state/action/trace prefix reproduction in pure replay;
- prove exact zero baseline actions, exact-Card15 issue at task step 10,
  exact stored-center cancellation at task step 11, and exact zero afterward;
- prove that no forbidden controller field or current-run future value is
  admitted; and
- pass local, empty-directory package, and installed-server validation.

After authentic execution, all safety gates are mandatory:

```text
strict raw / exact identity                             72 / 72
fresh controller / fresh TSC                            72 / 72
restart snapshot and state-0 exact                      72 / 72
physical state/action/trace prefix through state 10     72 / 72
causal calibration complete                             72 / 72
full 35/37-state horizon                                72 / 72
fresh zero baseline reproduces D1R13 zero path            8 / 8
baseline post-prefix actions and current increments       all zero
signed issue event exact                                64 / 64
signed stored-center cancellation exact                 64 / 64
post-cancellation actions/current increments              all zero
finite R/Z/Ip, coil and wire-current records               all
runtime / plant / solver / saturation / clipping errors      0
forbidden controller inputs / future values                  0
raw, snapshot, manifest, inventory corruption                0
maximum current utilization                          <= 0.55
```

Any safety/prefix/execution failure blocks response-geometry acceptance even
if the remaining trajectories appear informative.

## Frozen response construction and geometry gates

For each context and direction, use the matched fresh baseline `b`, positive
trajectory `p`, and negative trajectory `m`. From states 11 through the
unchanged horizon construct the normalized visible-output vector using:

```text
[R / 0.03, Z / 0.03, vR / 0.1, vZ / 0.1, Ip / 10000]
```

Subtract the common state-10 origin before response comparison. Define:

```text
odd  = 0.5 * (p - m)
even = 0.5 * (p + m) - b
```

The following prospective gates are fixed:

1. Every one of the 32 context-direction odd columns has maximum normalized
   state magnitude at least `0.005` over states 11 through horizon.
2. Every signed pair has `max_abs(even) / max_abs(odd) <= 0.50` using the
   same flattened five-output window and a fail-closed zero denominator.
3. For each of the eight contexts, flatten each of the four odd response
   columns over the complete state-11-through-horizon window, normalize each
   column to unit L2 norm, and assemble one matrix with four columns.
4. Each matrix must have numerical rank four at relative singular-value
   tolerance `1e-10`.
5. Each matrix condition number must be at most `20.0`.

Matched hidden-history differences are reported per pair and direction but
are not required to vanish. D1R14 is explicitly testing context-dependent
local geometry, not asserting that hidden-history response is identical.

The four-direction geometry is a sentinel for non-vacuous separability only.
It is not a qualified predictor and may not be used directly as an MPC model.

## Frozen routes

```text
ZERO_BASELINE_EXCITATION_OFFLINE_FAIL_NO_TSC
ZERO_BASELINE_EXCITATION_RUNTIME_OR_PREFIX_FAIL_STOP
ZERO_BASELINE_EXCITATION_SAFETY_FAIL_REDESIGN_REQUIRED
ZERO_BASELINE_EXCITATION_GEOMETRY_FAIL_REDESIGN_REQUIRED
ZERO_BASELINE_EXCITATION_SENTINEL_PASS_TIME_DISTRIBUTED_ID_DESIGN_REQUIRED
```

The first matching failure route wins. An offline failure creates no TSC
evidence. Runtime/prefix and safety failures are classified separately from
response-geometry/design failures. Formal tracking never controls the route.

Even a full D1R14 PASS authorizes only prospective design of a separate,
fresh-identity, time-distributed zero-baseline identification campaign
(D1R15). It does not authorize that campaign, a transition model, MPC, expert
data, BC, DAgger, bounded residual RL, or any relaxation of the remaining
restart/history/target/continuous-parameter/noise/disturbance/long-hold gates.
