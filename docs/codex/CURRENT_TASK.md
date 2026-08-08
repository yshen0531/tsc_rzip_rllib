# CURRENT_TASK.md — finite-horizon restart MPC architecture evidence stage

## 0. User-authorized final objective and learning-transition policy

The user clarified and authorized this interpretation on 2026-08-06.  The
practical final objective is:

```text
For a limiter-configuration plasma, obtain safe, causal feedback that makes
the plasma follow a user-commanded trajectory approximately.  High-precision,
zero-error, globally optimal, or universally perfect tracking is not required.
```

This policy supersedes any earlier wording that could be read as requiring
MPC to solve every robustness case perfectly before learning.  It does not
change any completed result, reopen any consumed holdout, weaken any
preregistered gate after seeing its result, or alter the immutable formal
timing contract.

### 0.1 Hard MPC qualifications before learning

Before expert-data, BC, DAgger, or bounded residual learning, the MPC base
must demonstrate within a prospectively stated finite envelope:

1. exact authentic plant restart and causal controller-state restart;
2. no future, hidden-label, source-outcome, or forbidden-state leakage;
3. enforced hard action/current/Card15/saturation constraints, reliable
   solver fallback, and safe behavior when the residual is identically zero;
4. deterministic core acceptance under the unchanged 30 mm R/Z, 0.1 m/s,
   frozen Ip/arrival-streak, 250/270 ms arrival, and 350/370 ms hold contract;
5. a deployable observer/controller mechanism that does not fail
   catastrophically on the frozen hidden-history and different-initial-state
   qualification;
6. bounded, non-divergent, hard-safe behavior on prospectively frozen
   continuous delay/gain/slew, plant/model mismatch, measurement-noise,
   disturbance-recovery, and independent long-hold qualifications; and
7. an explicit residual-authority audit showing that remaining performance
   errors are local and potentially repairable by the restricted residual
   interface without giving RL unconstrained control of all 14 coils.

Exact safety, causality, restart, integrity, and deterministic core formal
gates are not relaxable.  The future stochastic/continuous robustness
qualifications need not demand universal 100% performance success: their
finite envelope, sample matrix, aggregate success/confidence criterion, and
zero-hard-safety-violation rule must be frozen before outcomes are seen.  An
individual formal miss must still be recorded as a miss; it may not be
relabeled as a pass.

Independent long hold means the formal arrival/hold gate is satisfied first,
followed by bounded, safe, non-divergent behavior over a separately chosen
horizon.  It does not require zero steady-state error or perfect tracking for
an unlimited duration.

### 0.2 Performance gaps that may remain for bounded residual learning

After the hard qualifications pass, MPC may retain modest systematic model
error, continuous-parameter tracking loss, noise-related estimation error,
disturbance-recovery delay, overshoot, energy/smoothness cost, or occasional
held-envelope performance misses.  Such a gap is eligible for residual
learning only if all of the following are shown prospectively:

```text
the base MPC moves in the correct direction and remains in a safe basin
the residual-zero closed loop remains stable and safe
the error is finite, local, measurable, and not an unresolved causal alias
a fixed bounded residual action/subspace has plausible repair authority
the residual cannot bypass hard constraints or become the 14-coil controller
```

A fundamentally wrong-direction action, unstable base loop, failed restart,
unobservable state with no deployable causal estimator, or need for large
full-authority correction is still an MPC/observer blocker rather than an RL
task.

### 0.3 Two explicit pause gates

```text
Gate A — safe-and-useful MPC expert qualified
  Pause for user confirmation before creating the expert dataset or entering
  BC/DAgger.  "Qualified" means every required robustness axis has been
  implemented and independently tested to the finite criteria above, not that
  MPC is universally perfect.

Gate B — imitation baseline and residual interface ready
  After a confirmed expert-data -> BC -> DAgger phase, independently verify
  baseline fidelity, safety projection, residual bounds, fallback, and useful
  residual headroom; then pause again before bounded residual RL.
```

If the qualified MPC already satisfies the user's coarse trajectory-following
goal and RL has no measurable benefit commensurate with its added risk and
complexity, it is valid to finish without residual RL.

This policy does not authorize learning now.  The current R8/R8R1 response-
model boundary must still be completed honestly under its already frozen
gates, followed by a genuine receding-horizon controller and the finite
qualification sequence above.

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

## 39. Final T13S16 result and active T13S17 task

T13S16 completed its complete 144-trajectory authentic development campaign
at implementation checkpoint `8487951`.  Exact restart, causality, Card15,
zero-net, current, raw parsing, and independent reporting recomputation passed
144/144.  The raw inventory is 144 JSON.GZ files, 8,188,964 bytes, digest:

```text
b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668
```

The QR basis repaired S15's excitation geometry.  Its maximum normalized
condition was `1.0245902744`, all 128 response projections passed, and the
rank-seven point estimate passed center error in 120/128 rows.  The frozen
provisional tube nevertheless passed containment only 82/128, cap only
40/128, and all model gates jointly only 14/128.  Velocity tubes exceeded
their unchanged caps in 48 vR and 88 vZ rows, while other finite response
components still escaped the box.

The exact final route is:

```text
ORTHOGONAL_FIXED_BASIS_IDENTIFICATION_FAIL_BELIEF_MPC_REDESIGN
```

There is no runtime, deployment, restart, causality, raw, statistics, or
reporting error.  This is a local response/tube design failure and no MPC or
closed-loop controller was run.  The complete report is:

```text
docs/codex/reports/STAGE4_2R3C3T13S16_FORENSIC_REPORT.md
```

The active zero-new-TSC task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S17_CAUSAL_MULTI_DRIFT_BELIEF_PREFLIGHT_DESIGN.md
```

T13S17 uses the current-run visible states 1--10, including both causal
settling states before response issue, and always retains three fixed
Legendre drift hypotheses of degrees one through three.  It propagates each
hypothesis's observed calibration residual through its exact prediction
leverage, adds the unchanged Card15 input uncertainty, and forms a
componentwise belief hull.  State 11 response outcomes cannot be opened until
all causal belief artifacts are hashed.

S17 consumes only S16 development raw and runs zero new TSC.  A pass requires
128/128 coverage inside the unchanged component caps and authorizes only a
new whole-pair training/calibration/fresh-context identification campaign.  A
failure requires robust-observer redesign.  Neither route authorizes MPC,
expert data, BC, DAgger, or bounded residual RL.

## 40. Final T13S17 result and active T13S18 task

T13S17 completed its zero-new-TSC server audit at implementation checkpoint
`65e00c3`, with the package-verification-only hotfix `0f9ef6b`.  It
authenticated all 144 S16 source raw files, 16 source snapshots, and 12
required compact source artifacts.  The source raw inventory digest remains:

```text
b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668
```

All 384 fixed degree-one through degree-three hypothesis rows were causal and
finite, the maximum design condition was `3.1980986512`, and every state-11
response was inside the belief hull.  The unchanged halfwidth caps passed
only:

```text
all components per row                               0 / 128
component counts R/Z/vR/vZ/Ip             128/124/0/16/128
maximum halfwidth
  0.0021893899 m / 0.0035035150 m /
  0.1402725944 m/s / 0.1148451016 m/s / 569.3096777 A
```

Independent server recomputation reproduced the 128/128 containment and
0/128 cap result exactly.  S17 created zero raw, snapshots, TSC calls, or
plant steps.  Its exact route is:

```text
CAUSAL_MULTI_DRIFT_BELIEF_PREFLIGHT_FAIL_ROBUST_OBSERVER_REDESIGN
```

The per-trajectory regression residual, not Card15 uncertainty or
hypothesis-center disagreement, dominates the failed tube.  This is a
robust-observer residual-set design failure, not a runtime, restart, raw,
reporting, real-MPC, or plant-reachability failure.  The full report is:

```text
docs/codex/reports/STAGE4_2R3C3T13S17_FORENSIC_REPORT.md
```

A post-failure retrospective whole-pair screen, explicitly not validation,
found that a nine-feature pooled predictor using only the causal degree-three
point response and numeric issued-action coordinate had a required maximum
tube expansion of `1.30124665`; a fixed 4x inner-OOF residual tube covered
128/128 development rows while remaining well inside every unchanged cap.

The active zero-new-TSC task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S18_POOLED_CAUSAL_OBSERVER_PREFLIGHT_DESIGN.md
```

T13S18 must enforce eight outer whole-pair folds, train-only scaling and
ridge selection, per-fold model/tube hashing before held outcomes open,
same-trajectory action-coordinate reconstruction, and exact propagation of
current-run Card15 feature uncertainty.  A pass can authorize only a new,
separately preregistered training/calibration/fresh-context campaign.  No
controller, MPC, expert data, BC, DAgger, or bounded residual RL is
authorized.

## 41. Final T13S18 result and active T13S19 task

T13S18 completed its zero-new-TSC server audit with the fold artifact frozen
under `fba9144` and the semantics-neutral batch-evaluation correction
`960ac1e`.  It authenticated all 144 S16 source raw files and evaluated 128
responses in eight exact whole-pair folds.  Frozen prediction, fold hash, and
independent recomputation checks were exact.

```text
containment / cap / joint                       128 / 128 / 128
maximum scaled point error                         0.0010531744
held outcome access before fold hash                          0
forbidden predictor inputs                                    0
new raw / snapshots / TSC / plant steps             0 / 0 / 0 / 0
```

The final route is
`POOLED_CAUSAL_OBSERVER_PREFLIGHT_PASS_FRESH_CAMPAIGN_REQUIRED`.  The result is
a consumed-development architecture pass, not independent observer or MPC
validation.  Two prepare/evaluate implementation defects were repaired without
changing model, outcome, split, tube, or gate semantics; the final report is:

```text
docs/codex/reports/STAGE4_2R3C3T13S18_FORENSIC_REPORT.md
```

The active task is the prospectively frozen 360-rollout T13S19 campaign in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S19_PROSPECTIVE_POOLED_OBSERVER_CAMPAIGN_DESIGN.md
```

A server-side freshness audit parsed 900 earlier T13 identification raw files
and found zero responses for all 20 selected whole pairs.  S19 must keep the
fixed 12/4/4 training/calibration/holdout split, freeze the pooled model before
calibration, freeze the calibrated tube before holdout, and stop at the first
failed boundary.  Even a complete pass authorizes only offline robust-
transport MPC feasibility work.  Expert data, BC, DAgger, and bounded residual
RL remain prohibited.

## 42. Final T13S19 result and active T13S20 task

T13S19 authenticated all sources and began its prospective campaign at
implementation checkpoint `14f3646`. Its training-baseline phase produced 24
structured raw files: 23 complete successes and one deterministic controller
exception. The raw inventory digest is:

```text
3a2a468a92ea656b240280125ebac9b4e947d14bc3beb8e61a0fcdd82d1e01da
```

Independent raw audit found exact restart, causality, actuator execution,
calibration schedule, zero net, and pre-response semantics in all 23 complete
baselines. A separate authentic two-step TSC reproduction proved the failed
path crossed a Card15 exponent boundary: the frozen `-0.016` kAt increment at
center `-9.904E-01` requested unrepresentable `-1.0064`, while Card15 could
encode only `-1.006E+00` at that precision. This is an excitation-design
defect surfaced by a controller guard, plus a partial-failure reporting defect;
it is not a TSC, restart, causality, raw, observer, MPC, control, or plant
failure. Training probes, calibration, and holdout were not run.

S19 is frozen and may not resume under changed action semantics. Its report is:

```text
docs/codex/reports/STAGE4_2R3C3T13S19_FORENSIC_REPORT.md
```

A zero-new-TSC development replay of 187 causal events found that retaining
the frozen QR directions while recomputing the nearest exact displacement at
each current Card15 center passed 187/187 action gates. Complete baseline
sequences were exact zero net 23/23; all causal designs retained rank eight,
with maximum condition `3.1980986512`. The exponent-boundary event was repaired
to actual increment `-0.0156` kAt and input coordinate `0.975`.

The active task is the separately frozen T13S20 campaign in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S20_DYNAMIC_EXACT_CARD15_CAMPAIGN_DESIGN.md
```

S20 keeps the unchanged 12/4/4 whole-pair split but reruns all 360 trajectories
under a new controller and campaign identity. It uses actual same-trajectory
dynamic input coordinates, requires coordinate magnitude `[0.85,1.15]`, cross
coordinate at most `0.15`, cosine at least `0.98`, off-basis residual at most
`0.15`, causal design condition at most `4.0`, and exact calibration net zero.
The model must be hashed before calibration and the tube before holdout.

Even a complete S20 pass authorizes only robust-transport MPC feasibility.
Probe raw remains forbidden from expert data; BC, DAgger, and bounded residual
RL remain prohibited.

The first S20 package (`1861dbd`) stopped during zero-plant offline
authentication with zero raw and zero TSC because its config carried the
legacy recorded S19 inventory token `dc31ee...` rather than the digest produced
by S19's frozen `_raw_inventory`. Server recomputation over the unchanged 24
files reproduced 24 files, 1,300,417 bytes, and canonical digest
`3a2a468a...1e01da`; all other source hashes and semantic counts were exact.
This is a package/statistics reference bug only. The action semantics, split,
gates, controller revision, and campaign identity remain unchanged. The failed
offline run is preserved and cannot be resumed; package v2 must use a new empty
run directory.

## 43. Final T13S20 result and active T13S21 task

Package v2 at execution commit `9113198` passed the fresh offline gate and
started the S20 training-baseline phase at:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s20_runs/
stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_20260803_9113198
```

It produced exactly 24 training-baseline JSON.GZ files. Independent
server-side raw, snapshot, manifest, source, and complete-log forensics found:

```text
raw parse / expected                                      24 / 24
complete success / structured partial failure             23 / 1
successful runtime / restart / causality                  23 / 23
successful actuator / dynamic design / exact net          23 / 23
successful-context zero-plant probe replays              184 / 184
snapshot inventories                                      40 / 40
maximum dynamic design condition                       3.1980986512
maximum successful current utilization                  0.392
formal tracking diagnostic                                10 / 23
training probe / calibration / holdout raw                 0 / 0 / 0
```

The raw inventory is 24 files, 1,342,538 bytes, digest
`d78ba9a01e54611c7489bc13ae70883b2020a5647473976e6ca29c9c2f22de52`.
The one failed raw is experiment `s42r3c3_a40f88ad021de4a85a93`, with
trajectory/trace lengths 8/7. It stopped while constructing the eighth action
with `ValueError('T13S20 dynamic calibration sequence is not exact zero net')`.
No eighth plant advance occurred.

Source-exact zero-plant replay found that independent nearest quantization
would leave only coil index 8 at `+0.0004 kA-turn`. The exact negative of the
seven-event running net is nevertheless Card15-representable on 14/14 coils
and passes all unchanged gates:

```text
signed primary / maximum cross coordinate        1.000000 / 0.025000
desired/actual cosine                              0.9999973274
relative off-basis residual                            3.74e-16
incremental / total normalized action             0.214810 / 0.216048
predicted current utilization                              0.3761
```

This is an excitation-sequence design failure, not a runtime, TSC, restart,
raw, observer, MPC, control, or plant failure. The state also contains a
reporting-only defect: `finished=true` and stop reason are correct, but
`phase_status` remains `offline_ready`.

S20 is frozen and cannot resume because cumulative closure changes the
controller source fingerprint and failed-path physical action. Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S20_FORENSIC_REPORT.md
```

The active task is the separately frozen T13S21 design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S21_CUMULATIVE_EXACT_CLOSURE_DESIGN.md
```

S21 uses fresh stage/campaign/controller/package identities and reruns all
360 trajectories. Steps 0--6 retain S20's causal nearest dynamic-exact rule;
step 7 applies the exact negative of the seven-event Decimal running net and
must satisfy the unchanged primary/cross/cosine/off-basis/action/current and
exact-zero gates. S20 raw cannot be relabeled or reused as S21 outcomes.

Implement, validate, deploy, and run S21 only through its frozen phased gates.
A complete holdout pass permits only offline robust-transport MPC feasibility
and a separately preregistered real-MPC experiment. Expert data, BC, DAgger,
and bounded residual RL remain prohibited.

## 44. Final T13S21 result and active T13S22 task

T13S21 completed its prospectively phased campaign at deployed checkpoint
`98dc353`. It produced exactly 360 successful real-TSC raw files:

```text
training / calibration / holdout rollouts              216 / 72 / 72
raw files / bytes                                  360 / 21,083,271
raw inventory digest
  8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4
runtime / restart / raw / reporting errors                      0 / 0 / 0 / 0
fresh holdout point / containment / cap / joint            64 / 64 / 64 / 64
maximum fresh-holdout scaled point error                    0.0108949379
```

The training model was hashed before calibration and the calibrated tube
before holdout. Independent server raw recomputation reproduced both
artifacts and the final summary exactly. The final route is:

```text
CUMULATIVE_EXACT_CARD15_POOLED_OBSERVER_HOLDOUT_PASS_LOCAL_SET_MODEL_ONLY
```

This is a finite local response-set model PASS, not a real MPC or formal
control PASS. Retrospective raw/spec-matched route forensics found baseline
formal control 16/40, measured signed-probe formal control 99/320, and zero
repairs across all 24 failing contexts. Six passing contexts had at least
one measured-probe regression. The complete classification is in:

```text
docs/codex/reports/STAGE4_2R3C3T13S21_FORENSIC_REPORT.md
```

The active zero-new-TSC task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S22_FULL_HORIZON_AFFINE_AUTHORITY_DESIGN.md
```

T13S22 must authenticate all 360 S21 raw files, reproduce all 360 raw formal
diagnostics, construct the four odd signed full-horizon responses per
context, and optimize one coefficient vector in `[-1,1]^4` under the exact
unchanged formal metric. A 40/40 optimistic affine pass authorizes only a
small separately preregistered real combination sentinel. A failure vetoes
this single-issue affine model and requires a sequential state-conditioned
transition model. Neither route authorizes real MPC, expert data, BC,
DAgger, or bounded residual RL.

## 45. Final T13S22 result and active T13S23 task

T13S22 completed its zero-new-TSC full-horizon affine authority audit at
implementation and deployment checkpoint `dc4b559`. It authenticated all
360 S21 raw, reproduced 40/40 baselines and 320/320 measured probes, and
completed all 40 bounded optimizations and independent forward checks.

```text
baseline formal pass / total                              16 / 40
optimistic affine formal feasibility                      16 / 40
failed baselines repaired                                  0 / 24
passing baselines regressed                                 0 / 16
all solutions with a coefficient within 1e-6 of a bound   40 / 40
new raw / snapshots / TSC / plant advances               0 / 0 / 0 / 0
```

All 24 failed affine contexts were limited by sustained position error; four
also had a negative post-arrival-speed margin, and Ip was not limiting. The
independent server postprocessor reconstructed every saved coefficient
trajectory directly from raw and reproduced the exact classification. The
final route is:

```text
AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED
```

This is a clean finite model-class/authority failure, not a runtime,
deployment, raw, restart, statistics, reporting, real-controller, real-MPC,
or global plant-reachability result. The complete report is:

```text
docs/codex/reports/STAGE4_2R3C3T13S22_FORENSIC_REPORT.md
```

The active zero-new-TSC task is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S23_SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_DESIGN.md
```

T13S23 authenticates the S21/S22 chain and replays a fixed 24-sequence
Sylvester-Hadamard design over the same 40 baselines. Each sequence combines
the four fixed S21 QR directions at issue steps 10, 13, 16, and 19 with
adjacent exact stored-center cancellations. It must pass 3,840 issue and
3,840 cancellation constructions, exact Card15/zero-net/action/current
gates, per-slot rank four, global rank 16, normalized condition at most 3,
and late-slot novelty in every context.

S23 creates zero raw and executes zero TSC or plant step. A pass authorizes
only a separately implemented 1,000-rollout sequential identification
campaign. That campaign must freeze its causal transition-model family,
whole-pair training/calibration/holdout boundaries, recursive-prediction
gates, and stop-at-boundary policy before any response outcome opens. No S23
route authorizes a real MPC, expert data, BC, DAgger, or bounded residual RL.

## 46. Final T13S23 result and active schedule-redesign task

T13S23 completed twice from the installed `7aab947` package with byte-exact
independent outputs. It authenticated all 360 S21 raw files, reproduced all
40 baselines and 320 measured probes, and executed zero new TSC, Ray,
controller, plant, or snapshot work.

```text
finite issue/cancel constructions                         7680 / 7680
issue action/geometry/current gates                       1920 / 3840
exact cancellation gates                                  3720 / 3840
central-sign target symmetry                              1280 / 1280
global rank/condition contexts                               40 / 40
slot rank/condition blocks                                  160 / 160
late novelty contexts                                        40 / 40
maximum global condition                              1.6539378019
maximum slot condition                                1.1695106354
minimum late residual                                 0.9428090416
maximum current utilization                                  0.3917
```

Every issue failure was reproduced from the raw event rows. Exactly 960 rows
failed only the `0.10` off-basis cap and 960 failed both the off-basis cap and
`0.98` cosine floor. All 3,840 issue actions passed the unchanged `0.25`
incremental cap; the maximum was `0.0944439202`. The 120 cancellation
failures were confined to slot 3 in five contexts and failed only the `0.25`
incremental cap, with maximum `0.3106592894`; exact target return and zero net
were 3,840/3,840.

The final route is:

```text
SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_FAIL_SCHEDULE_REDESIGN
```

This is a deterministic action-schedule-design failure, not a runtime,
deployment, source/raw, restart, reporting, controller, real-MPC, plant, or
global-reachability failure. Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S23_FORENSIC_REPORT.md
```

S24 is not authorized. The active task is a new-identity, zero-TSC
development search followed by a separately frozen schedule preflight. It
may prospectively alter coordinate sparsity, amplitude, sequence matrix, or
knot locations, but it may not relabel S23, weaken S23 after the result,
change the immutable formal timing contract, or claim plant response. No real
identification campaign may begin until the new frozen preflight passes and
is independently reproduced. MPC, expert data, BC, DAgger, and bounded
residual RL remain prohibited.

The bounded D1 development search is frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S23D1_SCHEDULE_REDESIGN_SEARCH.md
```

D1 evaluates only the fixed ternary-template, amplitude, knot, and seeded
schedule space in that document. A found candidate authorizes only a separate
S23R1 zero-TSC design and replay; a D1 result never authorizes S24 directly.

## 47. Final T13S23D1 result and active T13S23R1 task

T13S23D1 completed twice from deployed checkpoint `7f66d4c`; detailed,
summary, and manifest outputs were byte-identical. It authenticated the full
S21/S22/S23 chain and evaluated all 128,000 frozen signed-template events.

```text
feasible sign pairs at every issue step                    103 / 160
step 10--17 cancellation contexts                      40 / 40 each
step 18 / 19 cancellation contexts                       39 / 40, 35 / 40
admissible four-knot sets                                      5
seeded schedule tests                                     100000
global-condition passes                                        0
best requested normalized global condition             7.2966498190
new raw / snapshots / TSC / plant / controller          0 / 0 / 0 / 0 / 0
```

The exact route is:

```text
BOUNDED_TERNARY_SCHEDULE_SEARCH_FAIL_NEW_EXCITATION_ARCHITECTURE_REQUIRED
```

This is a deterministic random independent-block schedule-architecture
failure, not a runtime, raw, reporting, controller, plant, or MPC failure.
Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S23D1_FORENSIC_REPORT.md
```

