# CURRENT_TASK.md — finite-horizon restart MPC architecture evidence stage

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

## 17. Final T10 interaction-aware feasibility result

T10 implementation/design commit `0af50e1` and package-marker compatibility
fix `d36f7b4` were fully validated before execution. The marker fix changed
no source, model, input, optimizer, gate, or physical semantics. Local tests
passed 602/602; the installed server package passed 15/15 focused and 602/602
complete tests.

T10 authenticated all 224 immutable T9 raw trajectories in place and ran no
new TSC, Ray campaign, plant step, or real MPC. Its six-term interaction-aware
surface passed rank, conditioning, and exact measured-node reconstruction in
32/32 contexts:

```text
design rank                                                6
maximum design condition                    2.9897369702272503
maximum node reconstruction error          1.0842021724855044e-19
formal baseline pass/margin match                          32/32
```

The unchanged-contract optimistic result nevertheless remained:

```text
formal feasibility                                        16/32
failed baseline repairs                                    0/16
baseline pass regressions                                     0
```

All 16 failed optima were exact measured T9 factorial corners: 11 used
`(+1,+1)` and 5 used `(+1,-1)`. Their optimized margins equal the certified
T9 raw-derived corner margins exactly. The failure is therefore not caused
by unvalidated interior interpolation or a reporting error. Helpful margin
gains of `0.00471--0.01758` are too small; 13 failures remain position-limited
and 3 post-speed-limited.

Exact output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t10_interaction_feasibility/
stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505
```

Primary hashes:

```text
manifest     1bed61bc20f47545fdfcaf9acf665623aae985edfa2414cb6f3af00d9787a834
audit        8c15b5339a10d45987839a28d57aa3294e765a2ee0175b6ce1247a2229d0f1a0
feasibility  9d792677e9bccfea4159ee31f9132e24b9ffba1192694696528af9a4e6b52aa3
model bank   8039b5b61255cf53e49848a9d2f61e85d3c3c887f084ccdf5482d8fb40d6fd31
```

T10 is a clean offline measured-authority FAIL, not a runtime, corruption,
restart, real-control, or reporting failure. The 128-task axis de-aliasing
campaign is vetoed, and R3c4 remains unauthorized.

The active next task is to prospectively design and preflight a genuinely
new time-localized plant-response identification that separates early
transport authority from late braking authority. It must not scale the
failed T7/T8/T10 episode-wide schedules, must preserve exact restart and
paired hidden histories, must keep probe actions out of expert data, and
must leave the 250/270 ms arrival and 350/370 ms hold contract unchanged.
No real TSC should run until the new action schedule, current envelope,
context matrix, symmetry/history gates, and downstream MPC-identifiability
criterion are frozen independently of outcomes.

## 18. Stage4.2R3c3T11 persistent-step preflight live handoff

T11 prospectively freezes six persistent incremental-current schedules:

```text
physical modes                                      0, 1, 2
first transport effect state                              3
first braking effect state                               17
positive amplitude                                   0.0075
post-contract cancellation effect states              39..44
observation through state                                 50
new directions                                             6
prospective real tasks        32 baselines + 384 probes = 416
```

The 250/270 ms arrival and 350/370 ms hold contract is unchanged. The
preflight executes no TSC and cannot authorize a controller.

Implementation and source-reference commits are:

```text
3798a21  frozen T11 design and offline preflight
0b61f93  column-normalized numerical rank calculation
a9807b9  exact T3/T9 eight-basis source authentication; package v2
```

Local validation passed 610/610 complete tests and 14/14 empty-package
focused tests. Installed server package v2 passed 228/228 hashes, shell
syntax, compile/JSON, 14/14 focused tests, and 610/610 complete tests. The
load-bearing installed hashes are:

```text
PACKAGE_MANIFEST.json  565591d0983bc941031c9d0a797b11b6d261c2dd86d54a2585d0d0ce84e525d4
SHA256SUMS             4db3b4ffac46e923b47021e7a4cf3a68099fdca612bf44421f47ca18d817fb73
validation log         8ef47cb218cc5bc006675e567bc2734f08f4d37c11019c5119f4aed3142e57a3
```

Two offline invocations stopped before writing a preflight JSON. The first
used an unnormalized numerical rank on differently scaled columns. After
that was corrected, forensics proved the deeper cause: the launcher supplied
the same-shape T7 controller bank instead of the exact T3 eight-basis bank
authenticated by T6 and T9. The T7 bank made the reconstructed candidates
overlap the old span. Package v2 now authenticates the correct T3 bank SHA
`6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86`.
Neither stopped invocation produced a verdict or ran Ray, `gotsc`, TSC, a
plant step, a controller, or a new snapshot.

The corrected third invocation has not started. Four fixed-endpoint SSH
attempts timed out before session establishment after the successful server
v2 validation. This is an external connectivity blocker, not a T11 gate,
plant, restart, control, statistics, or reporting result.

When connectivity returns, run only the guarded corrected offline identity:

```text
output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t11_preflights/
  stage4_2r3c3t11_persistent_step_preflight_v3_20260731_a9807b9

log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t11_persistent_step_preflight_v3_20260731_a9807b9.log
```

First require both paths to be absent. If the corrected preflight passes all
frozen gates, then and only then implement the exact 416-task authentic
identification campaign. If it fails, write the compact result and redesign
without weakening novelty, conditioning, current, or formal timing. R3c4,
BC, DAgger, and residual RL remain unauthorized.

## 19. Final corrected T11 preflight result

SSH recovered and both guarded v3 paths were absent. The corrected offline
preflight then completed normally and passed all frozen gates:

```text
actuator cases                                             2/2
existing / new / augmented rank                       12 / 6 / 18
maximum augmented normalized condition              3.1459621
minimum novelty residual                            0.7726912
bounded and exact zero net                                2/2
real TSC / Ray / gotsc executions                         0/0/0
```

Exact compact hashes:

```text
JSON  a449fd5447bd174b5fa067f464c651bc5a1d3e146bae7f67d22535eed076dfbd
log   aec6db4f4c35436825b66181adb888dc0b9b1622c6aaf2c6c0886ca2eb009050
```

This is an action-design PASS only. The active task is now to implement the
exact preregistered 416-task authentic persistent-step identification and
complete the local-package-server-raw-audit loop. It must not change the six
schedules, 32 contexts, symmetry/history/current/rank/condition gates, or
formal timing. It does not authorize R3c4, BC, DAgger, or residual RL.

## 20. Final Stage4.2R3c3T11 authentic identification result

The exact package at commit `40944f9` completed the frozen 416-task campaign
once, in fixed Ray batches `128 + 128 + 128 + 32`. Independent server-side
raw/snapshot/manifest postprocessing reproduced the reported result exactly.

```text
raw parsed / expected                                      416/416
execution / restart / causality                            416/416
extended baseline prefix                                    32/32
central symmetry                                           192/192
matched hidden-history response                              96/96
response rank 6                                             32/32
response condition <= 25                                    25/32
maximum response condition                              38.9150751
maximum current utilization                            0.3904/0.55
runtime / restart / solver / reporting errors                    0
```

The raw inventory digest is
`f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3`.
The independent server audit SHA-256 is
`02933f9ee05f91f6db565e955e0106c65dc6591f273fb562e68ac2767d28c19c`.
The compact forensic JSON SHA-256 is
`8cf365fcac69924c09bae51c9c5c1c3cc003959ff3e7a92111b387316a8b617b`.

This is a clean identification-design FAIL. Seven context matrices retain
rank 6 but violate the frozen unnormalized condition gate. Independent raw
R/Z differencing and SVD reproduce all reported values to `4.97e-14`, so the
result is not a statistics or reporting bug. Do not normalize columns or
relax the threshold after seeing the result.

Formal tracking remains diagnostic: 207/416 overall, with the exact 16/32
unprobed baseline result preserved. The 500 ms observation horizon changes no
formal deadline and is not a long-hold result.

The active task is now to prospectively design a genuinely new
time-localized identification that improves weak-mode authority and separates
the p9/minus near-collinear response columns without amplitude-only rescaling
or gate weakening. Preserve all T11 raw on the server. Do not build a T11
response bank or R3c4 feasibility model, run R3c4, or start
BC/DAgger/residual RL. No new real TSC is authorized until the new schedule,
action-space novelty, current envelope, context matrix, and downstream
identifiability gate are frozen before outcomes.

## 21. Post-T11 route update and active T12 audit

Read-only server forensics added the missing T11 formal-versus-condition
cross table:

```text
baseline formal PASS / condition PASS                  12
baseline formal PASS / condition FAIL                   4
baseline formal FAIL / condition PASS                  13
baseline formal FAIL / condition FAIL                   3
```

Thus only three of the seven T11 condition failures overlap the sixteen
authentic baseline formal failures. Repairing condition alone would spend
most of its effort on four contexts whose baseline control already passes
and would miss thirteen formal failures whose condition already passes.

The same server-side read-only audit inspected all twelve authentic signed
T11 probe corners around every failed baseline:

```text
failed baselines with any real single-probe repair       0/16
real single-probe repairs in failed contexts                 0
best per-context signed-margin gain range       0.00117--0.00807
probe regressions around passing baselines               1/192
```

These are diagnostic measured-corner facts, not a response-bank combination
or controller-feasibility result. T11 remains a clean identification-design
FAIL under its original 25/32 condition result.

The active stage is now Stage4.2R3c3T12, frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T12_FORMAL_GAP_ROUTE_DISCRIMINATOR_DESIGN.md
```

