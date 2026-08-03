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

Stage4.2R3c3T11 then completed its exact preregistered persistent-step
identification campaign:

```text
authentic restart rollouts                 416/416
execution / restart / causality            416/416
central symmetry                           192/192
matched hidden-history response              96/96
response rank 6                              32/32
response condition <= 25                     25/32
maximum response condition               38.9150751
maximum current utilization                  0.3904
```

Independent server-side raw/snapshot/manifest postprocessing reproduced the
reported result exactly. Independent raw R/Z differencing and SVD reproduced
all 32 condition values to `4.97e-14`. T11 is frozen as a clean
identification-design FAIL due to seven context-dependent weak or
near-collinear response matrices. It is not a runtime, restart, corruption,
reporting, or real MPC failure. Formal tracking was diagnostic only: 207/416
overall and exactly 16/32 unprobed baselines.

The 500 ms T11 observation horizon does not change the 250/270 ms arrival
deadlines or the 350/370 ms formal hold endpoints and is not a long-hold
success test. T11 probe trajectories are forbidden from expert datasets;
its matched-history response gate does not independently validate
hidden-history closed-loop robustness.

Post-T11 read-only server forensics found that response conditioning and
formal control are largely different axes:

```text
baseline formal PASS / condition PASS                  12
baseline formal PASS / condition FAIL                   4
baseline formal FAIL / condition PASS                  13
baseline formal FAIL / condition FAIL                   3
failed baselines repaired by any real T11 single probe  0/16
best per-context measured margin gain          0.00117--0.00807
```

Stage4.2R3c3T12 then authenticated all 416 immutable T11 raw files in place
and reproduced the cross table and measured-corner formal-gap coverage. It
ran no Ray, `gotsc`, TSC, controller, optimizer, plant step, or snapshot
creation. T12 found 0/16 failed baselines repaired by any actual single
probe, with best gap coverage only 0.47%--11.46%. It froze the fixed
condition-first response-basis route as vetoed without changing T11's FAIL or
claiming global plant unreachability.

Stage4.2R3c3T13 completed its no-new-TSC finite-horizon restart MPC
architecture and evidence map. Its V4 read-only audit authenticated 1,408
existing raw trajectories. All 1,504 causality/effect-state gates passed, but
the fixed Stage3.4 lifted Jacobian passed the relative prediction gate
0/1,504. This is a prediction-model/design gap, not runtime, restart, raw,
reporting, global reachability, or real closed-loop evidence. T13 ends as
`MINIMAL_SENTINEL_REQUIRED`.

Stage4.2R3c3T13S1 completed its one authorized 52-rollout campaign with
exact package, restart, causality, execution, raw, snapshot, rank, condition,
current, and report integrity. Its frozen scientific gates failed: central
symmetry was 0/24 and matched hidden-history response was 0/12. The official
route is `SENTINEL_FAIL_STOP_IDENTIFICATION`. Read-only immutable-raw
forensics separated the failure layers: requested command symmetry was
24/24, observed first-effect current symmetry 0/24, immediate plant symmetry
3/24, full-window plant symmetry 0/24, immediate matched history 6/12, and
full-window matched history 0/12. Of 336 active compared coil-command
components, 304 were smaller than one source-defined Card15 `.3E` grid.

T13S1 is a clean identification/model/action-resolution design FAIL, not a
runtime, restart, corruption, reporting, real-MPC, or global-reachability
result. It may not be rerun or enlarged under the same identity and its probe
trajectories are forbidden from expert data.

Stage4.2R3c3T13S2 completed its zero-new-TSC audit of all 2,600 transitions
and 36,400 coil components. Exact Card15 target reconstruction matched only
13,000 components at `1e-9 A`; the maximum target-to-TSC-readback difference
was `1.0000000003174137e-5 A`, so its exact frozen route is
`ACTUATOR_MAPPING_IMPLEMENTATION_GAP`. It found eight exact causal-feature
collision groups but zero groups with both the same feature and the same
applied current path, hence zero exact observational aliases. All 24 matched
histories were finitely separable by allowed clean causal features, which is
not observer or hidden-history robustness.