Post-D1 structured algebra found a single amplitude-coded H16 candidate using
only D1-authenticated feasible templates: `++++` and `+-+-` at `0.25`, and
`++--` and `+--+` at `0.50`. Its requested matrix has global condition
`2.8284271247`, slot condition `2.0`, and minimum late residual
`0.9428090416`.

The active zero-TSC S23R1 design is frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S23R1_AMPLITUDE_CODED_HADAMARD_PREFLIGHT_DESIGN.md
```

S23R1 must use issue steps `10,13,15,17`, adjacent exact cancellations, the
exact fixed amplitude map, and unchanged Card15/cosine/off-basis/action/
current/rank/condition/novelty/formal gates. A pass authorizes only a
separately frozen S24 identification campaign; it does not authorize real
MPC or RL. Expert data, BC, DAgger, and bounded residual RL remain prohibited.

## 48. Final T13S23R1 result and active T13S24 task

T13S23R1 completed its zero-TSC fixed-candidate preflight twice from deployed
checkpoint `58d212c`; all three output files were byte-identical. Independent
server-side forensics strictly parsed all 360 immutable S21 raw JSON.GZ and
recomputed every detailed event and matrix gate.

```text
source raw authentication / strict parse                  360 / 360
contexts / event rows                                    40 / 3840
finite issue/cancel constructions                      7680 / 7680
issue / cancellation gates                         3840 / 3840 each
central-sign Decimal checks                            1280 / 1280
global rank-16 contexts / slot rank-4 blocks             40 / 160
maximum actual global / slot condition        2.87688005 / 2.03426139
minimum actual late-column residual                     0.94280904
new raw / snapshots / TSC / plant / controller      0 / 0 / 0 / 0 / 0
```

The final route is
`AMPLITUDE_CODED_HADAMARD_PREFLIGHT_PASS_FREEZE_S24_REQUIRED`.  This is a
clean action-schedule preflight PASS, not a plant, controller, MPC, or restart
control result.  The complete forensics are frozen in:

```text
docs/codex/reports/STAGE4_2R3C3T13S23R1_FORENSIC_REPORT.md
```

The active task is the new-identity 1,000-rollout S24 sequential transition
identification campaign prospectively frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24_SEQUENTIAL_TRANSITION_IDENTIFICATION_DESIGN.md
```

S24 uses the unchanged twenty whole-pair split and 40 authenticated contexts.
Each context receives one fresh baseline and all 24 S23R1 sequences, for
training/calibration/fresh-holdout counts `600/200/200`. Its model must
recursively predict from authentic causal state-10 history to the unchanged
state-35/37 formal endpoint, freeze after training, freeze its tube after
calibration, and pass a fresh whole-pair holdout plus independent raw
recomputation. Every failed phase boundary stops the campaign before later
outcomes open.

An S24 pass authorizes only a separately preregistered zero-TSC robust
finite-horizon feasibility/MPC design. It does not authorize real MPC,
expert data, BC, DAgger, or bounded residual RL.

## 49. Final T13S24 training result and active T13S24D1 task

The authentic S24 training boundary completed 600/600 raw: 24/24 baselines and
576/576 sequential specs. Independent server-side reconstruction found 522
complete sequence successes and 54 structured failures. Every failure was a
0.50-amplitude `sequential_cancel` incremental-action guard; all 1,152 actually
executed 0.25 cancellation events passed, with maximum increment 0.2360657249.

There were zero active old-hotfix, issue-action, TSC, solver, restart,
causality, raw-corruption, or other runtime failures and zero reporting errors.
The state route `SEQUENTIAL_IDENTIFICATION_RUNTIME_FAIL` is coarse: the raw
scientific classification is an online action-schedule design failure. Model
fitting, calibration, and holdout were never opened. S24 may not resume, and
its partial successful sequence raw may not be mixed into a new model.

Full evidence is frozen in:

```text
docs/codex/reports/STAGE4_2R3C3T13S24_FORENSIC_REPORT.md
```

The active stage is the already preregistered zero-new-TSC S24D1 contracted
amplitude preflight. Its only allowed amplitude map is:

```text
++++  0.25
+-+-  0.25
++--  0.225
+--+  0.225
```

S24D1 must independently authenticate the complete S24 boundary and archived
hotfix failure inventory, replay all 3,840 issue and 3,840 cancellation
constructions on the 40 immutable S21 contexts, and select all 54 allowed S24
failures for a fresh-identity sentinel table. Any changed source failure class
must stop. A pass authorizes only Stage4.2R3c3T13S24D2 real-TSC safety
sentinel execution with the added prospective 0.24 online cancellation margin.
It does not authorize a full campaign, transition MPC, expert data, BC,
DAgger, or RL.

## 50. Final T13S24D1 result and active T13S24D1R1 task

S24D1 authenticated the complete source boundary and replayed all 7,680
zero-TSC constructions. Its fixed `0.25/0.25/0.225/0.225` map failed:

```text
source applicability                                      pass
issue gates                                         1920 / 3840
cancellation gates                                  3840 / 3840
central-sign checks                                 1280 / 1280
rank-16 contexts / rank-4 slot blocks                  40 / 160
new raw / Ray / gotsc / TSC / plant / controller         all zero
route        CONTRACTED_AMPLITUDE_PREFLIGHT_FAIL_REDESIGN_REQUIRED
```

All 1,920 issue failures were `++--` or `+--+` at 0.225. Every one failed
relative off-basis residual and 960 also failed desired/applied current cosine.
The active-coordinate, action, current, cancellation, finite, rank, condition,
and novelty gates passed. This is a real static schedule-design failure, not a
runtime, raw, restart, control, or reporting result. No sentinel was authorized.

The active stage is the prospectively frozen zero-TSC S24D1R1 design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R1_GEOMETRY_RESTORING_AMPLITUDE_SEARCH_DESIGN.md
```

It keeps `++++` and `+-+-` at 0.25 and searches `++--` then `+--+`
independently on the exact Decimal grid 0.225 through 0.500 in 0.005 steps.
The first amplitude passing all 960 unchanged issue gates is selected for each
pattern, followed by one complete all-context replay. No grid refinement,
continuous optimizer, or gate relaxation is allowed. A pass authorizes only a
fresh-identity real-TSC sentinel over all 54 S24 failure contexts with the
prospective 0.24 online cancellation margin; the full campaign, MPC, expert
data, BC, DAgger, and RL remain unauthorized.

## 51. Final T13S24D1R1 result and active T13S24D1R2 task

S24D1R1 completed its frozen zero-TSC search from installed checkpoint
`8486837`. Independent server-side parsing and byte/hash assertions reproduced
the saved result:

```text
selected amplitudes                              ++-- 0.290 / +--+ 0.360
issue / cancellation gates                         3840 / 3840 each
finite constructions / central signs                 7680 / 1280
global rank contexts / slot-rank blocks                  40 / 160
requested global / maximum slot condition      2.03646753 / 1.44
selected unique sentinel specifications                    54 / 54
new raw / snapshots / Ray / TSC / plant / controller      all zero
route       GEOMETRY_RESTORING_AMPLITUDE_SEARCH_PASS_REAL_SENTINEL_REQUIRED
```

The immediately preceding grid points, 0.285 and 0.355, each failed all 960
occurrences only on the unchanged off-basis cap; the selected points passed
all original gates. This is a finite static construction PASS, not plant,
restart-control, model, MPC, or robustness evidence. Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R1_FORENSIC_REPORT.md
```

Independent inspection also found a metadata-only generator defect before any
sentinel execution: the authoritative stage/campaign/controller fields say
D1R2, but several opaque experiment/path/package label strings retain the
older hard-coded `s24d2/contracted` token. The 54 identities are unique and
the selected snapshots, tasks, actions, timing, gates, and forbidden-input
semantics are unchanged. The completed D1R1 artifacts remain immutable.

The active task is to freeze Stage4.2R3c3T13S24D1R2 before implementation.
It must deterministically normalize only those stage-derived identity labels,
prove all scientific fields unchanged, and then execute all 54 selected
trajectories with a fresh TSC process and causal controller. Every trajectory
must reach its full 35/37-state horizon, execute all four issue/cancel pairs,
pass the unchanged 0.25 action safety cap plus the prospective 0.24 online
cancellation margin, and pass restart, calibration, causality, Card15,
current, exact-zero, no-label, raw, snapshot, and manifest gates.

A D1R2 pass authorizes only a separately frozen new-identity full replacement
sequential transition-identification campaign. It does not authorize a
transition MPC, expert data, BC, DAgger, or RL.

The D1R2 design is now frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R2_REAL_TSC_SAFETY_SENTINEL_DESIGN.md
```

It fixes the ordered normalized-spec digest
`50832fadb244bbd338bd7c5cd5f9ff136eedce498d920f416458516d7655648f`,
54 fresh one-actor/one-TSC/one-controller rollouts, 20 normal and 34 weak-slew
formal horizons, all original S24 gates, and the additional fail-closed 0.24
online cancellation margin. The independent raw forensic implementation must
also be frozen before any response outcome opens.

## 52. Final T13S24D1R2 result and active cancellation-redesign task

D1R2 package v2 repaired only a pre-TSC selected-snapshot aggregation bug.
The successful zero-plant preflight authenticated all 18 selected snapshots
and 54 normalized specs, after which the same run identity executed all 54
fresh real-TSC rollouts. Independent raw and complete-log forensics found:

```text
raw strict parse / exact identity                    54 / 54
full-horizon successes / structured safe stops       45 / 9
restart / causality / calibration                    54 / 54 each
issue gates                                         216 / 216
successful applied cancellation gates               207 / 207
failed, unapplied cancellation attempts                    9
0.24 cancellation margin pass / fail                 207 / 9
original 0.25 cancellation cap pass / fail           211 / 5
maximum successful / attempted increment    0.2162433 / 0.2787208
maximum current utilization                              0.392
runtime / raw / snapshot / restart errors                    0
route     GEOMETRY_RESTORED_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED
```

All nine failures were the task-step-18 slot-3 `++--=0.290` exact-center
cancellation in sequence rows 6, 10, and 18: three in p5 plus-first and three
in each p9 history member. The failed action was recorded before return and
was not applied; every partial raw contains 19 states and 18 trace rows.

The prospective audits selected the correct route but their top aggregates
omitted the executed prefixes of structured failures. A reporting-only audit
authenticated the frozen v2 package and all raw, corrected the totals above,
and left state, verdict, route, raw, and experiment semantics unchanged.

This is a genuine sequential action-schedule design failure. D1R1's static
construction used a frozen S21 baseline and did not represent the evolved
plant/feedback center at the fourth cancellation. Full report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R2_FORENSIC_REPORT.md
```

D1R2 is immutable and may not resume. Its raw is development/forensic-only.
The full replacement identification campaign and every MPC/RL stage remain
blocked. The active next task is a separately frozen zero-new-TSC causal
two-step exact-return cancellation preflight. It may use the current raw only
for development replay, must preserve the 0.290 geometry floor and exact
Card15 telescoping net zero, and must keep each returned action inside a new
prospective sub-cap and all unchanged current/safety gates. A pass may
authorize only a fresh real-TSC sentinel over the nine failed contexts.

## 53. Final T13S24D1R3 result and active T13S24D1R4 task

D1R3 completed two byte-identical zero-new-TSC causal replays from final
package checkpoint `93afef5`. It authenticated and strictly parsed the exact
54-file D1R2 raw boundary and independently reproduced the result:

```text
source action / trace prefixes exactly reproduced          54 / 54 each
unchanged full-success paths / structured-stop prefixes     45 / 9
saved direct failure actions reproduced                      9 / 9
split-start constructions and frozen gates                   9 / 9
split-start incremental normalized action             0.175 exactly
maximum split-start total action / current use   0.0349527 / 0.38235
new raw / snapshots / Ray / gotsc / TSC / plant              all zero
route       CAUSAL_SPLIT_RETURN_PREFLIGHT_PASS_REAL_SENTINEL_REQUIRED
```

The split cases remain exactly task step 18, slot 3, sequence rows 6, 10, and
18 in the same three D1R2 contexts. D1R3 validates only the causal
intermediate construction at the recorded failure state. It has no state-19
plant response and makes no split-finish or formal-control claim. Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R3_FORENSIC_REPORT.md
```

The active task is to prospectively freeze and then execute a new-identity
Stage4.2R3c3T13S24D1R4 nine-case authentic real-TSC safety sentinel. It must
use one fresh TSC process and fresh causal controller per case, apply the
frozen split start at step 18, advance the plant once, and finish to the exact
stored center at step 19 with incremental action at most 0.24, original cap
at most 0.25, current utilization at most 0.55, no saturation/clipping, exact
Card15 reproduction, exact Decimal telescope, and all unchanged restart,
calibration, causality, forbidden-input, full-horizon, raw, snapshot,
manifest, and complete-log gates.

A D1R4 pass may authorize only a separately frozen full replacement
sequential transition-identification campaign. It does not authorize a
transition MPC, expert data, BC, DAgger, or RL.

The D1R4 design is now frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R4_REAL_TSC_SPLIT_RETURN_SENTINEL_DESIGN.md
```

It fixes nine fresh 35-step authentic rollouts, nine actors, three restart
snapshots, the exact D1R3 candidate digest, step-18 split start, one authentic
plant advance, step-19 causal exact-center finish, full raw/log/manifest gates,
and an independent raw implementation frozen before response outcomes.

## 54. Final T13S24D1R4 result and active T13S24D1R5 task

D1R4 package v1h2 completed nine fresh authentic TSC prefixes from checkpoint
`da3f4b4`. All nine raws strictly parse with exact identity, 20 states, and 19
executed trace rows. A reporting-only all-raw audit at checkpoint `69dedc0`
closed the prospective audits' structured-stop aggregation gap without
changing any raw, controller, gate, route, or experiment identity:

```text
restart / causality / calibration                         9 / 9 each
source action / trace prefix exact                        9 / 9 each
D1R3 step-18 split-start exact                             9 / 9
issue / direct cancel / split start events             36 / 27 / 9
step-19 exact-center finish attempts                        9
finish actions applied / safely rejected                  0 / 9
0.24 margin pass / fail                                   0 / 9
original 0.25 cap pass / fail                             0 / 9
finish intervention range                    0.2712316553--0.3540255817
maximum executed / predicted current use          0.39045 / 0.3838
runtime / raw / snapshot / restart errors                     0
formal endpoint evaluable trajectories                         0
route          CAUSAL_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED
```

Every step-18 split start was applied and followed by one finite authentic
plant advance. At state 19 the exact-center finish candidate passed every gate
except the frozen intervention increment relative to the new underlying
baseline. It was rejected before application. Its smaller diagnostic distance
from the previously executed command is not the preregistered metric and may
not be substituted after seeing the result.

The prospective audits selected the correct route but reported executed-prefix
aggregates as zero because their success-only branch excluded structured safe
stops. The new retrospective audit corrects only those counts. Formal tracking
is not 0/9 failure; no trajectory reached the endpoint, so the formal test was
not run to completion. Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R4_FORENSIC_REPORT.md
```

D1R4 is immutable and may not resume. Its raw is development/forensic-only.
The full replacement campaign, transition MPC, expert data, BC, DAgger, and RL
remain blocked.

The active task is the prospectively frozen Stage4.2R3c3T13S24D1R5
zero-new-TSC recursive split-return preflight. It must authenticate all nine
D1R4 raws and replay their controllers causally through state 19, reproduce the
rejected direct finish, and replace it only in the new controller identity with
another exact-Card15 0.175 intermediate. It must preserve every 0.18/0.24/0.25,
total-action, current, exact Decimal, forbidden-input, and timing gate. It may
use no state-20 value and may execute no plant step.

The complete frozen design is:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R5_RECURSIVE_SPLIT_RETURN_PREFLIGHT_DESIGN.md
```

A D1R5 pass authorizes only prospective design of a new-identity authentic
recursive-return sentinel whose exact-center finish boundary is no later than
task step 22. It does not authorize that run directly or any identification,
MPC, expert-data, BC, DAgger, or RL work.

## 55. Final T13S24D1R5 result and active T13S24D1R6 task

D1R5 completed two byte-identical zero-new-TSC server replays from final
package checkpoint `7389154`. Both authenticated the exact nine-file D1R4 raw
boundary, and the primary and independent implementations each obtained:

```text
strict source raw / controller replay                         9 / 9
source action / trace prefix exact                            9 / 9
saved state-19 direct finish failure reproduced               9 / 9
causal exact-Card15 0.175 continuation                        9 / 9
forbidden controller inputs                                       0
new raw / snapshots / Ray / gotsc / TSC / plant                  all zero
formal endpoint evaluable                                         0
route  CAUSAL_RECURSIVE_SPLIT_RETURN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

The direct finish increment remained `0.2712316553--0.3540255817`.
The continuation maximum was `0.17500000000000002`, total normalized action
maximum `0.0756922483`, and predicted current utilization maximum `0.38125`.
The nine D1R6 candidate specs have digest
`f3ca434af404bb20c85e7ff2fb6da40bc13c1d873ae9c74396ab8680533b889b`.

Two pre-scientific invocations are preserved. The first stopped before output
because the primary authenticator incorrectly required D1R4 to remain the
currently installed package. The second wrote the four successful primary
files and then the independent tool made the same resume-only check. These
were source-authentication/reporting code bugs with zero TSC and zero plant
advance. Fixes `b8626c1` and `55e7720` retained the frozen historical D1R4
package/source fingerprints and changed no controller or experiment
semantics. Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R5_FORENSIC_REPORT.md
```

D1R5 is immutable. It is not a state-20, finish, formal-control, model, MPC,
or robustness result.

The active task is the separately frozen Stage4.2R3c3T13S24D1R6 authentic
recursive-return safety sentinel. Its exact design is:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R6_REAL_TSC_RECURSIVE_RETURN_SENTINEL_DESIGN.md
```

D1R6 fixes nine fresh 35-step authentic TSC trajectories and nine fresh
controllers. Step 18 applies the original split start; step 19 must apply the
D1R5-authenticated 0.175 continuation. At steps 20--21 the current controller
may causally finish or apply another exact 0.175 continuation. Step 22 may
only finish or stop structurally before plant advance. The stored center must
be restored by task step 22 under every unchanged action/current/exactness
gate. Formal arrival remains step 25 and hold remains step 35.

A D1R6 pass authorizes only design of a full replacement sequential-transition
identification campaign. Neither route authorizes transition MPC, expert data,
BC, DAgger, or bounded residual RL.

## 56. Final T13S24D1R6 result and active schedule-redesign discriminator

D1R6 completed all nine fresh authentic TSC sentinels from final execution
package checkpoint `4177aa2`. Independent raw/log/snapshot recomputation and a
separate reporting-only physical-state audit found:

```text
strict raw / identity / restart / causality / calibration       9 / 9 each
physical source state / action / trace prefix exact              9 / 9 each
split start / first D1R5 continuation exact                      9 / 9 each
continuations at task steps 19 / 20 / 21                      9 / 9 / 9
continuation increment                                   exactly 0.175
exact-center finishes / full horizons                           0 / 9
task-step-22 structured safe stops                              9 / 9
failed action applied / plant advance afterward                    0 / 0
runtime / solver / raw / snapshot / current errors                  0
formal endpoint evaluable                                           0
route  CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED
```

The causal exact-center intervention range was
`0.2712316553--0.3540255817` at step 19,
`0.3755641011--0.4922624755` at step 20,
`0.5633025885--0.6879459063` at step 21, and
`0.3673570430--0.5149905137` at step 22. Repeated straight-line 0.175
intermediates therefore did not contract the return requirement. This is a
genuine fixed recursive action-schedule/controller-design failure, not a
runtime, restart, corruption, current, real-MPC, formal-control, or global
plant-reachability result.

The original primary/independent state-prefix count was 0/9 only because it
included `gotsc_subprocess_s` and `step_total_s`. A semantics-preserving audit
at checkpoint `c33a368` found 171 differences in each timing field and zero
unexpected physical-state differences, correcting the physical prefix count
to 9/9 without changing raw, controller, identity, route, or experiment
semantics. Its first server invocation omitted `PYTHONPATH` and stopped before
output; the corrected server-virtualenv invocation passed. That was a
postprocessing invocation error only.

Exact report and compact evidence:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R6_FORENSIC_REPORT.md

docs/codex/audits/
stage4_2r3c3t13s24d1r6_20260803_4177aa2/
```

D1R6 is immutable and may not resume. Its nine large raw JSON.GZ files remain
server-side and are forbidden from model fitting and expert data.

The active task is a prospectively frozen zero-new-TSC fixed-global-schedule
redesign/discriminator. It must authenticate S24 and D1R2--D1R6, preserve the
`++--=0.290` geometry floor and all 0.18/0.24/0.25, total-action, current,
exact-Decimal, rank/condition/novelty, forbidden-input, and immutable timing
gates. It may examine fixed sequence substitution, reordering, or knot
placement offline, but the eventual controller may not select from
pair/history/outcome labels. A pass may authorize only a separately frozen
fresh-identity real safety sentinel. It does not authorize the full campaign,
transition MPC, expert data, BC, DAgger, or RL.

The D1R7 candidate is now frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R7_TEMPORAL_BASIS_SUBSTITUTION_PREFLIGHT_DESIGN.md
```

It changes only the direction-2 temporal basis to
`++++, +--+, -+-+, --++`, retains the other three H4 temporal bases, and fixes
eight explicit central-sign pairs. Its requested matrix digest is
`c4430a13b679ad8dcceb72c259051a5eebad03da47d86816d46c4385cd811d77`.
D1R7 must replay all 7,680 static constructions in 40 contexts and freeze only
the six changed/new rows across the 18 D1R2 contexts, yielding 108 prospective
D1R8 specs. It executes zero TSC. Even a double byte-identical pass authorizes
only a separate D1R8 design.

## 57. Final T13S24D1R7 result and active T13S24D1R8 task

D1R7 final implementation/package checkpoints are `da578de` / `0c2311a`.
The first official invocation stopped before output because the primary
reader incorrectly asserted that all 54 authentic S24 structured failures
were slot 3/task step 18. Direct parsing of all 600 S24 raw showed the exact
unchanged failure distribution:

```text
slot 0 / step 11    12
slot 1 / step 14    16
slot 2 / step 16     4
slot 3 / step 18    22
```

Every event remained `sequential_cancel`, `passed=false`, and strictly above
0.25, with the original per-sequence counts and raw digest. The primary and
independent hotfix repaired only source authentication/reporting. It changed
no matrix, threshold, spec, gate, source fingerprint, controller/action,
formal timing, or physical semantics and ran zero TSC/plant steps.

The two accepted official outputs are byte-identical. Primary and independent
forensics found:

```text
S24 / D1R2 / D1R6 authenticated raw                  600 / 54 / 9
finite / issue / cancellation / central gates   7680 / 3840 / 3840 / 1280
global / slot / late gates                            40 / 160 / 40
maximum actual global / slot condition          2.0327654765 / 1.3944510812
minimum actual late residual                       0.9593473942
candidate specs / IDs / contexts / snapshots       108 / 108 / 18 / 18
new raw / Ray / gotsc / TSC / controller / plant       0 / 0 / 0 / 0 / 0 / 0
route  TEMPORAL_BASIS_SUBSTITUTION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

Exact report and compact evidence:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R7_FORENSIC_REPORT.md
docs/codex/audits/stage4_2r3c3t13s24d1r7_20260803_0c2311a/
```

The active D1R8 design is frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R8_REAL_TSC_TEMPORAL_BASIS_SENTINEL_DESIGN.md
```

