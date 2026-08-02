# Stage4.2R3c3T13S18 pooled causal observer preflight forensic report

## Result

Stage4.2R3c3T13S18 passed its frozen development-only whole-pair audit.  It
authenticated all 144 immutable S16 raw trajectories and evaluated 128 signed
responses in eight outer whole-pair folds.  Containment, unchanged component
caps, and their joint gate passed 128/128.  This is not independent validation:
S18 consumed the same development evidence that selected the architecture.

The exact route is:

```text
POOLED_CAUSAL_OBSERVER_PREFLIGHT_PASS_FRESH_CAMPAIGN_REQUIRED
```

## Code and server identities

```text
local branch
  codex/stage4_2r3c3t13s16-whitened-basis

initial implementation / package-normalization checkpoints
  e940fc8 / d178001

exact Card15 reconstruction fixes
  fa76af1 / fba9144

final evaluation consistency fix
  960ac1e

remote source
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s16_runs/
  stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_165232

remote S17 source
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s17_audits/
  stage4_2r3c3t13s17_causal_multi_drift_belief_preflight_20260803_0f9ef6b

remote final output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s18_audits/
  stage4_2r3c3t13s18_pooled_causal_observer_preflight_20260803_fba9144

remote log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s18_pooled_causal_observer_preflight_20260803_fba9144.log
```

The fold artifact was frozen under `fba9144`.  The existing artifact was then
safely evaluated under `960ac1e`; that change only restored the identical
16-row batch matrix multiplication used at freeze time.  Model coefficients,
features, folds, saved predictions, tube, outcomes, and gates did not change.

## Source and output integrity

```text
authenticated source raw                         144 / 144
source raw bytes                                  8,188,964
source raw inventory digest
  b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668

outer folds                                             8 / 8
held rows per fold                                    16 / 16
response rows                                        128 / 128
unique response IDs                                  128 / 128
fold hashes exact                                      8 / 8
frozen predictions exact in final                    128 / 128
training-outcome accesses                                  896
held-outcome accesses before fold hash                       0
held-outcome accesses after freeze                         128
forbidden predictor inputs                                   0
new raw / snapshots / TSC calls / plant steps       0 / 0 / 0 / 0
```

Compact final hashes are:

```text
pooled_observer_artifact.json
  a7f35260e18894da763adba557b5c93ff599e2e4d81d94e4dd43e4824c9a5518
final_result.json
  12817946f1a1dee8557798f0e98a281e9015cfd7c26c07e4ca537729047836fb
server_independent_postprocess.json
  09f7377887f3a42a707456dc8ed8bafc21faddacae7034c3a412a7b297f7dc9c
source_authentication.json
  d1c2fe5d415b2b89386e0ef0b5d1cc13e37fde5aaecf7a657e8f46a4cabff06a
stage4_2r3c3t13s18_state.json
  e08054d3fbc30cfe7fe130b18a9b169a101be41c24d810b2b9157cd606e84f5d
```

All five compact JSON files parse.  Independent server-side reconstruction
reproduced the complete artifact and reported summary exactly.

## Numerical result

Seven outer folds selected ridge `0`; one selected `0.01`.

```text
containment / cap / joint                       128 / 128 / 128
maximum absolute error R/Z/vR/vZ/Ip
  2.7251667e-7 m / 4.4692463e-7 m /
  2.7251667e-5 m/s / 4.4692463e-5 m/s / 2.1063489 A
maximum halfwidth R/Z/vR/vZ/Ip
  1.7818369e-6 m / 1.9207120e-6 m /
  1.7818369e-4 m/s / 1.9207120e-4 m/s / 10.497754 A
maximum scaled point error                         0.0010531744
minimum containment margin R/Z/vR/vZ/Ip
  7.7406371e-7 / 9.2817267e-7 /
  7.7406371e-5 / 9.2817267e-5 / 5.5548684
```

## Incidents and classification

The first invocation at `d178001` stopped during prepare before creating an
output directory.  The current-run coordinate radius was mathematically
equivalent to the S17 construction but differed by at most
`1.36669495e-12` because it doubled one rounded interval instead of separately
reconstructing the nominal-center and probe intervals.  `fa76af1` implemented
the exact subtraction order.  Real raw then showed that response rows inherit
the frozen center through `r3c3t13s9_center_card15_fields`, while the S16
calibration-only center is empty on those rows; `fba9144` corrected that field
source.  A server scan then reproduced all four saved feature quantities with
maximum difference exactly zero over 128 rows.

The final run froze all eight fold artifacts, then stopped during evaluation.
Prepare used a 16-row matrix multiply while evaluate recomputed one row at a
time.  The largest difference was `7.10542736e-15 A` in Ip; batch recomputation
was bit-exact.  `960ac1e` made the frozen batch operation canonical and safely
resumed the unchanged artifact.  An intervening SSH session reset before its
foreground resume command started; state, artifact, and log audit proved no
server computation or file change occurred, after which resume was detached.

These were implementation/report-consistency errors.  They were not TSC,
restart, raw, statistics, observer-design, control, or plant failures.  The
final result has zero runtime/environment, source raw/restart, and
statistics/reporting errors.

## What is and is not frozen

The exact nine-feature causal architecture, whole-pair fitting procedure,
fixed ridge grid, four-times residual tube, current-run Card15 propagation,
and original caps are frozen for a prospective campaign.  S18 weights may not
be reused as validated weights.  S18 did not run a controller, optimizer,
MPC, TSC, restart, noise, disturbance, continuous-parameter, long-hold, expert
data, BC, DAgger, or RL test.

The next action is a separately preregistered training/calibration/fresh-
holdout campaign.  Only its training outcomes may select a pooled model;
calibration may enlarge the tube by a fixed rule; final holdout outcomes must
remain unopened until both artifacts are hashed.
