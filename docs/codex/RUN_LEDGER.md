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

## Stage4.2R3c visible-state phase-aligned MPC development

- Local implementation:
  `codex/stage4_2r3c-phase-aligned-mpc` / `e8856f8`; authenticated-source
  contract hotfix `a5513e9`
- Package/controller:
  `r42r3c_visible_state_phase_aligned_mpc_v1` /
  `visible_state_phase_aligned_mpc_v42r3c`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c_runs/stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807`
- Expected/actual:
  offline original-start preservation 4/4; real TSC 32/32; exact plant
  restart and causal phase trace 32/32
- Real control:
  20/32 formal PASS; prefix 9 passed 16/16 and prefix 5 passed 4/16;
  12 genuine formal failures
- Diagnosis:
  selected ideal-reference phases 11--13 versus nearest actual R17 visible
  phases 12--20; phase-zero mismatch was repaired but ideal-reference phase
  underestimated the physical closed-loop phase
- Integrity:
  143 files / 2,963,470 bytes / digest
  `278395b364bb355c73b5f6de7461478b4bb239584a3f6bf9bf048aad12be9d13`;
  runtime, corruption, restart, and causality errors 0
- Evidence:
  `docs/codex/reports/STAGE4_2R3C_FORENSIC_REPORT.md`;
  `docs/codex/audits/stage4_2r3c_result_20260730_132807/`
- Independent raw forensics:
  `395427285a5bad0de9611629df0a13ade037ddd4f0e30e993e475a56c3dbafaa`
- Classification:
  failed controller development result; hidden-history robustness
  inconclusive because six pair groups failed both members
- Next:
  R3c1 authenticated actual R17 visible-manifold phase MPC; no
  BC/DAgger/RL

## Stage4.2R3c1 authenticated visible-manifold phase MPC

- Local implementation:
  `codex/stage4_2r3c1-visible-manifold` / `be3065b`
- Runtime/reporting hotfixes:
  `35e725c` first-sample causal zero-velocity resume;
  `0898b28` reporting-only package-chain audit
- Package/controller:
  `r42r3c1_authenticated_visible_manifold_phase_mpc_v1` /
  `authenticated_visible_manifold_phase_mpc_v42r3c1`
- Runtime package digest:
  `c78beb6649543512d3d54649c3001b1c870256929470f09fccaf082b7e087a99`
- Audit package digest:
  `61f31875d9ecbef70ecf46b6acbf1600cd877c66345db8cd7ce07bbb6e9f038a`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c1_runs/stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_143218`
- Fresh/resume:
  offline gate; initial 32-task real run; semantics-preserving resume of
  exactly four phase-20 first-sample runtime failures
- Initial incident:
  28 successful trajectories and four
  `terminal feedback requires at least two trajectory states` failures;
  complete evidence preserved under
  `stage4_2r3c1_runtime_bug_evidence/pre_hotfix_20260730_145053`
- Resume integrity:
  exact 28 prior-success raw hashes unchanged; only the four preserved
  runtime-failure experiment IDs changed; final raw/environment success
  32/32
- Final control:
  exact plant restart 32/32; causal/valid phase trace 32/32; formal PASS
  16/32; real formal failures 16
- R3c comparison:
  pass→pass 16, fail→fail 12, pass→fail 4, fail→pass 0
- Diagnosis:
  static R17 R/Z/Ip nearest-phase alignment is insufficient dynamic
  controller-state initialization; all 16 failures have unavoidable
  position violations, and four also have final/post-speed violations
- Integrity:
  166 files / 3,409,736 bytes / digest
  `5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f`;
  final runtime, corruption, restart, and causality errors 0
- Load-bearing hashes:
  server audit
  `0d81cbe3e0d9b67d72cf093143edd8a825a3b60ea5e3c449cf29de7cf0cc7712`;
  independent raw forensics
  `29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd`;
  pre-hotfix manifest
  `30303cc7a907a4ff2cd4c7680f3164990db39ac0495a6b978b9f4cac38a69cc9`
- No-TSC next-design diagnostic:
  `9a278b5e97416ae2d98d05b4cff7ad2328ddd0a1ec8f3d14ded0421b184c124d`;
  32/32 finite causal restart-regulation first actions, 4/4 phase-zero
  original-source preservation, no plant advance
- Download:
  final large raw/snapshots remain server-side; compact evidence at
  `docs/codex/audits/stage4_2r3c1_result_20260730_143218/`
- Evidence:
  `docs/codex/reports/STAGE4_2R3C1_FORENSIC_REPORT.md`
- Classification:
  final 16/32 is a true controller-design/closed-loop failure; repaired
  runtime, deployment-permission, and reporting incidents are separate;
  hidden-history robustness remains inconclusive
- Next:
  new Stage4.2R3c2 identity with phase-zero preservation and immediate causal
  target-state regulation for nonzero visible restart phases; no
  BC/DAgger/RL

## Stage4.2R3c2 restart target-state regulation MPC

