# Stage4.2R3c3T12 formal-gap route discriminator design

## Status and purpose

Final status: completed at package commit `386c051`; the fixed
condition-first route was vetoed. The immutable design below is retained for
audit. The final result is in
`STAGE4_2R3C3T12_FORMAL_GAP_ROUTE_DISCRIMINATOR_REPORT.md`.

This design is frozen after the final T11 identification result and its
read-only server forensics. T12 is a retrospective, server-side route audit
of immutable T11 evidence. It is not a new identification campaign and it
does not reinterpret T11's failed response-condition gate.

T12 answers a narrower planning question:

```text
Is repairing the seven T11 condition failures aligned with repairing the
sixteen authentic R3c1/T11-baseline formal-control failures?
```

It executes no Ray task, `gotsc`, TSC plant step, restart rollout, probe,
controller, optimizer, or snapshot creation. The 250/270 ms arrival and
350/370 ms hold contract is immutable.

## Frozen source identity

The only real-rollout source is:

```text
stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9
```

Required source facts are:

```text
T11 implementation package commit                         40944f9
raw count                                                   416
raw total bytes                                      19,273,198
raw inventory digest
  f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3
manifest SHA-256
  4bdf50b4c1dd3ed21ea6450f3a7c74fac728bdc679cc4d4a1d54f19505ba9fc0
results SHA-256
  056fdb109d5ec9956bad0beaa20fa5c8f2c732bd7554543bd567829af942d5b3
condition results SHA-256
  56a7743a8e318a597f3338ff16c1b6858c8f8664ed80a30f1db1b037660d7d5b
independent server audit SHA-256
  02933f9ee05f91f6db565e955e0106c65dc6591f273fb562e68ac2767d28c19c
```

Every raw JSON.GZ must be reopened in place. The audit requires 416 unique
experiment IDs, 416 successful/completed results, 416 51-state trajectories,
416 50-row causal traces, and zero forbidden controller-input declarations.
Large raw files remain on the server.

## Frozen analysis

The audit uses the exact 32 context keys:

```text
pair_id, history_member, target_id, actual_delay_steps, actual_slew_scale
```

Each context must contain one extended baseline and the exact twelve measured
T11 signed probes. No response columns may be added, rescaled, normalized,
combined, optimized, or extrapolated.

The following quantities are recomputed:

1. The 2-by-2 cross table of baseline formal PASS/FAIL against the frozen
   unnormalized T11 condition PASS/FAIL.
2. For every failed baseline, the best actually measured single-probe formal
   signed margin, absolute gain, gap-coverage ratio, probe identity, and count
   of real single-probe repairs.
3. For every passing baseline, the count and identities of real single-probe
   regressions.
4. Counts stratified by prefix family, target, actuator case, hidden-history
   member, and probe schedule.
5. Exact reproduction of the frozen T11 condition values and the seven failed
   context identities without changing their acceptance status.

The gap-coverage ratio for a failed baseline is descriptive only:

```text
max(0, best_measured_probe_margin - baseline_margin)
-----------------------------------------------------
                    abs(baseline_margin)
```

It is not a linear-combination model, counterfactual controller, or formal
feasibility claim.

## Frozen route interpretation

T11 remains an identification-design FAIL if its original condition gate is
25/32. T12 cannot change that verdict.

The fixed-basis-condition-first route is vetoed when the authenticated cross
table shows both of the following:

- a formal-PASS/condition-FAIL population, proving that failed conditioning
  is not necessary for formal failure;
- a formal-FAIL/condition-PASS population, proving that passed conditioning
  is not sufficient for formal control.

An immediate full-size new TSC campaign is not authorized by T12. If the
measured T11 corners do not close every failed baseline, the next work is an
architecture-first formal-gap analysis. Any later real identification must
use a separately preregistered sentinel with a prospective continuation gate
based on measured task-relevant authority, robust identifiability,
interaction validation, and current safety.

## Scientific limitations

T12 is retrospective development evidence. It cannot prove that the plant is
globally unreachable, that arbitrary time-varying actions are insufficient,
or that a state-conditioned/relinearizing MPC cannot work. It does not
validate hidden-history robustness, unseen targets, continuous actuator or
plant parameters, noise, disturbance recovery, or long hold.

It does not build a T11 response bank or R3c4 feasibility model. Probe
trajectories remain forbidden from expert datasets. R3c4, BC, DAgger, and
bounded residual RL remain unauthorized.
