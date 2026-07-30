# SERVER_WORKFLOW.md

## 1. Purpose

This file defines the repeatable Windows ↔ air-gapped TSC server development loop.

No local archive operations are permitted. Use direct tree/file transfer.

## 2. Variables

PowerShell local setup:

```powershell
$Repo = (git rev-parse --show-toplevel).Trim()
Set-Location $Repo

$Ssh = "tsc-airgap"
$RemoteProject = "/home/yangshen0711/tsc_all/tsc_rzip_rllib"
$RemoteStaging = "/home/yangshen0711/tsc_software"
$RemoteVenv = "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu"
```

Do not infer a different path without evidence.

### 2.1 Authorized fixed-endpoint fallback

Use `tsc-airgap` by default. In the current Codex process the alias may fail
name resolution even though the endpoint and key work. After an observed
alias-resolution failure, the user has explicitly authorized this exact
fallback:

```powershell
$SshArgs = @(
  "-i", "$env:USERPROFILE\.ssh\id_ed25519_tsc",
  "-o", "IdentitiesOnly=yes",
  "-o", "PreferredAuthentications=publickey",
  "-o", "PasswordAuthentication=no",
  "yangshen0711@10.10.60.108"
)
ssh @SshArgs 'echo SSH_KEY_OK; whoami; hostname; echo "HOME=$HOME"'
```

For `scp`, use the same identity and `-o` options followed by the exact local
and remote paths. Do not inspect, enumerate, copy, edit, hash, or print the
identity file or SSH configuration. Do not substitute another endpoint,
username, key, or authentication method.

The fixed command was connectivity-tested successfully on 2026-07-30:

```text
SSH_KEY_OK
yangshen0711
master
HOME=/home/yangshen0711
```

## 3. Start-of-task preflight

Local:

```powershell
$Repo = (git rev-parse --show-toplevel).Trim()
Set-Location $Repo
git status --short
git branch --show-current
git log -1 --oneline
```

Remote, read-only:

```powershell
ssh tsc-airgap @'
set -eu
printf 'HOME=%s\n' "$HOME"
test -d "$HOME/tsc_all/tsc_rzip_rllib"
test -f "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
cd "$HOME/tsc_all/tsc_rzip_rllib"
printf 'REMOTE_PROJECT=%s\n' "$PWD"
'@
```

If and only if the alias is unresolved, invoke the same remote script with
the exact `$SshArgs` fallback from section 2.1.

Do not run destructive commands before this succeeds.

## 4. Local evidence analysis

Before changing code:

1. Locate the exact local run directory and log.
2. Read manifest, state, resolved config, summaries, verdict, all raw JSON/JSON.GZ, snapshot manifests, and snapshot files.
3. Build an inventory:
   - expected tasks;
   - actual tasks;
   - unique experiment IDs;
   - parse failures;
   - `success=true/false`;
   - failure stages/reasons;
   - snapshot availability;
   - restart availability.
4. Recompute load-bearing metrics from raw data.
5. Write a report under:
   ```text
   docs/codex/reports/
   ```
6. Write machine-readable audits under:
   ```text
   artifacts/codex_audits/
   ```
7. Do not modify controller code before the evidence map is complete unless the task is an obvious startup/import failure with no TSC tasks executed.

## 5. Local code changes

Use only repository files.

Recommended branch naming:

```text
codex/stage4_2r1-forensics
codex/stage4_2r1-hotfix-<short-cause>
codex/stage4_2r2-controller-restart
```

For a hotfix after real tasks completed:

- preserve experiment IDs and controller revision if physical behavior is unchanged;
- add a package revision;
- add manifest-upgrade compatibility;
- add regression tests that call the real interface, not a mock that hides the bug;
- prove successful raw remains resume-safe;
- reject incompatible source/run revisions.

## 6. Local validation

Use the existing project-local Python environment if present. Do not install packages outside the repository.

At minimum:

```powershell
python -m compileall -q configs scripts tsc_rzip_rllib tests
python -m unittest discover -s tests -p "test*.py"
```

Run the current stage's self-test and package verification where compatible with Windows. Linux shell syntax must also be checked on the server before execution.

Parse all JSON:

```powershell
@'
from pathlib import Path
import json
root = Path(".")
for path in root.rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))
print("JSON OK")
'@ | python -
```

Keep temporary files under `.codex_tmp/`.

## 7. Direct deployment without archives

### 7.1 Full clean replacement

