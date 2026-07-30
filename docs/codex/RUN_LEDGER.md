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

### R1c final server result

- Local code checkpoint:
  `4ff8a1d`
- Package/controller:
  `r42r1c_terminal_wire_telemetry_resume_v4` /
  `true_tsc_plant_restart_action_replay_v42r1`
- Server validation:
  staging and installed checksum/import/compile/`bash -n` passed; installed
  complete unit discovery 428/428
- Resume:
  PID `1217510`, Ray capacity 128, same run and experiment identity
- Log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r1_true_tsc_plant_restart_action_replay_20260730_070023.log`
- Real TSC:
  18 concurrent `gotsc` capture processes and 18 concurrent fresh-restart
  `gotsc` processes observed
- Final counts:
  capture 18/18 success; restart 18/18 success; snapshot cases 18/18;
  snapshot payloads 144 plus 18 manifests
- Integrity:
  261 files, 2,134,623,716 bytes; remote/local SHA-256 missing 0, extra 0,
  mismatch 0; strict run JSON/JSON.GZ 114/114
- Independent result:
  source/capture/action/snapshot/restart/recombined equality 18/18; 14-coil
  maximum difference 0 A after kA-turn conversion; 48-wire maximum difference
  0 A; fixed formal gate 18/18
- Minimum formal margin:
  `1.04569209997685e-05`, `RZ_p10_m10`, delay 0, slew 0.9, 270 ms
- Classification:
  authentic finite same-source plant restart success; no controller-state
  restart claim
- Next:
  Stage4.2R2 persistent controller checkpoint with online action
  recomputation; no BC/DAgger/RL

## Stage4.2R2 persistent controller checkpoint replay

- Local code branch/commit:
  `codex/stage4_2r2-controller-checkpoint` / `84962ef`
- Controller revision:
  `persistent_mpc_controller_checkpoint_replay_v42r2`
- Package revision:
  `r42r2_persistent_controller_checkpoint_v1`
- Relevant hashes:
  controller module
  `8dffdc6f6a9b851577e3a4bc98102893d8abbb418be6381d14fc54d611bf711c`;
  `PACKAGE_MANIFEST.json`
  `3479504de287e919a644d5215e9237e9ee7dd74809455c0cc236b3651f399337`;
  `SHA256SUMS`
  `bc8ae857da2ec962e78ac376ce849525171998f51cd90d32ac2c9f63bc65e1f6`
- R17 source:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_1r17_runs/stage4_1r17_original_deadline_one_sided_robust_braking_closure_20260729_142501`
- R1c plant/snapshot source:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r1_runs/stage4_2r1_true_tsc_plant_restart_action_replay_20260729_162619`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r2_runs/stage4_2r2_persistent_controller_checkpoint_replay_20260730_082250`
- Remote log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r2_persistent_controller_checkpoint_replay_20260730_082828.log`
- Fresh/resume:
  one run directory; offline gate first, then the same resumable run continued
  into a fresh real-TSC replay phase after a reporting-only state hotfix
- Expected/actual:
  checkpoints 18/18; offline causal recomputation cases 18/18 and 282 suffix
  actions; real fresh-TSC rollouts 18/18; raw JSON.GZ 18/18
- Real TSC:
  Ray capacity 128; 18 concurrent `gotsc` restart processes observed
- Result:
  online action, visible suffix, and full-wire suffix exact 18/18; fixed
  formal contract 18/18; minimum signed margin
  `1.0456920999768471e-05` at `RZ_p10_m10`, delay 0, slew 0.9
- Independent server audit:
  50 R2 input files / 604,967 bytes / strict JSON 30 and JSON.GZ 18; source
  snapshot manifests 18 and payloads 144 / 2,133,646,442 bytes; corruption,
  reporting, checkpoint/design, plant-fidelity, and formal-control failure
  counts all 0
- Known repaired tooling/reporting bugs:
  Windows remote-shell quoting during clean install; verifier included runtime
  bytecode; offline-only phase was incorrectly marked finished/failed; first
  audit-tool launch lacked project `PYTHONPATH`; SFTP mishandled the Unicode
  local path and aggregate SCP later timed out after 18/19 compact files
- Download:
  no large raw/snapshot download; compact local evidence at
  `artifacts/server_audits/stage4_2r2_20260730_082250`, 19 files and 185,302
  bytes
- Evidence:
  `docs/codex/reports/STAGE4_2R2_FORENSIC_REPORT.md`;
  `docs/codex/audits/stage4_2r2_20260730_082250/`
- Load-bearing audit hashes:
  forensic audit
  `ae188ed87d70040b1f20cd7857febaaa7749e3922647ca3d0c7c85e2b2066674`;
  case rows JSON
  `ce8c6aa9954bb995d29125d5eb2e023681d08cfefe0e2a84b7a6f9f0a07d7d85`;
  input inventory
  `9bd9f8d3d6be3a1a76dbee601edb2b25292e72315abd81a7685bcf51376fc2f0`
- Frozen claim:
  exact causal persistent-controller restart only for the finite clean
  same-source grid
- Next:
  Stage4.2R3 matched-visible/different-hidden-history pair construction and
  different-initial-state testing; no BC/DAgger/RL

## Stage4.2R3 authentic hidden-history state generation

- Local implementation:
  `codex/stage4_2r3-hidden-history` / `9d752d2`; offline CLI fix `5748f83`
- Package/controller:
  `r42r3_authentic_hidden_history_initial_state_v1` /
  `authentic_hidden_history_initial_state_mpc_v42r3`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3_runs/stage4_2r3_authentic_hidden_history_initial_state_20260730_100915`