- Local implementation:
  `codex/stage4_2r3c2-restart-regulation` / `c4b9143`
- Package/controller:
  `r42r3c2_restart_target_state_regulation_mpc_v1` /
  `restart_target_state_regulation_mpc_v42r3c2`
- Runtime/audit package digest:
  `b35ef6df933d3e268705584834b1ffff5b7b6172fb882d82f4c338b75e06f1cd`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c2_runs/stage4_2r3c2_restart_target_state_regulation_mpc_20260730_164616`
- Offline gate:
  original-source phase-zero/full-action exact 4/4; 32/32 finite causal
  restart-regulation first actions; hidden-wire invariant 32/32; no raw or
  real TSC
- Real execution:
  exactly 32/32 environment-success raw; fresh controller/TSC, exact restart,
  causal phase/model/regulator trace all 32/32; no resume or rerun
- Final control:
  formal PASS 12/32; real formal failures 20; minimum signed margin
  `-0.5203167999999989`
- Grouped outcome:
  prefix-5 0/16; prefix-9 12/16; nominal 8/16; offset 4/16; normal actuator
  8/16; weak actuator 4/16
- R3c1 comparison:
  pass→pass 12, fail→fail 16, pass→fail 4, fail→pass 0
- Diagnosis:
  zero-nominal terminal regulation discarded target-conditioned transport;
  representative prefix-5 normal-actuator maximum action fell from about
  0.55--0.92 under R3c1 to about 0.08; all 20 failures have unavoidable
  position violations
- Integrity:
  147 files / 3,287,591 bytes / run digest
  `2119d2edad615dbb9594ad4332b758a9cf7ffc2e62b988650c41297aace8cff2`;
  raw digest
  `b01a07c9dc136677f323d292d0f9388904cc39663514bf4025f4fa4fed767653`;
  runtime, corruption, restart, causality, solver, and saturation failures 0
- Deployment incident:
  one pre-run remote quoting/install command failed after deleting only named
  package code paths; exact validated staging was immediately restored and
  canonical package plus all 516 tests passed before TSC; no experiment data
  was touched
- Evidence:
  `docs/codex/reports/STAGE4_2R3C2_FORENSIC_REPORT.md`;
  `docs/codex/audits/stage4_2r3c2_result_20260730_164616/`
- Load-bearing hashes:
  server audit
  `87461800e5fd9ea6f228d49e36269eb80ffbb537720fcf804c69812ed2ddf7cf`;
  independent raw forensics
  `644da85280e03015732bb63deb1205bf5fcafeabc53b0f8a9e606565a27efbb2`;
  local compact inventory
  `35ac2b2731047a7e2d5e67e63d28b9eb108b649c31cb712af012a20fd3a2f0b1`
- Classification:
  recovered pre-run deployment-command error is separate; final result is a
  true controller-design/closed-loop failure; hidden-history robustness
  remains inconclusive
- Next:
  Stage4.2R3c3 identification-only bounded task-clock response probes on the
  R3c1 target-conditioned baseline; only a passed response/hidden-history
  gate may support R3c4 MPC; no BC/DAgger/RL

## Stage4.2R3c3 restart task-clock local-response identification

- Local runtime implementation:
  `codex/stage4_2r3c3-restart-response-id` / `8623bcf`
- Independent forensic tool:
  `83e78e4`
- Package/controller:
  `r42r3c3_restart_task_clock_local_response_identification_v1` /
  `restart_task_clock_local_response_probe_v42r3c3`
- Runtime/audit package digest:
  `1ba40b276a6a998e266e68d044c8ad3e819d86b6f7c8e52c7c60c6000a05a661`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3_runs/stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427`
- Offline gate:
  exact 256-case grid; 32/32 exact R3c1 baseline first actions and probe-first
  actions; hidden-wire invariant 32/32; no raw and no real TSC
- Real execution:
  exactly 256/256 environment-success/completed raw; fresh controller/TSC,
  exact plant restart, causal controller trace, four exact bounded zero-net
  probe issues, and no forbidden controller input in every trajectory
- Identification result:
  central symmetry 128/128; matched-hidden-history response 64/64;
  conditioned rank-4 matrices 32/32; maximum condition number `8.0984`;
  maximum current utilization `0.3904`
- Formal diagnostic:
  125/256 probe trajectories passed and 131/256 failed the unchanged formal
  contract; this was preregistered as non-acceptance diagnostic data
- Integrity:
  1048 files / 25,371,364 bytes / run digest
  `ef377ce1367d7a969b8f90cdb247445106f50b8706146f4c97b312892e909754`;
  256 raw files / 8,933,607 bytes / raw digest
  `88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563`
- Errors:
  final runtime, raw/snapshot, restart, causality, solver, identification,
  and statistics/reporting errors all 0; pre-run staging/test-command and
  monitoring/download incidents are separately recorded and did not affect
  the scientific run