D1R8 must execute exactly 108 fresh authentic real-TSC sentinels from the
frozen D1R7 table: six changed/new rows across 18 authentic contexts, with 48
35-step and 60 37-step horizons. It must preserve every action/current,
restart, causality, calibration, blindness, exactness, and immutable timing
gate. A pass authorizes only design of a full replacement identification
campaign. It does not authorize the campaign itself, MPC, expert data, BC,
DAgger, or RL.

## 58. Final D1R8--D1R10 evidence and active D1R11 campaign

D1R8 completed its 108 authentic sentinels with 105 full-horizon successes
and three structured safe stops. All three stops were D1R7 row 22's final
cancellation at task step 18. The candidate action was not applied and the
plant did not advance afterward. Independent raw forensics found exact
restart and causal executed prefixes in 108/108, no runtime/solver/raw/current
error, and a real schedule-design failure rather than plant unreachability.
The success-only partial-prefix aggregate was a reporting bug and was
corrected without changing raw, actions, identity, or route.

D1R9 then ran zero TSC and completed two byte-identical primary/independent
exhaustive preflights. It changed only central row 22 and selected:

```text
requested matrix digest
  106dfed384febb16019e4d39ce1da03762ad9dbb5e8e69120a4a9d9acdebc30b
selected sorted central primaries
  [0, 1, 3, 4, 5, 7, 8, 9]
selected ordered central primaries
  [0, 4, 1, 5, 3, 7, 9, 8]
exact-safe / contradicted / unknown rows
  17 / 0 / [3, 7, 11, 15, 20, 21, 22]
```

D1R10 executed those seven rows on 18 contexts. Complete independent raw
recomputation found:

```text
strict raw / successful full horizon                    126 / 126
restart / causality / calibration                       126 / 126
issue / cancel / margin events                          504 / 504 each
runtime / raw / snapshot / forbidden-use errors                   0
maximum cancellation incremental action          0.20245088117122614
maximum current utilization                                    0.392
formal tracking diagnostic                                  28 / 126
route
  EXACT_ROW_COMPLETION_SENTINEL_PASS_FULL_REPLACEMENT_IDENTIFICATION_DESIGN_REQUIRED
```

The first post-run independent-audit invocation omitted the repository root
and failed with `ModuleNotFoundError` before output. Hotfix `9068bf0` made the
entrypoint cwd-independent; its audit is byte-identical to the already
successful audit. A first CRLF checksum package and a partial SFTP staging
upload were also rejected before installation/TSC. None changed experiment
semantics or required a TSC rerun. Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R10_FORENSIC_REPORT.md
```

The active task is the prospectively frozen D1R11 full replacement campaign:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R11_FULL_REPLACEMENT_IDENTIFICATION_DESIGN.md

training      12 whole pairs / 24 contexts / 600 fresh rollouts
calibration    4 whole pairs /  8 contexts / 200 fresh rollouts
fresh holdout  4 whole pairs /  8 contexts / 200 fresh rollouts
total         20 whole pairs / 40 contexts / 1000 fresh rollouts
ordered spec digest
  e370269558ab079fe6d1f2293b2920b7774e3239942c7dd60ae4b638138f8c7a
```

D1R11 must authenticate both byte-identical D1R9 outputs, complete D1R10 raw
and independent audit, and the original S24 source chain before zero-TSC
offline acceptance. It preserves the original S24 causal model candidates,
ridge ordering, recursive error gate, tube construction, formal verdict
reproduction, and immutable timing. It carries the D1R10 0.24 cancellation
margin as an additional pre-apply safety guard.

All D1R11 baseline and sequence trajectories have a fresh identity and fresh
TSC/controller. S24/D1R10 raw is authentication/safety evidence only and is
forbidden from the D1R11 model, tube, holdout, and expert datasets. Training
must hash-freeze its model before calibration opens; calibration must
hash-freeze its tube before holdout opens. Any phase failure keeps later
outcomes unopened and must be classified separately.

Even a full D1R11 pass authorizes only a separately preregistered zero-new-TSC
robust finite-horizon MPC feasibility/controller design. Real MPC execution,
expert data, BC, DAgger, and bounded residual RL remain unauthorized.

The first official D1R11 `offline` invocation used run directory
`stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_20260804_571b932_v1`
and stopped before any TSC/controller/plant execution. The source
authentication code incorrectly read the nonexistent D1R9 detailed-output
field `primary_pass`; the authenticated official schema uses top-level
`passed=true`. Direct read-only inspection confirmed that both D1R9 output
directories remain byte-identical across all five files and that route,
independent pass, source/requested matrix digests, changed/contradicted/unknown
rows, and the complete requested matrix all match the frozen D1R11 contract.

Checkpoint `027f555` changes only that field lookup and adds a regression test
using the official schema. It changes no config, source hash, requested matrix,
task identity, controller action, phase boundary, model/tube gate, formal
timing, or scientific route. The failed invocation created zero raw and is a
pre-execution source-authentication code error, not a runtime TSC failure,
reporting/statistics error, design failure, or control/plant-restart result.

## 59. Final D1R11 result and active causal architecture redesign

The source-authentication hotfix was packaged at checkpoint `05c8521` without
changing experiment semantics. The installed package passed 1,023/1,023
tests with one expected server skip. D1R11 then completed the complete frozen
training boundary:

```text
training baselines / sequential responses             24 / 576
training total                                           600 / 600
strict raw / exact source restart / causal execution     600 / 600 each
training raw bytes                                        35,511,922
training raw inventory digest
  8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7
calibration / fresh holdout                                  0 / 0
runtime / solver / raw / snapshot / report errors                0
formal tracking diagnostic                                158 / 600
```

The accepted independent v3 audit strictly parsed all 600 raw files, rehashed
192 files across 24 restart snapshots, authenticated every source endpoint,
and reproduced all 4,800 calibration and 4,608 issue/cancel events. Earlier
v1/v2 audit attempts had postprocessing-only assumptions about checkpoint
time, cancellation schema, and explicit zero baseline schedules; their fixes
changed no raw, controller, state, or experiment semantics.

All 24 preregistered L/SA/Q recursive transition candidates failed the frozen
training gate. The selected L/ridge-1 candidate reproduced 532/600 formal
diagnostics, had 68 mismatches, and reached maximum recursive scaled error
`0.9580646071` against the unchanged `0.1` limit. Its R/Z/vR/vZ tube precursor
also exceeded the frozen caps. No model or tube was frozen, and calibration
and holdout outcomes were never opened. The final route is:

```text
FULL_REPLACEMENT_TRANSITION_TRAINING_MODEL_FAIL
```

This is a genuine frozen transition-model/design failure, not a runtime,
deployment, restart, causality, corruption, statistics/reporting, real-MPC,
closed-loop-control, or plant-unreachability result. The 158/600 formal count
is diagnostic identification-trajectory behavior, not an MPC result. All
D1R11 probe raw is forbidden from expert datasets. Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R11_FORENSIC_REPORT.md
```

D1R11 is immutable and may not resume with a changed model. Its unopened
calibration and holdout phases may not be consumed by a post-result redesign.
The active task is a new-identity, zero-new-TSC causal transition-architecture
study using only the 600 authenticated D1R11 training trajectories as
development data. It must retain whole-pair outer validation, the original
`0.1` recursive point-error gate, tube caps, forbidden-input semantics,
action/current gates, and immutable formal timing. A stable kinematically
consistent innovation/state-space model with causal online context adaptation
must first pass deterministic independent leave-pair replay before any fresh
calibration/holdout campaign can be preregistered. Real MPC, expert data, BC,
DAgger, and bounded residual RL remain blocked.

## 60. Final D1R12 result and active D1R13 safety sentinel

D1R12 consumed only the 600 already-open D1R11 training trajectories and ran
zero Ray, `gotsc`, TSC, controller, or plant tasks. Its stable causal
innovation-state-space discriminator excluded phase/manifold, labels,
coil/wire currents, future measurements, and future executed actions; used
only the authentic visible prefix, past issued commands, completed causal
calibration coordinates, numeric targets, clock, and already revealed
requested coordinates; enforced exact R/Z kinematics; and projected the
dynamic transition to frozen spectral-radius caps.

All 54 deterministic candidates failed the unchanged gates:

```text
training raw / whole-pair folds                    600 / 12
point-gate candidates                                0 / 54
tube-cap candidates                                  0 / 54
best maximum recursive scaled error          0.8323055840
unchanged point limit                                 0.1
forbidden / future action / future measurement inputs 0 / 0 / 0
new raw / TSC / plant steps                            0 / 0 / 0
route
  STABLE_CAUSAL_INNOVATION_STATE_SPACE_DEVELOPMENT_FAIL_DECONFOUNDED_IDENTIFICATION_REQUIRED
```

Supporting development diagnostics found that simple baseline extrapolation,
causal GRU/kNN models, causal response decomposition, and even a deliberately
forbidden actual-future-action oracle also failed. D1R11's future absolute
trajectory confounds authentic plant response with evolving R17 feedback and
online Card15 centers. This is a transition-target/architecture design
failure, not a runtime, restart, report, real-MPC, control, or plant-
unreachability conclusion.

Exact report and compact evidence:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R12_CAUSAL_ARCHITECTURE_FORENSIC_REPORT.md

docs/codex/audits/stage4_2r3c3t13s24d1r12_20260804/
d1r12_stable_innovation_probe_v1_compact.json
```

The active task is the separately frozen eight-case D1R13 authentic
zero-increment deconfounding safety sentinel:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R13_ZERO_INCREMENT_DECONFOUNDING_SENTINEL_DESIGN.md
```

D1R13 must reproduce each selected D1R11 baseline's physical state/action/
trace prefix through state 10, then apply exactly zero 14-coil current
increment through the unchanged 35/37-state formal horizon. Its eight cases
cover prefix 5/9, both hidden histories, zero/shifted targets, and normal/weak
slew. Formal tracking is diagnostic only. A pass authorizes only prospective
design of a separate bounded zero-baseline excitation sentinel. Transition
model fitting, MPC, expert data, BC, DAgger, and bounded residual RL remain
blocked.

## 61. Final D1R13 result and active D1R14 safety/geometry sentinel

D1R13 completed all eight fresh authentic TSC/controller trajectories from
execution-package checkpoint `df3910f`. The primary result and independent
server-side raw/snapshot audit agree:

```text
strict raw / exact identity / fresh controller / fresh TSC       8 / 8 each
restart snapshot / state-0 / physical source prefix              8 / 8 each
source action / controller trace / calibration                   8 / 8 each
full 35/37-state horizon                                         8 / 8
post-prefix actions                                      208 / 208 exact zero
post-prefix coil-current increments                              8 / 8 exact zero
finite R/Z/Ip / coil / wire-current records                      8 / 8 each
runtime / plant / solver / saturation / clipping errors               0
forbidden input / raw / snapshot / report errors                      0
maximum current utilization                                          0.3904
formal tracking diagnostic                                            2 / 8
route
  ZERO_INCREMENT_DECONFOUNDING_SENTINEL_PASS_EXCITATION_SENTINEL_DESIGN_REQUIRED
```

The remote raw inventory is 8 files and 241,738 bytes with digest
`f9b4dd9259736ebe2d26f9fcfd06bb0497be69a886de7ecc8d359009992f1c0a`.
Large raw and snapshots remain server-side. Exact report and compact evidence:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R13_FORENSIC_REPORT.md

docs/codex/audits/
stage4_2r3c3t13s24d1r13_20260804_df3910f/
```

The accepted run had no runtime, restart, corruption, statistics/reporting,
solver, plant-abnormality, action, current, or forbidden-input error. The
formal 2/8 is a real zero-increment tracking diagnostic, not a sentinel
failure and not control success. D1R13 proves only finite safe zero-increment
evolution in this fixed eight-case clean-source envelope.

Read-only server design evidence found that existing D1R11 signed sequences
cannot be relabelled as zero-baseline response trajectories. Continuing R17
feedback and evolving Card15 centers produced maximum old-feedback even/odd
ratio `14.0321503`, matched-history relative odd difference `0.5221102`,
zero-versus-R17 divergence `2.6781085`, zero natural drift `1.3010891`, and
selected R17 post-state-10 action `0.3652533`.

The active task is prospectively frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14_ZERO_BASELINE_SIGNED_EXCITATION_SENTINEL_DESIGN.md
```

D1R14 fixes 72 fresh authentic trajectories over the same eight contexts:
one fresh zero baseline plus four fixed physical directions times two signs
per context. Steps 0--9 reproduce the source prefix; every signed probe issues
one exact-Card15 coordinate at step 10, restores the stored center at step 11,
and commands exact zero afterward. Safety/prefix/full-horizon gates are
mandatory before frozen odd-signal, even/odd, rank-four, and condition-at-most
20 geometry gates are considered. Formal tracking remains diagnostic.

A D1R14 pass authorizes only a separately frozen time-distributed
zero-baseline identification design. It does not authorize that campaign,
transition-model fitting, MPC, expert data, BC, DAgger, or bounded residual
RL. All remaining restart/history/target/continuous-parameter/noise/
disturbance/long-hold gates remain unchanged.

## 62. D1R14 v1 issue-gate result and v2 hotfix

D1R14 v1 package checkpoint `2d5304c` completed 72/72 strict raw. The eight
zero baselines reached the full 35/37-state horizon, but all 64 signed probes
stopped safely before the task-step-10 plant advance. Primary and independent
server-side recomputation found:

```text
strict raw / exact restart and source prefix                 72 / 72
fresh zero baselines reaching the full horizon                 8 / 8
signed probe issue constructions attempted                    64 / 64
signed issue actions actually applied                           0 / 64
runtime / plant / solver / raw / snapshot / report errors            0
exact Card15 target reproduction / actuator gate              64 / 64
incremental / total action and current safety gates            64 / 64
maximum attempted incremental normalized action        0.0518518519
maximum predicted current utilization                         0.37705
```

The controller accidentally reused S24 dense-four-active-coordinate geometry
predicates. The D1R14 one-hot request has three deliberately zero coordinates,
so `min(abs(all four coordinates)) >= 0.18` and four-coordinate sign equality
were structurally impossible. They failed 64/64 before TSC could receive the
otherwise safe action. Dense-row cosine and off-basis predicates also failed
32/64 and 48/64, respectively, but were never part of the preregistered D1R14
one-hot action-safety contract.

The v1 raw inventory is 72 files, 1,841,053 bytes, digest
`bf07f39c4b83666a48f545d89ab4c7cff18f6ef473a89133b7afd99fd34321df`.
Its primary final SHA is
`bfd8c88705f8bea138adc36a42d576c472b56b79e44f081a4bbd241e2720a908`;
the independent audit SHA is
`3a6958c2519da4d43e0d910a51d33c0c971352e01a2f68578c1bc4b6b6750e2b`.

This is a controller issue-gate integration bug, not a runtime, restart,
plant, response-geometry, control, or MPC conclusion. The exact audit and
prospective v2 gate boundary are frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14_V1_ISSUE_GATE_HOTFIX_AUDIT.md
```

The v1 run may not resume because the controller source fingerprint changes.
Controller/package revision v2 repeated all 72 trajectories with a fresh run
identity while preserving the requested coordinates, exact Card15
construction, physical actions, timing, task matrix, action/current bounds,
response geometry, and scientific scope.

## 63. Final D1R14 v2 result and active D1R14R1 preflight

D1R14 v2 package checkpoint `d32761c` completed all 72 authentic TSC tasks.
Primary and independent server-side audits found 72/72 strict raw, exact
restart/source prefixes, safety and finite rows; 8/8 zero-baseline
reproductions; 64/64 exact issue and stored-center cancellation actions; and
zero runtime, plant, solver, saturation, clipping, action-safety, forbidden-
input, raw, snapshot, or reporting errors. Maximum current utilization was
`0.3904`. The raw inventory is 72 files, 2,239,479 bytes, digest
`0433a64ebaea73186bb193d5102686721497219acfcbecbb721e7fad62e8d7a3`.

The frozen response geometry failed: signal 24/32, symmetry 27/32, rank 8/8,
condition 7/8, minimum odd peak `0.0005766750`, maximum even/odd ratio
`0.7567864`, and maximum condition number `20.5851685`. The isolated coil-8
direction failed the signal floor in every context. The final route is
`ZERO_BASELINE_EXCITATION_GEOMETRY_FAIL_REDESIGN_REQUIRED`.

This is a genuine excitation/response-geometry design failure, not a runtime,
restart, plant, corruption, reporting, formal-control, or real-MPC failure.
Formal tracking 18/72 remains diagnostic only. Full evidence and
classification are frozen in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R14_FORENSIC_REPORT.md`.

The active task is D1R14R1, a separately preregistered zero-new-TSC
pooled-whitened amplified mixed-basis recomputation and exact static Card15
issue preflight. It must authenticate and consume only the immutable D1R14 v2
development raw, reproduce the deterministic basis and matrix digest, and
prove every proposed issue action against the unchanged incremental/total/
current gates. Cancellation safety remains only a linearized diagnostic until
a new real sentinel. An R1 pass authorizes only design and execution of a
fresh D1R14R2 safety/geometry sentinel. MPC, expert data, BC, DAgger, and
bounded residual RL remain blocked.

## 64. Final D1R14R1 result and active D1R14R1A preflight

D1R14R1 package `36f0d41` executed the frozen zero-new-TSC audit. It
authenticated 72/72 D1R14 v2 raw and reproduced the official source geometry
exactly. The seed-140042, 60,000-candidate search selected candidate 35377 and
passed its predicted gates: minimum odd peak `0.006` and maximum condition
`3.7020780`.

The exact static Card15 gate passed only 48/64. All 16 failures were mixed
direction 2, both signs in all eight contexts, and the only failed predicate
was relative off-basis residual: maximum `0.1359745` versus the unchanged
`0.10` cap. Exact target reproduction, action/current/saturation/clipping,
cosine, and actuator gates all passed; maximum issue and linearized cancel
were `0.1161111`. The final route is
`POOLED_MIXED_BASIS_PREFLIGHT_FAIL_REDESIGN_REQUIRED`.

This is a prospective basis quantization-margin design failure, not runtime,
reporting, restart, plant, control, or MPC failure. New raw, controller,
plant, Ray, gotsc, and TSC counts were zero. The exact report is
`docs/codex/reports/STAGE4_2R3C3T13S24D1R14R1_FORENSIC_REPORT.md`.

A post-freeze development-only scale grid found that multiplying direction 2
by `1.275` is the first 0.025-grid value with 64/64 static passes; maximum
residual becomes `0.0990759` and maximum issue/idealized cancel becomes
`0.1401852`. This is not a validation pass. The active task is a separately
frozen D1R14R1A zero-TSC exact replay of that fixed candidate. Only R1A may
authorize a fresh D1R14R2 design. MPC, expert data, BC, DAgger, and bounded
residual RL remain blocked.

## 65. Final D1R14R1A result and active D1R14R2 design

D1R14R1A completed its frozen zero-new-TSC fixed-candidate replay from
implementation/package checkpoints `58912e7 / b8040b6`. It authenticated the
exact D1R14R1 failure boundary and all 72 immutable D1R14 v2 raw files in
place. It regenerated the matrix by scaling only column 2 by `1.275` and
matched digest:

```text
c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
```

Independent row-level compact recomputation found:

```text
contexts / signed constructions                              8 / 64
all exact static issue gates                                64 / 64
predicted minimum odd peak                      0.005999999999999252
predicted maximum unit-column condition                3.7020780012
maximum off-basis residual                            0.0990759019
maximum issue / linearized cancel increment           0.1401851852
minimum desired/applied cosine                        0.9945784028
maximum predicted current utilization                         0.38005
new raw / TSC / controller / plant steps                 all zero
route  QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED
```

This is a finite development-selected static construction PASS. It does not
validate state-11 online cancellation, plant response, symmetry, transition
model, controller, MPC, robustness, or formal tracking. Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R1A_FORENSIC_REPORT.md
```

The active task is to prospectively freeze and independently implement
Stage4.2R3c3T13S24D1R14R2. Its maximum matrix is the same eight contexts with
one fresh zero baseline and four fixed mixed directions times two signs per
context, for 72 fresh authentic TSC/controller rollouts. It must reproduce
the exact source prefix through state 10, apply the fixed issue at task step
10, causally restore the stored center at task step 11 under both the 0.24
online margin and original 0.25 cap, and command exact zero to the unchanged
35/37-state horizon.

All restart, causal trace, Card15, action/current, saturation/clipping,
forbidden-input, raw, snapshot, and complete-log gates precede the original
D1R14 signal/symmetry/rank-four/condition-at-most-20 geometry gates. Formal
tracking remains diagnostic. A D1R14R2 pass may authorize only a separately
frozen time-distributed zero-baseline identification design. Transition-model
fitting, MPC, expert data, BC, DAgger, and bounded residual RL remain blocked.

## 66. D1R14R2 implementation checkpoint pending package

The prospective D1R14R2 design is frozen at design hash
`5344a7436277c18d3a85a750d5516c69595c6d84090d47f9cc01af85b888896a`.
The completed local implementation uses the exact R1A matrix digest
`c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c`,
re-authenticates R1A plus the complete D1R13/D1R11/snapshot source closure,
and fails resume/postprocess closed on any package, source, spec, or state
fingerprint change. The structurally separate forensic tool authenticates R1A
and reconstructs all 72 raw/snapshot/action/geometry gates independently.

Local validation before package construction is:

```text
all repository JSON                                      503 parsed
compileall                                                passed
focused D1R14R2 tests                                    15 / 15
complete repository tests                             1072 / 1072
real TSC executed                                              no
```

The next actions are package/manifest construction, empty-directory deployment
simulation, installed-server validation, a zero-plant 72-spec offline gate,
then one fresh 72-task authentic TSC campaign. No response result has yet been
observed. MPC, expert data, BC, DAgger, and bounded residual RL remain blocked.

## 67. Final D1R14R2 result and active sign-split redesign

D1R14R2 implementation/package checkpoints are `e7fe6c8 / ca2815a`. The
installed 543-file package, mandatory zero-TSC source/spec gate, 72 authentic
TSC tasks, primary postprocessor, and independent raw/snapshot audit all
completed. Raw inventory is 72 files, 2,254,876 bytes, digest
`c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649`.

Exact safety/restart/causality results were 72/72, with 8/8 baseline
reproduction and 64/64 issue/cancellation. Runtime, prefix, plant, solver,
saturation, clipping, forbidden-input, snapshot, corruption, and reporting
error counts are zero. Maximum current utilization is `0.3904`. Formal
tracking 18/72 remains diagnostic.

The frozen geometry failed only central symmetry:

```text
signal                                            32 / 32
central symmetry                                  28 / 32
rank four                                           8 / 8
condition <= 20                                     8 / 8
minimum odd peak                       0.005466000000009519
maximum even/odd                       0.8528017842241936
maximum condition                     8.802962394477525
route  MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED
```

All four failures are in the two hidden histories of
`p9_q2_a0p900_gap3_settle4`. Raw reconstruction found the actual positive and
negative issue coordinates and physical field deltas exactly antipodal for
32/32 pairs. The residual even response is therefore genuine late-time
context/sign dependence, not asymmetric quantization or an action bug.

A labelled posthoc architecture diagnostic leaves the R2 verdict unchanged.
When positive and negative response branches are kept separate, all 16
context/sign branches have four-direction signal at least
`0.005310999999896815`, rank 4, and condition at most `9.55784063525667`.
This motivates, but does not pass, a sign-split model architecture.

