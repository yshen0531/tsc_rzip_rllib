# Stage4.2R1 final-result forensic report

## Executive conclusion

The downloaded Stage4.2R1/R1a result does **not** contain an authentic
plant-restart result.  All 18 expected capture tasks returned structured raw
JSON, but every task failed in `prepare_replay` before `env.reset()`, before
the first TSC step, before any action replay, and before any snapshot request.
The common exception is:

```text
AttributeError("'NoneType' object has no attribute 'cfg'")
```

The exact failing access is `runner.cfg.start_folder`.  The worker caches
`runner = self.runner` while `base_worker.env.runner` is still `None`; the
environment only constructs its `TSCStepRunner` inside `_ensure_runner()`,
which is normally called by `env.reset()`.

Therefore:

- capture instrumentation fidelity is not established;
- snapshot integrity is not evaluable because no snapshot was created;
- plant-restart initial-state and suffix fidelity are `not_run`;
- restart formal-contract preservation is `not_run`, not failed;
- Stage4.2R2 must not begin yet;
- a minimum runner-initialization-order hotfix can preserve the frozen R17
  actions, experiment IDs, task matrix, controller semantics, and formal
  timing, so the existing remote run is eligible for `resume=1` after complete
  validation.

## Evidence identity

- Local branch at baseline audit: `codex/stage4_2r1-forensics`
- Local pre-fix commit: `d7be328` (`codex md prep`)
- Local run:
  `stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619`