T12 is a server-side retrospective route audit. It authenticates all T11 raw
in place, reproduces the cross table and actual measured-corner formal-gap
coverage, and records whether condition-first basis expansion is aligned with
the real control deficit. It runs no Ray, `gotsc`, TSC, controller, optimizer,
plant step, or new snapshot.

Do not implement a full new identification campaign directly from the T11
condition failures. After T12, first freeze the downstream finite-horizon,
state-conditioned transport/braking MPC architecture and its task-relevant
authority requirements. If existing evidence is insufficient, use a separate
prospective small sentinel with an explicit stop/continue gate before any
full 32-context campaign.

Formal timing, T11's verdict, the controller information boundary, current
limits, and the prohibition on T11-bank/R3c4/BC/DAgger/residual RL remain
unchanged.

## 22. Final Stage4.2R3c3T12 result and active T13 task

Stage4.2R3c3T12 completed one guarded, read-only server audit at package
commit `386c051`. It authenticated all 416 immutable T11 raw files in place
and reproduced the exact T11 report and route expectations. It ran no Ray,
`gotsc`, TSC, plant step, controller, optimizer, or snapshot creation.

Exact output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t12_route_audits/
stage4_2r3c3t12_formal_gap_route_discriminator_20260801_386c051
```

Load-bearing compact hashes:

```text
audit
  3e5e8e4c52e5b7efb3e068146ceb012f3bb2dc2717c9b5f05107b51ed8fa2970
route result
  9a334aadc45d118ebc8cb58acd6171876c2a9da9f5d2aadf3b46ae9ae1d0be25
manifest
  1efd48c7ce5be3cd3530fa8aa27c2478e661c9e8338b105fd73592515e7cec19
raw inventory digest
  f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3
```

Final route facts:

```text
formal PASS / condition PASS                              12
formal PASS / condition FAIL                               4
formal FAIL / condition PASS                              13
formal FAIL / condition FAIL                               3
failed baselines repaired by a measured single probe     0/16
best measured gap coverage                         0.47%--11.46%
fixed condition-first route                            VETOED
```

This is a route/design conclusion, not a new real closed-loop result. There
was no runtime, environment, packaging, raw, snapshot, statistics, or
reporting error. T11 remains a clean identification-design FAIL at 25/32
condition passes, and the R3c1/T11 unprobed baselines remain a genuine 16/32
controller result.

The detailed report is:

```text
docs/codex/reports/
STAGE4_2R3C3T12_FORMAL_GAP_ROUTE_DISCRIMINATOR_REPORT.md
```

Stage4.2R3c3T13 was frozen in scope by:

```text
docs/codex/reports/
STAGE4_2R3C3T13_FINITE_HORIZON_RESTART_MPC_ARCHITECTURE_PLAN.md
```

T13 is a no-new-TSC architecture and evidence-mapping stage. It must specify
the causal controller state, independent formal clock and local model
coordinate, target-conditioned transport/braking sequence, actuator queue,
hard constraints, robust/model-validity interface, solver fallback, and
audit trace. It must map every component to exact source code and raw-backed
evidence and explicitly distinguish measured support from interpolation and
extrapolation.

The first source-call-graph checkpoint is recorded in:

```text
docs/codex/reports/
STAGE4_2R3C3T13_SOURCE_ARCHITECTURE_AUDIT.md
```

It confirms that the inherited controller uses a fixed Stage3.4 lifted
Jacobian, soft weighted least squares, a separately applied nonlinear coil
scheduler, and fresh-state initialization with zero integral/previous
correction and nominally primed delay queue. The next read-only T13 step is
to test whether that lifted model can predict the time-resolved signed
restart perturbations already present in R3c3/T1/T2/T6/T9/T11 raw evidence.

That no-new-TSC model audit is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_DESIGN.md
```

It corrects `T3` to `T2/T6` in the measured-raw list because T3 produced no
real trajectories. It authenticates 1,408 existing raw files in place and
predefines 576 signed comparisons, 896 same-run baseline-relative measured
nodes, and 32 T9 Walsh interaction contrasts. Its primary input is the
three-mode projection of the actual 14-coil current increment, not the
requested probe schedule. No prediction error was inspected before this
design was frozen.

The first V1 invocation then stopped on its very first raw file before any
Jacobian multiplication or output creation. Source inspection proved that
the trajectory coil-current difference is a post-Card-15 TSC observation,
whereas the trace action is the exact pre-Card-15 command and Card 15 uses
`.3E` finite-precision formatting. V1 had incorrectly required those two
different quantities to agree to `1e-9 A`.

The corrected, still pre-prediction design is frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_DESIGN_V2.md
```

V2 uses the exact recorded 14-coil trace action, multiplied by the actual
slew and projected into the authenticated Stage3.4 mode basis, as the native
Jacobian input. Observed adjacent coil-current differences remain a reported
TSC quantization diagnostic and are not used to select or tune a predictor.
This is an audit-design correction, not a code/summary bug in an experiment
and not a Jacobian, plant, restart, or controller result.

Before starting the complete V2 audit, an input-only one-file preflight found
that the trace action's source-defined `float32` representation produces a
`3.81e-8 A` modal residual. V2's `1e-9 A` gate was therefore below the source
numerical precision; no V2 output identity or Jacobian multiplication was
started. The source-derived conservative bound is `6.7e-7 A`.

The final pre-prediction numerical correction is frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_DESIGN_V3.md
```

V3 changes only the command-subspace numerical gate to `1e-6 A`. All raw
identities, comparison counts, output-error thresholds, causality gates,
formal timing, route rules, and prohibitions remain unchanged.

The first complete V3 invocation then stopped before any Jacobian
multiplication because its raw-schema code expected every R3c3/T1 member to
have 36/35 rows. Exact raw inventory shows the normal cases are 36/35 and the
weak-slew 370 ms cases are authentically 38/37; all were successful and the
forbidden-input checks were clean. T2/T6/T9/T11 remain 51/50.

