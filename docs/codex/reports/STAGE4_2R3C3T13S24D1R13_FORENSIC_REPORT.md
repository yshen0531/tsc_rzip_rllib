# Stage4.2R3c3T13S24D1R13 final forensic report

## Result

Stage4.2R3c3T13S24D1R13 completed all eight prospectively frozen authentic
TSC trajectories. The primary postprocessor and an independent server-side
raw/snapshot audit both support the final route:

```text
ZERO_INCREMENT_DECONFOUNDING_SENTINEL_PASS_EXCITATION_SENTINEL_DESIGN_REQUIRED
```

This is a finite safety/deconfounding PASS. It is not a tracking-controller,
transition-model, MPC, robustness, long-hold, expert-data, BC, DAgger, or RL
PASS. Formal tracking was diagnostic only and passed 2/8.

## Exact identity and locations

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition

implementation checkpoint
  ac85824

final execution-package checkpoint
  df3910f

independent-audit checkpoint
  23148e9

remote installed source
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

remote staging source
  /home/yangshen0711/tsc_software/
  stage4_2r3c3t13s24d1r13_df3910f

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r13_runs/
  stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_20260804_df3910f_v1

remote logs
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r13_{offline,run,postprocess}_20260804_df3910f_v1.log

compact local evidence
  docs/codex/audits/
  stage4_2r3c3t13s24d1r13_20260804_df3910f/
```

The execution package used these installed hashes:

```text
PACKAGE_MANIFEST.json
  f83c4401a94cdb36626a67002d966c663a9b772eb760f7366413cf27def63fe2
SHA256SUMS
  a23187b898c35a2bb4f8417c0b21c5b166fb669761bcc05943551302b3b1ab89
config
  3712fb986201999e99fc1bc0062d201fa64f90fd65646a8df0e095377a28235b
implementation module
  fb3b3f1b4d3e4e2cca20474ddef5c2fc140623e979fc79f2dbd15ab68bddc6db
independent forensic tool
  78d3069feae9cdbd4846f477b96d8b6cbbdff05deac83c6da406526ca170e978
```

## Raw, snapshot, manifest, and log evidence

Expected and actual authentic tasks were 8/8. All eight raw JSON.GZ files
remain on the server and were strictly parsed there. Their inventory is:

```text
count    8
bytes    241,738
digest   f9b4dd9259736ebe2d26f9fcfd06bb0497be69a886de7ecc8d359009992f1c0a
```

All eight selected authentic restart snapshots passed exact manifest and
payload auditing. Each contains eight files; all source state-0 records and
the physical state/action/controller-trace prefixes through state 10 were
recomputed against the selected D1R11 source baseline.

Key result hashes are:

```text
final_result.json
  f8570641d5dd4e41962660712790bcd60c4ce8bf6a33e1f360235ffc8c69b9ca
stage_state.json
  7e72c8975a8d0ee0ad325cd5ac0c44340a335d0d22c2f5cd8c8e40790e19dd7d
stage_manifest.json
  2809e7e261dfb88404a96b0a89fb60b74a834f578e98c707529cb059d5a0d3fe
independent server forensics
  bd778f42d8755e8b45d572e895cefb171acad8f0fa688b238fd1acb3402e5ee4
offline / run / postprocess logs
  b471f73feb92cc1db20283cef2534bdc1208ce46616781853e6d03666fd3fd5b
  ce8a6131dc6a389905a90fe49f2e637f86dad7089ab1bcd793027ef791f98b02
  b2c1dabcb4e0e05998cb649cc8bfa9370662bd639eebccd4d9f53fcd35d4361a