Exact report and compact evidence are in:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R2_FORENSIC_REPORT.md
docs/codex/audits/stage4_2r3c3t13s24d1r14r2_20260804_ca2815a/
```

The active task is a prospectively frozen zero-new-TSC sign-split response
feasibility audit. It must authenticate every D1R14R2 raw/snapshot/output,
reproduce the R2 symmetry FAIL without changing it, and test fixed
positive/negative four-direction authority. Only a pass may authorize design
of a fresh time-shifted safety/identification campaign. Model fitting, MPC,
expert data, BC, DAgger, and bounded residual RL remain blocked.

## 68. Final D1R14R3 result and active D1R14R4 design

D1R14R3 design/implementation/final-package checkpoints are
`343a516 / aa3325a / ca49a36`. It created no new raw and executed no
controller, plant, Ray, gotsc, or TSC. Both server-side implementations
strictly re-read all 72 immutable R2 raw files and repeated the complete
source/restart/snapshot/action/safety audit.

The initial package correctly stopped at `SOURCE_FAIL_NO_TSC` because the R2
state-file expected SHA had been transcribed incorrectly. The authentic hash
was already committed in the pre-R3 compact inventory. A separately recorded
source-fingerprint erratum changed only that expected SHA; v1 remains frozen,
and corrected v2 used a fresh output directory.

R2's shared odd-model failure was reproduced exactly at 28/32 symmetry with
four unchanged failed pairs. The different fixed sign-split architecture
passed: signal 64/64, rank four 16/16, condition at most 20 for 16/16, exact
opposite issued coordinates/physical fields 32/32, minimum direction peak
`0.005310999999896815`, and maximum condition `9.55784063525667`. Primary and
independent outputs agree exactly. Route:

```text
SIGN_SPLIT_RESPONSE_FEASIBILITY_PASS_TIME_SHIFT_SENTINEL_DESIGN_REQUIRED
```

This is only finite single-time local branch feasibility. The active task is
to prospectively freeze Stage4.2R3c3T13S24D1R14R4, a fresh authentic
time-shifted sign-split safety/identification sentinel. It must validate
independently cancelled responses at fixed earlier/later issue times before
any model fit or MPC. Expert data, BC, DAgger, and bounded residual RL remain
blocked.

## 69. Final D1R14R4 result and active D1R14R5 preflight

D1R14R4 design/implementation/final-package checkpoints are
`ea49eac / d27993b / f5b8348`. Its 200 authentic TSC tasks completed 200/200
with strict raw parse, safety, finite full-horizon trajectories, exact source
state/action/trace prefixes, and causal stored-center issue/cancellation.
Runtime, restart, plant, solver, saturation/clipping, forbidden-input,
raw/snapshot, and reporting error counts are zero. Maximum current utilization
is `0.3904`; formal tracking 50/200 is diagnostic only.

The primary and structurally independent audits agree exactly. Signal passed
254/256, rank four 64/64, condition at most 20 for 64/64, and exact issue
coordinate/physical-field antipodality 128/128. The only failures are both
signs of `pooled_mixed_0` at issue step 18 for
`p9_q2_a0p750_gap4_settle4 / minus_first`, with peaks `0.004465` and
`0.004298` below the unchanged `0.005` floor. Maximum condition is
`11.5700741087`. This is a genuine local response-signal design failure, not
a runtime, restart, corruption, report, control, or MPC failure. Route:

```text
TIME_SHIFTED_SIGN_SPLIT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED
```

The 200 raw files remain server-side: 6,285,765 bytes, inventory digest
`44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9`.
Compact evidence and the exact report are:

```text
docs/codex/audits/stage4_2r3c3t13s24d1r14r4_20260804_f5b8348/
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R4_FORENSIC_REPORT.md
```

R4 is immutable and may not resume. The active task is the prospectively
frozen zero-new-TSC D1R14R5 global direction-0 gain preflight in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R14R5_GLOBAL_DIRECTION0_GAIN_PREFLIGHT_DESIGN.md`.
The frozen design-document SHA-256 is
`8383ef5e0cf7678adcf9f3c776fbe925e7b57b8e6e9398eae13bff35e1f5b400`.
It fixes one global candidate, column 0 times `1.5`, with matrix digest
`69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8`,
and tests all 8 contexts, issue times 14/18/22, and both signs using only
authenticated zero-baseline current centers. A pass may authorize only a
separately frozen 48-probe real-TSC sentinel. Model fitting, MPC, expert data,
BC, DAgger, and bounded residual RL remain blocked.

## 70. Final D1R14R5 result and active D1R14R6 design

D1R14R5 final implementation/package checkpoints are `e7b550a / a4c43bb`.
It created no new raw and executed no controller, plant step, Ray, gotsc, or
TSC. Both final implementations authenticated all 200 R4 raw and 72 R2 raw,
reproduced the exact R4 failure geometry, and evaluated the one frozen global
column-0 `1.5x` candidate.

The exact static result passed:

```text
candidate matrix digest
  69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8
signed issue constructions                                  48/48
exact coordinate/field antipodal pairs                       24/24
maximum issue increment                         0.17481481481481495
maximum ideal return increment                  0.17481481481481495
maximum predicted current utilization                        0.3799
maximum relative off-basis residual              0.05794563546539851
route  GLOBAL_DIRECTION0_GAIN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

The initial launcher and report-comparison failures are preserved and
classified as environment/reporting bugs. They changed no action, experiment
identity, threshold, or raw and ran no plant step. The passing primary output
was preserved; only the structurally independent audit resumed after the
comparison hotfix. Exact report and compact evidence:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R5_FORENSIC_REPORT.md
docs/codex/audits/stage4_2r3c3t13s24d1r14r5_20260804_a4c43bb/
```

R5 proves only finite static exact issue/ideal-return safety. Real online
cancellation, plant response, model, MPC, formal control, and robustness are
unvalidated.

The active task is the prospectively frozen D1R14R6 fresh authentic 48-probe
direction-0 replacement sentinel. Its design SHA-256 is
`aa59b97868ae74b9a7e5d19e76f5541b3d5ed36dc5c75cc57ddd839d535a9b5b`.
It replaces only direction 0 at issue steps 14/18/22 and combines those raw
with immutable R2 step-10 and R4 directions 1--3. Only a full 256/256 signal,
64/64 rank/condition, 128/128 issue-antipodality result after 48/48 safety may
authorize a separately frozen transition-model fit. MPC, expert data, BC,
DAgger, and bounded residual RL remain blocked.

## 71. Final D1R14R6 result and active causal response-model design

D1R14R6 final package checkpoint is `1e62c2c`. Its first official offline
invocation exposed an R1A-versus-R5 expected-matrix authentication bug before
any stage directory, raw, controller, Ray, gotsc, TSC, or plant execution.
The corrected fresh run preserved all experiment semantics and completed
48/48 authentic trajectories.

Primary and independent server-side raw/snapshot recomputation agree:

```text
strict raw / safety / full horizon                         48 / 48 each
source prefix / exact R4 issue state                       48 / 48 each
exact issue / causal stored-center cancellation             48 / 48 each
runtime / plant / solver / action / raw / report errors              0
R6 direction-0 signal                                      48 / 48
combined R2/R4/R6 signal                                  256 / 256
combined rank four / condition <= 20                        64 / 64
combined issue coordinate/field antipodality              128 / 128
minimum R6 / combined signal             0.0068060000 / 0.0051890000
maximum combined condition                            12.1210121871
raw count / bytes                                      48 / 1,509,679
raw digest
  c743eff98395325e4da35a28d2e646aacffb00e678753ceb0faf4b86a64aeb83
route  DIRECTION0_REPLACEMENT_SENTINEL_PASS_MODEL_FIT_DESIGN_REQUIRED
```

Formal tracking 12/48 is diagnostic only. R6 proves a finite authentic,
causal, safe, signal-bearing and conditioned response bank; it does not prove
a transition model, MPC, formal control, robustness, or reliable expert.
All R2/R4/R6 probe trajectories remain forbidden from expert datasets.
Exact report and compact evidence:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R6_FORENSIC_REPORT.md
docs/codex/audits/
stage4_2r3c3t13s24d1r14r6_20260804_1e62c2c/
```

The active task is a separately prospectively frozen, zero-new-TSC causal
response-model fit and held validation over the authenticated R2/R4/R6 bank.
It must model deconfounded increments about the matched zero baselines, keep
issue time and sign explicit, and validate by whole hidden-history groups.
Predictors may use only causally visible state/action history, numeric target,
clock, and already revealed fixed request. Pair/history/prefix labels, source
outcomes, current-run future values, coil/wire hidden-current files, and
future actions/measurements remain forbidden. D1R11/D1R12's failed absolute
future closed-loop trajectory target may not be revived under a new name.

This stage must freeze its candidate grid, folds, error/tube gates, and
independent replay before inspecting results. A pass may authorize only a
separate robust finite-horizon MPC feasibility design. Real MPC execution,
expert data, BC, DAgger, bounded residual RL, and every remaining robustness
gate remain blocked.

## 72. D1R14R7 structural stop, final D1R14R7R1 result, and active R7R2

D1R14R7 final installed package `5a17fe0` authenticated all R2/R4/R6
sources, then stopped before output/model because an inner fold trained only
through lag 25 while its held weak pair required lags 26/27. No prospective
tail rule existed. This is a frozen model-architecture coverage failure; no
raw, controller, Ray, `gotsc`, TSC, plant step, or model result was created.

D1R14R7R1 design/implementation/package checkpoints are
`81552da / 8087a1c / 3c90f21`. Its continuous Legendre lag tensor repaired the
undefined tail and completed every nested fold over the exact 256-response
bank. Primary and independent server-side implementations agreed within the
frozen tolerance. The result failed unchanged center gates:

```text
response rows / all-gate passes                         256 / 150
relative-L2 / cosine / peak-ratio passes          206 / 161 / 196
finite / point-error passes                        256 / 256 each
tube cap                                                     PASS
worst relative L2                                    2.8666592379
minimum cosine                                       0.1899193709
peak-ratio range                          0.1601688053--3.2735052329
predicted signal / rank / condition         256/256 / 64/64 / 64/64
maximum condition                                    15.4034595026
new raw / controller / plant / TSC                       all zero
route
  CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_FAIL_BROADER_DECONFOUNDED_IDENTIFICATION_REQUIRED
```

There were no runtime, package, source-authentication, corruption,
statistics, or reporting errors. This is a causal response-center design
failure and gives no real controller, restart, plant, or MPC conclusion.
Full detailed/independent outputs remain server-side; compact evidence and
the exact report are:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r7r1_20260804_3c90f21/
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R7R1_FORENSIC_REPORT.md
```

Retrospective diagnostics are not validation. They found exact 1.0x/1.5x
direction-zero request pairs with median linear-scaling error `0.1001449319`
but maximum `0.8482887417`, and the best original-R7 nonlinear-kernel tail
screen reached only 218/256. Thus request magnitude, nonlinear context, and
more complete causal history all matter; a global amplitude correction alone
does not pass.

The active task is prospectively frozen before implementation in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R7R2_ACTION_CONDITIONED_FULL_HISTORY_KERNEL_DESIGN.md
```

R7R2 authenticates all 320 immutable source raw and uses the full 304-response
R2/R4/R6 amplitude-paired bank. It adds only the complete current-run visible
history and already revealed request scale, retains whole-pair nested
validation and all unchanged response/tube/formal gates, and uses a fixed
nonlinear per-lag kernel plus causal lag-26/27 tail. A pass may authorize only
fresh authentic multi-pulse validation. A fail requires a new broader
deconfounded identification campaign. MPC, expert data, BC, DAgger, bounded
residual RL, and all later robustness claims remain blocked.

## 73. Final D1R14R7R2 result and active D1R14R8 design

D1R14R7R2 design/implementation/package checkpoints are
`5d35db2 / bcde159 / 995d81c`. The 898-file direct-copy package passed local
empty-directory, staging, and installed hashes plus the complete 1,136-test
suite. It used only the project/server virtual environments and ran no
controller, Ray, `gotsc`, TSC, or plant step.

Both final implementations authenticated all 320 immutable R2/R4/R6 raw,
reconstructed the exact 304-response bank, and agreed on every nested
whole-pair prediction and route:

```text
all response gates                                      236 / 304
relative-L2 / cosine / peak-ratio               253 / 247 / 267
finite / point-error                               304 / 304 each
tube cap                                                    PASS
worst relative L2                                   1.5695004725
minimum cosine                                      0.2450755612
peak-ratio range                         0.2516766914--2.3254004095
predicted signal                                          304 / 304
canonical / operational geometry                     64/64 / 64/64
route
  ACTION_CONDITIONED_FULL_HISTORY_MODEL_FAIL_NEW_IDENTIFICATION_REQUIRED
```

The failure is pair-dependent: the four pair pass counts are `68/76`,
`70/76`, `54/76`, and `44/76`, while signs are exactly balanced at `118/152`
each. Point error, tube, and predicted authority passed. This is a genuine
causal response-center whole-pair generalization failure, not runtime,
deployment, source, raw/snapshot, statistics, reporting, restart, control,
plant-unreachability, or real-MPC evidence. Full row outputs remain
server-side; compact evidence and exact report are:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r7r2_20260804_995d81c/
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R7R2_FORENSIC_REPORT.md
```

The active R8 design is frozen prospectively in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8_PARTITIONED_BROAD_RESPONSE_IDENTIFICATION_DESIGN.md
SHA-256
  c225c6163fbf2146772fdabf100a34b13a3c6d59ee416f605698598acdc2022f
```

This final pre-implementation hash includes the explicit Phase-0 boundary:
offline checks validate static Card15 algorithm/configuration representability,
while the physically realized issue/cancel margins at later states are hard
gates only after each fresh baseline creates those causal centers.

It authenticates the fixed D1R11 20-pair table and confirms that D1R11 opened
only training raw (`600/600`), with calibration `0/200`, holdout `0/200`, and
`heldout_outcomes_opened=false`. R8 retains the four consumed R2/R4/R6 pairs
as training-only, adds the other eight fixed training pairs, freezes a model
before four fresh calibration pairs, freezes a tube before four fresh holdout
pairs, and may execute at most 1,248 new authentic rollouts. Any earlier gate
failure stops later partitions unopened.

An R8 pass may authorize only a separately frozen fresh multipulse
superposition/interaction sentinel. MPC, expert data, BC, DAgger, bounded
residual RL, unseen targets, continuous plant/actuator variation, noise,
disturbance recovery, and long hold remain blocked.

## 74. Final D1R14R8 result and active short-horizon route discriminator

D1R14R8 executed 624/624 fresh authentic training-extension rollouts and
stopped before calibration or holdout. Primary and independent raw audits
agree on exact restart, source prefix, causal issue/cancel actions, finite
full horizons, 16/16 restart snapshots, zero runtime/solver/saturation/raw
errors, and maximum current utilization `0.392`. The raw inventory is
19,725,920 bytes with digest
`b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762`.

The frozen 912-response, twelve-whole-pair model result is:

```text
response rows passing all gates                       719 / 912
relative L2 / cosine / peak ratio              763 / 731 / 829
finite / point error                                  912 / 912
maximum relative L2                             1.5279087085521352
minimum cosine                                -0.16994497675301598
peak ratio                         0.17852411174023414--2.1303641273377756
maximum scaled point error                       0.05081135014313233
vR tube precursor                                  0.010162370028626466 m/s
predicted canonical / operational geometry              192/192 each
actual canonical / operational geometry                 192/192 each
route
  PARTITIONED_BROAD_RESPONSE_TRAINING_MODEL_FAIL_STOP
```

The final independent output has `passed=true`,
`scientific_gate_passed=false`, and exact primary numerical, outcome, and
model-artifact-presence agreement. Its SHA-256 is
`cfb4ad0aebc838045468e6dd9e5937007c06a07458a458f253a0dd411861cba0`.
No model file exists, `heldout_outcomes_opened=false`, and calibration and
holdout raw counts remain zero. Four repaired offline/reporting/audit-tool
defects changed no raw, controller action, experiment identity, formal gate,
or scientific metric. The exact report is:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8_FORENSIC_REPORT.md
```

R8 is immutable and may not resume with a changed model. The active task is
a new-identity, prospectively frozen, zero-new-TSC short-horizon response
discriminator using only the 912 already-opened training responses. It must
fix the R8-selected PCA4/bandwidth-2/ridge-0.1 candidate before evaluation,
retain whole-pair outer validation and every unchanged response/tube/signal/
geometry gate, and evaluate common relative-lag horizons 4, 6, 8, 10, and 12.
Only horizons 8, 10, and 12 are controller-useful route candidates; select
the largest fully passing horizon, while 4 and 6 are diagnostic only. No R8
calibration/holdout outcome may be opened. A pass authorizes only a separate
fresh authentic multipulse superposition/interaction sentinel; a fail routes
to causal online innovation/adaptation or new identification, not more
capacity in the failed long-horizon point-center kernel. MPC, expert data,
BC, DAgger, and bounded residual RL remain blocked.

## 75. Final D1R14R8R1 result and active causal-innovation design boundary

R8R1 authenticated the complete R2/R4/R6/R8 training bank and reconstructed
912 responses in twelve whole-pair outer folds. The primary completed
normally. After a focused independent state-path repair, the structurally
independent recomputation agreed exactly with every primary numerical result,
route, and model-artifact outcome. The accepted result is:

```text
relative-lag states / elapsed ms       4/40    6/60    8/80   10/100  12/120
all response gates                  832/912 804/912 788/912 770/912 763/912
controller-useful route candidate       no      no      yes      yes      yes
scientific gate                          FAIL    FAIL    FAIL     FAIL     FAIL
selected horizon                         none
route
  FIXED_CANDIDATE_SHORT_HORIZON_FAIL_CAUSAL_INNOVATION_REQUIRED
```

The 40 ms diagnostic alone passed the componentwise tube cap but failed
response and actual-condition gates. The 60--120 ms horizons retained
direction/relative-amplitude and vR-tube failures. Predicted signal and
geometry were intact. Shortening therefore does not make the fixed
cold-start point-center kernel controller-useful.

The accepted audit package is `892ac7c`; independent and final-state hashes
are respectively
`3f378dba6eb1304422397b44a347e34d35827624ca6ea61791e85f16e7a5341c`
and `3f25e7070fd56243b1581b7da17cb433e0876821437bc9e7e098cdf4626d869f`.
The postcheck strictly parsed all 624 R8 training raw. Calibration and
holdout remain unopened with zero raw. R8R1 ran zero Ray, `gotsc`, TSC,
controller, or plant advances and emitted no model.

The first independent `KeyError: 'state'` was an audit-tool path/runtime
defect, repaired without changing any raw, candidate, fold, horizon, gate, or
scientific result. R8R1 is final as a response-model/design FAIL, not a
restart, causality, raw, reporting, real-control, formal-control, real-MPC,
or plant-reachability failure. Its exact report is:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R1_FORENSIC_REPORT.md
```

R8R1 is immutable. Before any further result is computed, the next task
must prospectively freeze a new-identity causal online innovation/adaptation
study. It must use only causal observations available by each prediction
time, keep whole-pair separation, forbid source labels/future outcomes, and
distinguish deployable same-trajectory adaptation from retrospective paired-
baseline differencing. It may not tune another cold-start point-center
candidate after R8R1. A development pass can authorize only a separate
fresh authentic interaction sentinel; MPC, expert data, BC, DAgger, residual
RL, and Gate A remain blocked.

## 76. Frozen D1R14R8R2 causal online innovation/adaptation task

R8R2 is prospectively frozen before implementation or any R8R2 result in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R2_CAUSAL_ONLINE_INNOVATION_ADAPTATION_DESIGN.md
SHA-256
2613cd42b7b3a2e9c985c7ac1a9fd055fc20aa596e16add5a2e4c54cc8514dfe
```

It authenticates only the twelve already opened R8 training pairs and runs
zero new TSC. The matched no-action trajectory is evaluator-only. Every live
feature must be reconstructed from the same probe trajectory's causal visible
prefix, known issued action, fixed R8 candidate, and a fixed four-state affine
no-action forecast. It tests rolling eight-state/80 ms predictions after
update lags 2 and 4, with no origin shift or later formal deadline.

The fixed adapter is a recency-weighted vR/vZ/Ip innovation anchor with
`lambda in [0.0, 0.5, 0.8]`, selected only through nested whole-pair inner
validation. Future R/Z is anchored causally and integrated from the corrected
response velocity. Forbidden labels, source outcomes, matched future
baseline, and future probe values may not enter the predictor.

Hard deployability gates retain finite output, unchanged point/tube bounds,
nonnegative direction, bounded amplitude, signal, and rank/condition for all
912 rows. The prospectively relaxed practical gate requires at least 867/912
unchanged response-quality passes, at least 69/76 per pair and 34/38 per
context, at least 46-row improvement over the rolling cold comparator, and no
per-pair regression. The frozen no-action forecast must independently pass
all 96 future windows inside the unchanged physical component bounds.

The active task is to implement primary and structurally independent R8R2
postprocessors, validate/deploy them under the established package workflow,
and compute the zero-TSC result without opening R8 calibration or holdout.
A PASS authorizes only a separately frozen authentic interaction sentinel. A
FAIL routes to a new observer/identification design. Neither route authorizes
MPC, expert data, BC, DAgger, residual RL, or Gate A.

## 77. Final D1R14R8R2 result and active observer-identification boundary

R8R2 was implemented and evaluated under its prospective design without
opening any R8 calibration or holdout outcome.  Primary and structurally
independent recomputations authenticated all 912 existing training responses,
reconstructed every probe descriptor from its own causal prefix, used zero
forbidden or matched-future predictor inputs, and agreed within the frozen
tolerance.

The fixed four-state affine no-action forecast failed before any adaptive
update was fitted:

```text
baseline future windows                                  96
passing windows                                          17
issue-step pass counts
  task step 10                                         0/24
  task step 14                                         0/24
  task step 18                                        11/24
  task step 22                                         6/24
maximum scaled point error                   25.23346999999822
R / Z / vR / vZ / Ip cap violations       20 / 31 / 61 / 72 / 0
outer update folds                                        0
selected update lag                                    none
development artifact                                 absent
route
  CAUSAL_ONLINE_INNOVATION_BASELINE_FORECAST_FAIL_OBSERVER_IDENTIFICATION_REQUIRED
```

Both history signs and all twelve physical pairs failed broadly.  Ip was not
limiting; visible velocity extrapolation dominated the failure, with maximum
vR/vZ errors `0.2523346999999822 / 0.1729267443999999 m/s`.  This rejects the
fixed four-point affine trend as a deployable no-action dynamics observer. It
does not evaluate or reject the frozen online innovation update itself,
because that stage was never reached.

Accepted detailed, summary, independent, and final-state SHA-256 values are:

```text
ad04374987ce4de599d71f4673ac110fe763928831e4c9610cdb117efd7977cf
05d761ef64c9e7c2373a6754184ecf42cf0a250d26ee235293e768c0416c0bb2
2ca90fab851c4131f7242bd9a5331286bde15ccaf47d251348b7d80a4597066c
ee06726c8a5170ffd03a9465432ceed6f42053e2db8f710442c80c7809f07670
```

