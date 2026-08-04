# Stage4.2R3c3T13S24D1R11 forensic report

## Result

D1R11 is final as:

```text
FULL_REPLACEMENT_TRANSITION_TRAINING_MODEL_FAIL
```

The 600-rollout training acquisition is an authentic, complete real-TSC
identification result. The subsequently frozen L/SA/Q recursive transition
model family failed its preregistered training gate. Calibration and holdout
were therefore never opened. This is a transition-model/design failure, not
a runtime, packaging, restart, causality, raw-corruption, reporting, real-MPC,
closed-loop-control, or plant-unreachability failure.

## Code and package identity

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition
implementation commit
  027f555  Fix D1R11 D1R9 source authentication
deployed package checkpoint
  05c8521  Package D1R11 source authentication hotfix
PACKAGE_MANIFEST.json SHA-256
  e493cdf0afc43afb97bb8dfed084380b5785acb01bb8cecc67bc82eddc441f3e
SHA256SUMS SHA-256
  9e1d4bfbf6c1bc07c16c16cbf72626e98e0dce24f8b83006d941fab83c97cf93
ordered spec digest
  e370269558ab079fe6d1f2293b2920b7774e3239942c7dd60ae4b638138f8c7a
```

The first official offline invocation stopped before output because the
source reader looked for D1R9 `primary_pass` instead of the official
top-level `passed` field. The run directory was proven empty and contained
zero raw before the authentication-only fix. Checkpoints `027f555` and
`05c8521` changed no task, controller, action, model, gate, timing, or physical
semantics. The corrected package passed 1,023/1,023 local and installed
server tests, with one expected server skip.

## Remote evidence

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
staging package
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s24d1r11_05c8521
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r11_runs/
  stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_20260804_571b932_v1
stage directory
  <run root>/stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification
training-sequence log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r11_training_sequence_20260804_05c8521_v1.log
fit-training log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r11_fit_training_20260804_05c8521_v1.log
independent audit directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r11_audits/
  stage4_2r3c3t13s24d1r11_training_sequence_20260804_05c8521_v1
```

Large raw and snapshot files remain server-side. Compact local evidence is
under:

```text
docs/codex/audits/stage4_2r3c3t13s24d1r11_20260804_05c8521/
```

## Real execution inventory

The frozen matrix was 600 training, 200 calibration, and 200 fresh holdout
rollouts. The fail-closed boundary produced:

```text
training baselines                                      24 / 24
training sequential responses                         576 / 576
training total                                         600 / 600
calibration                                               0 / 200  not run
fresh holdout                                             0 / 200  not run
strictly parsed training raw                           600 / 600
training raw bytes                                    35,511,922
training raw inventory digest
  8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7
unique authentic R3b source endpoints                         24
unique restart snapshots                                      24
snapshot files independently rehashed                         192
snapshot bytes independently rehashed               2,844,821,932
```

No calibration or holdout experiment ID is present in raw. The terminal
state has `heldout_outcomes_opened=false`, an empty model hash, and an empty
tube hash.

## Independent raw and snapshot recomputation

The accepted independent audit is v3. It did not use the official verdict
as its gate. It strictly parsed all raw, matched every embedded spec to the
frozen 1,000-spec table, rehashed every listed file in all 24 snapshots,
strictly parsed the 24 R3b source raw files, and compared every D1R11 initial
R/Z/Ip, coil-current, wire-current, vessel-current, and time field to the
authentic R3b endpoint.

```text
source endpoint exact                                  600 / 600
snapshot authentication exact                          600 / 600
fresh controller / fresh TSC / online causal trace     600 / 600
calibration events                                   4,800 / 4,800
sequential issue/cancel events                       4,608 / 4,608
independently recomputed event-detail gates          4,608 / 4,608
exact issue-to-stored-center cancel trajectories       576 / 576
forbidden predictor/controller use                               0
runtime / solver / abnormal-state error                           0
raw / snapshot corruption                                        0
summary/statistics discrepancy                                   0
maximum absolute normalized action                    0.6481496914
maximum incremental action                            0.2360657249
maximum online cancel incremental action              0.2360657249
maximum measured current utilization                           0.392
maximum predicted current utilization                         0.3919
maximum requested-coordinate error                    0.0567326657
minimum active coordinate                             0.2321457683
minimum desired/applied-current cosine                0.9927943695
maximum relative off-basis residual                   0.0998036448
```

The v1 and v2 audit attempts are preserved as audit-tool failures. V1
incorrectly hard-coded every checkpoint time to 1230 ms and applied the
issue-event schema to stored-center cancel records. V2 repaired those two
assumptions but incorrectly required a baseline schedule dictionary to be
empty, while the frozen baseline spec explicitly stores eight zero-valued
slots. V3 reads each true source endpoint time, checks cancel records by
their exact stored-center semantics, allows intermediate cumulative-exact
calibration residuals while requiring final exact closure, and requires the
baseline schedule values to be exactly zero. V3 passed with zero raw
failure. These were postprocessing/audit implementation errors only; none
changed raw, experiment state, controller action, or source package.

Accepted compact hashes:

```text
independent audit v3 JSON
  04dc071c8eca990340dcbabafd31951106ac85ede9f230b55ed231918b4508c9
independent audit v3 log
  2eec9afdac121f94a8a7ac529361398e5d70f1625a903f47be8a480f9ec926a3
independent audit v3 script
  8f095978bc824eea71a00ced7749acb970509622a04faa1a3bbb99e8bbd639bc
training-sequence log
  d8b7894e2ceb2373012c6a6f87c2b5fa1813804ab22fee353117433d76d64d1d
```

