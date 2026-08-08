# Stage4.2R3c3T13S24D1R14R8R23 causal online-innovation receding-horizon preflight design

Frozen prospectively on 2026-08-09 Asia/Shanghai while the already authorized
R8R22 held-qualification trajectories were still running, after the R8R22
offline and safety raw audits passed, but before the R8R22 qualification raw
audit, formal metrics, repair count, oracle, verdict, or final route were
opened. No R8R22 qualification outcome was used to choose this design.

## 1. Conditional activation and scientific question

R8R23 is a zero-new-TSC preflight. It becomes active only if final R8R22
primary and independent audits agree exactly, all source/offline/raw/safety
and formal-integrity gates pass, and the final route is exactly one of:

```text
BOUNDED_CONTINUOUS_MULTIDIRECTION_PASS_CAUSAL_RECEDING_HORIZON_CONTROLLER_DESIGN_REQUIRED
BOUNDED_CONTINUOUS_MULTIDIRECTION_AUTHORITY_INSUFFICIENT_ONLINE_FEEDBACK_MODEL_REDESIGN_REQUIRED
```

An R8R22 execution, safety, raw, source, reporting, or independent-agreement
failure vetoes R8R23. The applicable integrity repair must be frozen first.

R8R23 asks whether a fixed causal local model, replanned at each of the four
existing decision points and optionally corrected by already observed
one-step innovation, is accurate and conservative enough to justify a fresh
real-TSC controller sentinel. It does not claim that an offline predicted
repair is a real closed-loop repair, and it is not Gate A.

## 2. Immutable development evidence and separation

Authenticate without modifying or rerunning:

1. final R8R7 authentic baseline/source-prefix evidence;
2. final R8R15 and valid R8R20 complete four-slot `U/V` Boolean-tree raw;
3. final R8R22 raw, primary/independent audits, manifest, state, and report;
4. every source fingerprint transitively authenticated by R8R22.

The interrupted R8R20 `_v1` workspaces remain forbidden. All 16 existing
contexts are development evidence for R8R23; none is described as a fresh
controller holdout. Model assessment uses the immutable eight physical
pairs as eight leave-one-whole-pair-out outer folds, always excluding both
hidden-history members of the held pair from fit, calibration, support, and
tie breaking. Any later real controller stage requires a separately frozen
fresh finite context envelope.

R8R23 may use these trajectories for deterministic controller-model
development only. They remain forbidden from expert, BC, DAgger, residual-RL,
or other policy-learning datasets.

## 3. Causal controller boundary

The delegated authentic source prefix remains exact through task step 9.
The only controller decisions remain task steps `[10,14,18,22]`. At a live
decision R8R23 may use only:

1. current and past visible R/Z/Ip;
2. current and past 14-coil readback;
3. the user target and causal task clock;
4. its own previously requested and applied cumulative coordinates; and
5. innovation from a prediction whose endpoint has already been observed.

It may not use pair/history labels, source/candidate outcomes, future state
or action, wire or vessel current, simulator internals, another rollout,
formal-pass labels, or an evaluator oracle.

Every issue uses a fresh exact Card15 target constructed from the current
causal coil readback. Between decisions and through the formal endpoint the
stored exact target is refreshed exactly as in R8R22. A rejected action is
not applied and no later plant step occurs.

## 4. Closed action and sequence family

Use the unchanged coordinates:

```text
U = + canonical c2
V = - canonical c1
```

The cumulative decision-level alphabet is frozen to baseline zero plus the
ten R8R22 levels:

```text
q0 = (0,0)
q(w,a) = (a*w, a*(1-w))
w in [0.00,0.25,0.50,0.75,1.00]
a in [1.25,1.50]
```

At each decision, enumerate only levels whose exact live construction from
the current applied target passes every unchanged R8R22 gate:

```text
incremental normalized action <= 0.25
total normalized action       <= 1.00
maximum current utilization   <= 0.55
desired/applied cosine        >= 0.98
relative off-basis residual   <= 0.10
exact Card15 issue and refresh
no saturation, clipping, forbidden input, or non-finite value
```

The maximum unfiltered planning tree is `11^4 = 14,641` sequences. No new
weight, amplitude, sign, direction, decision time, interpolation, continuous
optimizer, or post-result grid refinement is allowed. Before intervention,
zero is the fail-closed fallback. After intervention, the fallback holds the
last exact stored target if that continuation passes the live gates;
otherwise the controller stops before the next plant advance.

## 5. Fixed causal feature and transition targets

Fit a separate model for each decision interval. Immediately before a
decision, construct the feature below using only already visible samples:

```text
last four visible samples, oldest first:
  (R-target_R)/0.030
  (Z-target_Z)/0.030
  (Ip-target_Ip)/10000

current 14-coil readback / frozen per-coil absolute limits
current minus previous-decision 14-coil readback / the same limits
previous applied cumulative (U,V) coordinate / 1.50
```

At the first decision, the delegated-prefix endpoint is also the
previous-decision coil readback and the previous cumulative coordinate is
zero. No fitted feature selection, PCA, whitening, learned normalization, or
history/pair identifier is permitted.

For a candidate cumulative level `q=(qU,qV)`, append the fixed action basis:

```text
qU, qV, qU^2, qU*qV, qV^2,
qU-previous_qU, qV-previous_qV,
and every causal feature component multiplied separately by qU and qV
```

Predict normalized visible R/Z/Ip and backward-difference R/Z velocity at
every plant sample through the next decision, or through the unchanged
formal endpoint after task step 22. Velocity uses visible samples only.

## 6. Frozen cold model, tube, and online innovation

