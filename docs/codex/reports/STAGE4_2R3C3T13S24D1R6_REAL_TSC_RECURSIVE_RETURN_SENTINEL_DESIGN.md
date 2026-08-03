# Stage4.2R3c3T13S24D1R6 authentic recursive-return sentinel design

Status: prospectively frozen after the final byte-identical D1R5 result and
before D1R6 implementation, package creation, output, or TSC execution.

## Purpose and claim boundary

D1R5 proved offline that every authenticated D1R4 state-19 measurement admits
another causal exact-Card15 0.175 intermediate. It did not advance the plant
and therefore could not test whether a later state permits an exact-center
finish.

D1R6 is the smallest authentic plant sentinel for that missing boundary. It
runs exactly nine fresh 35-step TSC trajectories. Each fresh causal controller
must reproduce the frozen prefix, apply the split start at task step 18,
apply the D1R5-authenticated continuation at task step 19, and then either
finish to the stored center or continue under the same fixed rule. A finish is
required no later than task step 22.

D1R6 is still a development-set action-safety sentinel. A pass can authorize
only prospective design of a full replacement sequential-transition
identification campaign. It is not transition-model identification, MPC,
expert data, robustness, independent long hold, BC, DAgger, or RL.

## Immutable source boundary

```text
D1R5 final package checkpoint / revision
  7389154
  r42r3c3t13s24d1r5_recursive_split_return_preflight_v1

D1R5 primary output
  stage4_2r3c3t13s24d1r5_recursive_split_return_preflight_20260803_190536_7389154_v2

D1R5 repeat output
  stage4_2r3c3t13s24d1r5_recursive_split_return_preflight_20260803_190715_7389154_repeat

D1R5 final route
  CAUSAL_RECURSIVE_SPLIT_RETURN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED

D1R5 candidate count / digest
  9
  f3ca434af404bb20c85e7ff2fb6da40bc13c1d873ae9c74396ab8680533b889b

D1R5 candidate-spec file SHA-256
  14b2cc3a42814dd14a8c524b981d9fc0450fd932b0a3872630eeb417cb190fe2

D1R5 detailed / summary / manifest / independent SHA-256
  2d820f3129c7df0d3a6b31546db6de9adabeda237a7217ec13cd7321f23f1cda
  20f3de3b8429bfc9a72e0210afe6ba5ed3acf1dcc802b52615c908635f32e206
  622c010f1d45cffaacf4aacdce95da011f48e7ee1c1207c41e954e6d7aaf5247
  60055b733f73c14068d053ca9e64cb52b9f87b2491593d2f57ce5feb2c0adaad

D1R5 primary / repeat complete-log SHA-256
  6860f3c653fb96956ae5b433ab5b10bd606965a095a8ab989637490aede92c3d
  59123d93ce009f00cbdc1a980797c2ca5f17d34da0c0d375bed57b2680951cc8

D1R4 raw count / bytes / inventory digest
  9 / 363807
  9327a301498349eaebdb834d1c0f243bcc1939b5efb5d059ee6d6ec43b036190
```

D1R6 must authenticate both D1R5 directories as byte-identical, all five
output hashes, both complete logs, the exact D1R4 package/raw/log/snapshot
chain authenticated by D1R5, and the nine candidate specifications. Any
mismatch stops before Ray or TSC.

## Frozen identity and matrix

```text
stage
  Stage4.2R3c3T13S24D1R6

campaign identity
  causal_recursive_split_return_safety_sentinel_v1

controller revision
  causal_recursive_split_return_probe_v42r3c3t13s24d1r6_v1

source specifications
  exact nine D1R5 candidate specs, no additions or removals

sequence-index counts
  6: 3
  10: 3
  18: 3

horizon
  35 actions / 36 states for every successful row

parallel capacity
  exactly nine Ray actors, one spec per fresh actor

plant/controller lifecycle
  one fresh authentic TSC process, reset, and controller per spec
```

