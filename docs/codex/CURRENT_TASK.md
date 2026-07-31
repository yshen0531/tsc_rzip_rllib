# CURRENT_TASK.md — post-T7 target-authority redesign

## 1. Terminology and certified checkpoint

```text
R1  = Stage4.2R1 authentic TSC plant-state restart
R17 = Stage4.1R17 frozen finite static-grid controller source
```

Certified foundations:

```text
Stage4.1R17 finite clean static grid                    18/18
Stage4.2R1c authentic plant-state restart               18/18
Stage4.2R2 causal controller-state restart              18/18
Stage4.2R3c3 bounded local response identification     256/256
```

Frozen development control results:

```text
R3b fresh phase-zero control                  0/32
R3c ideal-visible phase alignment            20/32
R3c1 authenticated R17 R/Z/Ip alignment      16/32
R3c2 zero-nominal restart regulator          12/32
```

These stages are immutable. Do not overwrite, relabel, resume under changed
semantics, or weaken their gates.

## 2. Final Stage4.2R3c3T1 result

Exact real run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_runs/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441
```

Result:

```text
raw / execution / exact restart / causal trace          128/128
central symmetry                                          64/64
matched hidden history                                    32/32
transport-only rank and condition                         32/32
combined rank six                                         32/32
combined condition <= 25                                  27/32
worst combined condition                             29.2962711
runtime / restart / causality / solver errors                  0
maximum current utilization                              0.3904
```

T1 is a real identification-design FAIL, not a runtime, plant-restart,
summary/reporting, or real MPC control failure.

Load-bearing fingerprints:

```text
T1 raw inventory
  f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f

T1 server audit
  0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd

corrected six-basis feasibility diagnostic
  e7bc8f0168ff1d2019f1a9a232b5152a27d46a66a92f9542d31d80c6942c3164
```

The corrected audit reproduces all 32 saved R3c1 formal results and shows:

```text
mode0 scale   combined condition pass   optimistic formal pass
1.00                        27/32                      16/32
0.85                        32/32                      16/32
0.80                        32/32                      16/32
0.75                        32/32                      16/32
0.70                        32/32                      16/32
```

No scale repairs a failed formal context. Do not run an amplitude-only T2.

Full report:

```text
docs/codex/reports/STAGE4_2R3C3T1_FORENSIC_REPORT.md
```

## 3. Final Stage4.2R3c3T2 result

Stage4.2R3c3T2 was executed as a new independent identity:

```text
purpose
  identify a bounded odd response that remains active through the immutable
  350/370 ms formal hold, then neutralizes after the contract

observation horizon
  50 steps / 500 ms

positive physical-effect states
  3..8

negative physical-effect states
  39..44

observation tail
  45..50

amplitudes
  held_transport_mode0 = 0.0060
  held_transport_mode1 = 0.0075

matrix
  32 contexts × (1 extended baseline + 2 modes × 2 signs)
  = 160 real TSC tasks
```

The complete prospective design is frozen in:

```text
docs/codex/reports/STAGE4_2R3C3T2_PREREGISTERED_DESIGN.md
```

Follow it exactly. Any change to schedule, amplitude, context matrix, formal
timing, acceptance thresholds, or controller information boundary requires a
new prospective design identity before real TSC.

The first v2 execution attempt is preserved at run
`stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_222433`.
Its 11/11 saved raw files are structured runtime failures caused by an
inherited 35/37-step episode limit; zero trajectories succeeded. This is not
a scientific T2 result. Package v2h1 restored the preregistered 50-step
episode horizon and adds payload/environment horizon guards without changing
controller or experiment semantics. The failed run must not be overwritten
or resumed.

The exact valid run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t2_runs/
stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_225902
```

Independent raw recomputation certified:

```text
raw / execution / exact restart / causal trace          160/160
extended zero-probe prefix exact                          32/32
central symmetry                                          64/64
matched hidden history                                    32/32
transport rank and condition                              32/32
combined six-basis rank and condition                     32/32
worst combined condition                              22.893801
maximum current utilization                              0.3904
runtime / restart / causality / solver errors                  0
formal tracking diagnostic                               70/160
```

