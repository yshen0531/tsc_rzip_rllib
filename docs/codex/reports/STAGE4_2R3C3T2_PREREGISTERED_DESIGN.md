# Stage4.2R3c3T2 preregistered design

## Implementation hotfix record

The first real execution attempt used package
`r42r3c3t2_post_contract_held_transport_identification_v2`:

```text
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t2_runs/
  stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_222433

driver PID
  1458105

structured raw failures
  11/11 RuntimeError('environment truncated before T2 horizon')

successful trajectories
  0
```

The inherited R3c3 payload builder replaced the intended 50-step episode
limit with its frozen 35/37-step formal horizon. The resolved payloads and
all 11 raw tracebacks agree on this cause. The exact T2 driver was stopped;
all raw, manifest, state, and log evidence was preserved.

This is an implementation/runtime error, not a plant-restart, controller,
identification, statistics, or reporting result. It does not change the
prospectively frozen 50-step design. Package
`r42r3c3t2_post_contract_held_transport_identification_v2h1` only restores:

```text
train_cfg.episode.max_episode_steps = 50
stage4_1r4_horizon_steps            = 50
```

It adds pre-TSC payload/environment horizon guards. Controller actions,
probe schedules, amplitudes, contexts, formal 35/37-step evaluation
prefixes, gates, and information boundaries are unchanged. Because the
package fingerprint changed and the old raw files are structured failures,
the failed run is not resumed or overwritten; v2h1 uses a fresh run
directory.

## 0. Pre-implementation design correction

The first prospective draft contained 128 signed probe tasks but no
unprobed 500 ms baseline. The frozen R3c1 source trajectories end at their
350/370 ms formal horizons, so they cannot authenticate central symmetry
over the new states 38--50.

This was found before T2 code, deployment, offline execution, or real TSC.
Design revision 2 adds one real zero-probe extended baseline per context.
No observed T2 result exists, and no gate was changed after data inspection.

```text
design revision                           2
extended zero-probe baselines            32
signed probe tasks                       128
total real TSC tasks                     160
```

## 1. Purpose and scientific route

Stage4.2R3c3T2 is a new real-TSC identification identity. It does not resume
or relabel Stage4.2R3c3T1.

T1 proved that its two long-separation responses were authentic and locally
symmetric, but:

```text
combined velocity condition                         27/32
six-basis optimistic formal feasibility             16/32
failed R3c1 contexts repaired                         0/16
```

An authenticated scale scan showed that reducing transport mode 0 can repair
conditioning but cannot repair any formal context. An amplitude-only T2 is
therefore rejected before execution.

The active design defect is temporal: T1 cancels its positive block at states
15--20, before the 250/270 ms arrival deadline and well before the 350/370 ms
hold endpoint. R3c3T2 instead identifies a response that remains active
through the complete immutable formal contract and neutralizes only after
that contract has ended.

This is identification, not MPC control, restart certification, long-hold
certification, or training data.

## 2. Frozen sources

Required T1 source:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_runs/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441
```

Required T1 fingerprints:

```text
raw count
  128

raw inventory digest
  f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f

server audit
  0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd

corrected six-basis diagnostic
  e7bc8f0168ff1d2019f1a9a232b5152a27d46a66a92f9542d31d80c6942c3164
```

Required R3c3 bank:

```text
audit bank
  51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32

controller bank
  6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0

manifest
  a17322dcfc1d019de0455950c95e45b0b7d0f8f29fc3c68a22211481f261a066

provenance
  5ec49166e59df915105d4411df36a9901db56f365594b83ff08bbc6abf3751f6
```

The exact R3b restart snapshots, R3c1 baseline identities, visible-manifold
controller, R17 source, and all inherited fingerprints remain unchanged.

T1 must authenticate as a completed primary FAIL caused only by the frozen
combined-condition gate. T2 must refuse a source whose raw, manifest,
package, or forensic identity differs.

## 3. New experiment identity

```text
stage
  Stage4.2R3c3T2

controller revision
  post_contract_neutralized_held_transport_probe_v42r3c3t2_v2

