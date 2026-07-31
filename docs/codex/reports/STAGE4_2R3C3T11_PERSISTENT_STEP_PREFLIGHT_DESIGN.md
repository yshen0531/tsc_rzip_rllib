# Stage4.2R3c3T11 persistent-step response preflight design

## Rationale

T10 fitted its measured interaction surface exactly but repaired none of the
16 failed contexts. Every failed optimum was already a real T9 factorial
corner. T8 had separately shown that scaling the existing target-direction
columns through 4x also repaired none. The next design must therefore add
new temporal authority, not scale or de-alias the failed episode schedules.

R3c3 used short zero-net pulses at early and deadline phases. T1/T2 used
multi-step early ramps. T6/T9 used full formal-window target-residual
schedules. T11 instead proposes persistent step responses: one bounded mode
increment is applied at a fixed physical effect state and held by the plant's
incremental-current semantics until an equal and opposite post-contract
neutralization. This is a new time-localized input-response experiment for a
future relinearizing MPC model.

## Frozen schedules

For each public actuator case and each of physical modes 0, 1, and 2:

```text
transport step first physical effect state      3
braking step first physical effect state       17
positive step amplitude                    0.0075
negative compensation effect states        39..44
compensation per state                  -0.00125
observation horizon                            50
```

Delay is handled only by converting each physical effect state to the public
task issue step `effect - delay - 1`. The schedule does not depend on pair,
history, target, source result, source action, coil current, or hidden wire
current. Each signed probe has seven nonzero issues, exact zero net, component
bound 0.0075, and formal L2 below 0.015.

The two start states separate early transport authority from authority that
begins before both immutable arrival deadlines and can affect braking and
hold. Compensation begins only after both formal hold endpoints.

## Frozen offline gates

The preflight must authenticate the exact T3, T6, T9, and T10 chain. It must
reconstruct the old 12-column action schedule matrix exactly, then require in
both public actuator cases:

- all six new schedule columns have rank 6;
- the old plus new matrix has rank 18;
- normalized augmented condition number is at most 10;
- every new normalized column has residual norm at least 0.25 outside the
  old 12-column span;
- all issue/effect states, amplitudes, zero-net sums, and bounds are exact.

The old eight columns are read from the T3 eight-basis bank with SHA-256
`6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86`,
which is the exact bank authenticated by the frozen T6 and T9 preflights.
Two initial T11 invocations stopped before producing an output because the
launcher incorrectly supplied the same-shape T7 controller bank. Correcting
that source reference changes no new schedule, gate, task count, or formal
timing term.

If the preflight passes, the prospective real identity is fixed at 32 fresh
extended baselines plus `32 x 6 x 2 = 384` signed probes, 416 real rollouts
total. Real acceptance would additionally require exact restart and causal
execution, central symmetry, paired-history invariance, current utilization
no greater than 0.55, rank 6, and velocity condition no greater than 25 in
all 32 contexts.

## Scope

The preflight executes no TSC. Action novelty is not plant-response novelty.
Even a successful real signed-step identification would be a local
development-envelope result, not a global nonlinear plant model and not a
controller result. A later combined-step validation would still be required
because T9 proved material interaction at episode-schedule amplitude.

The formal 250/270 ms arrival and 350/370 ms hold contract is unchanged.
Probe trajectories are not demonstrations. R3c4, BC, DAgger, and residual RL
remain unauthorized.