Load-bearing evidence:

```text
raw inventory
  e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f

server audit
  e96f9538f5878ac745424d783e8f57c5ff41d61220b7d22ea66bfb1a08107d9c
```

Two post-run reporting/resume bugs were repaired without rerunning TSC or
changing raw/controller semantics: the 50-step result is copied and truncated
to the frozen 35/37-step evaluator, and completed-run resume no longer treats
authenticated existing raw as a failed first-run empty-directory gate.
Package v2h2 contains these normal-source fixes and passed 549/549 tests.

Full report:

```text
docs/codex/reports/STAGE4_2R3C3T2_FORENSIC_REPORT.md
```

## 4. Formal timing remains immutable

```text
slew 1.0:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms

R/Z tolerance                 30 mm
speed threshold               0.1 m/s
Ip thresholds                 frozen
arrival streak                frozen
```

The 500 ms identification horizon does not permit later arrival and is not
an independent long-hold success test. Neutralization begins physically at
state 39, after both formal hold endpoints.

## 5. Mandatory controller boundary

T2 may use only current/past visible R/Z/Ip, current/past 14-coil currents,
target, causal task-start actuator values, the exact R3c1 controller, and
the fixed T2 task-clock schedule.

It may not use wire/vessel currents, pair/history labels, T1/R3c3 source
actions or outcomes, another member, future measurements/actions, or
post-action current-step telemetry.

Probe trajectories are identification data and are forbidden from expert
datasets.

## 6. Required pre-run validation

Before real TSC:

- compile changed Python and parse every JSON;
- focused and complete tests;
- import closure, manifest, and checksum verification;
- exact R3b/R3c1/R3c3/T1 fingerprints;
- exact 32 contexts, 32 extended baselines, 128 signed probes, and 160 T2
  identities;
- exact delay-aware issue/effect mapping;
- exact 12-issue requested/applied zero net;
- first negative physical effect exactly state 39;
- hidden-wire, label, source, and future-information guards;
- source-fingerprint and resume-compatibility tests;
- empty-directory direct-copy simulation inside the repository;
- server preflight, shell syntax, import/compile/package/full tests;
- offline finite controller audit for 160 specs;
- offline raw zero, plant advance zero, real TSC false.

Use direct uncompressed transfer only.

## 7. Prospective T2 gates

```text
complete / exact restart / causal                         160/160
extended zero-probe prefix exact                            32/32
exact signed probe schedule                               128/128
runtime / solver / clipping / forbidden-input errors              0
maximum current utilization                                    <= 0.55

central even velocity RMSE                                <= 0.004 m/s
central even position RMSE                                <= 0.0005 m
central even Ip RMSE                                      <= 20 A

matched-history odd velocity RMSE                         <= 0.006 m/s
matched-history odd position RMSE                         <= 0.001 m
matched-history odd Ip RMSE                               <= 40 A

contract-prefix transport rank / condition                2/2, <= 25
contract-prefix combined rank / condition                  6/6, <= 25
```

Condition windows end at the original formal hold state 35 or 37. The
post-contract cancellation tail must be reported separately and cannot
improve the controller-use condition matrix.

Formal tracking of signed probes is diagnostic-only.

## 8. Completed server result loop

The valid 160-task identity is complete. All raw and snapshots remain on the
server. Only compact audit JSON, state, manifest, config, summary, verdict,
and logs were downloaded.

Always distinguish:

- runtime/environment error;
- packaging/deployment error;
- raw/snapshot corruption;
- summary/reporting error;
- unrun test;
- identification-design failure;
- real plant-restart or closed-loop control failure.

## 9. Final T3 eight-basis complementarity result

The authenticated post-T2 six-basis bank was built on the server. The frozen
gate result is:

