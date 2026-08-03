# Stage4.2R3c3T13S23 sequential Hadamard lattice preflight design

## Status and purpose

This design is frozen after S22's complete forensic classification, but
before S23 implementation or any S23 schedule computation. S23 is a
zero-new-TSC action-space and downstream-identifiability preflight. It may
read the immutable S21 raw on the server, but it may not create a snapshot,
start Ray, call `gotsc`, advance a plant, or execute a candidate controller.

S22 proved that one bounded state-10 issue/cancel family repairs zero of 24
failed contexts even under an optimistic affine construction. T9 proved that
combined-action interaction is material. T11 proved that merely adding an
early persistent step and one braking step can remain poorly conditioned.
The next identification experiment must therefore provide independently
conditioned, combined excitation at multiple task-relevant times before a
sequential state-conditioned transition model is fitted.

S23 asks only:

```text
Can one fixed, label-independent, exact-Card15 multi-knot schedule provide
safe rank-16 excitation over four directions at four task-relevant issue
times in every one of the 40 S21 contexts?
```

## Immutable source contract

S23 must authenticate the complete S21 source chain used by S22:

```text
S21 execution checkpoint
  98dc353
S21 run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s21_runs/
  stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353
raw files / bytes / digest
  360 / 21,083,271 /
  8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4
S21 final result
  e72e66318836c11dac025b66a74682e8459d0c336dac5d0d27e54d5353c5e233
S22 detailed result
  ed2a2f4c714670428c8d89026ee0a00420b59d20bfb7f82e048853dc934fd67d
S22 independent postprocess
  82f18ad41f6f03b073ced10cbd5a52154918889ab67f677856f18f3a26bea3a1
S22 route
  AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED
```

All 40 baseline raw and all 320 signed-probe raw must authenticate. Schedule
construction uses only each baseline's causally available visible state,
14 coil currents, contemporaneous underlying-controller action, and the
four fixed S21 QR field directions. S21 probe outcomes may be authenticated
but may not select an amplitude, row, context, slot, or acceptance threshold.

## Frozen causal action coordinate

The four physical field directions retain the exact S21 order:

```text
0  mode0_without_coil8
1  mode0_coil8_component
2  mode1
3  mode2
```

For each context, their exact field increments are frozen causally at task
step zero by the existing S21 QR construction. No direction may be rotated,
rescaled from an outcome, or replaced per context.

At an issue step, the underlying controller first computes its normal causal
action from the current visible state. The quantized actuator maps that
action and the current 14 coil currents to the contemporaneous Card15 center.
The probe then requests a fixed four-coordinate field displacement relative
to that center. Each coil target is the deterministically nearest exactly
representable Card15 displacement, using the existing search radius 16 and
tie-breaking implementation. The applied coordinate is reconstructed in
physical coil-current space from the same four frozen field columns.

At the adjacent cancellation step, the only accepted target is the exact
stored pre-issue Card15 center. Thus each issue/cancel pair has exact zero
target-field jump net. There is no post-contract compensation and no
dependence on a delay or slew label.

This is the same post-queue intervention coordinate whose real execution was
authenticated in S21. The task-step-to-effect contract remains:

```text
action issued at task step t -> first physical effect at recorded state t+1
```

## Frozen multi-knot schedule

Four issue/cancel pairs are fixed:

```text
slot              0       1       2       3
issue task step   10      13      16      19
cancel task step  11      14      17      20
issue effect      11      14      17      20
cancel effect     12      15      18      21
```

These knots span initial transport, intermediate transport, braking onset,
and pre-deadline settling. Every cancellation effect occurs before both the
250 ms and 270 ms arrival deadlines. Observation and formal scoring retain
the source horizon: state 35 for normal slew and state 37 for weak slew.

Let `H16` be the unpermuted Sylvester matrix
`[[1,1],[1,-1]]` Kronecker-powered four times. Its columns are assigned in
row-major order:

```text
column = 4 * slot + direction
```

The 16 primary sequence rows are rows 0 through 15 of `H16`. Eight additional
central-sign sentinels are the exact negatives of primary rows 0 through 7.
The fixed sequence count is therefore 24. Every issue coordinate is:

```text
0.25 * schedule_sign
```

There is no zero, single-direction, target-conditioned, pair-conditioned,
history-conditioned, partition-conditioned, delay-conditioned, or
slew-conditioned variant. The 0.25 amplitude is frozen before replay: it is
one quarter of each already authenticated S21 direction, while simultaneous
four-direction signs preserve the combined-action interaction that T9 says
cannot be discarded.

