# Run ledger

## 2026-08-21 fixed-1000 NR1 R4 FAIL and R4R1 decision

- R4 route `ONE_MS_NR1000S1R4_EFFECT_CONTRACT_FAIL_STOP`; 3 rollouts and
  10 advances. Hold primary/replay were exact.
- Pattern-A return issued `0.30000 A`; coil 11 actual-current change was
  `0.30001 A`, so the unchanged hard observed gate stopped before step 3.
- Decision: no resume and no threshold relaxation. R4R1 is a fresh identity
  with pattern command magnitude capped at `0.299 A`, leaving 1 mA reserve
  below the same 0.3 A hard gate.

## 2026-08-21 fixed-1000 R3R2 PASS and NR1 R4 freeze

- R3R2 route:
  `ONE_MS_NR1000S0R3R2_CANONICAL_1000_RESTART_SEMANTICS_QUALIFIED`.
- Zero TSC; four rollouts/eight raw states reparsed. Stable artifacts and all
  physical semantics were exact. Each outputa contained exactly one launch
  wall-clock and one CPU-time line; normalized hashes were exact.
- Decision: freeze fresh NR1 R4 on reconstructed r0. First source-to-successor
  actual-current delta is descriptive and removed only by matched-hold
  differencing; command slew and all later observed slew remain hard gates.

## 2026-08-21 fixed-1000 R3R1 four-call result and R3R2 decision

- R3R1 v2 result SHA-256:
  `9cc0b7ce85ad1b277d9091ff71203a127face51c0f460864b38c1dfd93fd17b0`.
- All four one-ms hold rollouts passed locally; issued delta was `0 A`, the
  descriptive actual-current delta was `8 A`, and state semantics matched.
- Final frozen route is
  `ONE_MS_NR1000S0R3R1_CROSS_RESTART_ARTIFACT_FAIL`: only state1 outputa
  hashes differ. Direct diff identified launch wall-clock and CPU-time lines.
- Decision: no replay. R3R2 is a zero-TSC raw reparse that permits removing
  exactly one line of each frozen non-semantic timing class and requires every
  remaining outputa byte plus all stable artifacts and physical semantics to
  agree.

## 2026-08-21 fixed-1000 R3R1 zero-call text-format stop

- Installed R3R1 offline passed, then execution stopped before runner step:
  `tsc_invocations=0`, `maximum_issued_delta_a=0.0`.
- The only reason was `LIVE_CARD15_CENTER`: two Card15 strings encoded the
  same Decimal currents in different formats. This was not a plant, restart,
  action or safety result.
- Decision: preserve the zero-call output; replace byte-string equality with
  exact parsed-Decimal command equality. No gate, target, budget or physical
  identity changes, so a fresh output path under the same R3R1 campaign is
  permitted after server regression.

## 2026-08-21 fixed-1000 R3 evaluator failure and R3R1 decision

- R3 output: `rgeo_zgeo_1ms_1000_restart_dual_validation_20260821_5f7f86d5_v1`.
- Result SHA-256: `4ae91488537dbe67d7a8201dda337b54d5e9f0887dd5d3e5c9122f2c27208fa9`.
- One TSC invocation produced state1 at exactly 1.001 s with q0 Card15 and
  finite R/Z/Ip. It was rejected by the legacy actual-current slew check
  (`8 A`), although issued command delta was exactly zero.
- Decision: freeze R3 as evaluator-wiring FAIL; do not rerun it. R3R1 uses a
  new identity, preserves the four-call maximum/no retry, checks issued slew
  in the Card15 command coordinate, records source actual-current bias only
  descriptively, and requires exact state/artifact agreement across both
  byte-distinct reconstructed restart roots.

## 2026-08-21 fixed-1000-ms restart reconstruction R2R2

- Implementation revision: `ddbab85ff38cf35f63e616beeb2bcf9b5126d3c2`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_restart_reconstruction_r2r2_20260821_ddbab85f_v1`
- Validation: focused `24/24`; all one-ms `727/727`; zero-TSC route
  `ONE_MS_NR1000S0R2R2_OFFLINE_PASS`
- Execution: two complete 0--1 s full-input calls; no restart calls; result
  SHA-256 `7182fb4a98c375a5ce07b82768d2b3b9cb451dbb56383b9e0d76fcda40829f12`
- Result: `ONE_MS_NR1000S0R2R2_INITIAL_RECONSTRUCTION_FAIL`
- Exact finding: R/Z/R_mid/Ip, 14 coils and 48 wires are identical across
  reconstructions; `sprsoua` hashes differ (`de986e49...d79145` versus
  `283d55bd...4969d`), and complete output text hashes also differ
- Classification: frozen exact-restart-file repeatability FAIL; not a plant,
  model, Authority, Recourse or controller result
- Decision: do not reconstruct again. R3 binds both complete roots and tests
  two fresh one-ms replays from each; only checked cross-restart semantics can
  qualify, while R2R2 remains FAIL


## 2026-08-21 fixed-1000-ms restart reconstruction R2R1

- Implementation revision: `b63f86be7b69f93e505d2c67be31e7df40de01e1`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_restart_reconstruction_r2r1_20260821_b63f86be_v1`
- Validation: focused `23/23`; all one-ms `726/726`; zero-TSC route
  `ONE_MS_NR1000S0R2R1_OFFLINE_PASS`
- Execution: one counted call, no retry; result SHA-256
  `7c5b98d4b5981ac2a2acaa33b171929d7d01e17d80b52a2a0cae75aff51ab497`
- Result: `ONE_MS_NR1000S0R2R1_INITIAL_RECONSTRUCTION_FAIL`
- Root cause: the offline path applied 2700 s, but `execute()` reloaded the
  source config and passed 180 s to the runner; stderr and identical 0.10253-s
  progress prove the intended R2R1 runtime budget was never exercised
- Classification: execution-path implementation wiring FAIL; not another
  scientific input, TSC-physics, model, Authority, Recourse or controller test
- Decision: R2R2 uses one tested helper to apply 2700 s in both paths; no
  R2R1 resume and no change to scientific semantics


## 2026-08-21 fixed-1000-ms restart reconstruction R2

- Implementation revision: `49e3d1cb33ed3b1ce9b947e6b5cfa0d0b50c2473`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_restart_reconstruction_r2_20260821_49e3d1cb_v1`
- Validation: focused `22/22`; all one-ms `725/725`; zero-TSC route
  `ONE_MS_NR1000S0R2_OFFLINE_PASS`
- Execution: exactly one counted full-input TSC invocation; no retry
- Result: `ONE_MS_NR1000S0R2_INITIAL_RECONSTRUCTION_FAIL`; result SHA-256
  `b018d713b9b410b6f1dbf4288e4155def984920c4341df7d60d4e1981040f84f`
- Forensics: normal progress reached internal time `0.10253 s` in 180 s;
  TSC then returned the runner timeout code `-999`. No reconstructed state,
  second initial run or restart validation was produced, and no process remains
- Classification: inherited process-timeout budget design FAIL; not an input,
  TSC-physics, model, Authority, Recourse or controller result
- Decision: new R2R1 identity changes only the full initial-run timeout to
  2700 s; scientific inputs, gates, four-call maximum and no-retry rule remain


## 2026-08-21 fixed-1000-ms restart reconstruction R1

- Implementation revisions: `ebb5f50c / c9cf6c74 / 47b5edc3`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_restart_reconstruction_47b5edc3_v2`
- Validation: focused `20/20`; all one-ms `723/723`; zero-TSC preflight PASS
- Execution: exactly one counted TSC invocation; no retry
- Result: `ONE_MS_NR1000S0R1_INITIAL_RECONSTRUCTION_FAIL`
- Failure: full reconstruction was incorrectly seeded by the 1229-byte
  restart checkpoint `inputa` (`IRST1=1`) without a restart file; TSC stopped
  in `problem_size` and produced no reconstructed state
- Classification: initial-input design FAIL; not runtime, plant, model,
  Authority, Recourse, controller or reachability evidence
- R2 basis: original 13,800-byte non-restart input SHA-256
  `0fce4f5fd5da6e848d93c709fc1fc5f338a8772e27bfaf3890fbacbc36df10ae`
  with four saved state artifacts byte-identical to the selected 1000-ms state

## 2026-08-21 fixed-1000-ms first interface attempt

- Branch/checkpoints: `codex/rgeo-zgeo-1ms-1000ms-control`,
  `5d4e05ce / 66e3f434 / c74cc2b3`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_nr1_result_20260821_c74cc2b3`
- Validation: fixed-1000 focused `14/14`; all one-ms `717/717`; zero-TSC
  interface preflight PASS
- Execution: one reset and one matched-hold plant advance; no retry and no
  remaining rollout
- Result: `ONE_MS_NR1000S1R1_EFFECT_CONTRACT_FAIL_STOP`
- Forensics: successor internal time was 1.1000--1.1010 s and its R/Z/Ip
  reproduced the historical 1100-ms source.  The nominal 1000/1100
  `sprsina` SHA-256 values are identical (`5ead6983...afabe`), while authentic
  1000 `outputa` spans 0--1.0000 s.
- Classification: source/restart identity failure; not runtime, solver,
  plant-effect, model, Authority, Recourse, controller or reachability
- Next: maximum-four-invocation isolated initial-run restart reconstruction,
  followed by two one-ms replay validations; immutable source remains read-only

## R_geo/Z_geo 1 ms ID-2Z37 fresh engineering-event qualification

- Implementation revision:
  `d552379737c9541e8f41770a0a1af9e0bfa6dab7`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z37_20260821_d5523797_v1`
- Server validation: focused `6/6`; complete one-ms suite `712/712`; offline
  preflight PASS with zero TSC
- Execution: calibration/replay `6/6`; `438/438` attempts, TSC calls and
  verified advances; blind `0`; models fit/updated `0`
- Raw: `444` states, `2,220` artifacts, `26,148,458,256` logical bytes,
  digest `9ec32962eaac03627924aa4eb343dd4db4bf0ee9abae9c8ac656d8c39da12ffd`
- Calibration: fixed event containment `1/1`; maximum non-event R/Z/Ip error
  `0.639621/0.111249 mm/7.10555 A`; R and Z exceed frozen
  `0.05/0.05 mm` gates; replay and independent audit PASS
- Route: `ONE_MS_ID2Z37_FRESH_CALIBRATION_FAIL_CLOSE_EVENT_BOX_ROUTE`
- Primary / independent SHA-256:
  `1a14f7013726a55b13714d223102c6b2fa45a50b4ec58c3d50e3cc5c767b206d /`
  `d4acb6bc64d4ba120d5e8325c9f7d2c74843e50e8e72855a0e3bbe8f6e57aacc`
- Cleanup: after matching compact hashes and independent PASS, removed only
  the exact run `rollouts/` subtree (`26,552,831,713` filesystem bytes);
  server available space became `224,678,121,472` bytes
- Evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2z37_20260821_d5523797_v1/`
- Decision: close the sparse event-box route; no adjacent widening, phase or
  third model. Pause for higher-level route review before any new TSC/model.

## R_geo/Z_geo 1 ms ID-2Z36 engineering-floor event set

- Implementation revision: `0246104bec239c0dfcb5440ea65aa71cb629211c`
- Server validation: focused `3/3`; complete one-ms suite `706/706`
- Zero TSC / plant advances / fits / ID2Z35 fit rows: `0/0/0/0`
- Payload SHA-256:
  `ace09ffba98b7bf60336452c9f4765ce5b8dc6bfe5bf71e33739eeba5e22c9a8`
- Primary / independent SHA-256:
  `e5090d4deeb804db172f039290ad0513c1314773e4973897d576bba78860242a /`
  `9bd8335e0d894f129fb2d8a0a865060ae03550f427973eaf76aed4e7bb31145f`
- Route:
  `ONE_MS_ID2Z36_ENGINEERING_FLOOR_EVENT_SET_PASS_FRESH_QUALIFICATION_ONLY`
- Evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2z36_20260821_0246104b_v1/`
- Next: fresh phase48 calibration, then only after PASS unopened phase54 blind

## R_geo/Z_geo 1 ms ID-2Z35 fresh event-set qualification

- Implementation revision:
  `2b6adb1c311da59b66537c4f6d8a49f72d58a627`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z35_20260821_2b6adb1c_v1`
- Server validation: focused `6/6`; complete one-ms suite `703/703`
- Execution: calibration/replay `6/6`; `438/438` verified advances; blind `0`
- Raw: `444` states, `2,220` artifacts, `26,148,458,256` logical bytes,
  digest `5259c835a8581b794c70f6076d8a77a3bef497ace1806b5972c39bc89a27da37`
- Primary / independent SHA-256:
  `f7e29710d19ffe230d8b523f431cd4d3063c61e96b911a8985acf2a17125d077 /`
  `dbd92d91d2497cab21ce79e80474220d6d7d955214952fa1fa494b49a5d3200b`
- Result: q_R-minus/effect-age-13 missed fresh phase-52 containment `0/1`;
  all non-event errors stayed below `0.021134/0.034790 mm` R/Z and `2.23235 A`;
  replay and independent audit PASS
- Route: `ONE_MS_ID2Z35_FRESH_CALIBRATION_FAIL_STOP_BEFORE_BLIND`
- Cleanup: after compact hash recovery and independent PASS, removed only the
  exact run `rollouts/` subtree (`26,552,858,293` filesystem bytes)
- Evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2z35_20260821_2b6adb1c_v1/`
- Next: one no-search robust-event successor with fresh calibration and blind;
  ID2Z35 rows remain zero fit and no controller/Authority/Recourse is open

## R_geo/Z_geo 1 ms ID-2Z34 event-set model development

- Date: 2026-08-21 Asia/Shanghai.
- Revision: `e04aeb0811dcb81d1122a29a237d4c1aeaf86a1b`.
- Validation: focused `7/7`; complete one-ms suite `697/697`.
- Work: two frozen models fit over eight ID2Z33 branch families; zero TSC,
  zero plant advances and zero calibration/holdout reads.
- Smooth candidate: FAIL, maximum R point error `0.319267 mm > 0.300 mm`.
- Event-set candidate: PASS, one event cell, R full width `0.704388 mm`;
  maximum non-event R/Z/Ip errors `0.019447 mm / 0.014427 mm / 0.95555 A`.
- Selected payload SHA-256:
  `7f4ea48fc0117a77a23c7df378748a0cbac2f3194a6a47e254ba1bcd472df846`.
- Route: `ONE_MS_ID2Z34_EVENT_SET_MODEL_PASS_FRESH_QUALIFICATION_DESIGN_ONLY`.
- Primary / independent SHA-256:
  `0c58ea1a8c1bc48c316dcf153de4ce7af326493371a6980cb707875349c6c641 /`
  `ecef293d6205cfbd5f1e88456e2f44f7ebc7a2b14796b975f3a61e40114e5f9d`.
- Next: freeze the artifact; fresh intermediate-phase calibration, then an
  unopened whole-phase blind family. No controller prerequisite is implied.

## R_geo/Z_geo 1 ms ID-2Z33 corrected moving-center D0

- Date: 2026-08-21 Asia/Shanghai.
- Physical / reporting-audit revisions: `3892b0c1` / `6e9c0049`.
- Server output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z33_20260821_3892b0c1_v1`.
- Validation: focused `3/3`, all one-ms `690/690`, offline action separation,
  exact return, slew/current/headroom and storage gates PASS.
- Execution: `10/10`, `730/730` attempts/gotsc/verified advances, 740 states.
- Raw: 3,700 required artifacts / 43,580,763,760 bytes / digest
  `7feeaf08be6982334fbfabc5c0e7e2d860ebffcd7dda624a57f32f39d0dff83f`.
- Result: all eight signed branches and all four phase/horizon geometry gates
  PASS; exact replay and independent raw audit PASS.
- Route: `ONE_MS_ID2Z33_CORRECTED_MOVING_CENTER_D0_PASS_MODEL_DESIGN_ONLY`.
- Primary / independent SHA-256:
  `14f0b4f081f95ff69e418ea0f9f4de6725705c963a153bd7603e324e066f29c3 /`
  `735cd75f5d0b7636fd123e66bc0e94a9ea678a4bb9e142ac942bf89b9c469e5a`.
- The direct independent entrypoint initially missed repository `sys.path`;
  `6e9c0049` repaired reporting only and ran zero TSC.
- Cleanup: after compact hash recovery, removed only this run's authenticated
  `rollouts/` subtree (`44,254,755,926` filesystem bytes); compact and log
  remain; free space `224,689,799,168` bytes.
- Next: one server-only, at-most-two-candidate event-aware development model
  comparison. Fresh qualification and control prerequisites remain closed.

## R_geo/Z_geo 1 ms ID-2Z32 post-event delayed-tail D0

> **Erratum:** server forensic SHA-256
> `710f31b0887cc0cd834224318c6d77071d85177f09b8131db3f168bc4ea8b673`
> proves all four issue-56 action streams are identical to baseline. The saved
> signal-FAIL route is not a valid plant-response result. Correct classification:
> `ACTION_STREAM_CONSTRUCTION_DESIGN_FAIL_NO_SCIENTIFIC_ISSUE56_RESPONSE_TEST`.
> ID2Z32 remains zero fit weight; a changed stream requires a new identity.

- Date: 2026-08-21 Asia/Shanghai.
- Design / implementation: `99cc9bb5` /
  `c6b1c5b9b4bf3e350c7567af2f84f070c33bf879`.
- Server output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z32_20260821_c6b1c5b9_v1`.
- Validation: focused `4/4`, all one-ms `686/686`, offline streams/storage PASS.
- Execution: `10/10`, `730/730` attempts/gotsc/verified advances, 740 states.
- Raw: 3,700 required artifacts / 43,580,763,760 bytes / digest
  `e7601a252393b22146fb6fa5890889fa96130b80b3e73e3b3d695302136df51a`.
