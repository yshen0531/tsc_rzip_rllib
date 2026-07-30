# Stage2 three-mode real-TSC trajectory optimization

- Source Stage1.1 run: `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage1_1_runs/stage1_1_svd234_strict_validation_100ms_20260718_025916`
- Start folder: `1100ms`
- Horizon: 100 ms
- Action space: first 3 validated SVD modes
- Parameterization: 5 nodes x 3 modes = 15 variables
- Optimizer: covariance-adapting cross-entropy method
- Linear R/Z/Ip model: pre-screening only
- Velocity, hold gates, and final ordering: real TSC only

## Optimization state

- Completed generations: 8
- Finished: True
- Stop reason: `max_generations`

## Stage1.1 SVD3 benchmark

- scale 0.75: terminal error 47.267 mm, terminal speed 0.06998 m/s, late speed RMS 0.07083 m/s
- scale 0.85: terminal error 42.234 mm, terminal speed 0.16067 m/s, late speed RMS 0.12417 m/s
- scale 1.00: terminal error 34.785 mm, terminal speed 0.30857 m/s, late speed RMS 0.25061 m/s

## Best real-TSC candidate

- Candidate: `g007_1417404bd2e7a119`
- Generation: 7
- Gate: `PASS_DAMPED_HOLD_40MM`
- Terminal R error: -25.694 mm
- Terminal Z error: 32.069 mm
- Terminal R/Z speed: 0.01056 m/s
- Late velocity RMS: 0.08661 m/s
- Trailing +/-30 mm samples: 0
- Trailing +/-40 mm samples: 10

## Confirmation verdict

- Verdict: `PASS_DAMPED_HOLD_40MM_CONFIRMED`

## Interpretation rule

Stage2 is successful only when real TSC satisfies the strict 30 mm terminal hold gate. The linear model is never allowed to declare a velocity or hold success.
