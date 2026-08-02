# Stage4.2R3c3T13S8 first-effect transition audit design

## Status and question

This design is frozen after the final T13S7R1 result and support forensic,
and before any T13S8 single-transition extraction, rank, tube, support,
prediction, or route output is computed. T13S8 is a new zero-new-TSC,
read-only audit identity over the consumed q1/q2 raw.

T13S7R1 proved that the two-state measured input concatenates incompatible
issue/cancel geometry. T13S8 asks a narrower causal question: does the first
physical transition alone admit a supported local hypothesis bank across
the finite histories? It does not rewrite T13S5, S6, S7, or S7R1.

## Immutable sources and effect states

Authenticate the exact final S1/S5 raw inventories, official source audits,
T13S7 effect-contract forensic, and final T13S7R1 audit. Use:

```text
S1 first physical effect state   issue + action_delay + 1, exact spec field
S5 first physical effect state   issue + 1
```

All 24 S1 and 32 S5 signed groups must match their authenticated effect
contract. No later response state or cancellation-transition current may
enter the T13S8 input or output.

## Causal coordinate and response

For each signed probe relative to its exact same-context baseline:

```text
x = measured 14-coil TSC-current difference at the first effect state
y = (R, Z, vR, vZ, Ip) difference at the first effect state
```

Velocity is the same backward causal difference already frozen in T13S7.
The input is measured current, not requested direction, direction label,
source action, ideal mode coefficient, Card15 target, or future readback.
The current-run candidate input is observable after the actuator transition
and is valid for a one-step receding-horizon update; this audit does not
claim an open-loop pre-actuation predictor.

The frozen causal state feature remains exactly the T13S7 schema, including
current/past R/Z/Ip, backward velocity and known flag, measured coil current
and past difference/known flag, target, formal issue time, finite delay, and
slew. Pair/q/history/prefix/source IDs, source action/result, wire/vessel
current, future values, and outcome labels remain forbidden.

## Leave-one-context-out hypothesis bank

Keep the two strata (`delay=0` easy and `delay=2` hard), four contexts per
stratum, and leave one context out. Fit per-context, per-window minimum-norm
maps from odd measured input to odd response on each fold's three training
contexts:

```text
S1 expected local rank                                     3
S5 expected local rank                                     4
local models                                      8 * 2 = 16
```

All three same-stratum training maps are retained as causal robust
hypotheses. This prospectively replaces T13S7R1's two-nearest selection;
there is no history label at inference and no outcome-dependent selection.
For each held signed input, first apply the unchanged measured-input
row-space residual gate `<= 0.15`. Unsupported hypotheses make no
prediction, and every held row must have at least one supported hypothesis.

For a retained bank, acceptance is union containment: the actual held
transition must lie in at least one supported hypothesis tube and have a
supported hypothesis center with scaled relative error `<= 0.10`. A later
robust controller would have to enforce safety for the entire retained bank;
this existential validation gate does not authorize that controller.

## Tube and exact gates

Fit signed residual tubes only on the corresponding training context:

```text
response scales       (0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)
radius                numerical floor + 1.5 * max signed residual
component caps        (0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A)
scaled error gate     <= 0.10
input support gate    <= 0.15
```

Frozen pass counts:

```text
S1/S5 raw authentication                              52 / 52, 68 / 68
campaign-specific first-effect timing                         56 / 56
trace identity                                               120 / 120
single-transition signed extraction                          112 / 112
pre-effect causality                                         112 / 112
local rank                                                     16 / 16
local non-vacuous tube                                         16 / 16
leave-one-context-out folds                                          8
held rows with supported hypothesis                          112 / 112
componentwise union containment                              112 / 112
nearest supported scaled relative error <= 0.10              112 / 112
disjoint exact causal feature/input aliases                          0
forbidden feature/trace/model inputs                                 0
```

Unsupported rows fail closed. Empty error sets serialize as JSON `null`.
No threshold, source role, or formal deadline may change after output.

## Routes

```text
FIRST_EFFECT_CAUSAL_TRANSITION_CANDIDATE_Q3_HOLDOUT_REQUIRED
  every gate passes;
  authorize only a fresh, prospectively frozen q3 history holdout using the
  same post-actuation first-effect coordinate.

FIRST_EFFECT_CAUSAL_TRANSITION_INSUFFICIENT_REDESIGN
  any gate fails;
  move to an active calibration/persistent observer or a new unified
  post-queue excitation campaign before any controller.
```

T13S8 executes no controller, MPC, TSC, plant step, or new probe. Neither
route authorizes expert data, BC, DAgger, or bounded residual RL. Formal
arrival and hold timing remains unchanged.
