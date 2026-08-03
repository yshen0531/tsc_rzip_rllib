# Stage4.2R3c3T13S24D1 contracted-amplitude preflight design

## Status and purpose

This design is frozen while the already-open S24 training-sequence boundary
is still completing and before its final task count, inventory, or terminal
state is known.  The observed failure class is therefore allowed to determine
whether this design is applicable, but no last-wave outcome may change the
fixed amplitude, gate, selection rule, or route below.

S24D1 is a zero-new-TSC development preflight.  It asks whether one fixed
contraction of the S23R1 amplitude-coded schedule remains exactly
constructible on all forty authenticated S21 source baselines and whether the
completed S24 training raw has exactly the failure class this contraction is
designed to address.  It does not simulate the plant response to the new
amplitude and cannot authorize a full identification campaign directly.

## Required S24 source boundary

S24D1 may run only after the opened S24 training-sequence command has exited
and its campaign state is terminal.  It must authenticate, in place:

- the 24 active successful training baselines;
- all 576 active training sequence raw files and exact saved specs;
- the active raw inventory, state, manifest, training gate, and complete log;
- the separately preserved 576-file pre-hotfix failure inventory and its
  exact audited digest;
- the semantics-neutral fixed-basis dictionary hotfix audit;
- the exact S23R1 detailed, summary, manifest, and 360 immutable S21 raw.

The active S24 raw is applicable to this design only if all of the following
are true:

```text
strictly parsed active training raw                         600 / 600
successful active baseline raw                               24 / 24
sequence success plus structured failure                    576 / 576
old fixed-basis dictionary error in active raw                     0
issue-action failure                                               0
TSC / solver / restart / causality / corruption failure            0
every sequence failure event                    sequential_cancel only
every failed cancel requested amplitude                            0.50
every failed cancel criterion other than incremental-action        pass
every actually executed 0.25 cancel event                          pass
calibration outcomes opened                                           0
holdout outcomes opened                                                0
```

If any condition differs, S24D1 must stop with
`S24_SOURCE_FAILURE_CLASS_CHANGED_STOP`.  It may not add another amplitude,
weaken a gate, discard a failing context, or reinterpret the result.

## Fixed contracted schedule

The H16 construction, row order, central-negative rows, direction order,
issue/cancel steps, exact Card15 search, and all S23R1/S24 physical gates are
unchanged.  Only the two formerly 0.50 canonical block amplitudes change:

```text
canonical block     S24 amplitude     S24D1 candidate
pattern "++++"          0.25                0.25
pattern "+-+-"          0.25                0.25
pattern "++--"          0.50                0.225
pattern "+--+"          0.50                0.225
```

The machine-readable map is exactly:

```json
{
  "++++": 0.25,
  "+-+-": 0.25,
  "++--": 0.225,
  "+--+": 0.225
}
```

No amplitude grid, alias, or post-result search is allowed.

For the requested 24 by 16 matrix, the preregistered algebraic expectations
are:

```text
rank                                                        16
normalized global condition                   1.5713484026368
maximum normalized slot condition             1.1111111111112
central negative rows                         exact 8 / 8
```

## Static exact-Card15 replay

S24D1 must replay the fixed contracted matrix on all forty S21 source
baselines using the same recorded source baseline issue/cancel states as
S23R1.  Every one of the 3,840 issue and 3,840 cancellation constructions
must preserve the unchanged gates:

```text
exact 10-character target/reproduction                    14 / 14
requested coordinate error                                  <= 0.07
minimum active absolute coordinate                           >= 0.18
desired/applied physical-current cosine                      >= 0.98
relative off-basis residual                                  <= 0.10
incremental normalized action                                <= 0.25
total normalized action                                      <= 1.00
predicted current utilization                                <= 0.55
exact return to stored issue center                              true
exact zero target-field jump net                                 true
no clipping, saturation, nonfinite value, or hidden label use    true
```

Every actual reconstructed context matrix must retain global rank 16,
normalized global condition at most 3, rank four and condition at most 3 in
each slot, late residual at least 0.5, and Decimal-exact central sign target
symmetry.

This replay is not a plant-response simulation.  In particular, a static
cancel pass is not evidence that the contracted online cancel remains below
0.25 after the issue changes the real plant and the underlying feedback
action.

## Fixed sentinel-spec selection

If and only if the source and static gates pass, S24D1 constructs a compact
sentinel spec table from every S24 active sequence raw whose structured
failure is the allowed 0.50 cancellation incremental-action failure.  It may
not select only the worst row or omit a history member.

Each selected spec keeps its exact source snapshot, numerical target, clean
actuator regime, horizon, and sequence index, but receives fresh stage,
campaign, controller, package, environment, experiment, run, raw, state,
manifest, log, and Ray identities.  Its schedule uses the fixed contracted
map above.  S24 raw may be used only for source authentication and deterministic
spec selection; no S24 future state, action, coil current, wire current, or
outcome is available to the sentinel controller.

The sentinel design to follow must require every selected trajectory to:

- use a fresh TSC process and fresh causal controller;
- execute all four issue/cancel pairs and the full 35/37-state horizon;
- pass all unchanged 0.25 action/current/Card15 gates;
- additionally keep maximum online cancellation increment at or below 0.24;
- preserve exact restart, calibration, causality, no-label access, and zero
  target-jump net;
- treat formal tracking as diagnostic only.

The stricter 0.24 sentinel margin is an added prospective development gate;
it does not replace or weaken the repository-wide 0.25 action safety cap.

## Routes

Source class or authentication failure:

```text
S24_SOURCE_FAILURE_CLASS_CHANGED_STOP
```

Contracted static Card15/geometry failure:

```text
CONTRACTED_AMPLITUDE_PREFLIGHT_FAIL_REDESIGN_REQUIRED
```

The only pass route is:

```text
CONTRACTED_AMPLITUDE_PREFLIGHT_PASS_SAFETY_SENTINEL_REQUIRED
```

A pass authorizes only the separately implemented real-TSC safety sentinel
over the exact selected failed-spec set.  It does not authorize S24 resume,
the full replacement identification campaign, a transition model, MPC,
expert data, BC, DAgger, or RL.

## Scientific interpretation

S24D1 creates zero raw, snapshots, TSC processes, controller actions, or
plant advances.  It must report runtime/environment errors, deployment
errors, raw corruption, reporting/statistics errors, action-schedule design
failures, and real control/restart conclusions separately.

The immutable 250/270 ms arrival deadlines and 350/370 ms hold endpoints are
unchanged.  Probe and sentinel trajectories remain forbidden from expert
datasets.  Independent hidden histories and initial states, new targets,
continuous delay/gain/slew, plant/model mismatch, noisy sensing, disturbance
recovery, and independent long hold remain unvalidated.
