# Stage4.2R3c3T13S24D1R5 recursive split-return preflight design

Status: prospectively frozen after final D1R4 raw and retrospective forensics,
before D1R5 implementation or any D1R5 output.

## Purpose and claim boundary

D1R4 proved that all nine causal 0.175 split starts survive one authentic TSC
plant advance, but an immediate exact-center finish at state 19 requires an
intervention increment of 0.2712316553--0.3540255817 relative to the new
underlying baseline. All nine finishes were rejected before application.

D1R5 is a zero-new-TSC causal controller replay. It tests only whether the
authenticated state-19 measurements support another exact-Card15 0.175
intermediate under the unchanged action/current envelope. It cannot observe a
state-20 response and therefore cannot validate termination, exact-center
finish, a real recursive sentinel, full-horizon control, a transition model,
MPC, expert data, or learning.

## Immutable source boundary

```text
D1R4 execution package checkpoint / revision
  da3f4b4
  r42r3c3t13s24d1r4_causal_split_return_safety_sentinel_v1h2

D1R4 run
  stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_20260803_1802_da3f4b4_v1h2

D1R4 raw count / bytes / inventory digest
  9 / 363807
  9327a301498349eaebdb834d1c0f243bcc1939b5efb5d059ee6d6ec43b036190

D1R4 complete log SHA-256
  ca86693375685e4c6d1d21b37b39c405b79ff3f391a1c888bcca00592d00536d

D1R4 final / manifest / state SHA-256
  640730223f213b5075f628591d6c7213dbafe6d7822fea6fee49d0ab7acbb6c7
  d008d8f94bf6f5bfebb9ad827d1a801e6e0ffd80a34b6eab03b180225270e6a3
  ff2463cbfcead8cb3ba3554afcb581136d3ba1ee231d0310d91b87cfe01b02c2

D1R4 prospective / retrospective audit SHA-256
  58dc2ac72e59e98a7fc4f496bdc6679b098b9f2a857db9028ce889a32a99688d
  f1ada0a11ce76e50c1dd2896c01874a1b3cdc73369e5a7937ca2332b532c5b0d

D1R3 candidate digest
  143d0c8e5fa2678e2d7519cba22441a24f6274e39457d18c85fb92fc57c9e1ec
```

D1R5 must authenticate this exact boundary, the nine raw filenames and
hashes, the three snapshots, all nine D1R2 source raws, the D1R3 split table,
the original execution fingerprint, both D1R4 audits, and the complete log.
Any mismatch stops before controller replay.

## Frozen identity and replay matrix

```text
stage
  Stage4.2R3c3T13S24D1R5

identity
  causal_recursive_split_return_preflight_v1

controller revision
  causal_recursive_split_return_probe_v42r3c3t13s24d1r5_v1

source rows
  the exact nine D1R4 structured split-finish stops

new raw / snapshots / Ray / gotsc / TSC / plant
  all zero
```

The output order is the canonical D1R4 spec order. No row, context, amplitude,
state, or result may be added or removed after an output opens. D1R4 raw is
development-only and remains forbidden from training and expert data.

## Causal replay and forbidden information

For each row, D1R5 must instantiate a fresh controller, replay only the
current rollout's measured states 0 through 19, and reproduce the D1R4 actions
and trace exactly through step 18. At step 19 it may use only:

```text
the current measured state-19 visible state and coil currents
the controller's own causal state and pending return state
the exact center/target/intermediate fields stored by that controller
the underlying controller action computed from the same state 19
the current task step
```

It may not use pair/history/partition/sequence/source-outcome labels, source
actions or currents, D1R4 saved failure action, D1R4 future values, state-20
values, wire currents, candidate tables, or any cross-row information inside
the controller. Source raw and labels may be used only by the offline selector
and independent auditor. The saved D1R4 failure event is evidence to reproduce,
not a controller input.

## Frozen recursive return rule

Let `C` be the controller-stored exact center and let `M18` be its step-18
intermediate. At current state `k >= 19`, compute the underlying causal action
`bk` and the exact stored-center action `dk` with the unchanged actuator
function. Define `delta = ||dk - bk||_infinity`.