Local full tests and the accepted v3 installed server suite passed 1165/1165
with one expected server-side isolated-data skip.  Two preserved pre-result
deployment defects changed no scientific result: generated `.pyc` files in
the first staging copy, then an absolute-path `cp --parents` invocation.  The
fresh v3 package passed all 930 hashes and authenticated the task-created
930-file wrong-path mirror before removing it.  The exact report is:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R2_FORENSIC_REPORT.md
```

R8R2 created zero raw and ran zero Ray, `gotsc`, TSC, controller, or plant
advances.  It is a causal baseline-forecast/observer-design FAIL, not a
runtime, deployment, restart, causality, raw, reporting, controller,
formal-control, real-MPC, or plant-reachability failure.

R8R2 is immutable.  The next task must be frozen under a new identity before
any new metric is computed.  It must identify and validate a deployable
causal dynamics observer from allowed visible histories and already issued
actions/currents, with whole-pair separation and no future closed-loop action,
matched-baseline future, source label, hidden state, or heldout outcome used
as predictor input.  A development observer pass may authorize only a
separately frozen combination with the R8R2 innovation architecture; it does
not authorize a controller, real MPC, expert data, BC, DAgger, residual RL,
or Gate A.

## 78. Frozen D1R14R8R3 causal history no-action observer task

R8R3 is prospectively frozen after final R8R2 evidence, but before any R8R3
feature matrix, fit, cross-validated prediction, observer metric, route, or
artifact, in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R3_CAUSAL_HISTORY_NO_ACTION_OBSERVER_DESIGN.md
SHA-256
c55130a41f6522259d6fe9073686f0c86226c7dc11be7e93607b63f0abd0dfcb
```

It authenticates only already opened R8 training evidence and creates zero
new raw.  A structure-only server read made before freezing the design and
without fitting or scoring an observer established the exact source shape:
12 physical pairs, 24 history contexts, 96 prescribed issue windows,
baseline visible lengths 36/38, and 360 eligible origins with ten causal
history steps and twelve future target steps.

The deployable 353-dimensional input at each origin is fixed to eleven
visible states, ten already issued 14-coil normalized actions, eleven measured
14-coil applied-current states through the origin, three numeric user target
offsets, and one relative task clock.  Pair/history/source/regime labels,
wire currents, matched future, future measurements, future current/action,
and outcomes are forbidden.  Every one of the 912 probe issue features must
be reconstructed from its own prefix, with matched-baseline equality used
only as an audit assertion.

The model predicts twelve direct future changes in vR/vZ/Ip and reconstructs
R/Z kinematically.  Its fixed 48 candidates combine PCA ranks 8/16/24/32
with prospectively declared linear or RBF kernels and fixed ridge/bandwidth
grids.  Twelve outer whole-pair folds use only inner whole-pair validation for
candidate selection and fold-local tubes.  All 360 outer rows, including all
96 prescribed issue rows, must satisfy every unchanged component cap; every
row must also be contained by a finite fold-local tube whose half-widths stay
inside those caps.  No aggregate exception can turn a miss into a pass.

The active task is to implement primary and structurally independent R8R3
audits, validate and directly deploy them under the repository package
workflow, and compute the zero-TSC result without opening R8 calibration or
holdout.  A PASS authorizes only a separately frozen combination with the
R8R2 innovation architecture.  A FAIL requires a new-identity fresh causal
observer-identification design.  Neither route authorizes a controller, MPC,
expert data, BC, DAgger, residual RL, or Gate A.

## 79. Final D1R14R8R3 result and active fresh-identification boundary

R8R3 was implemented and evaluated under its prospective design with no new
raw and without opening R8 calibration or holdout. Primary and structurally
independent implementations separately rebuilt all source authentication,
360 causal origin rows, 912 own-prefix probe features, 48-candidate nested
whole-pair selection, fold-local tubes, metrics, and route. They agree within
the frozen tolerance.

```text
outer folds                                             12
origin rows / component-cap passes                 360 / 346
prescribed issue rows / passes                       96 / 89
tube-cap folds                                         0 / 12
held rows contained by fold-local tubes             360 / 360
R / Z / vR / vZ / Ip violations                 0 / 0 / 22 / 8 / 0
maximum physical error
  R / Z                          0.00102411 / 0.00082837 m
  vR / vZ                        0.01387848 / 0.01076855 m/s
  Ip                                           36.83328 A
route
  CAUSAL_HISTORY_NO_ACTION_OBSERVER_FAIL_FRESH_IDENTIFICATION_REQUIRED
```

All point violations occurred at future lags 9--12. Prescribed origins
10/14/18/22 passed `18/24, 24/24, 23/24, 24/24`. All twelve fold-local tubes
exceeded both velocity caps; worst vR/vZ cap ratios were 4.3145/2.1904. Every
selected candidate used the maximum frozen PCA rank 32. No observer artifact
was emitted.

Accepted detailed, summary, independent, and state SHA-256 values are:

```text
a0db5c6db2687747ffd5de8a4a773635bfce15973e8e817eebe74a3356470a00
b8992e53a07e339015dc714377fcca57860dac3cb7b4b169d67e3623b520e364
4cb71b25ad69848349a2034fff335b9d869a56f709465be9baed6b209637f8ba
e016c0ab9ee2c7a2f4701e553733c4392f48026f648450408cca4e19df9a9bcb
```

Local, staging, and installed full suites passed 1176/1176; server suites had
one expected skip. Direct-copy package closure was 939 declared files plus
manifest/sums. Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R3_FORENSIC_REPORT.md
SHA-256
e7d1efef0aaf227c828fe0653a8229a0444088453c0499244f26b0761aae9ad3
```

R8R3 is a finite observer/model/data-coverage design failure, not a runtime,
deployment, restart, causality, raw, controller, formal-control, real-MPC,
plant, or reachability result. It created zero raw and ran zero Ray, `gotsc`,
TSC, controller, or plant advances.

R8R3 is immutable. Before any new fit, metric, or TSC, freeze a new-identity
fresh causal observer-identification campaign. It may preregister a practical
finite qualification consistent with the 2026-08-06 application policy, but
only on genuinely fresh development/holdout evidence and without relabeling
R8R3 or weakening hard safety, causality, restart, integrity, or formal
timing. A future observer pass can authorize only a separately frozen combined
adaptation validation. Controller, MPC, Gate A, expert data, BC, DAgger,
residual RL remain blocked.

## 80. Frozen D1R14R8R4 fresh causal observer-identification task

Before any R8R4 implementation, feature matrix, fit, prediction metric, new
TSC trajectory, model/tube artifact, or route, R8R4 is prospectively frozen
in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R4_FRESH_CAUSAL_OBSERVER_IDENTIFICATION_DESIGN.md
SHA-256
942b7698e9d19ee905d75dc7ee9fda370e642e9e986298af32d8f17ed22f8119
```

R8R4 is a new stage identity and uses exactly sixteen fresh baseline-only
trajectories. The fixed development set contains both histories of the four
former R8 calibration pairs; only after development execution/raw audit,
nested whole-pair qualification, model/tube serialization, hash freeze, and
structurally independent agreement may the two histories of the four former
R8 holdout pairs be opened as blind holdout. R8's own calibration/holdout raw
directories remain empty. No R8R4 trajectory contains a probe, and all are
still forbidden from expert, BC, DAgger, or RL datasets.

The observer retains the exact R8R3 353-dimensional causal history feature,
direct 12-state vR/vZ/Ip change target, and kinematic R/Z reconstruction. Its
fixed 48-candidate family expands PCA ranks to 32/48/64/96. Development uses
twelve already opened training pairs plus four fresh pairs under nested
whole-pair validation. A successful all-development model and empirical tube
are frozen before blind holdout and may not be refit, recalibrated, expanded,
or reselected afterward.

The prospective practical point caps are 3 mm R/Z, 0.02 m/s vR/vZ, and
1000 A Ip. At least 95% of all and prescribed-issue rows and 90% per history
must pass; each history must pass at least 3/4 issue rows. Every future point
must also remain inside 10 mm, 0.05 m/s, and 3000 A finite exclusion caps.
The frozen tube has the same 95% aggregate and 90% per-history containment
requirements and cannot exceed those exclusion caps. Every miss is retained.
These finite observer gates do not relax deterministic formal tracking.

Restart, physical prefix, causality, exact zero future action, constant
commanded current target, Card15, current, solver, raw, snapshot, and
independent-integrity gates remain all-or-nothing. The active task is to
implement, locally validate, directly package/deploy, and execute R8R4 in its
frozen order. A development failure stops before holdout. A blind-holdout PASS
authorizes only a separately frozen combined observer/innovation validation.
Controller, MPC, Gate A, expert data, BC, DAgger, and residual RL remain
blocked.

## 81. Final D1R14R8R4 result and active context-robust holdout boundary

R8R4 completed its strict development-only boundary. All eight authentic
baselines passed runtime, restart, causal prefix, exact zero-future-action,
constant-future-current, Card15, current, raw, and snapshot gates. Primary
and independent raw inventories agree at eight files, 245279 bytes, digest
`8d0d6c2c8f7e4e8436f9ef958fb30e4276823a8004fbab97b8c50d71b1ed3f66`.

The 16-fold outer point evaluation passed 480/480 origins and 128/128 issue
origins under the prospective practical caps. There were zero finite-
exclusion violations and the maximum scaled point error was
`0.12737875204525517`. The all-development selection was the
linear/PCA32/ridge-1e-6 candidate.

The fixed higher-quantile-scaled tube remained far inside its caps and met
aggregate containment at 457/480 against a 456 requirement. It failed the
90% per-history floor in five of 32 contexts, however, with contained counts
`12/14, 11/16, 12/16, 10/14, 12/14` against integer requirements
`13,15,15,13,13`. The structurally independent implementation reproduced
every primary number and the route exactly. No model or tube artifact was
emitted, and fail-closed authorization kept blind holdout at zero raw.

Final state SHA-256 is
`617c6ea2e2ae81d5d1ad9f0de2f331a1b0d19caa3031dc76e4714ecc4c417015`.
The exact report is
`docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R4_FORENSIC_REPORT.md`,
SHA-256
`57b43c220de0fe2e37ac1dde17b4054bcd7f679255de58e2d782ee1bea2b53a3`.

R8R4 is final as
`FRESH_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT`. It is a finite
uncertainty-calibration/design failure, not a runtime, restart, raw,
controller, formal-control, real-MPC, plant-reachability, or global-
observability conclusion. Its eight trajectories remain forbidden from
expert and learning data. R8R4 may not resume under changed tube semantics.

## 82. Frozen D1R14R8R5 context-robust observer holdout task

Before any R8R5 fit, residual recomputation, tube metric, artifact, route,
new TSC, or blind-holdout outcome, R8R5 is prospectively frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R5_CONTEXT_ROBUST_OBSERVER_HOLDOUT_DESIGN.md
SHA-256
c7b5d570a6d74b39368e4ee4ef677f84a7a81b469a000515ea843e2797622daa
```

R8R5 treats all R8R4 development evidence as consumed and runs zero new
development TSC. It fixes the R8R4-selected linear/PCA32/ridge-1e-6 point
candidate, recomputes complete whole-pair OOF predictions, and derives one
shared global tube. Its fixed scalar is 1.25 times the maximum of the global
higher-q95 row ratio and every history context's higher-q90 row ratio, with
a floor at one. Context IDs are evaluator-only and never model inputs or
deployment-time selectors.

If and only if unchanged point/exclusion gates, tube caps, calibration
coverage, source authentication, and a structurally independent
recomputation all pass, R8R5 may freeze model/tube hashes and run the eight
still-unopened baseline histories from four whole physical pairs under a new
identity. The blind result cannot refit or expand the model or tube. Every
hard restart, causality, zero-action, Card15, current, raw/snapshot, and formal
timing contract remains unchanged.

A blind-holdout PASS authorizes only a separately frozen combined
observer/innovation-adaptation validation. A FAIL requires another observer
or finite-envelope redesign. No R8/R8R4/R8R5 trajectory may enter expert,
BC, DAgger, or RL data. Controller execution, MPC, Gate A, and all learning
remain blocked.

## 83. Final D1R14R8R5 result and observer-redesign boundary

R8R5 completed its frozen development, authorization, authentic blind
holdout, independent raw/model audit, and postprocess sequence. The package
checkpoint is `26b96e8`; the direct-copy closure contained 966 declared files
plus manifest/sums. Local and installed full suites passed 1198/1198, with
one expected Linux skip on the server.

The development bank passed all gates and froze the exact
linear/PCA32/ridge-1e-6 model and context-robust global tube before holdout:

```text
development point / issue / tube rows        480/480 / 128/128 / 480/480
observer model SHA-256
  d3d7ecebbe51ca20e83cdb126682d2bebad749b8fd5cb67dd57b3baf416e77e4
observer tube SHA-256
  3a436307a507b9aacda85321dd4d55e6bbcc996efe2e25c2b5026571c7108786
```

All eight blind baseline rollouts completed with exact runtime, restart,
source prefix, zero-future-action, constant-current, Card15/current, finite
raw, and independent inventory gates. The raw inventory is eight files,
245493 bytes, digest
`55cae64bf5b907b4cd6013615388dbb637dd2f1f14e49bda7fb49d11cf5b3d14`.

The blind point model passed 120/120 origins and 32/32 prescribed issues.
Aggregate tube containment passed 117/120 against 114, but the prospectively
frozen per-context gate failed in exactly one history:

```text
p5_q2_a0p900_gap4_settle4 | plus_first       14/16; required 15/16
```

Three rows were outside the tube; all four violating cells were Ip at future
lags 11--12 and every row remained within its point cap. Primary and
independent raw and model audits agree exactly. Final state SHA-256 is
`dc564ddfb9edae9b044dfa358ddb98306b56f328a8fc06c60b8c43ade772e48c`.
The exact report is:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R5_FORENSIC_REPORT.md
SHA-256
cd9f7f0c70e3c858193f7511abd1e0ece4fa612f6cfa1bf16b1bdebb038cc91c
```

R8R5 is immutable as
`CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN_REQUIRED`. This is a
finite uncertainty-qualification design failure, not a runtime, restart,
raw, controller, formal-control, real-MPC, plant, reachability, or global-
observability conclusion. Its baseline trajectories remain forbidden from
expert and learning data.

## 84. Frozen D1R14R8R6 causal one-step innovation observer task

Before any R8R6 implementation, adapted prediction, residual, tube, metric,
route, or artifact, R8R6 was prospectively frozen at checkpoint `0352207`:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R6_CAUSAL_ONE_STEP_INNOVATION_OBSERVER_DESIGN.md
SHA-256
6f8886f42321a2e99a97332ecf03c1827b5385ebfc50f6ee07fefefcafa182f1
```

R8R6 executes zero new TSC. It combines the now-consumed 20 physical
baseline pairs into 20 whole-pair outer folds with 600 causal origins. The
cold model remains fixed at linear/PCA32/ridge-1e-6. Origin 10 is unchanged
startup/fallback; each later origin uses only the one-step vR/vZ/Ip prediction
error that has already become observable on the same trajectory, with fixed
physical clipping `[0.02,0.02,1000]` and fixed persistence `rho=0.8`. R/Z are
reintegrated causally from the observed origin.

The 560 adapted rows use one frozen global tube derived with higher-q95 and
every-context-higher-q90 ratios, a prospective reserve multiplier 2.0, and
the unchanged 10 mm/0.05 m/s/3000 A caps. Point, finite, prescribed-issue,
aggregate tube, and every-context gates remain explicit. Adaptation must also
reduce aggregate MSE by at least 5%, regress no context by more than 5%, and
strictly improve at least 24/40 contexts.

If observer/tube gates pass without measurable adaptation gain, the frozen
route selects the static robust observer rather than preserving unnecessary
adaptation. Any observer route still authorizes only a separately frozen
fresh authentic interaction sentinel. The active task is to implement
primary and structurally independent R8R6 audits, validate/package/deploy
them, and execute the zero-new-TSC stage. Controller execution, MPC, Gate A,
expert data, BC, DAgger, and residual RL remain blocked.

## 85. Final D1R14R8R6 result and active interaction-sentinel boundary

R8R6 completed its frozen zero-new-TSC primary, structurally independent,
and postprocess sequence at implementation/package checkpoints
`df2e8c4 / 6b00e24`. Local and installed full suites passed 1208/1208; the
installed server suite had one expected skip. The empty direct-copy package
contained 980 declared files plus manifest/sums.

The source bank authenticated 20 physical pairs, 40 histories, 600 origins,
160 prescribed issue rows, and zero forbidden or future predictor inputs.
The fixed linear/PCA32/ridge-1e-6 causal observer and prospective factor-two
context-robust tube passed:

```text
startup fallback point rows                              40 / 40
adapted point rows                                     560 / 560
adapted prescribed issue rows                          120 / 120
adapted tube rows                                      560 / 560
contexts satisfying every point/tube gate                40 / 40
finite-exclusion / innovation-clipping rows                 0 / 0
tube cap                                                     PASS
```

The separately frozen adaptation usefulness gate failed:

```text
adapted / cold aggregate MSE                         1.0781373396
required                                                 <= 0.95
strictly improved contexts                               8 / 40
required improved contexts                             >= 24 / 40
contexts within 1.05 regression limit                   12 / 40
worst context ratio                                    1.287598795
```

Primary and independent numerical, outcome, and artifact comparisons agree
exactly. The route is
`CAUSAL_ONE_STEP_INNOVATION_NO_MEASURABLE_GAIN_STATIC_ROBUST_OBSERVER_SENTINEL_REQUIRED`:
the static causal observer and robust tube qualify, while the innovation
adapter is disabled for lack of measured benefit.

R8R6 created no raw directory and ran zero Ray, `gotsc`, TSC, controller, or
plant steps. It is not a closed-loop, formal-control, real-MPC, Gate A, or
learning result. Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R6_FORENSIC_REPORT.md
SHA-256
cf948786db23de51a5f30a8407cee30d06e8ddf1cafe4476f0c45a78c6a7eeea
```

R8R7 has now passed its fresh authentic interaction gate. The active task is
to freeze a new-identity genuine receding-horizon controller design before
any implementation, optimizer result, controller trajectory, or outcome is
seen. It must use the qualified static observer and response/tube artifacts,
causal startup/fallback, exact Card15 actions, hard current and action bounds,
a frozen finite controller matrix, and prospective acceptance criteria. Gate
A, expert data, BC, DAgger, residual RL, and all R8-family trajectories as
learning data remain blocked.

## 86. Frozen D1R14R8R7 fresh multipulse interaction-sentinel task

Before any R8R7 implementation, derived metric, model/tube artifact, raw
result, or TSC trajectory, the prospective design was frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R7_FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_SENTINEL_DESIGN.md
SHA-256
a2d2abda8189ff475455ae945391948ede937ba49ab559d79f1c48c74e80067f
```

R8R7 uses 16 contexts from the eight former R8 calibration/holdout pairs,
whose action-response outcomes remain unopened. Phase 1 runs 16 fresh
zero-future-action baselines and must independently pass the frozen static
observer gate before phase 2. Phase 2 runs 32 authentic four-pulse trajectories
using two fixed direction/sign schedules and unchanged fail-closed Card15,
increment, cancellation, current, restart, causality, raw, and snapshot gates.

The four-step predictor is the byte-authenticated R8R6 static observer plus
one fixed R8R1 PCA4/RBF-median-times-two/ridge-0.1 response deployment fit
trained only on the immutable 912-row R8 bank. Innovation, R8R7 refit,
candidate selection, pair/history labels, matched-baseline future, and future
measurements are forbidden. Primary and structurally independent audits must
agree on all source hashes, artifacts, raw inventories, predictions, gates,
and routes.

The active boundary is to implement, test, package, deploy, and execute R8R7
under the frozen phase boundary. A PASS authorizes only a separately frozen
receding-horizon MPC design. R8R7 is not MPC or Gate A. All R8R7 trajectories
are forbidden from expert data and all learning remains blocked.

## 87. R8R7 pre-action multipulse runtime hotfix boundary

Phase one is complete and independently accepted: 16/16 authentic baseline
raw passed all execution gates, and the static observer passed 64/64 point
and tube rows with every context at 4/4. The independent raw audit initially
used an incompatible JSON inventory digest; `a39c5a9` restores the frozen
primary `name/NUL/size/NUL/SHA` digest and changes no scientific result.

The first phase-two invocation wrote 32 failure files. All have one reset
state, zero trace rows, zero actions, zero events, and zero plant advances;
all stopped in the inherited R4 constructor because R8R7 issue step 10 was
incorrectly passed through the historical R4 `(14,18,22)` validator. The
inventory is 32 files, 145407 bytes, digest
`7cadf53a6870980802009eef71e3d7c8e5c2707eb446d85f125851e239af160d`.

The active task is the narrowly audited `4a8b558` runtime hotfix described in
`STAGE4_2R3C3T13S24D1R14R8R7_MULTIPULSE_RUNTIME_HOTFIX_AUDIT.md`. Preserve
and authenticate the failure files, leave the accepted run fingerprint and
all frozen experiment semantics unchanged, validate in the server virtualenv,
then execute the same 32 specs once. Do not count the failed attempts as
scientific multipulse trajectories and do not create a new identity unless a
plant advance/action is discovered or an experiment semantic must change.

## 88. Final R8R7 result and MPC-design handoff

The audited hotfix preserved all 32 pre-action failure files and then executed
the same frozen specifications once. Baseline and multipulse execution passed
`16/16` and `32/32`; raw inventories independently matched. Exact issue and
cancellation gates passed `128/128 / 128/128`, with zero forbidden trace.

The frozen model passed baseline point/tube `64/64 / 64/64` and multipulse
point/tube `128/128 / 128/128`. Every context, direction, sign, tube cap, and
finite-exclusion gate passed. Primary and independent numerical, outcome,
route, inventory, and artifact hashes agree exactly. The final route is:

```text
FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_PASS_MPC_DESIGN_REQUIRED
```

Formal tracking remained diagnostic only (`6/16` baseline and `12/32`
multipulse). R8R7 is a finite interaction-model qualification PASS, not a
controller, MPC, formal-control, Gate A, or learning result. Every R8R7
trajectory remains forbidden from expert/BC/DAgger/RL data.

The active boundary is to freeze a separately identified genuine receding-
horizon MPC design before implementation or outcome inspection. It must then
be implemented and tested through the deterministic core and every finite
qualification axis in Section 0.1. Do not claim Gate A until all those axes
pass, and do not create expert data or enter BC/DAgger without the user's
confirmation at Gate A.

## 89. Frozen D1R14R8R8 causal discrete-pulse MPC-core task

Before any R8R8 implementation, offline candidate result, controller
decision, formal outcome, raw trajectory, or TSC plant advance, the complete
prospective design was frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R8_CAUSAL_DISCRETE_PULSE_RECEDING_HORIZON_MPC_CORE_DESIGN.md
SHA-256
0906ca9e58126cc2f414f167a685e766d95790ec4f3d28052debb4b5e6db0244
```

R8R8 uses the 16 accepted R8R7 baseline contexts but runs fresh controlled
TSC trajectories under a new identity. At task steps `[10,14,18,22]`, it
causally exhausts zero plus four canonical directions times two signs at
scale 1.0. Its fixed robust quadratic score uses only the authenticated
static observer, four-step response model, and frozen static/combined tubes.
It executes only the first exact Card15 pulse and its next-step exact stored-
center cancellation, then replans from the newly observed prefix.

Primary and structurally independent zero-TSC preflights must agree on 576
candidate predictions/scores, 64 decisions, and 512 pure issue/cancellation
constructions before real TSC is authorized. The authentic deterministic core
requires exact runtime/restart/causality/integrity/safety gates and unchanged
formal tracking `16/16`. A lesser formal result is a finite controller-design
FAIL when execution gates pass; it is not a runtime or global-reachability
conclusion.

