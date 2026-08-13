# R_geo/Z_geo 1 ms NR2R2C1a canonical-source replay design

Status: prospectively frozen before implementation, server deployment, or new
TSC outcome inspection on 2026-08-13 Asia/Shanghai.

Stage identity:

```text
rgeo-zgeo-1ms-nr2r2c1a-canonical-source-replay-v1
```

## 1. Question and claim boundary

C1a asks only whether resetting every rollout to the canonical 1100 ms source
and replaying a complete, already finite-safe causal Card15 prefix is
deterministic, history-complete, and affordable as an offline source-origin
shooting mechanism. It does not restart a generated successor `sprsina` and
does not qualify snapshot restart, arbitrary suffixes, a moving-state Oracle,
hold, recovery, controller, model, MPC, tracking, teacher data, or online 1 ms
execution.

All records have purpose `interface_replay_qualification_only` and are forever
forbidden from model fitting, training, calibration, holdout, and expert data.

## 2. Unchanged hard contract

```text
source                                             1100 ms
control period                                        1 ms
per-coil single-turn command/readback slew          <=0.3 A
equality at +/-0.3 A                                allowed
Card15 unit                                        kA-turn
R_geo/Z_geo                         paired same-boundary definition
boundary invalid                                  fail closed
Ip/current/limiter/outer campaign envelope         unchanged from NR1R2/B0
```

Every issue is prevalidated in exact command coordinates before the runner is
called. Every successor is checked in exact readback coordinates. Legacy
runner clipping may neither authorize nor repair a request.

## 3. Frozen matrix and budget

Only action streams already observed safely in NR1R2 or B0 are allowed:

```text
family       horizon (steps)       independent canonical resets
q0                 4                         2
q0                 8                         2
q0                16                         2
q0                32                         2
pattern_a          4                         2
pattern_b          4                         2
total rollouts                              12
maximum plant advances                     136
```

The q0 4/8/16 schedules are strict prefixes of B0's already observed 32-step
q0 stream. `pattern_a` and `pattern_b` are exactly the four-step NR1R2 streams,
including their exact Card15 fields. No new sign, amplitude, event time,
temporal pattern, cumulative center movement, or suffix is introduced.

Each rollout is a fresh canonical reset. The paired member is not a resumed
process or successor snapshot. The complete action prefix is reissued from
step zero. Failure stops the remaining matrix; changed semantics require a new
identity and never resume this result.

## 4. Per-step gates

Before each issue and after each successor require:

1. paired-boundary signal, limiter and Ip parse successfully and time equals
   `1100 + state_index` ms;
2. the exact frozen Card15 fields are issued and remain inside absolute current
   limits;
3. adjacent command and adjacent readback slew are each `<=0.3 A` in exact
   decimal arithmetic;
4. requested/serialized target and observed first-effect semantics agree with
   the NR1R2 direct `k -> k+1` contract;
5. TSC return code is zero, state is non-abnormal, and no later issue follows a
   failed post-state;
6. `R_geo` remains inside the limiter midplane intersections,
   `|R_geo-R0|,|Z_geo-Z0| <=0.05 m`, Ip sign is unchanged, and
   `|Ip-Ip0| <=0.10|Ip0|`.

## 5. Paired replay and history-integrity gates

For each identical pair, at every matching state require:

```text
R_geo/Z_geo/R_mid                              <=1e-12 m
Ip                                               <=1e-9 A
14 coil-current readbacks                        <=1e-9 A
48 wire-current diagnostics                      <=1e-9 A
issued/serialized Card15 fields                    exact
issue time, state time and action index             exact
effect age/direct-successor association              exact
inputa/geqdsk/coil/wire artifact SHA-256             exact
```

`sprsina` size/hash/difference is recorded per state but is diagnostic and is
not part of this new source-origin mechanics claim. B0's frozen exact-all-
artifact FAIL remains unchanged. C1a never loads a generated `sprsina` as a
fresh source, so it cannot establish semantic identity or snapshot behavior.

## 6. Cost evidence

Record per reset, per advance, per rollout, and total wall time; failures and
timeouts; state-directory byte/file counts; and the worst replay error by
prefix length. Report both:

```text
online_1ms_oracle_eligible = worst complete branch turnaround <= 0.001 s
offline_source_shooting_usable = all finite gates pass and no timeout/failure
```

The first predicate is expected to be stringent and may fail without failing
the offline tool. No timing result is extrapolated beyond the tested horizons.

## 7. Independent evidence and routes

A structurally separate auditor reparses every state directory and recomputes
the signal, current, action, timing, replay, inventory and cost claims. Large
raw remains server-side; only compact evidence is copied directly.

```text
offline/package/source failure
  ONE_MS_NR2R2C1A_OFFLINE_FAIL_NO_TSC

runtime/interface/safety/history failure
  ONE_MS_NR2R2C1A_EXECUTION_OR_HISTORY_FAIL_STOP

paired source replay mismatch
  ONE_MS_NR2R2C1A_SOURCE_REPLAY_MISMATCH_STOP

finite source replay passes
  ONE_MS_NR2R2C1A_CANONICAL_SOURCE_REPLAY_QUALIFIED_C2A_DESIGN_ONLY
```

A PASS authorizes only a separately frozen C2a nominal-hold design. It does
not qualify a novel C2a action. Any novel suffix first needs an independent,
pre-result successor bound and hard filter; if none exists, C2a is blocked.