The V4 schema correction is frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_DESIGN_V4.md
```

V4 authenticates those exact full horizons and still feeds only states
0--35/actions 0--34 to the Stage3.4 model. It changes no model threshold,
comparison, timing, or route rule and creates a new output identity.

The complete V4 audit then authenticated 1,408 immutable raw files totaling
62,444,406 bytes and evaluated the frozen matrix:

```text
signed prediction                                 0 / 576 PASS
finite measured-node prediction                   0 / 896 PASS
T9 Walsh interaction prediction                    0 / 32 PASS
causality                                       1504 / 1504 PASS
first physical effect-state match               1504 / 1504 PASS
```

All 1,504 comparisons failed the scaled relative-response gate. The signed
and interaction tiers passed every absolute gate; finite nodes passed every
absolute gate except four endpoint-late errors with maximum `0.00411513 m/s`
against the unchanged `0.004 m/s` gate. A retrospective optimal-scalar
diagnostic repaired 0/1,504 responses to relative error `<= 0.10`, so the
mismatch is direction/time shape rather than a global gain.

There was no runtime, environment, packaging, raw, snapshot, statistics,
reporting, restart, or causality error. V1--V3 were pre-prediction
audit-design/schema corrections and have no model result. T13 ran no real
controller, optimizer, Ray, `gotsc`, TSC plant step, or snapshot.

The exact T13 result and architecture are:

```text
docs/codex/reports/
STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_REPORT.md
STAGE4_2R3C3T13_RESTART_MPC_ARCHITECTURE_SPEC.md
```

T13 was required to end with exactly one of:

```text
OFFLINE_ARCHITECTURE_COMPLETE
MINIMAL_SENTINEL_REQUIRED
```

The final T13 outcome is:

```text
MINIMAL_SENTINEL_REQUIRED
```

The fixed Stage3.4 lifted Jacobian is vetoed as an unqualified restart
predictor. It is not evidence of global unreachability or a new closed-loop
failure. The missing object is an immediately neutralized, state- and
issue-time-conditioned single-step transition response at transport and
braking time, including the real delay queue and matched hidden histories.

The active prospective design is Stage4.2R3c3T13S1, frozen before code or
execution in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S1_MINIMAL_TRANSITION_SENTINEL_DESIGN.md
```

Its exact matrix is four bookend contexts, four extended baselines, and
48 signed probes: three modes by two signs by two physical effect windows,
for 52 real rollouts if later authorized. Each probe uses `+/-0.0075` at one
issue and the exact inverse at the next issue, producing physical effects at
states 3/4 or 17/18 with exact zero requested net. It observes through state
50 without changing formal endpoints.

T13S1 was implemented under a new campaign/package identity at local commit:

```text
898b559ba5d2f716f4e2e255f9a570b87af3bbb2
ecc05f61838e5c9214bad75fe0a61295429f7a33  package import-closure fix
```

The implementation and local validation record is:

```text
docs/codex/reports/
STAGE4_2R3C3T13S1_IMPLEMENTATION_VALIDATION.md
```

Focused tests pass 7/7, the complete repository suite passes 639/639 in the
repository-local virtual environment, all JSON/compile/checksum gates pass,
and an isolated empty-directory direct-copy import/compile/full-test
simulation passes. The package now declares 269 hashed files plus
`SHA256SUMS`.
The local Windows `bash` maps to an unavailable WSL distribution, so exact
Linux `bash -n` remains a mandatory server pre-run gate.

T13S1 still has zero real trajectories and its scientific result is
`NOT_RUN`. The user authorized continued execution through the prerequisites
for RL on 2026-08-01. Proceed with exact server deployment, server validation,
the zero-plant-step 52-spec offline audit, and then the authentic 52-rollout
campaign only if every pre-run gate passes.

T13S1 PASS can authorize only an offline local-transition model and
prospective holdout design. Its scientific FAIL stops identification
expansion and routes to observer/model/action-resolution redesign. Neither
outcome authorizes a 32-context campaign or a real controller by itself.

Do not build a T11 bank, run R3c4, change formal timing or physical
thresholds, or start BC, DAgger, or bounded residual RL. Continue the full
roadmap autonomously, freezing and validating each new physical experiment,
and pause for user confirmation only when bounded residual RL is genuinely
ready to begin.

## 23. Final Stage4.2R3c3T13S1 result and active T13S2 task

Stage4.2R3c3T13S1 completed its one authorized real campaign at deployed
package commit `ecc05f6`:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s1_runs/
stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_ecc05f6
```

All 52/52 authentic restart `gotsc` trajectories completed. The immutable
raw inventory is 52 JSON.GZ files, 2,463,366 bytes, digest:

```text
de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603
```

Package, four snapshots, restart, causality, solver, scheduler, current,
signal, local rank/condition, raw parse, manifest, and summary recomputation
passed. The frozen scientific response gates did not:

```text
central symmetry                             0 / 24 PASS
matched hidden-history response              0 / 12 PASS
official route          SENTINEL_FAIL_STOP_IDENTIFICATION
```

The official result is final. T13S1 may not be rerun or enlarged under the
same identity. It did not test a real MPC and does not prove plant
unreachability. Its 26 formal trajectory passes are diagnostic only because
formal tracking was not the identification-probe acceptance gate. All probe
trajectories remain forbidden from expert data.

The final read-only forensic at commit `9b8353d` authenticated all 52 raw
files in place and ran zero controller, Ray, `gotsc`, TSC, or plant steps:

```text
requested first-issue command symmetry        24 / 24 PASS
observed first-effect current symmetry          0 / 24 PASS
immediate plant symmetry                        3 / 24 PASS
plant symmetry through formal endpoint          0 / 24 PASS
immediate matched-history response               6 / 12 PASS
full-window matched-history response             0 / 12 PASS
active compared coil-command components             336
components below one Card15 .3E grid                304
maximum observed integer-grid residual       2.1032e-12
```

Finite Card15 action resolution is therefore material. It does not explain
all immediate or later plant behavior. Small causal visible-state/velocity
differences and different forbidden wire-current histories also coexist in
the matched pairs, so the failed matched-history ratio is not a clean proof
of one hidden-current mechanism. The required classification is a clean
identification/model/action-resolution design FAIL: zero runtime,
deployment, restart, corruption, reporting, or real-MPC error.

The formal report and compact downloaded evidence are:

```text
docs/codex/reports/STAGE4_2R3C3T13S1_FORENSIC_REPORT.md
docs/codex/audits/stage4_2r3c3t13s1_result_20260801_9b8353d/
```

The active task is Stage4.2R3c3T13S2, prospectively frozen before audit code
or output in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S2_QUANTIZED_ACTUATION_CAUSAL_OBSERVABILITY_DESIGN.md
```

T13S2 is zero-new-TSC. It must reconstruct all 2,600 T13S1 transitions and
36,400 coil components from the exact Card15 formatter, current-run measured
current, trace action, resolved slew/current bounds, and authenticated turn
counts. It must then audit exact collisions in a causal feature containing
only current/past R/Z/Ip, causal velocity or explicit unknown initial
velocity, measured coil current, already-issued current-run commands/queue,
formal task time, target, and finite development actuator setting.

Pair/history/prefix labels, wire/vessel currents, source action/result,
future measurements, and future probe schedules remain forbidden. Absence of
an exact collision is only finite clean separability, not observer or hidden-
history robustness. Unresolved latent effects must remain a
multi-hypothesis/tube uncertainty.

T13S2 may authorize only an exact quantized-actuator primitive, causal
observer-state schema, set-valued transition interface, and a separately
preregistered minimal lattice-aligned holdout sentinel if existing raw is
insufficient. It cannot authorize a full identification campaign, real MPC,
R3c4, expert data, BC, DAgger, or bounded residual RL.

## 24. Final T13S2/T13S2R1 results and active T13S3 task

Stage4.2R3c3T13S2 completed its frozen zero-new-TSC audit at implementation
commit `626f635`. It authenticated all 52 T13S1 raw files and all 52 exact
environment variants in place. It ran no controller, Ray, `gotsc`, TSC, or
plant step.

Exact source Card15 target reconstruction produced:

```text
transitions                                   2,600 / 2,600
coil components                             36,400 / 36,400
within 1e-9 A                               13,000 / 36,400
maximum target-to-readback residual A             1.0e-5
primary route          ACTUATOR_MAPPING_IMPLEMENTATION_GAP
```

This is an actuator-model completeness gap, not a runtime, raw, restart,
reporting, plant-control, or real-MPC failure. The T13S2 gate and result are
unchanged.

Causal feature and actual-current-path separation found:

```text
issue records                                             48
exact causal-feature collision groups                      8
same feature and same applied-current-path groups           0
exact observational aliases                                0
finite clean matched-history separations                24 / 24
route                           FINITE_CLEAN_SEPARATION_ONLY
```

Finite clean separation is not observer certification. Independent histories,
arbitrary restart states, measurement noise, and continuous parameters remain
unvalidated.

Stage4.2R3c3T13S2R1 was separately frozen and executed as a read-only
target-to-readback residual forensic at commit `ae4241b`. Four baselines
identified a constant per-coil residual:

```text
[2, 2, 2, 2, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0] * 1e-6 kA-turn
```

That fixed development bias then reproduced all 33,600 signed-probe
components within the unchanged `1e-9 A` numerical comparison; maximum
residual was `2.8422e-14 A`. This is a retrospective development-set split,
not an independent holdout. The bias may be a traced nominal term only and
must retain a nonzero uncertainty set.

The detailed report is:

```text
docs/codex/reports/STAGE4_2R3C3T13S2_QUANTIZED_OBSERVABILITY_REPORT.md
```

The active task is the prospectively frozen, offline Stage4.2R3c3T13S3
quantized causal tube interface:

```text
docs/codex/reports/
STAGE4_2R3C3T13S3_QUANTIZED_CAUSAL_TUBE_INTERFACE_DESIGN.md
```

T13S3 must implement exact Card15 serialization, the traced development bias
as a nominal term, at least one nonzero output-grid uncertainty unit on every
coil, unknown restart velocity, a causal numeric queue, forbidden-field
rejection, and a fail-closed multi-hypothesis/tube transition contract. It
runs no TSC and may end only as `INTERFACE_COMPLETE_HOLDOUT_REQUIRED` or
`INTERFACE_IMPLEMENTATION_FAIL`.

Do not claim point-model, observer, hidden-history, real-MPC, or robustness
validation from T13S3. A complete interface permits only a separately frozen
minimal lattice-aligned holdout. Formal timing and all RL prohibitions remain
unchanged.

## 25. Final T13S3 result and active T13S4 task

Stage4.2R3c3T13S3 implemented the frozen offline software interface at
commit `37e391361b7d397b90bd2f2747918084bf443e0a`. It contains:

```text
exact TSC-order Card15 serialization and clipping
T13S2R1 development nominal with exact report-hash provenance
at least one nonzero 1e-6 kA-turn uncertainty unit per coil
immutable causal restart state with unknown initial velocity
current-run numeric command and delay queue only
strict forbidden and unknown field rejection
multi-hypothesis affine prediction with propagated additive tube
measured/interpolation/extrapolation support reporting
point_model_certified = false
robust_controller_authorized = false
```

Validation completed as follows:

```text
local focused tests                           15/15
local isolated direct-copy tests              15/15
server isolated tests                         15/15
frozen predeployment package checksums       269/269
server installed complete tests              654/654, one skip
TSC/controller/Ray/gotsc/plant steps                0
```

The exact server validation log is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/
stage4_2r3c3t13s3_server_validation_37e3913.log
SHA-256 f70598458c08aee524298bb402789c7097b66203e50cc9332a2b5942ce15dfc5
```

T13S3 ends as `INTERFACE_COMPLETE_HOLDOUT_REQUIRED`. There was no runtime,
packaging, interface, statistics/reporting, raw, or snapshot error, but also
no plant model, real controller, restart, or robustness result. The detailed
report and compact audit are:

```text
docs/codex/reports/
STAGE4_2R3C3T13S3_QUANTIZED_CAUSAL_TUBE_INTERFACE_REPORT.md
docs/codex/audits/
stage4_2r3c3t13s3_interface_20260801_37e3913/
```

The active task is the separately frozen Stage4.2R3c3T13S4 design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S4_LATTICE_TRANSITION_HOLDOUT_DESIGN.md
```

T13S4 uses the `q2` p5/p9 matched pairs that were not used in the T13S1
probe or T13S2R1 bias fit. `plus_first` is fixed as development and
`minus_first` remains unopened by the model builder until the local model
and non-vacuous tube artifact is hashed. Its maximum matrix is 52 fresh
rollouts: four baselines plus 48 dynamic-lattice signed probes at transport
and braking time. The probe moves exact symmetric Card15 fields by at least
four local formatter steps on significant mode coils; it is not an
amplitude-only T13S1 rerun.

T13S4 may end only as
`LATTICE_HOLDOUT_PASS_LOCAL_MODEL_ONLY` or
`LATTICE_HOLDOUT_FAIL_REDESIGN`. A PASS authorizes only an offline robust
finite-horizon MPC prototype and a separately preregistered minimal real-MPC
sentinel. T13S4 raw remains forbidden from expert data. Formal timing is
unchanged and R3c4, real MPC, BC, DAgger, and bounded residual RL remain
blocked during T13S4.

## 26. Final T13S4 result and active T13S5 task

T13S4 completed its mandatory offline gate but did not enter its real TSC
campaign. The exact final identity is:

```text
commit/package
  21df2dc / r42r3c3t13s4_lattice_transition_holdout_v1h2
remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s4_runs/
  stage4_2r3c3t13s4_lattice_transition_holdout_20260801_21df2dc
route
  LATTICE_PREFLIGHT_FAIL_NO_REAL_TSC
```

Independent machine-readable audit:

```text
specifications                                      52/52
offline complete                                    11/52
issue design failures                               40/52
exact cancellation failures                          1/52
raw / plant advances / real TSC                       0/0/0
audit SHA-256
  1e60d04dfc7a9b5a26558aff9bee3cfd40ece0f1deed95988b592b0af8a8e6d2
```

The 40 issue failures have first-candidate incremental normalized action
`0.264604..0.403766`, above the unchanged `0.25` gate. Their direction
cosine, off-direction residual, total action, current bounds, and utilization
otherwise remain inside their frozen limits, although ten also cross a
Card15 exact-symmetry boundary. One p9 development transport mode-1 negative
probe passes issue but cannot express the exact negative displacement at the
next Card15 center.

Two preflight aggregation bugs originally stopped before writing the full
audit/state. Revisions v1h1/v1h2 repaired only failure aggregation and
terminal state reporting; every threshold, action selector, controller,
schedule, formal horizon, context, and physical semantic remained unchanged.
Each attempt had a new zero-raw directory. Installed validation passed
664/664 with one expected skip.

T13S4 is a prospective identification-design FAIL. It is not a runtime,
restart, corruption, plant-control, or real-MPC result, and its unrun 52-task
matrix must not be launched under the old identity.

The active task is the separately frozen Stage4.2R3c3T13S5 design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S5_LATTICE_NATIVE_SPLIT_HOLDOUT_DESIGN.md
```

T13S5 retains the same independent q2 development/blind split but uses four
lattice-native identification directions:

```text
physical mode 0 without coil index 8
the separately scaled physical-mode-0 coil-index-8 component
physical mode 1
physical mode 2
```

It uses causal return-first hybrid cancellation and 68 fresh trajectories:
four baselines plus 64 signed direction/window probes. The exact zero-TSC
actuator/input preflight passed 8/8 context-window groups with rank 4,
maximum condition `7.9547833`, maximum issue increment `0.1028397`, and
maximum selected cancel increment `0.1873576`. Audit SHA-256:

```text
378ff7d945a10b4d5c544460ed733cdbe0c25004d07b651af9f03a5c1f5a478b
```

This preflight is not plant/model/MPC evidence. Implement T13S5 completely,
validate and deploy it under a new identity, run exactly its authorized real
matrix only after a zero-plant offline gate, retain large raw on the server,
and independently analyze development before opening blind holdout raw.

Formal timing and tolerances remain immutable. T13S5 probes are forbidden
from expert data. R3c4, real MPC, BC, DAgger, and bounded residual RL remain
blocked until the T13S5 route authorizes the next offline MPC step.

## 27. Final T13S5 result and active T13S6 task

T13S5 completed exactly 68/68 authentic restart TSC trajectories under the
execution commit/package `d048686 / r42r3c3t13s5_lattice_native_split_holdout_v1`.
The two later reporting-only revisions were `8c8d087` and `70e9429`; they did
not change the controller, actuator, task matrix, thresholds, source
snapshots, or formal timing.

Exact immutable evidence:

```text
remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s5_runs/
  stage4_2r3c3t13s5_real_20260802_d048686

