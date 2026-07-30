# Stage2.1 Report

- Source Stage2 run: `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_runs/stage2_svd3_real_tsc_cem_100ms_20260720_114614`
- Real-TSC evaluations: **1536**
- Successful evaluations: **1536**
- Strict 30 mm gates: **0**
- Relaxed 40 mm gates: **598**
- Confirmation verdict: **PASS_DAMPED_HOLD_40MM_CONFIRMED_ONLY**
- Damped archive: **64**
- Precise-but-underdamped archive: **32**

## Method

The Stage2 hard gate was not loosened. Stage2.1 warm-started from the completed Stage2 run, kept independent damped and precise archives, concentrated search on the final three nodes, and used explicit precise-front/damped-tail bridges.

The continuous objective uses mean, maximum and terminal excess outside the 30 mm box over the final window. This is a ranking signal only; strict success still requires the original final-three-step, velocity and Ip conditions.

## Best candidate

- Candidate: `s21g006_0b291509e6d6e307`
- Gate: **PASS_DAMPED_HOLD_40MM**
- R error: **-27.318 mm**
- Z error: **31.070 mm**
- Terminal velocity: **0.006701 m/s**
- Late velocity RMS: **0.087560 m/s**