- Evidence:
  `docs/codex/reports/STAGE4_2R3C3_FORENSIC_REPORT.md`;
  `docs/codex/audits/stage4_2r3c3_result_20260730_182427/`
- Load-bearing hashes:
  server audit
  `5172fc54a8446418bbcccd31c84515f62ad2594a52904b831a3b2064d52a44b4`;
  independent raw-response forensics
  `1a1d1acb2b6401a726a5e313301d9a37643cf023b4d2013a9f9c37e23f8a097b`;
  local compact inventory
  `ed2443a8e3ea5d9559517a815df33bbb706263a3559f902953fcc940898cc957`
- Classification:
  finite locked-development-bank local-response identification success;
  independent hidden-history control robustness and a reliable restart MPC
  remain unvalidated; probe trajectories are forbidden from expert datasets
- Next:
  freeze a compact authenticated R3c3 response bank and preregister a new
  Stage4.2R3c4 restart-integrated target-conditioned deadline MPC; no
  BC/DAgger/RL

## Stage4.2R3c4 pre-execution bounded-response feasibility

- Local branch/checkpoint:
  `codex/stage4_2r3c4-deadline-mpc` / `84483f6`
- Compact-bank builder:
  `fbcbb16`;
  `docs/codex/audit_tools/stage4_2r3c3_compact_response_bank.py`
- Source run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3_runs/stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427`
- Remote compact bank:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c4_response_bank`
- Response-bank coverage:
  R3c3 raw 256/256; exact R3c1 baselines 32/32; signed groups 128/128;
  matched-hidden-history groups 64/64; condition groups 32/32
- Bank hashes:
  audit bank
  `51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32`;
  controller bank
  `6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0`;
  manifest
  `a17322dcfc1d019de0455950c95e45b0b7d0f8f29fc3c68a22211481f261a066`
- Bank guard:
  controller-facing recursive forbidden pair/history/source/raw/result/wire/
  pass/fail key count 0; provenance digest
  `5ec49166e59df915105d4411df36a9901db56f365594b83ff08bbc6abf3751f6`
- Tooling incidents:
  first read-only attempt incorrectly required a three-axis velocity array;
  second used the R3c3 probe formal wrapper on an R3c1 baseline; both stopped
  before creating bank files; corrected third attempt produced the final
  deterministic compact files. These are postprocessing-tool errors, not
  runtime, raw, restart, or control errors.
- Prospective feasibility:
  exact R3c1 formal evaluator reproduction 32/32 with maximum margin error
  zero; bounded four-basis optimistic oracle 16/32, repaired 0/16, best
  remaining failed margin `-0.060314716666669765`, worst
  `-0.3585158333333367`
- Execution:
  R3c4 controller implementation not authorized; offline launch not run;
  real TSC not run; raw count 0
- Classification:
  pre-execution controller-design infeasibility. It is not a real closed-loop
  R3c4 failure and does not weaken any R3c3 or formal gate.
- Download:
  compact evidence only at
  `docs/codex/audits/stage4_2r3c4_response_bank_20260730/`;
  six transferred files / 3,847,978 bytes / inventory digest
  `222eabf8089e52d0e18fddafc9f038b28ceae66a3e510e8e5e09e65877f96397`
- Evidence:
  `docs/codex/reports/STAGE4_2R3C4_PREREGISTERED_DESIGN.md`
- Next:
  Stage4.2R3c3T1 long-separation zero-net transport-response identification;
  R3c4 remains blocked until a combined six-basis oracle is feasible 32/32;
  no BC/DAgger/RL

## Stage4.2R3c3T1 long-separation transport identification

- Local branch/checkpoints:
  `codex/stage4_2r3c3t1-transport-response`;
  preregistration `b8e66da`; implementation/deployment `ba8c455`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_runs/stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441`
- Remote audit:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_audits/stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441`
- Runtime package fingerprint:
  `cea1e49470afed77387cdf3d636de38541c47998846a817edc32dafd9b60f44a`
- Raw:
  expected/actual/parsed/execution/exact restart/causal `128/128`;
  inventory digest
  `f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f`
- Run inventory:
  532 files / 12,861,181 bytes / digest
  `159ee8f85fc07fec52280cb0f153a75d5f24b8bf69629502f8177b7810567c52`
- Passing response gates:
  central symmetry 64/64; matched history 32/32; transport-only condition
  32/32; maximum current utilization 0.3904
- Failing primary gate:
  combined rank six 32/32 but combined condition 27/32; five `p9`
  contexts exceed 25; maximum `29.296271086222426`
- Formal probe diagnostic:
  56/128 pass; not an identification acceptance gate
- Server audit:
  summary exactly recomputed; runtime/audit fingerprints identical; SHA
  `0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd`
- Corrected optimistic six-basis diagnostic:
  exact R3c1 evaluator reproduction 32/32; original response formal
  feasibility 16/32; repaired 0/16; amplitude scales 0.85 through 0.70
  repair conditioning to 32/32 but still repair 0/16; SHA
  `e7bc8f0168ff1d2019f1a9a232b5152a27d46a66a92f9542d31d80c6942c3164`