If a later real campaign is authorized, it must use exactly one baseline and
these 24 sequences in each of the same 40 contexts:

```text
training contexts / later rollouts                       24 / 600
calibration contexts / later rollouts                     8 / 200
fresh holdout contexts / later rollouts                   8 / 200
total later real rollouts                                40 / 1000
```

These are prospective counts only. S23 itself executes zero real rollouts.

## Frozen replay and geometry gates

For every context, every sequence, and every slot, S23 replays the issue and
cancellation construction on the matching S21 baseline's recorded causal
state and underlying action. This yields 3,840 issue constructions and 3,840
cancellation constructions. It is an action/lattice replay, not a plant or
response simulation.

For each issue, all of the following are required:

```text
exact 10-character Card15 target fields                         14 / 14
no action saturation or current clipping                        14 / 14
requested coefficient sign preserved                              4 / 4
absolute applied coefficient                         [0.18, 0.32]
maximum absolute coefficient error from 0.25                        0.07
desired/applied physical-current cosine                            0.98
maximum relative off-basis residual                                0.10
incremental normalized action                                    <= 0.25
total normalized action                                             <= 1
predicted current utilization                                      <= 0.55
```

Every cancellation must exactly reproduce the stored pre-issue Card15 center,
pass the same action/current guards, and produce exact zero target-field jump
net. No inverse approximation is accepted in S23.

For each context, form the actual `24 x 16` matrix from the four reconstructed
issue coordinates at the four slots. Without column normalization, and also
after unit-column normalization, require:

```text
global matrix rank                                                   16
normalized global condition                                      <= 3.0
each 24 x 4 slot-block rank                                           4
each normalized slot-block condition                              <= 3.0
each late column residual outside the slot-0 span                 >= 0.5
```

For the eight primary/sign-sentinel pairs at each slot, target-field central
symmetry about the same replayed baseline center must be Decimal exact on all
14 coils. This is only an action-construction gate; it is not a claim about
plant-response symmetry.

## Authentication and primary gate

S23 passes only if all of the following pass simultaneously:

```text
S21 source raw authentication                              360 / 360
baseline raw selected by exact frozen spec                   40 / 40
fixed basis rank and S21 condition reproduction               40 / 40
finite issue/cancel constructions                         7680 / 7680
issue action/geometry/current gates                       3840 / 3840
exact stored-center cancellation and zero net             3840 / 3840
central-sign action construction                          1280 / 1280
per-context global rank/condition                            40 / 40
per-context four slot rank/condition blocks                 160 / 160
per-context late-column novelty                              40 / 40
new raw / snapshots / TSC / plant advances                 0 / 0 / 0 / 0
```

All artifacts and the final summary must be independently recomputable from
the S21 raw and frozen S23 config. A reproduction or source mismatch is a
code/reporting failure, not an excitation-design failure.

## Routes

If every primary gate passes:

```text
SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_PASS_CAMPAIGN_REQUIRED
```

This authorizes only a separately implemented and validated S24 campaign
using the exact 1,000-rollout matrix above. Before any S24 response is opened,
S24 must prospectively freeze a causal state-conditioned transition-model
family, whole-pair training/calibration/holdout boundaries, recursive
prediction gates, and a stop-at-boundary policy. S23 does not authorize a
controller or MPC.

If authentication and reproduction pass but any frozen action, current,
rank, condition, or novelty gate fails:

```text
SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_FAIL_SCHEDULE_REDESIGN
```

The failed S23 identity remains frozen. A new design may change amplitude or
schedule only under a new stage identity; it may not weaken S23's gates after
seeing the result.

If source identity, raw parsing, formal source reproduction, or independent
artifact reproduction fails, stop as a runtime/code/reporting investigation.
Do not infer a plant or design conclusion.

## Scientific prohibitions and scope

Neither S23 nor a later identification controller may use `pair_id`, history
member, partition, prefix, target ID, delay, slew, current/future wire current,
source future action, source future measurement, or matched-baseline future
values. Those fields may appear only in offline grouping and audit output.

The immutable 250/270 ms arrival and 350/370 ms hold contract is unchanged.
Probe trajectories are forbidden from expert data. No S23 route authorizes
real MPC, new histories, new targets, continuous actuator variation, plant
error, noise, disturbance recovery, long hold, BC, DAgger, or bounded
residual RL.