- Result: issue-50 signal/geometry PASS; issue-56 four-branch response exactly
  zero; replay and independent audit PASS.
- Route: `ONE_MS_ID2Z32_POST_EVENT_DELAYED_TAIL_D0_SIGNAL_FAIL_CLOSE_CELL`.
- Primary / independent SHA-256:
  `b704bc754d537cd1c4d885541dd687b3bb359b1742f98a03b5c895398f5b0e7d /`
  `e478e79f0d5424f2cdb867011d7eaebe909a5c280d4f7a369cf1666dd62b83a9`.
- Cleanup: removed only this run's authenticated server `rollouts/`; compact
  and log retained; free space `163,825,262,592` bytes.
- Next: zero-TSC nominal/action-allocation and materially different basis audit.

## R_geo/Z_geo 1 ms ID-2Z18 full-horizon token development

- Date: 2026-08-20 Asia/Shanghai.
- Physical / reporting-audit revisions: `dc577537` / `08e15ac0`.
- Server output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z18_20260820_dc577537_v1`.
- Validation: focused `10/10`, all one-ms `558/558`, shell/compile, offline
  `24/24` static streams and storage gates PASS.
- Execution: `16/16` complete rollouts, `1040/1040` attempts/gotsc/verified
  advances, 14 fit-weight histories and two exact zero-weight replays.
- Raw: `5280` required artifacts / `62,190,927,744` bytes / digest
  `05dcc1f085c5696698c9deeeb7e91bf915284af18b24b648fd9537db574b3652`.
- Scientific gates: all six pair separations `2.715--7.465 mm`; increment
  rank `3`, condition `2.086086164`; calibration/holdout reads `0`, models `0`.
- Final route:
  `ONE_MS_ID2Z18_FULL_HORIZON_DEVELOPMENT_DATA_PASS_MODEL_COMPARISON_ONLY`.
- Primary / corrected independent SHA-256:
  `5fbba54efc3ae3a921d77fc32adb31a7af59775dc677b09bfbc209807e4d4d8c /`
  `6d7603de3e5d805082a61f1dde2a2148117105b130578f2dc98e9187a0d077b5`.
- The preserved initial audit SHA
  `60e4f8a93f5d428f799a65949620881fbbcdf2292806dccbfd991c98848a0bb1`
  failed only because it compared post-write outgoing raw `inputa` to a
  preissue compact hash. The reporting-only repair reran no TSC.
- Cleanup: after independent audit and 20/20 compact/log hash recovery,
  removed only this run's `rollouts/` subtree (`63,153,736,435` filesystem
  bytes); free space `118,086,983,680` bytes.
- Next: exactly one separately frozen two-candidate development model
  comparison; calibration/holdout and controller remain closed.

## R_geo/Z_geo 1 ms ID-2Z17 remaining-basis beam

- Date: 2026-08-20 Asia/Shanghai.
- Design / implementation revisions: `3545fc9c` /
  `4bfcca2d7c7185dd4a08ef76db7a352005836f91`.
- Server output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z17_20260820_4bfcca2d_v1`.
- Validation: focused `13/13`; all one-ms `548/548`; offline static tree
  `121/121`; storage and shell/compile gates PASS.
- Execution: `18/18` complete rollouts, `1170/1170` verified advances,
  `1188` states, zero safe stops and exact selected replay.
- Raw: `5940` required artifacts / `69,964,793,712` bytes / digest
  `07fe40a1a22e844c007f0ad2852e81d8c123a63b7c2ad154c0e5305339baed1e`.
- Selected path: `f100__f8__f8__p08_plus4__p08_plus4`; terminal maxima
  `28.167666 mm / 0.377144 m/s / 2.12136% Ip`; no capture.
- Final route:
  `ONE_MS_ID2Z17_NEW_BASIS_BEAM_NO_CAPTURE_PHYSICAL_REACHABILITY_REDESIGN_REQUIRED`.
- Primary / independent SHA-256:
  `58e89a7292b8f256bb58d1e633d0e46794852727675f9db79da188da13f37994 /`
  `ad86d43a83dec29bf6b2d37f69a01c44518c548b7bb5cd53cf5ce9f70cbb1419`.
- Cleanup: after independent audit and 22/22 compact/log hash recovery,
  removed only the exact run's raw `rollouts/` subtree (`71,071,432,704`
  filesystem bytes); free space `118,093,258,752` bytes.
- Next: one bounded full-horizon reachability/learning-contract redesign;
  ID-2Z17 remains zero fit weight and no controller/Recourse-L1 is open.

## R_geo/Z_geo 1 ms ID-2Z10 five-context model comparison

- Date: 2026-08-19 Asia/Shanghai.
- Implementation revision: `31b90c237e0801ff4ff083343a2b8b15db19ce6b`.
- Server output: `rgeo_zgeo_1ms_id2z10_runs/20260819_31b90c23_v1`.
- Validation: focused 6/6; all one-ms 472/472; shell/compile/hashes PASS.
- One pre-fit launcher attempt hit transferred execute-bit `Permission denied`;
  output did not exist, so the server bit was restored and the unchanged
  identity ran once.
- Zero TSC/plant/controller/optimizer and zero calibration/holdout reads.
- Stable: mean/max NRMSE `0.229901/0.323605`, max R p95 `0.726041 mm`,
  min cosine `0.991803`, max regret `0.194231`.
- Stable+GRU4: mean/max NRMSE `0.233554/0.395545`, max R p95
  `0.873908 mm`, min cosine `0.985044`, max regret `0.194231`.
- Both predicted `b4` in every fold; no candidate eligible and no artifact.
- Primary / replay-audit SHA-256:
  `eb725e6feeb3d46a04aebdd2e2bbb97ab15217db314644f466403f634b23e618 /`
  `dac2cf62251a4f6d64d5fa1f5b92c6d950c8b10b7266fd9b9164a613a4b13c48`.
- Final route: `ONE_MS_ID2Z10_FIVE_CONTEXT_MODEL_FAIL_ACTION_BASIS_CONTROL_REVIEW`.
- Next: pause for action-basis/control-utility and model-target review; no
  capacity ladder, calibration, holdout or controller execution.
- ID-2Z9 cleanup: removed only its audited `rollouts/` subtree,
  51,311,622,623 bytes; top-level compacts/audits/logs remain remotely.

## R_geo/Z_geo 1 ms ID-2Z9 late-root branch utility/support

- Date: 2026-08-19 Asia/Shanghai.
- Physical / reporting-audit revisions: `63f68c2b / 01164ef1`.
- Server output:
  `rgeo_zgeo_1ms_id2z9_runs/20260819_63f68c2b_v1`.
- Validation: initial focused 9/9 and all one-ms 465/465; reporting repair
  focused 10/10 and all one-ms 466/466; shell/compile PASS.
- Execution: 11/11 canonical-source rollouts, 847/847 verified advances,
  858 states, zero guarded safe stops.
- Raw: 4,290 files / 50,530,128,792 bytes / digest
  `308a222e8b4f6f4d40babeadc685ce7b9693f1abd8277ec90dc7c7a8c417d5fe`.
- Round D selected `b2f2`; Round E selected `f2b2`; full sequence is
  `f4 -> b2f2 -> f2b2 -> b2f2 -> f2b2`.
- Score improved from matched hold `3.737459254` to `2.983667001`; exact
  replay passed; ten new complete development-weight windows exist.
- Capture still failed: terminal maximum distance `26.767972 mm`, speed
  `0.298366700 m/s`, Ip fraction `0.036971927`.
- Initial independent audit SHA-256
  `5ea6cfec175e82a79de70f1e5b39bd9ecdc01656beffae16db1858d44b010251`
  is preserved FAIL because it inherited ID-2Z6's 1169-ms raw horizon and
  wrong compact schema. Repaired independent SHA-256
  `13430405c3b1cedd092fe3408e1908b53707fc734052d1cbfdf104fa31298d97`
  passed on the same raw with zero new TSC.
- Primary SHA-256:
  `c0137121efd593af6b00dd690fd0b4bec6b6f094720c40f28e99b59d2ac59d6d`.
- Final route:
  `ONE_MS_ID2Z9_LATE_ROOT_BRANCH_UTILITY_SUPPORT_PASS_FIVE_CONTEXT_MODEL_ONLY`.
- Next: exactly one five-context comparison of the unchanged ID-2Z8 stable
  and stable-plus-GRU4 candidates; no larger model or controller authorization.

## R_geo/Z_geo 1 ms ID-2Z8 bounded small sequence-model comparison

- Date: 2026-08-19 Asia/Shanghai.
- Implementation revision: `584bc28db2a000325a51d5484f63e621034a422f`.
- Server output: `rgeo_zgeo_1ms_id2z8_runs/20260819_584bc28d_v1`.
- Validation: focused `8/8`; all one-ms `456/456`; shell/compile PASS.
- Execution: zero TSC/plant/controller/optimizer; two candidate classes,
  six fold-backbone fits and nine fold-GRU fits; no full-data artifact.
- Stable candidate: max response NRMSE `0.2244456`, max R/Z/Ip p95
  `0.460884 mm / 0.265906 mm / 28.7714 A`, minimum peak cosine `0.989965`,
  max terminal-score regret `0.194231`.
- GRU4 candidate: max response NRMSE `0.2196040`, max R/Z/Ip p95
  `0.502982 mm / 0.212997 mm / 14.5225 A`, minimum peak cosine `0.982424`,
  max regret `0.194231`.
- Both predicted `b4` in all three held contexts; measured best arms were
  `f4`, `b2f2`, `f2b2`. No candidate was eligible.
- Primary / deterministic-audit SHA-256:
  `8c7056826077b3dfd6d3aef447caf5b538d0fd28a2d7571eafa8b98da13ed11c /`
  `5265a78921d71806976f024600232fdf911ca66fbd6086c5cb81f8a90652fb9e`.
- Final route: `ONE_MS_ID2Z8_SMALL_MODEL_FAIL_TARGETED_DATA_OR_BASIS_REVIEW`.
- Next boundary: at most two fresh late-root B/F/H sibling contexts as a
  combined utility/support discriminator; no larger network or holdout.

## R_geo/Z_geo 1 ms ID-2Z6 early-root branch teacher

- Date: 2026-08-19 Asia/Shanghai.
- Original / reporting-resume / failure-finalizer / corrected-audit revisions:
  `39a2c3ac / ce5cb4fe / c7840b55 / 6e3556bb`.
- Server run:
  `rgeo_zgeo_1ms_id2z6_runs/20260819_39a2c3ac_v1`.
- Execution: 8 resets, 486 attempts/`gotsc`, 485 verified successors, seven
  complete rollouts and one partial rollout; 493 states.
- Required raw inventory: 2,465 files / 29,034,211,532 bytes / digest
  `4d75fef0b3dc61cfcb3609cac87b3d6bf07745ae70ffd37637c28f2b7b498ef0`.
- Round 0 completed all five siblings and selected `f4` with score
  `3.676826525` versus hold `4.407677637`.
- The original run had a post-trajectory descriptive-key exception. The
  reporting-only resume then omitted the run-specific raw root and was
  stopped during `r1__f4`; no retry occurred.
- Primary / corrected independent SHA-256:
  `6f9ebc89f9f0fb9f3666a397cdf960dfd134b3c133abcf93375aaf7b8ac6752b /`
  `a98b9747eae86879a2e65bbf3b9e9c88e97d70d696d102acf25b2a04d66943b0`.
- Final route: `ONE_MS_ID2Z6_EXECUTION_OR_INTERFACE_FAIL_STOP`.
- Status: implementation/driver FAIL, not scientific teacher or control
  evidence. ID-2Z7 must be a fresh later-round continuation with mandatory
  run-root isolation; interrupted round-1 paths have zero weight.
- Cleanup: after commit/push and remote/local hash equality, only the exact
  audited `rollouts/` subtree (`29,484,012,604` bytes) and exact interrupted
  runtime workspace (`263,600,858` bytes) were irreversibly removed. Free
  server space became `141,796,622,336` bytes; compact evidence remains.

## R_geo/Z_geo 1 ms ID-2Z3 bounded braking rolling search

- Date: 2026-08-19 Asia/Shanghai.
- Status: prospectively frozen design; implementation, server validation and
  TSC not yet run.
- Initial logical prefix: ID-2Z2 selected Round-B state 77, excluding its
  four look-ahead hold states.
- Budget: at most five decisions, 15 canonical-source branches, 1,455 plant
  advances, 1,470 states and 90 GB estimated raw.
- Candidate alphabet: matched hold, p03-forward4 and p07-minus4.  Each branch
  has four active issues plus eight hold issues.
- Selection: minimum terminal four-state maximum R/Z speed subject to paired
  response, Ip and matched-hold geometry gates.
- Coarse stabilization discriminator: four terminal states within 25 mm
  source R/Z distance, 0.1 m/s step speed and 5% source-relative Ip.  This is
  not the historical 5-mm short-hold or a recoverable set.
- Storage cleanup: after tracked/pushed compact and independent evidence was
  hash-verified, only the completed ID-2Z1 and ID-2Z2 remote `rollouts`
  subtrees were irreversibly deleted (30,978,808,884 and 66,979,955,014
  bytes).  Their top-level results, compact evidence, audits, preflights and
  logs remain.  Free space after cleanup: 157,094,965,248 bytes.

## R_geo/Z_geo 1 ms ID-2Z2 two-decision rolling branch

- Date: 2026-08-19 Asia/Shanghai.
- Physical source revision:
  `b7fcce9513e7284503b45bd1f3e730037cbc11ef`; reporting/recovery revision
  `0cd4a84f318ce66edfe0ab09cdbde23adf2eacb9`.
- Server output:
  `rgeo_zgeo_1ms_id2z2_20260819_b7fcce95`.
- Installed repair validation: 13/13 focused and 408/408 complete one-ms
  tests.
- Execution: 14/14 branches, 1,106/1,106 attempted/`gotsc`/verified
  advances, 1,120 retained states.
- Required raw inventory: 5,600 files / 65,960,074,880 bytes / digest
  `fa93bf54b958b6032c7f6741529b6fe0f7b43fc73bd04eaef184096e631e0059`.
- Primary / final independent SHA-256:
  `15753e20d6e615591e26968f9555c29202ddb780a633c1b229b4bdd7292048d6 /`
  `c9b640c8b25df85150b9b40b9f906ae5eb9fdb7836f37805fe84506e83cb0c51`.
- The first complete `r0__hold` raw was compacted after a missing-horizon
  reporting repair and never replayed; the initial failed reporting audit is
  retained as `db3dc60a044d776d39ac772ecf7f4b6a9dbbfbe7950b7d5c9a49344d238550c3`.
- Both rounds nominated p03-forward4 and p07-minus4. The selected sequence is
  `p03forward4 -> p03forward4`; Round-B terminal improvement is 0.871520 mm
  with 144.760 A maximum paired Ip.
- Final route:
  `ONE_MS_ID2Z2_TWO_DECISION_ROLLING_BRANCH_PASS_HOLD_CONTROLLER_DESIGN_ONLY`.
- Status: finite repeated transport decision PASS only. The selected state81
  path remains 24.349695 mm from source and is still moving near 0.39 m/s;
  bounded rolling braking/hold design is next.

## R_geo/Z_geo 1 ms ID-2L1 structured history model comparison