- Tooling incident:
  first read-only six-basis diagnostic used RZI positions for the frozen
  velocity condition and is preserved as invalid SHA
  `a19169f1aa7bf38547216ec4536ef06e8b97d34a784036af2c0551eb87845f4f`;
  corrected v2 reproduces the certified 27/32 and 29.2962711 values. No raw,
  run, summary, or verdict changed.
- Classification:
  identification-design FAIL; no runtime, deployment, raw, restart, causal,
  T1 summary/reporting, or real-MPC failure
- Compact download:
  `docs/codex/audits/stage4_2r3c3t1_result_20260730_204441/`; large raw
  remained server-side
- Evidence:
  `docs/codex/reports/STAGE4_2R3C3T1_FORENSIC_REPORT.md`
- Next:
  Stage4.2R3c3T2 post-contract-neutralized held-transport identification;
  amplitude-only T2 and current six-basis R3c4 are vetoed; no BC/DAgger/RL

## Stage4.2R3c3T6 target-residual new-direction identification

- Local implementation commits: `2735f99`, `256cc4b`, `71ee63c`
- Reporting-only hotfix commits: `62af8ef`, `1a070f7`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t6_runs/stage4_2r3c3t6_target_residual_new_direction_identification_20260731_040257`
- Expected/actual raw: `224/224`; raw inventory digest
  `594b4333eb848c762aec557744fe2dcef9101e1cc495f8713ed8bbe2f2913f61`
- Runtime/restart/causal/probe/solver errors: all 0; snapshots `8/8`
- Passing T6 gates: central symmetry `96/96`; matched history `48/48`;
  new three-basis condition `32/32`, maximum `5.6097803`; current
  utilization maximum `0.3904`
- Failing gate: combined eleven-basis rank `32/32`, condition pass `2/32`,
  maximum `79.1359286`
- Reporting incident: native bank currents were initially joined to
  presentation-order raw currents. Safe resume changed no raw file; the
  before/after inventory hash is
  `3a119e0f255b0d09bfc8b1e6401c94c970076fca3e5ac5b5e40dd7aa3e28938b`
- Structural design finding: inherited T3 condition passes only `11/32`,
  so the combined <=25 gate was unreachable in at least 21 contexts
- Corrected independent server audit:
  `6e04a023ddfa36216c74d669a4848261a7f4581b31ac74a4b35561f06b638dfa`
- Classification: corrected statistics/reporting bug plus genuine
  preregistration/combined-bank design failure; no real MPC was run
- Evidence:
  `docs/codex/reports/STAGE4_2R3C3T6_FORENSIC_REPORT.md`;
  `docs/codex/audits/stage4_2r3c3t6_result_20260731_040257/`

## Stage4.2R3c3T7 authenticated target-basis feasibility

- Local implementation/design commit: `d530ed5`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t7_basis_feasibility/stage4_2r3c3t7_basis_feasibility_20260731_d530ed5`
- Execution: server-side offline postprocessing only; no Ray, `gotsc`, TSC,
  raw trajectory or snapshot creation
- Fixed global subset: T3 indices `0,1,2,3,7` plus all three T6 directions;
  no pair/history label conditioning and no posthoc response scaling
- Condition result: rank/condition pass `32/32`; maximum `20.517347`
- Formal result: optimistic pass `16/32`; repair `0/16`; regression `0/16`
- Authority forensics: new direction coefficients saturated in `15/16`,
  `16/16`, `16/16` failed contexts; all 16 margins worsened relative to T3
- Output hashes: manifest
  `e69980452e756686c43ce37b6f3a471b37d6c804b3a6109fa22ea5905921ed74`;
  audit bank
  `e18f5cfc7fb510f32f0f35128274e108f224c1c4a2afec262ec6fb8d91cf0d61`;
  controller bank
  `fef1eb299cede180c1f43d8713b3174aa9afd8724ea6af4509b06ad5d92febd8`;
  feasibility
  `d4dbcd4a114eec10110432d6bf4337182bcb805b27ab83d689a9e216a052ed30`
- Classification: well-conditioned representation but real bounded linear
  authority failure in a pre-execution optimistic audit; not a real
  closed-loop failure; R3c4 remains unauthorized
- Evidence:
  `docs/codex/reports/STAGE4_2R3C3T7_TARGET_BASIS_FEASIBILITY_REPORT.md`;
  `docs/codex/audits/stage4_2r3c3t7_basis_feasibility_20260731_d530ed5/`
- Next: quantify target-direction current-headroom requirement as a
  diagnostic, then preregister new combined-action/temporal identification
  if insufficient; no R3c4/BC/DAgger/RL

## Stage4.2R3c3T8 measured-current headroom diagnostic