```text
condition pass                                      32/32
maximum condition                               22.893801
optimistic formal pass                              16/32
failed baseline repair                               0/16
baseline-pass regression                             0/16
```

This is a pre-execution design failure. R3c4 must not be implemented or
launched.

The new read-only eight-basis complementarity audit used:

```text
R3c3 local four
+ T1 long-separation two
+ T2 held-transport two
```

It retained the unchanged gate:

```text
eight-basis optimistic formal feasibility               32/32
coefficients                                             [-1,1]
baseline pass regression                                      0
formal timing unchanged                                      yes
```

The final result is:

```text
eight-basis rank                                    32/32
eight-basis condition <= 25                         11/32
maximum condition                              78.1544662
optimistic formal feasibility                       16/32
failed baseline contexts repaired                    0/16
baseline-pass regressions                            0/16
real TSC executed                                      no
```

All 16 failed contexts improve relative to the old four-basis, T1 six-basis,
and T2 six-basis alternatives, but all remain below zero signed margin. The
eight coefficients are saturated in 15 or 16 of the 16 failed contexts.
This proves useful complementarity but insufficient bounded causal authority,
and the eight-column representation is also partly redundant.

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T3_EIGHT_BASIS_COMPLEMENTARITY_REPORT.md
```

R3c4 remains unauthorized. The active task is prospective, no-new-TSC route
discrimination:

1. quantify the response-amplitude extrapolation required to repair the
   locked failed contexts, without treating extrapolation as validation;
2. determine whether an authenticated richer response model is available;
3. freeze any new real identification schedule/amplitude as a new identity
   before execution.

Do not relax or reinterpret the failed T3 gate. A diagnostic extrapolation
cannot authorize R3c4 or a real TSC controller run.

The first route discriminator is frozen as Stage4.2R3c3T4:

```text
profiles
  transport-only coefficient expansion
  uniform eight-basis coefficient expansion

scales
  1.25, 1.50, 2.00

execution
  server-side authenticated offline postprocessing only
  no Ray, gotsc, TSC, trajectory, or snapshot creation

interpretation
  unvalidated linear amplitude requirement only
  never an R3c4 authorization
```

Prospective design:

```text
docs/codex/reports/
STAGE4_2R3C3T4_AMPLITUDE_ENVELOPE_DESIGN.md
```

## 10. Final T4 amplitude-envelope result

T4 completed as a server-side offline diagnostic:

```text
profile / scale       formal pass   repairs   condition <= 25
transport 1.25×            16/32      0/16              2/32
transport 1.50×            16/32      0/16              2/32
transport 2.00×            20/32      4/16              0/32
uniform   1.25×            16/32      0/16             11/32
uniform   1.50×            16/32      0/16             11/32
uniform   2.00×            20/32      4/16             11/32
```

Only four slow-actuator nominal-target contexts repair at `2×`; all 12
offset-target contexts remain failed. No coefficient exceeds its diagnostic
bound, no TSC was run, and R3c4 remains unauthorized.

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T4_AMPLITUDE_ENVELOPE_REPORT.md
```

The active next task is to determine whether exact authenticated plus/minus
raw trajectories support a separable even/quadratic response diagnostic:

```text
baseline + sum(c_i * odd_i + c_i^2 * even_i)
```

This must be prospectively frozen before execution, retain coefficients
`[-1,1]` and immutable formal timing, and report that cross interactions,
combined-action safety, and real control remain unvalidated. If exact even
terms cannot be authenticated, or the diagnostic fails, proceed to a new
real identification identity with genuinely new target-relevant temporal or
actuator directions. Do not return to amplitude-only scaling.

The read-only availability check found:

```text
signed raw files / pairs                         512/512, 256/256
raw success and hash failures                                  0
odd-response maximum reproduction error                       0.0
```

T5 is now prospectively frozen with coefficients `[-1,1]`, exact formal
timing, and all cross interactions explicitly omitted:

```text
docs/codex/reports/
STAGE4_2R3C3T5_SEPARABLE_QUADRATIC_DESIGN.md
```

It is a server-side offline route diagnostic only. Regardless of its formal
count, it cannot repair the measured T3 odd-column condition failure or
authorize R3c4.

The first T5 server attempt stopped before optimization/output because
float64 recomposition of a 30 kA Ip value accumulated exactly one ULP
(`3.637978807091713e-12`) and tripped the `1e-12` identity gate. Odd/raw
agreement remained exactly zero-error. T5h1 commit `ff3b391` evaluates only
that defining identity in 80-digit decimal arithmetic, preserves the
original threshold and all scientific semantics, and must run under a new
output/log identity.

## 11. Final T5 separable-quadratic result

T5h1 authenticated all raw inputs and completed:

```text
signed raw files / pairs                         512/512, 256/256
odd and signed-endpoint reproduction error                    0.0
optimistic quadratic formal pass                         16/32
failed T3 contexts repaired                               0/16
baseline-pass regressions                                  0/16
unchanged odd condition <= 25                            11/32
real TSC executed                                           no
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T5_SEPARABLE_QUADRATIC_REPORT.md
```

The separable even terms improve 11 failed margins and worsen five, but
repair none. All zero-new-TSC variants of the existing eight response
directions are now exhausted. R3c4 remains unauthorized.

The active task is a new-direction design preflight:

1. use authenticated R17 source actions, visible target error, and existing
   response-bank spans to quantify the residual action direction;
2. prove the candidate adds a target-relevant direction rather than another
   scaled or collinear copy of the existing eight;
3. prospectively freeze a new bounded signed-probe identity before any real
   TSC execution;
4. retain plant restart, causal information, current limit, and formal timing
   unchanged.

Do not run another amplitude-only or interaction-free-model audit.

Even a pass does not validate a reliable restart MPC, independent histories,
unseen targets, continuous actuator/plant parameters, noise, disturbance
recovery, or long hold.

BC, DAgger, and bounded residual RL remain prohibited.

## 12. Final T6 target-residual identification result

T6 executed 224/224 authentic restart TSC tasks. A reporting bug initially
matched native-TSC bank currents against presentation-order raw currents, so
all 32 combined matrices were incorrectly reported as unrun. Commits
`62af8ef` and `1a070f7` corrected only that join and added an exact
semantics-preserving resume/package chain.

The resume reused all 224 raw files; before/after raw SHA-256 inventories are
byte-identical:

```text
3a119e0f255b0d09bfc8b1e6401c94c970076fca3e5ac5b5e40dd7aa3e28938b
```

Independent corrected result:

```text
raw / execution                                     224/224
central symmetry                                      96/96
matched hidden history                                48/48
new three-basis condition <= 25                       32/32
maximum new condition                               5.609780
combined eleven-basis rank                            32/32
combined condition <= 25                               2/32
maximum combined condition                         79.135929
runtime / restart / causal / probe / solver errors          0
```

The inherited T3 bank itself passes condition <=25 in only 11/32 contexts,
with maximum 78.154466. T6 preflight checked schedule conditioning but not
this inherited response condition, making the combined gate structurally
unreachable in at least 21 contexts. This is a preregistration/design defect.
It does not change T6 to PASS.

Corrected server audit SHA-256:

```text
6e04a023ddfa36216c74d669a4848261a7f4581b31ac74a4b35561f06b638dfa
```

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T6_FORENSIC_REPORT.md
```

## 13. Final T7 authenticated target-basis feasibility result

T7 froze the same label-independent global 8-of-11 subset for every context:

```text
T3 indices                                 0,1,2,3,7
T6 directions                              all three
```

It executed no TSC. The exact old evaluator and `[-1,1]` bounds produced:

```text
rank / condition <=25                               32/32
maximum condition                                20.517347
optimistic formal pass                              16/32
failed baseline repairs                               0/16
baseline-pass regressions                              0/16
```

All three new-direction coefficients saturate in 15/16, 16/16 and 16/16
failed contexts. Every failed T7 margin is worse than the corresponding T3
solution. The bank representation is now well-conditioned, but measured
bounded linear authority remains insufficient.

Exact hashes:

```text
implementation/design commit
d530ed5

