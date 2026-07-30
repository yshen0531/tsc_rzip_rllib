# Run ledger

## Stage4.2R1 authentic plant restart action replay

- Local baseline branch/commit:
  `codex/stage4_2r1-forensics` / `d7be328`
- Controller revision:
  `true_tsc_plant_restart_action_replay_v42r1`
- Package revision:
  `r42r1a_capture_failure_finite_summary_v2`
- Source run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_1r17_runs/stage4_1r17_original_deadline_one_sided_robust_braking_closure_20260729_142501`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619`
- Initial log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619.log`
- R1a resume log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_234105.log`
- Fresh/resume:
  initial fresh run followed by R1a summary-hotfix resume
- Expected/actual:
  source 18/18; capture raw 18/18 but success 0/18; snapshots 0/18;
  restart `not_run` (0/18)
- Result:
  runtime failure before environment reset/TSC/snapshot request; no scientific
  plant-restart result
- Known bugs:
  lazy runner read before initialization; missing snapshot path counted as
  `"."`; unrun restart/formal status serialized as false; Windows inventory
  canonical path separator mismatch
- Download location:
  `stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619`
- Evidence:
  `artifacts/codex_audits/stage4_2r1_inventory.json`
- Next:
  minimum lifecycle/reporting hotfix, full validation, direct deployment, and
  safe resume of the same run

### R1b hotfix checkpoint

- Package revision:
  `r42r1b_lazy_runner_capture_resume_v3`
- Controller/experiment semantics:
  unchanged; isolated resume simulation matched all 18 experiment IDs
- Local validation:
  compile passed; 427/427 full tests passed; 23/23 focused tests passed;
  1133 JSON and 10703 JSON.GZ parsed strictly; 105 checksums passed;
  empty-directory import/self-test/focused tests passed
- Server status:
  the `tsc-airgap` alias remains unresolved, but the user explicitly
  authorized the existing identity file for this endpoint. The task-scoped
  read-only preflight connected successfully and confirmed the old R1a
  package, 42-file run tree, 18/18 parseable failed captures, 0/18 snapshots,
  0/18 restart raws, and no active Stage4.2R1 process. Server remains
  untouched pending R1b deployment.

### R1b server resume result

- Local deployment checkpoint:
  `0c87297`; task-scoped access documentation checkpoint `a04aae1`
- Server validation:
  staging and installed package checksums/import/compile/`bash -n` passed;
  installed complete unit discovery passed 427/427
- Resume:
  PID `1203573`, Ray capacity 128 CPUs, 18 capture actors
- Log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260730_061527.log`
- Real TSC:
  18 concurrent `gotsc` capture processes observed; capture completed 18/18
- Final capture:
  raw 18/18, parse 18/18, success 0/18; all failed at terminal
  `action_replay` telemetry because normal truncation cleanup cleared
  `runner.current_folder` before `_read_wire_currents_a`
- Preserved evidence:
  18 authentic 1300 ms snapshot case directories, 144 files total; required
  files complete 18/18; checkpoint coil match 18/18 at `1e-12`; 48-wire exact
  18/18; snapshot manifests 0/18
- Prefix fidelity:
  visible prefix exact 18/18; recorded action prefix exact 18/18
- Restart/formal:
  restart raw 0/18, restart `not_run`, formal preservation `not_run`
- Download:
  186 files, 2,134,305,226 bytes; remote/local SHA-256 mismatch 0
- Classification:
  runtime/instrumentation error, not control failure and not authentic
  plant-restart failure

### R1c terminal telemetry checkpoint

- Local commit:
  `4ff8a1d`
- Package revision:
  `r42r1c_terminal_wire_telemetry_resume_v4`
- Controller/experiment semantics:
  unchanged
- Fix:
  after normal terminal cleanup, full-wire telemetry reads the authentic
  output folder retained in `env.last_state["folder"]`
- Local validation:
  compile passed; 428/428 complete tests; 24/24 focused tests;
  1186 JSON and 10721 JSON.GZ parsed strictly; 105 checksums;
  41-module import closure; actual R1b resume matched experiment IDs 18/18
  and pending captures 18/18; empty-directory 106-file simulation passed
- Next:
  direct R1c deployment, server validation, same-run resume, complete
  uncompressed download, and raw/snapshot/restart re-audit