- Date: 2026-08-17 Asia/Shanghai.
- Model revision:
  `a6d509b52ed78b554317e11e05c16585129cbd3f`; reporting-only launcher
  follow-up `1fe0a3eb`.
- Server tests: 10/10 focused and 203/203 complete one-ms tests.
- Output directory: `rgeo_zgeo_1ms_id2l1_model_a6d509b5`.
- Primary / independent full-refit SHA-256:
  `af67b3915afead8c5df2846982c90c4b41ef17aa448a0904b48e24157e7969fd /`
  `52a5f8aedaad5a8347b0b9fca9d112c9b482f418b6e9585b563511017034176b`.
- Twenty fold models, zero TSC/reset/plant advances, zero calibration or
  holdout reads; independent maximum numeric difference `0.0`.
- Best candidate `stable_signed_even`: mean response NRMSE `0.602347`, peak
  direction `32/32`, response/free gates PASS; 1 ms and composite-history
  2 ms absolute R recenter gates FAIL.
- Contextual mean NRMSE `7.257824`; GRU residual `1.812266`; no model artifact
  emitted.
- Final route: `ONE_MS_ID2L1_STRUCTURED_MODEL_FAIL_ROUTE_REVIEW`.
- Next recommendation: zero-fit ID-2M0 per-event nominal/innovation
  attribution; no automatic new TSC or larger model.
- Cleanup: exact ID-2K1 server `rollouts` subtree (90,028,813,364 bytes)
  removed after compact/raw-audit/model evidence was preserved. Top-level
  compact/result/audit remain.

## R_geo/Z_geo 1 ms ID-2K1 factorized history/sign development

- Date: 2026-08-17 Asia/Shanghai.
- Implementation revision:
  `8416bd6c5dd59e6b01c493aa58bf4b48a4c1433c`.
- Server directory:
  `rgeo_zgeo_1ms_id2k1_runs_20260817_8416bd6c`.
- Execution: 43/43 rollouts, 40 unique cells, 1,462/1,462 verified advances,
  1,505 retained states, eight whole-history groups and 32 probe cells.
- Required raw inventory: 7,525 files / 88,633,850,620 bytes / digest
  `97ba08db00d12bc604396b32dbd794d3c415d7549b3402ce59d06c78fba9f158`.
- Primary / independent raw SHA-256:
  `a7a5f64a86118dd5002b9da44f7cf5e126571f30d6e6ef3d3005b369eb4e6643 /`
  `69911aaa5d16b7f52381b0f7d211d51b0eee6377a11830dd00812e7183af8444`.
- All matched-prefix, critical-replay, signal and Ip gates passed. Peak paired
  R/Z norm was `0.128188--0.690277 mm`; maximum paired Ip was `50.1590 A`.
- Final route:
  `ONE_MS_ID2K1_FACTORIZED_HISTORY_SIGN_DATA_PASS_STRUCTURED_MODEL_ONLY`.
- Status: development data PASS only. ID-2L1 structured whole-history model
  comparison is authorized; calibration, holdout, controller and safety work
  are not.

## R_geo/Z_geo 1 ms ID-2B1 final structured model result

- Date: 2026-08-15 Asia/Shanghai.
- Implementation revision:
  `1e223619e2f6ac9685012665502a924744bd9bcd`.
- Server validation: 7/7 focused and 116/116 all one-ms tests; log SHA-256
  `208cc4924535551a2bd971bd1388242376ad76d28da034f4be1832a0bb18dcbb /
  e1924e9a5c7187195ba863e04ec67e12f839a52adf23a5d8a0e802470fb7e87d`.
- Output directory: `rgeo_zgeo_1ms_id2b1_model_1e223619`.
- Primary / model artifact / independent SHA-256:
  `20441c50e20bcd4fb25c498904ebc35d5337b5cc067a3f16fac1d6383d9e2984 /
  ae79b79e64b13b0db248ffad7f8017a62875b842b32a179c9cba2dc70dca2379 /
  ef38f236f2dfa93f5ccb9a9aa6d73d669a7c94e14abcf2a9398a4e170a77be01`.
- Independent deterministic refit passed with maximum metric and artifact
  differences zero. Twelve fold models were fit; zero TSC, plant advances,
  calibration records and holdout records were used.
- Best diagnostic `stable_exp_signed`: paired-response improvement
  `+43.0%/+44.3%/-32.3%` for late-q0/p04-arrival/p03-arrival folds; direction
  fractions `5/6, 5/6, 1/4`. No candidate passed all folds.
- Final route:
  `ONE_MS_ID2B1_NO_CONTEXT_ROBUST_ACTION_MODEL_TARGETED_DATA_REQUIRED`.
- Status: clean model/support FAIL. Context-bridge design review required;
  no automatic new TSC or larger neural model.

## R_geo/Z_geo 1 ms ID-2B1 structured model development

- Date: 2026-08-15 Asia/Shanghai.
- Identity: `rgeo-zgeo-1ms-id2b1-structured-model-development-v1`.
- Source ID-2B0 result / independent SHA-256:
  `2a3211b601bdfffba232b1d4c6f95350b8824e3037f57c7ba7de17db0174eec7 /
  99d40de6fc9b45fd945e14e3bab43e895e1bc30e4d0c97ba012f2c3128009868`.
- Config / design SHA-256:
  `de37d8f84eab8acf9eda018336d0c31e74d7f1e7e7100800d54091acd7efe112 /
  270d1c6ce096c0746e9347d25bb7826b8da4a262d38bada49ff1190817ee4eb9`.
- Data: 39 uniquely weighted ID-2A development cells in three complete LOCO
  context folds; three exact critical replays remain integrity-only.
- Models: persistence, damped last velocity, action-blind history and three
  fixed-pole stable lifted action models. No neural residual in this stage.
- Evaluation: absolute rolling finite-horizon R/Z/Ip plus evaluator-only
  matched-baseline action response. Future readback/baseline leakage forbidden.
- Status: design frozen; implementation/server fit pending. Zero new TSC.

## R_geo/Z_geo 1 ms ID-2B0 model-readiness audit

- Date: 2026-08-15 Asia/Shanghai.
- Active identity: `rgeo-zgeo-1ms-id2b0-model-readiness-audit-v1`.
- Source: immutable ID-2A server run
  `rgeo_zgeo_1ms_id2a_runs_20260815_d25ee2a9` at implementation revision
  `d25ee2a9e6112f9da25014b5349888298e1bd500`.
- ID-2A result: 42/42 rollouts, 1,344/1,344 verified advances, 1,386 states,
  6,930 artifacts and final route
  `ONE_MS_ID2A_DURATION_HISTORY_DEVELOPMENT_PASS_MODEL_FIT_ONLY`.
- ID-2A primary / independent SHA-256:
  `163080f641a5063b965738b20d233e77e1c29861643f12aca2788548abf0fe1a /
  b9655ecfae6993b1802b14ebaf4ebc6d54185435379f00a834a4802cade3fe31`.
- ID-2B v1 is preserved as an unexecuted superseded design checkpoint; no
  model fit or training has occurred.
- ID-2B0 counters are frozen at zero TSC, zero plant advances, zero model fit
  and zero holdout reads. It reparses ID-2A raw read-only and writes a new
  compact audit identity only.
- Design:
  `docs/codex/reports/RGEO_ZGEO_1MS_ID2B0_MODEL_READINESS_AUDIT_DESIGN.md`.
- Config / design SHA-256:
  `7294f89182e709ec0e52fc2ac0be1192ef4473bc521ee87539f98297cad3b6b6 /
  e8cea2321808deb01d3bd94ebbb6a9eda07af79fd9df388d7d7602ea0eaee166`.
