# Stage4.2R3c3T13S10 combined post-queue first-effect audit design

## Status and question

This design is frozen after the final T13S9 raw/server audit and before any
T13S10 extraction, fit, support, prediction, or route output is computed.
T13S10 is a zero-new-TSC read-only audit over consumed T13S5 q2 and T13S9 q1
identification raw.

T13S8 could not compare q1 and q2 in one physical input coordinate because
S1 acted before the inherited delay queue. T13S9 prospectively regenerated
q1 with the exact S5-style post-queue Card15 contract. T13S10 asks whether
those unified first-effect transitions support a finite causal
leave-one-context-out hypothesis bank across q1/q2 histories.

## Immutable source authentication

Authenticate before any modeling:

```text
T13S5 q2 raw files / digest
  68 / 09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
T13S5 independent server audit SHA-256
  dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033
T13S9 q1 raw files / digest
  68 / 9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
T13S9 independent server audit SHA-256
  df4d7982f98a6216997d89ac5adea9ca2e3b2bf367451c3412d5458ccc5c60e0
```

Both campaigns are post-queue lattice campaigns. For every signed probe,
the first physical effect state is exactly `issue_step + 1`, independent of
the environment delay label. No cancellation transition or later response
may enter this audit.

## Causal transition coordinate

Relative to the exact same-context baseline, extract:

```text
x = measured 14-coil TSC-current difference at issue_step + 1
y = (R, Z, vR, vZ, Ip) difference at issue_step + 1
```

Velocity is the backward causal difference already frozen in T13S8. The
input is measured current, not requested direction, q/pair/history label,
ideal coefficient, Card15 target, source action, source result, or future
readback. The same causal visible feature schema as T13S8 is retained for
collision and forbidden-input audit, but it does not select a history label.

Allowed fields are current/past R/Z/Ip, causal velocity and known flag,
measured coil current and past current difference/known flag, target, formal
issue time, finite delay, and slew. Pair, q, history, prefix, source IDs,
source actions/results, wire/vessel currents, future values, and outcome
labels are forbidden in features, support, fit, prediction, and selection.
Labels may be opened only after prediction to audit fold composition.

## Frozen leave-one-context-out bank

There are eight contexts: q1/q2, two histories, and two delay/slew strata.
Within each stratum, leave one of its four contexts out and fit three
per-context maps for each window from the other three contexts. Each local
map uses its four lattice directions and both signs.

```text
contexts                                                       8
windows per context                                            2
local context/window maps                                     16
leave-one-context-out folds                                    8
signed first-effect rows                                     128
```

Every local map must have rank 4, condition `<=15`, signal above the frozen
floor, and a non-vacuous tube. All three training maps are retained as a
label-free robust hypothesis bank. No nearest-history selector or
outcome-dependent choice is allowed.

For each held signed input, apply the unchanged measured-input row-space
residual gate `<=0.15` separately to each training hypothesis. Unsupported
hypotheses make no prediction. Every held row must have at least one
supported hypothesis.

Acceptance remains the T13S8 existential validation diagnostic: the actual
held transition must lie within at least one supported componentwise tube
and have at least one supported center with scaled relative error `<=0.10`.
A later robust controller would have to remain safe for the entire retained
bank; this audit cannot authorize such a controller.

## Tube and frozen gates

```text
response scales       (0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)
radius                numerical floor + 1.5 * max signed residual
component caps        (0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A)
input support gate    <= 0.15
scaled error gate     <= 0.10
```

Required exact pass counts:

```text
S5/S9 raw authentication                                68 / 68, 68 / 68
trace identity                                                   136 / 136
post-queue first-effect contract                                  64 / 64
single-transition signed extraction                              128 / 128
pre-effect causality                                             128 / 128
local signal/rank/condition/tube                                   16 / 16
held rows with supported hypothesis                              128 / 128
componentwise union containment                                  128 / 128
nearest supported scaled relative error <= 0.10                  128 / 128
disjoint exact causal feature/input aliases                              0
forbidden feature/trace/model inputs                                     0
```

Unsupported rows fail closed. Empty finite-error sets serialize as JSON
`null`. No threshold, fold, source role, response state, or formal deadline
may change after output.

## Routes

```text
UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_CANDIDATE_Q3_HOLDOUT_REQUIRED
  every frozen gate passes;
  authorize only the prospective design of a fresh q3 hidden-history
  identification holdout under the same post-queue coordinate.

UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_INSUFFICIENT_OBSERVER_REDESIGN
  any gate fails;
  stop this static first-effect bank and move to persistent state/observer,
  active calibration, or nonlinear state-conditioned tube redesign before
  another physical campaign.
```

T13S10 runs no controller, optimizer, Ray, `gotsc`, TSC, plant step, or new
snapshot. Both source campaigns are consumed development evidence. Neither
route authorizes real MPC, expert data, BC, DAgger, or bounded residual RL.
Formal arrival and hold timing remains unchanged.