- Remote log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3_authentic_hidden_history_initial_state_20260730_101040.log`
- Expected/actual:
  state rollouts 54/54; snapshots 54/54; pairs 27/27; control 0 because
  the state gate failed
- Result:
  visible match 27/27; hidden separation 0/27; maximum hidden difference
  0.048 A versus frozen 1,000 A; control `not_run`
- Classification:
  state-generation design/threshold failure; no runtime, corruption,
  plant-restart, or real control conclusion
- Evidence:
  `docs/codex/reports/STAGE4_2R3_FORENSIC_REPORT.md`;
  `docs/codex/audits/stage4_2r3_result_20260730_100915/`
- Next:
  new R3a delayed-counterpulse state-generation identity

## Stage4.2R3a delayed-counterpulse hidden-history state generation

- Local implementation:
  `codex/stage4_2r3a-delayed-history` /
  `8a3eb670e9db210594f21260c2391cea0a32a255`
- Package/controller:
  `r42r3a_delayed_counterpulse_hidden_history_v1` /
  `delayed_counterpulse_hidden_history_initial_state_mpc_v42r3a`
- Package hashes:
  `PACKAGE_MANIFEST.json`
  `e9a5eb5582b8d0de3570d60d216bdd70b657f097d22b543f4f7db9cd4649088c`;
  `SHA256SUMS`
  `f9454a40316755ae419b4f1efe4cdc28de77dafff47b2c61340398bfed34080a`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3a_runs/stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_20260730_110128`
- Remote log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_20260730_110200.log`
- Fresh/resume:
  offline no-gotsc gate first, then safe same-identity resume for real TSC
- Expected/actual:
  state rollouts 72/72; snapshots 72/72; pairs 36/36; control 0 because
  the frozen state gate failed
- Independent result:
  visible match 24/36; different initial state 36/36; hidden separation
  under frozen 1.0 A gate 0/36; observed maximum 0.527 A; control `not_run`
- Integrity:
  739 files / 8,535,699,130 bytes / run digest
  `9be432ee725035b31cee32f9415298aacd1fa576e24190588b8ef2c2be08eae7`;
  runtime and corruption errors 0
- Download:
  no large raw/snapshot download; compact evidence 25 files / 971,284 bytes
  at `docs/codex/audits/stage4_2r3a_result_20260730_110128/`
- Classification:
  experimental-design/threshold-calibration failure; no unit-conversion,
  runtime, deployment, reporting, plant-restart, or real control failure
- Evidence:
  `docs/codex/reports/STAGE4_2R3A_FORENSIC_REPORT.md`
- Next:
  new R3b confirmation grid with prospective material hidden-state gate;
  no retroactive R3a reinterpretation and no BC/DAgger/RL

## Stage4.2R3b confirmatory hidden-history and different-initial-state control

- Local implementation:
  `codex/stage4_2r3b-confirmatory-history` / `8fb1534`
- Package/controller:
  `r42r3b_confirmatory_hidden_history_v1` /
  `confirmatory_hidden_history_initial_state_mpc_v42r3b`
- Package hashes:
  `PACKAGE_MANIFEST.json`
  `2fcd4e5a5e9d9d69512e56dcb4b614ed93e5496c72887df3d29befc0adbb5c37`;
  `SHA256SUMS`
  `fb8b008fc8baac8bb5606fe7376b9520087eac9efe18c97c7b8e5025c82ad194`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526`
- Fresh/resume:
  offline no-gotsc gate first, then safe same-identity resume for real TSC
- Expected/actual:
  state 72/72; snapshots 72/72; candidate pairs 36/36; selected pairs 4/4;
  fresh control 32/32
- State result:
  visible match 16/36; hidden separation 34/36; accepted 14/36; exact
  prefix-by-direction selection 4/4; different-initial-state and prefix
  separation gates passed
- Control integrity:
  environment, fresh-controller, fresh-TSC, exact visible/full-wire restart,
  and causal trace 32/32; future action/measurement and hidden-wire input 0
- Real control:
  immutable formal contract 0/32; position and speed fail 32/32; formal
  signed margins `-6.447296` to `-3.960849033333333`
- Independent diagnosis:
  restart states nearest R17 phases 12--20 but controller nominal phase reset
  to 0; first actions remain within 0--0.0163 of phase-zero source actions and
  differ by 0.9019--1.4371 from nearest-phase actions; original-start R17
  source remains 32/32 PASS
- Integrity:
  874 files / 8,538,932,691 bytes / run digest
  `301a3ad2be01c83209d8e260c1a8c80f090d01afafb9c173f63cf9219caac8fc`;
  runtime, corruption, plant-restart, and causality failure counts all 0
- Reporting issue:
  saved `observer_or_history_identification_failure_count=0` is inconclusive,
  not observer success, because both members fail all 16 groups under a
  common-mode controller failure
- Download:
  large raw/snapshots remain server-side; compact evidence at
  `docs/codex/audits/stage4_2r3b_result_20260730_115526/`
- Evidence:
  `docs/codex/reports/STAGE4_2R3B_FORENSIC_REPORT.md`
- Load-bearing audit hashes:
  server audit
  `f1e907888e19846d07099714d4b581e26aac80c5675a373364d396db78130831`;
  raw control forensics
  `975205eff41f62d319e4f6e22643bb687461e42d3c73c1d09f0424f2a7c5cf32`;
  run inventory document
  `f4e9c9d91f5d9439769adca9176431243ebf8d5a430a29cb54a5b15d2b5d6407`
- Classification:
  real finite-envelope control/design failure; authentic state generation
  and plant restart passed; hidden-history robustness remains unvalidated
- Next:
  R3c visible-state phase-aligned MPC development on the locked R3b
  snapshots, followed by independent R3d new-history confirmation before new
  targets; no BC/DAgger/RL