- Remote run recorded by the launcher:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619`
- Initial remote/local log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619.log`
- R1a resume remote/local log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_234105.log`
- Controller revision:
  `true_tsc_plant_restart_action_replay_v42r1`
- Package revision:
  `r42r1a_capture_failure_finite_summary_v2`
- Package revision history:
  `r42r1_plant_restart_action_replay_v1`
- `PACKAGE_MANIFEST.json` SHA-256:
  `f0c8afebb61548adad8b189ac832af4edc6819355f62281a56a534852c63cdaa`
- `SHA256SUMS` SHA-256:
  `807c40beab913ac104c9e05d0ec315da095ae03c86686913d50cd6db72f8e405`
- Direct R17 source fingerprint:
  `aaab69882fff50eed024fd7ffa7babf473a27c729a0944914c739034c9b4f2f6`
- Selected 18-case expert fingerprint:
  `95ef2cdbdbbbecdf0a58b316b44cca4fb788613b1a87c1f9b48e897175b2c112`

The run tree contains 42 files: 22 plain JSON files, 18 raw JSON.GZ files,
and two CSV files.  Every JSON and JSON.GZ stream parses.  The downloaded
tree contains no snapshot files and no restart raw files.

## Expected versus actual tasks

| Phase | Expected | Actual | Successful | Scientific status |
|---|---:|---:|---:|---|
| R17 selected source cases | 18 | 18 | 18 | authenticated finite source |
| R1 capture | 18 | 18 raw results | 0 | runtime error before TSC |
| Snapshot banks | 18 after valid capture | 0 | 0 | not created |
| Fresh restart suffix | 18 after capture gate | 0 | 0 | `not_run` |

The Ray log line `18/18` means only that 18 Python capture tasks returned.  It
does not mean 18 TSC captures ran.

## R17 source verification

The selected source inventory references 18 raw trajectories: 14 unchanged
R11-derived source trajectories and four R17 weak-slew one-sided-braking
trajectories.  All 18 referenced files:

- exist in the local repository;
- have the exact manifest-recorded size;
- have the exact manifest-recorded SHA-256;
- parse as JSON.GZ;
- have `success=true`;
- contain no abnormal state in the formal slice;
- contain the required 35 or 37 formal actions.

The R17 formal-grid rows are 18/18 pass with the original deadlines:

- slew 1.0/1.1: arrival by step 25 and evaluation through step 35;
- slew 0.9: arrival by step 27 and evaluation through step 37.

The minimum recorded/recomputed source signed margin is
`1.0456920999768471e-05`, for `RZ_p10_m10`, delay 0, slew 0.9.  This confirms
the finite source but also confirms that its global margin is razor-thin.
Nothing in R1 broadens that envelope.

## Capture audit

All 18 capture raw files have the same causal sequence:

1. `LocalPlantReplayWorker.evaluate_capture()` reads `runner = self.runner`.
2. `self.runner` returns `self.base_worker.env.runner`.
3. At worker construction time that field is `None`.
4. The code tries to read `runner.cfg.start_folder`.
5. The task exits with an empty trajectory.
6. The later calls to clear/request a restart snapshot and `env.reset()` are
   never reached.

Per-case invariants:

- exception stage: `prepare_replay` (18/18);
- trajectory states/actions: 0/0 (18/18);
- snapshot path recorded: empty (18/18);
- traceback present: yes (18/18);
- source/capture shape comparable: no (18/18);
- primary audit category: `snapshot request not triggered` (18/18).

No conclusion can be made about action equality, visible-state equality, coil
equality, full-wire equality, snapshot time alignment, or capture formal
metrics because the capture environment never started.

## Restart audit

`stage4_2r1_plant_restart_replay` and `stage4_2r1_restart_bank` are empty.
There are zero restart raw files.  The exact gate that stopped restart is:

```text
plant_checkpoint_capture.passed == false
```

The restart phase is therefore `not_run`.  It is scientifically incorrect to
label plant-restart fidelity or restart formal preservation as an observed
failure.

## 1. Runtime/environment errors

- Proven code/runtime error: capture reads the lazily initialized runner
  before calling either `_ensure_runner()` or `env.reset()`.
- Scope: 18/18 capture tasks.
- Effect: no R1 TSC subprocess was launched and no capture trajectory began.
- The Ray runtime itself initialized and scheduled the expected 18 tasks; no
  Ray capacity failure is present.

## 2. Packaging/deployment/import errors

- The deployed R1a package identity and run manifest are internally
  consistent with the downloaded results.
- The selected R17 raw inventory validates exactly by size and SHA-256.
- A Windows-only validation issue was also exposed: nested source inventory
  digests use `str(Path.relative_to(...))`, producing backslashes locally
  while the server-recorded digest uses forward slashes.  File bytes match;
  only the canonical relative-path separator changes.  This is a
  cross-platform verification bug and must be fixed or normalized before the
  complete local import/resume validation can pass.  It did not cause the
  server capture failure.

## 3. Raw/snapshot integrity errors

- Raw R1 parse failures: 0/18.
- Truncated raw JSON.GZ streams: 0/18.
- Snapshot corruption cannot be assessed: zero snapshot directories/files
  exist.
- There is no evidence of missing or mismatched coil/wire vectors because
  those vectors were never captured.

## 4. Statistics/reporting bugs

- The initial R1 summary converted incomparable shapes to `inf`; strict JSON
  serialization then crashed.  R1a correctly replaced non-finite metrics with
  structured `null`/mismatch information and preserved raw failures.
- The R1a summary reports `distinct_snapshot_paths=1` because every missing
  path is converted through `Path("")` to `"."`.  The evidence-backed count
  of actual snapshot paths is 0.
- `plant_capture_instrumentation_changed_source_trace=true` is misleading:
  no capture trace exists, so the correct state is `not_comparable`, not
  “changed”.
- The top-level `formal_contract_preserved=false` conflates an unrun restart
  phase with an observed formal failure.  The phase status is `not_run`.

These reporting issues do not turn the capture into a valid experiment.

## 5. Experimental-design flaws

- The original capture worker had no interface-level regression test that
  exercised lazy runner initialization through the real environment/worker
  boundary.  Unit tests covered snapshot helper methods but did not catch the
  lifecycle ordering error.
- R1 intentionally omits observer, integrator, previous correction, pending
  queue, and trusted controller checkpoint state.  That remains a valid R1
  isolation choice and is not the cause of the present failure.
- The exact-restart requirement is intentionally strict.  It has not yet
  been exercised and must not be weakened after results are seen.

## 6. Real plant-restart conclusions

- Capture instrumentation fidelity: `not_established_runtime_error`
- Snapshot integrity: `not_evaluable_no_snapshot_created`
- Plant-restart initial-state fidelity: `not_run`
- Plant-restart suffix fidelity: `not_run`
- Formal-contract preservation across restart: `not_run`

There is no authentic R1 plant-restart success or failure in the downloaded
result.

## 7. What can be frozen

- R17 finite 18-case source identity and exact source-file hashes.
- Four weak-slew modified paths: delay 1 uses 6x one-sided braking; delay 2
  uses 7x.
- Fourteen unchanged source paths.
- Original formal timing and unchanged position/speed/Ip/arrival-streak gates.
- R1 experiment IDs, action sequences, target/delay/slew matrix, checkpoint
  step 20, and intended 1300 ms snapshot folder.
- R1 remains a plant-only action replay; controller checkpoint replay remains
  deferred.

## 8. What remains unvalidated

- Any authentic snapshot export, including `sprsina`, 14-coil, and full-wire
  state.
- Fresh-process plant initialization and first-step continuity.
- Exact restart suffix replay and prefix/suffix reconstruction.
- Formal-contract preservation through a restart.
- Controller-state restart.
- Different initial states and hidden vessel/eddy histories.
- New targets, continuous delay/gain/slew, plant/Jacobian mismatch, noise,
  disturbance recovery, independent long hold, and deployment robustness.
- BC, DAgger, and bounded residual RL remain out of scope.

## 9. Next step tied to the final task

Apply the minimum runner lifecycle fix before `runner.cfg` is read, add a
real-interface regression test, normalize canonical inventory paths for local
cross-platform validation without changing any file content or scientific
identity, assign a new package hotfix revision while retaining the controller
revision and experiment IDs, and prove resume compatibility.  After full
local validation, deploy directly without archives and resume the exact
existing remote run.  Only failed/incomplete captures are reusable as
pending; there are no successful R1 captures to preserve.  Restart may run
only after all 18 captures and snapshots authenticate.

This action directly advances the reliable MPC expert roadmap by establishing
the authentic plant-state restart prerequisite.  It does not advance to
controller restart or learning prematurely.

## Audit artifacts

- `artifacts/codex_audits/stage4_2r1_inventory.json`
- `artifacts/codex_audits/stage4_2r1_capture_audit.csv`
- `artifacts/codex_audits/stage4_2r1_restart_audit.csv`
- `artifacts/codex_audits/stage4_2r1_snapshot_audit.csv`

## Commands and outcomes at the baseline forensic checkpoint

- Repository/PWD preflight: passed; current directory is inside the Git root.
- `git status --short`, branch, log, root: inspected; starting tree was clean.
- Complete mandatory context files: read.
- Local R1 run inventory: 42 files, 9 directories.
- Full R1/R1a logs: read.
- All 18 capture raw JSON.GZ streams: parsed and classified.
- All 18 selected R17 source raw files: parsed and checked against recorded
  sizes/SHA-256.
- All 22 plain run JSON plus 18 run JSON.GZ: parse passed.
- Server commands at this checkpoint: none.
- R1 true `gotsc` capture/restart execution at this checkpoint: no.

## R1b minimum hotfix and predeployment validation

The evidence-backed hotfix package is:

```text
controller_revision = true_tsc_plant_restart_action_replay_v42r1
package_revision    = r42r1b_lazy_runner_capture_resume_v3
```

The controller revision is deliberately unchanged.  The package revision
records these non-physical fixes:

- construct the real lazy `TSCStepRunner` through
  `TscRzipEnv._ensure_runner()` before reading runner configuration or
  registering the snapshot request;
- retain R1 and R1a as accepted legacy package revisions;
- preserve the original path-bearing selected-expert digest during resume so
  the 18 experiment IDs remain unchanged;
- compare cross-host selected expert evidence by case identity, experiment ID,
  byte size, and SHA-256 rather than trusting the absolute locator root;
- canonicalize nested source inventory relative paths with POSIX separators;
- count no missing snapshot path as `"."`;
- report a missing capture trace as `not_comparable`;
- serialize unrun restart fidelity/formal metrics as `null` with explicit
  `not_run` status.

The isolated resume simulation copied the original manifest, state, and all
18 raw capture files into `.codex_tmp/` and proved:

- old package history upgraded from R1/R1a to R1b;
- direct R17 source digest remained
  `aaab69882fff50eed024fd7ffa7babf473a27c729a0944914c739034c9b4f2f6`;
- selected expert digest remained
  `95ef2cdbdbbbecdf0a58b316b44cca4fb788613b1a87c1f9b48e897175b2c112`;
- all 18 current capture spec IDs exactly matched the 18 old raw filenames;
- all 18 failed captures remained pending;
- a separate regression test proved only a complete successful capture with
  an untampered snapshot/manifest is reusable.

The local source audit was also recomputed through the actual R17/R13/R8
tracking-metric code after canonical path normalization.  All 18 cases passed
and every recomputed margin matched the frozen R17 formal-grid value; the
minimum remained `1.0456920999768471e-05`.

Predeployment validation:

| Check | Outcome |
|---|---|
| `compileall` over configs/scripts/package/tests | passed |
| Complete unit-test discovery | 427/427 passed |
| Focused R1b tests | 23/23 passed |
| Strict plain JSON parse | 1133/1133 passed |
| Strict raw JSON.GZ parse | 10703/10703 passed |
| Package checksum rows | 105/105 passed |
| Declared versus actual package tree | 99/99 tree files matched |
| Internal import closure | passed, 41 packaged modules |
| Empty-directory direct-copy simulation | 106/106 files copied |
| Empty-directory checksum/import/self-test | passed |
| Empty-directory focused R1b tests | 23/23 passed |

Predeployment package hashes:

- `PACKAGE_MANIFEST.json`:
  `dfe902357f58b278763b141a77d5ab2a447aeca58441242f22c2a39d3d82b6e0`
- `SHA256SUMS`:
  `c519666eeb46725479df08464dca81889575da449c3ee57af401b2986a6e1ab5`
- R1 config:
  `8f4f4fcdf71c6dc4ab05e9c3568d7c8f257939ba9ccc845dbc1c1cfc96a7efa1`
- R1 implementation:
  `ed410725b3fee8df4de9c3486ca2c7217461e44ca1bf94799010d5cc7ec878ca`
- Focused R1 tests:
  `3813ca13bde60a73b7d02743b7fc2b00f4d7c1a061f11c147731e653bdf6f004`

At this checkpoint the server is still untouched by the hotfix and no new TSC
task has been claimed.

## Remote preflight status

The `tsc-airgap` alias was not resolvable by the only local OpenSSH client.
On 2026-07-30 the user then explicitly authorized that client to use the
existing `id_ed25519_tsc` identity for the recorded endpoint, with
identity-only, public-key-only authentication.  Codex used that narrow
authorization without reading or changing the identity or external SSH
configuration.

The task-scoped read-only preflight connected successfully and verified the
canonical project and virtualenv paths.  The server still holds package
`r42r1a_capture_failure_finite_summary_v2` and controller revision
`true_tsc_plant_restart_action_replay_v42r1`.  The exact existing run has 42
files and 9 subdirectories: capture raw 18/18 and parseable 18/18, successful
capture 0/18, snapshot case directories 0/18, and restart raw 0/18.  No
Stage4.2R1 process is active.  These remote observations agree with the local
forensic evidence and establish that the exact run is inactive and eligible
for the already-proved R1b semantic-preserving resume.

No remote file was transferred or changed during these checks and no TSC task
ran.  Direct uncompressed deployment and server validation are now the next
steps; the exact handoff is recorded in `docs/codex/CURRENT_STATUS.md`.

## R1b final server-result forensics

R1b was subsequently deployed with the exact predeployment hashes above.
Both staging and installed validation passed checksum verification,
compile/import closure, scientific guards, `bash -n`, and 427/427 complete
server tests.  The exact old run was resumed without changing the controller
revision, 18 experiment IDs, R17 selected-expert digest, or formal timing.

Execution identity:

```text
local deployment checkpoint = 0c87297
remote project              = /home/yangshen0711/tsc_all/tsc_rzip_rllib
remote run                  = /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619
remote log                  = /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260730_061527.log
driver PID                  = 1203573
backend/workers             = ray / 128
```

Eighteen concurrent real `gotsc` processes and 18 stage-owned episode
directories were observed.  Therefore R1b did perform authentic TSC capture
work.  It did not perform a true filesystem restart.

The complete run has 186 files totaling 2,134,305,226 file bytes.  The
uncompressed server tree and log were copied directly into the repository.
Independent remote and local SHA-256 inventories each contain 186 rows:
missing 0, extra 0, mismatched 0.

### Capture evidence

All 18 new capture raw JSON.GZ files parse.  All 18 have:

```text
success                = false
capture_exception_stage = action_replay
failure_reason         = TypeError(Path(None))
```

The common traceback is:

```text
evaluate_capture
  -> env.step(final action)
  -> _state_record_full
  -> _read_wire_currents_a
  -> Path(runner.current_folder)