First validate the remote working directory:

```powershell
ssh tsc-airgap @'
set -eu
cd "$HOME/tsc_all/tsc_rzip_rllib"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
printf 'SAFE_REMOTE_PROJECT=%s\n' "$PWD"
'@
```

Then remove only the named code directories and current root shell files:

```powershell
ssh tsc-airgap @'
set -eu
cd "$HOME/tsc_all/tsc_rzip_rllib"
test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
rm -rf configs scripts tests tsc_rzip_rllib
find . -maxdepth 1 -type f -name '*.sh' -delete
rm -f PACKAGE_MANIFEST.json SHA256SUMS
'@
```

Transfer directly:

```powershell
scp -r "$Repo\configs"        "tsc-airgap:$RemoteProject/"
scp -r "$Repo\scripts"        "tsc-airgap:$RemoteProject/"
scp -r "$Repo\tests"          "tsc-airgap:$RemoteProject/"
scp -r "$Repo\tsc_rzip_rllib" "tsc-airgap:$RemoteProject/"
```

Transfer only the current stage's root scripts plus manifest/checksums. Example:

```powershell
scp "$Repo\run_stage4_2r1_true_tsc_plant_restart_action_replay_native.sh" "tsc-airgap:$RemoteProject/"
scp "$Repo\run_stage4_2r1_true_tsc_plant_restart_action_replay_nohup.sh"  "tsc-airgap:$RemoteProject/"
scp "$Repo\run_stage4_2r1_self_test.sh"                                  "tsc-airgap:$RemoteProject/"
scp "$Repo\run_stage4_2r1_verify_package.sh"                             "tsc-airgap:$RemoteProject/"
scp "$Repo\run_stop_stage4_2r1_now.sh"                                   "tsc-airgap:$RemoteProject/"
scp "$Repo\PACKAGE_MANIFEST.json"                                        "tsc-airgap:$RemoteProject/"
scp "$Repo\SHA256SUMS"                                                    "tsc-airgap:$RemoteProject/"
```

Adapt filenames to the actual current stage. Never upload a historical forest of root `.sh` files.

### 7.2 Patch deployment

A patch-only deployment is allowed only when:

- the exact server base hashes are verified;
- the patch is idempotent;
- physical controller semantics and experiment IDs remain unchanged;
- the complete standalone local tree is also updated.

Otherwise perform a full clean replacement.

## 8. Server package validation

```powershell
ssh tsc-airgap @'
set -eu
cd "$HOME/tsc_all/tsc_rzip_rllib"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
chmod +x ./*.sh scripts/*.sh scripts/*.py 2>/dev/null || true
./run_stage4_2r1_verify_package.sh
'@
```

Use the actual current-stage verify script.

Record the complete output in a repository-local text file under:

```text
artifacts/server_validation/
```

## 9. Start or resume a server run

Fresh run example:

```powershell
ssh tsc-airgap @'
set -eu
cd "$HOME/tsc_all/tsc_rzip_rllib"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
STAGE4_2R1_WORKERS=128 \
STAGE4_2R1_BACKEND=ray \
STAGE4_2R1_COMMAND=all \
STAGE4_2R1_RESUME=0 \
./run_stage4_2r1_true_tsc_plant_restart_action_replay_nohup.sh
'@
```

Resume example:

```powershell
ssh tsc-airgap @'
set -eu
cd "$HOME/tsc_all/tsc_rzip_rllib"
source "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
STAGE4_2R1_RUN_DIR="/absolute/existing/run_dir" \
STAGE4_2R1_WORKERS=128 \
STAGE4_2R1_BACKEND=ray \
STAGE4_2R1_COMMAND=all \
STAGE4_2R1_RESUME=1 \
./run_stage4_2r1_true_tsc_plant_restart_action_replay_nohup.sh
'@
```

Resume only when experiment identity and physical semantics are unchanged.

## 10. Monitor actual execution

Capture run and log paths from the launcher output or latest pointer files.

Read-only monitoring example:

```powershell
ssh tsc-airgap @'
set -eu
cd "$HOME/tsc_all/tsc_rzip_rllib"
RUN_DIR="$(cat stage4_2r1_runs/latest_stage4_2r1_run.txt)"
LOG_FILE="$(cat logs/nohup/latest_stage4_2r1_true_tsc_plant_restart_action_replay.log)"
printf 'RUN_DIR=%s\nLOG_FILE=%s\n' "$RUN_DIR" "$LOG_FILE"
tail -n 200 "$LOG_FILE"
'@
```