- Local implementation/design commit: `d98820e`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t8_headroom_diagnostics/stage4_2r3c3t8_headroom_diagnostic_20260731_d98820e`
- Execution: server-side offline postprocessing only; no Ray, `gotsc`, TSC,
  plant advance, new raw trajectory or snapshot
- Scale results: `1, 1.25, 1.5, 2, 3, 4` all remain `16/32`, with `0/16`
  failed-baseline repairs and no regressions
- Current: `32/32` pass at every scale; maximum predicted utilization stays
  `0.3904 <= 0.55`
- Scale-four failure margins: best `-0.0183834`, median `-0.0977671`, mean
  `-0.1380697`, worst `-0.3347514`
- Scale-four new-direction saturation: `15/16`, `16/16`, `16/16`
- Independent evidence: 512 unique referenced raw hashes exact, all 256
  odd responses exact, formal maximum error `4.44e-15`, current error 0
- Exact frozen-velocity enumeration: all 165 global 8-of-11 subsets checked;
  only T7's `[0,1,2,3,7,8,9,10]` passes condition <=25 on 32/32; compact
  enumeration SHA
  `b4512c71d64e1c43ce123b59c608a5cf09e990246936645c7683fbf4d4840e88`
- Result / manifest / independent audit hashes:
  `5fba92cbe0690267d25a7b6f97f53c0d2144e9453420fc7945c05b29d45e18a1`,
  `a966edd0dfde43dbf16ce76372d13340d25b7361a0ca0b7637e6032639967602`,
  `d7ab83a37496fde3ba9afcd8fdfebeff16df8313931c013d93fbd3b7d366b2b8`
- Runtime incident: first launch omitted project-root `PYTHONPATH`, exited
  before import and created no output; unchanged v2 launch succeeded
- Classification: present target-direction temporal design remains
  insufficient; not current-limited, not a real closed-loop failure, no
  reporting error; R3c4 remains unauthorized
- Evidence:
  `docs/codex/reports/STAGE4_2R3C3T8_HEADROOM_DIAGNOSTIC_REPORT.md`;
  `docs/codex/audits/stage4_2r3c3t8_headroom_diagnostic_20260731_d98820e/`
- Next: preregister new temporal/actuator combined-action identification;
  no amplitude-only, separable-even, R3c4, BC, DAgger or residual RL

## Stage4.2R3c3T9 PC3 and mixed-interaction preflight

- Local implementation/design commit: `cbb970b`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t9_preflights/stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b`
- Execution: authenticated server-side offline preflight only; no Ray,
  `gotsc`, TSC, trajectory, raw, or snapshot creation
- Exact source authentication: R17 `18/18`, R3c1 `32/32`, T3 bank `32/32`,
  T6/T7/T8 compact hashes exact
- PC3 singular values: normal `1.1347038781`, weak `0.7778123389`
- Four-direction minimum residual coverage: normal `0.9999124092`, weak
  `0.9953619114`
- Action schedule gates: complete rank `12/12`, condition `2.5510604`;
  selected rank `9/9`, condition `1.2300223`; T6 schedule reproduction
  maximum error `0`
- Mixed factorial: exact four signs, common amplitude
  `0.01060660171779821`, formal L2 `0.015`, bounded components, exact
  zero-net, first cancellation state `39`
- Output hash:
  `9a37168cce679df7deeb242bceb996c11f41bf9e589459e27386ece45f41e560`
- Validation: local and empty-deploy `587/587`; remote complete `587/587`;
  installed package `203/203` exact
- Classification: action-design PASS only; plant response, mixed
  interaction, selected nine-basis response condition, control and
  feasibility remain unrun
- Evidence:
  `docs/codex/reports/STAGE4_2R3C3T9_PC3_MIXED_INTERACTION_PREFLIGHT_REPORT.md`;
  `docs/codex/audits/stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b/`
- Next: implement the frozen independent `32 + 64 + 128 = 224` real
  identification identity; no R3c4/BC/DAgger/RL

## Stage4.2R3c3T9 real-identification attempts

- Implementation commit: `15e7033`
- Cross-process/reporting-only hotfix commit: `b489acc`
- Frozen controller revision:
  `pc3_mixed_interaction_probe_v42r3c3t9_v1`
