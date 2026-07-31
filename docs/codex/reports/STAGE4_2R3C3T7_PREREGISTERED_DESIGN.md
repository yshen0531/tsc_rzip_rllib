# Stage4.2R3c3T7 authenticated target-basis feasibility design

Frozen before T7 formal optimization and server output creation on
2026-07-31. The candidate subset was already exposed by post-T6 development
forensics; it is not a blinded selection and is not independent validation.

## Purpose

T6 remains a certified identification-design failure:

```text
new three-basis rank / condition                    32/32, <= 5.609781
combined eleven-basis rank                         32/32
combined eleven-basis condition <= 25                2/32
maximum combined condition                         79.135929
```

The inherited T3 eight-column bank alone exceeds condition 25 in 21/32
contexts. By singular-value interlacing, appending columns cannot make the
eleven-column condition gate pass in those contexts. This was a T6
preflight-design defect, not a TSC runtime, restart, causality, raw, or new
three-direction failure.

Post-result route discrimination exhaustively inspected all 8-of-11 global
subsets and exposed one fixed subset that is rank eight and condition <=25
on all 32 locked development contexts:

```text
T3 basis indices                              0, 1, 2, 3, 7
T6 probes                    r17_target_action_residual
                              matched_visible_target_equal_pc1
                              matched_visible_target_equal_pc2
worst observed raw velocity condition                 20.517347
```

No selection may depend on pair or hidden-history labels. No response column
may be normalized or rescaled after measurement.

## Exact prospective T7 question

Using the fixed eight directions above, test the same optimistic linear
formal-feasibility question used by T3:

```text
baseline + sum(c_i * authenticated_odd_response_i)
c_i in [-1, 1]
```

The formal evaluator, timing, R/Z tolerance, speed threshold, Ip thresholds,
arrival streak, exhaustive ternary grid, multistart SLSQP settings, and
tie-breaking remain frozen.

## Authentication

T7 must independently authenticate:

- corrected T6 manifest, state, summary, server audit, raw count and raw
  inventory digest;
- exact T6 package/source identity and reporting-only resume chain;
- all 224 T6 raw identities, completion/success, schedules, and context
  coverage;
- exact T3 manifest, audit bank, controller bank and feasibility hashes;
- exact frozen T3 optimizer and formal evaluator hashes;
- 32/32 equality between the T6 extended-baseline formal prefix and the T3
  saved baseline;
- a one-to-one T3 controller-bank/T6 baseline numeric key mapping;
- deterministic exhaustive reproduction of the fixed global subset.

Any mismatch aborts before output creation.

## Frozen gate

```text
contexts                                                  32
baseline formal passes                                    16
selected basis count                                       8
rank / raw velocity condition                       8, <=25 on 32/32
coefficients                                           [-1,1]
optimistic formal passes                                  32
failed baseline repairs                                   16
baseline-pass regressions                                  0
formal timing                                        unchanged
```

T7 runs no Ray, `gotsc`, TSC process, plant trajectory, or snapshot. A
failure keeps MPC execution blocked. A pass authorizes only implementation
of a development restart MPC followed by separate offline and real-TSC
gates; it does not establish a reliable expert.

T6 probe trajectories remain identification data and are forbidden from
expert datasets. BC, DAgger, and bounded residual RL remain prohibited.
