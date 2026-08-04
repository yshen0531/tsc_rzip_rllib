# Stage4.2R3c3T13S24D1R14 v1 issue-gate hotfix audit

## Scope and evidence boundary

This audit was frozen after the first D1R14 package completed its 72 raw
results and independent server recomputation, but before any corrected
controller or corrected TSC run was implemented.  It does not change the
prospectively frozen D1R14 task matrix, physical requested coordinates,
timing, response gates, action bounds, current bounds, or scientific scope.

The affected immutable run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14_runs/
stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_20260804_2d5304c_v1
```

Its raw inventory is 72 files and 1,841,053 bytes with digest
`bf07f39c4b83666a48f545d89ab4c7cff18f6ef473a89133b7afd99fd34321df`.
The primary final-result SHA-256 is
`bfd8c88705f8bea138adc36a42d576c472b56b79e44f081a4bbd241e2720a908`;
the accepted independent audit SHA-256 is
`3a6958c2519da4d43e0d910a51d33c0c971352e01a2f68578c1bc4b6b6750e2b`.

## Recomputed result

Primary and independent server-side recomputation agree:

```text
strict raw / exact restart and source prefix                 72 / 72
fresh zero baselines reaching the full horizon                 8 / 8
signed probes stopped before task-step-10 plant advance       64 / 64
signed issue actions actually applied                           0 / 64
signed trajectory / controller-trace lengths               11 / 10 each
runtime / environment / solver / plant / corruption errors           0
```

All 64 attempted issue constructions passed the actual D1R14 action and
plant-safety predicates:

```text
finite / exact center / exact target / target reproduction    64 / 64
actuator gate / incremental action / total action              64 / 64
current utilization / no saturation / no current clipping     64 / 64
maximum attempted incremental normalized action        0.0518518519
maximum predicted current utilization                         0.37705
```

They were rejected by predicates inherited from the dense four-active-
coordinate S24 row design:

```text
all-four-coordinate sign predicate                              0 / 64
minimum over all four coordinates >= 0.18                       0 / 64
dense-row cosine predicate                                     32 / 64
dense-row off-basis predicate                                  16 / 64
```

The first two predicates are structurally incompatible with the D1R14
one-hot coordinate matrix: three requested coordinates are exactly zero by
design.  The inherited implementation takes the minimum over all four actual
coordinates and requires every actual sign, including quantization residuals
in inactive coordinates, to equal the corresponding requested zero sign.

## Classification

The v1 route `ZERO_BASELINE_EXCITATION_SAFETY_FAIL_REDESIGN_REQUIRED` is an
accurate report of the executed code, but it is not a plant, probe-response,
geometry, control, or MPC result.  It is a controller issue-gate integration
bug: the exact Card15 action was safely constructed, then rejected before it
could reach TSC by dense-row identification predicates that were never part
of the D1R14 preregistered one-hot action contract.

The D1R14 design explicitly freezes only the following issue gates:

- finite construction;
- one fixed nonzero requested coordinate at the frozen direction and sign;
- exact stored center and exact Card15 target fields;
- exact target reproduction by the actuator;
- no saturation or current clipping;
- incremental normalized action at most `0.25`;
- total normalized action at most `1.0`;
- predicted current utilization at most `0.55`; and
- the unchanged underlying actuator safety gate.

The active-coordinate sign is retained as a fail-closed check of the frozen
signed direction.  Actual-coordinate error, active magnitude, desired-current
cosine, inactive-coordinate leakage, and off-basis residual remain recorded
diagnostics.  They are not retroactively introduced as D1R14 acceptance gates.
Non-vacuous plant response, even/odd separation, rank, and condition remain
the unchanged post-execution D1R14 response gates.

## Execution decision

The controller source and source fingerprint must change, so the v1 run may
not resume.  Its 72 raw files remain immutable.  The corrected package must
use a new controller/package revision and a fresh run directory, repeat all
72 fresh controllers and TSC trajectories, and pass the complete local,
empty-directory, staging, installed-server, primary, and independent audit
chain.  No raw from v1 may satisfy a corrected-run gate or enter an expert
dataset.

This hotfix authorizes only the intended D1R14 sentinel.  Transition-model
fitting, MPC, expert data, BC, DAgger, and bounded residual RL remain blocked.