- First v1 run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t9_runs/stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_083514_15e7033`
- First-run result: 224/224 structured startup failures, all trajectory
  and controller-trace lengths zero; no real TSC/plant conclusion
- First-run cause: T9 contract installed only in the driver process while
  fresh Ray workers instantiated the inherited T6 worker; the summarizer
  then crashed while reshaping empty requested rows
- First-run raw inventory digest:
  `05052110c7575c43d176fb42c63ca7c3a6480673113da0c0d86d0f9ee1519845`
- First-run compact forensic audit SHA-256:
  `45dbbabc7bdcfaad3fa2f2e0e1aa587edbd42e0f9fc30db31748198aee78b205`
- Hotfix classification: Ray-worker runtime adapter and reporting robustness
  only; 224-task identity, controller action semantics, and formal gates
  unchanged; new run required because v1 had no TSC trajectories
- v1h1 validation: local and empty deployment complete tests 596/596;
  server focused 13/13 and complete 596/596; offline 224/224 PASS with zero
  plant advance
- v1h1 run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t9_runs/stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005`
- v1h1 real log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090158.log`
- Last verified state at `2026-07-31 17:51:54 +08:00`: PID `1618922`
  alive, 128/224 raw complete, 96 second-batch `gotsc` active, no logged
  fatal exception
- First-batch health: 128/128 successful real T9 results, each with 51
  trajectory states, 50 trace rows and 48 wire currents per state; zero
  solver, forbidden-input, or abnormal-state rows
- External incident: SSH became unreachable after the last check. No new
  run, resume, stop, cleanup, postprocess, or scientific classification was
  performed. Resume from the exact run only after connectivity, interruption
  cause, and package compatibility are established.
- Connectivity recovered with no intervention to the run. PID `1618922`
  had exited, 224/224 raw and all final files were present, and no T9 or
  `gotsc` process remained.
- Final raw health: 224/224 strict JSON, success, unique identities, exact
  specs, 51-state trajectories, 50-row traces; 11424/11424 states contain 48
  wire currents; zero abnormal, solver, forbidden-input, restart, causal, or
  runtime rows.
- Independent postprocess: raw/manifest integrity PASS, snapshots 8/8,
  reported summary exact, statistics/reporting error count zero.
- Identification gates: execution 224/224, baselines 32/32, standalone
  symmetry 32/32, PC3 history 16/16, mixed response 32/32, mixed history
  16/16, selected rank/condition 32/32, worst condition `23.1552081`, current
  maximum `0.3904`.
- Linear route: 0/32. Mixed velocity ratio passes 2/32 with range
  `0.0716381--0.3002820`; PC3 background modulation passes 0/32 with range
  `0.1810114--1.0798643`.
- Formal tracking: 104/224, diagnostic-only for probes; not a T9 acceptance
  gate and not a real R3c4 result.
- Raw inventory digest:
  `e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2`
- Server audit SHA-256:
  `05547765ca5e1282e58b0d33e454b0a2a4dd87ee16e85146261650510ebd05f8`
- Classification: clean real identification PASS; fixed linear/separable
  model-route FAIL; no runtime/restart/corruption/reporting failure and no
  real MPC conclusion.
- Evidence:
  `docs/codex/reports/STAGE4_2R3C3T9_PC3_MIXED_INTERACTION_IDENTIFICATION_REPORT.md`;
  `docs/codex/audits/stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005/`
- Next: preregister an interaction-aware offline model using the measured
  Walsh mixed contrast and background modulation; no R3c4/BC/DAgger/RL.

## Stage4.2R3c3T10 interaction-aware feasibility

- Implementation/design commit: `0af50e1`
- Package-marker compatibility fix: `d36f7b4`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t10_interaction_feasibility/stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505`
- Execution: server-side offline raw audit only; no Ray, `gotsc`, plant step,
  new trajectory, real controller, or new snapshot
- Source authentication: T9 raw 224/224, exact spec set, raw digest
  `e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2`
- Model: fixed six-term stress/PC3 surface; rank 6; condition
  `2.9897369702`; fit 32/32; maximum measured-node error `1.0842e-19`
- Formal reproduction: 32/32 pass/margin exact; baseline passes 16/32
- Feasibility: 16/32; repairs 0/16; regressions 0
- All 16 failed optima are real T9 corners: 11 at `(+1,+1)`, 5 at
  `(+1,-1)`; T10/T9 corner margins match with maximum error 0
- Failed margin gain range `0.00471--0.01758`; best remaining margin
  `-0.0584972`; worst `-0.3562992`; active constraints position 13 and
  post-speed 3
- Output hashes: manifest
  `1bed61bc20f47545fdfcaf9acf665623aae985edfa2414cb6f3af00d9787a834`;
  audit `8c15b5339a10d45987839a28d57aa3294e765a2ee0175b6ce1247a2229d0f1a0`;
  feasibility `9d792677e9bccfea4159ee31f9132e24b9ffba1192694696528af9a4e6b52aa3`;
  server-only model bank
  `8039b5b61255cf53e49848a9d2f61e85d3c3c887f084ccdf5482d8fb40d6fd31`
- Classification: clean offline measured-authority/design failure; not
  runtime, corruption, restart, reporting, or real MPC failure
- Evidence:
  `docs/codex/reports/STAGE4_2R3C3T10_INTERACTION_AWARE_FEASIBILITY_REPORT.md`;
  `docs/codex/audits/stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505/`
- Next: veto axis de-aliasing and preregister time-localized target-relevant
  transport-versus-braking response identification; no amplitude expansion,
  R3c4, BC, DAgger, or residual RL

## Stage4.2R3c3T11 persistent-step action preflight

- Design commit: `3798a21`
- Numerical rank hotfix: `0b61f93`
- Exact T9/T3 source-reference hotfix and package v2: `a9807b9`
- Execution scope so far: offline preflight only; zero Ray, `gotsc`, TSC,
  plant, controller, or snapshot executions
