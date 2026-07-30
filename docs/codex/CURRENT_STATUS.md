# Current status

## Stage4.2R1 R1b hotfix

Status timestamp: 2026-07-30 Asia/Shanghai

Local branch/commit:

```text
codex/stage4_2r1-forensics
ce03aa5 docs(stage4.2r1): record ssh alias handoff
code checkpoint: 0c87297 fix(stage4.2r1): initialize capture runner before resume
```

Package identity:

```text
stage               = Stage4.2R1
controller_revision = true_tsc_plant_restart_action_replay_v42r1
package_revision    = r42r1b_lazy_runner_capture_resume_v3
```

The baseline forensics, minimum lifecycle/reporting fix, full local tests,
strict JSON/JSON.GZ parse, source recomputation, resume compatibility test,
checksum verification, import closure, and empty-directory deployment
simulation have passed.  The user-authorized explicit identity command has
also restored task-scoped server access and the read-only remote preflight has
passed.  No server file has yet been changed and no new TSC task has run.

## Remote access and read-only preflight

The configured `tsc-airgap` alias remains unavailable to the local OpenSSH
client.  On 2026-07-30 the user explicitly authorized the existing OpenSSH
client to use the existing `id_ed25519_tsc` identity for this endpoint, with
`IdentitiesOnly=yes`, public-key-only authentication, and password
authentication disabled.  Codex did not read, copy, display, or modify the key
or external SSH configuration.

That task-scoped route connected successfully as `yangshen0711` on `master`.
The mandatory non-destructive checks confirmed:

1. `HOME=/home/yangshen0711`;
2. canonical project and virtualenv paths exist;
3. the remote package is still
   `r42r1a_capture_failure_finite_summary_v2`;
4. the controller revision is still
   `true_tsc_plant_restart_action_replay_v42r1`;
5. the existing run contains 42 files and 9 subdirectories;
6. capture raw is 18/18 and parses 18/18, with success 0/18;
7. snapshot cases are 0/18 and restart raw is 0/18;
8. no Stage4.2R1 process is active.

The remote package/run remains untouched.  The next authorized actions are:

1. directly replace the four declared code trees and current R1 root files,
   without archives;
2. run the server package verifier, import/compile checks, and `bash -n`;
3. resume the exact existing run with:

   ```text
   STAGE4_2R1_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619
   STAGE4_2R1_RESUME=1
   STAGE4_2R1_COMMAND=all
   STAGE4_2R1_BACKEND=ray
   STAGE4_2R1_WORKERS=128
   ```

4. monitor the exact PID/state/raw/snapshot/restart counts;
5. directly download the complete uncompressed run and log;
6. verify remote/local counts and hashes and rerun the forensic audit.