feasibility
d4dbcd4a114eec10110432d6bf4337182bcb805b27ab83d689a9e216a052ed30

manifest
e69980452e756686c43ce37b6f3a471b37d6c804b3a6109fa22ea5905921ed74
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T7_TARGET_BASIS_FEASIBILITY_REPORT.md
```

R3c4 remains unauthorized.

The active task is a new post-T7 route discriminator:

1. quantify, without claiming validation, whether the unused current
   headroom can close the T7 margins for the newly measured target-relevant
   directions;
2. retain exact `[-1,1]` T7 as failed and do not weaken any gate;
3. if headroom is insufficient, freeze a new real identification identity
   with genuinely new target-relevant temporal/actuator authority and
   combined-action nonlinearity measurement;
4. do not repeat the old T4 amplitude-only or T5 separable-even routes;
5. do not implement R3c4, BC, DAgger or residual RL.

Even a future development-set feasibility pass will not establish
independent histories, unseen targets, continuous actuator/plant
parameters, noise, disturbance recovery or long hold.

## 14. Final T8 measured-current headroom result

T8 implementation/design commit:

```text
d98820e
```

T8 executed no TSC. It authenticated the T7 bank and 512 referenced raw
plus/minus files, reconstructed all selected current odd responses, and
expanded only the three new target-direction coefficient bounds:

```text
scale             1.00   1.25   1.50   2.00   3.00   4.00
formal pass      16/32  16/32  16/32  16/32  16/32  16/32
failed repairs    0/16   0/16   0/16   0/16   0/16   0/16
current pass     32/32  32/32  32/32  32/32  32/32  32/32
maximum current  0.3904 at every scale
```

At scale four, the best remaining margin is `-0.0183834`, the worst is
`-0.3347514`, and the three new coefficients remain saturated in `15/16`,
`16/16` and `16/16` failures. Current headroom is not the bottleneck.

Exact post-result enumeration of all 165 global 8-of-11 subsets found that
T7's subset is the only one satisfying rank eight and condition <=25 in all
32 contexts. There is no remaining condition-qualified old-subset route.
Enumeration SHA-256:

```text
b4512c71d64e1c43ce123b59c608a5cf09e990246936645c7683fbf4d4840e88
```

Independent raw/current/formal audit SHA-256:

```text
d7ab83a37496fde3ba9afcd8fdfebeff16df8313931c013d93fbd3b7d366b2b8
```

The first launch had a pre-import `PYTHONPATH` environment error and created
no scientific output. The unchanged v2 launch completed successfully. This
is recorded separately from the scientific result.

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T8_HEADROOM_DIAGNOSTIC_REPORT.md
```

T8 is a clean offline route veto. It is not a real controller or plant
failure. R3c4 remains unauthorized.

The active next task is to preregister and preflight a genuinely new
target-relevant temporal/actuator combined-action identification:

1. add temporal authority not collinear with the failed T7/T8 bank;
2. measure combined-action interaction directly, not by separable-even or
   columnwise linear assumptions;
3. keep arrival at 250/270 ms and hold through 350/370 ms;
4. authenticate the same restart state and hidden-current evidence;
5. require response symmetry, history invariance, conditioning and a
   prospective feasibility gate before any R3c4 implementation;
6. run no BC, DAgger or residual RL.

## 15. Final T9 PC3 and mixed-interaction preflight result

T9 preflight implementation/design commit:

```text
cbb970b
```

The preflight executed no Ray, gotsc, or TSC. It authenticated the exact
R17/R3c1/T3/T6/T7/T8 source chain, reproduced the first three T6 schedules
with zero error, and added the third equal-context target-residual principal
direction outside the complete eleven-schedule T6 span:

