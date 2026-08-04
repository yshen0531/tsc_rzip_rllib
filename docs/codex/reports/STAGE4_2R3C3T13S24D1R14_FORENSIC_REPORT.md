# Stage4.2R3c3T13S24D1R14 final forensic report

Date: 2026-08-04

## Result

D1R14 v2 completed all 72 authentic TSC trajectories, and all restart,
prefix, causality, action-construction, cancellation, current, runtime, solver,
raw, snapshot, and reporting checks passed. The frozen response-geometry gate
failed. The final route is:

```text
ZERO_BASELINE_EXCITATION_GEOMETRY_FAIL_REDESIGN_REQUIRED
```

This is a genuine finite excitation/response-geometry design failure. It is
not a runtime, deployment, restart, plant-abnormality, raw-corruption,
statistics/reporting, formal-control, plant-unreachability, or real-MPC
failure.

## Identity and paths

Local branch and accepted package checkpoint:

```text
codex/stage4_2r3c3t13s24-sequential-transition
d32761c Package D1R14 one-hot gate hotfix
implementation checkpoint: c215333
controller revision: zero_baseline_signed_excitation_v42r3c3t13s24d1r14_v2
```

Package hashes:

```text
PACKAGE_MANIFEST.json  0980b9eec37b56d4c511de4ccbf045a746644f68fe1674d77cd5aa52a1709639
SHA256SUMS             6823f0466cf90d7987a8ec827c171d81aa972943b92bad9bfbd5b918516ddbf6
```

Remote package, run, and logs:

```text
/home/yangshen0711/tsc_software/stage4_2r3c3t13s24d1r14_d32761c_package
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14_runs/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_20260804_d32761c_v1
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/stage4_2r3c3t13s24d1r14_d32761c_installed_verify.log
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s24d1r14_offline_20260804_d32761c_v1.log
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s24d1r14_run_20260804_d32761c_v1.log
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s24d1r14_postprocess_20260804_d32761c_v1.log
```

## Raw and independent audit

Expected and actual task counts were both 72: eight fresh zero baselines and
64 signed probes. The immutable raw inventory remains on the server:

```text
count   72
bytes   2,239,479
digest  0433a64ebaea73186bb193d5102686721497219acfcbecbb721e7fad62e8d7a3
```

All 72 raw files parsed strictly. Eight distinct snapshots passed. Exact
source state and trace prefixes passed 72/72. The independently recomputed
counts were:

```text
safety / finite                                  72 / 72
fresh-baseline reproduction                        8 / 8
exact issue / exact stored-center cancellation    64 / 64
runtime or environment errors                          0
plant failures / solver errors                         0 / 0
saturation or clipping                                 0
action-safety failures                                 0
prefix failures / forbidden trace fields               0 / 0
maximum current utilization                         0.3904
```

The primary final JSON SHA is
`1a65a37c301ba52325f586e0948b0b94b1266c540e2f2a332e5bc02df60a7da2`.
The independent server audit SHA is
`8e7d3d045477502c1060fe621f2c43235e1d530b59c5d22849337dd20aac3eae`.
The independent audit reproduced the official route and geometry exactly.
Only compact results, logs, manifests, state, and specifications were copied
locally; raw and snapshots were deliberately not downloaded.

## Frozen geometry result

All eight contexts retained numerical rank four, but the full preregistered
gate failed:

```text
signed response pairs                       32
odd-signal pass                         24 / 32
even/odd symmetry pass                  27 / 32
rank-four context pass                    8 / 8
condition-at-most-20 context pass         7 / 8
minimum observed odd peak       0.0005766750000008036
maximum even/odd ratio           0.7567864128647219
maximum condition number        20.585168494548288
```

The isolated coil-8 component failed the `0.005` signal floor in all 8/8
contexts, with odd peaks only about `0.000577` to `0.000723`. Mode 0 without
coil 8 passed signal and symmetry 8/8. Modes 1 and 2 each passed signal 8/8
and symmetry 7/8. One context exceeded the condition cap at `20.5852`.

Formal tracking passed 18/72, but was preregistered as diagnostic only. It is
not a controller result and cannot establish or refute MPC performance.

## D1R14 v1 integration bug versus v2 design failure

Package `2d5304c` also produced 72 strict raw, but all 64 signed tasks stopped
before applying the state-10 action because inherited S24 dense-coordinate
predicates were incompatible with D1R14's one-hot request. Independent audit
proved 64/64 attempted exact Card15 and safety constructions were safe and
0/64 issue actions reached TSC. That immutable run is a controller integration
bug with no signed response geometry.

The v2 hotfix changed only the erroneous issue gate, used a new source
fingerprint and fresh run, and preserved the requested physical directions,
timing, task matrix, safety limits, geometry gates, and scientific meaning.
Therefore v2 is the first valid D1R14 response result.

## Development-only redesign evidence and next action

Server-side development analysis consumed all D1R14 v2 signed responses. It
showed that amplitude-only scaling cannot change the worst unit-column
condition number, and 120,000 bounded arbitrary mixes found no simultaneous
`0.005` signal and condition-at-most-20 solution. A deterministic pooled-Gram
whitening plus seeded orthogonal rotation produced a candidate amplified mixed
basis whose linearized response predicts minimum odd peak `0.006` and maximum
condition `3.702078`. Its requested-coordinate matrix has maximum absolute
coordinate `3.92155`; linearized reconstruction estimates maximum issue and
cancel action near `0.116194`, below the frozen bounds.

Those estimates use consumed development data and do not prove exact Card15
action safety, nonlinear cancellation, or real response geometry. The next
stage is therefore D1R14R1: a separately frozen zero-new-TSC deterministic
recomputation and exact static Card15 issue preflight. Only an R1 pass may
authorize a fresh real-TSC D1R14R2 mixed-basis safety/geometry sentinel.

## Scientific boundary

D1R14 proves that the one-step zero-baseline experiment executed safely and
that the original four one-hot directions are an inadequate identification
basis over this finite eight-context envelope. It does not validate a
time-distributed transition model, MPC, expert policy, unseen targets,
continuous actuator variation, noisy sensing, disturbance recovery, long
hold, BC, DAgger, or residual RL. Probe trajectories remain forbidden from
expert datasets.

Commands actually executed covered local compile/JSON/tests/package closure,
empty-directory deployment, direct unarchived transfer, server `bash -n`,
package verification, server-virtualenv compile/import/tests, offline source
authentication, fixed-capacity Ray execution, primary postprocessing, and an
independent server-side raw/snapshot audit. No transition model, MPC, expert
dataset, BC, DAgger, or RL run was performed.
