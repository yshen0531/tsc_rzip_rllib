# Stage4.2R3c3T10 interaction-aware feasibility report

Date: 2026-07-31 (Asia/Shanghai)

## Final result

T10 is a clean offline feasibility FAIL. It authenticated all 224 immutable
T9 raw trajectories, fitted the preregistered interaction-aware surface in
32/32 contexts, and reproduced all 32 frozen formal baseline metrics exactly.
The surface nevertheless passed unchanged-contract optimistic feasibility
only 16/32 and repaired 0/16 failed baselines.

T10 ran no TSC, plant step, Ray campaign, or real MPC controller. This is not
a real closed-loop failure. It is evidence that the measured bounded joint
stress/PC3 authority is insufficient.

```text
authenticated T9 raw                                  224/224
model fit                                               32/32
formal baseline reproduction                            32/32
saved / reproduced baseline passes                      16/32
optimistic interaction-aware feasibility                16/32
failed baselines repaired                                0/16
baseline passes regressed                                   0
axis-validation campaign authorized                         no
R3c4 authorized                                             no
```

## Exact code and execution

```text
implementation/design commit  0af50e1
package-marker hotfix          d36f7b4
branch                         codex/stage4_2r3c3t10-interaction-aware-feasibility
```

The hotfix changed only a package-rule key from `root_shell_scripts_include_`
to the backward-compatible `root_shell_scripts_are_` prefix. Before the
change, the server complete suite passed 599/602; the three failures were old
launcher-availability assertions. After the metadata-only fix, package tests
passed 15/15 and the complete server suite passed 602/602. No T10 optimizer
or result existed before that correction.

```text
remote output
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t10_interaction_feasibility/
stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505

remote log
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505.log
```

Deployed hashes:

```text
PACKAGE_MANIFEST.json  f3db9ed9b1fe20e42cf3d71cda30861137fe50d3d5a607e50377fde2259a0083
SHA256SUMS             06c2b1e8a9b52bb68fc3f9f99d9da5b42e9373b197408b1e10a17d10c4712502
T10 config             4187c86daeecf04c303a410ec8f3a3fe5be0bea889e923a66a0f639c1bea7fec
T10 tool               971aa7e41294875eb0e0ea14e16b74b981fa60997a937f2eace54a77f8c6264d
formal evaluator       7b7b3d15b770efaa9a6d648aa69e4dfb35dbdb596c34dc8d6e38fdfba65f31b2
```

## Raw authentication and model fit

```text
T9 raw inventory
e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2

raw count / unique exact specs                         224 / 224
execution authentication                              224 / 224
T9 certified identification result                         PASS
T9 fixed linear route                                      FAIL
```

The fixed six-term surface had rank 6 and condition
`2.9897369702272503`. Its maximum error at all seven measured nodes was
`1.0842e-19`. The frozen formal evaluator reproduced every T9 baseline pass
and margin with maximum error zero.

## Full context forensics

The 16 passes were exactly the original 16 baseline passes. Breakdown:

```text
prefix 5 / prefix 9                                      4/16 / 12/16
offset target / nominal target                           4/16 / 12/16
delay 2 weak / delay 0 normal                            4/16 / 12/16
minus-first / plus-first                                  8/16 / 8/16
```

Every failed-context optimizer selected a boundary point. All 16 optima
were actual T9 factorial nodes rather than unmeasured interior interpolation:

```text
(stress, PC3) = (+1,+1)                                    11
(stress, PC3) = (+1,-1)                                     5
```

The T10 optimum margins equal the independently stored T9 raw-derived
factorial formal margins in 16/16 contexts, with maximum difference zero.
None of those real measured corners passed formal control.

```text
failed margin gain range                 +0.0047100 to +0.0175795
failed mean margin gain                               +0.0085002
best remaining failed margin                         -0.0584972
worst remaining failed margin                        -0.3562992
active position constraint                                13/16
active post-speed constraint                                3/16
```

This rules out an interpolation/reporting explanation for the negative
result. The measured actions move every failed context in the helpful
direction, but not far enough. T8 had already shown that linear coefficient
expansion through 4x does not repair these contexts; T10 now shows that the
measured nonlinear joint corners do not repair them either.

## Output inventory

```text
manifest      1bed61bc20f47545fdfcaf9acf665623aae985edfa2414cb6f3af00d9787a834
audit         8c15b5339a10d45987839a28d57aa3294e765a2ee0175b6ce1247a2229d0f1a0
feasibility   9d792677e9bccfea4159ee31f9132e24b9ffba1192694696528af9a4e6b52aa3
model bank    8039b5b61255cf53e49848a9d2f61e85d3c3c887f084ccdf5482d8fb40d6fd31
run log       db9e325e83b653f78df43462ffec6c164d19ea368bca90b550f86f603204a09f
```

The 1.41 MB model bank remains on the server. Only the compact manifest,
audit, feasibility result, and log were downloaded.

Two read-only post-run inventory commands were malformed by the local
PowerShell-to-SSH quoting layer. One left `grep -En Traceback` waiting on
stdin. Its exact shell PID 1663689 and child PID 1663814 were inspected and
terminated. This validation incident neither touched T10 nor changed any
result file.

## Error classification and next route

```text
runtime/environment error in T10                              no
raw or snapshot corruption                                    no
statistics/reporting error                                    no
model rank/condition/node-fit failure                         no
pre-run package metadata compatibility bug                   yes
metadata bug changed scientific semantics                    no
real plant restart tested by T10                              no
real closed-loop controller tested by T10                     no
measured bounded authority sufficient                         no
```

The previously proposed 128-task axis de-aliasing campaign is vetoed: it
cannot rescue a surface whose failed optima are already exact measured
corners. The next stage must identify genuinely new time-localized
target-relevant authority that separates transport from braking. It must not
be an amplitude expansion of T7/T8/T10, and it must retain authentic restart,
hidden-history pairing, zero-net safety, current limits, and the immutable
formal timing. R3c4, BC, DAgger, and residual RL remain unauthorized.