- Initial implementation revision `f0c3876f7f95a91180cb74f3e1eacde94e611e51`
  stopped before raw readiness analysis because the locally transcribed
  independent-audit SHA had one wrong nibble (`...eba4e...` rather than the
  server file's `...ebaf4...`). The preserved route is
  `ONE_MS_ID2B0_INPUT_OR_RAW_INTEGRITY_FAIL_STOP`; counters are zero TSC,
  zero plant advances, zero model fits and zero holdout reads. Direct server
  SHA-256 and JSON parsing confirmed the source independent audit has
  `audit_passed=true` and 1,386 reparsed states. The corrected hashes above
  are an input/authentication-only hotfix; no scientific contract changed.
- Valid execution revision:
  `7ffc89e8f80525b80d91ab6740237f40d95c0ad7`; output directory
  `rgeo_zgeo_1ms_id2b0_readiness_7ffc89e8_verified`.
- Server focused tests passed 5/5 and all one-ms regression tests passed
  109/109. Validation/regression log SHA-256 values are
  `306a56132cc80f155f654ad07fe3d1744eb6377d11d3707c90456b110ce45296 /
  0c00ad2060e3b8d4cb2170a9b224b431eacd01f0dc53819df67bb4fc036be48f`.
- Final primary / independent SHA-256:
  `2a3211b601bdfffba232b1d4c6f95350b8824e3037f57c7ba7de17db0174eec7 /
  99d40de6fc9b45fd945e14e3bab43e895e1bc30e4d0c97ba012f2c3128009868`.
  Both route to `ONE_MS_ID2B0_READINESS_COMPLETE_ID2B1_REDESIGN_REQUIRED`;
  independent reparse covered 42 rollouts/1,386 states and maximum metric
  difference was zero. Counters remained zero TSC, plant, fit and holdout.
- An accidentally launched result using a non-Git 40-character revision was
  terminated before independent audit and is invalid evidence. It is kept in
  `rgeo_zgeo_1ms_id2b0_readiness_7ffc89e8` and is not used by ID-2B1.
- Status: final readiness PASS; only ID-2B1 structured development unlocked.

## Stage4.2R3c3T13S24D1R14R8R8 prospective causal discrete-pulse MPC core

- Date: 2026-08-07 Asia/Shanghai.
- Frozen before any implementation, offline candidate result, controller
  decision, formal outcome, raw trajectory, or TSC plant advance.
- Matrix: conditional 16 fresh authentic trajectories over the accepted R8R7
  baseline contexts; four causal online decisions per trajectory.
- Optimizer: exhaustive zero plus four canonical directions by two signs at
  scale 1.0; four-step static-observer plus response forecast; fixed robust
  quadratic score and 0.5% improvement threshold.
- Execution: first exact Card15 pulse only, exact stored-center cancellation
  at the next task step, then replan from actual causal history.
- Offline gate: dual-audited 576 forecasts/scores, 64 selections, and 512 pure
  issue/cancellation constructions before TSC.
- Core acceptance: every hard execution/integrity/safety gate and unchanged
  formal tracking `16/16`.
- Boundary: even PASS authorizes only separately frozen finite robustness
  qualification; no Gate A or learning claim. All R8R8 trajectories are
  forbidden from expert and learning datasets.
- Design:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R8_CAUSAL_DISCRETE_PULSE_RECEDING_HORIZON_MPC_CORE_DESIGN.md`.
- Design SHA-256:
  `0906ca9e58126cc2f414f167a685e766d95790ec4f3d28052debb4b5e6db0244`.
- Design / implementation checkpoints: `e61ee72 / 7e1dc89`.
- Local validation: project-venv compile and focused `10/10`; complete unittest
  with the existing Windows `resource` shim `1229/1229`, zero failures/errors/
  skips. No offline result, controller decision, raw, or TSC plant advance yet.
- Package `9179c9a` passed empty-copy, staging, and installed checks. Its first
  offline invocation stopped before stage creation because the authenticator
  expected R8R7 state `"finished"`; immutable raw evidence says `"complete"`.
  No R8R8 raw, decision, or TSC advance occurred, and the empty v1 run root is
  preserved.
- Authentication-only hotfix `2b287cb` corrects that field and adds independent
  source/hash/raw-inventory authentication. Local focused/full validation is
  `11/11 / 1230/1230`; repackaging and a separately named v2 offline attempt
  are required.

## Stage4.2R3c3T13S24D1R14R8R7 final fresh multipulse interaction result

- Design / implementation / execution package: `6287ff6 / a1a60a9 /
  d8d231e`; inventory-reporting fix / runtime hotfix: `a39c5a9 / 4a8b558`.
- Final forensic / audited-package checkpoints: `dbfe40f / 1463342`.
- Final package declared / direct-copy total: `996 / 998`; manifest / sums
  SHA-256: `0c4b289d45fe851d90209a7de122cf010ee8fadcc95f5bb5d76799fbcbe32cdb /
  efe7be132c64e6fb01155d26ed9b8e41e454e77d08a5d85a2c3f55d70f9bb40e`.
- Final local / staging / installed full tests: `1219/1219 / 1219/1219 /
  1219/1219`; one expected server skip. Staging and installed validation log
  SHA-256: `82da01c3158c127f7860cfae2abae3ca870b573e53ee29a4c0cabb8035cf89b6 /
  6105122cf8862526366d0182931a05f9121ee0373997f27d08e07ffd9c36e720`.
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r8r7_runs/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel_20260807_d8d231e_v1`.
- Valid authentic raw: baseline `16/16`, multipulse `32/32`; exact issues /
  cancellations `128/128 / 128/128`; zero forbidden traces.
- Raw inventories: baseline `16 / 487298 /
  46df626a462dfdbfe7cdf9138a50b6b19c03f0ae5e8bb18cf18c6fcbe05c01a5`;
  multipulse `32 / 1068664 /
  d8435c8cd61fd082e143d79a3628ad2274780faefc6b676367df917355f49e31`.
- Frozen point/tube gates: baseline `64/64 / 64/64`; multipulse
  `128/128 / 128/128`; all context, direction, sign, and exclusion gates
  passed.
- Independent raw inventory, numerical, outcome, route, and artifact hashes
  agree exactly with primary.
- Formal tracking diagnostic only: baseline `6/16`, multipulse `12/32`.
- Final route:
  `FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_PASS_MPC_DESIGN_REQUIRED`.
- Classification: finite fresh-interaction model PASS; no MPC, Gate A,
  expert-data, or learning conclusion. All R8R7 trajectories are forbidden
  from expert and learning datasets.
- Report:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R7_FORENSIC_REPORT.md`.

## Stage4.2R3c3T13S24D1R14R8R7 pre-action runtime hotfix

- Phase-one baseline: authentic raw `16/16`; static observer point/tube
  `64/64 / 64/64`; all 16 contexts `4/4`; primary/independent agreement.
- Independent inventory reporting fix: `a39c5a9`; no raw/model/gate change.
- First multipulse attempt: 32 raw files, 145407 bytes, digest
  `7cadf53a6870980802009eef71e3d7c8e5c2707eb446d85f125851e239af160d`.
- All 32: one reset state, zero trace/action/event/plant advance; common
  inherited-constructor exception before controller creation.
- Runtime hotfix: `4a8b558`; inherited compatibility placeholder only, live
  R8R7 clock and every frozen scientific/safety semantic unchanged.
- Classification: implementation plus reporting error; no multipulse model,
  controller, plant, MPC, or reachability result yet.
- Continuation: authenticate/preserve failed raw, server-validate the hotfix,
  and rerun exactly the same 32 frozen specs once under the existing identity.
- Audit:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R7_MULTIPULSE_RUNTIME_HOTFIX_AUDIT.md`.

## Stage4.2R3c3T13S24D1R14R8R7 prospective fresh multipulse interaction sentinel

- Date: 2026-08-07 Asia/Shanghai.
- Identity: frozen before any R8R7 implementation, derived metric, artifact,
  raw result, or TSC trajectory.
- Matrix: conditional maximum 48 authentic trajectories: 16 fresh baselines,
  then 32 fixed four-pulse interactions over 16 response-unopened contexts.
- Predictor: byte-authenticated R8R6 static observer plus fixed R8R1
  PCA4/RBF2/ridge0.1 40 ms response deployment fit; adaptation disabled.
- Boundary: a PASS may authorize only a separately frozen MPC design; no Gate
  A or learning claim, and all R8R7 trajectories are forbidden from
  expert/BC/DAgger/RL data.
- Design:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R7_FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_SENTINEL_DESIGN.md`.
- Design SHA-256:
  `a2d2abda8189ff475455ae945391948ede937ba49ab559d79f1c48c74e80067f`.

## Stage4.2R3c3T13S24D1R14R8R6 final causal innovation observer

- Design / implementation / package: `0352207 / df2e8c4 / 6b00e24`.
- Package declared / direct-copy total: `980 / 982`.
- Local / installed full tests: `1208 / 1208`; one expected server skip.
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r8r6_audits/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer_20260807_6b00e24_v1`.
- New TSC / raw / source modification: `0 / 0 / false`.
- Startup / adapted point / adapted issue / tube:
  `40/40 / 560/560 / 120/120 / 560/560`; context gates `40/40`.
- Tube maximum `[R,Z,vR,vZ,Ip]`:
  `[0.0032254596,0.0033520607,0.0386971126,0.0443856721,117.0384656]`.
- Adapted/cold MSE ratio: `1.0781373396` versus required `<=0.95`;
  improved contexts `8/40`, context-regression-limit passes `12/40`.
- Independent numerical/outcome/artifact agreement: all true.
- Final route:
  `CAUSAL_ONE_STEP_INNOVATION_NO_MEASURABLE_GAIN_STATIC_ROBUST_OBSERVER_SENTINEL_REQUIRED`.
- Classification: observer qualification PASS, adaptation usefulness FAIL;
  select static observer. No controller, MPC, formal-control, plant, Gate A,
  or learning conclusion.
- Report:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R6_FORENSIC_REPORT.md`,
  SHA-256 `cf948786db23de51a5f30a8407cee30d06e8ddf1cafe4476f0c45a78c6a7eeea`.

## Stage4.2R3c3T13S24D1R14R8R5 prospective context-robust holdout

- Frozen before any R8R5 fit, tube value, metric, artifact, route, TSC, or
  holdout outcome on 2026-08-07.
- Design:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R5_CONTEXT_ROBUST_OBSERVER_HOLDOUT_DESIGN.md`
- Design SHA-256:
  `c7b5d570a6d74b39368e4ee4ef677f84a7a81b469a000515ea843e2797622daa`
- Consumed development: twelve R8 training pairs plus four R8R4 development
  pairs; zero new development TSC.
- Fixed point model: linear, PCA rank 32, ridge 1e-6.
- Tube: one global 1.25-reserved scalar enforcing aggregate q95 and every
  context q90 calibration; unchanged finite caps.
- Blind boundary: eight unopened histories may run only after primary/
  independent development and model/tube hash freeze.
- Learning boundary: all data forbidden; even PASS authorizes only separately
  frozen combined adaptation.

## Stage4.2R3c3T13S24D1R14R8R4 final fresh observer result

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation / execution package / accepted audit package:
  `5083686 / 3c12aa3 / a1fdee3 / 7810525`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r8r4_runs/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification_20260807_a1fdee3_v1`
- Development raw: `8/8`, 245279 bytes, digest
  `8d0d6c2c8f7e4e8436f9ef958fb30e4276823a8004fbab97b8c50d71b1ed3f66`.
- Point gate: `480/480` origins and `128/128` issue origins; zero exclusion
  violations; maximum scaled error `0.12737875204525517`.
- Tube: `457/480` aggregate against 456 required, caps PASS, but only `27/32`
  contexts passed their 90% floor.
- Holdout raw / model files: `0 / 0`.
- Primary detailed / summary / independent / final state SHA-256:
  `af8cb6d75a435ecd96948b4c15a2e1929c98527edd5483c8f29c0c6394125dac`,
  `bde614d6ac34535d5f22f187925723969921e8333b41d429a32e0719cb8b3bfd`,
  `12ee920fb0d49d46285bba31a443a24e09a5b6b9b3b1d0b5ddc61560a20fa86b`,
  `617c6ea2e2ae81d5d1ad9f0de2f331a1b0d19caa3031dc76e4714ecc4c417015`.
- Route: `FRESH_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT`.
- Classification: finite uncertainty-calibration/design FAIL; no runtime,
  restart, raw, controller, formal-control, MPC, plant, or reachability
  conclusion.
- Report:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R4_FORENSIC_REPORT.md`.

## Stage4.2R3c3T13S24D1R14R8R4 prospective fresh observer design

- Frozen before implementation, fitting, metrics, or TSC on 2026-08-07.
- Design:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R4_FRESH_CAUSAL_OBSERVER_IDENTIFICATION_DESIGN.md`
- Design SHA-256:
  `942b7698e9d19ee905d75dc7ee9fda370e642e9e986298af32d8f17ed22f8119`
- Scope: eight fresh baseline-only development trajectories, then a frozen
  dual-audited observer/tube, then eight whole-pair blind holdout trajectories.
- Safety/formal boundary: unchanged restart, causality, Card15, current,
  integrity, 250/270 ms arrival, and 350/370 ms hold contracts.
- Learning boundary: every trajectory forbidden from expert data; a PASS can
  authorize only a separately frozen combined adaptation validation.
- Status: design frozen; zero R8R4 TSC/plant advances; implementation pending.

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

## Stage4.2R3c3T13S4 offline lattice holdout preflight

- Frozen design commit: `5c14577`
- Implementation/package checkpoints: `1762862`, `586cc8a`
- Final offline aggregation commits: `ec5410b`, `21df2dc`
- Package revision: `r42r3c3t13s4_lattice_transition_holdout_v1h2`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s4_runs/stage4_2r3c3t13s4_lattice_transition_holdout_20260801_21df2dc`
- Route: `LATTICE_PREFLIGHT_FAIL_NO_REAL_TSC`
- Offline specs/pass/fail: `52 / 11 / 41`
- Failure phase: issue `40`, exact cancellation `1`
- Raw / plant / Ray / gotsc / TSC: `0 / 0 / 0 / 0 / 0`
- Audit SHA-256:
  `1e60d04dfc7a9b5a26558aff9bee3cfd40ece0f1deed95988b592b0af8a8e6d2`
- Installed validation: `664/664`, one expected skip; log SHA-256
  `1bbc3aa354e0b6ed2f611c4633af675d3705965f8e020773781cb3f9f870d01b`
- Classification: frozen prospective identification-design failure; two
  semantics-neutral offline aggregation/report defects repaired; no runtime,
  deployment, restart, raw, plant-control, or real-MPC result
- T13S5 zero-TSC route audit: split mode-0 plus modes 1/2, return-first hybrid
  cancellation, `8/8`, maximum input condition `7.9547833`, SHA-256
  `378ff7d945a10b4d5c544460ed733cdbe0c25004d07b651af9f03a5c1f5a478b`
- Next: implement and validate the separately frozen 68-rollout T13S5
  lattice-native split-direction holdout; all expert/RL routes remain blocked

## Stage4.2R3c3T13S12 causal natural-history observer preflight

- Branch: `codex/stage4_2r3c3t13s1-transition-sentinel`
- Initial implementation / target hotfix: `3eda0cb` / `d2940b3`
- Execution: zero-new-TSC server-side raw audit
- Final remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s12_audits/stage4_2r3c3t13s12_causal_natural_history_observer_20260802_d2940b3m1`
- Source raw: q1 68 / 3,610,295 bytes, q2 68 / 3,610,097 bytes
- Source raw digests: `9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad`,
  `09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01`
- Final audit/log SHA-256: `1ccaaea1f8da5b5271331758a0a390c5dc663f98c5099299ff3a440007b94b4a`,
  `42b2b4e295e731a04c6142e69f87d9efe095e5244b7439ca8288e85bc1c36b0e`
- Counts: history 8/8, extraction/causality 64/64, support 64/64,
  containment 61/64, error 44/64, both 41/64
- Maximum condition / error: `1.000000000000045` / `1.701539079`
- Route:
  `CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_INSUFFICIENT_NONLINEAR_OBSERVER_REDESIGN`
- Known incidents: one target-payload schema implementation error and one
  direct-file module-path launcher error; each stopped before result and ran
  zero TSC/plant steps. Final output has no runtime or reporting error.
- Compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s12_result_20260802_d2940b3/`
- Classification: finite affine observer/model design failure; no controller,
  MPC, expert data, BC, DAgger, or RL authorization
- Next: prospectively freeze broader same-trajectory causal sequence
  identification and recurrent/nonlinear set-valued observer holdout
## Stage4.2R3c3T13S16 orthogonal fixed-basis identification

- Branch: `codex/stage4_2r3c3t13s16-whitened-basis`
- Design / implementation commits: `8118d9a`, `8487951`
- Package revision: `r42r3c3t13s16_orthogonal_fixed_basis_identification_v1`
- Package digest: `9437a6b09945da5ee843def84b614ce8f7f81d1082e02ed18a629add6e70f461`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s16_runs/stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_165232`
- Remote baseline / response logs:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_165521.log`,
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_170802.log`
- Fresh execution: 16 baselines followed by 128 probes; expected/actual raw
  `144/144`
- Raw bytes / digest: `8,188,964` /
  `b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668`
- Exact restart, causality, Card15, zero-net, current, parse, and independent
  report recomputation: `144/144`
- Center / tube containment / tube cap / all model gates:
  `120/128`, `82/128`, `40/128`, `14/128`
- Result:
  `ORTHOGONAL_FIXED_BASIS_IDENTIFICATION_FAIL_BELIEF_MPC_REDESIGN`
- Known bugs: none in the final execution or report.  One oversized read-only
  SSH hash command was reset; smaller command packets reconnected and changed
  no server state.
- Large raw/snapshots remain server-side; compact evidence hashes are in
  `docs/codex/reports/STAGE4_2R3C3T13S16_FORENSIC_REPORT.md`
- Classification: finite local response/tube design failure; no runtime,
  deployment, restart, raw, reporting, real-MPC, or plant-unreachability
  failure
- Next: zero-new-TSC S17 causal multi-drift belief preflight; a pass can only
  authorize a fresh whole-pair identification campaign

## Stage4.2R3c3T13S17 causal multi-drift belief preflight

- Branch: `codex/stage4_2r3c3t13s16-whitened-basis`
- Design / implementation / verification-hotfix commits: `be9c316`,
  `65e00c3`, `0f9ef6b`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s17_audits/stage4_2r3c3t13s17_causal_multi_drift_belief_preflight_20260803_0f9ef6b`
- Source raw count / bytes / digest: `144` / `8,188,964` /
  `b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668`
- New raw / snapshots / TSC / plant steps: `0 / 0 / 0 / 0`
- Hypothesis rows / maximum condition: `384/384` / `3.1980986512`
- Containment / cap / joint: `128/128`, `0/128`, `0/128`
- Maximum belief halfwidth:
  `(0.0021893899 m, 0.0035035150 m, 0.1402725944 m/s,
  0.1148451016 m/s, 569.3096777 A)`
- Route:
  `CAUSAL_MULTI_DRIFT_BELIEF_PREFLIGHT_FAIL_ROBUST_OBSERVER_REDESIGN`
- Compact primary hashes: belief
  `d8c8ee8f0c3f2e80cb1642c7f6400f47d5280e47459361dfa274421c37fdca76`,
  final `98afee17ff682326853e7caa708264186c87ccf88bec92ddf2cd3275855b9a69`,
  independent
  `a59355266f94f2013b07a5b58c0857ee3925e9ebcd6c1147a6e2affd4f728326`
- Known incident: package verifier incorrectly scanned historical remote
  `.codex_tmp` JSON-like files; manifest-scoped hotfix changed no scientific
  semantics and final validation passed 379/379 plus 802 tests (one skip)
- Classification: robust-observer residual-set design failure; no runtime,
  restart, raw, final-reporting, controller, real-MPC, or reachability failure
- Next: zero-new-TSC S18 fixed pooled causal observer preflight; only a pass
  may authorize a separately frozen fresh whole-pair campaign

## Stage4.2R3c3T13S18 pooled causal observer preflight

- Branch: `codex/stage4_2r3c3t13s16-whitened-basis`
- Implementation/package checkpoints: `e940fc8`, `d178001`
- Exact Card15 reconstruction fixes: `fa76af1`, `fba9144`
- Final batch-evaluation consistency fix: `960ac1e`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s18_audits/stage4_2r3c3t13s18_pooled_causal_observer_preflight_20260803_fba9144`
- Source raw count / bytes / digest: `144` / `8,188,964` /
  `b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668`
- New raw / snapshots / TSC / plant steps: `0 / 0 / 0 / 0`
- Outer folds / held rows / response rows: `8 / 16 each / 128`
- Containment / cap / joint: `128/128`, `128/128`, `128/128`
- Maximum scaled point error: `0.0010531744`
- Artifact / final / independent hashes:
  `a7f35260e18894da763adba557b5c93ff599e2e4d81d94e4dd43e4824c9a5518`,
  `12817946f1a1dee8557798f0e98a281e9015cfd7c26c07e4ca537729047836fb`,
  `09f7377887f3a42a707456dc8ed8bafc21faddacae7034c3a412a7b297f7dc9c`
- Route: `POOLED_CAUSAL_OBSERVER_PREFLIGHT_PASS_FRESH_CAMPAIGN_REQUIRED`
- Incidents: exact Card15 interval reconstruction and batch-versus-single-row
  BLAS consistency bugs; both stopped before TSC and changed no scientific
  semantics.  One foreground resume SSH session reset before server execution.
- Classification: consumed-development architecture PASS only; no independent
  observer, controller, MPC, continuous-parameter, noise, disturbance,
  long-hold, expert-data, BC, DAgger, or RL validation
- Next: prospectively frozen 360-rollout S19 with 12/4/4 whole-pair
  training/calibration/fresh holdout and strict phase-boundary artifact hashes

## Stage4.2R3c3T13S20 dynamic-exact Card15 pooled observer campaign

- Branch: `codex/stage4_2r3c3t13s21-cumulative-closure`
- Implementation / S19-authentication hotfix commits: `1861dbd`, `9113198`
- Package revision:
  `r42r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_v2`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s20_runs/stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_20260803_9113198`
- Fresh execution: expected full matrix 360; actual training baselines 24 raw,
  23 complete successes and one structured failure; later phases zero raw
- Raw bytes / digest: `1,342,538` /
  `d78ba9a01e54611c7489bc13ae70883b2020a5647473976e6ca29c9c2f22de52`
- Independent successful-baseline audit: runtime/restart/causality/action/
  exact-net `23/23`; successful-context zero-plant probe replay `184/184`;
  snapshot inventory `40/40`
- Failed experiment: `s42r3c3_a40f88ad021de4a85a93`, stopped before
  eighth plant advance because the planned net retained coil-8 `+0.0004 kAt`
- Enhanced zero-plant forensic: cumulative inverse representable `14/14`,
  primary `1.0`, cross `0.025`, cosine `0.9999973274`, action/current PASS
- Compact audit hashes: final-net
  `64c018a839492bc80e92ffecd3db41eba4375f2f937e92dee0694362f1cce364`,
  full forensic v2
  `8a94fa842ab49a466ef3bbce07e248adb582f5abd461dca56a7bc81a1d39f890`
- Known bugs: independent nearest-event quantization does not guarantee the
  frozen global exact-zero net; terminal `phase_status` remains stale. The
  former changes physical action and forbids S20 resume; the latter is
  reporting-only.
- Classification:
  `DYNAMIC_EXACT_CARD15_CALIBRATION_SEQUENCE_DESIGN_FAIL_NEW_IDENTITY_REQUIRED`;
  no runtime, restart, raw, observer, MPC, control, or plant failure
- Large raw/snapshots remain server-side; compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s20_result_20260803_9113198/`
- Next: implement the separately frozen S21 cumulative-exact step-7 closure
  under a new identity; all expert/BC/DAgger/RL gates remain closed

## Stage4.2R3c3T13S24D1R1 geometry-restoring amplitude search

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation / package checkpoints: `bd74e6d`, `70be4b2`,
  `8486837`
- Package revision:
  `r42r3c3t13s24d1r1_geometry_restoring_amplitude_search_v1`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r1_audits/stage4_2r3c3t13s24d1r1_geometry_restoring_search_20260803_145327`
- Remote log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s24d1r1_offline_20260803_145327.log`
- Fresh/resume: fresh zero-TSC offline audit
- Source raw authenticated / new raw: `360 / 0`
- Selected amplitudes: `++--=0.290`, `+--+=0.360`
- Issue/cancel/finite/central gates: `3840/3840`, `3840/3840`,
  `7680/7680`, `1280/1280`
- Selected unique sentinel specs: `54/54`
- Detailed / summary / sentinel / manifest hashes:
  `81168e646f2b40e443fa85f535193474651eb899ac8a74e1c9cd282b4f66ff98`,
  `0ec97157184ba85c70507adcc9978f9c2f87afbaa462af58152bccc008e145a0`,
  `61574900383ae91083173065561ea8f2a80a96a4c6935f3a965ef7ce43215c46`,
  `d6f42befe92b170226ea19f73bebbe8623191debde756b61500d6daa22ea7b9f`
- Route:
  `GEOMETRY_RESTORING_AMPLITUDE_SEARCH_PASS_REAL_SENTINEL_REQUIRED`
- Known defect: metadata-only hard-coded `s24d2/contracted` tokens in several
  future identity labels; no scientific field changed and no sentinel ran
- Classification: finite static construction PASS only; no plant, restart
  control, model, MPC, expert-data, BC, DAgger, or RL evidence
- Next: freeze D1R2 identity-only normalization and run the exact 54-case
  fresh real-TSC safety sentinel with the additional 0.24 cancellation margin

## Stage4.2R3c3T13S24D1R14R1A quantization-margin preflight

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation / package checkpoints: design frozen before
  implementation, `58912e7`, `b8040b6`
- Package revision:
  `r42r3c3t13s24d1r14r1a_quantization_margin_preflight_v1`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r1a_audits/stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight_20260804_b8040b6_v1`
- Remote log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s24d1r14r1a_offline_20260804_b8040b6_v1.log`
- Fresh/resume: fresh zero-TSC fixed-candidate replay
- Source raw authenticated / new raw: `72 / 0`
- Matrix digest:
  `c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c`
- Static issue / predicted geometry gates: `64/64`, `8/8`
- Maximum off-basis / issue / current: `0.0990759019`, `0.1401851852`,
  `0.38005`
- Detailed / summary / manifest hashes:
  `a9ffc98b798d4735d7302b1ca4407dbc60266228007d82d34418a291df2b0e8d`,
  `77194861b0406257d055b5ebe0e087b9f9c8222e76600fa443de9d34e7fc682f`,
  `d6b4c53c46b8948d979d3eaee1861885f61d33ac70097a7576110361f0bafa87`
- Route:
  `QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED`
- Known limitation: online cancellation is diagnostic-only and unproved;
  no controller, plant, Ray, `gotsc`, TSC, or formal tracking ran
- Classification: finite development-selected static-construction PASS; no
  plant, controller, MPC, expert-data, BC, DAgger, or RL evidence
- Next: prospectively freeze and execute a fresh 72-case D1R14R2 authentic
  safety/geometry sentinel

## Stage4.2R3c3T13S24D1R14R2 mixed-basis authentic sentinel

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation / package checkpoints: `5f7fb80`, `e7fe6c8`,
  `ca2815a`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r2_runs/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_20260804_ca2815a_v1`
- Expected / strict raw / safety: `72 / 72 / 72`
- Raw bytes / digest: `2,254,876` /
  `c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649`
- Baseline / issue / causal cancel: `8/8`, `64/64`, `64/64`
- Runtime / restart / plant / solver / saturation / raw / reporting errors:
  all zero
- Signal / symmetry / rank / condition: `32/32`, `28/32`, `8/8`, `8/8`
- Minimum odd / maximum even-to-odd / maximum condition:
  `0.005466000000009519`, `0.8528017842241936`, `8.802962394477525`
- Final / independent hashes:
  `3df193e52ee0ce8fe72620af9f72597f58af4419c6386c37d62fb051bcefd79a`,
  `68f21e95694c607084b9cc7d39732bcda05d57a14f6f3cc4f1e78e8941e7e2df`
- Route:
  `MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED`
- Classification: genuine finite context/sign-dependent response-geometry
  design failure; no runtime, restart, action, plant-abnormality, corruption,
  reporting, control, or MPC failure
- Large raw/snapshots remain server-side; compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r2_20260804_ca2815a/`
- Next: zero-new-TSC sign-split response feasibility audit; no model, MPC,
  expert-data, BC, DAgger, or RL authorization

## Stage4.2R3c3T13S24D1R14R3 sign-split feasibility audit

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / source-hash-hotfix / final-package checkpoints: `343a516`,
  `aa3325a`, `ca49a36`
- Initial output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r3_audits/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_20260804_85012c1_v1`
- Corrected output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r3_audits/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_20260804_ca49a36_v2`
- New raw / controller / plant / Ray / gotsc / TSC: all zero
- Source raw authenticated: 72 files / 2,254,876 bytes / digest
  `c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649`
- v1 route: `SIGN_SPLIT_RESPONSE_FEASIBILITY_SOURCE_FAIL_NO_TSC`; one
  pre-existing expected-state-SHA transcription error, no raw/source change
- R2 reproduction: shared-model symmetry 28/32 FAIL, four exact failed pairs
- Sign-split signal / rank / condition: `64/64`, `16/16`, `16/16`
- Exact issue coordinate / physical-field sign pairs: `32/32`, `32/32`
- Minimum branch-direction peak / maximum condition:
  `0.005310999999896815`, `9.55784063525667`
- Corrected primary / independent hashes:
  `30755ebccee65a5bcfd08d04632368979ec1c309ac42d4a46df49b3b921cd590`,
  `f138611d56b77839bb3d87744b49eb08df4c4409947038e25b520f8d43764d90`
- Route:
  `SIGN_SPLIT_RESPONSE_FEASIBILITY_PASS_TIME_SHIFT_SENTINEL_DESIGN_REQUIRED`
- Classification: reporting/source-fingerprint hotfix followed by finite
  sign-split architecture PASS; no time-shift, model, MPC, control, expert,
  BC, DAgger, or RL evidence
- Compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r3_20260804_ca49a36/`
- Next: prospectively freeze D1R14R4 fresh authentic time-shifted sign-split
  safety/identification sentinel

## Stage4.2R3c3T13S24D1R14R4 time-shifted sign-split sentinel

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation / final-package checkpoints: `ea49eac`, `d27993b`,
  `f5b8348`
- Package fingerprint:
  `c9c6fc870618ecbefe1bf9891a6f918927c2062753e2750596d2e73ec7ecf523`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r4_runs/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_20260804_f5b8348_v1`
- Expected / actual / strict raw / safety: `200 / 200 / 200 / 200`
- Raw bytes / digest: `6,285,765` /
  `44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9`
- Baseline / issue / causal cancel: `8/8`, `192/192`, `192/192`
- Runtime / restart / plant / solver / saturation / corruption / reporting
  errors: all zero
- Signal / rank / condition / issue antipodality: `254/256`, `64/64`,
  `64/64`, `128/128`
- Minimum signal / maximum condition / maximum current utilization:
  `0.00429800000001368`, `11.570074108693706`, `0.3904`
- Failed columns: direction 0, issue step 18, both signs,
  `p9_q2_a0p750_gap4_settle4 / minus_first`
- Primary / independent hashes:
  `af9acfb9e524e6ad33799b832981ec7fb2e265ff7c1d3e78796413e83382db71`,
  `6a4eec4a660beb6a29e11e184906b8b7a737834280091f1997af74e86fbd761c`
- Route:
  `TIME_SHIFTED_SIGN_SPLIT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED`
- Classification: genuine local time/context response-signal design failure;
  no runtime, deployment, restart, action, raw, reporting, control, or MPC
  failure
- Large raw remains server-side; compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r4_20260804_f5b8348/`
- Next: zero-new-TSC global direction-0 1.5x exact safety preflight; no model,
  MPC, expert-data, BC, DAgger, or RL authorization

## Stage4.2R3c3T13S24D1R14R5 global direction-0 gain preflight

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / final implementation / final-package checkpoints: `0260c6b`,
  `e7b550a`, `a4c43bb`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r5_audits/stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight_20260804_bb829f3_v3`
- Source raw authenticated / new raw: `272 / 0`
- Static issue / exact antipodal pairs: `48/48`, `24/24`
- Maximum issue / ideal return increment: `0.17481481481481495` /
  `0.17481481481481495`
- Maximum current / off-basis residual: `0.3799` /
  `0.05794563546539851`
- Primary detailed / summary / manifest / independent hashes:
  `deb57e9c774ef792ed9f8464987e4528b69f3876a09dcd7ff4ca55ea8d9dedc9`,
  `fc9d1fded5bf63e2658ad0c8da5aca642011006edd04ae1ee8aaaec58051a213`,
  `be2b358bbe35f5fff1029f4cb94b8a1638fd7e5b2c3bb244fe51fb1de0fd0d35`,
  `306fd16a65ad44bea1972fb37f4ce316363eeff8a3834ceea8973afe1f42f3cb`
- Route:
  `GLOBAL_DIRECTION0_GAIN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED`
- Classification: finite static exact-action safety PASS; no real response,
  cancellation, model, MPC, control, expert-data, BC, DAgger, or RL result
- Large source raw and detailed row outputs remain server-side; compact
  evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r5_20260804_a4c43bb/`
- Next: frozen D1R14R6 fresh 48-probe authentic direction-0 replacement
  sentinel

## Stage4.2R3c3T13S24D1R14R6 direction-0 replacement sentinel

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design/implementation/final-package checkpoints: `307fdbb`, `f0c864a`,
  `1e62c2c`
- Package revision:
  `r42r3c3t13s24d1r14r6_direction0_replacement_v2_r1a_auth_hotfix`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r6_runs/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_20260804_1e62c2c_v2`
- Expected / actual / strict raw / safety: `48 / 48 / 48 / 48`
- Raw bytes / digest: `1,509,679` /
  `c743eff98395325e4da35a28d2e646aacffb00e678753ceb0faf4b86a64aeb83`
- Exact prefix/R4 issue state / issue / cancellation: `48/48` each
- Runtime / plant / solver / action / raw / snapshot / report errors: all
  zero
- R6 direction-0 / combined signal: `48/48`, `256/256`
- Combined rank / condition / issue antipodality: `64/64`, `64/64`,
  `128/128`
- Minimum R6 / combined signal: `0.0068060000`, `0.0051890000`
- Maximum condition / current utilization: `12.1210121871`, `0.3799`
- Primary / independent hashes:
  `5c9669818249e8146b6f63d6e50e54f482cb27e64a809fb857bdf64ed617f016`,
  `a705aa669aaafd9b6708d6915655498f3f4f443ab37683eaa5ae5a8902ae9b1f`
- Route:
  `DIRECTION0_REPLACEMENT_SENTINEL_PASS_MODEL_FIT_DESIGN_REQUIRED`
- Classification: finite authentic identification safety/geometry PASS;
  no transition-model, MPC, formal-control, expert-data, BC, DAgger, or RL
  result
- Large raw/full audit remains server-side; compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r6_20260804_1e62c2c/`
- Next: prospectively freeze a zero-new-TSC deconfounded causal response-model
  fit with whole-history held validation

## Stage4.2R3c3T13S24D1R14R7/R7R1 causal response-model development

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- R7 final package: `5a17fe0`
- R7 result: no model/output; frozen independent-lag architecture undefined
  at held weak-horizon lags 26/27; zero new raw/TSC/plant
- R7R1 design/implementation/package: `81552da / 8087a1c / 3c90f21`
- R7R1 package revision:
  `r42r3c3t13s24d1r14r7r1_continuous_lag_response_model_v1`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r7r1_audits/stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model_20260804_3c90f21_v1`
- Source raw authenticated/read in place / new raw: `320 / 0`
- Response all-gate / relative / cosine / peak-ratio / point passes:
  `150/256`, `206/256`, `161/256`, `196/256`, `256/256`
- Tube / signal / rank / condition: `PASS`, `256/256`, `64/64`, `64/64`
- Worst relative / minimum cosine / peak-ratio range:
  `2.8666592379`, `0.1899193709`, `0.1601688053--3.2735052329`
- Primary / independent SHA-256:
  `8e46e13a985ad701c8ddb5bedfa58da723fb392e0ebca40d7dc876b846c8ab03`,
  `53c23fd7f31d13bb48b87f21b1a20918e103f87e514291925acb5144d7bcd03c`
- Runtime/deployment/raw/report errors: all zero
- Controller/Ray/gotsc/TSC/plant: all zero
- Route:
  `CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_FAIL_BROADER_DECONFOUNDED_IDENTIFICATION_REQUIRED`
- Classification: genuine causal response-center model design failure; no
  control, restart, plant, or MPC conclusion
- Compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r7r1_20260804_3c90f21/`
- Next: frozen zero-new-TSC R7R2 full-history/action-conditioned nonlinear
  kernel audit over all 304 existing responses; no MPC/expert/RL authorization

## Stage4.2R3c3T13S24D1R14R7R2 action-conditioned full-history model

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design/implementation/package: `5d35db2 / bcde159 / 995d81c`
- Package files / local-staging-installed full tests:
  `898 / 1,136 / 1,136 / 1,136`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r7r2_audits/stage4_2r3c3t13s24d1r14r7r2_action_conditioned_full_history_kernel_20260804_995d81c_v1`
- Source raw authenticated/read in place / new raw: `320 / 0`
- Response all / relative / cosine / peak / point:
  `236/304`, `253/304`, `247/304`, `267/304`, `304/304`
- Tube / signal / canonical geometry / operational geometry:
  `PASS`, `304/304`, `64/64`, `64/64`
- Worst relative / minimum cosine / peak range:
  `1.5695004725`, `0.2450755612`, `0.2516766914--2.3254004095`
- Detailed / independent SHA-256:
  `0f7c801ed5138260ab7e836b898df31f2f252c9cc9b89a34353b27bc4209f84d`,
  `743fd3c06ff97ff1d4a1b32e5494658dbf1f9ec33bba99e9d5d65d9d7a7a9bb1`
- Route:
  `ACTION_CONDITIONED_FULL_HISTORY_MODEL_FAIL_NEW_IDENTIFICATION_REQUIRED`
- Classification: genuine whole-pair response-center/data-coverage failure;
  no runtime, restart, raw, report, control, plant, or real-MPC failure
- Compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r7r2_20260804_995d81c/`
- Next: prospectively frozen R8 partitioned 12-training/4-calibration/4-holdout
  broader deconfounded identification; no MPC/expert/RL authorization

## Stage4.2R3c3T13S24D1R14R8 partitioned response identification

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Final route: `PARTITIONED_BROAD_RESPONSE_TRAINING_MODEL_FAIL_STOP`
- Fresh training raw: `624/624`, 19,725,920 bytes, digest
  `b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762`
- Combined whole-pair responses / passes: `912 / 719`
- Calibration / holdout raw: `0 / 0`; model artifact absent
- Runtime/restart/causality/raw/snapshot errors: zero
- Classification: authentic finite identification completed; frozen
  response-center model/design FAIL, no controller or MPC result
- Report:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8_FORENSIC_REPORT.md`

## Stage4.2R3c3T13S24D1R14R8R1 short-horizon discriminator

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation repair / accepted package:
  `bd7acfa / ea4b404 / 892ac7c`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r8r1_runs/stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator_20260805_c2ed69f_v1`
- Source raw authenticated / new raw / plant advances: `624 / 0 / 0`
- Response passes at 4/6/8/10/12 states:
  `832/804/788/770/763` of 912
- Primary detailed / summary / accepted independent / final state hashes:
  `bd0041c3e16b56fce28abb80526bb5f1628ee74f6f5b52a70aaa07019e86a1ee`,
  `5d6c2eb4282dba1ba29e25624b147af8b760c8cfbe5fd085374cf54110de6204`,
  `3f378dba6eb1304422397b44a347e34d35827624ca6ea61791e85f16e7a5341c`,
  `3f25e7070fd56243b1581b7da17cb433e0876821437bc9e7e098cdf4626d869f`
- Local/server full tests: `1157/1157` with one expected isolated-data skip
- Route:
  `FIXED_CANDIDATE_SHORT_HORIZON_FAIL_CAUSAL_INNOVATION_REQUIRED`
- Classification: fixed cold-start short-horizon response-center design
  FAIL; no runtime, restart, causality, raw, controller, formal-control,
  real-MPC, or plant conclusion
- Compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r8r1_20260806_892ac7c/`
- Next: prospectively freeze a deployable causal online innovation/adaptation
  study; Gate A and all expert/learning stages remain blocked

## Stage4.2R3c3T13S24D1R14R8R2 causal online innovation audit

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation / package / metadata correction:
  `431f7e3 / a636583 / 3ce1e04 / c90e299`
- Installed package files / local full tests / server full tests:
  `930 / 1165 / 1165`, with one expected server isolated-data skip
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r8r2_audits/stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation_20260807_c90e299_v1`
- Baseline forecast windows / passes: `96 / 17`
- Issue-step passes at `10/14/18/22`: `0/24, 0/24, 11/24, 6/24`
- R/Z/vR/vZ/Ip cap violations: `20/31/61/72/0`
- Maximum scaled point error: `25.23346999999822`
- Update folds / selected lag / development artifact: `0 / none / absent`
- Primary detailed / summary / independent / final state hashes:
  `ad04374987ce4de599d71f4673ac110fe763928831e4c9610cdb117efd7977cf`,
  `05d761ef64c9e7c2373a6754184ecf42cf0a250d26ee235293e768c0416c0bb2`,
  `2ca90fab851c4131f7242bd9a5331286bde15ccaf47d251348b7d80a4597066c`,
  `ee06726c8a5170ffd03a9465432ceed6f42053e2db8f710442c80c7809f07670`
- New raw / Ray / gotsc / TSC / controller / plant: all zero
- Route:
  `CAUSAL_ONLINE_INNOVATION_BASELINE_FORECAST_FAIL_OBSERVER_IDENTIFICATION_REQUIRED`
- Classification: causal affine baseline-forecast/observer-design FAIL; no
  runtime, deployment, restart, raw, control, MPC, or plant conclusion
- Compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r8r2_20260807_c90e299/`
- Next: prospectively freeze a new-identity causal dynamics observer/
  identification design; Gate A and all expert/learning stages remain blocked

## Stage4.2R3c3T13S24D1R14R8R3 causal history no-action observer

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation / package: `a0fa6bf / a3148a3 / e8cea14`
- Package manifest files / clean closure: `939 / 941`
- Local / staging / installed full tests: `1176 / 1176 / 1176`, with one
  expected server isolated-data skip
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r8r3_audits/stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer_20260807_e8cea14_v1`
- Origin cap passes / prescribed issue passes: `346/360 / 89/96`
- R/Z/vR/vZ/Ip violations: `0/0/22/8/0`
- Tube cap folds / contained rows: `0/12 / 360/360`
- Primary detailed / summary / independent / state SHA-256:
  `a0db5c6db2687747ffd5de8a4a773635bfce15973e8e817eebe74a3356470a00`,
  `b8992e53a07e339015dc714377fcca57860dac3cb7b4b169d67e3623b520e364`,
  `4cb71b25ad69848349a2034fff335b9d869a56f709465be9baed6b209637f8ba`,
  `e016c0ab9ee2c7a2f4701e553733c4392f48026f648450408cca4e19df9a9bcb`
- New raw / Ray / gotsc / TSC / controller / plant: all zero
- Route:
  `CAUSAL_HISTORY_NO_ACTION_OBSERVER_FAIL_FRESH_IDENTIFICATION_REQUIRED`
- Classification: finite causal observer/model/data-coverage design FAIL; no
  runtime, deployment, control, MPC, formal-control, or plant conclusion
- Compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r8r3_20260807_e8cea14/`
- Next: prospectively freeze a fresh-identity observer-identification campaign;
  Gate A and all expert/learning stages remain blocked

## Stage4.2R3c3T13S24D1R14R8R4 fresh causal observer development

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Final route: `FRESH_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT`
- Fresh development raw: `8/8`, 245279 bytes, digest
  `8d0d6c2c8f7e4e8436f9ef958fb30e4276823a8004fbab97b8c50d71b1ed3f66`
- Point / issue / aggregate tube: `480/480 / 128/128 / 457/480`
- Context tube passes: `27/32`; holdout/model counts `0/0`
- Model candidate selected: `linear / PCA32 / ridge 1e-6`
- Primary detailed / summary / independent / final state SHA-256:
  `af8cb6d75a435ecd96948b4c15a2e1929c98527edd5483c8f29c0c6394125dac`,
  `bde614d6ac34535d5f22f187925723969921e8333b41d429a32e0719cb8b3bfd`,
  `12ee920fb0d49d46285bba31a443a24e09a5b6b9b3b1d0b5ddc61560a20fa86b`,
  `617c6ea2e2ae81d5d1ad9f0de2f331a1b0d19caa3031dc76e4714ecc4c417015`
- Classification: clean finite uncertainty-calibration/design FAIL; no
  runtime, restart, raw, controller, formal-control, real-MPC, plant, or
  reachability conclusion
- Report:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R4_FORENSIC_REPORT.md`

## Stage4.2R3c3T13S24D1R14R8R5 context-robust observer holdout

- Branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Design / implementation / package: `546c6f7 / 4f0bf06 / 26b96e8`
- Package declared / direct-copy total: `966 / 968`
- Local / installed full tests: `1198 / 1198`, one expected server skip
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r8r5_runs/stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout_20260807_26b96e8_v1`
- Development new raw / point / issue / tube:
  `0 / 480/480 / 128/128 / 480/480`
- Blind holdout execution / restart / prefix / raw: `8/8 / 8/8 / 8/8 / 8/8`
- Blind point / issue / aggregate tube: `120/120 / 32/32 / 117/120`
- Context passes: `7/8`; failed context
  `p5_q2_a0p900_gap4_settle4|plus_first = 14/16`, required `15/16`
- Raw count / bytes / digest: `8 / 245493 /
  55cae64bf5b907b4cd6013615388dbb637dd2f1f14e49bda7fb49d11cf5b3d14`
- Model / tube SHA-256:
  `d3d7ecebbe51ca20e83cdb126682d2bebad749b8fd5cb67dd57b3baf416e77e4`,
  `3a436307a507b9aacda85321dd4d55e6bbcc996efe2e25c2b5026571c7108786`
- Stage manifest / final state SHA-256:
  `d737bb77a9547fac8c1378dab3fdbd63aeca60cc30fefc38ecf5dab181d441cc`,
  `dc564ddfb9edae9b044dfa358ddb98306b56f328a8fc06c60b8c43ade772e48c`
- Final route:
  `CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN_REQUIRED`
- Classification: clean finite uncertainty-qualification design FAIL; no
  runtime, deployment, restart, causality, raw, controller, formal-control,
  real-MPC, plant, reachability, or global-observability conclusion
- Compact evidence:
  `docs/codex/audits/stage4_2r3c3t13s24d1r14r8r5_20260807_26b96e8/`
- Report:
  `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R5_FORENSIC_REPORT.md`

## Stage4.2R3c3T13S24D1R14R8R6 prospective causal innovation observer

- Frozen before implementation or metrics: design checkpoint `0352207`
- Design SHA-256:
  `6f8886f42321a2e99a97332ecf03c1827b5385ebfc50f6ee07fefefcafa182f1`
- Data boundary: 20 consumed physical pairs, 40 history contexts, 600 causal
  origin rows; zero new TSC
- Fixed adapter: causal prior one-step vR/vZ/Ip innovation, fixed physical
  clipping, `rho=0.8`, exact R/Z reintegration
- Fixed uncertainty reserve: context-robust global tube multiplier `2.0`
- Adaptation requires measurable MSE benefit; otherwise choose the static
  robust observer route
- Next: implement, independently audit, package/deploy, and execute R8R6;
  controller, MPC, Gate A, expert data, and learning remain blocked

## R_geo/Z_geo 1 ms NR2 / NR2R1 causal model qualification

- Branch: `codex/rgeo-zgeo-1ms-nr2`
- Design / implementation / NR2R1 / final correction:
  `2404e36 / 9b559ee / 25f5b7e / 45257ba`
- NR2 remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_nr2_runs/rgeo_zgeo_1ms_nr2_structural_residual_20260813_9b559ee`
- NR2 result: one safe q0 advance, then fail-closed at exact structural
  readback error `0.00001 A`; no fitting or holdout
- NR2R1 remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_nr2_runs/rgeo_zgeo_1ms_nr2r1_q0_structural_residual_20260813_25f5b7e`
- NR2R1 execution: `36/36` trajectories, `576/576` authentic plant advances
- Dev/cal independent checks: `448/448`; holdout checks: `128/128`
- Maximum command / observed step: `0.3 A / 0.3 A`
- Maximum structural current error: `1e-26 A`
- Frozen model SHA-256:
  `73dbf615911e05f14ddc0125d5dc5d3dbaf56e3085d208921fab93db8164f916`
- Corrected result: every model exceeds the frozen maximum-over-horizon
  interval cap; holdout was erroneously authorized and is diagnostic only
- Final route: `ONE_MS_NR2R1_CALIBRATION_FAIL_NO_HOLDOUT`
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_nr2r1_result_20260813_25f5b7e/`
- Classification: statistics-gate implementation error plus finite causal
  model/uncertainty qualification failure; no controller, MPC, RL, global
  plant-reachability or closed-loop conclusion
- Next: pause before a new prospective model/state architecture; NR3 and new
  TSC remain blocked

## R_geo/Z_geo 1 ms NR2R2B0 source q0 baseline

- Branch: `codex/rgeo-zgeo-1ms-nr2r2a-identifiability`
- Architecture reassessment / NR2R2A design / audit / B0 design /
  implementation: `ae5a614 / f6d9be5 / d00ec50 / eb549fb / f4b1537`
- Remote project: `/home/yangshen0711/tsc_all/tsc_rzip_rllib`
- Offline gate: `artifacts/nr2r2b0_offline_f4b1537_v1.json`, PASS, zero plant
  advances, SHA-256
  `b6cd36efff19149d384f0a24c98c77609b289abb4b722f95e32d60377952bef1`
- Remote run: `artifacts/nr2r2b0_run_f4b1537_v1`
- Remote log: `logs/nr2r2b0_run_f4b1537_v1.log`
- Fresh process PID: `3393675`, exited after final result
- Expected/actual: `6x32 / 6x32`, 192/192 authentic advances, 198 raw states
- Primary/independent route:
  `ONE_MS_NR2R2B0_BASELINE_REPEATABILITY_FAIL_STOP`
- Physical repeatability: exact zero difference in R/Z/R_mid, Ip, 14 coil
  currents and 48 wire-current components; Card15 exact
- Artifact repeatability: inputa/geqdsk/coil/wire exact; sprsina differs on
  every successor state across resets, so the frozen all-artifact gate fails
- q0 short hold: FAIL; maximum source drift `17.6013 mm R / 23.4419 mm Z /
  335.723 A Ip`; terminal max step `0.6177/0.8058 mm`
- Raw inventory: 990 required files / 11,660,798,952 bytes / digest
  `c8a8de054f3cd5af9e731d46f56beb4601ee13d6176ff3029e608479076f3789`
- Primary / independent / compact SHA-256:
  `ed4aff78c7d5b231841d114ced259774d43cea44bab35b2456ca16ff32588595`,
  `c2428464e97fafca794549ecbabab4e48997343764a834fc505adcf9548ec086`,
  `3f95504d2b329f9b3e5dd937b221749351678ddade77ca10ee4add8474548bb6`
- Classification: frozen artifact/restart-identity repeatability design FAIL
  plus genuine finite q0-hold FAIL; not runtime, TSC, physical-output
  nondeterminism, model, controller, MPC or reachability evidence
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_nr2r2b0_20260813_f4b1537/`
- Next: pause for explicit active source hold/recovery architecture and
  prospective sprsina semantic audit; no atlas/probe/model TSC

## R_geo/Z_geo 1 ms NR2R2C2aA1 level-2 authority discriminator

- Branch: `codex/rgeo-zgeo-1ms-c2a-nominal-hold`
- Design / implementation / offline-audit correction:
  `64c2983 / 4845004 / 3e85a4b`
- First offline result: zero plant advances; exact doubled-offset check used
  the wrong post-conversion coordinate and failed closed. The file is retained.
- Accepted offline result: PASS, 32 action steps, maximum adjacent exact issue
  delta `0.15 A`, zero plant advances
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_nr2r2c2aa1_runs/rgeo_zgeo_1ms_nr2r2c2aa1_level2_authority_20260814_3e85a4b`
- Remote log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/rgeo_zgeo_1ms_nr2r2c2aa1_level2_authority_20260814_3e85a4b.log`
- Expected/actual: `2x32 / 2x32`, 64/64 authentic advances, 66 states
- Execution/replay: PASS; exact checked geometry, Ip, 14 coil, 48 wire,
  actions and semantic hashes; `sprsina` non-identical diagnostic
- Raw inventory: 330 required files / 3,886,932,984 bytes / digest
  `e297d26c2eb13d85dc10ced2a8dc7a954fbbbf31b8477e0ac6cba90ad169c594`
- Primary / independent SHA-256:
  `f069c33191a13f03c872c52e54d72d0ff40c1019e504b0e8337a435f60e36cd6 /`
  `286a96b7e3ce5162a6adaa92dc424f05280b671b1bfe79d971c3250dc44ade15`
- Authority: mean `0.0070801 mm`, positive `2/14`, maximum `1.0156325 mm`;
  maximum q0-relative Ip deviation `32.4491 A`
- Final route: `ONE_MS_NR2R2C2AA1_LEVEL2_AUTHORITY_FAIL_REDESIGN`
- Classification: finite action-direction/schedule authority FAIL; not a
  runtime, interface, model, controller, recovery, MPC or reachability result
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa1_result_20260814_3e85a4b/`
- Next: prospective supported-cube sign/direction discriminator only;
  Nominal-H1, C2b, model, atlas, MPC and learning remain blocked

## R_geo/Z_geo 1 ms NR2R2C2aA2 supported-cube directions

- Branch: `codex/rgeo-zgeo-1ms-c2a-nominal-hold`
- Design / implementation: `104cfd5 / 8bd6964`
- Validation: local/server focused `11/11`; server full `1697/1697`, one
  expected skip; offline PASS with zero plant advances
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_nr2r2c2aa2_runs/rgeo_zgeo_1ms_nr2r2c2aa2_supported_cube_directions_20260814_8bd6964`
- Expected/actual: `3x32 / 3x32`, 96/96 authentic advances, 99 states
- Execution/safety: PASS; maximum successor `0.79909 mm R / 0.84181 mm Z /
  33.2962 A Ip`; maximum issued/readback step `0.3/0.3 A`
- Raw inventory: 495 files / 5,830,399,476 bytes / digest
  `72611161f6f01e2374a89a6bfad998621b5b9103217314582a5d6e85660d0279`
- Primary / independent SHA-256:
  `9e94ce75071c0b9a05d0b4f97943273d272857c1c2d4136768702efda59e096f /`
  `c8e1a06c558531c83c222856f53d2d634aa4739372e14f413505165a64887ef9`
- P03-minus: mean `0.355931 mm`, positive `14/14`, maximum `0.523279 mm`,
  maximum q0-relative Ip difference `37.6619 A`; FAIL unchanged maximum gate
- P04/P07-minus: positive `14/14`, means `0.186802/0.159783 mm`; FAIL mean
  and maximum gates
- Final route: `ONE_MS_NR2R2C2AA2_SUPPORTED_CUBE_DIRECTIONS_FAIL_REDESIGN`
- Classification: finite supported-cube direction authority FAIL; not runtime,
  interface, raw, model, controller, MPC, recovery or reachability evidence
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa2_result_20260814_8bd6964/`
- Next: prospective repeated p03-minus cumulative-domain/incremental-gain
  sentinel only; Nominal-H1 and later control stages remain blocked

## R_geo/Z_geo 1 ms NR2R2C2aA3 p03 cumulative level2

- Branch: `codex/rgeo-zgeo-1ms-c2a-nominal-hold`
- Design / plant implementation / audit-only fix:
  `0821c78 / e01411d / 134b133`
- Validation: focused `15/15` before plant; server full `1701/1701`; after
  audit fix focused `5/5`, server full `1702/1702`; one expected skip
- Offline: PASS, zero plant advances, maximum adjacent issue `0.3 A`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_nr2r2c2aa3_runs/rgeo_zgeo_1ms_nr2r2c2aa3_p03_cumulative_level2_20260814_e01411d`
- Expected/actual: `2x32 / 2x32`, 64/64 advances, 66 states
- Maximum successor: `0.803476 mm R / 0.827237 mm Z / 42.7190 A Ip`
- Raw inventory: 330 files / 3,886,932,984 bytes / digest
  `08749807d68650a23d7575aad66c4fe15919ab9e7ce7d4caa898837b0b3e5fa4`
- Primary / independent SHA-256:
  `1e082fda5e87e74655f53215b4815edb563ffd386516b704abd34a5393d71b76 /`
  `12be18d78acb1fe373bb975e8153f41e1802bc56ff872c8400cacb9ed24834c1`
- Total opposition: mean `0.741923 mm`, positive `14/14`, maximum
  `1.072706 mm`; maximum q0-relative Ip `75.758 A`
- Incremental over p03 level1: mean `0.385992 mm`, positive `14/14`
- Final route:
  `ONE_MS_NR2R2C2AA3_P03_CUMULATIVE_LEVEL2_PASS_TIME_VARYING_C2A_DESIGN_ONLY`
- Classification: finite adjacent cumulative-level authority PASS; not hold,
  recovery, model, controller, MPC or reachability evidence
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa3_result_20260814_e01411d/`
- Next: prospective time-varying q0/p03-level1/level2 C2a search only

## R_geo/Z_geo 1 ms ID-1B persistent-dwell geometry

- Branch: `codex/rgeo-zgeo-1ms-id0-vector-tail`
- Design / plant implementation / audit-only fix:
  `4d079502 / bd1b5802 / 666c8e06`
- Package / audit-hotfix package: `4d7a3a55 / 6b920f4e`
- Server validation: pre-run focused `31/31`; audit-hotfix focused `32/32`;
  zero-plant offline preflight PASS
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id1b_runs_20260814_bd1b5802`
- Expected/actual: `14x24 / 14x24`, 336/336 verified advances, 350 states
- Raw inventory: 1,750 files / 20,612,523,400 bytes / digest
  `31170185118b0c8d5698db80bd9f3862823602b95247216a42479ac657a0975d`
- Primary / final independent SHA-256:
  `54ed170bc628237d6d7b8828f6dc3c77b06e549f064a63ae4281af9aea0d0db8 /`
  `4eb32fd6021f8d30c20103ada2530c444d73ad7c38707441f77f7e227c6c6791`
- Exact replay, per-arm signal, Ip and rank gates PASS; best pair condition
  `1.8089786595722026`
- Positive span FAIL: all six persistent means have positive dR; maximum
  angular gap `299.72069139587876 deg`; minimum directional support
  `-0.089323963 mm`
- Initial independent audit FAIL was an issue-0 inputa reconstruction bug;
  the preserved raw were re-audited after a zero-TSC reporting-only fix and
  passed with maximum metric difference `6.78e-21`
- Final route:
  `ONE_MS_ID1B_PERSISTENT_POSITIVE_SPAN_FAIL_DIRECTION_REDESIGN`
- Classification: finite q0-centred action-direction design FAIL; not
  runtime, raw, model, controller, MPC, recovery or global reachability
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id1b_result_20260814_bd1b5802/`
- Next: zero-new-TSC direction/active-nominal-centre design review; no fit
  or further TSC until prospectively frozen

## R_geo/Z_geo 1 ms ID-1C0 consumed-development direction screen

- Implementation / identity fix: `51dcc7b5 / 3986502f`
- Execution: server project virtual environment only; focused `2/2`; zero
  TSC, plant advance, reset, `gotsc`, fit and training
- Inputs: 23 files / 1,854,612 bytes / digest
  `d60600155c8261913580ac4962dced57bf4ea8e10d800c934c64a4bfe066e4a6`;
  NR2R1 development only, no holdout
- Final result SHA-256:
  `4f89bd34555287b236d1c22a4bfb12883dd1b603cf4a49a46bfff63a174428db`
- Selected directions: p01+p09; rank 2; maximum angular gap
  `98.6800382 deg`; minimum directional support `0.0218296712 mm`; best
  two-ray condition `2.0015232`; maximum absolute Ip response `14.2429 A`
- Final route:
  `ONE_MS_ID1C0_DIRECTION_SCREEN_PASS_FRESH_PERSISTENT_VALIDATION_REQUIRED`
- Classification: retrospective consumed-development direction screen only;
  not persistent validation, fit, controller or authority qualification
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id1c0_direction_screen_20260814_3986502f/`
- Next: fresh exact-centred half-amplitude p01/p09 ID-1C persistent basis
  validation; PASS still does not authorize fitting from ID-1C

## R_geo/Z_geo 1 ms ID-1C persistent basis validation

- Implementation / package revisions: `9401377d / e7c1bba3`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id1c_runs_20260814_9401377d`
- Remote logs: `logs/nohup/id1c_real_9401377d.log` (zero-TSC permission
  failure) and `logs/nohup/id1c_real_9401377d_v2.log` (complete campaign)
- Fresh/resume: fresh; first launcher attempt stopped before Python/TSC,
  second launch used the unchanged identity after executable-bit repair
- Execution: 10/10 rollouts, 180/180 verified one-ms advances, 190 states
- Raw: 950/950 required files, 11,189,655,560 bytes, digest
  `a4ee5ade9db3131afa320ba59747fa6d9909c52837700636a5ed2f35be30c611`
- Primary / independent SHA-256:
  `7e6bf6d535c1f4b880301c56c952f58820c354339467618ce39055946dc0a359 /`
  `92a19f62ab9a452b5d7deba29a1b47dd96dc2701321eee88789e89b44f408aef`
- Execution, raw, repeatability, signal, Ip and rank PASS; independent raw
  recomputation PASS
- Scientific FAIL: p09 even norm `0.109626 mm`; maximum angular gap
  `180.150886 deg`; positive span FAIL
- Final route: `ONE_MS_ID1C_SIGNAL_SYMMETRY_OR_IP_FAIL_REDESIGN`
- Classification: finite duration/history/action-basis design FAIL; not
  runtime, raw, model, controller, MPC, recovery or global reachability
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id1c_result_20260814_9401377d/`
- Next: stop static mean-basis ladder; prospectively design fit-eligible
  duration/history primitives and resolve server storage before new raw TSC

## R_geo/Z_geo 1 ms ID-2C1 active nominal/vector development

- Branch: `codex/rgeo-zgeo-1ms-duration-history-model`
- Design / implementation / independent ordering fix:
  `63f5ab56 / c4378ae3 / e2b2a1d3`
- Server validation: focused `6/6`, complete one-ms `126/126`, zero-plant
  offline preflight PASS
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2c1_runs_20260816_c4378ae3`
- Expected/actual: 11/11 rollouts, 352/352 verified advances, 363 states
- Raw: 1,815 required files / 21,378,131,412 bytes / digest
  `54b5f7c8b55ca10f000fe2eb4a9b6667351c0b5e55c2f76fde7def22cd8d4d47`
- Primary / final independent SHA-256:
  `eb3ee5d73dcc05f8cccdc551291b2df9a4ef1b34310454a98ddd53f88ad41d42 /`
  `7065a8af5677dd89c9f01c35e468ebe8b7a000b93e6a8992732f0e7749e02454`
- Selected exact `p03_minus_stride1`; terminal R/Z norm reduction 34.188%;
  maximum source-relative Ip 722.743 A
- Six signed residual arms complete, peak R/Z 35--52 um, descriptive rank 2,
  best-pair condition 2.70623
- Initial independent FAIL was alphabetical campaign-row ordering only; the
  v2 auditor reparsed unchanged raw and reproduced all metrics without TSC
- Final route:
  `ONE_MS_ID2C1_ACTIVE_NOMINAL_AND_LOCAL_VECTOR_DEVELOPMENT_COMPLETE_ID2C2_DESIGN_REQUIRED`
- Classification: finite development search PASS; not repeatability, fit,
  calibration, holdout, tube, recourse, controller or reachability evidence

## R_geo/Z_geo 1 ms ID-2C2 fresh nominal/vector validation

- Design / implementation: `15e80345 / 58f24fc0`
- Server validation: focused `7/7`, complete one-ms `133/133`, `bash -n`,
  compile and zero-plant 18-stream offline preflight PASS
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2c2_runs_20260817_58f24fc0`
- Remote log:
  `logs/nohup/rgeo_zgeo_1ms_id2c2_20260817_58f24fc0.log`
- Expected/actual: 18/18 rollouts, 576/576 verified advances, 594 states
- Raw: 2,970 required files / 34,982,396,856 bytes / digest
  `ace05c327380a5945fecad6b9c5e1576543b852a58e85e08b0b687b020389ad5`
- Primary / independent SHA-256:
  `3d665ba7044ae3dca0635987249c241a5d2559764437de802737580ae933a925 /`
  `a4f693915a001d31a64954f30c31d1b3ba345ed6cd8cc4f85d9c0751b3051976`
- Nine fresh whole-trajectory replay pairs exact in checked geometry, Ip,
  14-coil, 48-wire, action and semantic-artifact fields
- Both nominal replays reduce terminal R/Z norm 34.188%; all signal/Ip/tail/
  two-sided geometry gates PASS; rank 2, condition 2.70623, maximum angular
  gap 136.40943 degrees
- Final route:
  `ONE_MS_ID2C2_FRESH_NOMINAL_VECTOR_VALIDATION_PASS_STRUCTURED_MODEL_DESIGN_REQUIRED`
- Classification: finite fresh source-local empirical validation PASS only;
  evaluator-only, not fit/calibration/holdout/tube/controller data

## R_geo/Z_geo 1 ms ID-2D1 v1 zero-TSC preflight

- Design / implementation: `8ef69732 / 1ba484eb`
- Server: exact patch deployment; no run directory or raw tree created
- Validation: `bash -n` and Python compile PASS; focused tests `6/7`
- Failure: frozen combined three-coordinate lag-16 matrix rank `42/48`
- Zero-plant factorization: p04/p07 lag16 rank `32/32`, condition `14.73875`;
  p09 event lag10 rank `10/10`, condition 1; p09 forced lag16 rank `10/16`
- Execution: zero resets, zero `gotsc`, zero TSC and zero plant advances
- Final classification: `ZERO_TSC_LAG_SUPPORT_DESIGN_FAIL`; the original
  rank48 gate was not weakened or re-labelled as PASS
- Next: new ID-2D1R1 identity with unchanged physical campaign and separate
  smooth/event lag-support gates

## R_geo/Z_geo 1 ms ID-2D1R1 active-nominal duration/time development

- Design / implementation: `7a0e9955 / 3e5b28b3`
- Server validation: focused `7/7`, complete one-ms `140/140`, `bash -n`,
  compile and zero-plant 24-stream preflight PASS
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2d1r1_runs_20260817_3e5b28b3`
- Remote log:
  `logs/nohup/rgeo_zgeo_1ms_id2d1r1_20260817_3e5b28b3.log`
- Expected/actual: 24/24 rollouts, 768/768 verified advances, 792 states
- Raw: 3,960 required files / 46,643,195,808 bytes / digest
  `bd726766870f08e98ae46342c3ad41763a465e2e6e0adef832b7e295af688b50`
- Primary / independent SHA-256:
  `f68d30865ed47503f32cf830da42e829b94bb6db6a3c4165d586a19ba726a7a8 /`
  `85e7d598332905a6a2de11a71816a2eb3d2d374cef62ac1b5ce685084ac0ae02`
- Exact baseline repeatability, smooth lag16 rank32, event lag10 rank10 and
  all signal/Ip gates PASS; independent raw recomputation PASS
- Several minus cells have authentic delayed state27 peaks of 0.63--0.75 mm,
  so a globally odd or instantaneous residual model is not presumed
- Final route:
  `ONE_MS_ID2D1R1_ACTIVE_NOMINAL_DURATION_TIME_DEVELOPMENT_PASS_STRUCTURED_MODEL_ONLY`
- Classification: finite source-local fit-eligible development PASS only;
  not calibration/holdout/tube/controller data; ID-2C2 remains evaluator-only

## R_geo/Z_geo 1 ms ID-2E1 structured active-nominal model

- Design / implementation / independent audit:
  `02a7f113 / 59d2790a / d8bb8dc3`
- Server validation: `bash -n`, compile, focused `7/7`, complete one-ms
  `147/147`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2e1_models_59d2790a`
- Execution: 21 development fits; zero reset, `gotsc`, TSC and plant advance
- Primary / strengthened independent SHA-256:
  `b0fb654f9f1e5a1f947740a1c5012669f863518dcfd975f00d8c8cb642e38062 /`
  `80b31220b0d7a3d89a0652d4da2b98b6a31ff11d85bd7f9bc4a90fd2f1523078`
- Independent full-fold recomputation: PASS; maximum difference `2.78e-17`
- Candidate result: no p04/p07 fixed-pole/FIR candidate passed all five
  whole-schedule folds; no selected artifact
- P09 event development: NRMSE `0.1717123`, improvement `80.36%`
- ID-2C2 evaluator: unopened, zero records read
- Final route: `ONE_MS_ID2E1_GROUPED_DEVELOPMENT_MODEL_FAIL_ROUTE_REVIEW`
- Classification: model/data-geometry failure before evaluator; not runtime,
  TSC, calibration, holdout, controller or reachability evidence
- Next: route review of the state19/state27 sign-dependent event pattern

## R_geo/Z_geo 1 ms ID-2G1R1 full-Card15 grouped model comparison

- Branch: `codex/rgeo-zgeo-1ms-duration-history-model`
- Model implementation / action-blind correction:
  `7841a173 / ebdb42a0`
- Server validation after correction: focused `12/12`, complete one-ms
  `169/169`; compile and zero-TSC preflight PASS
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2g1r1_models_20260817_ebdb42a0`
- Execution: zero reset, `gotsc`, TSC and plant advance; zero ID-2C2,
  calibration or holdout records read
- Selected model: causal TCN; mean three-context response NRMSE
  `0.68097772`, action-blind improvement `31.9022%`
- Fold response NRMSE: `0.71370094 / 0.66436756 / 0.66486466`
- Worst recursive p95: `0.359981 mm R / 0.181205 mm Z / 10.9505 A Ip`
- Primary / independent / selected-model SHA-256:
  `6d2389d7d7a5d86eea221cadd4fe386b6f95a734405496b36eab07a372856afa /`
  `614b01bdc8b422bc1ced2472da1ccac3f5d9445ca8baed1c431f8a0dbc1ad83e /`
  `14502175c95d1d0b5b36846a35af249af0041405eb6c013f099caa4dd18d176b`
- Independent full raw re-extraction/refit: PASS; maximum numeric difference
  zero
- Final route:
  `ONE_MS_ID2G1R1_GROUPED_MODEL_PASS_FRESH_CALIBRATION_DESIGN_ONLY`
- Classification: finite three-context development-model selection PASS;
  not calibration, blind holdout, tube, controller or closed-loop evidence
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2g1r1_20260817_ebdb42a0/`
- Next: separately frozen fresh whole-history calibration design for the
  exact selected artifact; no model tuning or controller work

## R_geo/Z_geo 1 ms ID-2J0 post-holdout attribution

- Branch: `codex/rgeo-zgeo-1ms-duration-history-model`
- Implementation / reporting-only repair:
  `2e1eaa784c98bda084206bf4b19a167a366ead01 / 53d0f9db24a73bf85716aafb7f040dfacea07793`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2j0_runs_20260817_2e1eaa78`
- Execution: 16/16 diagnostic rollouts, 544/544 verified one-ms advances,
  560 states and eight exact matched baseline/probe prefixes
- Raw: 2,800 required files / 32,980,037,440 bytes / digest
  `fd884699425916b774650c882659bff3826f41b7d8d689a093984f7fea3bd52d`
- Primary / independent raw SHA-256:
  `8f473103b4b609db8845735f3ee28701ce1e74c93f65f492dd31fec4c76d31f2 /`
  `7b4885bbc005cf2270d263d969a2332fe889b4e6b6567965ea734d9f3f63cf8f`
- Attribution / independent audit SHA-256:
  `fbc1a58a34e15c0c0b9f87afcc3852ccf8c09f712f1281a393e02edb49d1f02d /`
  `f3cec48ab5102cc403b665db6bcf5f4ae3f166835c7ca22e3e83c7a534f73c65`
- Result: exact 1 ms truth recenter paired NRMSE `1.133318`, positive peak
  direction `5/8`; three minus histories retain negative cosine; six of eight
  probe prefixes outside full-feature development support
- Actuator diagnostic: maximum next-current residual `1.00000000031741e-05 A`
- Final route: `ONE_MS_ID2J0_MIXED_DATA_AND_STRUCTURED_MODEL_REQUIRED`
- Classification: post-holdout diagnostic re-observation and zero-fit
  attribution; not blind validation, fitting, calibration, controller or
  safety evidence
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2j0_20260817_53d0f9db/`
- Next: prospective factorized history/sign/action development data, then
  structured nominal + stable memory + optional small residual comparison

## R_geo/Z_geo 1 ms ID-2U1 moving-nominal development

- Branch: `codex/rgeo-zgeo-1ms-duration-history-model`
- Design / implementation / result commits: `3afc52aa / 787e14b2 / e9843ea3`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2u1_20260818_63d498c5`
- Remote log: `logs/id2u1_20260818_63d498c5_v2.log`
- Expected/actual: 20/20 rollouts, 800/800 verified one-ms advances,
  820 states
- Raw: 4,100 required artifacts / 48,292,197,680 bytes / digest
  `f42fd452c5b7fe0d718d0232371498b18b3b6068f58556f14dc859c68d979f94`
- Primary / independent SHA-256:
  `297d32bfb5a945238150f5a951d4de5c6df2e28f16a3d13f816778ecc27cc3b4 /`
  `bf3c68a26d94406e8c54c4bd96b6d3e621735d923ebdf1ef28c478ac0c6ffd62`
- First launch used system Python and stopped before output/reset/TSC;
  corrected v2 used the server venv without changing experiment semantics
- Result: all execution/raw/prefix and 16/16 signal/Ip gates PASS; large
  delayed response confined to `u00` minus cells in this finite matrix
- Final route:
  `ONE_MS_ID2U1_MOVING_NOMINAL_DEVELOPMENT_PASS_MODEL_COMPARISON_ONLY`
- Classification: fit-eligible moving-nominal development data only; paced
  calibration and blind families unopened

## R_geo/Z_geo 1 ms ID-2U2 bounded causal model comparison

- Branch / implementation: `codex/rgeo-zgeo-1ms-duration-history-model / 45265ef0`
- Server validation: focused `10/10`, complete one-ms `328/328`, compile,
  shell syntax and zero-TSC preflight PASS
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2u2_45265ef0`
- Remote log: `logs/id2u2_20260818_45265ef0.log`
- Execution: eight development whole-family fold fits; zero reset, `gotsc`,
  TSC and plant advance; zero calibration or blind records read
- Primary / independent SHA-256:
  `30f303ecd35b21399d3c894f15dfa0f4c3e6c212d5a5f09eabe7eb647ac495a8 /`
  `c7a92cc351ae064fb6aceb38aff215098e0c6bd0a54ad647b63754e215f27d05`
- Local/event model mean/worst response NRMSE `1.055527/1.141862`; small
  GRU residual regressed to `2.412078/4.119342`; no selected model artifact
- Final route: `ONE_MS_ID2U2_NO_ELIGIBLE_CAUSAL_MODEL_REVIEW_REQUIRED`
- Classification: finite model/support-design FAIL, not runtime, TSC,
  controller or reachability evidence
- Next recommendation: preserve unopened `u01/u03/u05/u07`; add one new
  fit-eligible arrival history at each existing level/time corner before a
  new bounded low-capacity comparison

## R_geo/Z_geo 1 ms ID-2Z1 late-action macro utility

- Branch: `codex/rgeo-zgeo-1ms-duration-history-model`
- Design / implementation / reporting-only audit repair:
  `8de743bc / ecb43246de07186d7d2bcd4d0cdc5951c6398685 / 5d83301d`
- Remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_id2z1_20260819_ecb43246`
- Server validation: pre-plant focused `9/9`, complete one-ms `394/394`;
  post-repair focused `10/10`, complete one-ms `395/395`
- Execution: 7/7 complete branches, 511/511 attempted, `gotsc` and verified
  one-ms advances, 518 states
- Raw: 2,590 required artifacts / 30,506,534,632 bytes / digest
  `85376c20f157ef5df12d89be50e2bb9ac3b3570afd5cabbe59b8b7715d36abff`
- Primary / independent SHA-256:
  `c1a6f2af83fa37c06a961a8836f2cc9bca0e2a779317f59570ca27c2848943ec /`
  `fc9eb327b6575c647b5cc2d3a7da950039c77d3e89a161c7ce958cb1934ea841`
- Result: p03-forward4 and p07-minus4 passed persistent finite utility;
  p03-forward4 selected with `0.9465 mm` terminal distance improvement and
  `145.0614 A` maximum paired Ip
- Known reporting defect: the first independent audit expected a float current
  alias absent from its raw parser; `5d83301d` repaired only that diagnostic and
  the zero-new-TSC full-raw rerun passed. The outer background rc helper contains
  literal `1n`; raw, primary result and repaired audit are intact.
- Final route:
  `ONE_MS_ID2Z1_LATE_MACRO_UTILITY_PASS_ROLLING_SEQUENCE_DESIGN_ONLY`
- Classification: finite source-local transport-macro utility and sequence
  nomination only; not hold, recovery, controller, waypoint or reachability
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2z1_20260819_ecb43246/`
- Next: prospectively frozen two-decision canonical-prefix rolling branch
  campaign, replanning at state69 and selected state73

## 2026-08-19 ID-2Z7 fresh branch continuation

- Implementation revision: `cb5c7a40c112208d13e3f2b42ded820d445b1c90`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z7_runs/20260819_cb5c7a40_v1`
- Server validation: focused 9/9; all one-ms 448/448; static action matrix
  25/25; zero-TSC preflight PASS
- Execution: 11/11 complete fresh paths; 759/759 attempts, `gotsc` calls and
  verified advances; 770 states; zero guarded safe stops
- Raw: 3,850 files / 45,347,551,480 logical bytes / digest
  `acafcc901839bb52d68d42b8fd47dc8de37a9099029a5400915951fe6990d539`
- Primary / independent SHA-256:
  `d4cf6c2d2328a1b58c24c5a07a69150c13e559c740a3fe9842e347cbac9ed54a /`
  `a46fd35ce6a197817334864b9e3dfd01da51e8448ec1b877d058237ee9fbebd1`
- Selected sequence: `f4 -> b2f2 -> f2b2`; exact replay PASS; combined
  complete development-weight windows 15/15
- Scientific boundary: terminal score improved `4.40768 -> 3.27475`, but
  capture failed (`26.38866 mm`, `0.32747 m/s` at state 69)
- Final route:
  `ONE_MS_ID2Z7_BRANCH_CONTINUATION_PASS_REPLAY_RECOURSE_AND_SMALL_MODEL_DESIGN_ONLY`
- Cleanup: removed only the independently audited raw `rollouts/` subtree,
  46,050,216,111 filesystem bytes; compact evidence/logs retained; free bytes
  after cleanup 136,051,212,288
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2z7_20260819_cb5c7a40_v1/`
- Next: one bounded two-candidate, whole-context small-model comparison; no
  controller or Recourse-L1 authorization

## 2026-08-19 ID-2Z3 bounded braking rolling search

- Physical implementation: `68dff0c7733b6ff19dacbbe2917c3c82db8e8a73`
- Reporting-only audit repair: `54e1601836da796098fda40b2d9eea6e4472742d`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_id2z3_20260819_68dff0c7`
- Execution: 14/14 admitted rollouts, 1,366/1,366 advances, 1,380 states,
  zero guarded safe stops
- Raw: 6,900 required files / 81,272,235,120 bytes / digest
  `7978b9e074b45e233147aa64f3d181cf34eb593723d9701692ae15e4a0e5de9c`
- Primary / repaired independent SHA-256:
  `72ba717fb4b4ad59e35b96e8d4ee5f3689c8df4f886b1497bddfd08dc631106c /`
  `d5bdeb5f88189e0c0617e89408441a4f7c138b0c4a983414dda03695c76f12fe`
- Initial independent SHA-256:
  `47420fc3ec5f7e822be084ba23d88636763abb69b67bdcfa5d1f2f3b69ddbb84`
  (reporting-only rewritten-`inputa` lifecycle mismatch; preserved FAIL)
- Server validation after audit repair: focused 8/8; all one-ms 416/416
- Selected sequence: five consecutive `p07minus4` macros
- Final held-lookahead: maximum distance `25.4024 mm`, maximum speed
  `0.300687 m/s`, Ip inside the five-percent cap
- Final route:
  `ONE_MS_ID2Z3_BRAKING_SEARCH_EXHAUSTED_GRAMMAR_INSUFFICIENT`
- Classification: finite source-local action-grammar failure; not runtime,
  raw, actuator, prefix, plant, controller, recovery or reachability failure
- Compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2z3_20260819_68dff0c7/`
- Next: bounded two-axis capture-grammar design at the exact selected
  state-97 prefix; no extension of the p07-only ladder

## 2026-08-19 ID-2Z3 cleanup and ID-2Z4 design

- Irreversibly removed only:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_id2z3_20260819_68dff0c7/rollouts`
- Removed bytes: `82,525,197,355`
- Retained remotely: all per-rollout compact JSON, primary result, initial
  independent FAIL, repaired independent PASS, offline preflight and logs
- Free bytes after cleanup: `157,079,855,104`
- ID-2Z4 freezes eight state-97 capture candidates, at most eight resets /
  968 advances, with a 65-GB estimate and no model fit
- Design:
  `docs/codex/reports/RGEO_ZGEO_1MS_ID2Z4_CAPTURE_GRAMMAR_DESIGN.md`
- Config: `configs/rgeo_zgeo_1ms_id2z4_capture_grammar.json`
- Next: implementation, server-only validation, zero-TSC preflight and only
  then the finite real-TSC discriminator

## 2026-08-21 fixed-1000 NR1 R4R1 interface qualification

- Implementation revision: `3435b1862cbab53484154deb584839e51b3d23a1`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_nr1_r4r1_20260821_3435b186_v1`
- Server validation: focused `17/17`; all one-ms `736/736`; offline PASS
- Execution: `6/6` rollouts, `24/24` plant advances, 30 raw states
- Independent audit: 24 action checks, 56 first-effect component checks,
  18 later observed-slew checks, zero failures
- Maximum reserved issued excitation: `0.299 A`; unchanged hard observed
  slew limit: `0.3 A`
- Primary / independent SHA-256:
  `791375f0337d2e683f3c5b33b5bae254e03cd16660632acc2f6e3b93c5300644 /`
  `934d44dc415123d8f8f04a57022500e95f8405ea3e7ea05dc3c499e48fd32827`
- Final routes:
  `ONE_MS_NR1000S1R4R1_INTERFACE_QUALIFIED` / `ONE_MS_NR1000S1R4R1_INDEPENDENT_PASS`
- Classification: finite fixed-source 1 ms interface qualification only;
  not a drift, model, Authority, hold, recovery or feedback result
- Next: a new fixed-1000 matched-baseline and signed temporal-response
  development identity; no fixed-1100 model/evidence inheritance

## 2026-08-21 fixed-1000 B0 natural-drift baseline

- Implementation revision: `d3ecd3cda5253d88b8253e261ef9b8d12a7f44e8`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_b0_20260821_d3ecd3cd_v1`
- Server validation: focused `5/5`; all one-ms `741/741`; offline PASS
- Execution: `2/2` rollouts, `128/128` verified advances, 130 raw states
- Independent audit: 128 actions and 126 later observed-slew checks; exact
  R/Z/Ip, 14-coil, 48-wire and semantic-artifact replay
- Terminal source delta at state64: R `-23.538658 mm`, Z `0 mm`,
  Ip `+825.9437 A`
- Last eight states: net R `-2.324410 mm`, maximum R/Z speed
  `0.318027 m/s`
- Primary / independent SHA-256:
  `d6eaa48c4e158c48831c34aeb71c51ac455e253fab8e2868d92ec93d402868de /`
  `585c8825de755a7b0e7ec30bcaa3a636d9023cd7e0c8e3cf96dc401203ffef74`
- Final routes:
  `ONE_MS_NR1000B0_BASELINE_COMPLETE_SIGNED_ID_DESIGN_ONLY` /
  `ONE_MS_NR1000B0_INDEPENDENT_PASS`
- Classification: deterministic q0 natural drift only; not hold, stability,
  Authority, model, recovery or feedback
- Next: fresh multi-phase signed even/odd temporal-response D0

## 2026-08-22 fixed-1000 D0/D0R1 signed temporal response

- D0 implementation revision: `b5eaaaf6fd54cc439a91a9399af36349f615bd3d`
- D0 stopped at zero-plant preflight because requested `0.15 A` quantized to
  `0.20 A` on two coils, above its frozen `0.151 A` construction cap
- D0 used zero reset and zero plant advance; route:
  `ONE_MS_NR1000D0_OFFLINE_FAIL_NO_TSC`
- D0R1 implementation revision: `6113ce54917101417553c55898d21fc30a30afac`
- D0R1 changed only requested amplitude to `0.14 A` and froze measured
  quantized maximum `0.146 A`; hard `0.3 A` limit and science gates unchanged
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_d0r1_20260821_6113ce54_v1`
- Execution: `14/14` rollouts, `560/560` advances, 574 raw states, 33 GB
- Independent audit: 560 action checks, 546 later observed-slew checks,
  two exact critical replays, zero failures
- Phase-best condition / sigma-min mm: `2.81244/0.149968`,
  `1.93944/0.071388`, `1.81024/0.076201`
- Primary / independent SHA-256:
  `dba46b4810ee267e36b85f4167580a517476a2d146d40f0e94323a648f6f342f /`
  `79d670e4073273a71afbd732ed0a6902eec3fb4041408badf4d40438b94377dd`
- Initial independent FAIL was reporting-only: raw state0 inputa had been
  semantically reserialized by issue0; Card15 fields matched. Auditor revision
  `4c21a85a` retained field comparison and all other source artifact hashes;
  no TSC rerun
- Final routes:
  `ONE_MS_NR1000D0R1_SIGNED_TEMPORAL_PASS_MODEL_AND_AUTHORITY_DESIGN_ONLY` /
  `ONE_MS_NR1000D0R1_INDEPENDENT_PASS`
- Classification: finite fixed-1000 signed temporal development PASS only;
  next is cumulative/sustained exact-return D1, not feedback qualification

## 2026-08-22 fixed-1000 D1 cumulative temporal response

- Execution revision: `66b5c2d37d050cd3371f9832ba211e76cadfe9f0`
- Reporting-only repair revision: `464ec7dca89748b7155cf555d0a84a99184231b2`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_d1_20260822_66b5c2d3_v1`
- Server validation: focused `7/7`; the execution revision previously passed
  all one-ms tests `755/755` and offline preflight
- Execution: `10/10` rollouts, `480/480` verified advances, 490 raw states
- Initial result SHA-256:
  `1306313c534ab0a7f441b5e0f87a6668c26f15bce6dc1020bf7cca952f6ce1f4`
  and route `ONE_MS_NR1000D1_CRITICAL_REPLAY_FAIL_STOP`
- Reporting defect: D1 reused D0's `41-state/40-action` replay cardinality;
  both D1 replays actually contain the required `49 states / 48 actions` and
  have zero checked physical difference. No TSC rerun was made.
- Repaired-primary / independent SHA-256:
  `bb0899377b10306f373b9b72517a0458dc3498cbd21f4927298e0fb5d4580148 /`
  `a17df1173bdd31c41893de376b4e6322a9eebfbbc9729c5dd89a3ab23c720e00`
- Phase-best condition / sigma-min mm: phase 8
  `1.459061971/0.6310575`; phase 24 `1.557923416/0.2071960`
- Signed separations h4/h8 mm: phase8 even `1.07655/1.262115`, odd
  `0.707253/1.841504`; phase24 even `0.414392/0.599565`, odd
  `0.645591/1.827800`
- Final routes:
  `ONE_MS_NR1000D1_CUMULATIVE_TEMPORAL_PASS_MODEL_AND_AUTHORITY_DESIGN_ONLY` /
  `ONE_MS_NR1000D1_INDEPENDENT_PASS`
- Classification: finite cumulative fixed-1000 development PASS only; opens
  a small causal short-horizon model and separate Authority design, not hold,
  capture, recovery, feedback or path tracking

## 2026-08-22 fixed-1000 N0 radial nominal development

- Implementation revision: `2325e0aade98c940ed257dd2b499b9bd112b417b`
- Server validation: focused `5/5`, all one-ms `761/761`
- One initial zero-TSC preflight used a wrongly expanded revision string;
  it is invalid labeling evidence only and authorized no run. The corrected
  preflight SHA-256 is
  `53e3c00c48090e13ef524d0f06411e17e8f96b3078ad3977b6b9e1ddca9ba5c2`.
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/artifacts/server_runs/rgeo_zgeo_1ms_1000_n0_20260822_2325e0aa_v1`
- Execution: `5/5` rollouts, `320/320` verified advances, 325 raw states
- Replay: depth 12 exact in R/Z/Ip, 14 coils, 48 wires and semantic artifacts
- Terminal distance/speed by depth 4/8/12/16:
  `23.6548/0.37945`, `24.2850/0.37825`, `24.9034/0.37965`,
  `25.3739 mm/0.41390 m/s`; q0 is `23.5387 mm/0.31803 m/s`
- Primary / independent SHA-256:
  `4d769f9160e7c2f2fa7c50d7de7b83677a2387620b1239f5f06c9cba15e6893c /`
  `3072925f59d7a0eb441bfb22cac80d318ce4399ed0f0839fbdd288c2d2d6740c`
- Final routes:
  `ONE_MS_NR1000N0_RADIAL_NOMINAL_UTILITY_INSUFFICIENT_REDESIGN` /
  `ONE_MS_NR1000N0_INDEPENDENT_PASS`
- Classification: clean static ramp-and-hold schedule FAIL; not runtime,
  safety, raw corruption, global authority or controller evidence
