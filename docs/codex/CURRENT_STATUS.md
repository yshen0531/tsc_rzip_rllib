# Current status

## Stage4.2R1 R1c predeployment checkpoint

Status timestamp: 2026-07-30 Asia/Shanghai

Local branch/commit:

```text
codex/stage4_2r1-forensics
4ff8a1d fix(stage4.2r1): preserve terminal wire telemetry
```

Package identity:

```text
stage               = Stage4.2R1
controller_revision = true_tsc_plant_restart_action_replay_v42r1
package_revision    = r42r1c_terminal_wire_telemetry_resume_v4
```

## R1b server result

R1b was deployed and validated with the existing server virtualenv, then
resumed against the exact existing run:

```text
run = /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619
log = /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260730_061527.log
pid = 1203573 (finished)
```

Observed execution and final evidence:

1. Real capture `gotsc` ran with 18 concurrent processes/tasks.
2. Capture raw is 18/18 and parses 18/18, but success is 0/18.
3. All failures are the same terminal telemetry error:
   `Path(runner.current_folder)` received `None` after normal environment
   truncation cleanup.
4. The 12 normal trajectories contain 35 rather than 36 states; the 6 weak
   trajectories contain 37 rather than 38 states.  The terminal action had
   executed, but its terminal state row was not persisted.
5. Every persisted visible prefix and recorded action prefix is bit-exact to
   its frozen R17 source.
6. All 18 authentic 1300 ms snapshot folders exist with 8 files each.  Required
   files are complete 18/18; checkpoint coil vectors agree within
   `7.105427357601002e-15` kA-turn and all 48 wire currents are bit-exact.
7. Snapshot manifests are 0/18 because the terminal exception occurred before
   snapshot inventory finalization.
8. Restart raw is 0/18.  Restart and formal preservation are `not_run`, not
   failed.

The complete uncompressed 186-file, 2,134,305,226-byte run and log were
downloaded.  Remote/local inventory is 186/186 with missing 0, extra 0, and
SHA-256 mismatch 0.

## R1c fix and validation

R1c adds only a terminal full-wire telemetry fallback to the TSC output folder
already retained in `env.last_state["folder"]`.  It does not change the
controller revision, action sequence, environment observation, TSC lifecycle,
task matrix, checkpoint, or formal timing.

Local validation:

```text
compileall                         passed
complete unittest discovery       428/428
focused R1 tests                   24/24
strict JSON                        1186/1186
strict JSON.GZ                     10721/10721
package checksums                  105/105
package-tree files                 99/99
internal import closure            41 modules, passed
actual R1b resume experiment IDs   18/18 unchanged
failed R1b captures pending        18/18
R17 source audit                   passed
empty-directory direct copy       106/106
empty-directory focused tests     24/24
```

Package hashes:

```text
PACKAGE_MANIFEST.json  c7971a09a647628b9e035d3c46be447571e20e7fee8c963305265248ba920d82
SHA256SUMS             39ae778673accb3df9cb9c6f6c9d6575aa625f224494df17aed082e113a2d4fc
R1 config              7cc9c1442bcc7b369e73e8b25adce29852fb2137f522d81709c437ce9072a80a
R1 implementation      83e0bf0c7113e9b8eb1b56ef11c02bfa90079f301344c49627ba3a81e6d90161
focused test           c672a516a854c45020c55ba28bb87a7a848f74e1f924ece059882750fa9d99d5
```

## Next action

The server currently contains the finished R1b package/run.  R1c is ready for
direct uncompressed deployment and installed-package validation.  After those
checks pass, resume the same run with:

```text
STAGE4_2R1_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619
STAGE4_2R1_RESUME=1
STAGE4_2R1_COMMAND=all
STAGE4_2R1_BACKEND=ray
STAGE4_2R1_WORKERS=128
```

The task-scoped user-authorized explicit identity route remains the access
method because the local `tsc-airgap` alias is unresolved.  Codex does not
read, copy, display, or modify the identity or external SSH configuration.
