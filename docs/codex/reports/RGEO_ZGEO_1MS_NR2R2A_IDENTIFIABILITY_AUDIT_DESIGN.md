# R_geo/Z_geo 1 ms NR2R2A identifiability audit design

Status: prospectively frozen local audit design on 2026-08-13
Asia/Shanghai, before implementation or result generation.

Stage identity:

```text
rgeo-zgeo-1ms-nr2r2a-identifiability-audit-v1
```

This stage is the first executable step of the post-NR2R1 revised route.  It
is deliberately smaller than a new model comparison: authenticate and
measure the causal input/history geometry that NR2R1 actually supplied, then
freeze the deployable state boundary and the questions that the next fresh
TSC sentinel must answer.

It runs locally only.  It authorizes no server command, server-raw read, TSC,
plant advance, snapshot/replay, controller, fitting, training, optimization,
MPC, RL, expert data or new trajectory generation.

## 1. Immutable physical and signal contract

The audit cannot change these accepted definitions:

```text
fixed takeover time                         1100 ms
control period                                 1 ms
per-coil single-turn current step          <= 0.3 A absolute
equality at either endpoint                  allowed
coil order                                      TSC
Card15 unit                                kA-turn
R_geo                 (boundary_R_min + boundary_R_max) / 2
Z_geo                 (boundary_Z_min + boundary_Z_max) / 2
boundary source                 same valid boundary at the same state/time
invalid or missing boundary                  fail closed; no fallback
R_mid            (inner_limiter_midplane + outer_limiter_midplane) / 2
side                 HFS exactly when R_geo < R_mid, otherwise LFS
R_mid crossing                     belief/history identity never resets
Ip                    observed/coupled soft-hold and hard-safety quantity
```

No `xmag/zmag`, pressure-weighted center, split R/Z source or silent fallback
may enter the audit.

## 2. Frozen evidence boundary

The only trajectory inputs are the 28 NR2R1 development/calibration compact
records whose filenames and SHA-256 values are already frozen in:

```text
docs/codex/audits/
  rgeo_zgeo_1ms_post_nr2r1_reassessment_20260813/
  INPUT_SHA256SUMS
```

Their ordered inventory identity is:

```text
files                                      28
bytes                               2,431,302
ordered inventory SHA-256
98f6bd1992b9681ec548e4bbc8f1f6b6c7332309522a81e961c8be57edbd3c49
```

The implementation must reject a missing, extra or hash-mismatched selected
record.  It must reject any input whose declared split is `holdout`.  NR2R1
development/calibration is already consumed architecture-development
evidence; it cannot later be relabelled as blind NR2R2 calibration/holdout.
The invalidly opened NR2R1 holdout may not be read, summarized or used to
choose any field, window, action or threshold.

The saved neural/ARX bundle is also excluded.  The audit may read tracked
NR2R1 result scalars for source authentication, but it may not execute or
refit a saved model.

## 3. Required input authentication

For every selected compact record, the primary implementation must verify:

1. filename and file SHA-256 match the frozen inventory;
2. campaign identity is
   `rgeo_zgeo_1ms_nr2r1_q0_structural_residual_v1`;
3. `passed=true`, `plant_advances=16`, exactly 17 states and 16 actions;
4. the embedded spec equals the deterministic tracked NR2R1 spec;
5. state times are exactly 1100 through 1116 ms in 1 ms increments;
6. action issue steps/times are exactly 0 through 15 / 1100 through 1115 ms;
7. all R/Z/Ip/current/action fields used below are finite and correctly
   shaped; and
8. all states use valid paired `R_geo/Z_geo`, finite `R_mid`, and a side label
   equal to the deterministic `R_geo-R_mid` rule.

This is compact-record authentication, not a replacement for the already
completed immutable-raw NR2R1 audit.

## 4. Frozen descriptive computations

No regression target or model coefficient is permitted.  The following
reductions are fixed before implementation.

### 4.1 Work-domain geometry

Recompute state count, unique physical 1100 ms starts, R/Z/Ip ranges,
`R_geo-R_mid` range, HFS/LFS counts, per-time means and endpoint changes.  For
each of R/Z/Ip, report the between-time sum-of-squares fraction using the
definition frozen in the post-NR2R1 audit.  It is descriptive dataset
geometry, not causal attribution or a significance test.

Report Pearson correlation of state time with R/Z/Ip only as another
descriptive collinearity measure.  Do not assign the common path to natural
drift because the campaign has no independent full-horizon q0 baseline.

### 4.2 Two causal action coordinates

For issue step `k`, compute both:

```text
issued_increment[k] = saved command_delta_decimal_a_tsc[k]
q0_offset[k]        = exact target current[k] - exact q0 target current
```

The first is what the NR2R1 model was given.  The second is the physically
clear deviation about the commanded q0 baseline.  They answer different
questions and must never be silently interchanged.

For each split and coordinate, and for every lag length `L=1..16`, construct
only complete, unpadded causal rows:

```text
[u[k-L+1], ..., u[k]]   for every trajectory and k=L-1..15
```

