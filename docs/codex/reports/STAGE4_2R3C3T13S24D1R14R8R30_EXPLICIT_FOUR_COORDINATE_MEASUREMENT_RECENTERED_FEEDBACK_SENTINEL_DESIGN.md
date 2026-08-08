# Stage4.2R3c3T13S24D1R14R8R30 explicit-four-coordinate measurement-recentered feedback sentinel design

Frozen prospectively on 2026-08-09 after the R8R29 static feature-contract
failure was sealed at `7724088`, but before R8R30 config, implementation,
source-bank construction, feature value, model fit, tube, support hull, plan,
controller action, formal metric, package, deployment, raw, snapshot, Ray,
`gotsc`, TSC, or plant advance.

## 1. Scope and relation to R8R29

R8R29 failed before computation because its frozen 42D/133D U/V model could
not represent the six added non-U/V signed axes. R8R30 retains R8R29's exact
scientific question, authenticated source runs, 592-trajectory deduplicated
development bank, candidate directions/scales, six decision times, hard
action/current/Card15 boundary, measurement-recentered execution, fault
fallback, two-phase real execution, formal gate, independent audits, and
learning prohibition.

R8R30 prospectively replaces only the inconsistent action representation,
feature dimensions, task-step bank rows, model/support geometry, and stage
routes. It does not reinterpret R8R29 as a model result.

Exact R8R29 static audit:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R29_STATIC_DESIGN_AUDIT.md
SHA-256  b0b8ddfc2f7c7374c593609a3a2794db8cc825e3b7585995925330cab603854b
route    FULL_BASIS_MEASUREMENT_RECENTERED_FEEDBACK_PREFLIGHT_FAIL_NO_TSC
```

## 2. Immutable sources and exact bank

Authenticate the exact source contracts and hashes in Sections 2 and 5 of
the frozen R8R29 design, including final R8R23, R8R14, and R8R28. The
deduplicated inventory remains:

```text
R8R23 U/V and continuous-action model bank             432
R8R14 added non-U/V signed-axis rows                     96
R8R28 changed-timing U/V rows                            64
total trajectories                                      592
physical pairs / hidden-history contexts               8 / 16
global schedule identities                                 37
```

R8R14 UUUU/VVVV rows are excluded because R8R23 already represents those
schedule identities. No row may be duplicated to change fit weight.

For each trajectory construct causal interval rows at exactly:

```text
decision task steps  [10,12,14,16,18,22]
interval count per trajectory                           6
total interval records                     592 * 6 = 3552
```

At a task step where the source controller issued a new canonical increment,
`q` is that exact signed four-coordinate increment. At a task step where the
source only refreshed its active exact target, `q=[0,0,0,0]` means no new
canonical increment and target hold. For a baseline with no active target,
the same zero coordinate means unchanged zero continuation. Actual measured
currents and past physical actions remain in the causal history; no refresh
is relabeled as a nonzero axis.

Source raw stays on the server. All 592 trajectories are consumed MPC
development evidence, not fresh holdout or policy-learning data. No source or
new trajectory may enter expert, BC, DAgger, residual-RL, or other learning
data, and no prior R8-family TSC may be rerun.

## 3. Explicit four-dimensional action coordinate

Freeze the action coordinate order:

```text
q = [q_d0, q_d1, q_d2, q_d3]
```

`q_di = +s` requests `s` times canonical matrix column `i`; `q_di = -s`
requests its negative. All unspecified coordinates are exactly zero. The
canonical matrix digest remains:

```text
c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
```

The 17 ordered candidates become exactly:

```text
index  q
0      [ 0,     0,     0, 0]
1      [-1,     0,     0, 0]
2      [ 1,     0,     0, 0]
3      [ 0,     1,     0, 0]
4      [ 0,     0,    -1, 0]
5      [ 0,     0,     0,-1]
6      [ 0,     0,     0, 1]
7--11  [ 0,     0,     s, 0]  s=0.50/0.75/1.00/1.25/1.50
12--16 [ 0,    -s,     0, 0]  s=0.50/0.75/1.00/1.25/1.50
```

There is no simultaneous mixed-axis action and no post-result alphabet
expansion. Temporal switching is allowed only by choosing one frozen member
at successive decisions. A candidate must be inside the exact task-step
support hull; source absence closes it.

## 4. Exact causal and expanded features

Preserve R8R23 state, current, target, clock, and forbidden-input semantics,
but replace the two-coordinate fields with four-coordinate fields.

The exact 44D base order is:

```text
12  target-relative visible R/Z/Ip at states k-3,k-2,k-1,k
14  measured TSC-order coil currents at k, normalized by coil limits
14  current(k)-current(previous decision), normalized by coil limits
 4  previous decision's q divided by 1.5