package revision
  r42r3c3t2_post_contract_held_transport_identification_v2

run name
  stage4_2r3c3t2_post_contract_neutralized_held_transport_identification

observation horizon
  50 steps / 500 ms
```

No T1 raw file may be copied into the T2 raw directory. T2 has its own
manifest, resolved config, state, logs, raw identities, summaries, verdict,
and server audit.

## 4. Immutable formal timing

The longer identification observation does not change the formal contract:

```text
slew 1.0:
  arrival no later than state 25 / 250 ms
  formal hold through state 35 / 350 ms

slew 0.9:
  arrival no later than state 27 / 270 ms
  formal hold through state 37 / 370 ms

R/Z tolerance                 0.03 m
speed threshold               0.1 m/s
Ip thresholds                 frozen
arrival streak                frozen
```

States after 35/37 are identification neutralization and observation only.
They may never become later allowed arrival or hold endpoints.

## 5. Frozen probe schedules

Two physical modes are identified:

```text
held_transport_mode0 amplitude     0.0060
held_transport_mode1 amplitude     0.0075
probe signs                        -1, +1
```

The mode-0 amplitude is fixed prospectively at 80% of the T1 amplitude. In
the exact T1 response-column scan, this gave 32/32 combined-condition passes
with worst condition `23.5281276`, leaving more margin than the fragile
0.85 scale while retaining more authority than 0.75 or 0.70. Because the
temporal schedule changes, this is design evidence only; T2 must validate
the new response in real TSC.

For each sign and mode, the physical-effect schedule is:

```text
positive block       states 3, 4, 5, 6, 7, 8
quiet/held interval  states 9 through 38
negative block       states 39, 40, 41, 42, 43, 44
observation tail     states 45 through 50
```

The negative block is the exact opposite of the positive block. Requested
and applied physical coefficient sums must both equal zero to absolute
tolerance `1e-12`.

For actual delay `d`, an effect at state `s` is issued at task step:

```text
issue_step = s - d - 1
```

Thus the controller is causal and delay-aware. For delay 2, the first
neutralizing command is issued at task step 36 but remains in the validated
actuator queue until its first physical effect at state 39, after the weak
formal hold endpoint.

## 6. Matrix

The exact locked development matrix is:

```text
32 restart contexts
x (
    1 zero-probe extended baseline
    + 2 held-transport modes x 2 signs
  )