```text
actuator                         delay 0 / slew 1.0   delay 2 / slew 0.9
PC3 singular value                         1.134704              0.777812
minimum four-direction coverage            0.999912              0.995362
complete action rank                          12/12                 12/12
complete normalized condition               2.55106               2.55106
selected action rank                            9/9                   9/9
selected normalized condition               1.23002               1.23002
```

The direct mixed-action design uses one label-independent T8 failure-stress
schedule per public actuator case and the exact four signs:

```text
+stress +pc3
+stress -pc3
-stress +pc3
-stress -pc3
```

The common factorial amplitude is `0.01060660171779821`. Every schedule
retains formal L2 `<= 0.015`, component magnitude `<= 0.0075`, exact zero
net, and physical cancellation only at states 39 through 44.

Exact preflight hash:

```text
9a37168cce679df7deeb242bceb996c11f41bf9e589459e27386ece45f41e560
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T9_PC3_MIXED_INTERACTION_PREFLIGHT_REPORT.md
```

This is an action-design PASS only. It does not validate the PC3 plant
response, combined-action linearity, hidden-history control, formal control,
or R3c4 feasibility.

The active task is to implement and validate the frozen independent T9 real
identification identity:

```text
32 contexts x (
  1 extended baseline
  + 2 standalone PC3 signs
  + 4 stress-by-PC3 factorial signs
)
= 224 real TSC tasks
```

The real campaign must preserve exact restart/causality, current utilization
`<= 0.55`, standalone symmetry, PC3 and mixed-contrast history invariance,
and selected nine-basis response rank/condition `9/9, <=25`. A linear route
also requires mixed-response and PC3-background modulation ratios `<=0.10`.
A reproducible larger interaction must be retained in a separately validated
interaction-aware model; it may not be discarded.

R3c4, BC, DAgger, and residual RL remain unauthorized.

## 16. Final T9 real-identification result

The exact valid run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t9_runs/
stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005
```

Package v1h1 completed all 224 authentic restart TSC probes:

```text
raw / execution / exact restart / causal trace          224/224
extended baseline prefix exact                            32/32
standalone PC3 central symmetry                           32/32
PC3 matched-history response                              16/16
mixed-factorial response                                  32/32
mixed-contrast matched-history response                   16/16
selected nine-basis rank / condition <=25                 32/32
maximum selected condition                            23.1552081
maximum current utilization                               0.3904
runtime / restart / causal / solver / reporting errors         0
```

The independent raw and snapshot audit passed with exact reported-summary
recomputation:

```text
raw inventory
  e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2

server audit
  05547765ca5e1282e58b0d33e454b0a2a4dd87ee16e85146261650510ebd05f8
```

The identification gate passed, but the separately preregistered linear
route failed:

```text
mixed velocity ratio <=0.10                              2/32
PC3 background modulation <=0.10                         0/32
both linear-route conditions                              0/32
mixed ratio range                              0.071638--0.300282
PC3 modulation range                           0.181011--1.079864
```

The interaction is reproducible across the matched histories and cannot be
discarded. A fixed linear nine-column response bank is invalid for the
combined actions measured here. This is a model-route failure, not a T9
runtime, restart, corruption, reporting, or identification-design failure.

Formal tracking passed 104/224 as a preregistered probe diagnostic only. T9
did not run a new MPC controller, and its trajectories remain forbidden from
expert datasets.

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T9_PC3_MIXED_INTERACTION_IDENTIFICATION_REPORT.md
```

The active next task is to prospectively freeze and execute an independent
interaction-aware offline model audit. It must authenticate the exact T9
chain, retain stress, PC3, stress-by-PC3 Walsh contrast, and measured PC3
background modulation, preserve coefficients/current/formal timing, and
require unchanged-contract optimistic feasibility before any R3c4
implementation. It may not silently fall back to a fixed linear column,
separable-even model, amplitude expansion, BC, DAgger, or residual RL.