For each outer fold and interval, fit one multi-output ridge regression with
intercept and fixed penalty `1e-4`. Physical normalizations above are the
only scaling. No hyperparameter search or outcome-dependent model choice is
allowed.

Construct the uncertainty tube from nested whole-pair residuals inside the
seven outer-training pairs: refit seven times, each time leaving one complete
training pair out, then take `1.25` times the componentwise maximum absolute
residual over all nested held rows and forecast samples. The outer held pair
never contributes to its model or tube.

The cold predictor uses zero innovation. After a real or teacher-forced
transition endpoint is observed, form its normalized five-component
prediction residual `r_k` and update:

```text
b_0 = 0
b_k = clip(0.5*b_(k-1) + 0.5*r_k, -B, +B)
```

where `B` is the applicable training-only tube half-width before the `1.25`
reserve. At later forecasts the current `b_k` is added with interval decay
`0.5^h`, where `h=0` for the next interval. No future residual, held-row
refit, recursive least squares, gradient update, or cross-rollout state is
allowed. Controller state is reset exactly at every authentic restart.

Adaptation is retained only if all prospective usefulness gates hold over
outer-fold teacher-forced predictions:

```text
adapted aggregate squared error / cold error <= 0.95
outer pairs strictly improved                 >= 6/8
every outer-pair error ratio                  <= 1.05
innovation clipping rows                           0
```

If these usefulness gates fail but the cold model passes every model/tube
gate below, the frozen controller uses the cold model with causal replanning
and records `innovation_disabled_no_measurable_gain`. It may not preserve a
harmful adapter merely to claim adaptation.

## 7. Zero-TSC model and support gates

The immutable measured library contains baseline plus 16 R8R20 schedules
plus ten R8R22 schedules: 27 trajectories per context. Evaluate every
available decision-origin/forecast row in the eight whole-pair outer folds.
Primary and structurally independent implementations must agree within
absolute tolerance `1e-12`.

Every outer held row must be finite and supported. Support uses Euclidean
distance in the fixed causal feature. Its training-only threshold is `1.5`
times the maximum nearest-neighbor distance obtained by leaving each of the
seven outer-training pairs out in turn. A zero threshold requires exact zero
held distance.

The selected cold/adapted predictor passes only if:

```text
outer held R and Z point error             <= 0.015 m each
outer held R/Z velocity point error        <= 0.05 m/s each
outer held Ip point error                  <= 3000 A
reserved-tube containment                         100%
reserved R and Z tube half-width           <= 0.025 m each
reserved R/Z velocity tube half-width      <= 0.08 m/s each
reserved Ip tube half-width                <= 5000 A
held causal-feature support                       100%
finite exclusions / forbidden inputs                 0
```

These are transition-model gates, not formal-controller outcomes. A failed
gate stops before Ray, `gotsc`, controller, plant step, raw, or snapshot.

## 8. Frozen receding-horizon optimization and predicted-feasibility gate

At each recorded outer-held causal origin, enumerate the closed remaining
sequence tree, propagate the selected model and tube, and rank sequences by:

```text
1. robust satisfaction of the immutable formal arrival/hold contract;
2. smaller worst frozen formal-margin violation;
3. smaller integrated normalized R/Z/Ip error;
4. smaller cumulative normalized action movement;
5. smaller maximum predicted current utilization;
6. lexicographic sequence of alphabet indices.
```

The immutable formal contract remains:

```text
slew 1.0/1.1: arrive <= 250 ms; hold/evaluate through 350 ms
slew 0.9:     arrive <= 270 ms; hold/evaluate through 370 ms
R/Z tolerance 30 mm; speed threshold 0.1 m/s
Ip threshold 10000 A; arrival streak 3
```

Replan after each already observed decision interval; apply only the first
selected level. The offline preflight may report only model-predicted
feasibility. It must not stitch measured states, substitute a measured
counterfactual successor, or report a predicted sequence as real control.

The R8R23 preflight passes only if all are true:

```text
R8R22 final integrity and allowed route authenticated             yes
source/model/tube/support/action/causality gates                   pass
all 16 development starts produce a safe complete plan           16/16
predicted repairs among the ten R8R7 failed baselines             >= 1/10
predicted regressions among the six R8R7 passes                      0/6
predicted baseline-plus-policy oracle                             >= 7/16
primary/independent features, fits, tubes, plans, and route          exact
new TSC / plant steps / raw                                             0
```

PASS routes are selected prospectively as:

```text
adaptation useful:
CAUSAL_ONLINE_INNOVATION_RH_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED

cold model passes, adaptation not useful:
CAUSAL_FEEDBACK_RH_PREFLIGHT_PASS_STATIC_MODEL_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED
```

Model, tube, support, or predicted-feasibility failure route:

```text
CAUSAL_ONLINE_FEEDBACK_MODEL_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED
```

Authentication, causality, or independent-disagreement route:

```text
CAUSAL_ONLINE_FEEDBACK_PREFLIGHT_EVIDENCE_FAIL_STOP
```

No threshold, feature, penalty, tube rule, action alphabet, fallback,
objective, or route may change after R8R22 formal outcomes are opened.

## 9. Downstream Gate A boundary

An R8R23 PASS authorizes only a separately frozen fresh-identity real-TSC
safety sentinel for the selected causal receding-horizon controller. That
future design must predeclare fresh restart/history/target separation,
controller runtime and solver fallback, deterministic formal success, then
the finite continuous delay/gain/slew, mismatch, measurement-noise,
disturbance-recovery, and independent long-hold qualification matrix required
by Gate A. It may not reuse any R8-family row as fresh controller evidence.

R8R23 itself is not a controller execution, MPC result, robustness result,
or Gate A. Expert data, BC, DAgger, and residual RL remain blocked.
