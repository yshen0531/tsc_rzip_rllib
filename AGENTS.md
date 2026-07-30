# AGENTS.md — tokamak RL repository rules

## 0. Instruction priority and mandatory reading

This file is the repository-wide standing instruction for Codex.

Before doing any substantive work, read these repository files if they exist:

1. `docs/codex/TOKAMAK_RL_PROJECT_CONTEXT.md`
2. `docs/codex/SERVER_WORKFLOW.md`
3. `docs/codex/CURRENT_TASK.md`
4. The current stage's config, launcher, manifest, state, logs, raw JSON/JSON.GZ, and snapshot files.

`docs/codex/CURRENT_TASK.md` defines the active task. It may narrow this file, but it may not weaken the filesystem, scientific-integrity, formal-timing, or safety rules below.

Do not rely on prior chat summaries as evidence. Evidence priority is:

1. Raw TSC trajectories, raw JSON/JSON.GZ, snapshot files, coil/wire-current files.
2. The exact code and resolved config that generated them.
3. Manifests, hashes, state files, and complete logs.
4. Derived summaries and verdicts.
5. Old reports, comments, branch names, and previous assistant statements.

## 1. Hard local filesystem boundary

The VS Code workspace/repository root is the only local working area.

At the start of every task:

```powershell
$Repo = (git rev-parse --show-toplevel).Trim()
$Here = (Get-Location).Path
Write-Host "REPO=$Repo"
Write-Host "PWD=$Here"
```

Stop if the current directory is not inside `$Repo`.

Locally, do not directly read, enumerate, create, edit, move, copy, delete, or search any path outside the repository root.

Forbidden examples include:

- `Get-ChildItem C:\`
- enumerating the user profile
- reading or modifying `%USERPROFILE%\.ssh`
- using `%TEMP%`, `/tmp`, the Desktop, Downloads, or another repository as a work directory
- writing generated files outside the repository
- searching the whole disk
- changing system settings
- installing global software or packages

Use `.codex_tmp/` inside the repository for temporary work. Clean only files created there by the current task.

Allowed local process exceptions:

- invoke the existing `ssh`, `scp`, or `sftp` executable with the configured alias `tsc-airgap`;
- if and only if `tsc-airgap` name resolution fails in the current Codex
  process, invoke `ssh`, `scp`, or `sftp` with the user-authorized fixed
  endpoint and identity options documented in
  `docs/codex/SERVER_WORKFLOW.md`; do not inspect the identity or SSH config;
- invoke the existing Git executable and configured Git remote;
- invoke an existing Python interpreter or project-local virtual environment.

These process exceptions do not authorize Codex to open, inspect, alter, copy, or reveal external credential/configuration files. Never print private keys, tokens, SSH configuration, passwords, or secrets.

## 2. No local archive operations

Local files must not be compressed or extracted.

Do not run locally:

- `zip`, `unzip`
- `tar`
- `7z`
- `Compress-Archive`, `Expand-Archive`
- Python archive libraries for packing or unpacking
- any equivalent archive operation

Transfer directory trees and individual files directly with `scp -r` or `sftp`. Keep results uncompressed.

Do not silently convert a direct-copy workflow into an archive workflow.

## 3. Allowed remote scope

SSH alias:

```text
tsc-airgap
```

Actual endpoint, for identification only:

```text
yangshen0711@10.10.60.108
```

Use the alias by default. If the alias is unresolved in the current Codex
process, the only allowed fallback is the exact fixed endpoint, identity
filename, and non-interactive public-key options documented in
`docs/codex/SERVER_WORKFLOW.md`. This fallback was explicitly authorized and
connectivity-tested by the user on 2026-07-30. It does not authorize reading
or modifying the key or SSH configuration.

Canonical remote paths:

```bash
REMOTE_PROJECT="$HOME/tsc_all/tsc_rzip_rllib"
REMOTE_STAGING="$HOME/tsc_software"
REMOTE_VENV="$HOME/tsc_all/tsc_simulation/venv_simu"
```

Roles are different:

- `REMOTE_PROJECT` is the server-side tokamak RL repository and execution directory.
- `REMOTE_STAGING` is only an optional transfer/staging root.
- `REMOTE_VENV` may be activated/read, but its contents must not be modified.

Before any remote change, run a non-destructive preflight:

```bash
printf 'HOME=%s\nPWD=%s\n' "$HOME" "$PWD"
test -d "$HOME/tsc_all/tsc_rzip_rllib"
test -f "$HOME/tsc_all/tsc_simulation/venv_simu/bin/activate"
```

Remote permissions and constraints:

- no root or `sudo`;
- no `apt`, `yum`, system package installation, or global `pip`;
- server has no outbound internet;
- do not use Git on the server;
- do not modify `$HOME/tsc_all/tsc_simulation`, except sourcing the existing virtual environment;
- do not touch unrelated directories under `$HOME`;
- do not broadly kill Python, Ray, or other users' processes;
- stop only the exact current stage process via its PID/launcher/stop script;
- never use an unvalidated variable in `rm -rf`;
- before destructive work, require:
  ```bash
  cd "$HOME/tsc_all/tsc_rzip_rllib"
  test "$PWD" = "$HOME/tsc_all/tsc_rzip_rllib"
  ```

Existing stage launchers may create stage-specific directories under `/tmp`. Do not perform broad `/tmp` cleanup. Only remove a path created by the current stage when its exact ownership and path have been verified.

## 4. Repository focus

Code review and changes should normally be limited to:

1. `configs/`
2. `scripts/`
3. `tsc_rzip_rllib/`
4. `tests/`
5. root-level shell scripts required by the current stage
6. `PACKAGE_MANIFEST.json` and `SHA256SUMS` when used by the current stage
7. `docs/codex/` and task audit outputs created for this workflow

Do not modify historical branches, unrelated experiments, old output trees, or redundant documentation unless the active task proves that they are direct dependencies.

A complete server deployment must include every repository source file that is actually imported. It must not depend on `.git`, GitHub, the network, or an undeclared external source tree.

## 5. Git workflow on Windows

Before edits:

```powershell
git status --short
git rev-parse --show-toplevel
git log -1 --oneline
git branch --show-current
```

Default workflow:

1. Preserve the user's current work. Never reset, clean, stash, or discard unknown changes.
2. Create a focused branch such as:
   ```text
   codex/stage4_2r1-forensics
   codex/stage4_2r1-hotfix
   codex/stage4_2r2-controller-checkpoint
   ```
3. Make small, reviewable commits.
4. Do not rewrite history or force-push.
5. Do not commit large raw run trees unless the repository already tracks them or `CURRENT_TASK.md` explicitly requires it.
6. Keep a clear mapping among local commit, deployed file hashes, remote run directory, resolved config, and log.
7. Merge/push only after the required validation has passed and only according to `CURRENT_TASK.md`. Never push secrets or server credentials.

Create Git checkpoints before and after a substantive task.

## 6. Scientific integrity rules

Always distinguish:

- runtime or environment error;
- packaging/import/deployment error;
- raw-data or snapshot corruption;
- summary/statistics/reporting bug;
- test not run;
- design flaw;
- real closed-loop control failure;
- finite-envelope success;
- unvalidated extrapolation.

Never infer success from:

- a final verdict alone;
- `success=true` alone;
- a Ray `N/N` completion line alone;
- `audit_completed=true`;
- an empty failure reason alone;
- a summary that has not been recomputed from raw data.

Never claim real server `gotsc` execution unless the raw server results prove it.

Do not weaken a preregistered gate after seeing the result. Do not reinterpret an unrun phase as a failed or passed experiment.

When a code bug is found after real TSC tasks finished:

- preserve complete successful raw results;
- resume only if controller semantics, experiment identity, source fingerprints, and scientific task are unchanged;
- create a new run/stage if the controller, task matrix, formal gate, or physical action semantics change.

## 7. Immutable formal timing contract

Unless the user explicitly changes it, the formal contract is:

```text
slew = 1.0 or 1.1:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew = 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms
```

Also preserve:

```text
R/Z tolerance: 30 mm
speed threshold: 0.1 m/s
Ip threshold: unchanged from the frozen baseline
arrival streak: unchanged from the frozen baseline
```

R10/R11 750 ms and 2 s runs are auxiliary diagnostics only. A longer observation horizon must never silently become a later allowed arrival deadline.

Long-hold validation is a separate orthogonal test:

```text
first satisfy the formal arrival deadline
then extend the observation/hold horizon
```

## 8. Current frozen finite baseline

The most recent frozen finite static-grid baseline is Stage4.1R17:

- original-timing finite static grid: 18/18;
- 14 unchanged source paths;
- 4 weak-slew delay 1/2 paths use a one-sided braking patch;
- delay 1 uses 6× braking;
- delay 2 uses 7× braking;
- trusted calibration tokens reproduce Oracle traces exactly;
- R16's large-amplitude bidirectional response model remains invalid;
- this is only a clean, same-digital-twin, two-target, discrete static delay/slew result.

Do not overstate it as restart, hidden-history, unseen-target, continuous-parameter, noise, disturbance, or deployment robustness.

## 9. Current stage

R1c authentic plant-state restart and R2 causal persistent-controller restart
are certified for their finite clean same-source 18-case grids.

Stage4.2R3b completed 72/72 authentic state runs and 32/32 fresh restart
controls. Plant restart and causality were exact, but its phase-zero
controller passed formal control 0/32.

Stage4.2R3c added causal visible-state phase alignment and completed 32/32
authentic controls. It passed 20/32: all 16 prefix-9 cases and only 4/16
prefix-5 cases. Raw forensics found no runtime, corruption, restart,
causality, or solver error. R3c matched against an ideal nominal reference
and selected phases 11--13, while the restart states were nearest to actual
R17 closed-loop visible phases 12--20.

Stage4.2R3c1 then authenticated the actual R17 visible R/Z/Ip manifold and
completed 32/32 successful restart trajectories after a separately audited
four-task runtime hotfix. Exact plant restart and causality were 32/32, but
formal control passed only 16/32. Static nearest-visible-phase matching
repaired none of R3c's failures and regressed four previously passing cases.
The final 16 failures are genuine closed-loop/controller-design failures,
not runtime, restart, raw-corruption, or reporting failures.

Terminology remains:

```text
R1  = Stage4.2R1 authentic TSC plant-state restart
R17 = Stage4.1R17 frozen finite static-grid controller source
```

Stage4.2R3c2 completed 32/32 authentic restart trajectories with exact
restart, causal traces, no runtime/solver/saturation errors, and no raw
corruption, but formal control passed only 12/32. It repaired none of
R3c1's failures and regressed four R3c1 passes. All 16 prefix-5 cases
failed. The final 20 failures are genuine closed-loop/controller-design
failures: the zero-nominal terminal regulator is a local damping controller,
not a finite-horizon restart transport MPC.

Stage4.2R3c3 then completed 256/256 authentic bounded probe trajectories
with exact restart, causal probe execution, no runtime/solver/raw/reporting
error, and all preregistered response gates passed:

```text
central symmetry                    128/128
matched hidden-history response      64/64
rank-4 conditioned response          32/32
maximum condition number             8.0984
maximum current utilization          0.3904
```

R3c3 is only a finite development-envelope identification result. Its probe
trajectories are forbidden from expert datasets. The matched-history response
gate does not independently validate hidden-history closed-loop robustness.

The authenticated R3c3 compact response bank was recomputed from all 256 raw
and 32 exact R3c1 baselines. A prospective four-basis R3c4 feasibility gate
then reproduced all R3c1 metrics exactly but found only 16/32 bounded-oracle
feasibility and repaired 0/16 failed contexts. R3c4 was therefore vetoed
before controller implementation or real TSC; it has zero raw and is not a
real closed-loop result.

Stage4.2R3c3T1 completed all 128 authentic identification tasks. Restart,
causality, central symmetry, matched-history response, transport-only
conditioning, and current gates passed, but the frozen combined six-basis
condition gate passed only 27/32 with a maximum of 29.2962711. T1 is frozen
as an identification-design FAIL; it is not a runtime, restart, reporting,
or real MPC failure.

Corrected server-side optimistic feasibility reproduced all 32 R3c1 formal
results exactly. Scaling T1 mode 0 to 0.85 through 0.70 repaired combined
conditioning to 32/32 but left formal feasibility at 16/32 and repaired
0/16 failed contexts. An amplitude-only T2 and the current six-basis R3c4
are vetoed.

The current stage is Stage4.2R3c3T2 post-contract-neutralized
held-transport identification. Its fixed design is:

```text
mode 0 amplitude 0.0060
mode 1 amplitude 0.0075
positive physical effect states 3 through 8
negative physical effect states 39 through 44
observation through state 50
exact zero net
32 contexts × 2 bases × 2 signs = 128 real rollouts
```

The full gates are frozen in
`docs/codex/reports/STAGE4_2R3C3T2_PREREGISTERED_DESIGN.md` and
`docs/codex/CURRENT_TASK.md`. R3c3T2 may never use source actions/results,
current-run future values, source/current wire currents, or
pair/history/prefix labels inside the controller.

The 500 ms T2 horizon does not change the 250/270 ms arrival deadlines or
the 350/370 ms formal hold endpoints and is not a long-hold success test.

R3c4 may resume only if the combined R3c3 plus R3c3T2 six-basis optimistic
oracle is feasible 32/32 with every coefficient inside `[-1,1]` and no
formal-gate change.

## 10. Required validation before server execution

At minimum, perform and record:

Local/repository-side:

- Python compile or `compileall`;
- all JSON parse;
- focused and complete unit tests;
- import closure;
- manifest/checksum verification;
- source-fingerprint and resume-compatibility tests;
- empty-directory deployment simulation inside the repository;
- no undeclared external import/source-tree dependency.

Server-side:

- exact remote path preflight;
- `bash -n` for declared shell scripts;
- package verification script;
- Python import/compile using the existing server virtual environment;
- no Git/network dependency;
- fixed Ray campaign capacity;
- run-directory and log-path capture.

A local mock or unit test is not a real `gotsc` test. Label each validation accurately.

## 11. Server run and evidence loop

The standard loop is:

```text
inspect local evidence
→ implement locally
→ validate locally
→ transfer directly, without archives
→ validate on server
→ run with existing virtualenv and nohup launcher
→ monitor the actual job
→ transfer the complete uncompressed run/log tree back
→ verify inventory/hashes
→ analyze raw evidence
→ update code or advance the stage
```

Do not promise future analysis. Either continue monitoring in the current task, or leave an exact run-status handoff in `docs/codex/CURRENT_STATUS.md`.

## 12. Required reporting

Every substantive result report must include:

1. Exact local branch/commit.
2. Exact code/package revision and relevant hashes.
3. Remote source/run/log paths.
4. Expected versus actual task count.
5. Raw-result inventory and corruption checks.
6. Runtime errors.
7. Statistics/reporting errors.
8. Design flaws.
9. Real control/restart conclusions.
10. What is frozen and what is not validated.
11. Next action and why it serves the final task.
12. Commands actually run and their outcomes.
13. Honest statement of anything not run.

## 13. Final task and roadmap

The final task is not to obtain a favorable verdict for one stage.

Build a causal, safe, robust feedback controller that can:

- start from different initial states;
- handle hidden vessel/eddy-current histories;
- track different R/Z/Ip targets;
- handle continuously varying actuator delay/gain/slew;
- tolerate plant/Jacobian/model error;
- handle measurement noise;
- arrive within the immutable timing contract;
- decelerate;
- recover from disturbances;
- hold stably for the required operating horizon.

Roadmap:

```text
reliable MPC expert
→ authentic plant restart
→ controller-state restart
→ hidden-history and different-initial-state robustness
→ new preregistered targets
→ plant/Jacobian and continuous actuator variation
→ noisy sensing/observer
→ disturbance recovery and independent long hold
→ MPC expert dataset
→ Behavior Cloning
→ DAgger
→ bounded residual RL
```

RL is only a bounded residual corrector. It must not regain unconstrained control of all 14 coils.