raw files / bytes                                      68 / 3,610,097
raw inventory digest
  09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
independent audit SHA-256
  dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033
final compact SHA-256
  674b1e58f100c496608fae8fa695d6ed95ea7740a2f092e3d98ca07ae0122375
route forensic SHA-256
  97999cd48cb73cb5fd25c14dea3cde1ba2579f7cb496828ac5b8c29deaf300cd
final route
  LATTICE_HOLDOUT_FAIL_REDESIGN
```

Independent recomputation found:

```text
execution / authentic restart                         68 / 68
runtime, solver, saturation, corruption failures              0
forbidden controller/model inputs                             0
target Card15 central symmetry                         32 / 32
observed current signal and symmetry                   16 / 32
correctly timed pre-effect causality                    16 / 32
development signal                                     16 / 16
development rank/condition                                2 / 4
development non-vacuous tube                              3 / 4
consumed validation containment                        26 / 32
consumed validation relative error <= 0.10               0 / 32
maximum validation scaled relative error              18.7134597
maximum current utilization                              0.3904
```

The first post-raw finalizer exposed two reporting/workflow defects. Python
`inf` from a genuinely rank-deficient cell was not strict JSON, and the
ordinary resume path would have opened holdout raw before rebuilding the
model. The strict-JSON bug was repaired, and the unsafe resume path was
intercepted before execution. A dedicated existing-raw finalizer preserved
the actual order: 34 development files, model SHA
`bc710049e4eb6075f0d4675c3fd70ea5cb186b40635b0fa2041483c8c798e862`,
then 34 holdout files. The final report has no remaining statistics or
reporting error.

Source and raw timing forensics establish a separate experiment-design
error. The T13S5 wrapper called the inherited R3c1 action first, after R3c1
had already applied its software delay queue, and then replaced the final
Card15 action. Probe current therefore first changed at `issue_step + 1`,
not `issue_step + delay + 1`. All delay-2 response declarations were two
states late. This explains their rank-zero/rank-one development cells but
does not explain the delay-zero independent-history failure: those response
states were already immediate, yet validation still passed relative error
0/16. T13S5 is therefore both an effect-state design failure and a genuine
finite cross-history single-static-map failure. It is not a runtime,
restart, corruption, real-MPC, or global-reachability result.

The active task is the prospectively frozen zero-new-TSC T13S6 audit:

```text
docs/codex/reports/
STAGE4_2R3C3T13S6_IMMEDIATE_EFFECT_REINTERPRETATION_DESIGN.md
```

T13S6 must authenticate all 68 immutable T13S5 raw files and recompute each
response at `issue_step + 1` and `cancel_step + 1`. It must preserve the 34
original development files, treat the other 34 as already-consumed
validation, retain every S5 threshold, serialize non-finite values as strict
JSON, and use no forbidden labels, source results, wire/vessel currents, or
future values as model inputs.

T13S6 may end only as:

```text
IMMEDIATE_EFFECT_MODEL_CANDIDATE_NEW_HISTORY_HOLDOUT_REQUIRED
IMMEDIATE_EFFECT_LOCAL_MAP_INSUFFICIENT_REDESIGN
```

It runs no controller, Ray, `gotsc`, TSC, plant step, or snapshot creation.
Neither route authorizes a controller, real MPC, expert data, BC, DAgger, or
bounded residual RL. T13S5 probes remain forbidden from expert data and the
formal timing contract remains unchanged.

## 28. Final T13S6 result and active T13S7 task

T13S6 completed its frozen zero-new-TSC reinterpretation at audit commit
`efc5b30`. It opened the immutable T13S5 development files before the
already-consumed validation files, changed only the retrospective response
states to `issue_step + 1` and `cancel_step + 1`, and retained every S5
threshold.

```text
main result SHA-256
  2f3f373fd1ff6c4080af18147783f8a0a009b6b490b4b4e773c4e106b8044375
independent raw-to-route audit SHA-256
  fc96514c1eb054c858fca8ee58085d4d7d78de470c3685c210e523e5021ebea4
raw files / bytes                                      68 / 3,610,097
raw inventory digest
  09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
route
  IMMEDIATE_EFFECT_LOCAL_MAP_INSUFFICIENT_REDESIGN
```

Exact recomputed gates:

```text
trace / target symmetry / causality / current signal     68/68, 32/32
development signal                                       16 / 16
development rank/condition                                  4 / 4
development non-vacuous tube                                4 / 4
maximum condition                                      7.9547833
maximum tube/cap ratio                                 0.2020750
consumed validation containment                          14 / 32
consumed validation relative error <= 0.10                2 / 32
maximum validation scaled relative error               1.0973948
forbidden model or trace inputs                                 0
```

The independent audit directly hashed and parsed every JSON.GZ, rebuilt
causal velocity and two-state measured-current/plant responses, refit every
map and tube, and reproduced every validation value and the route within
`1e-12`. Its first invocation stopped before output on a wrong forensic
payload-directory assumption. The run-level environment-variant layout was
then fixed under commit/staging `99d2b2d`; this was an independent-audit
layout bug, not an experiment, raw, or result error.

T13S6 confirms two distinct design findings. Correcting effect timing repairs
the hard-cell rank failure, but it does not repair cross-history transfer.
The result has zero runtime, deployment, raw, snapshot, restart, causality,
or final reporting errors. It ran no controller, Ray, `gotsc`, TSC, plant
step, snapshot, or real MPC.

The active task is the prospectively frozen T13S7 design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S7_CAUSAL_MULTI_HISTORY_TUBE_FEASIBILITY_DESIGN.md
```

T13S7 is a zero-new-TSC, leave-one-context-out feasibility audit over all 52
S1 q1 and 68 S5 q2 raw trajectories. It uses immediate post-queue effects
and only current/past R/Z/Ip, causal velocity/unknown flags, measured coil
current/history, target, formal time, and finite delay/slew as selector
features. It fits local response hypotheses only on each fold's three
training contexts, preserves the S6 tube caps and `0.10` relative-error gate,
and evaluates the held-out context without refit.

Pair/q/history/prefix/source identifiers, source action/result, wire/vessel
currents, and future values are forbidden from the feature, selector, model,
support check, and prediction. Labels may be used only after prediction to
audit the split.

T13S7 may end only as:

```text
FINITE_CAUSAL_MULTI_HYPOTHESIS_CANDIDATE_Q3_HOLDOUT_REQUIRED
CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN
```

The q1/q2 files are already consumed development evidence, so neither route
can authorize a controller. A pass requires a fresh prospective q3 history
holdout; a fail requires observer/state/tube redesign before another
physical campaign. Probe data remain forbidden from expert datasets and all
MPC/BC/DAgger/RL gates remain closed.

## 29. Final T13S7 result and active T13S7R1 task

T13S7 executed its frozen zero-new-TSC audit at implementation commit
`14ea327` and final route:

```text
CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN
```

Exact compact identities:

```text
main audit SHA-256
  b62d7d49f2ce2ac47fa1245884a764a84f5372364f8e7f5f329867b50e1c101c
compact forensic SHA-256
  8a67ed6c1306bb3fcacbae46764be37c24d35dd5cdd9d8f2ee398ac3ac68066c
campaign effect-contract forensic SHA-256
  c78bd97c5c60c526d609ea5da15547abe5cb73927552086573f4a856d12e3f4a
```

The frozen output authenticated S1 52/52 and S5 68/68 raw files, 120/120
traces, 112/112 extracted signed probes, 112/112 pre-effect causality, 16/16
tubes, and zero forbidden inputs. Local rank passed only 12/16. Only 24/112
held-out rows had a supported hypothesis; the other 88 failed closed before
prediction. The reported maximum finite error `0.0` covers only those 24
supported rows and is not a complete accuracy result.

All 24 apparent passes were S1 hard/delay-2 zero-input/zero-output rows at the
wrong effect states. All four S1 hard maps were rank zero. Every S1 easy row,
S5 easy row, and S5 hard row was unsupported.

Source and raw timing forensics establish the cause:

```text
S1 probe insertion                  before inherited software delay queue
S1 physical effect state            issue + action_delay + 1
S1 campaign-contract match                                  24 / 24
S1 delay-2 immediate issue+1 match                            0 / 12

S5 probe insertion                  after inherited software delay queue
S5 physical effect state            issue + 1
S5 immediate match                                          32 / 32
S5 delay-2 immediate match                                  16 / 16
```

T13S7 is final under its frozen design and may not be rewritten. Its primary
classification is a cross-campaign effect-contract audit-design failure, not
a runtime, raw, restart, reporting, real-MPC, or valid multi-hypothesis
scientific failure.

The active task is the separately frozen T13S7R1 design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S7R1_CAMPAIGN_SPECIFIC_EFFECT_CONTRACT_DESIGN.md
```

T13S7R1 changes only S1 response extraction to its authenticated
`issue+delay+1` states; S5 remains `issue+1`. The exact T13S7 causal feature,
fixed scales, four-fold-per-stratum LOCO split, two-neighbor selection,
0.15 input row-space support, local-map/tube rules, component caps, 0.10
relative-error gate, collision audit, formal timing, and all forbidden-input
rules remain unchanged.

T13S7R1 may end only as:

```text
CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_CANDIDATE_Q3_HOLDOUT_REQUIRED
CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN
```

Both source campaigns are consumed development evidence. A pass still only
permits a new prospective q3 holdout; a fail requires unified excitation,
observer, or transition-tube redesign. No controller, MPC, expert data, BC,
DAgger, or RL is authorized.

## 30. Final T13S7R1 result and active T13S8 task

T13S7R1 completed at reporting revision `9e400e1` without any new TSC or
plant execution. Its exact final route is:

```text
CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN
```

Compact identities:

```text
main audit SHA-256
  9fb7c8ce1efc03a66d69b8b8c848bff9509196cfc2e7b583f98eb547dd829c80
support forensic SHA-256
  6683df634729fee74294971f1e945bec0eddd7532bb06b650044da937f88c799
```

The final audit authenticated 52 S1 and 68 S5 raw files, 56/56 campaign
effect groups, 120/120 traces, 112/112 signed responses, and 112/112
pre-effect causality. Correct timing restored local rank and tube to 16/16,
with maximum tube/cap ratio `0.202075`. The frozen feature selector found
supported hypotheses for 0/112 held-out rows, so containment and relative
error were not run and the finite maximum is correctly JSON `null`.

The initial `0a4b39a` invocation exposed a summary-only `max(empty)` bug and
wrote no result JSON. The `9e400e1` hotfix changed only empty-set reporting,
added a regression test, and used `pipefail`; it did not alter scientific
semantics or any gate.

Post-result support forensics preserved the `0.15` threshold. Across all 336
held-input/training-map comparisons, only 16 passed; they were the S5 hard
transport pair and none was selected by the frozen visible feature rule.
Cross-campaign support was 0/112, the minimum selected residual was
`0.202537`, and the median all-training minimum residual was `0.790417`.
This establishes an excitation/input-coordinate design failure, not a
response-error measurement on the unsupported rows.

The active task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S8_FIRST_EFFECT_TRANSITION_DESIGN.md
```

T13S8 is a zero-new-TSC leave-one-context-out audit using only each probe's
campaign-authenticated first physical effect. Its input is the measured
14-coil current difference at that state and its output is the causal
single-state R/Z/vR/vZ/Ip response. It excludes the incompatible adjacent
cancellation transition, considers all three same-stratum training maps as
a label-free robust hypothesis bank, and preserves the `0.15` support,
component tube caps, `0.10` relative error, causality, collision, and all
forbidden-input gates.

T13S8 may end only as:

```text
FIRST_EFFECT_CAUSAL_TRANSITION_CANDIDATE_Q3_HOLDOUT_REQUIRED
FIRST_EFFECT_CAUSAL_TRANSITION_INSUFFICIENT_REDESIGN
```

A pass only authorizes a fresh prospective q3 history holdout. A failure
routes to active calibration/persistent observer or a new unified post-queue
excitation design. It authorizes no controller, MPC, expert data, BC,
DAgger, or RL.

## 31. Final T13S8 result and active T13S9 task

T13S8 completed at implementation `77b3c59` with zero new TSC. Its final
route is `FIRST_EFFECT_CAUSAL_TRANSITION_INSUFFICIENT_REDESIGN`.

```text
audit SHA-256
  c842fe8632bff9bbcd49d44d5a7ee9a8bf89b817c79b33177952ff677bd2ba3b
log SHA-256
  566a54347d5bfb759cad39569e1540486c854b5a8521b6757c4559b3f2ce6b88
raw / trace / extraction / causality       120/120, 112/112, 112/112
local rank / tube                                      16/16, 16/16
held input support                                         64/112
componentwise containment                                  29/112
relative error <= 0.10                                     39/112
maximum finite relative error                             1.530032
```

All 48 S1 rows were unsupported. All 64 S5 rows were supported, but their
cross-history containment/error gates failed. The first-effect redesign
therefore removed one cancellation confounder but also separated a genuine
pre-/post-queue excitation mismatch from a remaining supported S5 model
failure. There were no runtime, deployment, raw, restart, causality,
statistics, or reporting errors and no controller/MPC execution.

The active task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S9_UNIFIED_POSTQUEUE_Q1_DESIGN.md
```

T13S9 is a new 68-trajectory authentic identification campaign. It reuses
only the four exact q1 snapshots and applies the exact S5 lattice-native
post-queue action/cancellation semantics. Delay-2 effects are correctly
declared immediate at states 1/2 and 15/16; delay-0 remains states 3/4 and
17/18. A complete campaign authorizes only a separately frozen combined
q1/q2 first-effect audit. It does not authorize a controller, MPC, q3,
expert data, BC, DAgger, or RL.

## 32. Final T13S9 result and active T13S10 task

T13S9 completed its frozen authentic campaign at executed package checkpoint
`2f5138a`. Its exact final route is:

```text
UNIFIED_POSTQUEUE_Q1_IDENTIFICATION_COMPLETE_COMBINE_Q2_REQUIRED
```

Exact evidence identities:

```text
raw JSON.GZ files / bytes                            68 / 3,610,295
raw inventory digest
  9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
server audit SHA-256
  df4d7982f98a6216997d89ac5adea9ca2e3b2bf367451c3412d5458ccc5c60e0
run inventory files / bytes                         295 / 8,469,039
run inventory digest
  e4dbef249beeba52de433f1112cf894d6d930daf1856dd4b66143f188a6be8b2
