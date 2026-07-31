# CURRENT_TASK.md — post-T2 six-basis optimistic feasibility

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

## 9. Failed six-basis gate and active complementarity audit

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

The active task is a new read-only eight-basis complementarity audit:

```text
R3c3 local four
+ T1 long-separation two
+ T2 held-transport two
```

It must retain the unchanged gate:

```text
eight-basis optimistic formal feasibility               32/32
coefficients                                             [-1,1]
baseline pass regression                                      0
formal timing unchanged                                      yes
```

All numeric thresholds, coefficient bounds, timing, baselines, and 32
contexts stay unchanged. It must authenticate exact R3c3, T1, and T2
raw/bank inventories and emit compact per-context evidence. It is not a real
TSC campaign.

If this fails, do not implement or launch R3c4. If it passes 32/32 with no
route choice, prospectively freeze and implement R3c4 as a new independent
controller identity, then complete the local-server-download-analysis loop.

Even a pass does not validate a reliable restart MPC, independent histories,
unseen targets, continuous actuator/plant parameters, noise, disturbance
recovery, or long hold.

BC, DAgger, and bounded residual RL remain prohibited.