Do not infer completion from a quiet log. Check:

- exact process/PID;
- state file;
- raw task count;
- final summary/verdict creation;
- launcher exit status if available.

If the task remains active, continue polling in the current Codex task when practical. If the session must stop, write exact status and commands to `docs/codex/CURRENT_STATUS.md`.

## 11. Evidence retrieval without archives

Large result trees must now be postprocessed in place on the server with the
existing project code and existing virtualenv.  Do not download large raw,
snapshot, or trajectory trees to the local repository.

For a large run:

1. keep the raw result tree immutable;
2. run a read-only Python postprocessor inside `REMOTE_PROJECT`;
3. make the postprocessor read every required raw JSON/JSON.GZ and snapshot
   payload, verify strict JSON, counts, sizes, SHA-256, source fingerprints,
   and recompute all load-bearing metrics;
4. write only compact audit JSON/CSV, inventory/hash lists, and analysis logs;
5. transfer those compact artifacts directly without compression;
6. record the exact remote run path so any raw claim remains reproducible.

The compact audit must contain enough per-case evidence to distinguish runtime,
package, corruption, reporting, design, and real control/plant conclusions.
It must not merely copy a saved verdict.

Small result trees may still be copied directly when a complete local copy is
materially useful.  No ZIP/TAR operation is permitted in either workflow.

### 11.1 Direct copy for a small result tree

Create a repository-local destination:

```powershell
$LocalRunRoot = Join-Path $Repo "artifacts\server_runs"
$LocalLogRoot = Join-Path $Repo "artifacts\server_logs"
New-Item -ItemType Directory -Force $LocalRunRoot | Out-Null
New-Item -ItemType Directory -Force $LocalLogRoot | Out-Null
```

Copy a small run tree directly:

```powershell
scp -r "tsc-airgap:/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/<run_name>" "$LocalRunRoot\"
scp    "tsc-airgap:/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/<log_name>" "$LocalLogRoot\"
```

Do not ZIP/TAR either side for this workflow.

When a small snapshot tree is copied, preserve filenames and directory
hierarchy exactly.

### 11.2 Windows Unicode path and remote-shell quoting safeguards

On a Windows workspace whose absolute path contains non-ASCII characters,
some interactive SFTP clients may replace the local path with `?` and still
return exit code 0 after transferring zero files.  Therefore:

1. prefer direct `scp` of exact compact files or one directly copied compact
   directory;
2. verify the local file count, total bytes, and SHA-256 values after every
   transfer;
3. never treat process exit code alone as transfer success.

When PowerShell invokes SSH, avoid embedding remote wildcard/destructive
expressions whose quotes must survive multiple parsers.  Prefer a fixed
repository script transferred and checked with `bash -n`.  If an inline
remote command is unavoidable, first test its quoting read-only and retain
the canonical-directory guard before any named deletion.  A failed quoting
step must be classified as deployment/tooling error and must not be reported
as an experiment result.

## 12. Verify retrieved evidence

After transfer:

1. compare remote and local file counts;
2. compare manifest-listed sizes/hashes;
3. parse every JSON/JSON.GZ;
4. check expected raw count;
5. check snapshot file inventory;
6. check no truncated file;
7. record transfer verification under:
   ```text
   artifacts/transfer_manifests/
   ```

A copied directory is not trusted until this check passes.  A server-processed
large run is not trusted until the compact audit proves raw coverage, strict
parse, snapshot inventory/hash integrity, and independent metric
recomputation.

## 13. Analyze and iterate

Classify findings:

```text
runtime/environment
deployment/package
snapshot/corruption
summary/statistics
design
true plant/control result
```

Then:

- summary-only bug with unchanged experiment semantics: patch and resume;
- physical controller/task change: new stage or new run;
- authentic plant restart success: advance to controller-state restart;
- authentic plant restart failure: isolate file/state/restart cause first;
- no route choice needed: implement the next complete standalone stage;
- route choice genuinely needed: present a compact evidence-based decision.

## 14. Run ledger

Maintain `docs/codex/RUN_LEDGER.md` with one entry per run:

```text
stage
local branch/commit
package revision
source run
remote run directory
remote log
fresh/resume
expected/actual tasks
result
known bugs
download location
evidence hashes
next step
```

This ledger is required to prevent version/result confusion across long-running iterations.