```text
if delta <= 0.24 and every direct-finish gate passes:
  return dk and clear the pending return

otherwise:
  alpha = min(1, 0.175 / delta)
  Mk = exact Card15 result of bk + alpha * (dk - bk)
  return Mk and retain the pending return
```

D1R5 is frozen to the second branch at state 19 because the authenticated D1R4
increments are all above 0.25. It must independently recompute those direct
increments; it may not read them from the failure event inside the controller.

The state-19 continuation must pass:

```text
increment relative to current underlying baseline              exactly 0.175
prospective intermediate increment cap                           <= 0.18
unchanged original intervention cap                              <= 0.25
total normalized action                                           <= 1.0
predicted current utilization                                     <= 0.55
exact 14-field Card15 target and reproduction                       true
no saturation or current clipping                                   true
0 < alpha < 1                                                        true
new intermediate differs from C and M18                              true
pending state retained                                               true
```

For exact Decimal fields `C`, issue target `T`, `M18`, and `M19`, every coil
must satisfy the expanded telescope:

```text
(T - C) + (M18 - T) + (M19 - M18) + (C - M19) == 0
```

No floating tolerance may replace this identity.

## Prospective real-sentinel policy authorized by a pass

A D1R5 pass authorizes design only, not execution, of a new D1R6 real-TSC
sentinel. That later design must use the same recursive rule online, may
continue with 0.175 intermediates while a direct finish exceeds 0.24, and must
freeze a latest exact-center finish at task step 22. Thus all return work must
complete before the unchanged normal arrival deadline at step 25. Failure to
finish by the frozen boundary must be a structured safe stop; there may be no
retry, clipping, threshold relaxation, or post-result horizon extension.

D1R5 does not claim that step 22 is feasible. State 20 and later remain
unobserved under the recursive policy and require a separately preregistered
authentic sentinel.

## Full preflight gates and independent evidence

The primary replay and a separately implemented independent audit must prove:

```text
strict raw parse / exact raw identity                             9 / 9
execution package, log, final, state, manifest consistency       9 / 9
restart, phase causality, calibration prefix                      9 / 9
D1R2 action and trace prefix through step 17 exact                9 / 9
D1R4 split-start action/fields/alpha exact                        9 / 9
D1R4 one-advance state-19 measurement consumed causally           9 / 9
saved finish failure independently reproduced                    9 / 9
new state-19 0.175 continuation and every gate                    9 / 9
exact expanded Decimal telescope                                  9 / 9
forbidden controller input count                                      0
new TSC, plant steps, snapshots, or controller training               0
```

The implementation, config, tests, output schema, manifest, deterministic
repeat contract, and independent audit must be committed and validated before
the first D1R5 output opens. Two new output directories must reproduce the
same detailed, summary, manifest, and candidate-spec bytes.

## Frozen routes

```text
source/package/raw/log authentication mismatch
  CAUSAL_RECURSIVE_SPLIT_RETURN_PREFLIGHT_SOURCE_STOP

any replay, causality, exactness, action, current, or continuation gate fails
  CAUSAL_RECURSIVE_SPLIT_RETURN_PREFLIGHT_FAIL_REDESIGN_REQUIRED

all nine primary and independent rows pass twice byte-exactly
  CAUSAL_RECURSIVE_SPLIT_RETURN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

No route authorizes a real run directly. D1R6 must receive a new identity and
freeze its raw, snapshot, capacity, recursive-boundary, stop/resume, formal,
and independent-forensic contracts before execution.

## Timing and learning veto

The immutable 250/270 ms arrival deadlines, 350/370 ms endpoints, R/Z, speed,
Ip, and arrival-streak gates are unchanged. D1R5 has no formal-control result
because it performs zero plant steps. D1R5 and all D1R4/D1R3 probe evidence
are forbidden from expert datasets. Full sequential identification, MPC, BC,
DAgger, and bounded residual RL remain unauthorized.
