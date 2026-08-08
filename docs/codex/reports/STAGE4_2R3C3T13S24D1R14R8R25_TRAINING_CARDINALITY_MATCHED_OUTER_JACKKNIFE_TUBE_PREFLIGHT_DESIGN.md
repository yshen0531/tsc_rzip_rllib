# Stage4.2R3c3T13S24D1R14R8R25 training-cardinality-matched outer-jackknife tube preflight design

Frozen prospectively on 2026-08-09 Asia/Shanghai after final R8R24 evidence,
route, compact audit, forensic report, and status were sealed at checkpoint
`f5e6e8d`, and before any R8R25 tube, containment value, cap result, candidate
plan, optimization result, or route was computed.

## 1. Activation and scientific question

R8R25 activates only for the exact final R8R24 route:

```text
CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED
```

Required R8R24 fingerprints are:

```text
primary detailed  0a795a08a98859ba84b567f1de299d489adf55a00c892cd17b78bfaebc16fd8b
primary summary   af587377782fec1bd78a10987578b64f3345cb8e67365a6210c6ab76d0d45596
independent       a48e45fba647229f7144f199e12fe342d758913786e47cdca70447bb01b62dd0
final report      581d6e7c8df11e6f50ff12c33ac71b1831f743f804b370f3445a87a95e1d73f8
model evidence    061897735bb01e4da75b388181ff97e83b1b7e51bc34f4f02551ef4f2333a30a
stage manifest    6bcb93d365835becfa41b73b45f95960f2f7fd6d890b8d1e4fa8d6cdff6533a6
stage state       a9129cb09551fc4c99bc06e4559464666163578560de5e15baa4fe43e17882f2
compact audit     90f0b6e3e5e2f406e27b6456f5a6dced61c4dac50443a53181c1c60a01448edc
```

R8R24 established that the unchanged cold point model passes every held
point-error and support gate and that a local inner-OOF tube contains every
held component. Its velocity tube is nevertheless too wide because its
calibration residuals come from models trained on only six physical pairs,
whereas every outer point model is trained on seven pairs and a final
development planner model would be trained on all eight.

R8R25 asks one narrow question: does a prospectively fixed, training-
cardinality-matched cross-outer residual envelope remain fully containing and
fit the unchanged caps without using the evaluated pair's own residual? This
is a finite development calibration question, not a statistical population
guarantee or controller result.

## 2. Immutable evidence and prohibition boundary

Authenticate without modification or rerun:

1. final R8R24 primary, independent, final, model, manifest, state, and compact
   evidence;
2. the exact R8R23 and transitive source fingerprints authenticated by R8R24;
3. the exact 432-trajectory bank and feature/target digests; and
4. R8R24's exact reproduction of the R8R23 cold point model.

No R8-family TSC trajectory may be rerun. The bank is consumed development
evidence and may not be described as a fresh holdout. Every R8-family
trajectory remains forbidden from expert, BC, DAgger, residual-RL, or other
policy-learning data.

R8R25 executes zero Ray, `gotsc`, TSC, controller, plant advance, snapshot,
or raw creation. It does not modify a source stage.

## 3. Point predictor remains unchanged

Recompute, rather than load, the exact R8R23/R8R24 cold predictor:

```text
causal base feature dimension                   42
fixed action-expanded feature dimension        133
model family           multi-output ridge with intercept
ridge penalty                                 1e-4
outer split                      eight whole physical pairs
separate model per decision interval          yes
masked final-horizon outputs                   yes
feature selection / PCA / search                no
innovation or bias update                       no
```

The causal features, action basis, output order, normalizations, decision
steps `[10,14,18,22]`, masked 13/15-sample final interval, and forbidden
predictor fields remain byte-for-byte the R8R24 contract. Pair, history,
source, schedule, future state/action, wire/vessel current, simulator
internals, and formal outcomes may not enter a point fit or live query.

Primary reproduction must match R8R24 feature/target digests, every outer
model, point metric, and support result within absolute tolerance `1e-12`.
Independent code must rebuild them without importing the R8R23, R8R24, or
R8R25 primary implementation.

## 4. Training-cardinality-matched cross-outer envelope

Construct the eight ordinary outer folds first. For physical pair `p`, fit
the unchanged point model on the other seven complete physical pairs and
retain absolute OOF residuals for every trajectory, decision interval, lead
sample, and output in `p`. These are the same seven-pair-trained point
predictions already required by the outer point gate.

For evaluation of held pair `p`, calibrate its tube only from outer OOF
residual records belonging to the other seven held pairs. The residuals from
`p` are completely excluded from its own tube. Thus no evaluated outcome
calibrates its own bound. All calibration predictors were trained on seven
physical pairs, matching the training cardinality of the evaluated outer
predictor.

At each fixed decision interval and lead-sample index:

```text
calibration source              seven other outer OOF physical pairs
same interval required                                      yes
same lead sample required                                    yes
feature-distance or learned metric                           none
residual aggregation                        componentwise maximum
reserve multiplier                                         1.25
```

Define the held-pair tube half-width componentwise as:

```text
max(
  1.25 * maximum absolute cross-outer residual,
  fixed physical point-error floor
)
```

The unchanged physical floors are:

```text
R       0.015 m
Z       0.015 m
Ip   3000 A
vR      0.050 m/s
vZ      0.050 m/s
```

This rule has no neighbor count, distance scaling, residual quantile,
outlier deletion, fitted uncertainty model, or hyperparameter selection. A
tube may never be clipped to make it pass.

If the model gate passes and planning opens, fit the point predictor on all
eight development pairs and calibrate each planning interval/lead tube from
all eight outer OOF residual groups. The planning tube is fixed by
interval/lead and does not use a predicted outcome or label.

## 5. Unchanged model and support gates

Across all eight outer held pairs, require:

```text
maximum R point error                         <=0.015 m
maximum Z point error                         <=0.015 m
maximum Ip point error                      <=3000 A
maximum vR point error                        <=0.050 m/s
maximum vZ point error                        <=0.050 m/s
reserved component containment                  100%
maximum reserved R half-width                <=0.025 m
maximum reserved Z half-width                <=0.025 m
maximum reserved Ip half-width              <=5000 A
maximum reserved vR half-width                <=0.080 m/s
maximum reserved vZ half-width                <=0.080 m/s
R8R23 support rate                               100%
finite exclusions                                  0
forbidden inputs                                   0
```

Retain the exact R8R23 support rule: each held query's closest outer-training
origin distance may not exceed `1.5` times the maximum training-only nested
whole-pair nearest-neighbor distance. The cross-outer tube cannot waive
support.

Primary and independent implementations must agree on features, outer fits,
residual-group digests, every interval/lead tube, containment, support, gate,
and route within absolute tolerance `1e-12`.

## 6. Conditional action-tree planning

Planning remains closed unless every source, point, support, cross-outer
tube, containment, cap, finite, forbidden-input, and independent-agreement
gate passes. A failure writes explicit zero/sentinel planning fields and
stops with zero plant advance.

If opened, use the exact R8R24/R8R23 closed action tree:

```text
zero plus ten R8R22 cumulative U/V levels       11
decisions                                        4
maximum unfiltered sequences                14,641
```

At each decision, recursively rebuild the exact causal feature from predicted
visible history and deterministic exact applied current. Use the all-eight-
outer-OOF interval/lead tube and require unchanged support. Every action must
pass the exact Card15 issue/refresh, incremental `<=0.25`, total action
`<=1.0`, current utilization `<=0.55`, cosine `>=0.98`, off-basis `<=0.10`,
finite, saturation, forbidden-input, and safe-stop gates.

The formal contract remains immutable:

```text
normal slew: arrive by 250 ms, hold through 350 ms
weak slew:   arrive by 270 ms, hold through 370 ms
R/Z tolerance 30 mm; speed 0.1 m/s; frozen Ip and arrival streak
```

For each of 16 development contexts, enumerate deterministically and select
the lexicographically first minimum-cost sequence satisfying the full reserved
tube. Zero remains the fallback before intervention. No measured
counterfactual state may be stitched into a predicted branch.

## 7. Gates and routes

An R8R25 scientific PASS requires all model gates plus:

```text
safe complete predicted plans                       16/16
predicted repairs among ten failed baselines         >=1
predicted regressions among six baseline passes        0
baseline-plus-policy predicted oracle              >=7/16
```

Routes are frozen to:

```text
source, causal, integrity, or independent failure:
  R8R25_INTEGRITY_FAIL_STOP

point, support, cross-outer tube, containment, or cap failure:
  TRAINING_CARDINALITY_MATCHED_OUTER_JACKKNIFE_TUBE_INSUFFICIENT_REDESIGN_REQUIRED

model pass but planning/repair/oracle failure:
  TRAINING_CARDINALITY_MATCHED_TUBE_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED

all model and planning gates pass:
  TRAINING_CARDINALITY_MATCHED_OUTER_JACKKNIFE_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED
```

No gate, floor, reserve, cap, or aggregation rule may be changed after an
R8R25 output is opened.

## 8. Authorization boundary

Even a complete R8R25 PASS authorizes only design and preregistration of a
new-identity fresh finite real-TSC controller sentinel with an explicit
safety-first partition, fresh finite contexts or parameters, independent raw
and formal auditing, hard fallback, and zero learning-data reuse.

R8R25 is not real MPC, formal-control qualification, or Gate A. Gate A,
expert data, BC, DAgger, and residual RL remain blocked.
