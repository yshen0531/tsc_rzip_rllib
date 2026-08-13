# Post-NR2R1 read-only descriptive audit

Status: documentation-only, zero new TSC, zero fitting/training.

This audit supports only the descriptive numbers in
`docs/codex/reports/RGEO_ZGEO_1MS_POST_NR2R1_ARCHITECTURE_REASSESSMENT.md`.
The machine-readable scalar result is `RESULT.json`.
It uses the 28 locally retained NR2R1 development/calibration compact records
under `.codex_tmp/nr2r1_evidence/records/`.  Those files are not added to Git;
their immutable filename/SHA-256 inventory is `INPUT_SHA256SUMS`.  The ordered
inventory contains 28 files, 2,431,302 bytes and has SHA-256
`98f6bd1992b9681ec548e4bbc8f1f6b6c7332309522a81e961c8be57edbd3c49`
when each line is `filename`, one ASCII space, SHA-256, and LF.

The invalidly opened NR2R1 holdout is excluded.  Development/calibration is
used here as consumed architecture-development evidence and may not become a
blind NR2R2 calibration or holdout partition.

## Independent scalar definitions

For every included record, read the 17 saved states without fitting a model.

- Envelope minima/maxima and side counts are direct scalar reductions.
- For coordinate `y`, the reported time-path fraction is:

  ```text
  overall_mean = mean over every trajectory and time
  time_mean[t] = mean over trajectories at time t
  between_time_SS = n_trajectories * sum_t((time_mean[t]-overall_mean)^2)
  total_SS = sum_trajectory,time((y-overall_mean)^2)
  fraction = between_time_SS / total_SS
  ```

  This is a descriptive sum-of-squares fraction over correlated deterministic
  trajectories, not a significance test or causal variance decomposition.
- For each declared plus/minus trajectory pair and horizon, the signed-pair
  half-difference is `(state_plus-state_minus)/2`.  Its maximum is a
  descriptive odd component, not a zero-baseline response or Jacobian.
- The step-11 comparison selects only development/calibration impulse records
  whose saved step-11 actual current vector is q0 and whose issued command
  delta is the all-zero vector.  It reports componentwise range of the current
  state, successor increment and wire-current vector.  It does not fit,
  regress or claim an exact hidden-state alias.
- Model-selection means and calibrated half-width locations are read from the
  tracked `fit_calibrate.json` and `corrected_calibration_audit.json`; no
  saved model is executed.

## Reproduced values

```text
trajectories / states                         28 / 476
unique physical start                              1
R span                                      9.5273635 mm
Z span                                     11.9430495 mm
R-R_mid range                      -92.7922615..-83.2648980 mm
HFS states                                      476/476
mean horizon-16 delta         -9.48479045 mm / +11.87758430 mm / -165.439193 A
between-time SS fraction R/Z/Ip   0.998826302 / 0.999771288 / 0.972727729
maximum signed half-difference R/Z       0.3752675 / 0.2193010 mm
step-11 current-state span       0.145713 / 0.104099 mm / 25.1849 A
step-11 next-increment span      0.8315565 / 0.3494700 mm / 13.5499 A
step-11 maximum wire-component span                     10.403 A
development selection mean ARX/GRU/LSTM/TCN
                              1.111476 / 1.171062 / 1.147252 / 1.119913
maximum calibrated R/Z half-width horizon                  13 (all classes)
```

Horizon 13 is state 13 after issued steps 0--12.  In the impulse schedule it
is after the step-9 full pulse and steps 10--12 q0 commands, immediately
before the new step-13 full command.  That command first affects horizon 14.
