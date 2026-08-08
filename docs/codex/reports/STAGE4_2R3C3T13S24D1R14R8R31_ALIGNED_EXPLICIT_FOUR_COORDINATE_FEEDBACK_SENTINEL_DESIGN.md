# Stage4.2R3c3T13S24D1R14R8R31 aligned explicit-four-coordinate feedback sentinel design

Frozen prospectively on 2026-08-09 after R8R30's static timing failure was
sealed at `b73a8c1`, but before R8R31 config, implementation, bank row,
feature value, fit, tube, support, search, controller action, metric, package,
deployment, raw, snapshot, Ray, `gotsc`, TSC, or plant advance.

## 1. Exact correction and inherited contract

R8R31 incorporates the complete R8R30 explicit-four-coordinate design with
one source-bank correction: exclude every R8R28 g3 trajectory because its
issues at task steps 13 and 19 fall inside R8R30 prediction intervals.

Load-bearing predecessor documents are:

```text
R8R30 design
  docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R30_EXPLICIT_FOUR_COORDINATE_MEASUREMENT_RECENTERED_FEEDBACK_SENTINEL_DESIGN.md
  6a65a7ed7e84cbd89f420e2461928ce0cafcf30a96768b8836d67ccc9508d1f4

R8R30 static timing audit
  docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R30_STATIC_TIMING_AUDIT.md
  5822af88f966207035ac45571a64b0a82fca7845666386d112aa691adf3bbde5
```

Unless replaced below, every R8R30 source hash, feature order, model/tube
algorithm, candidate, decision, support tolerance, search rank, action/current
gate, fallback, fault injection, two-phase execution rule, formal gate,
independent audit, route meaning, Gate A boundary, and learning prohibition is
immutable in R8R31.

## 2. Exact aligned bank

The only accepted source inventory is:

```text
R8R23 bank                                             432
R8R14 direction 0 -/+                                 32
R8R14 direction 1 +                                   16
R8R14 direction 2 -                                   16
R8R14 direction 3 -/+                                 32
R8R28 g2 UUUU/VVVV only                               32
R8R28 g3                                               0
total                                                 560
```

All included new-major-issue clocks are subsets of:

```text
[10,12,14,16,18,22]
```

Between adjacent model decisions, each included source uses only exact-target
refresh; there is no unencoded new canonical increment. Six rows per
trajectory give exactly:

```text
physical pairs / contexts                         8 / 16
global schedule identities                            35
trajectories                                         560
interval records                                    3360
```

Authenticate all final R8R23/R8R14/R8R28 source hashes from R8R30, plus the
R8R28 combined raw digest, before selecting g2 by immutable spec identity.
Selection may use only `grid_id == "g2"`; outcome, margin, history, or raw
value may not select a row. The excluded g3 raw remains immutable on the
server and is not interpreted as a model failure.

## 3. Explicit feature, action, and support identities

Use R8R30 exactly:

```text
q order             [d0,d1,d2,d3]
base feature        44
action block        18
interaction blocks  4 * 44
expanded feature    238
output order        [R/0.03,Z/0.03,Ip/10000,vR,vZ]
ridge               1e-4 with intercept
decision steps      [10,12,14,16,18,22]
candidate count     17
```

At a source refresh origin, `q=0` means no new canonical increment/current-
target hold and no within-interval major issue. Task-step support is the
convex hull of `concat(previous_q,current_q)/1.5`, with R8R30's unchanged SVD
and hull tolerances.

Whole-pair nested residual tubes and 35-schedule jackknife now train 34 and
hold exactly 16 trajectories for each schedule. Retain multiplier `1.25`,
physical floors, componentwise maximum combination, no clipping, all point/
tube/support caps, and `1e-12` primary-independent tolerance.

## 4. Offline authorization and conditional real controller

The zero-TSC gate remains:

```text
all source/bank/feature/model/tube/support/finite/forbidden gates pass
all 16 searches safe
predicted repair                                           >= 1/10
predicted fallback-plus-plan oracle                        >= 7/16
predicted baseline-pass regressions                           0/6
nonzero first action selections                                >= 1
six fault injections exact
primary/independent bank, fit, tube, support, plan, gate exact
```

Any failure stops before TSC. If and only if this passes, execute safety `4`
then qualification `12`, with formal outcomes closed until all 16 raw files
pass independent causal replay. The real gate remains repair `>=1/10`, formal
controller pass `>=7/16`, baseline-pass regression `0/6`, and exact dual
agreement under unchanged 250/270 ms arrival and 350/370 ms hold.

Maximum controller event counts remain 96 issues and 320 refreshes. Every
action enforces exact Card15, incremental `<=0.25`, total `<=1.0`, current
use `<=0.55`, cosine `>=0.98`, off-basis `<=0.10`, no saturation/clipping,
visible-state safety, and stop-before-failed-advance.

## 5. Frozen routes

```text
source/bank/feature/model/tube/support/search/fault failure before TSC
  ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_PREFLIGHT_FAIL_NO_TSC

runtime/restart/causality/Card15/current/raw/replay/safety failure
  ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_EXECUTION_OR_SAFETY_FAIL_STOP

integrity passes but real formal gate fails
  ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_CONTROL_INSUFFICIENT_REDESIGN_REQUIRED

real formal gate passes
  ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_CORE_PASS_GATE_A_QUALIFICATION_REQUIRED
```

R8R31 is immutable once any bank row or feature is built. A PASS is only a
finite deterministic controller core and does not satisfy Gate A. A FAIL is
not global plant unreachability. Every source and R8R31 trajectory remains
forbidden from all learning data.