The three exact source restart snapshots must all authenticate. All D1R6 raw
is development-only and is forbidden from expert or learning datasets.

## Causal controller boundary

The controller may use only the current rollout's visible state, measured
coil currents, its own causal internal state, its stored exact Card15 return
fields, the underlying controller action computed from the same current state,
and the current task step.

It may not receive or use pair/history/partition/sequence/source-outcome
labels, D1R4 or D1R5 actions/currents/results, source or current-run future
values, wire currents, candidate tables, cross-row information, or the
observed number of continuations from another rollout. Source labels remain
available only to the offline campaign builder and independent auditor.

Every forbidden field must be stripped before controller construction. The
raw trace must explicitly record every forbidden-use flag as false.

## Frozen prefix

Every row must reproduce:

```text
states 0 through 18 and actions/traces 0 through 17
  exact D1R4 source prefix

task step 18
  one exact D1R3/D1R4 split start
  incremental normalized action exactly 0.175
  one authentic plant advance to state 19

task step 19 direct candidate
  independently reproduce the D1R4 rejected exact-center candidate
  do not expose that saved result to the controller

task step 19 executed action
  exact D1R5 0.175 continuation fields and action
  one authentic plant advance to state 20
```

The state-19 continuation must be computed online from the fresh current run.
Its equality to D1R5 is an audit gate, not a controller input.

## Recursive rule for task steps 19 through 22

Let `C` be the controller-stored exact center, `T` the issue target, and `Mk`
the most recently executed intermediate. At each task step `k` while a return
is pending, compute the underlying causal action `bk` from the current state
and the exact stored-center candidate `dk`. Define:

```text
delta_k = ||dk - bk||_infinity
```

Then apply exactly this rule:

```text
if delta_k <= 0.24 and every direct-finish gate passes:
  execute dk
  require exact Card15 center C
  clear the pending return

else if k < 22:
  alpha_k = min(1, 0.175 / delta_k)
  execute bk + alpha_k * (dk - bk)
  require an exact Card15 intermediate
  retain the pending return

else:
  record a structured recursive-boundary failure
  apply no candidate action and perform no further plant advance
```

There is no retry after step 22, clipping, threshold relaxation, state-label
branch, fallback action, or horizon extension. If the direct or continuation
construction fails any safety/exactness gate, record a structured failure
before `env.step`.

The task-step-19 branch is already frozen to continuation by D1R5. Task steps
20 and 21 may causally finish or continue. Task step 22 may only finish or
stop. Thus each successful row has one to three continuation events after the
step-18 split start and exactly one finish at task step 20, 21, or 22.

## Action, current, and exactness gates

Every continuation must satisfy:

```text
increment relative to the current underlying action        exactly 0.175
continuation increment cap                                    <= 0.18
unchanged original intervention cap                           <= 0.25
total normalized action                                       <= 1.0
predicted current utilization                                 <= 0.55
exact 14-field Card15 result                                    true
no saturation or current clipping                               true
0 < alpha < 1 unless exact direct finish is selected             true
new intermediate differs from C and the prior intermediate      true
pending state retained                                           true
```

Every finish must satisfy:

```text
increment relative to the current underlying action            <= 0.24
unchanged original intervention cap                             <= 0.25
total normalized action                                         <= 1.0
predicted current utilization                                   <= 0.55
exact stored-center action and exact Card15 center C               true
no saturation or current clipping                                 true
pending state cleared                                             true
finish task step                                               <= 22
```

For every coil, exact Decimal fields must satisfy the expanded telescope over
the executed sequence:

```text
(T - C) + (M18 - T) + (M19 - M18) + ... + (C - Mlast) == 0
```

No floating tolerance may replace that identity. The executed normalized
action vector must exactly equal the action recorded in the full state after
each plant advance.

## Formal timing and full horizon

