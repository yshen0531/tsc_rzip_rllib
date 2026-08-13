# R_geo/Z_geo 1 ms NR2R1 q0-readback coordinate repair

Status: prospectively frozen before implementation and before any NR2R1 TSC
plant advance on 2026-08-13 Asia/Shanghai.

## Scope

NR2 stopped safely after one q0 step because its structural readback bias used
the finer source `inputa` command as origin. NR2R1 changes only that coordinate
origin. It keeps the complete frozen NR2 data matrix, schedules, splits,
model candidates, uncertainty rules, gates, safety envelope and maximum
budget from
`RGEO_ZGEO_1MS_NR2_MODEL_QUALIFICATION_DESIGN.md`.

```text
contract             rgeo-zgeo-1ms-nr2r1-v1
campaign             rgeo_zgeo_1ms_nr2r1_q0_structural_residual_v1
fixed source         1100 ms
control period       1 ms
single-turn limit    |delta I_i| <= 0.3 A per step, equality allowed
maximum              36 trajectories / 576 plant advances
```

NR2 raw is not reused, resumed, fitted or reclassified. NR2R1 starts from
independent 1100 ms resets and creates a fresh development/calibration and,
only if authorized, holdout dataset.

## Corrected structural coordinate

Before every trajectory, deterministically construct the exact q0 Card15
target from the source readback using the existing formatter. Define:

```text
q0_command_i = exact single-turn current represented by q0 Card15 field i
bias_i = source_readback_i - q0_command_i
predicted_readback_i[k+1] = issued_Card15_target_i[k] + bias_i
```

The bias is an interface coordinate, not a fitted response. It is computed
before the trajectory from source files and q0 only. It uses no future state,
plasma response, split label or outcome. Every successor must still match the
structural prediction within `1e-9 A` or the entire phase stops.

Command-to-command and readback-to-readback exact-decimal slew remain separate
`<=0.3 A` checks. Card15 serialization, q0 construction, issue-to-successor
effect state, runner, TSC semantics and all safety bounds are unchanged.

## Evidence and routes

The original NR2 failure and its single raw transition remain immutable at
the path recorded in `RGEO_ZGEO_1MS_NR2_RESULT.md`. NR1R2 raw may be inspected
only as interface evidence supporting this prospective correction; it cannot
enter fitting, normalization, calibration or holdout evaluation.

All original NR2 routes apply with `NR2R1` identity. In particular, any
structural mismatch is `ONE_MS_NR2R1_SAFETY_FAIL_STOP`; a calibration failure
prevents holdout; a holdout failure ends the model route. A PASS qualifies
only finite 16 ms same-source causal prediction and does not authorize NR3
controller execution without a separately frozen design.

