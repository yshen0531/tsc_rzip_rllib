# Stage4.2R3c3T8 measured-current headroom diagnostic report

Date: 2026-07-31 (Asia/Shanghai)

## Final result

T8 ran a server-side offline diagnostic over the 32 authenticated T7
development contexts. It did not execute Ray, `gotsc`, TSC, a plant step or
a controller.

Increasing only the three newly measured target-direction coefficient
bounds did not repair any failed context:

```text
target-direction scale       pass     repair     regression     current
1.00                        16/32       0/16          0        32/32
1.25                        16/32       0/16          0        32/32
1.50                        16/32       0/16          0        32/32
2.00                        16/32       0/16          0        32/32
3.00                        16/32       0/16          0        32/32
4.00                        16/32       0/16          0        32/32
```

The maximum predicted current utilization at every scale was `0.3904`,
below the unchanged `0.55` limit. Current headroom is not the active
bottleneck in this linear diagnostic.

T7 at scale one remains failed and unchanged. T8 does not authorize R3c4.

## Frozen implementation and validation

Prospective implementation/design checkpoint:

```text
d98820e  feat(stage4.2r3c3t8): freeze current-headroom diagnostic
```

Local:

```text
Python compile / all 43 config JSON                         PASS
focused T8 tests                                             3/3
full suite                                                583/583
empty-directory direct-copy full suite                   583/583
package closure                                           199/199
```

Server:

```text
package/checksum/import/shell syntax                         PASS
focused T6 / T8 tests                                    8/8, 3/3
full suite                                                583/583
installed validation log SHA-256
c98599f43cdb3ad4dbc0928748c134654cb13767ad36878a787c75f0fe54a5b6
```

Remote output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t8_headroom_diagnostics/
stage4_2r3c3t8_headroom_diagnostic_20260731_d98820e
```

Remote independent audit:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t8_audits/
stage4_2r3c3t8_headroom_diagnostic_20260731_d98820e
```

Primary hashes:

```text
result
5fba92cbe0690267d25a7b6f97f53c0d2144e9453420fc7945c05b29d45e18a1

manifest
a966edd0dfde43dbf16ce76372d13340d25b7361a0ca0b7637e6032639967602

independent server audit
d7ab83a37496fde3ba9afcd8fdfebeff16df8313931c013d93fbd3b7d366b2b8

successful execution log
7c61060204a28a86ee7deb57e716762a05499dc61a9f6fc57672d5136d33da2a
```

## Launch incident

The first offline launch exited before importing the project because the
subdirectory script invocation omitted the repository root from
`PYTHONPATH`:

```text
ModuleNotFoundError: No module named 'tsc_rzip_rllib'
```

It created no output and ran no optimizer, Ray, TSC or plant step. The
failed launch log SHA-256 is:

```text
6a2ead6ea50612512953c5bb121ec5ee146aacb3855970c1edee050e8a027527
```

The v2 launch changed only the process environment by setting
`PYTHONPATH=$PWD`; code, config, hashes, inputs, bounds, scale grid and
scientific identity were unchanged. This is a runtime/launch error followed
by a safe fresh offline launch, not a resume or scientific rerun.

SciPy emitted boundary-clipping warnings during some SLSQP trial steps. The
stored coefficients were explicitly clipped to the frozen bounds and then
re-evaluated. Independent recomputation confirms every final bound and
current constraint.

## Independent raw recomputation

The independent server audit read the large raw data in place and verified:

```text
T6 raw inventory                                           224
selected signed responses                                 256
unique referenced plus/minus raw files                    512
raw reference hashes exact                                yes
position odd responses exact                              yes
all old/new coefficient bounds exact                      yes
formal margins independently reproduced                   yes
maximum formal-margin difference                  4.44e-15
predicted currents independently reproduced               yes
maximum current-utilization difference                       0
reported scale summaries exact                            yes
```

The current odd model used:

```text
delta_current = (current_plus - current_minus) / 2
predicted_current = authentic baseline
                    + sum(coefficient * delta_current)
```

The maximum signed-pair midpoint discrepancy from the cross-stage baseline
was `0.25 A`, or `0.00125` normalized utilization, within the prospectively
frozen `0.0013` model-consistency bound.

Only the compact result, manifest, logs and audit were downloaded. Raw
JSON.GZ and large banks remain on the server.

## Scientific forensics

The failed-context margins improved slowly but never crossed zero:

```text
scale     best failed     median failed     mean failed     worst failed
1.00       -0.048522        -0.133635        -0.165987       -0.347448
1.25       -0.046766        -0.130951        -0.163563       -0.346390
1.50       -0.044681        -0.128565        -0.161266       -0.345331
2.00       -0.039422        -0.123970        -0.156720       -0.343215
3.00       -0.028903        -0.112055        -0.148231       -0.338981
4.00       -0.018383        -0.097767        -0.138070       -0.334751
```

At scale four, all 16 original failures remain:

```text
offset target / nominal target                         12 / 4
delay 2, slew 0.9 / delay 0, slew 1.0                 12 / 4
minus-first / plus-first                                8 / 8
active position / post-speed                           12 / 4
```

The target-action residual, matched-visible PC1 and PC2 coefficients are at
their expanded bounds in `15/16`, `16/16` and `16/16` failures. Increasing
their amplitude changes the margin but does not supply enough independent
temporal/actuator authority. Since current use stays baseline-dominated,
the failure is not caused by the `0.55` current gate.

A post-result route enumeration then checked all `C(11,8)=165` global
eight-direction subsets with the exact frozen velocity definition. T7's
`[0,1,2,3,7,8,9,10]` is the only subset that satisfies rank eight and
condition `<=25` in all 32 contexts. Thus there is no untested
condition-qualified global subset among the existing eleven directions.
The compact enumeration SHA-256 is:

```text
b4512c71d64e1c43ce123b59c608a5cf09e990246936645c7683fbf4d4840e88
```

All scales above one are unvalidated linear extrapolations. Their failure is
useful as a route veto; a hypothetical pass would not have been a real
plant or controller result.

## Error and conclusion classification

```text
first-launch runtime/environment error                       yes
first-launch scientific output created                        no
v2 runtime error                                               no
deployment/import error after PYTHONPATH correction            no
raw corruption                                                 no
statistics/reporting error                                     no
design limitation: present temporal directions insufficient   yes
current-headroom limitation                                    no
real plant restart test                                   not run
real closed-loop controller test                          not run
R3c4 implementation authorized                                 no
reliable MPC expert established                                no
```

The next route must prospectively identify genuinely new target-relevant
temporal/actuator directions and measure combined-action nonlinearity. It
must not repeat T4 amplitude-only scaling, T5 separable-even scaling, or T8
linear coefficient expansion. Formal timing remains unchanged. BC, DAgger
and residual RL remain prohibited.