All nine candidate rows have the unchanged 35-step normal horizon:

```text
arrive no later than state/task time 25 (250 ms)
hold and evaluate through state/task time 35 (350 ms)
R/Z tolerance 0.03 m
speed threshold 0.1 m/s
Ip threshold 10000 A
arrival streak 3
```

The global weak-slew contract remains 270/370 ms but is not instantiated by
these nine specs. Finishing no later than action step 22 leaves states 23--25
available for the unchanged three-state arrival streak. The 35-step horizon
may not become a later arrival allowance.

Formal metrics must be computed and reported for every full trajectory. They
remain diagnostic for this identification-action safety sentinel because the
interventions are development probes; a PASS is not a reliable-MPC claim.

## Offline gate, real execution, resume, and evidence

Before real execution, a zero-plant offline phase must:

1. authenticate the complete D1R4/D1R5 chain and all hashes above;
2. reproduce all nine candidate specs and their digest exactly;
3. authenticate the three restart snapshots and exact spec/horizon counts;
4. validate controller label stripping, recursive branches, deadline stops,
   exact Decimal telescopes, raw schema, package fingerprint, and resume
   compatibility;
5. prove zero raw, Ray, `gotsc`, TSC, reset, controller rollout, and plant
   steps in the offline phase.

Real execution is permitted only in a new run directory after local,
empty-package, staging, installed-package, import, compile, JSON, shell,
focused, and complete tests pass.

Resume is allowed only for missing real specs when the run identity, resolved
config, exact candidate digest, controller/source/package fingerprints,
formal gates, and action semantics are byte-compatible. A successful raw or
structured scientific-stop raw must never be overwritten. A controller,
matrix, threshold, timing, or physical-action change requires a new identity.

The complete real log, state, manifest, raw inventory, all raw JSON.GZ, three
snapshot checks, package fingerprint, and independent server-side raw audit
are mandatory. Large raw remains server-side; only compact audits and logs
may be downloaded.

## Full gates

```text
candidate specs and identities exact                              9 / 9
fresh actor / TSC / controller                                    9 / 9
strict raw parse and identity                                     9 / 9
restart / phase causality / calibration                            9 / 9 each
D1R4 state/action/trace prefix through state 19 exact              9 / 9
step-18 split start exact                                          9 / 9
step-19 D1R5 continuation exact and applied                        9 / 9
recursive decision recomputed from current state at each step      9 / 9
exact-center finish by task step 22                                9 / 9
full 35-action / 36-state horizon                                  9 / 9
expanded exact-Decimal telescope                                   9 / 9
all action/current/saturation/clipping gates                        9 / 9
forbidden controller input count                                       0
runtime / solver / raw / snapshot / corruption errors                  0
```

Continuation counts after step 19 are outcome-dependent and may not be frozen
post hoc. Each successful row must contain one to three total recursive
continuations at steps 19--21 and exactly one finish at steps 20--22.

## Frozen routes

```text
source/package/spec/snapshot mismatch
  CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_SOURCE_STOP

missing raw, runtime, solver, corruption, or non-structured execution error
  CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_RUNTIME_INCOMPLETE

any recursive boundary, action, current, exactness, or deadline failure
  CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED

all nine full trajectories and independent gates pass
  CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_PASS_FULL_REPLACEMENT_CAMPAIGN_DESIGN_REQUIRED
```

The action-fail route includes a correctly recorded step-22 safe stop. Such a
result is a genuine schedule/controller-design failure, not a runtime error.
An unrun formal endpoint on a structured prefix is `not run`, not a 0/9
formal-control failure.

## Learning veto

No D1R6 route directly authorizes a transition MPC, expert dataset, BC,
DAgger, or bounded residual RL. A pass permits only a separately frozen full
replacement identification design. A failure requires recursive schedule or
controller redesign without weakening the 0.18/0.24/0.25, total-action,
current, exactness, or formal-timing gates.
