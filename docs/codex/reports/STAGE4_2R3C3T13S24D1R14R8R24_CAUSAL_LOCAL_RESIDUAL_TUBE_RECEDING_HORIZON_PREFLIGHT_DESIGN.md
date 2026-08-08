# Stage4.2R3c3T13S24D1R14R8R24 causal local-residual-tube receding-horizon preflight design

Frozen prospectively on 2026-08-09 Asia/Shanghai after final R8R23 evidence,
route, compact audit, and forensic report were sealed at checkpoint
`8c8f71c`, and before any R8R24 implementation, local-residual query, fitted
tube, candidate plan, optimization result, or route was produced.

## 1. Activation and scientific question

R8R24 activates only for the exact final R8R23 route:

```text
CAUSAL_ONLINE_FEEDBACK_MODEL_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED
```

Required R8R23 fingerprints are:

```text
primary detailed  a40a9b895bcfb69069fa5fe6dd7441b7159189d56f7aa50cc893db34a3bcd1a5
primary summary   4d900b3c5b477ff89dc1d62466b3d8e9ce132480f9c85ae26db91d55b1da285a
independent       af1b419bec6854ec901755c32f1c91131da1a09a0a0d4a1e1cc033ca6f0dd99a
final report      3d1c88aca308baf67b30010b25df03398dd20e1d4458dfa2413a7c65ceb174cc
model evidence    9bc1e2a0e15597812defbf7724d673ae791ae50d7f70eb2aeda005d61f8ddc5f
stage manifest    2f3aef0b48cb5d35846da3e769110fb8e514374ea7cf57c18b364d9879c5e403
stage state       bd55964f69af3a17ce46f503ec629821c05dd54e9cbaf7ee71a9be644a227910
```

R8R23 established a specific separation: all held point-error and support
gates passed, but the nested global maximum-residual tube was incompletely
containing and exceeded both velocity caps. Its fixed innovation update
worsened error and was disabled. R8R24 asks whether the unchanged cold point
predictor can be paired with a prospectively fixed, causal, local residual
envelope that is both fully containing and narrow enough to justify opening
the already frozen safe action-tree preflight.

R8R24 is development-stage zero-new-TSC evidence. It cannot relabel any
R8-family row as a fresh holdout, cannot establish a real controller result,
and cannot qualify Gate A.

## 2. Immutable evidence and prohibition boundary

Authenticate without modification or rerun:

1. final R8R23 primary, independent, final, manifest, state, model, and
   compact evidence;
2. the exact R8R22 and transitive source fingerprints authenticated by
   R8R23; and
3. the exact 432-trajectory bank and its R8R23 feature/target digests.

The interrupted R8R20 v1 workspaces remain forbidden. The bank contains all
16 existing contexts and is now consumed model-development evidence. No row
may be described as a fresh controller holdout. Every R8-family trajectory is
forbidden from expert, BC, DAgger, residual-RL, or other policy-learning data.

R8R24 executes zero Ray, `gotsc`, TSC, controller, plant advance, snapshot,
or raw creation. It does not modify any source stage.

## 3. Point predictor is unchanged

Recompute rather than load predictions, and require exact reproduction of the
R8R23 cold predictor:

```text
causal base feature dimension                   42
fixed action-expanded feature dimension        133
model family           multi-output ridge with intercept
ridge penalty                                 1e-4
outer split                      eight whole physical pairs
nested split             seven whole pairs inside each outer fit
separate model per decision interval          yes
masked final-horizon outputs                   yes
feature selection / PCA / search                no
```

The 42 causal features, action basis, output order, physical normalizations,
decision steps `[10,14,18,22]`, masked 13/15-sample final interval, and all
forbidden predictor fields remain byte-for-byte the R8R23 contract. Pair,
history, source, schedule, future state/action, wire/vessel current, simulator
internals, and formal outcomes may not enter a fit, distance, or live query.

Primary reproduction must match the final R8R23 feature digest, target digest,
outer fitted values, point metrics, and selected cold-predictor outcome.
Independent code must rebuild them without importing the R8R23 or R8R24
primary implementation.

The failed R8R23 innovation update is removed, not retuned. R8R24 has no
online bias state and no alternative innovation hyperparameter.

## 4. Fixed local residual envelope

For each outer held pair and decision interval, construct calibration records
only from the seven outer-training pairs:

1. leave one of those seven whole pairs out;
2. fit the unchanged cold point model on the other six pairs;
3. predict every trajectory/origin in the inner-held pair; and
4. retain the absolute out-of-fold residual for each available lead sample
   and each of the five outputs.