```

Independent server postprocessing recomputed all 68 raw results and the
reported summary exactly. Authentic execution, restart, controller
causality, target-current symmetry, observed-current symmetry, and
pre-effect causality all passed. Card15 and current interval checks passed
34,272/34,272. All four development maps passed rank/condition and
non-vacuous tubes; maximum condition was `7.9547833`, maximum tube/cap ratio
`0.1471975`, and maximum current utilization `0.3904`.

The consumed internal q1 diagnostic passed componentwise containment only
15/32 and scaled relative error only 20/32, with maximum finite error
`1.7167681`. This is a cross-history diagnostic model failure, not a runtime,
restart, raw-corruption, statistics, or reporting error. T13S9 ran no
controller or MPC and makes no real control claim.

Two pre-execution workflow defects were repaired before real TSC: missing
empty-package import closure and Windows-transfer executable-bit loss. The
failed shell attempt created no run, raw, snapshot, Ray, `gotsc`, or plant
advance. Neither repair changed experiment semantics.

The active task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S10_COMBINED_POSTQUEUE_FIRST_EFFECT_DESIGN.md
```

T13S10 is a zero-new-TSC read-only audit over all 68 T13S5 q2 and 68 T13S9
q1 raw trajectories. Both campaigns use the same post-queue Card15 action,
so every signed probe is extracted only at `issue_step + 1`:

```text
x = measured 14-coil current difference
y = causal single-state R/Z/vR/vZ/Ip difference
```

It freezes eight contexts, two windows, 16 local maps, eight
leave-one-context-out folds, and 128 signed held rows. All three
same-stratum training maps remain as a label-free hypothesis bank. Required
exact gates include 16/16 rank/condition/tube, 128/128 support,
componentwise containment, and relative error `<=0.10`, with unchanged
support `<=0.15`, tube caps, causality, collision, and forbidden-input rules.

T13S10 may end only as:

```text
UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_CANDIDATE_Q3_HOLDOUT_REQUIRED
UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_INSUFFICIENT_OBSERVER_REDESIGN
```

A pass authorizes only prospective design of a fresh q3 identification
holdout. A failure stops this static bank and requires persistent
state/observer, active calibration, or nonlinear state-conditioned tube
redesign. Neither route authorizes a controller, MPC, expert data, BC,
DAgger, or bounded residual RL.

## 33. Final T13S10 result and active T13S11 task

T13S10 completed at executed audit package checkpoint `723c6bf` with zero
new TSC. Its exact final route is:

```text
UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_INSUFFICIENT_OBSERVER_REDESIGN
```

The audit authenticated 68 T13S5 q2 and 68 T13S9 q1 raw files against their
independent source audits. All 136 trace identities, 64 post-queue effect
contracts, 128 signed first-effect extractions, and 128 pre-effect causality
checks passed. All 16 local models passed signal, rank/condition, and
non-vacuous tube gates. Every held row had all three same-stratum hypotheses
inside the frozen input-support gate.

The response result nevertheless failed:

```text
componentwise containment                              107 / 128
scaled relative error <= 0.10                          110 / 128
both frozen response gates                              92 / 128
maximum finite scaled relative error                  0.9307636
```

Both campaigns, strata, and windows contain failures. The nearest
visible-feature map passed both gates only 64/128, and even an oracle single
hypothesis passed both only 72/128. This is a static causal transition-model
design failure. There were no runtime, deployment, raw, restart, causality,
statistics, or reporting errors, and no controller, optimizer, plant step,
Ray, `gotsc`, or TSC ran.

Exact compact audit SHA-256:

```text
f24768f7b4899c73f68fd0a4e3991f524239951883abf3d2809461b5ab82509b
```

The active task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S11_CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_DESIGN.md
```

T13S11 uses the consumed q1/q2 raw only. In each context, one positive
`mode0_coil8_component` transport transition supplies an eight-dimensional
absolute same-trajectory causal signature. Eight LOCO folds compute a
training-only rank-2 calibration state basis, a rank-4 braking-current basis,
and a 12-column state/current interaction model. It tests 64 later braking
first-effect rows. Support is tested non-vacuously and separately for the
held eight-dimensional calibration signature against the training rank-2
affine subspace and for the held 14-coil braking current against the training
rank-4 subspace; applying support to the full-rank 12-column interaction
coordinate is forbidden. Both retain `0.15`, with unchanged error `0.10`,
response scales, tube multiplier, component caps, causality, collision, and
forbidden-input rules.

T13S11 may end only as:

```text
CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_CANDIDATE_DUAL_WINDOW_TSC_REQUIRED
CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_INSUFFICIENT_PERSISTENT_OBSERVER_REDESIGN
```

A pass authorizes only a new authentic campaign in which calibration and
braking execute on the same physical trajectory. A failure requires a
longer observation sequence, multiple safe calibrations, or a persistent
nonlinear observer. Neither route authorizes a controller, MPC, expert data,
BC, DAgger, or bounded residual RL.

## 34. Final T13S11 result and active T13S12 task

T13S11 completed with zero new TSC. The final executed audit implementation
is `c8ca408`, and the exact final route is:

```text
CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_INSUFFICIENT_PERSISTENT_OBSERVER_REDESIGN
```

The preliminary `75c2751` result exposed a numerical affine-rank reporting
bug: mean-cancellation residue made three training points appear rank three.
The `c8ca408` hotfix computes the equivalent affine rank from two training
differences. It changed the reported rank gate from 4/8 to 8/8 and changed no
feature, basis, fit, tube, support, prediction, threshold, or route.

Final result:

```text
source raw / trace identity                              136 / 136
causal calibration / calibration causality                    8 / 8
signed braking extraction / causality                       64 / 64
calibration affine and current basis rank                     8 / 8
held state and current support                         8 / 8, 64 / 64
interaction rank 12                                           8 / 8
interaction condition <= 30                                   0 / 8
finite condition range                           23,065.6 -- 91,958.0
non-vacuous tube                                               8 / 8
containment / relative error                         56 / 64, 44 / 64
both response gates ignoring condition                       36 / 64
formal passed rows                                            0 / 64
```

Final compact audit SHA-256:

```text
6e595fbd4e86276d449fc953edcb06b676bd282b6f0bd68d4e5ac3effe97ffbe
```

This is an observer/model design failure, not a runtime, raw, restart,
causality, final-reporting, controller, or real-MPC failure. T13S11 ran no
Ray, `gotsc`, TSC, controller, optimizer, plant step, snapshot, or new raw.

The active task is frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S12_CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_DESIGN.md
```

T13S12 uses the full deployable baseline visible sequence through the
braking issue: target errors, backward-causal R/Z velocity, and measured
14-coil currents/current differences. Eight LOCO folds build a training-only
rank-2 history basis and rank-4 braking-current basis, whiten both coordinate
sets, and fit the same zero-at-zero-current 12-column interaction model.
Support remains separately non-vacuous in the original history and current
spaces at `0.15`; response error remains `0.10` with unchanged tube rules.

T13S12 may end only as:

```text
CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_CANDIDATE_Q3_SEQUENCE_TSC_REQUIRED
CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_INSUFFICIENT_NONLINEAR_OBSERVER_REDESIGN
```

A pass authorizes only a new q3 same-trajectory observation/probe campaign.
A failure stops the affine observer and requires a broader prospective
history campaign plus recurrent/nonlinear observer. Neither route authorizes
a controller, MPC, expert data, BC, DAgger, or bounded residual RL.

## 35. Final T13S12 result and active T13S13 design task

T13S12 completed its frozen zero-new-TSC audit after a semantics-preserving
target-schema hotfix at commit `d2940b3`. The first implementation had
incorrectly required the payload base target to include the raw task offsets;
the authenticated controller contract is base target plus specification
offset. The failed invocation wrote only a log. A later direct-file
invocation also stopped before import because the project root was absent
from `sys.path`; it likewise wrote no result. The unchanged module invocation
completed under a new output identity.