The frozen primary and structurally independent implementations were completed
at checkpoint `7e1dc89`. Local project-venv compilation and focused tests passed
`10/10`; after explicitly loading the existing Windows `resource` shim, the
complete unittest suite passed `1229/1229` with zero failures, errors, or skips.
No R8R8 offline result or TSC plant advance existed at that checkpoint.

Package checkpoint `9179c9a` passed empty-directory, staging, and installed
validation. Its first offline invocation stopped before creating the stage
because the source authenticator expected R8R7 state `"finished"` instead of
the immutable value `"complete"`. R8R7 hashes/route/verdict were unchanged;
the preserved v1 run root has no stage, raw, controller decision, or TSC
advance. Authentication-only hotfix `2b287cb` corrects that field and adds the
same independent source authentication without changing any scientific or
physical semantics. Local focused/full validation passed `11/11 / 1230/1230`.

The active boundary is to repackage/direct-copy/deploy the hotfix under the
same frozen experiment semantics, use a separately named v2 offline attempt,
pass the dual offline gate, and only then run the single 16-trajectory core
campaign. A PASS is not Gate A: continuous
delay/gain/slew, mismatch, noise, disturbance recovery, independent long hold,
and residual-authority qualifications remain required under separately frozen
designs. All R8R8 trajectories are forbidden from learning; expert data, BC,
DAgger, and residual RL remain blocked.

## 90. Final R8R8 result and frozen R8R9 measured-authority task

R8R8 v2 completed its dual zero-TSC computation but failed the primary frozen
scientific gate. Source authentication, 576 forecasts, 64 decisions, 512 issue
constructions, 512 cancellations, fault injection, and forbidden-input checks
all passed. Every decision selected zero, against the prospectively required
minimum of one nonzero selection. The final route is:

```text
CAUSAL_DISCRETE_PULSE_MPC_SOURCE_OR_OFFLINE_FAIL_NO_TSC
```

The independent computation reproduced all predictions, scores, selections,
actions, outcomes, and model hashes exactly. Reporting-only fix `98bcb9c`
corrected its route field without changing the computation: audit agreement is
true while primary/scientific gate pass is false. Corrected independent,
primary-summary, manifest, and state hashes are:

```text
625a1bb289db927d037a448b6dba88d930246d5360c4c78155b79e2e272b53c1
eb7cf6eb2a8abbea020d76f63a59f6f0b4c128255583998c321d6aa979086840
5b0ad4b85c390e33a38bfb99c03f5163d1ea72c5efb1dd100f0a80477c8d68bf
c7914e8f7842ee22892b008e861fba9ead7496fb5f48ae663c0d7fd2da116228
```

No real-TSC authorization, raw, controller action, or plant advance occurred.
Retrospective attribution showed every point forecast favored a nonzero pulse
slightly, but none reached the frozen 0.5% improvement; candidate-specific
response uncertainty made every robust nonzero score worse than zero. R8R8 is
therefore a clean offline objective/model/action-design FAIL. Full report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R8_FORENSIC_REPORT.md
```

Before inspecting whether the two real R8R7 schedules repaired specific
baseline failures, the zero-new-TSC R8R9 design is frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R9_MEASURED_MULTIPULSE_AUTHORITY_AUDIT_DESIGN.md
SHA-256
3cb4ca9768671aaf575f2cb71c8c33d8643156110dc68c0b1e7b4d714d3d4510
```

R8R9 must authenticate all 48 immutable R8R7 raw files and the R8R8 zero-TSC
boundary, reproduce the known 6/16 and 12/32 formal aggregates, and compare
the two measured schedules with their matching baseline using two equivalent
formal-metric paths. At least one of the ten failed baselines must be repaired
and measured-oracle coverage must reach at least 7/16 to authorize a later
causal selector design. A failure routes to a new action architecture, not to
post-result relaxation of R8R8. No new TSC or learning is authorized.

## 91. Final R8R9 result and action-architecture redesign boundary

R8R9 completed its frozen zero-new-TSC primary and structurally independent
audits. It authenticated the R8R7/R8R8 sources, strictly parsed all 48 R8R7
raw files, reproduced baseline/multipulse formal counts `6/16 / 12/32`, and
obtained exact `48/48` agreement between the two formal metric paths.

```text
failed baselines                                           10
strict best-schedule minimum-margin improvements          9/10
gain min / median / max
  -0.000105833333334 / 0.000125349647658 / 0.000926800000001
failed baselines repaired                                  0/10
measured-oracle formal pass                                6/16
route
  MEASURED_MULTIPULSE_FORMAL_AUTHORITY_INSUFFICIENT_ACTION_REDESIGN_REQUIRED
```

Primary and independent numerical, scientific-gate, and route results agree
exactly. R8R9 created no raw directory and ran zero Ray, `gotsc`, TSC,
controller, or plant advances. Accepted detailed/summary/independent/manifest/
state SHA-256 values are:

```text
4bda8b9dafef7d75dc73aa28b8aebdbfd9df34f98d14c369182c833bd912f4ef
ffb67e2a882605d01af609f57b181657d334297d93e5eee893789873439b23fd
768a0a408880a19c6d723eccfef98a45018d01fcb63d48ab98e65d61784ce9f0
96655d1ccc84796b687f05644150909ba6aa64a3da549542eeac92d913cd2e0d
e03c09dfd0afffe20bdd641b401dc6e2f3e13b3075c2d3033578b7f5c67355bb
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R9_FORENSIC_REPORT.md
SHA-256
66993c4d638dec5e9bc883e45ce6586a12b367b9a97bc214c36cc41c80454f98
```

R8R9 is a finite measured-action-authority design failure, not a runtime,
restart, causality, raw, reporting, real-MPC, formal-control, plant, safety, or
global-reachability conclusion. The canonical-scale four-pulse route may not
be tuned or rerun under the same identity.

The active boundary is to freeze, before outcome inspection, a genuinely
different action architecture or a zero-new-TSC authority discriminator over
already authenticated and already consumed development evidence. A read-only
PASS may authorize only a separately frozen controller or fresh safety
sentinel; a FAIL must route to a genuinely new sustained/asymmetric action
identification. No existing probe trajectory may enter expert data. Gate A,
expert data, BC, DAgger, and residual RL remain blocked.

## 92. Final R8R10 result and sustained/asymmetric action-design boundary

Before its matched formal outcomes were computed, R8R10 froze a read-only
comparison of canonical direction-zero 1.0x and replacement direction-zero
1.5x authority over 24 consumed development contexts. It then authenticated
all 872 immutable R4/R6/R8 training raw files, reproduced the complete source
formal aggregates, and obtained exact `312/312` agreement between the compact
and complete formal-metric paths.

```text
baseline formal pass                                      8/24
failed baselines                                             16
canonical / replacement formal-pass trajectories       48/144 / 48/144
canonical strict minimum-margin improvements               15/16
replacement strict minimum-margin improvements             16/16
replacement gain min / median / max
  0.000050072836658 / 0.000210307502231 / 0.015329058949230
canonical / replacement / combined oracle pass          8/24 / 8/24 / 8/24
canonical / replacement / replacement-only repairs      0/16 / 0/16 / 0/16
route
  REPLACEMENT_SCALE_FORMAL_AUTHORITY_INSUFFICIENT_SUSTAINED_ACTION_REDESIGN_REQUIRED
```

Primary and structurally independent numerical, scientific-gate, and route
results agree exactly. R8R10 created no raw directory and ran zero Ray,
`gotsc`, TSC, controller, or plant advances. Accepted detailed/summary/
independent/manifest/state SHA-256 values are:

```text
dea560af0e491fc2ee6022b50174bdc3902fc5a615800edb335d050e17850821
e359a5ae19d59de7e8cb60e00e13932706ccadd1ea643bf8955f34b86a6aef33
161180d549878874c28cf24d83f0aae86bb174fe1e02cd328dff0b71f214962f
60dfa552ec580e57f3b5284b56509d00feb273fc1c92e78ccf4765cff853c56c
8ab651f135a9b460ee54a89172bcc3f42b6bc60e535d39702ae7a7606414989e
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R10_FORENSIC_REPORT.md
SHA-256
1698e024fcbc9c00f65536915de37926b2cf927a7a5402a8655169cbeaccf1df
```

R8R10 is a finite fixed-amplitude action-authority design failure, not a
runtime, deployment, restart, causality, raw, reporting, formal-evaluator,
real-MPC, safety, plant, or global-reachability conclusion. The isolated
direction-zero 1.0x/1.5x pulse route may not be tuned or rerun under the same
identity.

Before any additional context-level outcome is opened or any new TSC is run,
the active task is to freeze a genuinely sustained or asymmetric causal
action architecture with unchanged Card15/current/saturation, safe fallback,
restart, causality, integrity, and formal timing contracts. A read-only design
may use only already consumed development evidence. A real-TSC stage requires
a new identity, a prospective finite matrix, an explicit safe-stop envelope,
and independent raw authentication. No R8-family trajectory may enter expert
data. Gate A, expert data, BC, DAgger, and residual RL remain blocked.

## 93. Frozen R8R11 sustained exact-target-refresh authority task

Before implementation, specifications, offline construction, formal metrics,
raw, or TSC, and before opening R8R10 context-level detailed outcomes, R8R11
was frozen at checkpoint `d53d38d` in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R11_SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_SENTINEL_DESIGN.md
SHA-256
43a2ad925c78c4656a68e27a7243daf952edab1170c811c85c3d679ca1ab1707
```

R8R11 uses the 16 accepted R8R7 restart contexts and the exact direction-zero
1.5x Card15 coordinate at task steps `[14,18,22]`, both signs. At `issue+1`
it causally reconstructs an action to the same stored exact target; at
`issue+2` it returns to the stored issue center. Every issue, refresh, and
cancellation is independently checked before plant advance under the
unchanged 0.25/0.24 action, current, Card15, saturation, finite-state, and
forbidden-input gates.

The fixed two-phase campaign is:

```text
phase 1 safety          4 contexts * 3 times * 2 signs       24
phase 2 qualification 12 contexts * 3 times * 2 signs       72
maximum new authentic TSC trajectories                       96
```

Phase 1 formal outcomes remain unopened during authorization. All 24 phase-1
members must complete with exact primary/independent execution and safety
agreement before phase 2. After all 96 authenticate, both formal evaluators
must agree for every baseline/candidate row. A PASS requires at least one of
the ten R8R7 baseline failures repaired and held-oracle coverage `>=7/16`.
It authorizes only a separately frozen causal-selector/controller design.
Any source/preflight mismatch stops with zero TSC; any unsafe online
construction is rejected before advance and stops the phase; an authority
FAIL routes to a genuinely asymmetric or multi-direction sustained sequence.

The active task is to implement, locally validate, directly package/deploy,
execute, and independently audit R8R11 in that frozen order. No archive,
global Python, source raw modification, R8R10 detailed outcome use, or
learning is authorized. Gate A remains blocked.

## 94. Final R8R11 result and asymmetric causal-sequence boundary

R8R11 completed all 96 prospectively frozen authentic trajectories in order:
24 safety rows followed by 72 qualification rows. All rows passed runtime,
full-horizon, restart, causal physical prefix, calibration, exact Card15
issue/refresh/cancel, current, finite-state, forbidden-input, and raw-integrity
gates. Safety and qualification raw inventories are:

```text
safety          24 files /  759481 bytes / 137fc4024b720b3b...
qualification   72 files / 2288228 bytes / 82958eb8c4e49ff2...
```

The initial phase audits compared 13 source-only R4/R8R7 wrapper metadata
fields that do not exist in the new R8R11 wrapper. The reporting-only repair
found `3120 / 9360` safety/qualification wrapper differences, zero executable
or non-wrapper differences, preserved all raw bytes, opened no formal result,
and left the primary controller hash unchanged. Corrected primary and
structurally independent raw audits agreed exactly `24/24 / 72/72`. No TSC
trajectory was rerun.

After dual raw authorization, the unchanged formal computation produced:

```text
baseline formal pass                                      6/16
candidate formal-pass trajectories                       36/96
failed baseline strict best-margin improvement            10/10
gain min / median / max
  0.000249522056861 / 0.000485133333335 / 0.001795445790614
failed baselines repaired                                  0/10
held-oracle formal pass                                    6/16
maximum primary/independent numerical difference              0
route
  SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_INSUFFICIENT_ASYMMETRIC_SEQUENCE_REDESIGN_REQUIRED
```

Primary and independent result, gate, and route agree exactly. Accepted
detailed/summary/independent/final-report/manifest/state SHA-256 values are:

```text
aecd3a9e19bc8349398d885b78f6ef6cdbb20974878571036f4062f7f8b71ce1
8214b9c0340f5562a181a42cb2d4e30ca2f1dd79900f1089fae3422ef3531e9b
13f4436fff270a5eba1e91790522e3a490df59a879d9bab7636a6c3dc32b7391
903cdb4f01ff0e124081230f92be2d473e38bde8d0cc0cdb082d71f900e8f3b5
aaa8062421b9e1a5fa92641bffdf27684229a1db31f8a1a6d98bcde997aa8107
d805d7de4822678f17b6a814b3cb095ad59b96001db4ae81fd8e047cf8659e24
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R11_SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_SENTINEL_FORENSIC_REPORT.md
SHA-256
8d1dbaf0c0055e00088a7d63e033d51104bdfa07fe46188581261327b09673f8
```

R8R11 is a finite sustained direction-zero action-authority design failure,
not a runtime, deployment, restart, causality, raw, reporting, formal-control,
safety, real-MPC, plant, or global-reachability conclusion. Its identity is
immutable and may not be tuned, resumed, or enlarged.

The active boundary is to freeze, under a new identity and before any new
outcome or TSC, a genuinely asymmetric or multi-direction causal sequence.
It must retain exact restart, causal visible-state/controller-state rules,
Card15/current/saturation/safe-stop gates, the immutable formal timing
contract, a finite two-phase matrix, and structurally independent raw and
final auditing. A measured-authority PASS may authorize only a separately
frozen causal controller/MPC design. Gate A, expert data, BC, DAgger, and
residual RL remain blocked, and no R8-family trajectory may enter learning.

## 95. Frozen R8R12 causal cumulative direction-2 staircase task

Before implementation, configuration, specification generation, candidate
formal outcomes, raw, or TSC, the next one-sided asymmetric sequence was
frozen at checkpoint `1d09508` in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R12_CAUSAL_CUMULATIVE_DIRECTION2_STAIRCASE_AUTHORITY_SENTINEL_DESIGN.md
SHA-256
46d959813a0810970e7ea6ab5a5a097c9afa5949e7642f22fc4b17a19ccd2f16
```

R8R12 uses the canonical direction-2 sign-plus coordinate at scale 1.0. At
task steps `[10,14,18,22]`, it constructs a new exact Card15 target from the
current measured center, then causally refreshes that stored target through
the next decision. The fourth level persists through the unchanged state-35/
37 formal endpoint. There is no accumulated return-to-origin cancellation.

The fixed two-phase campaign is one trajectory per R8R7 context:

```text
safety          4 contexts / 4 new authentic trajectories
qualification  12 contexts / 12 new authentic trajectories
maximum total  16 new authentic trajectories
```

Safety formal outcomes remain closed. Qualification requires exact primary
and structurally independent agreement on all four safety raw files. Every
issue/refresh is fail-closed before advance under the unchanged 0.25 action,
0.55 current, Card15, saturation, finite-state, restart, causality, and
forbidden-input gates. Candidate formal results open only after all sixteen
raw authenticate.

A scientific PASS requires at least one of ten failed baselines repaired and
retrospective held-oracle coverage at least `7/16`, with exact dual formal-
metric and independent agreement. A PASS authorizes only a separately frozen
causal selector/controller design. A failure cannot be tuned under R8R12.

The active boundary is to implement primary and structurally independent
offline/raw/final paths, validate with the project and server virtual
environments, directly package/deploy without archives, then execute R8R12 in
its frozen order. R8R12 is not MPC or Gate A. Expert data, BC, DAgger, and
residual RL remain blocked, and every R8-family trajectory remains forbidden
from learning datasets.

## 96. R8R12 v1 construction failure and frozen v2 implementation task

R8R12 v1 passed dual offline construction but its four authorized safety tasks
all stopped during controller construction with
`D1R14R6 per-spec issue schedule changed`. The four immutable raw files contain
only their initial state: zero controller trace, physical action, plant
advance, or snapshot. Canonical inventory is:

```text
4 files / 17687 bytes /
f59d7aa22205d995519742b049c516e0403a18840d593b5d0db9e058150d549d
```

Qualification and formal outcomes were never opened. The strict-JSON reporting
repair created no raw or worker call, and independent recomputation exactly
matched the primary failure audit. v1 is final and may not resume.

Before any corrected implementation or outcome, v2 is frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R12_V1_CONSTRUCTION_FAILURE_AND_V2_CORRECTION.md
```

The only permitted construction correction is to pass the inherited R6
constructor a valid inert placeholder `issue/cancel/zero_after = 14/15/16`.
The R8R12 subclass still delegates only task steps 0--9 and exclusively owns
the actual unchanged `[10,14,18,22]` staircase. v2 must change campaign
identity, controller revision, package revision, and run directory. Every
other frozen source, spec, Card15/action/current/saturation, safe-stop, formal
timing, two-phase authorization, authority, and data-prohibition gate remains
unchanged.

The active task is to implement and test that one correction, directly package
and deploy it, rerun dual offline construction under v2, and only then execute
at most four new safety trajectories. Qualification is authorized only by
exact primary/independent v2 safety agreement. Formal outcomes remain closed
until all 16 v2 trajectories authenticate. A v2 authority PASS still only
authorizes a separately frozen causal selector/controller design; it is not
MPC or Gate A. Expert data, BC, DAgger, and residual RL remain blocked.

## 97. Final R8R12 result and multi-direction sequence boundary

R8R12 v2 completed the corrected campaign from implementation/package
checkpoints `3203a02 / 523c706`. Local, empty direct-copy, server staging,
and installed validation passed the 1,040-file package, focused `10/10`, and
full `1262/1262` suites. Dual offline construction agreed exactly on all
`64/64` levels and `352/352` refreshes with zero TSC or raw.

The prospectively ordered authentic campaign then completed:

```text
safety raw          4 files / 130839 bytes / 8eb94b448e302721...
qualification raw  12 files / 395289 bytes / b51d78d0fa511255...
runtime / full horizon / causal physical prefix                 16/16
calibration / exact Card15 target chain                          16/16
issues / refreshes                                             64 / 352
maximum issue / refresh increment          0.1409259259 / 0.0000037037
maximum current utilization                                    0.3924
forbidden trace rows                                                 0
```

Primary and structurally independent safety audits agreed before
qualification authorization; qualification audits agreed before formal
outcomes opened. The unchanged formal computation produced:

```text
matching baseline formal pass                                  6/16
fixed staircase formal pass                                    6/16
failed-baseline strict margin improvement                       6/10
gain minimum / median / maximum
  -0.011194833333335 / 0.088958781607079 / 0.136483098392177
failed baselines repaired                                      0/10
baseline-pass contexts preserved                                6/6
held-oracle formal pass                                        6/16
maximum primary/independent numerical difference                  0
route
  CAUSAL_CUMULATIVE_DIRECTION2_STAIRCASE_AUTHORITY_INSUFFICIENT_SEQUENCE_REDESIGN_REQUIRED
```

Accepted detailed/summary/independent/final-report/manifest/state SHA-256
values are:

```text
123991e8e31d159361785666b483183a3fb31b7db540b3677e12537bc03fd88f
93df1e3ea60b6655cc0a325aacb5d7d089e349cf42df82968b16f755a545572f
848867b23b8fc0c9ba5723bf77e03baaf7de532119de1dd2c3d6b53cd1f1f1a4
2a018bd023ffd4ef1d82611283ead5ac79d00479691d00929c1c95b471e0dea3
48a0992757f4ee51dcbdf04f6cac0e32116e875d1b1c3626cb93bb9d342bc095
e5410b24f5b60e682b93c1c411ddae88caec50d17dd23a8be67604b0e4107daf
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R12_FORENSIC_REPORT.md
SHA-256
431db78078df7e27def9cee633f91d69e89d48b1833feb82765c10add933ecbd
```

R8R12 v2 is a finite fixed-policy cumulative direction-2-positive sequence
authority design failure, not a runtime, deployment, controller-construction,
restart, causality, raw, reporting, formal-control, safety, plant, real-MPC,
or global-reachability conclusion. v1 remains separately frozen as a
pre-advance implementation failure. Neither identity may be resumed, tuned,
or enlarged.

Before another outcome or TSC execution, the active task is to freeze a new
genuinely multi-direction or otherwise genuinely different asymmetric causal
sequence under the unchanged source authentication, exact restart,
visible-state causality, Card15/current/saturation/safe-stop, immutable formal
timing, finite two-phase, independent-audit, and learning-data-prohibition
contracts. A measured-authority PASS may authorize only a separately frozen
causal selector/controller or MPC design. Gate A, expert data, BC, DAgger,
and residual RL remain blocked.

## 98. Frozen R8R13 measured additive multi-direction discriminator

Before R8R13 implementation, additive composition, formal metric, output,
route, or further TSC execution, the next zero-new-TSC discriminator was
frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R13_MEASURED_ADDITIVE_DIRECTION0_ON_DIRECTION2_COMPOSITION_DESIGN.md
SHA-256
f643d4ded6131db8264847f8ce4aff121c4165c49666eb7b7e34211c0c72bc1f
```

R8R13 authenticates and strictly parses the exact 16 R8R7 baselines, 96
R8R11 direction-0 transient candidates, and 16 R8R12 direction-2 cumulative
staircases. It evaluates the six globally fixed R8R11 choices formed by issue
step `[14,18,22]` and sign `[-1,+1]`. For every context and R/Z/Ip state it
constructs:

```text
R8R12 + (R8R11 candidate - matching R8R7 baseline)
```

through two algebraically equivalent paths. The zero-correction control must
reproduce R8R12 exactly, both unchanged formal metric paths must agree, and
the primary/independent implementations must select the same global candidate
with exact numerical agreement. A PASS requires that one same candidate over
all sixteen contexts reaches at least `7/16`, repairs at least one of ten
failed baselines, and regresses none of the six baseline passes.

R8R13 composes no action, current, hidden state, or safety telemetry. It runs
zero Ray, `gotsc`, TSC, controller, plant advance, raw, or snapshot. Its
additive assumption is optimistic and does not validate cross-direction plant
interaction. A PASS authorizes only a separately frozen exact combined-action
Card15/current/saturation preflight; it cannot directly authorize real TSC.
A FAIL requires genuinely new sequence identification rather than post-result
family expansion. Gate A, expert data, BC, DAgger, and residual RL remain
blocked, and all source trajectories remain forbidden from learning data.

## 99. Final R8R13 result and new sequence-identification boundary

R8R13 was implemented and packaged at checkpoints `a4f999e / da1585d`.
Local, empty direct-copy, server-staging, and installed validation passed all
1,047 hashes, JSON, compilation, focused `7/7`, and full `1269/1269` tests,
with one expected isolated-evidence skip where applicable.

The accepted zero-new-TSC run is:

```text
stage4_2r3c3t13s24d1r14r8r13_runs/
stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition_20260808_da1585d_v1/
stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition
```