```

`TscRzipEnv.step()` performs normal episode cleanup before returning the final
truncated step.  That cleanup deliberately sets `runner.current_folder=None`.
R1b then attempted to read terminal full-wire telemetry through the cleared
pointer.  This is a runtime/instrumentation lifecycle error after the terminal
physical action, not a TSC failure.

The 12 normal-horizon raws contain 35 of 36 required state rows and 34 of 35
persisted action rows.  The 6 weak-horizon raws contain 37 of 38 state rows and
36 of 37 persisted action rows.  Control flow and traceback establish that the
last action was executed before the terminal telemetry read failed.

For every case:

- the complete persisted visible-state prefix is shape-comparable to the
  selected R17 source and bit-exact; maximum difference is `0.0`;
- the complete persisted action prefix is bit-exact;
- the terminal state/hold-through sample is missing, so the formal metric is
  `not_comparable`, not pass or fail.

### Snapshot evidence

The 200 ms one-shot requests fired in all 18 cases.  Every snapshot is at
source time 1300 ms and contains the six required files plus both optional
files:

```text
inputa
sprsina
geqdsk
outputa
coil_currents.csv
wire_currents.csv
sprsoua
tsc.cgm
```

This is 18 directories and 144 files.  Offline comparison against raw
checkpoint row 20 found:

- required-file completeness: 18/18;
- snapshot/checkpoint index and time alignment: 18/18;
- 14-coil vector shape: 14/14 in every case;
- maximum coil difference:
  `7.105427357601002e-15` kA-turn, within `1e-12`;
- full wire-current shape: 48/48 in every case;
- full wire-current exact equality: 18/18;
- maximum wire-current difference: `0.0` A.

No `restart_snapshot_manifest.json` was written because the terminal telemetry
exception occurred before `snapshot_inventory`.  The files are present and
remote/local hashes agree, but the preregistered in-run manifest/digest gate
was not completed.  The snapshots therefore cannot yet be frozen as
authenticated successful capture artifacts.

### Restart evidence

Restart raw is 0/18.  The exact prerequisite gate was failed capture
authentication.  The R1b summary now correctly records:

```text
plant_restart_replay_status        = not_run
plant_restart_fidelity_passed      = null
formal_contract_preservation_status = not_run
formal_contract_preserved          = null
```

This is no evidence for either restart success or restart failure.

## R1b result classification

### 1. Runtime/environment errors

There is one proven runtime/instrumentation error affecting 18/18 cases:
terminal full-wire telemetry dereferenced `runner.current_folder` after the
environment's normal truncation cleanup cleared it.  TSC itself completed all
18 capture horizons without a recorded abnormal exit.

### 2. Packaging/deployment/import errors

None in R1b.  Staging and installed package verification, import/compile,
shell syntax, and 427 server tests passed.  Deployed hashes matched local
R1b hashes.

### 3. Raw/snapshot integrity errors

Raw parse corruption: none.  Download corruption: none across 186 hashes.
All required snapshot files exist and checkpoint coil/wire comparisons pass
offline.  The missing in-run snapshot manifests are an incomplete capture
finalization result, not demonstrated byte corruption.

### 4. Statistics/reporting bugs

No new reporting bug was found.  R1b correctly preserves the partial
trajectories, reports a finite structured failure, counts no empty snapshot
path, and keeps restart/formal results tri-state `not_run`.

### 5. Experimental-design flaws

The real terminal lifecycle was absent from R1b's interface regression tests.
Tests covered lazy runner creation and snapshot export but not reading
full-wire telemetry after `TscRzipEnv.step()` performs normal terminal
cleanup.

### 6. Real plant-restart conclusions

Capture instrumentation is exact for every persisted prefix, and authentic
200 ms plant files were exported.  Complete capture fidelity is not yet
certified because the terminal state and in-run snapshot manifest are missing.
Fresh-process plant restart did not run.  No plant-restart or closed-loop
control failure is supported.

### 7. What can be frozen

R17 remains frozen only on its finite clean 18-case static grid, with the
original 250/350 and 270/370 ms contract.  R1b additionally proves that the
snapshot request reaches authentic TSC and exports complete checkpoint
coil/wire files in all 18 cases.  R1 itself cannot yet be frozen.

### 8. What remains unvalidated

Complete capture authentication, fresh plant restart initial-state fidelity,
restart suffix fidelity, formal preservation after restart, controller-state
restart, hidden histories, different initial states, new targets, continuous
parameters, plant/model error, noise, disturbance recovery, and independent
long hold remain unvalidated.  BC, DAgger, and residual RL remain blocked.

### 9. Next step tied to the final task

Fix only terminal telemetry folder selection, retain controller revision and
experiment identity, prove R1b resume compatibility, then resume the same run.
This is required to authenticate the plant restart substrate before adding
controller-state complexity.

## R1c terminal telemetry hotfix

The evidence-backed package is:

```text
local commit        = 4ff8a1d
controller_revision = true_tsc_plant_restart_action_replay_v42r1
package_revision    = r42r1c_terminal_wire_telemetry_resume_v4
```

R1c first reads full-wire telemetry from `runner.current_folder`.  Only when
normal terminal cleanup has cleared that pointer does it use the authentic
folder already retained in `env.last_state["folder"]`.  If neither exists it
still fails structurally.  No action, observation, TSC call, checkpoint,
matrix, deadline, hold horizon, controller state, or physical semantics
changed.  The same fallback covers terminal capture and terminal restart.

An actual R1b manifest/raw resume simulation proved:

- package history upgrades through R1b to R1c;
- controller revision is unchanged;
- source digest remains
  `aaab69882fff50eed024fd7ffa7babf473a27c729a0944914c739034c9b4f2f6`;
- selected expert digest remains
  `95ef2cdbdbbbecdf0a58b316b44cca4fb788613b1a87c1f9b48e897175b2c112`;
- experiment IDs match 18/18;
- failed captures remain pending 18/18;
- the R17 source audit still passes.

R1c local validation:

| Check | Outcome |
|---|---|
| `compileall` | passed |
| Complete unit-test discovery | 428/428 passed |
| Focused R1 tests | 24/24 passed |
| Strict plain JSON parse | 1186/1186 passed |
| Strict raw JSON.GZ parse | 10721/10721 passed |
| Package checksum rows | 105/105 passed |
| Declared versus actual package tree | 99/99 matched |
| Internal import closure | passed, 41 modules |
| Empty-directory direct-copy simulation | 106/106 files |
| Empty-directory focused R1 tests | 24/24 passed |

R1c package hashes:

- `PACKAGE_MANIFEST.json`:
  `c7971a09a647628b9e035d3c46be447571e20e7fee8c963305265248ba920d82`
- `SHA256SUMS`:
  `39ae778673accb3df9cb9c6f6c9d6575aa625f224494df17aed082e113a2d4fc`
- R1 config:
  `7cc9c1442bcc7b369e73e8b25adce29852fb2137f522d81709c437ce9072a80a`
- R1 implementation:
  `83e0bf0c7113e9b8eb1b56ef11c02bfa90079f301344c49627ba3a81e6d90161`
- Focused R1 test:
  `c672a516a854c45020c55ba28bb87a7a848f74e1f924ece059882750fa9d99d5`

## R1b/R1c audit artifacts

- `artifacts/codex_audits/stage4_2r1_r1b_inventory.json`
- `artifacts/codex_audits/stage4_2r1_r1b_capture_audit.csv`
- `artifacts/codex_audits/stage4_2r1_r1b_restart_audit.csv`
- `artifacts/codex_audits/stage4_2r1_r1b_snapshot_audit.csv`
- `artifacts/server_validation/stage4_2r1_r1b_remote_run_sha256_20260730_061527.txt`
- `artifacts/server_validation/stage4_2r1_r1b_local_run_sha256_20260730_061527.txt`
- `artifacts/server_logs/stage4_2r1_true_tsc_plant_restart_action_replay_20260730_061527.log`

## R1c final authenticated result

R1c was deployed and installed with the package hashes recorded above.  Both
staging and installed validation passed package checksum verification,
compile/import closure, scientific guards, shell syntax, and 428/428 server
tests.  The exact existing run was resumed:

```text
remote run = /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619
remote log = /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260730_070023.log
driver PID = 1217510
backend    = ray
workers    = 128
```

During capture and restart, 18 concurrent real `gotsc` processes were observed
for each phase.  The driver exited normally and the complete log contains no
traceback.

### Raw and snapshot evidence

The final run contains 261 files totaling 2,134,623,716 bytes:

- capture raw: 18/18, strict parse 18/18, success 18/18;
- restart raw: 18/18, strict parse 18/18, success 18/18;
- snapshot cases: 18/18;
- snapshot payloads: 144 files;
- snapshot manifests: 18/18;
- all run JSON/JSON.GZ: strict parse 114/114.

Independent remote/local SHA-256 inventories matched 261/261 with missing 0,
extra 0, and mismatch 0.  A separate server-side Python postprocessor then
read the selected source raw directly from their recorded R11/R17 paths and
verified all 18 recorded sizes and hashes.

All 18 snapshot manifests were independently reconstructed from their file
rows and all listed payload sizes/SHA-256 were recomputed.  Manifest/hash
failures were 0.  Each snapshot contains:

```text
inputa
sprsina
geqdsk
outputa
coil_currents.csv
wire_currents.csv
sprsoua
tsc.cgm
```

`1300ms` is the absolute TSC clock, not the elapsed checkpoint:
`1100 ms + 20 * 10 ms = 1300 ms`, so elapsed capture is exactly 200 ms.
After converting `coil_currents.csv` from kA-turn with the configured TSC-order
turn counts, its maximum difference from the raw checkpoint 14-coil vector is
0 A.  All 48 wire currents are also exactly equal.

### Independent recomputation

The postprocessor recomputed every comparison from raw data and matched the
saved per-case result rows:

```text
capture visible/source maximum difference       = 0
capture/source action maximum difference         = 0
snapshot coil maximum difference                 = 0 A
snapshot wire maximum difference                 = 0 A
restart initial and suffix visible difference    = 0
restart full 48-wire suffix difference           = 0 A
restart/source action maximum difference         = 0
recombined/source visible maximum difference     = 0
saved capture rows match recomputation            = true
saved restart rows match recomputation            = true
```

There is no duplicate or missing checkpoint interval: the recombination is
capture states `[0, 20)` plus restart states `[20, horizon]`, producing
`horizon + 1` states.

The immutable formal metric was recomputed from the combined raw trajectory:

- 12 normal-slew cases arrive at 250 ms and hold through 350 ms;
- 6 weak-slew cases arrive at 270 ms and hold through 370 ms;
- formal pass: 18/18;
- minimum signed margin:
  `1.04569209997685e-05`;
- minimum case:
  `RZ_p10_m10`, delay 0, slew 0.9, arrival 270 ms.

### Final classification

1. Runtime/environment errors: none in R1c.
2. Packaging/deployment/import errors: none.
3. Raw/snapshot integrity errors: none in the finite 18-case result.
4. Statistics/reporting bugs: no R1c mismatch; saved result rows match
   independent raw recomputation.
5. Experimental-design limitation: R1 uses exact action replay and deliberately
   restores no controller state.
6. Real plant-restart conclusion: authentic filesystem `sprsina` restart is
   bit-exact for R/Z/Ip, vessel aggregates, all 14 coil channels, and all 48
   wire currents over every same-action suffix in 18/18 cases.
7. What can be frozen: the R1 plant restart bank and same-source plant-restart
   fidelity on the finite clean R17 expert map.
8. What remains unvalidated: controller-state restart, hidden-history
   variation, different initial states, new targets, continuous parameters,
   plant/Jacobian error, noise, disturbance recovery, independent long hold,
   and deployment robustness.
9. Next step: Stage4.2R2 must persist controller state and recompute actions
   online on the certified plant bank.  BC, DAgger, and RL remain blocked.

Final compact evidence:

- `artifacts/codex_audits/stage4_2r1_r1c_inventory.json`
- `artifacts/codex_audits/stage4_2r1_r1c_remote_raw_forensics.json`
- `artifacts/server_hashes/stage4_2r1_r1c_remote_sha256_20260730.txt`
- `artifacts/server_logs/stage4_2r1_true_tsc_plant_restart_action_replay_20260730_070023.log`
- `artifacts/server_validation/stage4_2r1_r1c_staging_validation_20260730.log`
- `artifacts/server_validation/stage4_2r1_r1c_installed_validation_20260730.log`
