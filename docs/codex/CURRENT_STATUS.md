# Current status

> Superseding status (2026-07-31 Asia/Shanghai): T6 completed 224/224 but
> failed its combined-bank design gate after a reporting-only hotfix. T7
> repaired conditioning but remained 16/32 with 0/16 repairs. T8 then
> expanded only the three new target directions through 4× under
> independently recomputed 14-coil current constraints; every scale
> remained 16/32 and maximum predicted current stayed 0.3904. Thus current
> headroom is not the bottleneck, R3c4 remains unauthorized, and the active
> route is a new target-relevant temporal/actuator combined-action
> identification preflight. See `docs/codex/CURRENT_TASK.md` sections
> 12--14 and `STAGE4_2R3C3T8_HEADROOM_DIAGNOSTIC_REPORT.md`. No T8 TSC,
> Ray, `gotsc`, controller or plant run occurred.

## Stage4.2R3c3T1 failed cleanly; Stage4.2R3c3T2 is preregistered

Status timestamp: 2026-07-31 Asia/Shanghai

Current local branch:

```text
codex/stage4_2r3c3t1-transport-response
```

Current checkpoints:

```text
b8e66da  preregister T1 transport response
ba8c455  implement and deploy T1 campaign
```

## T1 real result

Remote run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_runs/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441
```

Remote audit:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_audits/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441
```

Compact local evidence:

```text
docs/codex/audits/stage4_2r3c3t1_result_20260730_204441/
```

Result:

```text
raw / execution / exact restart / causal             128/128
central symmetry                                       64/64
matched history                                        32/32
transport-only condition                               32/32
combined rank six                                      32/32
combined condition <= 25                               27/32
worst combined condition                          29.2962711
runtime / restart / causal / solver errors                  0
maximum current utilization                           0.3904
formal probe diagnostic pass/fail                      56/72
```

T1 is frozen as FAIL because of the preregistered combined-condition gate.
Formal tracking was diagnostic-only and was not used to change that result.

Fingerprints:

```text
runtime/audit package
  cea1e49470afed77387cdf3d636de38541c47998846a817edc32dafd9b60f44a

raw inventory
  f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f

run inventory
  159ee8f85fc07fec52280cb0f153a75d5f24b8bf69629502f8177b7810567c52

server audit
  0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd
```

No T1 task was resumed or rerun after completion.

## T1 forensic classification

```text
runtime/environment error                    no
package/deployment error                     no
raw/snapshot corruption                      no
T1 statistics/reporting error                no
plant restart failure                        no
real MPC control result                      not tested
identification-design failure                yes
```

The first read-only six-basis feasibility tool used position arrays for the
velocity condition calculation. Its invalid output is preserved with SHA
`a19169f1...`. Corrected v2 exactly reproduces the T1 27/32 condition count
and 29.2962711 maximum before computing formal feasibility:

```text
corrected diagnostic
  e7bc8f0168ff1d2019f1a9a232b5152a27d46a66a92f9542d31d80c6942c3164

optimistic six-basis formal pass               16/32
failed baseline contexts repaired               0/16
best remaining failed margin                -0.0458576
worst remaining failed margin               -0.3456933
```

Reducing transport mode 0 to scales 0.85, 0.80, 0.75, or 0.70 repairs
conditioning to 32/32 but leaves formal feasibility at 16/32. An
amplitude-only T2 is therefore vetoed before execution.

Full T1 report:

```text
docs/codex/reports/STAGE4_2R3C3T1_FORENSIC_REPORT.md
```

## Active T2 design

Prospective design:

```text
docs/codex/reports/STAGE4_2R3C3T2_PREREGISTERED_DESIGN.md
```

Frozen schedule:

```text
observation horizon                    50 steps / 500 ms
positive physical effects             states 3..8
negative physical effects             states 39..44
observation tail                       states 45..50
held transport mode 0 amplitude       0.0060
held transport mode 1 amplitude       0.0075
signed probe tasks                    128
```

Pre-implementation design review found that the 500 ms symmetry metric needs
a real baseline beyond the 350/370 ms source horizon. Design revision 2
therefore adds one zero-probe extended baseline per context:

```text
extended baselines                     32
signed probes                         128
total real TSC tasks                  160
```

No T2 code, offline run, server deployment, or real TSC preceded this
prospective correction.

The first negative physical effect is after both original formal hold
endpoints. Arrival remains due by 250/270 ms and formal hold remains through
350/370 ms. The longer run is identification-only, not a later deadline or
long-hold success.

Next implementation steps:

1. create a focused T2 branch and implementation checkpoint;
2. implement standalone config/module/launch/postprocess/tests;
3. complete local compile/JSON/full-test/import/package/empty-copy checks;
4. deploy directly without archives and validate the canonical server tree;
5. run the 160-spec offline no-TSC audit;
6. launch exactly one real T2 identity;
7. postprocess large raw server-side and download only compact evidence;
8. require T2 identification gates, then six-basis optimistic feasibility
   32/32 before any R3c4 implementation.

## Still unvalidated

A reliable restart MPC expert, independent histories and initial states,
unseen targets, continuous actuator and plant variation, noise, observer,
disturbance recovery, and independent long hold remain unvalidated.

BC, DAgger, and bounded residual RL remain prohibited.

## Stage4.2R3c3T9 preflight handoff

The post-T8 PC3/mixed-action preflight is complete at commit `cbb970b`.
No T9 TSC was executed.

```text
preflight gates                                      all PASS
PC3 singular value normal / weak            1.134704 / 0.777812
minimum four-direction coverage             0.999912 / 0.995362
complete action rank / condition             12 / 2.551060
selected action rank / condition              9 / 1.230022
factorial common amplitude                         0.0106066
prospective real task count                                224
```

Exact compact output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t9_preflights/
stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b/
stage4_2r3c3t9_pc3_mixed_interaction_preflight_v1.json

SHA-256
9a37168cce679df7deeb242bceb996c11f41bf9e589459e27386ece45f41e560
```

The active work is implementation of the frozen independent real
identification matrix:

```text
32 extended baselines
64 standalone PC3 signed probes
128 direct stress-by-PC3 factorial probes
```

This preflight does not authorize R3c4. Reliable MPC, independent unseen
histories/targets, continuous parameters, noise, disturbance recovery, and
independent long hold remain unvalidated. BC, DAgger, and residual RL remain
prohibited.
