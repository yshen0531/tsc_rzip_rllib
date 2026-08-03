# Stage4.2R3c3T13S21 cumulative-exact Card15 campaign design

## Status and purpose

This design is frozen before S21 implementation, deployment, plant advance,
or response outcome.  S21 is a new controller and experiment identity.  It
does not resume, overwrite, or relabel S20.

S21 repeats S20's independently specified pooled-observer question while
changing the calibration action algorithm prospectively: the eighth event
must close the exact cumulative seven-event Card15 field net.  S20 evidence
shows why this rule is required and proves feasibility for one failed
development path only.

## New identity and source boundary

The implementation must define new constants for:

```text
stage
  Stage4.2R3c3T13S21
campaign identity
  cumulative_exact_card15_pooled_causal_observer_campaign_v1
controller revision
  cumulative_exact_card15_calibration_probe_v42r3c3t13s21_v1
package revision
  r42r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_v1
```

S21 authenticates the final S20 forensic report and compact audit SHA-256
`8a94fa842ab49a466ef3bbce07e248adb582f5abd461dca56a7bc81a1d39f890`.
S20 raw is development evidence only.  No S20 raw file is an S21 campaign
result, and all S21 experiment IDs must be fresh.

## Frozen matrix and blindness

The whole-pair split, regimes, source snapshots, and rollout counts are
identical to the prospectively frozen S20 matrix:

```text
training pairs / contexts / rollouts       12 / 24 / 216
calibration pairs / contexts / rollouts      4 /  8 /  72
holdout pairs / contexts / rollouts          4 /  8 /  72
total pairs / contexts / rollouts           20 / 40 / 360
```

S21 reruns all 360 trajectories.  It reuses no successful or failed S20 raw.
Training, calibration, and holdout outcomes open only in that order.  The
pooled model is hashed before calibration outcomes open, and the calibrated
tube is hashed before holdout outcomes open.  A failed context cannot be
dropped, substituted, or reassigned.

## Causal cumulative-closure action

The underlying visible-state controller, task clock, QR field basis,
response action, delay/slew handling, horizons, and source authentication
remain as in S20.  Calibration task steps 0 through 6 retain S20's rule:

1. compute the underlying action from current causal state and memory;
2. obtain the current Card15 center;
3. keep the four-direction S16 QR basis frozen at task step zero;
4. choose the nearest exactly representable signed displacement around the
   current center;
5. record the actual four-dimensional current-domain coordinate;
6. apply all unchanged action, current, and geometry gates.

At task step 7 only, the action is frozen as:

```text
running_net = exact Decimal sum of actual field displacements at steps 0..6
closure_delta = -running_net
target_field = current causal Card15 center + closure_delta
```

Every target must be exactly representable as a ten-character Card15 field.
The selected action must reproduce those target fields exactly.  No nearest
independent negative pulse may replace cumulative closure at step 7.

The closure is still the negative sign of fixed direction index 3 and must
pass the unchanged S20 geometry gates against that desired negative
direction:

```text
signed primary coordinate                    [0.85, 1.15]
maximum absolute cross-coordinate                     0.15
minimum desired/actual current cosine                  0.98
maximum relative off-basis residual                    0.15
maximum incremental/total action              unchanged S16
maximum current utilization                   unchanged S16
exact cumulative net after step 7                         0
```

If exact cumulative closure is not representable or fails any gate, the
trajectory stops before the eighth plant advance and the phase fails.  The
algorithm may not look at a future measurement, future action, future Card15
center, outcome, pair/history/partition label, source action/result, or wire
current to avoid the failure.

The trace must separately record the seven-event pre-net, exact closure
delta, target fields, actual coordinate, geometry metrics, and post-event
exact net.  The selector method name is frozen as
`dynamic_cumulative_exact_card15_closure`.

## Model, statistical, and timing contract

The dynamic 10x8 design, nine pooled features, ridge grid, whole-pair outer
selection, response scales/floors, four-times calibrated residual tube,
component caps, point-error gate, and forbidden-input boundary are unchanged
from S20.

Formal timing is immutable:

```text
slew 1.0/1.1  arrive by 250 ms, hold through 350 ms
slew 0.9      arrive by 270 ms, hold through 370 ms
R/Z           30 mm
speed         0.1 m/s
Ip            10 kA
arrival streak 3
```

Baseline formal tracking remains diagnostic only.

## Phase order, reporting, and resume rules

```text
offline authentication and zero-plant preflight
training baselines -> zero-plant full-path lattice gate
training probes -> whole-pair OOF model -> model hash
calibration baselines -> zero-plant full-path lattice gate
calibration probes -> calibrated tube -> tube hash
holdout baselines -> zero-plant full-path lattice gate
holdout probes -> final independent raw recomputation
```

Every terminal failure must set a terminal `phase_status` consistent with
`finished=true` and its stop reason; S20's stale `offline_ready` terminal
field must have a regression test.

Resume may reuse only byte-authenticated S21 success raw generated by the
exact same controller source, experiment IDs, physical actions, task matrix,
and gates.  Any controller/action change requires another identity.  A
statistics/report-only correction may not open a later phase early.

## Required validation before real execution

- Python compile and all JSON parse;
- focused and complete unit tests;
- exact S20 forensic hash and full historical source authentication;
- exact 40 contexts and 360 fresh S21 experiment IDs;
- unit and integration tests for cumulative Decimal closure, exact target
  reproduction, geometry/action rejection, and stale terminal-state repair;
- source-fingerprint and resume incompatibility tests against S20;
- zero-plant replay of every available S20 training baseline, including the
  previously failed path, proving unchanged steps 0--6 and the new causal
  step-7 closure;
- import closure, manifest/checksum verification, and empty-directory direct
  copy simulation inside the repository;
- server path preflight, `bash -n`, package verification, compile/import,
  focused and complete tests using the existing virtualenv;
- a fresh S21 offline run with zero raw/TSC/plant advances before the first
  real phase.

## Routes and claim boundary

An execution or action-gate failure stops the phase and is classified before
any observer conclusion.  Training, calibration, and holdout observer routes
remain as in S20, under new S21 names.

A complete S21 holdout pass authorizes only an offline robust-transport MPC
feasibility stage and a separately preregistered real-MPC campaign.  It does
not validate closed-loop restart transport, unseen targets, continuous
parameters, noise, disturbance recovery, independent long hold, expert data,
BC, DAgger, or RL.  Every S21 probe trajectory remains forbidden from expert
datasets.