The separately frozen read-only T13S2R1 forensic identified a per-coil fixed
development readback bias from only four baselines and reproduced all 33,600
signed-probe components within `1e-9 A`. The TSC-order bias units are
`[2,2,2,2,2,2,2,1,0,0,0,1,0,0] * 1e-6 kA-turn`. This is a retrospective
development-set structure result, not an independent holdout. T13S1 remains
FAIL and T13S2 remains an exact-reconstruction FAIL.

Stage4.2R3c3T13S3 implemented the exact Card15 actuator boundary, traced
development bias plus nonzero per-coil interval, unknown-velocity causal
restart state, forbidden-field rejection, and fail-closed multi-hypothesis
transition tube at commit `37e3913`. Local isolated tests passed 15/15 and
the installed server suite passed 654/654 with one expected skip. T13S3 ran
zero TSC/plant steps and ends as `INTERFACE_COMPLETE_HOLDOUT_REQUIRED`; it
does not certify a point plant model, observer, robust controller, or MPC.

Stage4.2R3c3T13S4 then failed its prospective actuator/input gate before any
real TSC trajectory. Only 11/52 specifications were offline-complete; 40
violated the frozen incremental-action limit and one exact inverse was not
representable. It is frozen as `LATTICE_PREFLIGHT_FAIL_NO_REAL_TSC`, an
identification-design failure rather than a runtime, plant, or MPC result.

Stage4.2R3c3T13S5 subsequently completed 68/68 authentic q2 restart probe
trajectories with exact restart, causality, package, raw, snapshot, current,
and final-report integrity. The final route is
`LATTICE_HOLDOUT_FAIL_REDESIGN`: only 2/4 preregistered development cells had
rank four, only 3/4 had a non-vacuous tube, and the consumed independent
history validation passed relative error 0/32. Source and raw forensics found
that the lattice wrapper replaced the final Card15 action after the inherited
software delay queue, so the physical effect appeared at `issue_step + 1`
rather than `issue_step + delay + 1`. This effect-state design error does not
explain the delay-zero validation failure, which independently rejects the
single static cross-history map. T13S5 is not a runtime, restart, corruption,
real-MPC, or global-reachability failure.

Stage4.2R3c3T13S6 then authenticated and independently recomputed all 68
immutable T13S5 raw trajectories at `issue_step + 1` and `cancel_step + 1`.
The corrected timing restored development signal/rank/condition/tube to
16/16 and 4/4, but the already-consumed validation passed containment only
14/32 and relative error only 2/32, with maximum scaled error 1.0973948. The
final route is `IMMEDIATE_EFFECT_LOCAL_MAP_INSUFFICIENT_REDESIGN`. This is a
cross-history model-design failure, not a runtime, raw, restart, reporting,
real-MPC, or global-reachability result.

Stage4.2R3c3T13S7 authenticated all 120 S1/S5 raw files, but its frozen audit
applied S5's post-queue `issue+1` effect rule to S1. S1 source inserts its
probe before the inherited delay queue and all 24 raw odd-current groups
match `issue+delay+1`; all 32 S5 groups match `issue+1`. Consequently S1
hard maps were rank zero and 24 apparent zero-error validations were
vacuous, while 88/112 held-out rows were unsupported. T13S7 remains final as
`CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN`, classified primarily
as an audit-design/effect-contract failure rather than a valid
multi-hypothesis scientific test.

Stage4.2R3c3T13S7R1 then applied the authenticated campaign-specific effect
states and completed the zero-new-TSC audit. Local rank and tube gates
recovered to 16/16, but the frozen feature selector found supported input
hypotheses for 0/112 held-out rows. A post-result forensic found only 16/112
rows supported by any same-stratum training map, all in the S5 hard
transport pair; cross-campaign support was 0/112. The final route is
`CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN`.
This is an excitation-coordinate/support design failure, not a runtime,
restart, raw, real-controller, or plant result.

Stage4.2R3c3T13S8 then removed the adjacent cancellation transition and
audited only the first physical effect. Local rank/tube remained 16/16 and
support improved to 64/112, but containment was 29/112 and relative error
39/112. All 48 S1 pre-queue rows were unsupported; all 64 S5 post-queue rows
were supported, yet their cross-history accuracy still failed. T13S8 is
final as `FIRST_EFFECT_CAUSAL_TRANSITION_INSUFFICIENT_REDESIGN`.

