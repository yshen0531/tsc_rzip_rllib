# Stage4.2R3c3T13S23D1 bounded schedule-redesign search

## Status and claim boundary

This document freezes the D1 search space before D1 implementation or any D1
candidate computation. D1 is an adaptive, development-only, zero-new-TSC
search initiated after the frozen S23 schedule failed. It is not a
preregistered plant experiment, held-out model result, controller, or MPC.

D1 may nominate at most one exact schedule for a separately configured and
implemented S23R1 preflight. D1 itself cannot authorize S24, a real rollout,
an expert dataset, BC, DAgger, or RL.

## Immutable sources

D1 must authenticate, read in place, and not modify:

- all 360 raw files and compact artifacts from the completed S21 campaign;
- the exact S21 baseline selected for each of the 40 pair/history contexts;
- the final S22 output and its independent postprocessor;
- the primary failed S23 detailed output, summary, manifest, config, and
  implementation hashes.

It must reproduce the S21 baseline/probe formal counts and the S23 route and
gate counts exactly. Formal outcomes are authentication evidence only and may
not be a search objective.

## Frozen finite search space

The four coordinate columns retain the exact S21 active-calibration QR order:

```text
0  mode0_without_coil8
1  mode0_coil8_component
2  mode1
3  mode2
```

Candidate coordinate templates are exactly every nonzero vector in
`{-1,0,+1}^4`, multiplied by one amplitude in:

```text
0.25, 0.50, 0.75, 1.00
```

Global sign mates are evaluated explicitly. There are 80 signed ternary
directions per amplitude and 320 signed templates in total. No continuous
optimizer, rotated direction, response-derived direction, per-context
amplitude, or outcome-conditioned template is allowed.

Candidate issue steps are the integers 10 through 19. Cancellation is always
the immediately adjacent step `issue + 1`, so the last possible cancel step
is 20. A four-knot set must be strictly ordered, have at least two task steps
between consecutive issues, and pass the cancellation construction in all 40
contexts. The fixed basis must remain identical through every selected step.

The source-baseline replay semantics remain those of S23: issue construction
uses the recorded current and underlying action at the candidate issue step;
cancel construction uses the recorded current and underlying action at the
adjacent source-baseline cancel step and targets only the stored pre-issue
Card15 center. This is deliberately an action-space preflight and not a plant
or response simulation.

## Unchanged action and geometry gates

Every signed template retained for a step must pass in every one of the 40
contexts, and its global sign mate must also pass. Required gates are:

```text
exact Card15 center and target reproduction                 14 / 14
finite construction and no saturation or clipping          14 / 14
active coordinate sign preserved                      all active
maximum coordinate error from requested template             0.07
inactive coordinate absolute leakage                         0.07
minimum active absolute coordinate                            0.18
desired/applied physical-current cosine                       0.98
maximum relative off-basis residual                           0.10
incremental normalized action                               <= 0.25
total normalized action                                     <= 1.00
predicted current utilization                               <= 0.55
```

Changing amplitude changes the requested active coefficient; it does not
relax fidelity, cosine, off-basis, action, or current limits. For example, an
amplitude-1 template must reproduce each active coefficient within `0.07` and
keep each requested-zero coefficient within `0.07`.

Each candidate step must also reproduce the exact stored issue center at the
adjacent cancellation, remain exact zero target-field jump net for every
retained signed template, and pass the unchanged action/current limits in all
40 contexts.

## Deterministic schedule search

For each admissible four-knot set in lexicographic order, D1 constructs
candidate schedules from only the step-feasible signed-template catalog. A
schedule contains 16 primary rows and the exact global negatives of primary
rows 0 through 7 as eight central-sign sentinels, for 24 sequences total.

The pseudorandom generator seed is fixed to `423231`. At most 20,000 candidate
schedules may be tested per knot set. The first schedule, in the frozen knot
and generator order, that passes every gate below in all 40 contexts is the
only nominated candidate; search stops immediately:

```text
actual 24 x 16 global rank                                  16
maximum normalized global condition                       3.0
each actual 24 x 4 slot rank                                4
maximum normalized slot condition                         3.0
each late-column residual outside slot-0 span              0.5
all 32 per-context sign-sentinel target checks            exact
```

The matrices use reconstructed actual coordinates, not requested templates.
No formal trajectory score, pair/history label, partition label, target,
delay, slew, source response, future action, or future measurement enters
candidate generation or ranking. Pair/history keys may be used only to ensure
all 40 offline contexts pass the same schedule.

## D1 routes

If no schedule passes the complete fixed search, D1 reports:

```text
BOUNDED_TERNARY_SCHEDULE_SEARCH_FAIL_NEW_EXCITATION_ARCHITECTURE_REQUIRED
```

If a first passing schedule is found, D1 reports:

```text
BOUNDED_TERNARY_SCHEDULE_SEARCH_CANDIDATE_FOUND_FREEZE_S23R1_REQUIRED
```

The latter authorizes only a new S23R1 design document, exact config, complete
implementation/test/package validation, zero-TSC replay, and independent
artifact reproduction. It does not authorize the prospective 1,000-rollout
campaign.

## Scientific prohibitions

D1 executes no Ray, `gotsc`, TSC, controller, plant step, or snapshot. It
does not claim plant response, hidden-history robustness, global
reachability, or MPC feasibility. The immutable 250/270 ms arrival and
350/370 ms hold contract is unchanged. Probe trajectories remain forbidden
from expert data, and BC, DAgger, and bounded residual RL remain prohibited.
