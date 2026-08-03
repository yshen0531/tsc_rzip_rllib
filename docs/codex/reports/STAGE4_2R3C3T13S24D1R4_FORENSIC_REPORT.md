# Stage4.2R3c3T13S24D1R4 forensic report

Status: final authentic real-TSC split-return safety-sentinel result.

## Identity and evidence boundary

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition

prospective design checkpoint
  6398c0d

scientific implementation checkpoint
  ddff71f

executed package checkpoint
  da3f4b4

retrospective reporting-audit checkpoint
  69dedc0

executed package revision
  r42r3c3t13s24d1r4_causal_split_return_safety_sentinel_v1h2

installed PACKAGE_MANIFEST.json SHA-256
  93bde8503a85e6de5138cd60eb92a6a8c2638794350753a2b068a39583064abe

installed SHA256SUMS SHA-256
  a5eb857eb3eba1e921dec5d6cb2da1026af2dc95c4abb07b8945c18a9edc7be0

D1R4 config SHA-256
  8b402a48f15b6f5c783719bd7216cda8ae8eea459e5e797c2769e38cd88da683

D1R4 implementation SHA-256
  7e1b29aa3e37d2751946a5c8f04e7f59d19d033b1018ade7bde4dc7719394694
```

The completed run and complete stdout/stderr log are:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r4_runs/
stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_20260803_1802_da3f4b4_v1h2

/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t13s24d1r4_real_20260803_1804_da3f4b4_v1h2.log
```

The complete log SHA-256 is
`ca86693375685e4c6d1d21b37b39c405b79ff3f391a1c888bcca00592d00536d`.
The exact raw boundary is 9 files, 363,807 bytes, with inventory digest
`9327a301498349eaebdb834d1c0f243bcc1939b5efb5d059ee6d6ec43b036190`.
Large raw and restart snapshot trees remain on the server. Compact manifests,
audits, final/state files, and logs are mirrored under:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r4_20260803_da3f4b4_v1h2/server_compact/
```

## Pre-scientific implementation incidents

Two preserved invocations failed before any controller action or plant
advance and do not constitute D1R4 scientific trials.

The initial v1 zero-raw offline run reused a D1R2 helper that required 18
snapshots, although D1R4's selected subset contains exactly three. It stopped
before state/raw materialization and before TSC response. Package v1h1 added a
D1R4-specific three-snapshot aggregation without changing the task matrix,
controller, physical action, or gate.

The v1h1 real launcher then created nine fresh TSC/reset contexts but stopped
while constructing every controller because the selector metadata key
`partition` had not been stripped. Every raw had one initial state, zero
controller traces, and the structured runtime message `D1R4 forbidden
selection label reached controller`. No controller was constructed, no action
was returned, and no plant step occurred. Its separately frozen independent
forensic route was `CAUSAL_SPLIT_RETURN_SENTINEL_RUNTIME_INCOMPLETE`.
Package v1h2 stripped only that remaining forbidden metadata key. It changed
no controller state machine, task, action, timing, source, or formal gate, and
therefore correctly used a new empty run rather than overwriting or resuming
the v1h1 directory.

## Final validation

Before the v1h2 run opened a result:

```text
local focused D1R4 tests                                  12 / 12
local complete tests                                    957 / 957
server exact package inventory                          434 files
server bash syntax / package / import / JSON checks          pass
server installed complete tests                         957 / 957
server expected skips                                           1
```

The installed validation log is
`logs/stage4_2r3c3t13s24d1r4_server_validation_da3f4b4_v1h2.log`, SHA-256
`178d73fbfdda732a3996b38e91315800bc3f5ab552e549b752f8ea8b216d7a89`.
Only `/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python` was used
on the server.

After the result, the reporting-only prefix audit was compiled and executed
from the exact server-staging source
`/home/yangshen0711/tsc_software/d1r4_retrospective_69dedc0/audit.py`, SHA-256
`44c7628126a107795132868d8fe44a52802168df45e490d4d866e2aed52a65c1`.
Its two focused tests and the complete local suite passed 2/2 and 959/959.
It did not modify the installed controller package or any raw/final artifact.

## Raw and complete-log result

All nine actors and TSC processes completed their authentic prefix. Every raw
strictly parses and has exact identity, 20 trajectory states, and 19 executed
controller rows. Each controller reproduced the D1R2 action and trace through
task step 17, applied D1R3's exact 0.175 split start at step 18, and advanced
the authentic plant exactly once to state 19.

At state 19, each controller causally recomputed its underlying baseline and
the exact stored-center action. The finish candidate passed exact target,
Card15, Decimal telescope, total-action, current, no-saturation, no-clipping,
slot, timing, and one-plant-advance predicates. It failed only the intervention
increment gates:

```text
raw strict parse / exact identity                              9 / 9
executed-prefix forensic pass                                  9 / 9
restart / causality / calibration                              9 / 9 each
source action / trace prefix exact                             9 / 9 each
D1R3 split-start exact                                         9 / 9
issue / direct-cancel / split-start events                  36 / 27 / 9
failed step-19 finish attempts                                 9 / 9
failed finish actions not applied                              9 / 9
0.24 finish-margin pass / fail                                 0 / 9
original 0.25 cap pass / fail                                  0 / 9
finish intervention increment range             0.2712316553--0.3540255817
maximum executed current utilization                         0.39045
maximum failed-finish predicted current utilization           0.3838
forbidden-input trace count                                         0
runtime / raw / snapshot / restart errors                           0
formal endpoint evaluable trajectories                              0
```

The finish action's diagnostic distance from the previously executed split
command was only 0.0563036902--0.1103874805. That is not the preregistered
gate. The frozen contract defines the intervention increment relative to the
new state-19 underlying causal baseline `b19`; changing the reference after
seeing the result would change experiment semantics and is forbidden.

The final route is:

```text
CAUSAL_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED
```

## Reporting bug and independent correction

Both prospective audits selected the correct route and retained each complete
failure event. Their aggregate success branch nevertheless counted restart,
causality, source-prefix, event, current, and formal metrics only for
full-horizon successes. Because all nine rows were structured safe stops, the
top aggregates incorrectly reported zeros for those already executed prefix
checks and described formal tracking as 0/9 rather than not evaluable.

The reporting-only audit independently authenticated the prospective audit,
complete log, original execution package fingerprint, manifest, exact raw
inventory, all source raws, and every partial trajectory/trace. It corrected
the coverage counts above without changing raw, state, final, manifest, route,
threshold, controller, or experiment identity. Its output and log hashes are:

```text
retrospective_structured_failure_prefix_forensics_v1.json
  f1ada0a11ce76e50c1dd2896c01874a1b3cdc73369e5a7937ca2332b532c5b0d

