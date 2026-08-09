# Stage4.2R3c3T13S24D1R14R8R33 uniformly supported rank-12 schedule-generalizing feedback preflight design

Status: prospectively frozen after final R8R32 and before any R8R33 transform,
fit, prediction, residual, tube, support result, plan, implementation, package,
controller action, raw, or TSC.

## 1. Purpose and allowed adaptation

R8R32 never reached regression. Its frozen PCA rank 32 was not defined in
344/1,161 outer fold/interval/offset heads; the independently reproduced
minimum numerical rank was 13. R8R33 changes only the retained representation
rank to a single new fixed value:

```text
retained PCA rank                12
selection rule                   one dimension below the independently
                                 reproduced all-fold minimum rank 13
rank search in R8R33             forbidden
```

This is a transparent new-development-identity choice made from consumed R8R32
evidence. It is not an amendment or reinterpretation of R8R32, and it is not
a fresh holdout claim. R8R32 remains a PCA32 representation-design FAIL.

R8R33 asks whether one uniformly supported, lower-variance causal q4
representation can pass the unchanged whole-pair and whole-schedule point,
tube, support, safety, and formal-planning gates.

## 2. Immutable source authentication and bank

Authenticate final R8R32 and its final primary, independent, model, compact,
state, and manifest hashes. Independently authenticate the transitive R8R31
raw sources and rebuild exactly:

```text
R8R23 trajectories                              432
R8R14 non-U/V signed-axis trajectories           96
R8R28 g2 trajectories                             32
R8R28 g3 trajectories                              0
total trajectories                               560
physical pairs                                     8
history contexts                                  16
schedule identities                               35
decision steps                     [10,12,14,16,18,22]
six-interval records                            3360
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

All rows remain consumed controller-development evidence. Every R8-family
trajectory is forbidden from expert, BC, DAgger, residual-RL, or other
learning data.

## 3. Causal feature and fixed representation

Keep R8R32's exact causal 44D base:

```text
four visible R/Z/Ip samples through current decision       12
current 14-coil measured applied current                   14
current-minus-previous-decision applied current            14
previous executed q4 coordinate                             4
```

Keep the ordered 18 current-candidate action terms and all forbidden-input
rules unchanged. For every outer fold, interval, and sample offset, fit the
transform only on that head's training rows:

```text
mu_j       = arithmetic mean(B[:,j])
scale_j    = max(RMS(B[:,j]-mu_j), 1e-12)
Z          = (B-mu)/scale
Z          = U diag(s) V^T
rank gate  = numerical rank >= 12 under s_i > 1e-12*s_0
scores     = Z V[:12]^T
```

Sign-canonicalize each retained right singular vector by making its
largest-absolute loading positive, with first index winning exact ties.
Construct exactly:

```text
[scores12,
 action18,
 scores12*q0,
 scores12*q1,
 scores12*q2,
 scores12*q3]

dimension = 12 + 18 + 4*12 = 78
```

Center and RMS-scale every transformed training column with floor `1e-12`.
Zero-variance columns stay present as centered zero columns. No global PCA,
future row, held fold, source label, outcome, or forbidden state may enter a
transform. Any rank failure is a model-design FAIL before regression, never an
execution/runtime failure.

## 4. Fixed regression and independent path

Use one head per interval and available future offset with the unchanged mask:

```text
maximum offsets by interval    [2,2,2,2,4,15]
outputs                        [R,Z,Ip,vR,vZ]
ridge penalty                  0.01
intercept                      unpenalized
feature/hyperparameter search  forbidden
outlier deletion               forbidden
response reweighting           forbidden
```

Primary uses centered normal equations. Independent reconstruction uses an
independently rebuilt raw bank, independent transform/rank code, and augmented
least squares. Discrete outcomes must match exactly; all load-bearing
predictions, residual maxima, tubes, planning and formal values must agree to
absolute `1e-12`. Different coefficient serialization is allowed, and both
artifact hashes must be recorded.

## 5. Unchanged outer model gates

Always audit both exclusions before planning:

```text
whole physical pair       8 folds
whole schedule           35 folds
```

Keep R8R32/R8R31's exact training-cardinality-matched pair tube and schedule
jackknife tube. For every interval/offset/component:

```text
tube = max(1.25 * maximum eligible absolute residual,
           [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s])
```

Required for both fold families:

```text
maximum point error       [0.015,0.015,3000,0.05,0.05]
maximum tube half-width   [0.025,0.025,5000,0.08,0.08]
containment               100%
whole-pair state support  100%
finite exclusions         0
forbidden inputs          0
tube clipping             forbidden
```

The planning tube is the componentwise maximum of the passed pair and
schedule tubes. Any rank, point, tube, containment, or support failure closes
planning and writes explicit phase-closed fields.

## 6. Unchanged support, planning, safety, and formal contract

Only after all model gates pass, reuse without alteration:

```text
8D q-transition support          [previous_q4,current_q4]
candidate count                  17
decision steps                   [10,12,14,16,18,22]
beam width                       512
execute                          first action only
measurement recentering          required
failed plan                      forbidden
fallback                         exact current-target hold
```

Retain exact Card15 issue/refresh, dynamic search radius 16, normalized
increment `<=0.25`, total action `<=1.0`, current utilization `<=0.55`, cosine
`>=0.98`, off-basis residual `<=0.10`, saturation, finite, solver, and
stop-before-failed-advance rules. Required offline planning result remains:

```text
safe searches                                  16/16
predicted repairs among ten failed baselines   >=1
fallback-plus-plan oracle                      >=7/16
baseline-pass regressions                       0/6
nonzero first action                            >=1
fault injections selecting hold fallback         6/6
```

Formal timing is immutable: arrive by 250 ms for slew 1.0/1.1 or 270 ms for
slew 0.9, hold/evaluate through 350/370 ms, R/Z 30 mm, speed 0.1 m/s, and
unchanged Ip and arrival streak. No horizon changes a deadline.

## 7. Routes and scope

```text
source/integrity/runtime failure
  UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP

rank, pair, schedule, point, tube, containment, support, or model failure
  UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC

model pass but planning authority failure
  UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED

all model and planning gates pass
  UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

Every route executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and
snapshot. A PASS authorizes only prospective design of a new finite real-TSC
safety sentinel. It is not Gate A and does not authorize learning.

## 8. Required validation

Before execution require project-venv compilation, all JSON, focused and full
Windows-shimmed tests, exact manifest hashes, and a fresh manifest-only
empty-directory direct-copy test. Transfer directories directly without an
archive. On the server use only the existing venv and require preflight,
hashes, JSON, compilation, all declared `bash -n`, focused tests, and full
tests before primary and independent zero-TSC audits. Keep large evidence on
the server and download only compact final evidence.