T13S9 completed 68/68 authentic q1 identification trajectories through the
same post-queue Card15 coordinate as T13S5 q2. Raw, snapshot, restart,
causality, runtime, current, statistics, and reporting integrity passed.
All four development maps passed rank, condition, and non-vacuous tube
gates, but the consumed internal q1 history diagnostic passed containment
only 15/32 and relative error only 20/32. T13S9 is final as
`UNIFIED_POSTQUEUE_Q1_IDENTIFICATION_COMPLETE_COMBINE_Q2_REQUIRED`; it is an
identification completion result, not a controller or MPC pass.

T13S10 then authenticated all 136 T13S5/T13S9 raw files and completed its
zero-new-TSC combined audit. Input support, local signal, rank, condition,
and tube gates passed exactly, but containment passed only 107/128 and
relative error only 110/128; only 92/128 rows passed both. Its final route is
`UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_INSUFFICIENT_OBSERVER_REDESIGN`. This
is a finite causal transition-model design failure, not a runtime, raw,
restart, causality, reporting, controller, or real-MPC failure.

T13S11 then completed its zero-new-TSC calibration-conditioned preflight. A
numerical affine-rank reporting bug was repaired without changing any model
or prediction. Final calibration/causality/support/rank/tube gates passed,
but all eight unwhitened interaction conditions exceeded 23,000 and only
36/64 rows passed both response gates even if the condition gate is ignored.
Its final route is `CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_INSUFFICIENT_PERSISTENT_OBSERVER_REDESIGN`.

T13S12 then authenticated all 136 q1/q2 raw files and completed its
zero-new-TSC natural-history observer preflight. Every history/current
support, rank, whitening, condition, signal, tube, causality, and forbidden-
input gate passed; the maximum interaction condition was effectively one.
Response accuracy nevertheless passed only 44/64 and both frozen response
gates only 41/64, with maximum scaled error 1.701539079. Its final route is
`CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_INSUFFICIENT_NONLINEAR_OBSERVER_REDESIGN`.
This is a finite affine observer/model design failure, not a runtime, raw,
restart, reporting, controller, or real-MPC failure.

T13S13 completed 24/24 new training baselines and 384/384 new probes with
exact execution, restart, causality, Card15, current, raw, and reporting
integrity. Its frozen recurrent center nevertheless passed only 301/512
training response rows, so it stopped before calibration/holdout as
`RECURRENT_CAUSAL_SEQUENCE_TUBE_INSUFFICIENT_REDESIGN`. No model, tube,
controller, or MPC was certified.

T13S14 completed all 144 authentic trajectories with exact raw, restart,
causality, Card15, zero-net, current, and reporting integrity. Its best ESN
passed only 36/128 center rows and no kernel was eligible. The final route is
`ACTIVE_CALIBRATION_SENTINEL_FAIL_REDESIGN`; this is an observer and
experimental-design failure, not a runtime, restart, reporting, controller,
MPC, or plant-unreachability result.

T13S15 failed its frozen basis-condition gate before any plant advance.
T13S16 repaired the basis geometry and completed 144/144 authentic
trajectories, but its provisional local residual tube failed. T13S17's
causal multi-drift tube retained 128/128 containment but exceeded the frozen
caps. T13S18 then passed its zero-new-TSC whole-pair pooled observer preflight
128/128 and authorized a prospective fresh campaign only.

T13S19 produced 24 training-baseline raw files, with 23 complete successes
and one deterministic controller exception before its third plant advance.
Forensics proved that a frozen `-0.016` kAt calibration increment crossed a
Card15 decimal exponent boundary and could not be represented exactly at the
new causal center. This is an excitation-design defect plus a partial-failure
reporting defect, not a TSC, restart, causality, raw, observer, control, or
plant failure. S19 is frozen and cannot resume under changed action semantics;
training probes, calibration, and holdout were not run.