No zero padding, first-frame repetition, circular padding or cross-trajectory
history is allowed.  Scale the whole matrix by the fixed scalar `1/0.3 A`;
do not normalize columns from observed statistics.  Compute singular values,
rank with `tol=max(n_rows,n_cols)*eps*s_max`, relative smallest retained
singular value, and condition number only when the matrix has full column
rank.  A static `L=1` rank of 14 does not qualify any larger memory kernel.

For each split/coordinate, report the largest full-column-rank `L`, but do not
call it an adequate physical memory horizon.  Present 16 ms evidence can set
only a lower bound on required prospective tail measurement.

### 4.3 Baseline, action-age and factorization gaps

Recompute, without fitting:

- the number of full-horizon all-q0 trajectories;
- maximum absolute q0 offset and issued increment;
- whether any current target moves cumulatively outside `q0 +/- 0.3 A`;
- schedule/action-age counts for zero, half and full targets;
- signed-pair half-differences and equal-q0/zero-increment successor spreads;
- exact number of physical 1100 ms starts, side classes and independent
  position anchors; and
- whether the same declared primitive is repeated at different positions or
  under prospectively matched position/time/history strata.

The absence of a matched factor is a design gap, not a zero physical effect.
Plus/minus averaging is not a substitute for an all-q0 baseline.

### 4.4 History initialization and representation audit

The implementation must authenticate from source that the NR2R1 ARX feature
uses eight frames and left-pads short histories by repeating the first frame.
It must record that this is formal causal bookkeeping but not authentic
pre-1100 history.  It must also authenticate that absolute `step/16` enters
the model feature and that no explicit stable low-order passive/innovation
state is present.

These are source-contract facts.  They are not scored as model predictions.

## 5. Deployable state boundary frozen by NR2R2A

The first successor model may use only fields that can be carried by the NR0
causal contract and the qualified 1 ms actuator path:

```text
required observable context
  R_geo, Z_geo, Ip
  14 actual coil-current readbacks in TSC order
  issued/serialized/quantized/applied action identities and values
  exact queue/effect age and missing-data masks
  time since 1100 ms, dt, R_geo-R_mid

causal belief (estimated, not directly exposed as a TSC hidden label)
  velocity/drift state
  low-order passive/innovation memory
  calibrated initial uncertainty at 1100 ms
```

The 48-wire current vector is an offline diagnostic/possible auxiliary label
only.  It cannot be a required controller input unless a separate deployment
interface audit proves that it is truly available.  Future reference,
source/history IDs, restart hashes, outcome labels and TSC-only hidden state
are forbidden dynamics-model inputs.

The first successor must not initialize belief by claiming repeated/zero
padding is real history.  If no authentic pre-1100 deployable window exists,
it must use a separately calibrated 1100 ms initializer/set prior and retain
the corresponding uncertainty.

## 6. What this audit is allowed to conclude

NR2R2A may conclude only:

1. the finite state/action/history geometry of the consumed NR2R1
   development/calibration records;
2. which lagged action matrices are supported without artificial padding;
3. which deployable fields and initialization semantics are admissible; and
4. which prospective baseline/tail/repeatability experiments are necessary.

It cannot qualify a predictor, tube, controller, recovery policy, moving-
prefix Oracle, position-dependent gain, hidden-state observer or control
authority.

## 7. Independent recomputation and stop routes

A structurally separate verifier must independently parse the same frozen
inventory and reproduce all load-bearing scalar/rank tables.  It must not
import computation helpers from the primary audit module.

Agreement requirements are exact for counts, identities, ranks and boolean
facts; numeric values must agree to `1e-12` absolute and relative tolerance.

Frozen routes are:

```text
input/hash/schema/forbidden-holdout failure
  ONE_MS_NR2R2A_INPUT_AUDIT_FAIL_STOP

primary/independent mismatch
  ONE_MS_NR2R2A_INDEPENDENT_RECOMPUTE_MISMATCH_STOP

complete, agreeing audit
  ONE_MS_NR2R2A_IDENTIFIABILITY_AUDIT_COMPLETE_SOURCE_BASELINE_RECOVERY_DESIGN_REQUIRED
```

The last route is not a model PASS and does not itself authorize TSC.  It may
advance only to prospectively freezing a separate source q0-baseline,
repeatability and hold/recovery sentinel.

## 8. Mandatory counters and evidence

The result must explicitly record:

```text
server accesses                         0
server raw reads                        0
new TSC / plant advances                0
new snapshots / replay branches         0
model fits / training runs              0
holdout records read                    0
controller / optimizer executions       0
```

The tracked audit evidence will contain the design, exact input inventory
identity, primary compact JSON, independent compact JSON, their SHA-256
values, tests and a concise report.  Raw compact trajectories remain
untracked and immutable in their existing local evidence tree.

## 9. Pause boundary

After the audit agrees, implementation must still pause before any new TSC
until the next stage has prospectively frozen its q0-command baseline length,
repeat count, boundary/Ip/current stops, full-tail observation rule and a
non-circular active hold/backup/recovery qualification route.  Returning coil
currents to q0 is not evidence that the plasma is held or recoverable.