## Frozen training-model result

`fit-training` used only the 600 authenticated training trajectories. The
artifact records zero calibration and zero holdout outcome access before a
model hash. It evaluated all 24 preregistered combinations of L/SA/Q and
eight ridge values with leave-one-whole-pair-out recursion.

The selected candidate was:

```text
feature / ridge                                      L / 1.0
teacher rows                                          15,600
training pairs                                             12
training trajectories                                     600
formal verdict reproduced                            532 / 600
formal mismatches                                           68
maximum absolute recursive scaled error             0.9580646071
frozen maximum                                             0.1
mean squared recursive scaled error                 0.02176952613
```

All 24 candidates failed. The seven other L candidates with ridge at most
0.01 also had 68 mismatches and maximum error at least 1.0045; L/ridge=100
had 92 mismatches. The best SA/Q mismatch count was 117. The deterministic
selection order therefore selected the correct minimum-mismatch candidate;
the result is not a favorable-candidate reporting error.

Mismatch structure was concentrated but not ambiguous:

```text
p9_q1_a0p750_gap3_settle4                       44 false positives
p5_q2_a0p750_gap4_settle4                       20 false positives
p5_q1_a0p750_gap2_settle4              2 false positives + 2 false negatives
all other nine pairs                              0 formal mismatches
```

The maximum recursive error gate failed for every pair, including the nine
without a formal mismatch. Across all 600 rows the minimum trajectory-level
maximum scaled error was 0.1512, the median was 0.4721, and the maximum was
0.9581. The dominant maximum-error component was vZ in 448 trajectories and
vR in 152. This rules out interpreting the failure as only a few formal
boundary cases.

The selected leave-pair-out component residual and resulting 2x tube
precursor were:

```text
component               R       Z       vR       vZ       Ip
scaled residual      0.2424  0.4090   0.6863   0.9581   0.0844
physical halfwidth  14.55mm 24.54mm 0.1373m/s 0.1916m/s 337.57A
frozen cap           3.00mm  3.00mm 0.0100m/s 0.0100m/s 1000.0A
```

The point-error, exact-formal-reproduction, and tube-cap gates all fail by
large margins. No training model file or hash was produced.

Artifact hashes:

```text
failed_training_model_artifact.json
  136112ec465b551c2936aea09c4c9127970aff2c47f4f820d258596e3df35c89
training_model_audit.json
  f9fd06e7ed65eb4d4402919dd0af18e37e7526fe873f5790c10bbe58423195a3
terminal stage_state.json
  24728eccb317d60c20b29886320455c10b474ca9717663c62d7530dd7c8422fd
fit-training log
  bc4fc7b416fb0f640a8347074d9a8af33999804cab5bdb1e4b7f09f70ec13576
```

## Formal-control boundary

The real training trajectories passed the immutable formal tracking contract
158/600: 10/24 baselines and 148/576 sequential probes. This percentage was
diagnostic only and is not the D1R11 identification execution gate. Probe
actions are identification inputs and the trajectories are forbidden from
expert datasets. D1R11 did not implement or execute MPC, and neither its
158 passes nor its 442 failures are a reliable-MPC result.

## Classification

```text
runtime or environment error                         no
packaging/import/deployment error in accepted run    no
raw or snapshot corruption                           no
statistics/reporting error in accepted v3 result     no
audit-tool errors in v1/v2                           yes, postprocessing only
controller/action semantics failure                  no
authentic plant restart failure                      no
frozen transition-model design failure               yes
real MPC or closed-loop controller conclusion        none; not run
calibration result                                   none; not run
fresh holdout result                                 none; not run
expert data / BC / DAgger / RL authorization         no
```

## Commands and validation actually run

The work used the repository-local Windows virtual environment and the
existing server virtual environment only. It performed local compile,
focused/full tests, JSON validation, import/package closure, empty-directory
direct-copy simulation, direct SFTP deployment without archives, server
`bash -n`, package verification, import/compile, focused/full tests, guarded
offline authentication, 24 baseline TSC rollouts, 576 sequential TSC
rollouts in fixed batches, three independent server raw/snapshot audit
iterations, and the frozen serial `fit-training` phase. No global Python,
Git on the server, network package installation, local archive operation,
calibration rollout, holdout rollout, MPC, expert-data generation, BC,
DAgger, or RL was run.

## Next route

D1R11 is immutable and may not resume. In particular, its old calibration
and holdout phases may not be opened with a post-result model change.

The next work is a new-identity, zero-new-TSC causal transition-architecture
study using only the 600 authenticated D1R11 training trajectories as
development data. It must preserve whole-pair outer validation, the original
0.1 point gate, tube caps, forbidden-input list, action/current gates, and
formal timing. The evidence specifically motivates a stable kinematically
consistent innovation/state-space model with causal online context
adaptation, rather than another absolute-state global polynomial ridge. A
new architecture must pass deterministic independent leave-pair replay before
any separately preregistered fresh calibration/holdout campaign is allowed.

This route remains far before real MPC. Reliable constrained MPC under
authentic restart, hidden history/different initial state, unseen targets,
continuous actuator/plant variation, noise, disturbance recovery, and an
independent long hold must all pass before expert data, BC, DAgger, or bounded
residual RL can begin.
