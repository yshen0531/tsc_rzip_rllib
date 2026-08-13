# R_geo/Z_geo 1 ms NR1 safety and first-effect qualification

Status: prospectively frozen before implementation result, server write, or
new NR1 TSC plant advance on 2026-08-13 Asia/Shanghai.

## 1. Identity and claim boundary

```text
contract             rgeo-zgeo-1ms-nr1-v1
campaign             rgeo_zgeo_1ms_nr1_safety_effect_v1
intended use         interface_validation
fixed source         1100 ms
control period       1 ms
single-turn limit    |delta I_i| <= 0.3 A per step, equality allowed
coil order           TSC
Card15 unit          kA-turn
```

NR1 may qualify only:

1. authentic one-millisecond TSC restart advances from the fixed source;
2. paired same-step boundary-box `R_geo/Z_geo`, limiter, Ip, coil and wire
   current availability at every recorded state;
3. nonzero exact Card15 targets in both signs for every coil without any
   requested or observed single-turn step exceeding 0.3 A;
4. the direct runner contract in which an issue at state `k` first appears in
   the immediately generated state `k+1`, with no added software queue;
5. one-step return to the exact representable center, subsequent hold, and
   deterministic fixed-source replay; and
6. a fail-closed interface that performs no later advance after a violated
   pre-step or post-step gate.

NR1 does not qualify a learned model, observer, optimizer, trajectory
controller, arbitrary-state snapshot/branch Oracle, MPC, RL, expert data,
plant-wide safety, or any geometry-tracking work domain. All generated NR1
records are forever forbidden from model fitting and expert/learning data.

The immutable 10 ms / 3 A NR1 raw and PASS remain historical only. They are
not rescaled, replayed, or included in this qualification.

## 2. Evidence available before freeze

A minimal read-only server preflight verified the canonical project,
existing virtual environment, and the five required fixed-source files
`geqdsk`, `coil_currents.csv`, `wire_currents.csv`, `sprsina`, and `inputa`.
It found no actual `gotsc` or R_geo/Z_geo process. No raw campaign file was
read and no server file or plant state was changed.

A zero-plant calculation using the installed formatter and fixed source
found nonzero positive and negative Card15 lattice points within 0.3 A for
all 14 coils. Nearest nonzero grid spacings were:

```text
CS1U--CS4L, 480 turns                 0.020833333333 A
PF2U/PF2L, 200 turns at zero              0.00005 A
PF3U/PF4U/PF4L, 100 turns                     0.01 A
PF3L, 100 turns                                0.1 A
```

This proves offline representability only, not real application, response,
or safety.

## 3. Frozen action construction

Read the 1100 ms current in TSC order, convert it from kA-turn to single-turn
A with the configured turn counts, serialize each component with the existing
Card15 `.3E` formatter, parse it back, and call the result `q0`.

For a requested sign `s_i` in `{+1,-1}`, select the representable Card15
target with the largest signed displacement from `q0_i` subject to:

```text
sign(target_i - q0_i) = s_i
0 < |target_i - q0_i| <= 0.3 A
target_i inside the unchanged absolute current limits
```

Selection is deterministic. It searches only formatter outputs within the
closed 0.3 A interval; it may not clip an over-limit result or introduce a
smaller hidden cap. `pattern_a` uses alternating signs in TSC index order;
`pattern_b` is its exact sign antipode. Offline preflight must prove that all
14 components of each pattern are nonzero, within limits, and mutually
antipodal at the Card15-target-current level up to the source lattice's
direction-dependent spacing.

Every pulse prefix is:

```text
step 0    issue quantized pulse target
step 1    issue exact q0 return
step 2    issue exact q0 hold
step 3    issue exact q0 hold
```

The hold prefix issues exact q0 for all four steps.

## 4. Frozen real-TSC matrix

| rollout | prefix |
|---|---|
| `hold_primary` | hold |
| `hold_replay` | exact hold replay |
| `pattern_a_primary` | alternating-sign maximum lattice pulse |
| `pattern_a_replay` | exact pattern A replay |
| `pattern_b_primary` | sign-antipodal maximum lattice pulse |
| `pattern_b_replay` | exact pattern B replay |

