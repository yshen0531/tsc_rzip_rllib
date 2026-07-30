# Stage3.2 signed-margin, 250 ms long-hold, and causal-MPC report

## Scope and immutable hard gate

Stage3.2 starts from the real-TSC Stage3.1 strict nominal. It keeps the validated three-mode action space and the original 30 mm / 0.10 m/s / 10 kA hard limits. Arrival must be completed by 150 ms and the trajectory must remain safe through 250 ms.

The final project task is still a robust causal feedback controller across initial states, targets, plant uncertainty, measurement noise, and delay. This run does not validate that full scope and does not justify making residual RL the primary controller.

## Run summary

- Source Stage3.1: `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_1_runs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms_20260722_013158`
- New real-TSC optimization/identification evaluations: 810
- New successful evaluations: 810
- New 250 ms strict candidates: 314
- Margin stop reason: `max_margin_rounds`
- Long-hold stop reason: `max_hold_rounds`

## Best 150 ms margin candidate

- Candidate: `s32mr002p_60561a966014cce4`
- Hard signed margin: 0.030616140000000014
- Internal signed margin: -0.0575096654545455
- Sustained box: 0.0290815158 m
- Post-arrival velocity RMS: 0.020146686885443243 m/s

## Best 250 ms long-hold candidate

- Candidate: `s32cr000p_03075fa5a99f2223`
- Strict long hold: True
- Minimum signed margin: 0.031981773333333297
- Sustained box through 250 ms: 0.0290405468 m
- Post-arrival velocity RMS: 0.024192191262095444 m/s

## Causal feedback validation

- Tested scenarios: 33
- Selected controller scale: 1.0
- Target/disturbance feedback validated: False
- Online feedback validated in the tested scope: False
- Initial-state robustness validated: False
- Plant-parameter robustness validated: False

## Confirmation

- Verdict: `PASS_PRECISE_HOLD_30MM_250MS_OPEN_LOOP_CONFIRMED_FEEDBACK_NOT_VALIDATED`
- Online feedback validated: False
- Overall robustness validated: False

## Interpretation boundary

A confirmed 250 ms nominal establishes a stronger expert trajectory than Stage3.1, but it is not the final controller. A feedback pass covers only the configured target shifts and injected-mode disturbances from one initial state. Initial-state, vessel/eddy-current, plant-parameter, noise, delay, and longer-discharge validation remain mandatory before behavior cloning, DAgger, or bounded residual RL can be treated as deployment steps.