```

Only the 39-file, 898,408-byte compact evidence set was downloaded. The raw
trajectory and snapshot trees were not downloaded or archived.

## Recomputed gates

Primary and independent evidence agree on every load-bearing gate:

```text
strict raw / exact identity                              8 / 8
fresh controller / fresh TSC                             8 / 8
restart snapshot / state-0 exact                         8 / 8
physical source state prefix through state 10            8 / 8
source action / controller-trace prefix exact             8 / 8
causal calibration complete                              8 / 8
full 35/37-state horizon                                  8 / 8
post-prefix action rows                           208 / 208 exact zero
post-prefix coil-current increments                       8 / 8 exact zero
finite R/Z/Ip, coil and wire currents                     8 / 8
runtime / environment errors                                  0
plant abnormal termination / early truncation                 0 / 0
solver / saturation / clipping errors                         0 / 0 / 0
forbidden controller inputs                                   0
maximum current utilization                           0.3904 <= 0.55
formal tracking diagnostic                               2 / 8
```

The selected D1R11/R17 baselines passed the formal diagnostic 4/8. Removing
R17 feedback and applying zero current increments regressed the two normal-
slew nominal-history rows; both weak-slew nominal rows remained formal passes;
all shifted-target rows failed. These comparisons are diagnostic and do not
change the safety route.

## Error classification

- Runtime/environment: none in the accepted real run.
- Deployment/package: the first staging verification rejected CRLF in
  `SHA256SUMS` before installation or TSC. Checkpoint `79aab25` normalized the
  verifier input; `df3910f` repackaged the unchanged experiment.
- Raw/snapshot corruption: none.
- Statistics/reporting: the reused snapshot auditor initially assumed 40
  contexts, and the Ray launcher initially ignored its calculated actor cap.
  Both were found and fixed before real TSC. Runtime and plant abnormal
  termination counters were also separated before execution.
- Design: D1R11 signed trajectories are not zero-baseline response data,
  because R17 feedback and moving Card15 centers continue after state 10.
- Real plant/restart: authentic restart, causal prefix replay, zero-increment
  actuator semantics, finite full horizons, and the current envelope pass in
  this fixed eight-case clean-source envelope.
- Real control: not established. The formal diagnostic is only 2/8.

An initial server-side retrospective D1R14 evidence command had an
`IndentationError` before output. It was an offline postprocessing invocation
error with no Ray, `gotsc`, TSC, controller, raw, or plant change. The
corrected read-only output has hash
`0c9ee8b367171bdaf321c03e02b6199cb1f3b693133c092b42533f4f4f5db8a4`.

## Why D1R14 is required

Read-only server processing of the eight D1R13 zero trajectories and the
matching existing D1R11 `++++`/`----` trajectories found:

```text
D1R11 signed odd-response peak range             0.0306231--0.0469175
maximum old-feedback even/odd ratio                         14.0322
maximum matched-history relative odd difference              0.5221
maximum zero-versus-R17 trajectory divergence                 2.6781
maximum zero natural drift                                    1.3011
maximum selected R17 post-state-10 action                     0.3653
```

Therefore old D1R11 signed sequences cannot be relabelled as responses about
the D1R13 zero baseline. The clean next experiment is a separately frozen,
fresh-identity zero-baseline signed excitation sentinel.

## Validation actually run

- Local strict JSON parse: 413 files passed before packaging.
- Local compileall: passed using `./venv/Scripts/python.exe`.
- Focused D1R13 tests: 9/9 passed.
- Complete Windows suite with repository `resource` compatibility shim:
  1,032/1,032 passed. The unshimmed discovery collected 665 tests but had 27
  Unix-`resource` import errors; it is not a code failure.
- Two repository-local empty-directory deployment simulations: 778/778
  package hashes, compile/import closure, and 9/9 focused tests passed.
- Staging and installed-server validation: 778/778 hashes, all declared shell
  scripts under `bash -n`, server-venv compile/import/JSON checks, and focused
  tests passed.
- Real execution: eight Ray actors, eight fresh `gotsc`/TSC/controller tasks,
  all completed.
- Server-side primary postprocessing and separately implemented raw/snapshot
  forensics: both passed and matched.

No global Python, local archive operation, server Git/network operation,
long-hold test, transition-model fit, MPC, expert-data collection, BC,
DAgger, or RL was run.

## Frozen conclusion and next action

D1R13 is immutable and may not be converted into a tracking or MPC result.
Its raw is identification-development evidence only and is forbidden from an
expert dataset. The exact next action is the prospectively frozen D1R14
zero-baseline signed excitation sentinel. Even a D1R14 pass authorizes only
the design of a time-distributed deconfounded identification campaign; every
MPC and RL-roadmap gate remains in force.
