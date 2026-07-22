# Stage3.1 changelog

## Scientific changes from Stage3.0

1. Reuses the completed 420-row Stage3.0 catalog; the 96-run screen is not
   repeated.
2. Moves the first variable action from step 9 to step 8.
3. Expands the local control vector from 18 to 21 variables:
   steps 8-14 x three SVD modes.
4. Increases optimization from at most three to at most six SQP rounds, with a
   two-round no-improvement stop.
5. Uses two centers and forces different nominal families for the first two
   rounds.
6. Runs 42 real finite-difference probes per center and 15 real SQP proposals
   per center.
7. Tests 0.5x, 1.0x, and 1.5x SQP steps.
8. Replaces unconditional trust shrinkage with measured expand/hold/shrink
   rules.
9. Computes trust ratios at the same requested arrival endpoint for center,
   prediction, and real result.
10. Tracks trust scales by slot+nominal as well as nominal and slot fallbacks.
11. Keeps the Stage3.0 30 mm / 0.10 m/s / Ip hard gate unchanged.

## Controller-identification changes

1. Identifies a 35x21 real-TSC Jacobian.
2. Supports one optional re-identification pass when an identification probe
   itself becomes the new best candidate.
3. Normalizes R/Z, R/Z velocity, and Ip by their gate scales before computing
   gains.
4. Uses truncated SVD plus ridge regularization.
5. Exports time-indexed causal gains for steps 8-14.
6. Freezes unavailable Jacobian columns and represents unavailable diagnostics
   with JSON null, never NaN.

## Limited feedback POC

1. Adds 24 real-TSC causal-feedback rollouts:
   eight scenarios x scales 0, 0.5, and 1.
2. Includes +/-2 mm target shifts and +/-Mode-1 disturbances.
3. Applies only the current executable three-mode correction.
4. Scores 0.5 and 1.0 as two globally fixed controller scales and selects one
   scale for all scenarios; it never picks a different gain per scenario.
5. Bounds feedback by mode and existing current/slew constraints.
6. Never sets `online_feedback_validated` or `robustness_validated` true.

## Integrity and engineering changes

1. Complete standalone tree; no Git/network/external source-code dependency.
2. Strict JSON finite-value checks throughout.
3. Content fingerprint of all referenced Stage3.0 real-TSC results and key
   Stage3.0/Stage2.2 inputs.
4. Resume refuses changed source content.
5. Early source-result existence validation.
6. Exact Stage3.0 open-loop action reconstruction test.
7. Fixed shell behavior under `set -u` for RAY/TMP variables.
8. Runtime workspaces remain under `/tmp` and are cleaned after candidates and
   process exit.
9. Category-aware deterministic confirmation preserves distinct nominal
   families.
10. Report keeps the final-task boundary explicit.