= 160 real TSC tasks
```

The 32 contexts remain:

```text
4 authenticated hidden-history members
x 2 targets
x 2 locked actuator settings
```

No context may be removed, duplicated, reweighted, or replaced after
inspection.

The zero-probe row runs the same causal R3c1 controller through state 50
without a T2 correction. Its prefix through state 35/37 must exactly match
the authenticated R3c1 source trajectory for that context. It is the only
permitted baseline for T2 central-symmetry metrics after the source formal
horizon.

## 7. Controller information boundary

The T2 controller may use only:

- current and past visible R/Z/Ip;
- current and past 14-coil currents;
- target R/Z/Ip;
- causal actuator delay/gain/slew values available at task start;
- the exact R3c1 visible-manifold controller;
- its own prospectively frozen task-clock probe schedule.

Forbidden:

- source or current wire/vessel currents;
- T1 or R3c3 source actions, trajectories, outcomes, or formal labels;
- future state, future action, or future actuator values;
- pair, hidden-history, common-prefix, source-experiment, or other-member
  identity;
- post-action telemetry at the current decision step.

T1 raw and audit files may be read only by offline/server postprocessors, not
by the online controller.

## 8. Primary identification gates

Execution:

```text
environment complete / exact restart / causal trace       160/160
zero-probe extended baseline exact                           32/32
exact 12-issue requested/applied schedule                  128/128
requested and applied net zero                             128/128
runtime / solver / clipping / forbidden-input errors              0
maximum current utilization                                    <= 0.55
```

Central odd-response validity over all states 0--50:

```text
even R/Z velocity RMSE                              <= 0.004 m/s
even R/Z position RMSE                              <= 0.0005 m
even Ip RMSE                                        <= 20 A
```

Matched-hidden-history validity over all states 0--50:

```text
odd R/Z velocity RMSE                               <= 0.006 m/s
odd R/Z position RMSE                               <= 0.001 m
odd Ip RMSE                                         <= 40 A
```

The controller-use condition window is fixed to states 3 through the
original formal hold endpoint for that context: state 35 for slew 1.0 and
state 37 for slew 0.9. The post-contract neutralization tail is excluded
from the controller-use matrix and reported separately.

```text
held-transport rank / condition per context               2/2, <= 25
old four + new two rank / condition per context            6/6, <= 25
```

All gates must pass in every required group.

Formal tracking of the signed identification trajectories remains
diagnostic-only. The longer 500 ms horizon is not a long-hold success test.

## 9. Mandatory offline and server validation

Before real TSC:

1. compile all changed Python and parse all JSON;
2. run focused and complete repository tests;
3. verify import closure, package manifest, and checksums;
4. authenticate exact R3b/R3c1/R3c3/T1 sources and fingerprints;
5. verify 32 contexts, 32 baseline identities, 128 signed probe identities,
   and exactly 160 total identities;
6. verify effect/issue mapping for both delays;
7. verify the first negative physical effect is state 39 in every row;
8. verify exact requested/applied zero-net schedule logic;
9. test current, hidden-wire, future-information, and label guards;
10. test source fingerprints and resume compatibility;
11. simulate direct-copy deployment in an empty repository-local directory;
12. validate staging and canonical server trees with the existing venv;
13. run a no-TSC offline controller audit for all 160 specs;
14. prove offline raw count zero, plant advances zero, and real TSC false.

Only then may exactly one 160-task T2 identity be launched.

## 10. Server evidence loop

The run must be monitored by its exact PID and log. All raw JSON.GZ and TSC
work products remain on the server. The server postprocessor must:

- authenticate all 160 raw identities and specs;
- recompute execution, restart, causality, schedule, current, symmetry,
  history, condition, and formal-prefix diagnostics from raw;
- record a complete raw and run inventory with hashes;
- compare runtime and audit package fingerprints;
- preserve partial trajectories as structured failures;
- emit compact JSON/log evidence for direct download.

No failure may be converted to `inf` merely because a comparison is
non-applicable.

## 11. Advancement gate

If and only if all T2 identification gates pass, build a new combined bank
server-side and run the unchanged optimistic formal feasibility audit:

```text
exact R3c1 baseline
+ bounded old four R3c3 odd responses
+ bounded new two T2 held-transport odd responses
```

Required:

```text
all 32 contexts formally feasible
all six coefficients in [-1, 1]
baseline pass regressions 0
arrival/hold timing unchanged
```

If this gate fails, do not implement or launch R3c4. Preserve T2 raw and
redesign the dynamic response/MPC model.

Even if it passes, it authorizes only a preregistered R3c4 implementation.
It does not prove restart control, independent histories, unseen targets,
continuous parameters, plant error, noise, disturbance recovery, or long
hold.

BC, DAgger, and bounded residual RL remain prohibited.

## 12. Post-run disposition

The valid H1 campaign completed all 160 real TSC tasks in:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t2_runs/
stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_225902
```

Independent raw recomputation certified every prospective identification gate:

```text
execution / restart / causal                       160/160
extended baseline prefix exact                       32/32
central symmetry                                     64/64
matched hidden history                               32/32
transport condition                                  32/32
combined six-basis condition                         32/32
maximum combined condition                        22.893801
maximum current utilization                         0.3904
```

The formal tracking diagnostic was 70/160, exactly as a non-acceptance
diagnostic under this prospective design. The result is therefore an
identification pass, not a real-control pass.

The complete forensic report and compact audit are:

```text
docs/codex/reports/STAGE4_2R3C3T2_FORENSIC_REPORT.md
docs/codex/audits/stage4_2r3c3t2_result_20260730_225902/
```