No in-sample residual may calibrate a tube. For a query at a fixed interval
and lead-sample index, use only calibration records at that same interval and
lead index. Distance is ordinary Euclidean distance over the exact 133D
R8R23 action-expanded causal feature. There is no learned scaling, fitted
metric, feature weight, outcome weight, or pair/history term.

The neighbor rule is frozen to:

```text
k                                                32
ties at the kth distance                         include all
residual aggregation                             componentwise maximum
reserve multiplier                               1.25
```

Including all kth-distance ties prevents any source-label tie break. Define
the reserved tube half-width componentwise as:

```text
max(
  1.25 * maximum absolute inner-OOF residual among local neighbors,
  fixed point-error floor
)
```

The fixed physical floors are the unchanged R8R23 held point-error gates:

```text
R       0.015 m
Z       0.015 m
Ip   3000 A
vR      0.050 m/s
vZ      0.050 m/s
```

These floors are engineering guard bands, not fitted residual quantiles.
They do not change which R8R23 point predictions passed. A tube may never be
clipped to make it pass a cap. If the local reserved value exceeds a cap, the
query and the stage fail rather than truncate the tube.

The unchanged maximum tube caps are:

```text
R       0.025 m
Z       0.025 m
Ip   5000 A
vR      0.080 m/s
vZ      0.080 m/s
```

## 5. Outer model and support gates

Across all eight outer held pairs, every one of the following is required:

```text
maximum R point error                         <=0.015 m
maximum Z point error                         <=0.015 m
maximum Ip point error                      <=3000 A
maximum vR point error                        <=0.050 m/s
maximum vZ point error                        <=0.050 m/s
reserved component containment                  100%
all reserved tube half-widths within caps        yes
R8R23 support rate                               100%
finite exclusions                                  0
forbidden inputs                                   0
```

Retain the R8R23 support rule exactly: for each outer fold and interval, the
held query distance to the closest outer-training origin must not exceed
`1.5` times the maximum nearest-neighbor distance obtained inside training-
only nested whole-pair folds. Local-residual neighbors do not waive support.

Primary and independent implementations must agree on every feature digest,
point prediction, neighbor-set size after ties, tube component, containment,
support result, gate, and route within absolute tolerance `1e-12`.

## 6. Conditional action-tree planning

Planning remains closed unless every source, point, support, local-tube,
finite, forbidden-input, and independent-agreement gate passes. If any one
fails, write explicit zero/sentinel planning fields and stop with zero plant
advance.

If opened, use the exact R8R23 closed action tree without enlargement:

```text
zero plus ten R8R22 cumulative U/V levels       11
decisions                                        4
maximum unfiltered sequences                14,641
```

At each predicted decision, rebuild the causal feature from the recursively
predicted visible history and deterministic exact applied coil target. Apply
the local tube for that predicted causal/action query and require support.
Every action must pass the unchanged exact Card15 issue/refresh,
incremental-action `<=0.25`, total-action `<=1.0`, current-utilization
`<=0.55`, cosine `>=0.98`, off-basis `<=0.10`, finite, saturation,
forbidden-input, and safe-stop gates.

The formal contract remains immutable:

```text
normal slew: arrive by 250 ms, hold through 350 ms
weak slew:   arrive by 270 ms, hold through 370 ms
R/Z tolerance 30 mm; speed 0.1 m/s; frozen Ip and arrival streak
```

For each of the 16 development contexts, enumerate deterministically and
select the lexicographically first minimum-cost sequence satisfying the
entire reserved tube. Zero remains the safe fallback before intervention;
after intervention, hold the last exact target only if its complete remaining
reserved branch is safe, otherwise fail closed.

## 7. Planning gate and routes

An R8R24 scientific PASS requires all model gates plus:

```text
safe complete predicted plans                       16/16
predicted repairs among ten failed baselines         >=1
predicted regressions among six baseline passes        0
baseline-plus-policy predicted oracle              >=7/16
```

These are development predictions, not real control. Routes are frozen to:

```text
source, causal, integrity, or independent failure:
  R8R24_INTEGRITY_FAIL_STOP

point, support, local-tube, containment, or cap failure:
  CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED

model pass but planning/repair/oracle failure:
  CAUSAL_LOCAL_RESIDUAL_TUBE_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED

all model and planning gates pass:
  CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED
```

No gate or hyperparameter may be changed after an R8R24 output is opened.

## 8. Authorization boundary

Even a complete R8R24 PASS authorizes only design and preregistration of a
new-identity fresh finite real-TSC controller sentinel. That sentinel must
have an explicit safety-first partition, fresh contexts or parameters,
independent raw/formal auditing, hard fallback, and zero learning-data reuse.
It must not reuse an R8R24 development prediction as a measured outcome.

R8R24 is not real MPC, formal-control qualification, or Gate A. Gate A,
expert data, BC, DAgger, and residual RL remain blocked.
