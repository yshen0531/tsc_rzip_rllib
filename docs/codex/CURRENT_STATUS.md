# Current status

## Stage4.2R1 R1b hotfix

Status timestamp: 2026-07-30 Asia/Shanghai

Local branch/commit:

```text
codex/stage4_2r1-forensics
0c87297 fix(stage4.2r1): initialize capture runner before resume
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
simulation have passed.  No server file has been changed and no new TSC task
has run.

## Blocking condition

The mandatory read-only remote preflight was attempted with the required
alias:

```powershell
ssh tsc-airgap <read-only preflight>
```

The local OpenSSH client returned:

```text
ssh: Could not resolve hostname tsc-airgap
```

`Get-Command ssh -All` found only:

```text
C:\WINDOWS\System32\OpenSSH\ssh.exe
OpenSSH_for_Windows_9.5p2
```

Repository rules prohibit reading or changing external SSH configuration and
prohibit replacing the alias with a manually constructed endpoint/authentication
command.  The server is therefore untouched.

## Resume point after the alias is restored

Run the same non-destructive preflight first:

```powershell
ssh tsc-airgap @'
set -eu
printf 'HOME=%s\nPWD=%s\n' "$HOME" "$PWD"
test -d "$HOME/tsc_all/tsc_rzip_rllib"
test -f "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
cd "$HOME/tsc_all/tsc_rzip_rllib"
printf 'REMOTE_PROJECT=%s\n' "$PWD"
'@
```

Only after it passes:

1. verify the old remote package/run hashes and inactive recorded PID;
2. directly replace the four declared code trees and current R1 root files;
3. run the server package verifier and `bash -n`;
4. resume the exact existing run with:

   ```text
   STAGE4_2R1_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619
   STAGE4_2R1_RESUME=1
   STAGE4_2R1_COMMAND=all
   STAGE4_2R1_BACKEND=ray
   STAGE4_2R1_WORKERS=128
   ```

5. monitor the exact PID/state/raw/snapshot/restart counts;
6. directly download the complete uncompressed run and log;
7. verify remote/local counts and hashes and rerun the forensic audit.

