# ID2Z33 corrected moving-center delayed-tail D0 result

Date: 2026-08-21 (Asia/Shanghai)

## Verdict

ID2Z33 completed all ten prospectively frozen simulator-development
rollouts and all 730 plant advances. The primary result and an independent
raw reparse agree on
`ONE_MS_ID2Z33_CORRECTED_MOVING_CENTER_D0_PASS_MODEL_DESIGN_ONLY`.

This is finite D0 evidence only. It authorizes one bounded event-aware model
development identity. It does not certify a model, feedback controller,
Authority-L0, capture, recovery, Recourse-L1, waypoint/path controller,
position generalization, or repeated R_mid crossing.

## Identity and execution

- Physical source revision:
  `3892b0c15301a93c1a4e13c2a46b7b7c67598dc0`.
- Reporting-only direct-auditor import repair:
  `6e9c004943e73b7efdefb1bf20867add48080c6a`.
- Config SHA-256:
  `e4503fcd8c7d53cd768e50908af158d893dfd7986a52ecbae5857171f669388f`.
- Ten resets and ten complete rollouts; 730/730 attempts, `gotsc` calls and
  verified successors; 740 states.
- Required raw inventory: 3,700 artifacts, 43,580,763,760 bytes, digest
  `7feeaf08be6982334fbfabc5c0e7e2d860ebffcd7dda624a57f32f39d0dff83f`.
- Primary SHA-256:
  `14f0b4f081f95ff69e418ea0f9f4de6725705c963a153bd7603e324e066f29c3`.
- Independent audit SHA-256:
  `735cd75f5d0b7636fd123e66bc0e94a9ea678a4bb9e142ac942bf89b9c469e5a`.

The initially invoked independent script failed before reading raw because
direct execution did not put the repository root on `sys.path`. The repair
changed only that audit entry point. It did not change actions, plant
execution, metrics, thresholds, data roles, or the experiment identity, and
no TSC trajectory was rerun.

## Scientific result

All eight corrected branch streams differ from their matched moving-center
baseline inside their exact 16-issue windows and return to that center. All
eight passed the frozen h4/h8 signal, persistence and paired-Ip gates:

| phase | branch | h4 norm (mm) | h8 norm (mm) | cosine | max paired Ip (A) |
|---:|---|---:|---:|---:|---:|
| 50 | q_R+ | 0.057901 | 0.191731 | 0.999997 | 24.6150 |
| 50 | q_R- | 0.057843 | 0.189078 | 0.999125 | 24.6424 |
| 50 | q_Z+ | 0.061090 | 0.250673 | 0.993233 | 47.6307 |
| 50 | q_Z- | 0.061036 | 0.237386 | 0.993288 | 49.3483 |
| 56 | q_R+ | 0.058959 | 0.215144 | 0.998998 | 24.7600 |
| 56 | q_R- | 0.058693 | 0.191549 | 0.997310 | 25.9959 |
| 56 | q_Z+ | 0.058958 | 0.250656 | 0.991336 | 49.4822 |
| 56 | q_Z- | 0.058959 | 0.231284 | 0.990896 | 48.1934 |

The four task-plane geometry gates also passed. Maximum angular gaps were
98.53--108.75 degrees and weakest-best projections were 0.03982--0.04021 mm
at h4 and 0.13155--0.13642 mm at h8. The frozen replay was exact.

These measurements repair ID2Z32's unexecuted issue-56 comparison. They do
not retrospectively change ID2Z32, whose rows remain zero fit weight.

## Data role and next route

Only the eight prospective ID2Z33 branch families may enter the next
development fit. The matched baseline and replay have zero fitting weight;
ID2Z32 remains forbidden. The successor is limited to two preregistered
event-aware candidates using exact current R_geo/Z_geo/Ip, complete causal
history, exact Card15/current semantics and the full return/delayed-tail
window. A smooth wider tube, generic capacity search, or post-result family
selection is prohibited.

Development PASS may only freeze an artifact for fresh calibration and an
unopened whole-family blind holdout. Authority-L0 and Recourse-L1 remain
independent parallel prerequisites, and all three must pass before any real
controller execution.

## Evidence retention and cleanup

All top-level compact JSON and the complete log were copied directly and
hash-matched into
`docs/codex/audits/rgeo_zgeo_1ms_id2z33_20260821_3892b0c1_v1/`.
Only after independent authentication and compact recovery, the exact remote
`rollouts/` subtree was removed (44,254,755,926 filesystem bytes). The remote
result, audit and log remain; free space after cleanup was 224,689,799,168
bytes.
