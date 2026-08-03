# Stage4.2R3c3T13S23R1 amplitude-coded Hadamard preflight design

## Status and purpose

This design is frozen after the final S23 and D1 forensics, before S23R1
implementation or any S23R1 actual-coordinate replay. S23R1 is a zero-new-TSC
action/lattice preflight for one exact structured candidate. It is adaptive
to the D1 feasible-template catalog and is not a held-out plant result.

S23R1 asks only whether this exact candidate can be constructed under the
unchanged Card15 fidelity, action, current, rank, condition, symmetry, and
formal-timing boundaries in all 40 source contexts. A pass may authorize only
a separately preregistered sequential identification campaign.

## Sources and authentication

S23R1 must authenticate and read in place:

- the complete 360-raw S21 campaign and its compact model/tube/audits;
- the final S22 route and independent postprocessor;
- the exact failed S23 output and code identity;
- the exact D1 detailed output, summary, manifest, code, config, and route.

It must reproduce all S21 formal metrics and the S23/D1 terminal counts. No
formal outcome may enter action construction or candidate selection.

## Fixed coordinate basis and knots

The field columns retain the exact S21 QR order:

```text
0  mode0_without_coil8
1  mode0_coil8_component
2  mode1
3  mode2
```

The four issue/cancel pairs are fixed:

```text
slot              0       1       2       3
issue task step   10      13      15      17
cancel task step  11      14      16      18
issue effect      11      14      16      18
cancel effect     12      15      17      19
```

Every cancellation effect precedes the immutable 250/270 ms arrival
deadline. Formal scoring still holds through state 35 or 37. This is not an
arrival-deadline extension or a long-hold test.

## Exact amplitude-coded H16 schedule

Let `H16` be the same unpermuted Sylvester matrix as S23, with columns assigned
by `column = 4 * slot + direction`. Rows 0 through 15 are primary sequences;
rows 16 through 23 are the exact global negatives of primary rows 0 through
7. There are 24 sequences and 96 issue/cancel pairs per context.

For each four-sign block, canonicalize by a global sign so its first sign is
positive. The only four canonical block patterns and amplitudes are:

```text
+++     0.25
-+-     0.25
+--     0.50
--+     0.50
```

Restore the removed global sign after amplitude selection. No other pattern,
amplitude, zero coordinate, rotated direction, context-specific choice,
target-specific choice, history/pair/partition label, formal outcome, or
random search is permitted.

All four sign-pair templates were already inside D1's 103-pair feasible
catalog at every candidate step. This provenance motivates the candidate but
does not count as S23R1 validation.

The requested 24 x 16 matrix is fixed before actual replay and has:

```text
rank                                                        16
normalized global condition                     2.8284271247462
each slot rank                                               4
normalized slot condition                                   2
minimum late-column residual                 0.9428090415821
```

## Exact action and geometry gates

Issue construction uses the same source-baseline recorded current/action and
nearest exact Card15 rule with search radius 16 as S23/D1. For each issue:

```text
exact 10-character target and reproduction                  14 / 14
finite and no saturation/current clipping                   14 / 14
requested sign preserved                                      4 / 4
maximum coefficient error from requested amplitude              0.07
minimum active absolute coefficient                             0.18
desired/applied physical-current cosine                         0.98
maximum relative off-basis residual                             0.10
incremental normalized action                                 <= 0.25
total normalized action                                       <= 1.00
predicted current utilization                                 <= 0.55
```

The coefficient-error gate, not a post-result range, handles both amplitudes:
a `0.50` coefficient must be reconstructed within `0.07` of `0.50`. Cosine,
off-basis, action, and current gates are identical to S23; no observed S23 or
D1 gate is weakened.

At the adjacent cancellation step, the only target is the stored pre-issue
Card15 center. It must pass the same action/current limits, reproduce the
center exactly, and produce exact zero target-field jump net. The replay uses
the matching source-baseline recorded cancel current/action, exactly as S23
and D1; it is not a plant-response simulation.

For all 40 contexts, actual reconstructed matrices must satisfy:

```text
global rank                                                  16
normalized global condition                               <= 3
each slot rank                                                4
normalized slot condition                                <= 3
each late-column residual outside slot-0 span             >= 0.5
```

The eight sign-sentinel pairs must have Decimal-exact target symmetry about
the same stored center on all 14 coils at every slot.

## Primary gate and routes

S23R1 passes only with all of:

```text
S21 raw authentication                                     360 / 360
baseline/probe formal reproduction                      40/40, 320/320
S23 and D1 exact terminal authentication                       pass
fixed basis contexts                                         40 / 40
finite issue/cancel constructions                         7680 / 7680
issue action/geometry/current gates                       3840 / 3840
exact cancellation and zero-net gates                     3840 / 3840
central-sign Decimal target checks                        1280 / 1280
global rank/condition contexts                               40 / 40
slot rank/condition blocks                                  160 / 160
late-novelty contexts                                        40 / 40
new raw/snapshot/TSC/plant/controller count               0 / 0 / 0 / 0 / 0
```

Pass route:

```text
AMPLITUDE_CODED_HADAMARD_PREFLIGHT_PASS_FREEZE_S24_REQUIRED
```

This authorizes only a separately designed S24 campaign. Before any new
response is opened, S24 must freeze the exact 1,000-rollout matrix, causal
state-conditioned transition-model family, whole-pair train/calibration/
holdout boundaries, recursive prediction gates, and stop-at-boundary policy.

Fail route:

```text
AMPLITUDE_CODED_HADAMARD_PREFLIGHT_FAIL_NEW_EXCITATION_REQUIRED
```

The S23R1 identity then remains frozen. Thresholds and formal timing may not
be changed after the result.

## Scientific prohibitions

S23R1 executes no Ray, `gotsc`, TSC, controller, plant step, or snapshot. It
does not validate a sequential plant response, transition model, controller,
MPC, new history, new target, continuous actuator variation, noise,
disturbance recovery, or long hold. Probe trajectories remain forbidden from
expert data. BC, DAgger, and bounded residual RL remain prohibited.