--
44
```

Let current `q=[q0,q1,q2,q3]` and previous `p=[p0,p1,p2,p3]`. The exact 18D
action block order is:

```text
q0,q1,q2,q3,
q0*q0,q0*q1,q0*q2,q0*q3,q1*q1,q1*q2,q1*q3,q2*q2,q2*q3,q3*q3,
q0-p0,q1-p1,q2-p2,q3-p3
```

Append four 44D interaction blocks in order `base*q0`, `base*q1`,
`base*q2`, `base*q3`. The complete expansion is therefore:

```text
44 base + 18 action + 4*44 interactions = 238
```

Every dimension, order, normalization, and finite check is immutable. Pair,
history, partition, source identity/outcome, formal result, future state or
action, wire/vessel current, simulator internal, matched member, and future
R17 output remain forbidden. R8R23's failed bias-innovation update remains
disabled; causal feedback is live measurement re-centering and replanning.

## 5. Fixed model, validation, tube, and support

At each of six intervals, fit each available lead sample with a separate
multi-output ridge regression with intercept, ridge `1e-4`, no feature
selection, no hyperparameter search, and output order:

```text
[R/0.03, Z/0.03, Ip/10000, vR_m_per_s, vZ_m_per_s]
```

Each outer and nested fold excludes both histories of one whole physical
pair. Separately run whole-schedule jackknife over all 37 schedules, training
36 and holding 16 trajectories at a time. At identical interval and lead,
form componentwise absolute residual maxima times `1.25`, subject only to
physical floors `[0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]`. Combine pair
and schedule tubes componentwise by maximum. Tube clipping is forbidden.

The unchanged gates are:

```text
held point error R/Z/Ip/vR/vZ     <= 0.015/0.015/3000/0.05/0.05
reserved component containment                              100%
tube half-width R/Z/Ip/vR/vZ      <= 0.025/0.025/5000/0.08/0.08
held state support                                           100%
finite exclusions                                               0
forbidden inputs                                                0
```

For each decision task step build a convex hull over the exact 8D vector
`concat(previous_q,current_q)/1.5`. Use SVD affine tolerance `1e-12`, affine
reconstruction tolerance `1e-12`, hull inequality tolerance `1e-10`, and no
Qhull joggle. Outcome, residual, or formal result may not select support.
Primary and structurally independent bank, feature, fit, tube, support, and
gate paths must agree within `1e-12`.

Any failure ends R8R30 with zero Ray, TSC, controller action, plant advance,
raw, or snapshot.

## 6. Frozen receding-horizon controller

Preserve the exact R8R29 six decision steps `[10,12,14,16,18,22]`, beam width
`512`, lexicographic robust-formal ranking, first-action-only execution,
suffix discard, exact-target refresh between decisions, measurement
re-centering, and exact-target-hold fallback.

Each safe nonzero issue constructs the canonical coordinate `M @ q` from the
current measured-current center. A zero after an active issue performs exact
stored-target refresh; it does not cancel the active current target. Expected
maximum counts remain:

```text
issues          96 total = 24 safety + 72 qualification
refreshes      320 total = 80 safety + 240 qualification
```

Enforce unchanged hard gates on every issue and refresh:

```text
incremental normalized action L-infinity  <= 0.25
total normalized action absolute maximum  <= 1.0
current utilization                       <= 0.55
desired/applied cosine                     >= 0.98
relative off-basis residual                <= 0.10
exact Card15, no saturation/clipping, visible-state safety
safe stop before a failed plant advance
```

A nonzero first action may execute only from a safe, state-supported,
transition-supported robust-formal remaining plan. Best failing plans are
diagnostic only. Model exception, NaN, unsupported state/action, empty safe
set, solver timeout, and Card15 construction rejection each select the exact
fallback and must pass fault injection before TSC.

## 7. Offline and real gates

Before TSC, all model/support gates, all 16 searches, six fault injections,
and independent recomputation must pass. Require:

```text
predicted robust repair of failed baselines                 >= 1/10
predicted baseline regressions under fallback                  0/6
predicted fallback-plus-plan oracle                          >= 7/16
nonzero first-action selections                                 >= 1
```

If authorized, execute one deterministic rollout per context: safety `4`
then qualification `12`. Formal outcomes stay closed through safety and until
all 16 raw files pass independent causal decision/action replay. The
independent audit rebuilds every feature and decision from only the raw causal
prefix and its separately implemented 4D/44D/238D model chain.

The unchanged real scientific gate is:

```text
all integrity/runtime/restart/causality/safety/raw/replay gates pass
real repairs among ten failed baselines                      >= 1/10
real controller formal passes                               >= 7/16
regressions among six baseline passes                           0/6
primary/independent formal numerics, outcome, gate, route exact
```

Arrival remains 250/270 ms and hold remains through 350/370 ms with 30 mm
R/Z, 0.1 m/s speed, unchanged 10000 A Ip and streak 3. Report every miss,
fallback, model fault, issue/refresh, action/current maximum, signed margin,
and coarse tracking diagnostic without weakening a gate.

## 8. Frozen routes and authorization

```text
source/feature/model/tube/support/search/fault-injection failure before TSC
  EXPLICIT_FOUR_COORDINATE_FEEDBACK_PREFLIGHT_FAIL_NO_TSC

runtime/restart/causality/Card15/current/raw/replay/safety failure
  EXPLICIT_FOUR_COORDINATE_FEEDBACK_EXECUTION_OR_SAFETY_FAIL_STOP

integrity passes but real formal gate fails
  EXPLICIT_FOUR_COORDINATE_FEEDBACK_CONTROL_INSUFFICIENT_REDESIGN_REQUIRED

real formal gate passes
  EXPLICIT_FOUR_COORDINATE_FEEDBACK_CORE_PASS_GATE_A_QUALIFICATION_REQUIRED
```

R8R30 is immutable once any feature value or fit is computed. A PASS is a
finite deterministic controller-core result, not Gate A. Continuous
delay/gain/slew, mismatch, noise, disturbance recovery, independent long
hold, and residual-authority qualifications remain blocked and must be
prospectively frozen. A FAIL does not establish global plant unreachability.
All source and R8R30 trajectories remain forbidden from all learning data.
