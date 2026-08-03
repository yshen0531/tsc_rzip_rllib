# Stage4.2R3c3T13S24D1R6 forensic report

## Result

Stage4.2R3c3T13S24D1R6 completed all nine fresh authentic TSC sentinels.
Every rollout restarted exactly, reproduced the authenticated causal prefix,
and safely applied the frozen split start plus three 0.175 continuations. None
could return to the exact stored center by the frozen task-step-22 boundary.
The exact final route is:

```text
CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED
```

This is a genuine recursive action-schedule/controller-design failure. It is
not a TSC runtime, solver, restart, causality, raw-corruption, saturation,
current-limit, or plant-unreachability result. No trajectory reached the
formal endpoint, so formal tracking was not run to completion; it is not a
0/9 formal-control failure.

## Code, package, and execution identity

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition

controller/execution implementation checkpoint
  a2cab93

final execution-package checkpoint
  4177aa2

reporting-only physical-state correction checkpoint
  c33a368

package revision
  r42r3c3t13s24d1r6_recursive_split_return_safety_sentinel_v1

PACKAGE_MANIFEST.json SHA-256
  014068b0dd2c046c5985ca11c1e5a5464092c016f0b1f7f92cedc6fc0773d6b1

SHA256SUMS SHA-256
  dad07a6a8fd1116bb4156326d8312c925f70cfe744f3bb3c3b79f24b7c8d30dc

config SHA-256
  0ead2d73de119b7c7cef4d16ffb18d0a0ebcc934aa76a6129ad48418f5cacbe4

execution implementation SHA-256
  74ef096e5a7af92ab9ece03e9ec94a687b0a1a921003ceae35f45db9226827d4

ordered nine-spec digest
  f3ca434af404bb20c85e7ff2fb6da40bc13c1d873ae9c74396ab8680533b889b
```

The clean package contained 448 declared files and 450 files including the
manifest and checksum list. The final staging and installed project were:

```text
/home/yangshen0711/tsc_software/d1r6_deploy_4177aa2
/home/yangshen0711/tsc_all/tsc_rzip_rllib
```

The staging verifier passed all 450 transfer-file checks, shell syntax,
compile, JSON parsing, import closure, and 12/12 focused tests. The installed
server virtual environment passed the full suite 977/977 with one expected
skip. After the reporting-only correction, local D1R6/hotfix tests passed
16/16 and the full local suite passed 981/981. No global Python interpreter
was used.

## Exact remote run and logs

```text
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r6_runs/
  stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel_20260803_195509_4177aa2_v1

stage directory
  <run root>/stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel

complete real log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r6_real_20260803_195549_4177aa2_v1.log

complete real-log SHA-256
  14da67f6caac172ad67095fcce0843d6eb595671bd8c9ee935701acdc10b5a65

installed validation-log SHA-256
  c0f56dada33300d4f9a92941db21278dd3e7ba1361e2de0e9df620675204e59d

offline-log SHA-256
  439f0b3da4afc60de016a8f8d5c27e5e8ee053db48f6d5cb9a3fc79667e600b8

postprocess-log SHA-256
  9ba4a39fedb3e11e6994a7f681d3b308e7f8ed4c8d1c0ed74b90c5d29fda2e13

independent-log SHA-256
  15aecbdaf0562fbf23778ec9865ab2561497462ea5a164270d5540ae081ea50f
```

The offline phase authenticated the complete D1R4/D1R5 source boundary,
three snapshots, nine specs, package fingerprint, and resume contract with
zero raw, Ray, `gotsc`, TSC, controller rollout, or plant step. The real
launcher then used exactly nine actors and exited normally after all nine
fresh TSC processes completed or stopped structurally.

## Raw inventory and independent recomputation

```text
expected / actual raw                                    9 / 9
raw total bytes                                         422133
canonical raw inventory digest
  351f7484bd3ec2f68f76cc2f17ea6bc93a6227e2078b8be2f0cdf9e84055fd89
strict parse / exact identity                             9 / 9
restart / causality / calibration                         9 / 9 each
source action / trace prefix exact                        9 / 9 each
physical source-state prefix exact                        9 / 9
split start / first D1R5 continuation exact               9 / 9 each
runtime, solver, raw, snapshot, or corruption errors          0
```

The nine large raw JSON.GZ files remain on the server. Only compact JSON and
complete logs were copied directly and uncompressed to:

```text
docs/codex/audits/stage4_2r3c3t13s24d1r6_20260803_4177aa2/
```

Every downloaded file was compared with its server SHA-256. Load-bearing
compact hashes include:

```text
final result
  2236231582b31957d0920c7047b0245f7de3f27cf47dce3a46951c2531d4dec4
stage state
  792be3672bdd679a271d079f682040cf6b57f38c48b9b246a0f6c6c331eda170
stage manifest
  de0baf9fbe2c8923b5f3c863a9273667fb6fa9c652512388fee813ebfb452ecb
internal execution audit
  3264a6ea446d7e51a7dcfcff18ef66b7f098c815f3ece156d069549b1530656a
server raw recomputation
  0eace69afddfb35a45f5095bd358c1bfc678560bb406c27b1a836a0437454227