Primary and the structurally independent implementation authenticated and
strictly parsed all `16 + 96 + 16 = 128` source raw files and reproduced the
R8R7/R8R11/R8R12 formal aggregates exactly:

```text
source formal pass                     6/16 / 36/96 / 6/16
source formal-path maximum difference                       0
zero-correction exact                                  16/16
additive-path maximum absolute difference  1.0842021724855044e-19
composed formal-path maximum difference                       0
new raw / TSC / plant advances                          0/0/0
```

Every global candidate produced the same decisive outcome:

```text
formal pass                                      6/16
failed baselines repaired                         0/10
baseline-pass regressions                           0/6
```

The fixed rank `[5,3,1,0,2,4]` selected candidate 5 (issue step 22,
direction-0 positive), with failed-baseline minimum-margin gain
min/median/max `-0.0108065667 / 0.0886613584 / 0.1366534651`. It did not meet
the frozen `>=7/16` and `>=1/10` gates. Primary and independent outputs agree
exactly. The final route is:

```text
MEASURED_ADDITIVE_DIRECTION0_ON_DIRECTION2_AUTHORITY_INSUFFICIENT_NEW_SEQUENCE_IDENTIFICATION_REQUIRED
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R13_FORENSIC_REPORT.md
SHA-256
ecf78b5d36d7769c326f671b68b8c977e6830f2c75c0aca8b92cde57e2d0617a
```

R8R13 is immutable. It is a finite optimistic additive-authority design
failure, not a physical combined-action, controller, MPC, safety, plant, or
reachability result. Before any new outcome or TSC, the active task is to
freeze a new-identity genuinely different sequence-identification design
under unchanged restart, causality, Card15/action/current/saturation,
safe-stop, formal timing, independent-audit, and learning-data-prohibition
contracts. Gate A, expert data, BC, DAgger, and residual RL remain blocked.

## 100. Frozen R8R14 cumulative multidirection staircase identification

Before R8R14 implementation, config, offline construction, metric, result,
raw, snapshot, or TSC, the next genuine sequence-identification stage was
frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R14_CUMULATIVE_MULTIDIRECTION_STAIRCASE_AUTHORITY_IDENTIFICATION_DESIGN.md
SHA-256
06360433fd33fd8706453e145eeadca7e37fa80f4e99193cf779e62ab3af4f0f
```

R8R14 authenticates the exact 16 R8R7 baselines, final R8R12 v2, and final
R8R13 provenance. It reuses without rerunning R8R12's direction-2-positive
scale-1.0 staircase. The seven new cumulative candidates are:

```text
(0,-1) (0,+1) (1,-1) (1,+1) (2,-1) (3,-1) (3,+1)
decision task steps [10,14,18,22]
```

Each new row uses the same causal measured-current exact-Card15 issue and
stored-target refresh construction as R8R12. Primary and structurally
independent offline implementations must pass all 112 rows, 448 issues,
refresh chains, action/current/saturation gates, and exact spec agreement
before TSC. Any preflight failure ends with zero new TSC.

Prospective physical phases are:

```text
safety          4 contexts * 7 candidates = 28
qualification  12 contexts * 7 candidates = 84
maximum new authentic trajectories        = 112
```

Formal outcomes remain closed through safety and qualification raw audits.
Qualification requires byte-frozen primary/independent safety agreement;
formal computation requires exact primary/independent qualification
agreement. The final measured atlas is 16 existing R8R12 plus 112 new rows.

A PASS requires `>=1/10` failed-baseline repairs and an evaluator-only
do-nothing-safe held oracle of `>=7/16`, with unchanged formal timing and
exact independent agreement. This oracle is not a causal selector. A PASS
can authorize only a new frozen visible-state causal selector/controller
design; a FAIL requires sequence-basis redesign. R8R14 is not MPC or Gate A.
All source/new trajectories are forbidden from expert, BC, DAgger, and RL
data, and all learning remains blocked.

## 101. Final R8R14 result and temporal sequence-basis boundary

R8R14 was implemented and packaged at checkpoints `d737000 / 9874068`.
Local, empty direct-copy, server-staging, and installed validation passed all
1,053 declared hashes, compilation, focused `10/10`, and full `1279/1279`
tests, with one expected isolated-evidence skip where applicable. The accepted
server run is:

```text
stage4_2r3c3t13s24d1r14r8r14_runs/
stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification_20260808_9874068_v1/
stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification
```

Primary and independent offline construction agreed exactly on all 112 specs,
448 cumulative issues, and 2,464 stored-target refreshes. All 28 safety raw
then authenticated before the 84 qualification rows were authorized. Every
one of the 112 authentic trajectories passed the frozen runtime, horizon,
restart/source-prefix, causality, calibration, Card15, current, finite-state,
forbidden-input, raw, and report gates:

```text
safety raw          28 files /  913832 bytes / 8fd9e0e5...
qualification raw   84 files / 2757127 bytes / 5bd7e233...
issues                                                  448
forbidden trace rows                                      0
maximum measured current utilization                 0.3927
```

Formal evaluation reproduced every existing metric with maximum difference
zero. Baseline and reused R8R12 direction-2-positive both passed `6/16`. The
eight constant-direction/sign cumulative candidates passed between `5/16`
and `6/16`; none repaired any of the ten failed baselines, and the held oracle
remained `6/16`. Best failed-context margin gain was
`0.0255417333 / 0.0889587816 / 0.1364830984` min/median/max. Direction-2
positive was the best measured candidate in six failed contexts and
direction-1 negative in four. Primary and independent candidate summaries,
numerics, gate, and route agree exactly.

The final route is:

```text
CUMULATIVE_MULTIDIRECTION_ATLAS_AUTHORITY_INSUFFICIENT_SEQUENCE_BASIS_REDESIGN_REQUIRED
```

Exact report:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R14_FORENSIC_REPORT.md
SHA-256
306a51e6a83584a21a94928a3c6aa220292f628faa82831c0160f84fa2106be1
```

R8R14 is immutable. It rules out the frozen constant-direction cumulative
atlas only. It is not an MPC, Gate A, plant-unreachability, or learning result.
Before further TSC, the active task is to freeze a new-identity genuinely
time-varying sequence basis under unchanged restart, visible-state causality,
Card15/action/current/saturation, safe-stop, formal timing, two-phase,
independent-audit, and learning-data-prohibition contracts. Gate A, expert
data, BC, DAgger, and residual RL remain blocked.

## 102. Frozen R8R15 binary temporal-switching staircase task

Before R8R15 implementation, configuration, offline construction, raw,
snapshot, TSC, formal outcome, or route, the temporal basis was frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R15_BINARY_TEMPORAL_SWITCHING_STAIRCASE_AUTHORITY_SENTINEL_DESIGN.md
SHA-256
bc0651d9c07f25c961bb5251ab508bda45ddc611d2b32f052ea0592cfe938bfe
```

R8R15 uses only the two coordinates that were best in the R8R14 failed
contexts:

```text
U = direction 2, sign +1, scale 1.0
V = direction 1, sign -1, scale 1.0
decision task steps = [10,14,18,22]
```

It reuses immutable R8R12 `UUUU` and R8R14 `VVVV` without rerunning either.
Exactly eight new globally fixed sequences are allowed:

```text
UVVV  UUVV  UUUV  VUUU  VVUU  VVVU  UVUV  VUVU
```

They cover every single switch point in both temporal orders and the two
alternating controls. No other code, direction, sign, scale, timing, or
post-result family expansion is allowed under this identity.

Primary and independent offline implementations must agree exactly and pass
all 128 specs, 512 exact-Card15 issues, 2,816 stored-target refreshes, and
unchanged action/current/cosine/off-basis/saturation gates before any plant
advance. Physical execution is partitioned as 32 safety and 96 qualification
trajectories. Qualification requires exact dual safety raw agreement; formal
outcomes remain closed until all 128 new raw pass both audits.

The final evaluator-only atlas contains the R8R7 baseline, source `UUUU`,
source `VVVV`, and eight new measured sequences per context. A PASS requires
at least one of ten failed baselines repaired by a new sequence and a do-
nothing-safe measured oracle of at least `7/16`, with exact primary/
independent metric and route agreement. The held oracle is not a causal
selector. A PASS authorizes only a new frozen causal selector/controller; a
FAIL requires model-based sequence redesign under a new identity.

Implement, test locally with the project environment and Windows resource
shim, package through an empty direct-copy tree, deploy without archives,
validate with the existing server environment, and execute only in the frozen
two-phase order. Do not rerun R8, R8R1, R8R12, or R8R14. R8R15 is not MPC or
Gate A. All R8-family trajectories remain forbidden from expert, BC, DAgger,
and RL data, and all learning remains blocked.

## 103. Final R8R15 result and active model-based boundary

R8R15 completed its exact frozen campaign at design/implementation/package
checkpoints `e3d5302 / 222f5d5 / f23c96e`. Dual offline construction passed
`128/128` specs, `512/512` exact Card15 issues, and `2816/2816` refreshes.
All 32 safety raw passed exact primary/independent agreement before 96
qualification trajectories were authorized. All `128/128` authentic raw
passed runtime, full-horizon, restart/physical-prefix, calibration, target-
chain, action, current, causality, finite-state, forbidden-input, strict-JSON,
and inventory gates.

The unchanged formal evaluator reproduced baseline, source `UUUU`, and source
`VVVV` at `6/16`. Each of the eight new mixed sequences also passed exactly
`6/16`, repaired `0/10` failed baselines, and regressed `0/6` baseline passes.
Failed-context best minimum-margin gain was positive in every context, with
min/median/max `0.0255417333 / 0.0889587816 / 0.1364830984`, but no candidate
crossed the formal boundary and the held oracle remained `6/16`. Primary and
the structurally independent implementation agreed exactly. The final route
is:

```text
BINARY_TEMPORAL_SWITCHING_STAIRCASE_AUTHORITY_INSUFFICIENT_MODEL_BASED_SEQUENCE_REDESIGN_REQUIRED
```

The exact report is:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R15_FORENSIC_REPORT.md
SHA-256
ca51f7f7b9791199796e923704da84355b1ac5eb9c2669900165962d5a7fc04c
```

R8R15 is immutable and may not be resumed, enlarged, or tuned. It rules out
only the frozen binary U/V four-decision open-loop basis. It is not a plant-
unreachability, real-controller, MPC, or Gate A conclusion.

The active task is to freeze a new-identity model-based sequence redesign
before implementation, fitting, optimization output, candidate choice, or
any new TSC. It must explicitly separate model-development/calibration from
held scientific evaluation, use only allowed visible causal state, preserve
the unchanged authentic-restart, Card15/action/current/saturation, safe-stop,
formal timing, primary/independent, and finite-envelope contracts, and define
fail-closed routes before opening outcomes. Reusing immutable probe evidence
for model development does not make it expert data. No R8-family trajectory
may enter expert, BC, DAgger, or RL data.

Do not start expert data, BC, DAgger, or residual RL. Gate A remains blocked;
continue autonomously only along the model-based MPC qualification route and
pause for user confirmation if and only if Gate A is actually reached.

## 104. Frozen R8R16 temporal-affine completion preflight task

Before implementation, fitting, calibration output, missing-code prediction,
ranking, formal outcome, or route, R8R16 was frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R16_TEMPORAL_AFFINE_BINARY_CUBE_COMPLETION_PREFLIGHT_DESIGN.md
SHA-256
2b48e9d6e74222977db1af687009f031aac3da90e9e6b008a856412cc119367b
```

R8R16 is zero-new-TSC. It must authenticate and strictly parse the exact R8R7
baseline, R8R12 `UUUU`, R8R14 `VVVV`, and all final R8R15 evidence. For each
context and state, it models measured `[R,Z,Ip]` response relative to the
matched baseline with fixed code features `[1,q10,q14,q18,q22]`.

The evidence split is immutable:

```text
development       UUUU VVVV UVVV UUVV UUUV VUUU
calibration       VVUU VVVU UVUV VUVU
never executed    UVUU UUVU UVVU VUUV VVUV VUVV
```

The six-code development fit must predict all 64 calibration trajectories
without refitting. Every calibration row must stay within 3 mm R, 3 mm Z,
1000 A Ip, scaled point error 0.10, exact formal pass classification, and
minimum-margin error 0.05. The fixed uncertainty tube is twice the maximum
component/state calibration residual and must stay within 10 mm/10 mm/3000 A.
Primary and structurally independent fits, predictions, formal metrics, and
routes must agree exactly.

Only after calibration passes may the identical model refit all ten measured
codes and predict the exact six missing codes. A missing row is robustly
eligible only when its predicted formal margin remains positive after
subtracting twice the maximum calibration formal-margin error. A PASS needs
at least one robust predicted repair among the ten failed baselines and a
robust predicted oracle at least `7/16`.

Implement, test, package by empty direct copy, transfer without archives,
validate with the existing server environment, and execute the dual zero-TSC
primary/independent preflight. Do not run any new TSC under R8R16. A PASS may
only authorize a separately frozen fresh missing-sequence sentinel; a model
failure requires nonlinear redesign, while an adequate model with no robust
repair requires continuous multidirection redesign.

R8R16 is not a controller, MPC, physical-authority result, or Gate A. No
expert data, BC, DAgger, or RL is authorized, and every R8-family trajectory
remains forbidden from learning data.

## 105. Final R8R16 result and active nonlinear sequence-model boundary

R8R16 completed at design/implementation/package checkpoints
`d68aae4 / d7364e8 / e2325b0`. The 1,066-file empty direct-copy package
passed exact hashes, JSON, shell syntax, compilation, focused `9/9`, and full
`1299/1299` tests locally, in the empty copy, in server staging, and after
installation, with one expected isolated-evidence skip where applicable. No
archive or global Python was used.

The zero-new-TSC primary and structurally independent audits authenticated
the exact R8R15 source hashes and `32 + 96` raw inventories. The frozen design
and full matrices passed rank/condition at `5 / 3.1861406616` and
`5 / 2.6131259298`, and the fixed residual tube passed. Held calibration
reproduced formal classification `64/64`, but passed all numerical gates only
`63/64`: maximum minimum-formal-margin absolute error was
`0.05171944884413282`, above the frozen `0.05` cap. Maximum scaled point error
was only `0.004582066666663117`, and maximum component errors were
`0.137462 mm R / 0.108346 mm Z / 12.6991 A Ip`.

Primary explicit-SVD and independent `lstsq` computations agreed on the
outcome and route with maximum numerical difference `5.329070518200751e-15`.
The six never-executed sequence predictions, repairs, and oracle were not
opened. R8R16 executed zero TSC, controller, plant step, raw, or snapshot.
The final route is:

```text
TEMPORAL_AFFINE_SEQUENCE_MODEL_INADEQUATE_NONLINEAR_SEQUENCE_REDESIGN_REQUIRED
```

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R16_FORENSIC_REPORT.md
SHA-256
55da4885d8d886f9a28b525685b8a9d6665dd841f1186007b7fb054cd786df47
```

R8R16 is immutable. Its downstream zero counts are phase-closed sentinel
values, not a new baseline result. It rules out only the frozen temporal-
affine model, not nonlinear sequence models, the missing sequences, real
MPC, or plant reachability.

Before implementation, fitting, calibration output, missing-sequence
prediction, candidate ranking, or new TSC, freeze a new-identity nonlinear
sequence-model design over already consumed evidence. Preserve an explicit
development/calibration separation, the unchanged numerical and formal caps,
and fail-closed model/authority routes. Do not relax R8R16 after its observed
`0.0517194488` miss. A model PASS may authorize only a separately frozen
fresh physical sentinel.

Gate A, expert data, BC, DAgger, and residual RL remain blocked. Every
R8-family trajectory remains forbidden from learning data.

## 115. Frozen R8R22 bounded continuous-multidirection authority task

After final R8R20 evidence, route, and forensic report were sealed, but
before any R8R22 implementation, construction, raw, TSC, formal metric, or
route, freeze the design at:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R22_BOUNDED_CONTINUOUS_MULTIDIRECTION_AUTHORITY_SENTINEL_DESIGN.md
SHA-256
ae20525ecf55db472e61b0067c6b292b2fc861573723e5977aa72b386ffc8988
```

The exact ten candidates are the Cartesian product of amplitudes
`[1.25,1.50]` and U/V convex weights `[0,.25,.5,.75,1]`, applied as one
constant cumulative coordinate at task steps `[10,14,18,22]`. Primary and
independent offline paths must agree on 160 specs, 640 issue constructions,
and 3,520 exact stored-target refreshes before TSC. Execute 40 safety rows
first; only complete dual raw agreement may authorize the other 120 rows.

Formal evaluation opens only after all 160 raw pass. Preserve the immutable
250/270 ms arrival and 350/370 ms hold contract, exact source reproduction,
baseline `6/16`, and ten failed baselines. A finite authority PASS requires
at least one repair and baseline-plus-new oracle `>=7/16`. A PASS routes to a
separately frozen causal receding-horizon controller design; a FAIL routes to
a separately frozen causal online-feedback model redesign. R8R22 is not MPC
or Gate A, and every trajectory is forbidden from learning data.

## 116. Final R8R22 result and reporting hotfix

R8R22 completed at design/initial-implementation/initial-package checkpoints
`d2627e3 / f08f498 / f9d19c1`. All 1,100 declared hashes, compilation,
focused `12/12`, full `1349/1349`, empty direct-copy, server staging,
installed, and 435-shell `bash -n` gates passed, with one expected isolated-
evidence skip where applicable.

The real campaign completed 160/160 authentic full-horizon trajectories:
40/40 safety and 120/120 qualification. Dual raw audits passed every runtime,
restart/source-prefix, causality, calibration, candidate, exact Card15
target-chain, event, current, finite, forbidden-input, and inventory gate.
There were 640 exact issues and 3,520 refreshes. Maximum issue, refresh, and
current-utilization values were `0.2111111111111112`,
`3.7037037048793097e-06`, and `0.3924`.

The first formal report stopped before metric computation because the
primary R8R20 source loader required 160 rows instead of the authenticated
96. The independent loader and source contract were correct. Reporting-only
checkpoint `cd5c092` changed that constant to 96 and added a dual loader
test; package `fbfe431` passed local/empty/server validation and focused
`13/13`, full `1350/1350`. No physical row was rerun and no controller or
action semantics changed.

Corrected formal evaluation reproduced all 432 rows and old metrics exactly.
The ten new candidates produced 59/160 formal-pass rows, repaired 0/10 failed
baselines, and left the oracle at `6/16`; one largest pure-U candidate
regressed one baseline pass. Every failed context had positive best margin
gain `0.03576556666666786--0.1759552514673881`, median
`0.1249930059791512`, but none crossed the formal gate. Primary and
independent results agreed exactly. Final route:

```text
BOUNDED_CONTINUOUS_MULTIDIRECTION_AUTHORITY_INSUFFICIENT_ONLINE_FEEDBACK_MODEL_REDESIGN_REQUIRED
```

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R22_FORENSIC_REPORT.md
SHA-256
fdeef92777373090e4a170d7b971a132cee36019aff99b237396f3b21efdbe67
```

This is a finite fixed-action-family authority failure, not runtime, raw,
reporting, controller, real-MPC, Gate A, or global reachability evidence.

## 117. Final R8R23 causal online-feedback preflight result

Before the R8R22 qualification raw audit, formal outcome, repair count,
oracle, verdict, or route was opened, R8R23 was frozen at checkpoint
`0f61d94`:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R23_CAUSAL_ONLINE_INNOVATION_RECEDING_HORIZON_PREFLIGHT_DESIGN.md
SHA-256
fc06e9cfe22a4d4a6740e8822259ff1fdfdadbd2c08d72ceb0685a9d11fd6b6d
```

The exact R8R22 authority-FAIL route activates this design. Implement a
zero-new-TSC primary and structurally independent nested whole-pair preflight
over the authenticated baseline, R8R20 Boolean-tree, and R8R22 continuous-
level development evidence. Preserve the fixed causal feature, ridge
penalty, nested maximum-residual tube, support rule, optional already-
observed innovation update and usefulness gate, closed 11-level safe action
tree, formal timing contract, and predicted-feasibility gates exactly as
frozen.

R8R23 must not stitch measured counterfactual states or claim an offline
predicted plan as real control. It runs zero Ray, `gotsc`, TSC, controller,
plant step, raw, or snapshot. A complete PASS may authorize only a separately
frozen fresh-identity real-TSC controller sentinel; a failure requires model
redesign before any controller run.

Gate A, expert data, BC, DAgger, and residual RL remain blocked. Every
R8-family trajectory remains forbidden from expert or policy-learning data.

R8R23 completed at design/implementation/package checkpoints
`0f61d94 / c4af11d / 7b2739c`. The 1,106-file package passed exact hashes,
JSON, Python compilation, focused `6/6`, and full `1356/1356` locally, in a
fresh empty direct-copy tree, in server staging, and after installation.
Server validation additionally passed `bash -n` for all 436 shell files; one
isolated-evidence skip was expected. No archive or global Python was used.

Primary and structurally independent zero-new-TSC paths authenticated all 432
immutable trajectories, constructed the same 1,728 causal origin rows and
11,232 forecast points, and agreed exactly on features, fits, nested tubes,
support, innovation, fail-closed planning, outcome, and route. Maximum fit and
tube differences were both `0.0`.

All point-error and support gates passed. Support was `1728/1728`; maximum
R/Z/Ip/vR/vZ errors were `0.0011597712 m / 0.0032519124 m / 75.2220 A /
0.0177881871 m/s / 0.0431037178 m/s`. The reserved tube nevertheless
contained only `54,497/56,160`, or `0.9703881766381767`, and maximum vR/vZ
half-widths `0.1067713402 / 0.1838597090 m/s` exceeded the frozen `0.08`
caps. The optional innovation update worsened aggregate error to a
`1.2263836369504335` adapted/cold ratio, improved only `1/8` pairs, and
clipped 94 rows. It was correctly disabled.

The failed model gate kept planning closed. Its zero plan/repair fields and
oracle `6/16` are sentinel values, not controller evidence. R8R23 ran zero
Ray, `gotsc`, TSC, controller, plant step, raw, or snapshot. The final route
is:

```text
CAUSAL_ONLINE_FEEDBACK_MODEL_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED
```

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R23_FORENSIC_REPORT.md
SHA-256
20168a98ec3117dd0b8cf0c7979dfd97bfe13db3f8da4bbeb0dff8f231b89b07
```

This is a finite causal model and uncertainty-design failure, not runtime,
deployment, source, raw, restart, causality, reporting, authority,
controller, real-MPC, Gate A, or plant reachability. The 7.22 MB model stays
on the server; only five compact JSON files were downloaded. Every R8-family
trajectory remains forbidden from learning data.

## 118. Active post-R8R23 model-redesign boundary

Before computing any new fit, tube, plan, or controller output, freeze a
new-identity causal model and local uncertainty design. It may use the
consumed R8R23 bank only as explicit development evidence, never as a fresh
controller holdout. It must retain whole-physical-pair separation, causal
visible inputs, the exact action/Card15/current/saturation boundary, the
immutable formal timing contract, structurally independent recomputation,
and fail-closed routing. It may not relax the observed R8R23 containment or
velocity-tube gates post-result.

A zero-new-TSC redesign PASS can authorize only a separately frozen fresh
finite real-controller sentinel. It cannot itself establish MPC, formal
control, or Gate A. Gate A, expert data, BC, DAgger, and residual RL remain
blocked; pause for the user only if the full Gate A policy in Section 0 is
actually satisfied.