- Frozen proposal: modes 0/1/2 at first-effect states 3 and 17, amplitude
  `0.0075`, cancellation at states 39--44, observation through state 50,
  exact zero net
- Prospective real count if and only if preflight passes: 32 extended
  baselines plus 384 signed probes, 416 total
- Local validation: 610/610 complete tests; 14/14 empty-package focused
  tests; 228-file hashes and LF-only checksum file
- Installed server validation: 228/228 hashes, 14/14 focused, 610/610 full
- Final installed validation log SHA-256:
  `8ef47cb218cc5bc006675e567bc2734f08f4d37c11019c5119f4aed3142e57a3`
- First installed validation failure: CRLF checksum path parsing; package
  error only, before Python tests or preflight
- First preflight stop: unnormalized rank calculation plus wrong same-shape
  T7 bank; no output JSON
- Second preflight stop: normalized rank still exposed wrong T7 bank; no
  output JSON
- Forensic source hashes: exact T3/T9 bank
  `6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86`;
  incorrect T7 bank `fef1eb299cede180c1f43d8713b3174aa9afd8724ea6af4509b06ad5d92febd8`
- Corrected package changes no new schedule, formal gate, task count, current
  envelope, controller, or physical-action semantics
- Corrected v3 preflight not started: four SSH handshakes timed out after the
  successful package-v2 validation
- Next: when SSH returns, assert the corrected v3 output/log paths are absent,
  run exactly one offline preflight, retain compact evidence, and authorize
  the 416-task implementation only on an all-gates PASS
- Connectivity recovered; corrected v3 paths were absent and the one guarded
  offline preflight passed 2/2 actuator cases
- Corrected preflight JSON SHA-256:
  `a449fd5447bd174b5fa067f464c651bc5a1d3e146bae7f67d22535eed076dfbd`
- Corrected preflight log SHA-256:
  `aec6db4f4c35436825b66181adb888dc0b9b1622c6aaf2c6c0886ca2eb009050`
- Existing/new/augmented ranks: `12/6/18`; maximum condition
  `3.1459620743`; minimum novelty residual `0.7726912050`
- Classification: clean offline action-design PASS; no plant, restart,
  hidden-history, controller, or real-MPC conclusion
- Next: implement and validate the exact frozen 416-task real identification
  identity; do not change its schedule or gates and do not authorize R3c4

## Stage4.2R3c3T11 authentic persistent-step identification

- Branch: `codex/stage4_2r3c3t11-persistent-step-identification`
- Implementation commit: `322ade2`
- Deployed inventory-order fix: `40944f9`
- Forensics evidence checkpoint: `5e9d3d0`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t11_runs/stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9`
- Remote log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t11_persistent_step_response_identification_20260731_224518.log`
- Execution: 416/416 real authentic restart TSC rollouts in fixed batches
  `128 + 128 + 128 + 32`; 32 baselines and 384 signed probes
- Raw: 416/416 parse, 19,273,198 bytes, inventory digest
  `f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3`
- Integrity: exact spec/filename/manifest/package; 8/8 snapshots; reported
  summary exact on independent recomputation
- Execution/restart/causality/probe/solver/forbidden/reporting errors: zero
- Identification gates: execution 416/416, baseline prefix 32/32, symmetry
  192/192, matched history 96/96, rank 6 in 32/32, current maximum `0.3904`
- Failed gate: response condition <=25 in 25/32; maximum `38.9150751`
- Independent SVD: every reported condition reproduced with maximum absolute
  difference `4.97e-14`; seven failures retain rank 6
- Formal tracking: 207/416 diagnostic-only; baselines remain exactly 16/32
- Independent server audit SHA-256:
  `02933f9ee05f91f6db565e955e0106c65dc6591f273fb562e68ac2767d28c19c`
- Compact forensic SHA-256:
  `8cf365fcac69924c09bae51c9c5c1c3cc003959ff3e7a92111b387316a8b617b`
- Classification: clean identification-design FAIL due to context-dependent
  weak/near-collinear response columns; not runtime, restart, corruption,
  reporting, or real MPC failure
- Large raw/full inventory remain server-side; only compact derived evidence
  was downloaded
- Next: preserve raw and preregister a genuinely new time-localized response
  experiment; no post-hoc normalization, threshold relaxation,
  amplitude-only rescaling, R3c4, BC, DAgger, or residual RL

## Stage4.2R3c3T13S1 minimal transition sentinel

- Branch: `codex/stage4_2r3c3t13s1-transition-sentinel`
- Implementation commit: `898b559`
- Deployed package-closure commit: `ecc05f6`
- Final transition-forensic commit: `9b8353d`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s1_runs/stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_ecc05f6`
- Remote log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_110302.log`
- Execution: 52/52 fresh authentic restart `gotsc` trajectories
- Raw: 52 JSON.GZ, 2,463,366 bytes, digest
  `de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603`