T13S20 then passed its offline gate and produced 24/24 training-baseline raw
files. Twenty-three completed with exact restart, causality, actuator, dynamic
design, and zero-net checks. One stopped before its eighth plant advance when
independently nearest dynamic Card15 quantization left a `0.0004 kA-turn`
coil-8 residual. All 24 raw parse, 40/40 snapshots authenticate, and 184/184
successful-context probe paths replay without a plant advance. A separate
zero-plant forensic proved that the exact cumulative inverse is representable
and passes every unchanged action/geometry gate for the failed path.

S20 is frozen as an excitation-sequence design FAIL, not a runtime, restart,
raw, plant-control, or observer result. Its terminal `phase_status` is also a
stale reporting field even though `finished`, stop reason, and verdict are
correct. Because cumulative closure changes the controller source and failed-
path physical action, S20 cannot resume.

T13S21 completed the separately preregistered 360-rollout cumulative-exact
Card15 campaign. All raw, restart, causality, actuator, exact-net, training-
model, calibrated-tube, fresh-holdout, and independent server-recomputation
gates passed. The final raw inventory is 360 files, 21,083,271 bytes, digest
`8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4`.
Fresh holdout passed 64/64 with maximum scaled point error `0.0108949379`.

This is a finite local response-set model PASS only. Formal diagnostics were
16/40 for baselines and 99/320 for signed probes; none of the eight measured
state-10 directions repaired any of the 24 failing contexts. It is not a real
MPC or formal control PASS.

T13S22 then authenticated all 360 S21 raw, reproduced all 360 formal
diagnostics, completed 40/40 bounded optimizations and independent forward
checks, but passed optimistic affine feasibility only 16/40. These were
exactly the 16 unchanged baseline passes: the frozen state-10 affine family
repaired 0/24 failures and regressed 0/16 passes. All 24 failures were limited
by sustained position error; four also failed post-arrival speed, while Ip
was not limiting. S22 is final as
`AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED`. It ran zero TSC,
plant steps, snapshots, or controllers, so this is a model-class/authority
failure, not a real closed-loop or plant-reachability conclusion.

S23R1 later passed its static amplitude-coded schedule preflight, but S24's
real sequential campaign safely stopped 54 trajectories at a 0.50-amplitude
cancellation. D1's fixed contraction failed static geometry; D1R1 restored
that geometry with the exact amplitude map:

```text
+++ 0.250 / +-+- 0.250 / ++-- 0.290 / +--+ 0.360
```

D1R2 then executed the prospectively frozen 54-case real-TSC safety sentinel.
All 54 raw files strictly parse and all restart, causality, calibration,
Card15, current, and forbidden-input prefix checks pass. Forty-five reached
full horizon. Nine stopped safely before applying the task-step-18 slot-3
`++--=0.290` cancellation: four exceeded only the 0.24 prospective margin and
five also exceeded the original 0.25 cap. The maximum attempted increment was
0.2787208138. A reporting-only audit corrected success-only top aggregates to
216/216 issues, 207 successful cancellations, and nine failed attempts; the
FAIL route did not change.

D1R2 is frozen as a real sequential cancellation-design failure, not a
runtime, restart, raw, reporting-route, controller, or plant-unreachability
result. It may not resume, and its raw is forbidden from model fitting and
expert data. The active task is a separately frozen zero-new-TSC causal
two-step exact-return cancellation preflight. A pass may authorize only a
fresh real-TSC sentinel over the nine failed contexts. The full replacement
campaign, transition MPC, expert data, BC, DAgger, and residual RL remain
blocked.

Stage4.2R3c3T13S24D1R3 then authenticated all 54 immutable D1R2 raw files
and completed two byte-identical causal controller replays with zero new TSC
or plant advance. All 54 source action and trace prefixes reproduced exactly;
45 complete paths remained direct and all nine structured-stop prefixes
produced the frozen exact Card15 split start at exactly 0.175 incremental
normalized action. Independent server-side raw/output forensics passed.

D1R3 is only a split-start construction PASS. It cannot validate the
state-19 finish because it advances no plant. The active stage is a separately
preregistered new-identity D1R4 nine-case authentic real-TSC sentinel. A D1R4
pass may authorize only a new full replacement transition-identification
campaign; MPC, expert data, BC, DAgger, and residual RL remain blocked.

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
