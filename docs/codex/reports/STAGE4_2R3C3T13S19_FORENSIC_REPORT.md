# Stage4.2R3c3T13S19 final forensic report

## Outcome

Stage4.2R3c3T13S19 is frozen as a failed experiment identity. It may not be
resumed as a successful campaign. Its exact route is:

```text
PROSPECTIVE_POOLED_CAUSAL_OBSERVER_RUNTIME_OR_EXECUTION_FAIL_STOP
```

This route does not mean that TSC, plant restart, causality, the pooled
observer, or closed-loop control failed. The failure is a deterministic
excitation-design defect exposed by a fail-closed controller guard: an S16
fixed signed field displacement crossed a Card15 decimal-exponent boundary
and was not exactly representable at the new causal center.

## Frozen implementation and server evidence

```text
local branch                 codex/stage4_2r3c3t13s16-whitened-basis
implementation checkpoint   14f3646
remote project               /home/yangshen0711/tsc_all/tsc_rzip_rllib
remote run                   /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s19_runs/
  stage4_2r3c3t13s19_prospective_pooled_observer_campaign_20260803_14f3646
offline log                  logs/nohup/stage4_2r3c3t13s19_offline_20260803_14f3646.log
training-baseline log        logs/nohup/stage4_2r3c3t13s19_training_baseline_20260803_14f3646.log
```

The installed S19 package passed shell syntax, package verification, Python
import/compile, 16/16 focused tests, and the server full suite (831 tests, one
skip). The local full suite had 807 passes and one collection failure caused
by the local Windows environment lacking `gymnasium`; this was not counted as
a server or experiment pass.

Two earlier S19 startup attempts at `8f4ce41` and `e3217e3` produced zero raw,
zero plant steps, and zero real TSC trajectories. They found respectively a
CLI-to-loader keyword mismatch and an incomplete payload-context adapter.
Both were implementation/runtime defects repaired before the valid S19 run;
neither changed controller or experiment semantics.

## Raw inventory and terminal state

```text
expected training baselines               24
structured raw files                      24
successful complete raw                   23
structured failed raw                      1
raw parse/corruption failures              0
raw bytes                           1,300,417
canonical S19 `_raw_inventory` digest
  3a2a468a92ea656b240280125ebac9b4e947d14bc3beb8e61a0fcdd82d1e01da
terminal state sha256
  4e4d4247be7478f4a2352d092b6b72dba2916df69deba0d15cee7eaad203bdc2
```

The single failed experiment was
`s42r3c3_6bc94530a3ae407830ff`, pair
`p9_q1_a0p900_gap2_settle4`, history `minus_first`, training regime D. Its raw
SHA-256 is
`ebecebf89a465bfc9ddb66f7e089a9fdcb3803ab30d19c4ee121cd4a05a67ccc`.
The S16 exception path discarded the partial trajectory and trace in that raw;
this is a reporting defect, not the cause of the controller exception.

The terminal state is `finished=true`, `primary_pass=false`, and
`stop_reason=training_baseline_or_lattice_gate_failed`. Training probes,
calibration baselines/probes, and holdout baselines/probes were never run.
Calibration and holdout outcomes therefore remain unopened.

An earlier compact forensic note recorded
`dc31ee4be1159636cdf2d64638345f639ac0006d70d99862d7ce7af7774cd817`
as the inventory digest. During S20 offline authentication, direct server
execution of S19's frozen `_raw_inventory` over the unchanged 24 files
reproduced `3a2a468a...1e01da`, together with the same count and 1,300,417
bytes. The earlier token was therefore a statistics/recording error and is not
used as a source-authentication gate. No raw file or experiment result changed.

## Independent raw and TSC forensics

Independent server-side recomputation over the 23 successful baselines found:

```text
runtime/restart/causality/actuator pass       23 / 23
calibration schedule and zero net             23 / 23
pre-response semantics                        23 / 23
forbidden trace count                                0
maximum current utilization                  0.392
formal tracking pass, diagnostic only         10 / 23
zero-plant replay of prospective probes      184 / 184
```

The formal tracking count was never a baseline gate and is not an observer or
control verdict. The independent audit is
`analysis/training_baseline_independent_forensic.json`, SHA-256
`653962421fe0472d637975077deb69987f65f14ee6719f7a8bcb9aae009d47bc`.

A separately labelled one-task auxiliary reproduction advanced the authentic
plant twice and preserved the partial state and action trace. It failed before
the third plant advance, at task step 2, calibration direction 1, positive
sign. The decisive Card15 values were:

```text
causal center, coil 8            -9.904E-01 kAt
frozen requested increment             -0.016 kAt
mathematical target                    -1.0064 kAt
nearest displayed target          -1.006E+00 kAt
display error                          +0.0004 kAt
```

The improved reproduction is
`analysis/card15_failed_baseline_one_step_reproduction_v2.json`, SHA-256
`cd3396e50f14cf3476709bb44423c5363b3cd56b551ad97380e1565e602fc7c1`.
It is auxiliary forensic evidence and is not S19 campaign raw.

## Failure classification

```text
TSC runtime or solver failure                         no
plant restart or hidden-state authentication failure no
causality or forbidden-information failure           no
raw corruption                                       no
statistics/summary/verdict bug                       no
partial-failure reporting defect                    yes
excitation/action design defect                     yes
real observer conclusion                       not run
real MPC/control conclusion                    not run
plant reachability conclusion                  not run
```

Changing the fixed physical displacement into a current-centered nearest
exact displacement changes issued action semantics. Scientific integrity
therefore requires a new experiment identity and all 360 rollouts must be new;
the 23 S19 successful baselines cannot be reused as S20 raw.

## Post-failure development result

A zero-new-TSC server development replay used 187 causal calibration events:
184 from the 23 complete baselines and three preserved states from the failed
prefix. At every event it retained the frozen QR direction but recomputed the
nearest exactly representable signed Card15 displacement at that causal center.

```text
action/Card15 gates                         187 / 187
minimum desired/actual basis cosine          ~1.0
maximum relative off-basis residual       2.317e-15
signed primary coordinate range       0.975 -- 1.000
maximum cross-coordinate magnitude       1.887e-15
maximum incremental normalized action      0.216562
maximum total normalized action            0.648150
maximum current utilization                 0.392
rank-eight causal designs                    23 / 23
maximum design condition                  3.198099
exact complete calibration net zero          23 / 23
```

The failed exponent-boundary event was repaired exactly to `-1.006E+00`, an
actual increment of `-0.0156` kAt and a primary input coordinate of `0.975`.
The development artifact is
`analysis/s20_dynamic_card15_development.json`, SHA-256
`e16cfd02d1d7f0af1789c9ece07de8d8116eee11780ad8bf0e7cd23d1de14d64`.
This is development evidence only and not prospective validation.

## Frozen next action

Stage4.2R3c3T13S20 is a new, prospectively frozen 360-rollout campaign. It
keeps the S19 12/4/4 whole-pair partition and blindness boundaries, uses the
actual same-trajectory dynamic input coordinates, and reruns every baseline
and response. A pass can authorize only robust-transport MPC feasibility;
probe trajectories remain forbidden from expert data, BC, DAgger, and RL.