Exact final output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s12_audits/
stage4_2r3c3t13s12_causal_natural_history_observer_20260802_d2940b3m1
```

Final gates:

```text
source raw and trace identity                           136 / 136
causal history schema                                      8 / 8
braking extraction and pre-effect causality               64 / 64
history rank / whitening / current rank                     8 / 8
interaction rank / condition / signal                       8 / 8
maximum interaction condition                  1.000000000000045
tube / history support / current support            8/8, 8/8, 64/64
componentwise containment                                  61 / 64
scaled relative error <= 0.10                              44 / 64
both response gates                                        41 / 64
maximum scaled relative error                        1.701539079
forbidden inputs / disjoint exact aliases                       0 / 0
```

The final route is:

```text
CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_INSUFFICIENT_NONLINEAR_OBSERVER_REDESIGN
```

Final audit SHA-256 is
`1ccaaea1f8da5b5271331758a0a390c5dc663f98c5099299ff3a440007b94b4a`.
All 136 large raw files remain on the server. There is no final runtime,
deployment, raw, restart, causality, statistics, or reporting error and no
controller, optimizer, Ray, `gotsc`, TSC, plant step, or snapshot creation.
The failure is a finite affine observer/model design failure.

The active task is Stage4.2R3c3T13S13, prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S13_RECURRENT_SEQUENCE_TUBE_IDENTIFICATION_DESIGN.md
```

It covers all 36 R3b source pairs and all 72 authentic restart histories.
Whole pairs are split into 32 training, 20 calibration, and 20 fresh holdout
contexts. Eight consumed q1/q2 contexts contribute 136 training raw; the
remaining 64 contexts require 1,088 new trajectories. New execution is
strictly gated as training baseline/probe, calibration baseline/probe, then
fresh-holdout baseline/probe. Later-phase raw may not be created or opened
early, and a failed context may not be dropped.

The recurrent observer uses only current-run causal visible measurements and
previously issued commands. Its action coordinate is the pre-action Card15
nominal readback displacement plus an uncertainty box. Post-effect measured
current is outcome evidence and is forbidden from the fit input. The center
model is selected using training whole-pair CV; calibration may only freeze
the tube; the 20-context holdout is never refit.

The immediate work is a complete independent S13 implementation and zero-TSC
source/split/snapshot/safety preflight. Real TSC is allowed only after local,
empty-package, staging, and installed validations pass. The 250/270 ms
arrival and 350/370 ms hold contract remains immutable. No controller, MPC,
expert data, BC, DAgger, or bounded residual RL is authorized.

## 36. Final T13S13 result and active T13S14 task

T13S13 completed its training execution but stopped prospectively before
calibration and holdout. Its exact final route is:

```text
RECURRENT_CAUSAL_SEQUENCE_TUBE_INSUFFICIENT_REDESIGN
```

The server run is
`stage4_2r3c3t13s13_recurrent_sequence_tube_identification_20260802_c6c81fd`.
It completed 24/24 new training baselines and 384/384 new signed probes, and
authenticated all 136 consumed q1/q2 training raw. Independent server
postprocessing parsed 408/408 new raw with no runtime, restart, causality,
actuator, corruption, or environment error. Calibration and fresh holdout
each remain zero raw.

Two analysis-only defects were repaired without rerunning any raw. The first
rebuilt private R3b coil/wire state from authenticated state-generation raw
for the inherited restart audit. The second interpreted exactly 32 legacy
T13S5 q2 delay-2 declarations at their already authenticated post-queue
physical effect `issue+1`, as frozen in the T13S13 design. The final reporting
checkpoint is `f220714`; config, controller, action/spec semantics, formal
timing, and all 408 raw remained unchanged.

All 256 central identification groups, 512 pre-effect/input-box rows, history
and action support, and provisional componentwise tubes passed. All 54 frozen
ESN candidates were finite. The selected training-only whole-pair CV maximum
and mean center errors were `0.991216` and `0.166437`; full-training center
error passed only 301/512. The 211 failures are genuine causal response-center
model failures. No model/tube, controller, MPC, or control claim was produced.

Exact final evidence and hashes are recorded in:

```text
docs/codex/reports/STAGE4_2R3C3T13S13_FORENSIC_REPORT.md
```

The active task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S14_ACTIVE_CALIBRATION_SENTINEL_DESIGN.md
```

T13S14 uses 16 contexts from eight whole factor-selected pairs and 144 new
real trajectories. Every rollout executes the same four fixed, causal,
zero-net post-queue calibration pulses before a response probe at task step
10. It asks whether same-trajectory active excitation makes hidden history
causally observable enough for whole-pair response prediction. A pass permits
only a separately frozen full train/calibration/fresh-holdout campaign. No
controller, MPC, expert data, BC, DAgger, or bounded residual RL is authorized.

## 37. Final T13S14 result and active T13S15 task

T13S14 completed 16/16 calibrated baselines and 128/128 signed response
trajectories. All 144 raw parsed and passed runtime, exact restart, causality,
Card15, zero-net, current, and corruption checks. Four narrowly audited code
or reporting corrections preserved the experiment identity; the final two
reran zero raw and added zero plant advances. Independent recomputation
matched the final report exactly.

Its exact route is:

```text
ACTIVE_CALIBRATION_SENTINEL_FAIL_REDESIGN
```

All identification/interface gates passed, but no point response model did.
The best ESN passed only 36/128 center rows with maximum scaled error 1.18137.
All 12 frozen kernels failed their condition gate. Failed-data diagnostics
also rejected wider-ridge kernels, direct raw-history PCA, nearest-history
prediction, simple multi-hypothesis boxes, and uniformly enlarged residual
tubes. The failure is a genuine finite observer/experimental-design failure,
not a runtime, restart, reporting, or plant-control conclusion.

The decisive forensic finding is that S14 replanned every signed calibration
action around a changing underlying-controller Card15 center. Within each
trajectory, the eight calibration deviations therefore span rank eight, not
a frozen four-dimensional local input experiment. Eight visible transitions
cannot identify those input changes plus natural drift.

The complete result is frozen in:

```text
docs/codex/reports/STAGE4_2R3C3T13S14_FORENSIC_REPORT.md
```

The active task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S15_FIXED_BASIS_LOCAL_IDENTIFICATION_DESIGN.md
```

T13S15 freezes four exact physical field increments at task step zero, applies
explicit adjacent plus/minus pairs relative to each contemporaneous baseline
center, and fits a rank-seven constant/linear/quadratic-drift plus fixed-input
model from states 1--8. It keeps the same eight calibration steps, response
time, horizons, current limits, and immutable formal timing. It is a
development sentinel; no MPC, expert data, BC, DAgger, or RL is authorized.

## 38. Final T13S15 result and active T13S16 task

T13S15 submitted all 16 baseline task functions but stopped before the first
plant step in each task. All 16 structured raw files have empty trajectory
and controller trace. Source-exact server recomputation proved:

```text
physical field-basis rank four                           16 / 16
condition <= preregistered 3.0                            0 / 16
condition range                            4.1405793 -- 4.1409175
plant advances / successful trajectories                   0 / 0
response raw opened                                            0
```

The exact route is:

```text
FIXED_BASIS_LOCAL_IDENTIFICATION_FAIL_REDESIGN
```

This is a pre-action excitation-geometry design failure, not a TSC runtime,
restart, raw-corruption, reporting, statistics, or closed-loop control
failure. S15's condition threshold remains unchanged and S15 may not resume
as a successful identity.

The complete report is:

```text
docs/codex/reports/STAGE4_2R3C3T13S15_FORENSIC_REPORT.md
```

The active task is prospectively frozen as Stage4.2R3c3T13S16:

```text
docs/codex/reports/
STAGE4_2R3C3T13S16_ORTHOGONAL_FIXED_BASIS_DESIGN.md
```

S16 uses a deterministic causal QR field basis spanning the same four native
directions, with fixed relative amplitude factors `(1,1,1,0.6)`. A zero-TSC
development preflight passed rank, exact positive/negative action, unchanged
action/current limits, and native-response projection in 16/16 contexts; its
maximum normalized condition was `1.0245903`. This authorizes only independent
S16 implementation and its baseline-gated 144-trajectory development
sentinel. No controller, MPC, expert data, BC, DAgger, or bounded residual RL
is authorized.
