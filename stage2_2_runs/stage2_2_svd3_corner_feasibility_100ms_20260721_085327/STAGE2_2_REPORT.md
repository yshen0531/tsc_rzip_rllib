# Stage2.2 strict-corner feasibility report

- Source Stage2 run: `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_runs/stage2_svd3_real_tsc_cem_100ms_20260720_114614`
- Source Stage2.1 run: `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_20260720_151221`
- Combined unique real-TSC source vectors: **2965**
- New Stage2.2 real-TSC evaluations: **576**
- Successful evaluations: **576**
- Strict 30 mm holds: **0**
- Relaxed 40 mm holds: **153**
- Confirmation verdict: **PASS_DAMPED_HOLD_40MM_CONFIRMED_ONLY**

## Method

The hard Stage2 gate is unchanged. Stage2.2 recomputes the final-three-sample rectangular-box condition from every raw Stage2 and Stage2.1 TSC trajectory, then minimizes the largest normalized violation among final-three position, terminal speed, late speed and terminal Ip.

The search uses strict-speed damped, near-position precise, minimum-violation corner and strict archives. Three independent centers receive deterministic antithetic probes; all model predictions are ranking aids only.

## Best new corner candidate

- Candidate: `s22g005_adf586ba25597d7e`
- Gate: **POSITION_40MM_SPEED_FAIL**
- Final-three maximum box error: **31.044 mm**
- Terminal speed: **0.026640 m/s**
- Late speed RMS: **0.102958 m/s**
- Maximum normalized violation: **0.034812**
- Sum normalized violation: **0.064393**