independent server forensics
  e54bfe8369ed35865771a918a8d25dd6ff1ad84d2e73175c0ba67694e4149698
snapshot audit
  b3298d45d36c166ba68baa9f0aaca3bdc81e5fedb46f9b845ea69647e8a38854
source authentication
  85c4d93593477e5b055f998cb0191727a5e44d193cf440beb93f1f3ce6351992
```

## Real sequential result

```text
split-start events                                           9
recursive continuation events                              27
continuations at task steps 19 / 20 / 21                 9 / 9 / 9
continuation increment                         exactly 0.175 each
exact-center finishes                                         0
task-step-22 structured safe stops                            9
failed finish candidate applied                               0
plant advance after failed candidate                          0
full 35-action horizons                                       0
formal endpoint evaluable                                     0
maximum actual current utilization                      0.39045
forbidden controller-input rows                               0
```

The exact-center intervention relative to the same-state underlying causal
action evolved as follows:

```text
task step      minimum        maximum        mean
19             0.2712316553   0.3540255817   0.3026144652
20             0.3755641011   0.4922624755   0.4174935510
21             0.5633025885   0.6879459063   0.6081988539
22             0.3673570430   0.5149905137   0.4225301275
```

Thus the fixed straight-line exact-Card15 continuation did not contract the
causal finish requirement. It worsened sharply through steps 20--21 and was
still above both 0.24 and 0.25 in every row at the hard boundary. At step 22
the only false criteria were the derived actuator gate, the 0.24 finish cap,
and the unchanged 0.25 original cap. Exact target fields, Decimal telescope,
total action, predicted current, no saturation, and no clipping all passed.
The fail-closed behavior was correct.

## Reporting correction and invocation error

The prospective primary and independent audits initially reported
`source_prefix_state_exact_count=0`. Their comparison included two runtime
timing fields that are not physical plant state:

```text
gotsc_subprocess_s differences                 171 = 9 x 19
step_total_s differences                       171 = 9 x 19
unexpected physical-state differences                     0
```

The bound reporting-only correction at checkpoint `c33a368` excluded only
those two fields and recomputed physical R/Z/Ip, all 14 coil currents, all
wire currents, action, abnormal flag, and state indices as exact 9/9. Its
output SHA-256 is
`f64e7e2a1fc50b70804635971450676d83d53c4d2168ac8a710c0d5e925f8229`.
Raw, controller, experiment identity, route, and scientific conclusion did
not change.

The first server invocation of that correction omitted the project from
`PYTHONPATH` and stopped before output. Its 295-byte log SHA-256 is
`5bec52df013dc499678c195069a5bdfb0c1ee08a4a859e0f1d6105566bf2fe04`.
The corrected server-virtualenv invocation passed; its log SHA-256 is
`f06a04fd91a5566d53df45bdd8a6398395be121494fc4eb0f0ea39707013f47f`.
This was an invocation/environment error in postprocessing only, with no TSC,
raw, action, or plant effect.

## Scientific classification

- Runtime/environment error in the real campaign: **none**.
- Packaging/import/deployment error in the real campaign: **none**.
- Raw/snapshot corruption: **none**.
- Statistics/reporting error: **one semantics-neutral state-prefix comparison
  bug**, corrected from 0/9 to physical 9/9.
- Postprocessing invocation error: **one missing-`PYTHONPATH` attempt**, no
  output or experiment effect.
- Design flaw: **yes**. Repeated causal straight-line intermediates toward a
  fixed stored center do not create a bounded return under the evolving
  feedback baseline.
- Real restart conclusion: exact on this finite nine-case development grid.
- Real control conclusion: the tested recursive return schedule fails 9/9;
  formal closed-loop tracking was not reached and global reachability was not
  tested.

## Frozen conclusion and next action

D1R6 is immutable and may not resume. Its raw remains development/forensic
evidence and is forbidden from model fitting or expert datasets. The full
replacement campaign, transition MPC, expert data, BC, DAgger, and RL remain
blocked.

The next step must redesign the fixed global sequential excitation schedule,
not weaken the 0.18/0.24/0.25/current/timing gates or add more straight-line
continuations. A zero-new-TSC discriminator must authenticate S24 and
D1R2--D1R6, determine whether one fixed sequence/substitution/reordering can
retain the required rank/geometry while avoiding the known late-pair unsafe
return in every relevant context, and freeze its selection before any new
real sentinel. Outcome- or history-conditioned controller labels remain
forbidden. A finite offline pass may authorize only a separately frozen
fresh-identity real safety sentinel.

## Commands and honest execution statement

The work used the project-local Windows virtual environment for compile,
JSON, focused/full tests, and empty-package validation; direct `scp` without
archives for deployment and compact evidence; and only the existing server
virtual environment for Python validation, offline authentication, real TSC
execution, postprocessing, independent raw recomputation, and the reporting
correction. The actual driver and log were monitored until normal exit.

No full replacement identification, transition-model fit, MPC, unseen-target,
continuous-parameter, plant-mismatch, noise, observer, disturbance, long-hold,
expert-data, BC, DAgger, or RL stage was run.