Each rollout independently resets at 1100 ms, issues four targets at
1100--1103 ms, and records five states through 1104 ms. The exact maximum is
six rollouts, 24 plant advances, 30 states, and 24 issue records. A failure
stops the current rollout and prevents every later rollout. There is no Ray,
adaptive action, branch search, optimizer, or extra diagnostic TSC rollout.

## 5. Hard timing, action and effect gates

Before any real advance, the offline gate must prove:

- `start_folder == 1100ms`, `dt_ms == 1`,
  `current_slew_a_per_ms == 0.3`, and derived per-step limit exactly 0.3 A;
- all required source fields/files exist and the accepted geometry parser
  passes with no fallback;
- q0 and every frozen target are exact Card15 round trips;
- every source-to-q0, issued-target, return, and hold increment is at most
  0.3 A with no numerical allowance above the hard limit;
- both pulse patterns are nonzero on every coil and cover both signs.

During authentic execution and independent raw audit:

- state times must be exactly `1100,1101,1102,1103,1104` ms;
- every generated inputa must contain the expected 14 Card15 target fields;
- every observed consecutive single-turn current change must be at most
  0.3 A without an above-limit tolerance;
- for each pulse component, the first successor current change must be
  nonzero and have the issued sign; no effect may be credited to a later
  state or inferred from geometry alone;
- after the q0 return, the next state must return each readback to its
  source-center equivalence class within `1e-4 A`, a prospectively loose cap
  above the previously observed fixed Card15 readback biases but far below a
  control step; the following held state must remain within the same cap;
- TSC return code, abnormal state, non-finite value, missing artifact,
  saturation or solver failure is a hard failure.

The real effect contract qualified here is direct runner issue at state `k`
to current readback at state `k+1`. NR1 adds no software delay queue. Any
later controller queue must be represented and qualified separately rather
than being silently folded into this result.

## 6. Prospective safety and abort gates

These are campaign stop bounds, not claims about a physical machine's full
safe set:

- target and readback currents stay in the unchanged configured absolute
  limits and obey the exact 0.3 A step cap;
- `R_geo` remains between same-state limiter midplane intersections and
  within 0.05 m of its source value;
- `Z_geo` remains within 0.05 m of its source value;
- Ip retains sign and stays within 10% of source magnitude;
- paired boundary/limiter/Ip validity passes at every state.

A pre-step failure issues nothing. A post-step failure records the successor
and performs no later plant advance. `abort` means stop-without-another-step;
it is not an unqualified emergency action. When a safe state is rejected for
planning/model reasons, the only NR1 hold candidate is exact same-state
Card15 center refresh, and it must independently pass representability,
absolute-current and 0.3 A gates before issue.

## 7. Replay, integrity and routes

Each primary/replay pair must match at every state in time, boundary geometry,
Ip, all coil-current readbacks and the full wire-current vector within
`0 ms`, `1e-12 m`, `1e-9 A`, `1e-9 A`, and `1e-9 A`. Source/config/action
hashes and physical artifact hashes are recorded; parsed equality, not a
saved verdict, is load-bearing.

Primary and structurally independent auditors must parse the generated raw
directories and independently reconstruct Card15 targets, timing, currents,
effect signs, return/hold, safety and replay metrics.

Frozen routes:

```text
offline failure     ONE_MS_NR1_OFFLINE_FAIL_NO_TSC
safety/action fail  ONE_MS_NR1_SAFETY_FAIL_STOP
effect/timing fail  ONE_MS_NR1_EFFECT_CONTRACT_FAIL_STOP
replay fail         ONE_MS_NR1_REPLAY_NOT_QUALIFIED
all gates pass      ONE_MS_NR1_INTERFACE_QUALIFIED
```

Only the last route may authorize a prospectively frozen NR2 identification
and model-comparison design. It does not itself authorize additional TSC or
any controller implementation.