- Integrity: exact package/manifest/config, 4/4 snapshots, 4/4 baseline
  prefixes, 52/52 raw parse, exact independent summary recomputation
- Runtime/restart/causality/solver/scheduler/saturation/reporting errors: zero
- Passed scientific support gates: execution 52/52, causality 24/24, signal
  24/24, local rank/condition 4/4, maximum condition `9.1719426463`, maximum
  current utilization `0.3904 <= 0.55`
- Failed frozen gates: central symmetry 0/24 and matched hidden-history
  response 0/12
- Official route: `SENTINEL_FAIL_STOP_IDENTIFICATION`
- Read-only actual-current forensic: requested command symmetry 24/24,
  observed current symmetry 0/24, immediate plant symmetry 3/24,
  full-window plant symmetry 0/24, immediate matched history 6/12,
  full-window matched history 0/12
- Card15 resolution: 304/336 active compared command components below one
  `.3E` grid; maximum observed integer-grid residual `2.1032e-12`
- Classification: clean identification/model/action-resolution design FAIL;
  not runtime, restart, corruption, reporting, real MPC, or global
  unreachability
- Compact evidence downloaded directly; all 52 raw remain server-side
- Next: zero-new-TSC Stage4.2R3c3T13S2 exact Card15 actuator and causal-
  observability audit; no rerun/enlargement, T11 bank, R3c4, expert data, BC,
  DAgger, or residual RL

## Stage4.2R3c3T13S2 quantized observability and T13S2R1 readback forensics

- T13S2 implementation commit: `626f635`
- T13S2R1 design/implementation commits: `c926dad`, `ae4241b`
- T13S2 remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s2_audits/stage4_2r3c3t13s2_quantized_observability_20260801_626f635`
- T13S2 report/manifest SHA-256: `9ef183d20f3354d11bb70c2324bade6829879f00c05dd96b99c1312bcfd53d58`,
  `564569ec948399792d2db49c4d5742e70a2b20c9ad48efaad7eda34f95f096dd`
- Exact Card15 target reconstruction: 2,600 transitions, 36,400 components,
  only 13,000 within `1e-9 A`; maximum readback residual `1.0e-5 A`
- T13S2 primary route: `ACTUATOR_MAPPING_IMPLEMENTATION_GAP`
- Causal audit: 48 records, 8 feature collisions, 0 same-feature/same-input-
  path collisions, 0 exact aliases, 24/24 finite clean history separations
- T13S2R1 remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s2r1_audits/stage4_2r3c3t13s2r1_readback_residual_forensics_20260801_ae4241b`
- T13S2R1 report/manifest SHA-256: `62b28bec07bde398cfec6b4aaf42899960e63a8761ce19316f83e8c929903c87`,
  `adf0cc73a6bc9b05a6dbe7a9fdae09b80346fe54a41a4723fb9cfce0d0bf2edf`
- Baseline-derived fixed readback units:
  `[2,2,2,2,2,2,2,1,0,0,0,1,0,0] * 1e-6 kA-turn`
- Signed-probe retrospective holdout: 33,600/33,600 within `1e-9 A`, maximum
  residual `2.8422e-14 A`
- Runtime/raw/restart/reporting/TSC/plant errors or steps: zero
- Classification: finite development actuator/readback structure only; no
  observer, plant model, real MPC, or independent holdout validation
- Next: offline T13S3 quantized causal multi-hypothesis/tube interface; then
  a separately preregistered minimal lattice-aligned holdout

## Stage4.2R3c3T13S3 quantized causal tube interface

- Implementation commit: `37e3913`
- Evidence/report commit: `67543b8`
- Outcome: `INTERFACE_COMPLETE_HOLDOUT_REQUIRED`
- Implemented exact Card15 serializer, T13S2R1 development nominal plus
  nonzero per-coil interval, immutable unknown-velocity causal restart state,
  numeric issued-command/queue state, forbidden-field rejection, and
  fail-closed multi-hypothesis additive transition tube
- Point model certified / robust controller authorized: `false / false`
- Local focused and isolated direct-copy tests: `15/15`, `15/15`
- Server isolated and installed focused tests: `15/15`, `15/15`
- Server installed complete suite: `654/654`, one expected skip
- Frozen predeployment package checksum: `269/269`
- Server staging:
  `/home/yangshen0711/tsc_software/stage4_2r3c3t13s3_quantized_tube_37e3913`
- Server validation log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/stage4_2r3c3t13s3_server_validation_37e3913.log`
- Validation log SHA-256:
  `f70598458c08aee524298bb402789c7097b66203e50cc9332a2b5942ce15dfc5`
- Controller/Ray/gotsc/TSC/plant steps: zero
- Classification: software interface PASS only; no runtime, package,
  reporting, raw, point-model, observer, control, or robustness result
- Next: implement and validate the separately frozen 52-rollout T13S4
  dynamic-Card15 lattice transition holdout; do not run real MPC
