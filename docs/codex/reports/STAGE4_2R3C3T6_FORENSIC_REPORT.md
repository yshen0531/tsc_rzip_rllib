# Stage4.2R3c3T6 target-residual identification forensic report

Date: 2026-07-31 (Asia/Shanghai)

## Final result

T6 completed all 224 authentic restart TSC tasks. Its three newly measured
directions passed their own execution, symmetry, hidden-history and
conditioning gates, but the preregistered combined eleven-column gate
failed:

```text
raw / completed / execution pass                    224/224
extended baseline prefix exact                        32/32
central-symmetry response groups                      96/96
matched hidden-history groups                         48/48
new three-basis rank / condition                      32/32
maximum new three-basis condition                  5.6097803
combined eleven-basis rank                            32/32
combined condition <= 25                               2/32
maximum combined condition                        79.1359286
maximum current utilization                         0.390400
runtime / restart / causal / probe / solver errors          0
certified primary pass                                    no
```

Formal tracking was a preregistered diagnostic, not an acceptance gate:
100/224 passed and 124/224 failed the unchanged contract.

## Reporting bug and semantics-preserving correction

The original summary attempted to join each T6 baseline to the T3 controller
bank using:

```text
trajectory[0].currents_a_display
```

T3 `initial_coil_currents_A` is stored in native TSC order. The authentic raw
field that matches it element-for-element is:

```text
trajectory[0].currents_a_tsc
```

For a forensic sample, bank and `currents_a_tsc` had maximum absolute
difference zero, while the presentation-order field differed by up to
36.979 A. The original summary therefore marked all 32 T3 samples unmatched
and never evaluated a combined matrix.

This was a statistics/reporting bug, not a runtime, controller, task,
action, restart, plant, raw or snapshot error. The one-field fix and exact
resume/package-chain guard were committed as:

```text
62af8ef  fix(stage4.2r3c3t6): match bank currents in TSC order
1a070f7  fix(package): declare T6 hotfix contract count
```

The hotfix contract binds the original package digest and old/new hashes of
the T6 runtime source, server postprocessor and regression test. Controller
revision, package revision, config digest, task matrix, experiment IDs,
actions, formal gates and source fingerprints did not change.

Local validation:

```text
focused T6 tests                                      8/8
full test suite                                    577/577
empty-directory deployment suite                   577/577
manifest/checksum closure                          191/191
```

Server validation:

```text
manifest/checksum and shell syntax                     PASS
focused T6 tests                                      8/8
full test suite                                    577/577
validation log SHA-256
3b9bfceb371d101073ed7a2a2f9eed3ffc39d77da4b284030321c606423b9180
```

Safe resume reused all 224 complete raw results. The before/after raw
SHA-256 inventories are byte-identical:

```text
3a119e0f255b0d09bfc8b1e6401c94c970076fca3e5ac5b5e40dd7aa3e28938b
```

No actor, worker, Ray initialization, `gotsc`, plant advance or new raw file
was created by the resume.

## Independent raw and package audit

Remote run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t6_runs/
stage4_2r3c3t6_target_residual_new_direction_identification_20260731_040257
```

Remote corrected audit:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t6_audits/
stage4_2r3c3t6_target_residual_new_direction_identification_20260731_040257
```

Load-bearing evidence:

```text
original runtime package digest
4502545134ce2b4bc298fd99c3011e663b101ed6f26dbeced78ff8fe18aaba26

active reporting-hotfix package digest
86fd4d25abccce2b3714a93a30941059690b555e66ec880e381c6dd90132320e

raw count / raw inventory digest
224
594b4333eb848c762aec557744fe2dcef9101e1cc495f8713ed8bbe2f2913f61

corrected independent server audit SHA-256
6e04a023ddfa36216c74d669a4848261a7f4581b31ac74a4b35561f06b638dfa
```

The independent postprocessor found:

```text
raw identity, filename, spec and parse exact             yes
snapshot state count / integrity                          8/8
manifest and source evidence exact                        yes
runtime/audit package fingerprints exact                  yes
reported summary exactly reproduced from raw              yes
statistics/reporting error count after correction           0
```

Large raw JSON.GZ and snapshots remain on the server. Compact evidence is
under:

```text
docs/codex/audits/stage4_2r3c3t6_result_20260731_040257/
```

## Matrix-level scientific conclusion

All 32 combined matrices have rank eleven. The failure is conditioning, not
rank loss:

```text
condition minimum / median / maximum
22.0788908 / 38.1423122 / 79.1359286
```

The three new columns alone are well-conditioned in every context. The
inherited T3 eight-column matrix is not:

```text
T3 eight-column condition <= 25                     11/32
T3 eight-column maximum                         78.1544662
```

This exposes a preregistration/design defect in T6. The preflight verified
the condition of the commanded schedules, but not the already measured
context-specific eight-column response matrix. Since the old Gram matrix is
a principal submatrix of the augmented Gram matrix, singular-value
interlacing implies:

```text
condition([old, new]) >= condition(old)
```

Therefore the combined <=25 gate was structurally unreachable in at least
21/32 contexts before any T6 task ran. This does not convert T6 to PASS:
even among the 11 contexts where the inherited bank could meet the limit,
only two combined matrices passed.

Column normalization would pass 27/32, but post-result normalization is not
the preregistered raw-response gate and cannot be used to reinterpret T6.
Common rescaling of the new three columns also left the worst condition near
78.94 and never yielded more than two passing contexts.

## Error classification

```text
runtime/environment error                                  no
deployment/import error                                    no
raw or snapshot corruption                                 no
original statistics/reporting bug                         yes
reporting bug corrected without new TSC                    yes
plant restart fidelity failure                              no
controller causality failure                                no
new three-direction identification failure                  no
combined-bank preregistration/design failure               yes
real closed-loop controller failure                    not run
reliable restart MPC established                            no
```

T6 probe trajectories are identification data, not expert demonstrations.
They validate only bounded local response on the locked development
contexts. They do not validate independent histories, unseen targets,
continuous parameters, plant/model error, noise, disturbance recovery or
long hold.

T7 subsequently selected a fixed non-label-conditioned eight-direction
subset and tested formal feasibility without new TSC. Its separate report
records that result. BC, DAgger and bounded residual RL remain prohibited.
