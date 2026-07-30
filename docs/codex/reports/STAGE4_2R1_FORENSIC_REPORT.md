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

The required read-only command using `ssh tsc-airgap` was attempted after
commit `0c87297`.  The only locally available client,
`C:\WINDOWS\System32\OpenSSH\ssh.exe` (OpenSSH 9.5p2), returned
`Could not resolve hostname tsc-airgap`.  No remote command ran, no file was
transferred, and no server state changed.

The repository rules prohibit reading/changing external SSH configuration or
replacing the alias with the identification-only IP endpoint.  Deployment and
resume are therefore pending restoration of the required alias; the exact
handoff is recorded in `docs/codex/CURRENT_STATUS.md`.
