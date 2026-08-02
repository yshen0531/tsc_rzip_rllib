# Stage4.2R3c3T13S9 unified post-queue q1 identification design

## Status and purpose

This design is frozen after final T13S8 evidence and before T13S9 code,
offline actuation output, or real TSC output. T13S9 is a new experiment
identity. It does not rerun or reinterpret S1 and may reuse only its four
authenticated q1 restart snapshots.

T13S8 showed that all S5 post-queue first-effect inputs were supported while
all S1 pre-queue inputs were unsupported. T13S9 therefore repeats the q1
contexts under the exact S5 lattice-native post-queue actuation semantics so
that q1 and q2 can be compared in one physical input coordinate.

## Immutable q1 contexts

Use exactly the two selected q1 pairs and both members:

```text
p5_q1_a0p900_gap2_settle4, plus_first
  source R3c1 s42r3c1_a7cf656de03a975cccc8
  snapshot 4add3b5354fa2a0660cdd9c3f02212989e1f81f76804a8f9f7eba5a2969548b7
p5_q1_a0p900_gap2_settle4, minus_first
  source R3c1 s42r3c1_7f47bd92b5458cdb0d40
  snapshot 0c4141fe324eb930c9929db60c52190e1f745cf7a4c1cc4ff4badcfbb4ab8cf4
p9_q1_a0p750_gap2_settle4, plus_first
  source R3c1 s42r3c1_f7ac14b67b3eddb3659d
  snapshot 1edbbc2b7a2d31c7dcdf8e3bbade06e2a55ee91c33bedfa9d13fa0681fa7d910
p9_q1_a0p750_gap2_settle4, minus_first
  source R3c1 s42r3c1_ee404a8e3301e9caacb0
  snapshot 2af7aee6a2fc773ea3c25f4ebb92255300328a3bf4c0ab56bb9ed9aba5be27eb
```

The p5 contexts use target `RZ_p10_m10`, delay 2, slew 0.9 and formal horizon
37. The p9 contexts use nominal target, delay 0, slew 1.0 and horizon 35.
The expected unprobed R3c1 formal results/margins remain those already frozen
in the S1 bookend config. Pair/history labels are experiment-construction and
post-result audit fields only, never controller inputs.

## Unified action contract

Reuse the S5 four exact lattice directions and all original actuator gates:

```text
mode0_without_coil8
mode0_coil8_component
mode1
mode2
```

At each issue state, compute the complete causal R3c1 action first, then
replace its final Card15 action with the exact symmetric lattice action.
Cancellation is the same causal return-to-stored-center first policy, with
exact inverse fallback. No source action/result, wire current, future value,
pair/history/prefix, or control outcome may enter the controller.

Unlike S5's mistaken declaration, prospectively declare the actual
post-queue physical effects:

```text
delay 0 transport  issue 2 / cancel 3   effects 3 / 4
delay 0 braking    issue 16 / cancel 17 effects 17 / 18
delay 2 transport  issue 0 / cancel 1   effects 1 / 2
delay 2 braking    issue 14 / cancel 15 effects 15 / 16
```

The delay label still belongs to the future controller environment; the
post-queue identification action itself is immediate. This does not change
the formal arrival or hold deadlines.

## Matrix and gates

```text
per context
  1 baseline + 4 directions * 2 signs * 2 windows = 17
total authentic TSC trajectories                         68
signed groups                                            32
expected current components                           34272
```

Before TSC, all 68 specifications must pass the exact S5 offline Card15,
increment, current, clipping, cosine, and cancellation gates. Real execution
requires 68/68 fresh controllers, fresh TSC processes, exact authentic
snapshot restart, causal traces, successful solver/environment completion,
and current readback inside all 34,272 frozen intervals.

At the prospectively correct first effect require 32/32 central measured
current signals, symmetry, and pre-effect causality. Fit diagnostic local
first-effect maps for all four context/window cells and require rank 4,
condition `<=15`, and the unchanged single-state tube caps. The plus/minus
member split is retained only as a diagnostic; T13S9 data are all development
for the subsequent combined q1/q2 audit and cannot regain blind status.

## Routes

```text
UNIFIED_POSTQUEUE_Q1_IDENTIFICATION_COMPLETE_COMBINE_Q2_REQUIRED
  every offline, execution, restart, trace, actuator, first-effect signal,
  local rank/condition, and local tube gate passes;
  authorize only a separately frozen zero-new-TSC combined q1/q2 audit.

UNIFIED_POSTQUEUE_Q1_IDENTIFICATION_FAIL_REDESIGN
  any valid gate fails;
  stop before combined modeling and diagnose actuation/signal/runtime class.
```

The campaign does not require cross-history validation to complete; that is
the next stage's question. Probe raw are forbidden from expert data. No
controller, MPC, q3 holdout, BC, DAgger, or bounded residual RL is authorized.
