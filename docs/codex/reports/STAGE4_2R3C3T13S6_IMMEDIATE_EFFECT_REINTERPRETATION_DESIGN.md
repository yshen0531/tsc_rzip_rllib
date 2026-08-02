# Stage4.2R3c3T13S6 immediate-effect reinterpretation audit design

## Status and scope

This design is frozen after the final T13S5 result and before any corrected
effect-state model output is computed. T13S6 is a read-only audit of the 68
immutable T13S5 raw trajectories. It runs no controller, Ray, `gotsc`, TSC,
plant step, or snapshot creation.

T13S5 remains a scientific FAIL under its preregistered states. T13S6 may not
rewrite that result or recover blind status: all 34 former holdout files were
opened only after the T13S5 development model hash was frozen, but they are
now an already-consumed validation set for every later analysis.

## Frozen source finding

`LatticeTransitionProbeController.action()` first calls the causal R3c1
controller. R3c1 has already applied its software command queue through
`_stream_queue_apply(..., actual_delay)` and converted that applied mode
command to the final 14-coil action. T13S5 then replaces this final action
with an exact Card15 lattice move. The lattice move is therefore downstream
of the modeled delay queue and reaches the next TSC state immediately.

The T13S5 timing forensic independently found the first nonzero coil-current
difference at state 1 for every delay-2 transport probe and at state 15 for
every delay-2 braking probe. These are exactly `issue_step + 1`, two states
earlier than T13S5's frozen declarations.

T13S6 changes only the retrospective response indices:

```text
corrected first current/effect state   issue_step + 1
corrected cancel current/effect state  cancel_step + 1
```

It does not change raw, action traces, cancellation, formal timing, target,
controller semantics, or any acceptance threshold.

## Immutable evidence and split

```text
source run
  stage4_2r3c3t13s5_real_20260802_d048686

raw files                              68
original development role              34, plus_first
consumed validation role               34, minus_first
signed direction/window groups         32
```

The model fit must use only the original 34 development files. The consumed
validation files may be evaluated without refit, threshold selection, tube
growth, phase selection, or history labels. Pair/history/prefix, source
action/result, wire/vessel current, and current-run future values remain
forbidden model inputs.

## Frozen recomputation

For every signed group, subtract its same-context baseline at the corrected
adjacent states. The measured input is the full two-state by 14-coil current
displacement. The output is the two-state `(R,Z,vR,vZ,Ip)` displacement.

Preserve the T13S5 scales and gates:

```text
pre-effect R/Z                               <= 1e-9 m
pre-effect velocity                        <= 1e-7 m/s
pre-effect Ip                                 <= 1e-4 A
pre-effect coil difference       <= one frozen radius/coil
measured odd current signal        >= four radii in L2
measured current even/odd ratio                   <= 0.10
development rank                                      4
development condition                              <= 15
tube multiplier                                      1.5
tube caps per state     3 mm, 3 mm, .01, .01, 1000 A
validation scaled relative error                    <= 0.10
validation componentwise containment                  exact
```

Fit one minimum-norm map and development residual tube for each
`easy/hard x transport/braking` cell. Serialize all non-finite numbers as
strict JSON `null` with an explicit finite flag.

## Authentication gates

The audit must authenticate:

```text
raw identity, success, horizon, and immutable SHA       68/68
issue/cancel trace identity                              64/64
exact T13S5 target-field symmetry                        32/32
corrected pre-effect causality                           32/32
observed odd-current signal and symmetry                 32/32
development signal                                      16/16
rank/condition and non-vacuous tube                        4/4
consumed-validation containment                         32/32
consumed-validation relative error                      32/32
forbidden model inputs                                       0
```

Formal arrival and hold results remain diagnostic and the 250/270 ms arrival
and 350/370 ms hold contract is immutable.

## Outcome routes

```text
IMMEDIATE_EFFECT_MODEL_CANDIDATE_NEW_HISTORY_HOLDOUT_REQUIRED
  every frozen gate passes;
  authorize only a new prospectively split independent-history holdout
  design, not a controller or MPC.

IMMEDIATE_EFFECT_LOCAL_MAP_INSUFFICIENT_REDESIGN
  any corrected development or consumed-validation gate fails;
  preserve raw and redesign the causal state-conditioned/multi-hypothesis
  transition model before any new physical campaign.
```

Neither route authorizes real MPC, expert data, BC, DAgger, or bounded
residual RL. T13S5 probe trajectories remain forbidden from expert data.