## 119. Frozen and implemented R8R24 local-residual-tube preflight

The required new identity was frozen prospectively before any R8R24 fit,
local-residual query, tube, plan, or result:

```text
design checkpoint  218e176
implementation     484f2a9
design SHA-256      213bfaba33bba2559907e68eb53ec186b8a64f33f5eb7164072526fef5631dff
```

Exact design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R24_CAUSAL_LOCAL_RESIDUAL_TUBE_RECEDING_HORIZON_PREFLIGHT_DESIGN.md
```

R8R24 must retain the unchanged R8R23 cold 133-feature ridge point model and
authenticate exact reproduction of its outer coefficients, point metrics,
support outcome, feature digest, and target digest. The failed R8R23
innovation update is disabled rather than retuned. Local tubes are calibrated
only from nested whole-pair OOF residuals, at the same interval and lead
sample, with ordinary Euclidean distance, `k=32`, all kth-distance ties,
componentwise maximum times `1.25`, and fixed physical floors. Tubes may not
be clipped to the frozen caps. Point, 100% containment, tube-cap, 100%
support, finite, forbidden-input, and primary/independent agreement gates are
all fail closed.

Only a complete model PASS opens the unchanged 11-level, four-decision exact
Card15 action tree. A complete planning PASS requires safe plans `16/16`, at
least one predicted repair, zero predicted regressions, and oracle `>=7/16`
under the unchanged 250/270 ms arrival and 350/370 ms hold contract. These
remain development predictions, never measured controller outcomes.

R8R24 completed at design/implementation/package checkpoints
`218e176 / 484f2a9 / 4b22492`. Local, empty-direct-copy, server-staging, and
installed validation passed all 1,112 hashes, 123 JSON parses, compilation of
434 Python files, focused `8/8`, full `1364/1364`, and server `bash -n` for
437 shell files. One server isolated-evidence skip was expected. No archive or
global Python was used.

Primary and structurally independent zero-new-TSC paths authenticated all 432
trajectories and exactly reproduced the R8R23 cold outer models, point
metrics, and support. All source-reproduction maximum differences were `0.0`.
The new local tube used 32--44 neighbors after kth-distance ties and repaired
containment to `56,160/56,160 = 1.0`. Its maximum vR/vZ half-widths were still
`0.105299280302 / 0.181854519985 m/s`, exceeding the unchanged `0.08` caps.
The point, containment, and `1728/1728` support gates passed; the tube-cap gate
failed.

The model failure kept planning closed. Zero safe plans, zero repairs, and
oracle `6/16` remain fail-closed sentinel values. R8R24 ran zero Ray, `gotsc`,
TSC, controller, plant advance, raw, or snapshot. Primary/independent fit,
tube, plan, source reproduction, outcome, and route agreed exactly. Final
route:

```text
CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED
```

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R24_FORENSIC_REPORT.md
SHA-256
23e23051fc0fef84d57d3a5f37b9031e9c1dfab7f07b972e05a6fb12359318ca
```

R8R24 is a finite uncertainty-design failure, not runtime, controller,
real-MPC, Gate A, or plant-reachability evidence. It is immutable. Before any
new model/tube output or controller execution, freeze a new-identity causal
uncertainty redesign. All R8-family trajectories remain forbidden from
expert, BC, DAgger, residual-RL, or any other learning data. Gate A remains
blocked.

## 120. Active post-R8R24 uncertainty-redesign boundary

The exact R8R24 evidence separates point prediction from conservative
uncertainty: held point errors and support pass, and the local tube contains
all held components, but nested velocity residual maxima make the tube too
wide for the frozen planning caps. Do not relax the caps, reduce reserve,
discard residuals, or reinterpret the closed planning sentinel fields under
the R8R24 identity.

Before computing another tube or opening planning, prospectively freeze a
new-identity causal uncertainty mechanism. It must preserve whole-physical-
pair separation, same causal visible/action inputs, exact R8R23 point-model
reproduction unless a new model is explicitly preregistered, immutable formal
timing, hard Card15/action/current/saturation constraints, no clipping,
structurally independent recomputation, and fail-closed routes. Any use of the
R8R23/R8R24 bank is development only and cannot become a fresh controller
holdout.

A development PASS may authorize only a separately frozen fresh finite real-
controller sentinel. It cannot itself establish MPC or Gate A. Gate A and all
learning remain blocked.

## 121. Frozen and implemented R8R25 outer-jackknife tube preflight

Before any R8R25 tube, containment, cap, plan, or route was computed, the
training-cardinality-matched design was frozen and then made algorithmically
complete without outcome inspection:

```text
initial design checkpoint       cc0dee5
support clarification           e37f84f
implementation checkpoint       9089006
final design SHA-256             bb051a7318e4032c742d98fd91b273e4a00350d918d8f1412369672be1306e0a
```

Exact design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R25_TRAINING_CARDINALITY_MATCHED_OUTER_JACKKNIFE_TUBE_PREFLIGHT_DESIGN.md
```

R8R25 keeps the exact cold R8R23/R8R24 point model. For evaluation of held
pair `p`, its tube uses only outer OOF residual groups from the other seven
pairs; `p`'s own residual is excluded. Every residual-producing outer model
was trained on seven complete pairs, matching the evaluated model's training
cardinality. Tubes remain fixed by interval/lead, componentwise maximum times
`1.25`, fixed physical floors, no distance model, no quantile, no outlier
deletion, and no clipping. All point, containment, cap, support, finite,
forbidden-input, source-reproduction, and dual-agreement gates remain
all-or-nothing.

Only a complete model PASS opens the unchanged 11-level action tree. Its
all-eight point model uses all eight outer residual groups and an all-pair
support threshold fixed as `1.5` times the maximum leave-one-whole-pair
nearest-neighbor distance. Planning still requires safe plans `16/16`, at
least one predicted repair, zero regressions, and oracle `>=7/16` under the
unchanged formal timing and hard action boundary.

Local project-venv compilation, focused `9/9`, and Windows-resource-shimmed
full `1373/1373` passed. The active task is to update package manifest and
sums, validate a fresh direct-copy tree, transfer without archives, validate
server staging and installed files with the existing server virtual
environment, then run primary, structurally independent, and postprocess
paths with zero Ray, `gotsc`, TSC, controller, plant advance, raw, or snapshot.

Even a complete R8R25 PASS authorizes only freezing a separate fresh finite
real-controller sentinel. R8R25 is not MPC or Gate A. All R8-family evidence
remains forbidden from expert, BC, DAgger, residual-RL, or other learning
data; Gate A remains blocked.

## 113. Final R8R20 direct Boolean-cube completion result

R8R20 completed at design/implementation/package checkpoints
`f13e88a / ad64f09 / 98c67c5`. Local, empty-direct-copy, server-staging, and
installed validation passed all 1,094 declared hashes, compilation, focused
`11/11`, and full `1337/1337`, plus real server `bash -n`; one server
isolated-evidence skip was expected.

The first `_v1` safety launch lost its controlling SSH session after all 24
TSC tasks had started. No task raw was persisted, no formal outcome was
opened, and checkpoint `9921657` prospectively froze that run as a preserved
infrastructure/result-persistence failure. It may not be resumed or used as
scientific or learning evidence. A clean byte-identical `_v2` replacement
was authorized before any outcome inspection.

Valid v2 completed all `24 + 72 = 96` authentic trajectories. Primary and
independent audits passed every runtime, horizon, source-prefix, causality,
calibration, sequence, target-chain, Card15, action, current, finite,
forbidden-input, raw, and inventory gate. Formal evaluation reproduced all
immutable source metrics exactly, but all sixteen complete-cube codes passed
only the same `6/16` baseline contexts. Repairs were `0/10`, regressions
`0/6`, and the held complete-cube oracle was `6/16`, below the frozen
`>=7/16` requirement. Primary/independent maximum margin difference was
exactly `0.0`.

The final route is:

```text
DIRECT_BOOLEAN_CUBE_AUTHORITY_INSUFFICIENT_CONTINUOUS_MULTIDIRECTION_REDESIGN_REQUIRED
```

Every failed context nevertheless had a positive best-candidate margin gain
of `0.025541733333334093--0.1364830983921772`. This supports a bounded
continuous-amplitude/multidirection redesign but is not a formal repair. It
does not show runtime failure, wrong-direction action, real MPC failure, or
global plant unreachability.

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R20_FORENSIC_REPORT.md
SHA-256
d7a86439b31d5d71f94ff96e05f8260e7503f20981660f4aae4e9866516be7ea
```

## 114. Vetoed conditional R8R21 selector and active boundary

Before R8R20 formal outcomes were opened, a conditional zero-TSC causal
Boolean action-tree selector was frozen at checkpoint `fdf196c`:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R21_CAUSAL_BOOLEAN_ACTION_TREE_SELECTOR_PREFLIGHT_DESIGN.md
SHA-256
781df71aa196ceae8f9441f1bc1f16540db97ccb26fbe44d87b716ff9e72d734
```

Its activation condition required the R8R20 finite-authority PASS route.
R8R20 took the authority-FAIL route, so R8R21 is vetoed without
implementation, fitting, output, Ray, TSC, controller, plant step, raw, or
snapshot. Its thresholds may not be repurposed post-result.

Before any new implementation, fit, optimization, candidate selection, or
TSC, freeze a new-identity bounded continuous-multidirection authority
design. It must use a prospective development/calibration/holdout separation,
allowed visible causal state only, exact Card15 targets, unchanged hard
action/current/saturation/safe-stop gates, the immutable 250/270 ms arrival
and 350/370 ms hold contract, and structurally independent auditing. The
observed R8R20 margin gains may motivate the bounded family but may not be
used to tune on rows later claimed as fresh holdout.

R8R20 and all R8-family trajectories remain forbidden from expert, BC,
DAgger, and RL data. Gate A remains blocked; continue autonomously only on
the model-based controller qualification route.

## 111. Final R8R19 result and active direct-cube-completion boundary

R8R19 completed at design/implementation/package checkpoints
`f4c842b / e62c563 / 51b429a`. Local, empty-direct-copy, server-staging, and
installed validation passed all 1,087 hashes, compilation, focused `9/9`, and
full `1326/1326`, with one expected isolated-evidence skip where applicable.
Real server `bash -n` passed every declared shell file. No archive, global
Python, server Git, or new TSC execution was used.

The primary augmented-SVD and structurally independent normal-equation audits
authenticated final R8R15--R8R18 evidence and agreed to
`7.105427357601002e-14`. All frozen Boolean-code geometry, stability, point-
error, exact formal-classification `160/160`, and tube gates passed, but only
`156/160` LOCO rows passed the complete model gate. Maximum minimum-formal-
margin error was `0.06413974895404673 > 0.05`; maximum scaled point error was
`0.006226528571431423`.

The missing-code authority phase was not opened. R8R19 created zero TSC,
controller step, plant step, raw, or snapshot. The final route is:

```text
SATURATED_BOOLEAN_KERNEL_MODEL_INADEQUATE_DIRECT_CUBE_COMPLETION_REDESIGN_REQUIRED
```

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R19_FORENSIC_REPORT.md
SHA-256
7cecea2eefc36991bde612452bcf3cc0cac5f9f34b2a1c778825f08ffdf5c939
```

R8R19 is immutable. Its phase-closed zero counts are not physical outcomes.
The fixed predictor is vetoed, not the six missing physical sequences or the
plant. Before any new response is produced, freeze a new-identity direct
finite-cube-completion design for exactly
`UVUU,UUVU,UVVU,VUUV,VVUV,VUVV` over the same sixteen contexts. Use a
prospective fail-closed safety/qualification split, retain every existing
Card15, restart, causality, current, formal-timing, raw-integrity, and
independent-audit gate, and forbid all resulting trajectories from learning.

Direct completion may answer only finite authority and sequence-selection
questions. It is not MPC or Gate A. Gate A, expert data, BC, DAgger, and
residual RL remain blocked.

## 112. Frozen R8R20 direct Boolean-cube completion task

After final R8R19 evidence, route, and forensic report were sealed, but
before any R8R20 implementation, configuration, construction, raw, TSC,
formal output, or route, freeze the design at:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R20_DIRECT_BOOLEAN_CUBE_COMPLETION_AUTHORITY_SENTINEL_DESIGN.md
SHA-256
8b49ef5f49d15b994cc4fc8b1a94313fa2782c297f98a31863e35e6886f1c07c
```

Authenticate complete final R8R15 and R8R19 evidence. Execute only the six
previously unmeasured codes `UVUU,UUVU,UVVU,VUUV,VVUV,VUVV` over the same
sixteen R8R15 contexts using byte-identical U/V symbols, task steps
`[10,14,18,22]`, causal target refresh, exact Card15, and source prefix
through task step 9. Existing ten codes must not be rerun.

Before any plant advance, primary and structurally independent offline paths
must agree on all 96 specs, 384 exact issues, and 2,112 exact target refreshes
and pass every unchanged action/current/cosine/off-basis/saturation gate.
Execute the prospectively frozen `24`-trajectory safety phase first. Only
complete primary/independent raw and execution agreement may authorize the
remaining `72` qualification trajectories.

Formal evaluation opens only after all 96 raw files pass. Preserve the
250/270 ms arrival and 350/370 ms hold contract, formal metric equivalence
`1e-12`, baseline `6/16`, and ten failed baselines. A finite authority PASS
requires at least one R8R20 repair and complete-cube held oracle `>=7/16`.
A PASS authorizes only a separately frozen causal selector/receding-horizon
controller design; a FAIL routes to separately frozen bounded continuous-
multidirection redesign.

Implement, validate, package by empty direct copy, deploy without archives,
and execute fail-closed safety then qualification with dual raw and formal
audits. R8R20 is not MPC or Gate A. Gate A, expert data, BC, DAgger, and
residual RL remain blocked, and every R8-family trajectory is forbidden from
learning data.

## 110. Frozen R8R19 saturated Boolean kernel LOCO task

After sealing final R8R18 evidence, report, and route, but before any R8R19
response fit or output, freeze the new design at:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R19_SATURATED_BOOLEAN_KERNEL_LOCO_PREFLIGHT_DESIGN.md
SHA-256
e0d8529512da14e144c3dfa7502ccc905a59b4f7cdef8ff9e73fc7cf927bdb25
```

R8R19 uses the complete 16-column Walsh basis on the fixed four-slot Boolean
cube: intercept, four signs, six pairs, four triples, and the quadruple term.
The affine five-dimensional subspace is unpenalized; all eleven nonlinear
terms use the single frozen penalty `lambda=10`. This was selected only from
the closed code-geometry grid `[0.1,0.3,1,3,10]` as the first value satisfying
LOCO normal condition `<=64` and prediction-weight L2 `<=1.25`. R8R18 failed-
row identities and response values do not select any R8R19 feature or
hyperparameter.

Authenticate complete final R8R15--R8R18 evidence. Validate all ten measured
codes with ten leave-one-code-out folds over all 16 contexts, exactly 160
predictions. All `160/160` must pass the unchanged 3 mm/3 mm/1000 A, scaled
`0.10`, exact formal classification, minimum-margin `0.05`, and twice-residual
tube gates. Primary augmented SVD and independent normal-equation paths must
agree.

Only a complete model PASS may fit all ten codes and predict the same six
never-executed sequences. Robust authority remains at least one of ten failed-
baseline repairs and oracle `>=7/16` after the frozen two-times LOCO margin
buffer. A PASS authorizes only a separately frozen fresh physical sentinel;
a model failure routes to separately frozen direct finite-cube completion,
while an adequate model without authority routes to continuous
multidirection redesign.

Implement, validate, package by empty direct copy, deploy without archives,
and execute dual zero-TSC audits. R8R19 is not MPC or Gate A. Learning stays
blocked and all R8-family evidence remains forbidden from learning data.

## 106. Frozen R8R17 adjacent-switch interaction preflight task

After R8R16 was finalized but before inspecting its failed-row identity or
any R8R17 fit/output, the new nonlinear design was frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R17_ADJACENT_SWITCH_INTERACTION_BINARY_CUBE_PREFLIGHT_DESIGN.md
SHA-256
5432fe3f292800910dc8f70e979fc4db89ffee3fa6053ad22383b9029ebc73d0
```

R8R17 keeps the exact R8R16 development/calibration/missing split and all
numerical, formal, tube, and authority caps. It adds exactly one fixed
normalized sequential interaction:

```text
a(q) = (q10*q14 + q14*q18 + q18*q22) / 3
x(q) = [1,q10,q14,q18,q22,a(q)]
```

This feature was chosen from action-sequence structure and code-only matrix
geometry, not R8R16 per-row residuals. Frozen development/measured/cube
rank-condition values are `6/6.6990427629`, `6/2.6131259298`, and
`6/1.7320508076`.

R8R17 must authenticate the complete final R8R16 output and original R8R15
evidence, fit only the six development codes, and predict the same four held
calibration codes. All `64/64` trajectories must pass the unchanged 3 mm,
3 mm, 1000 A, scaled `0.10`, exact formal classification, minimum-margin
`0.05`, and fixed tube gates. Primary SVD and structurally independent
`lstsq` paths must agree.

Only a complete model PASS may refit all ten measured codes and predict the
same six never-executed codes. Robust authority still requires at least one
of ten failed-baseline repairs and oracle `>=7/16` after subtracting twice
the maximum held margin error. R8R17 is zero-new-TSC; a PASS authorizes only
a separately frozen fresh physical sentinel. A model failure routes to a
higher-order redesign; an adequate model with no authority routes to
continuous multidirection redesign.

Implement, validate, package by empty direct copy, deploy without archives,
and execute dual zero-TSC audits. R8R17 is not MPC or Gate A. No R8-family
trajectory may enter expert, BC, DAgger, or RL data.

## 107. Final R8R17 result and active higher-order model boundary

R8R17 completed at design/implementation/package checkpoints
`614487a / 6b62ca6 / d7d291a`. The 1,073-file package passed exact hashes,
JSON, compilation, focused `9/9`, and full `1308/1308` tests locally and in
the empty direct-copy tree. Server staging and installed validation also
passed every hash, JSON, declared-shell `bash -n`, compilation, focused
`9/9`, and full `1308/1308`, with one expected isolated-evidence skip where
applicable.

The dual zero-new-TSC audits reauthenticated R8R15 and final R8R16. All
frozen development/measured/cube rank-condition gates passed at
`6/6.6990427629`, `6/2.6131259298`, and `6/1.7320508076`. All `64/64`
formal classifications and the fixed tube passed, but only `61/64` held
trajectories passed every gate. Maximum minimum-formal-margin error was
`0.09336026574612744 > 0.05`; maximum scaled point error was only
`0.008405966666665465`. Primary and independent results agreed with maximum
numerical difference `2.1316282072803006e-14`.

The missing-code authority phase was not opened. R8R17 created zero TSC,
controller step, plant step, raw, or snapshot. The final route is:

```text
ADJACENT_SWITCH_INTERACTION_MODEL_INADEQUATE_HIGHER_ORDER_REDESIGN_REQUIRED
```

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R17_FORENSIC_REPORT.md
SHA-256
0162fa79e7fea0cb5ba8ef309eabed6be387341436b02c09e490b3426157852a
```

R8R17 is immutable. It rejects only the one prospectively fixed adjacent-
switch interaction. Its phase-closed zero counts are not baseline or
physical results.

Before inspecting the identities of the three failed held rows, freeze a
new-identity higher-order sequence model. Because more than six parameters
cannot be identified from the old six-row development set without a prior,
use all ten measured codes only through a prospectively specified leave-one-
code-out calibration, fixed Boolean interaction features and fixed
regularization. Keep missing physical outcomes closed and retain the
unchanged gates and fail-closed routes.

Gate A, expert data, BC, DAgger, and residual RL remain blocked. Every R8-
family trajectory remains forbidden from learning data.

## 108. Frozen R8R18 second-order Boolean ridge LOCO task

After sealing aggregate R8R17 but before inspecting any of its failed-row
identities or detailed residuals, the next zero-new-TSC design was frozen in:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R18_SECOND_ORDER_BOOLEAN_RIDGE_LOCO_PREFLIGHT_DESIGN.md
SHA-256
f7de518d1bc65588883d245eb7fd1de5f63b84c679713b38102db6047d28ab9d
```

R8R18 uses the fixed 11-feature Boolean family containing intercept, four
slot signs, and all six pair interactions. Affine terms are unpenalized; all
pair terms use one frozen ridge penalty `lambda=10`. That value was chosen
only from a closed code-geometry grid as the first entry satisfying maximum
LOCO normal condition `<=32` and prediction-weight L2 `<=1.30`; response
outcomes do not select it.

The exact ten measured codes are validated by ten leave-one-code-out folds,
giving `160` held trajectory predictions. All `160/160` must pass the
unchanged 3 mm/3 mm/1000 A, scaled `0.10`, exact formal classification,
minimum-margin `0.05`, and fixed two-times tube gates. Every fold retains
affine rank five and the regularized augmented system must have rank 11.
Primary augmented-SVD and independent normal-equation solves must agree.

Only a complete LOCO model PASS may fit all ten measured codes and predict
the same six never-executed sequences. Robust authority remains at least one
of ten repairs and oracle `>=7/16` after the frozen two-times LOCO margin
buffer. A PASS authorizes only a separately frozen fresh physical sentinel;
a model failure routes to nonparametric redesign, while an adequate model
without authority routes to continuous multidirection redesign.

Implement, validate, package by empty direct copy, deploy without archives,
and execute dual zero-TSC audits. R8R18 is not MPC or Gate A. Learning stays
blocked and all R8-family evidence remains forbidden from learning data.

## 109. Final R8R18 result and active nonparametric boundary

R8R18 completed at design/implementation/package checkpoints
`1366017 / 7dae75a / e5003f5`. Local, empty-direct-copy, server-staging, and
installed validation passed all 1,080 hashes, compilation, focused `9/9`, and
full `1317/1317`, with one expected isolated-evidence skip where applicable.
Real server `bash -n` passed every shell file. A checksum-line parsing error in
the first restricted install copy loop was fully recovered from the already-
validated staging tree before any run; installed hashes and the complete test
suite then passed. No run output, raw, or virtual-environment file changed.

The primary augmented-SVD and structurally independent normal-equation audits
authenticated R8R15, R8R16, and R8R17 and agreed to
`8.881784197001252e-15`. All code geometry, stability, point-error, exact
formal-classification `160/160`, and tube gates passed, but only `157/160`
LOCO rows passed the complete model gate. Maximum minimum-formal-margin error
was `0.05685241823211573 > 0.05`; maximum scaled point error was
`0.0061002004751214535`.

The missing-code authority phase was not opened. R8R18 created zero TSC,
controller step, plant step, raw, or snapshot. The final route is:

```text
SECOND_ORDER_BOOLEAN_RIDGE_MODEL_INADEQUATE_NONPARAMETRIC_SEQUENCE_REDESIGN_REQUIRED
```

Exact report:

```text
docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R18_FORENSIC_REPORT.md
SHA-256
22560269b6716e695c6a6c110536de5bc4765dd6d476755721e501625ca9ec1d
```

R8R18 is immutable. Its phase-closed zero counts are not physical outcomes.
Freeze a new-identity code-only nonparametric sequence prior and every
hyperparameter before computing response predictions. Retain all 160 LOCO
rows, unchanged physical/formal gates, the same six closed physical outcomes,
dual implementations, and fail-closed authority routing.

Gate A, expert data, BC, DAgger, and residual RL remain blocked. Every
R8-family trajectory remains forbidden from learning data.