stage4_2r3c3t13s24d1r4_retrospective_prefix_forensics_20260803_69dedc0.log
  f782e95848d1f6a2f9c23b438b2e1d081fbcab8110b9c5df328fd33f1044cc8d
```

The prospectively frozen independent output remains immutable, SHA-256
`58dc2ac72e59e98a7fc4f496bdc6679b098b9f2a857db9028ce889a32a99688d`.

## Classification and claim boundary

- Runtime/environment: no error in the final v1h2 run. The deliberate
  fail-closed `ValueError` is a structured scientific/action stop, not a TSC
  runtime failure.
- Packaging/deployment: the v1 and v1h1 incidents were pre-scientific
  implementation defects with zero controller actions and zero plant steps.
- Raw/snapshot integrity: exact and uncorrupted for 9/9 final raws and all
  three restart snapshots.
- Statistics/reporting: the prospective top-level prefix aggregation was
  incomplete; the retrospective audit repairs only that report coverage.
- Design: the frozen one-advance step-19 exact-center return is outside both
  intervention caps in all nine contexts.
- Real plant/control: one finite, causal, admissible split-start plant advance
  was demonstrated in every context. The exact-center finish was never
  applied, no trajectory reached the full horizon, and there is therefore no
  full closed-loop, formal-tracking, hold, MPC, or plant-recovery result.

D1R4 is immutable and may not resume. Its raw is development/forensic-only and
is forbidden from transition-model training and expert datasets. The immutable
250/270 ms arrival deadlines and 350/370 ms endpoints were unchanged.

## Next action

The real failure invalidates a one-advance exact return, not causal segmented
return in general. The next stage is a separately frozen zero-new-TSC D1R5
recursive split-return preflight. It may replay only the nine authenticated
D1R4 prefixes and use each actually observed state-19 current state to test a
second causal 0.175 intermediate. It may not reinterpret the D1R4 finish gate,
apply an action, or train a model. A pass can authorize only prospective design
of a new-identity recursive real-TSC sentinel; full identification, MPC,
expert data, BC, DAgger, and RL remain blocked.

## Commands and honest non-execution statement

The completed workflow used the project virtual environment for compile and
unit tests, direct uncompressed `scp`, server `sha256sum`/`bash -n`, installed
package verification, server-virtualenv tests, one final nine-actor Ray/TSC
campaign, two independent read-only raw audits, and strict local JSON/hash
verification of compact evidence. The final run did not execute a finish
action, full 35-step trajectory, formal endpoint, MPC, optimizer, expert-data
builder, BC, DAgger, or RL procedure.
