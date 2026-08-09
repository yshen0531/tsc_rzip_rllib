# Stage4.2R3c3T13S24D1R14R8R46 q0-calibration causal-innovation controller preflight design

Status: prospectively frozen on 2026-08-09 after final R8R44 and its compact
planning forensics were opened, but before any R8R46 config, source change,
bank rebuild, feature, residual, innovation, fit, tube, support, prediction,
plan, selected action, metric, route, package, deployment, Ray, `gotsc`, TSC,
controller, plant step, raw, or snapshot.

## 1. Scientific question and exact source gate

R8R44 proved that the fixed R8R43 cold ensemble is accurate and safe enough
for its frozen finite model gate, but carrying its worst whole-pair/schedule
tube through every hypothetical suffix leaves zero robust-formal deployable
plans. R8R46 asks a different prospective question:

```text
Can one exact target-hold interval provide a same-rollout causal innovation
state whose independently held post-calibration prediction/tube is accurate
and conservative enough to produce at least one safe robust-formal repair?
```

R8R46 is activated only by exact authentication of:

```text
R8R43 final route
  FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED

R8R44 final route
  FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_AUTHORITY_INSUFFICIENT_NO_TSC
```

The eight final R8R44 SHA-256 values are frozen:

```text
primary_summary  539691abbd779d6c56711cbbd489ed7f47bc9297472d1bbd9b358ef881bb409b
primary_detailed dabff158160e77d82207c95d0d38093c91aca3a97b06287216b3d83164877aa2
model            7a7b35b6189765653a1c4d16b4a80fc6096ea35fe135542cd5049f65b6ad16a5
independent      d757515ba0e6e3d1de895f2cc5c08f9423d48d56f4a9b8c916239d5cdf7a1a01
compact_audit    b0496ed69c8ba3a45ff611b086df955fc53fe8ed34b9def30706cae3361ea764
final_report     7bd1b8e31c81e82e4559f78acf0b2b37bd6705e178e64d4a53d03575aaf2b713
stage_state      7bbd2a69faaa9de560979120ff6651d65d85141cb7a79e47c8c869ffc346a794
stage_manifest   2a576650f3e540959ffc5f13ef5e10a035a49447d25959291ccb137476e0059a
```

Conditional R8R45 requires an exact R8R44 PASS and is blocked. It may not be
repurposed. R8R46 is a new zero-new-TSC identity and cannot relabel R8R44,
R8R37, or any earlier result.

## 2. Immutable evidence and cold model

Rebuild exactly the authenticated R8R43/R8R44 development bank:

```text
trajectories                                             560
physical pairs / history contexts                    8 / 16
schedule identities                                      35
decision intervals / interval records               6 / 3360
bank digest
  a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest
  80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest
  0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

The cold predictor is unchanged:

```text
global expert                         expanded-238 ridge 1e-4
local expert                  centered stable 62D k64 affine ridge 1
cold prediction                         0.25 global + 0.75 local
```

Refit both experts separately inside every held whole-pair and held whole-
schedule fold. Preserve feature order, normalizations, local-neighbor order,
ties, solvers, intercept handling, candidate coordinates, and binary64
weights. No weight, gain, ridge, neighbor, feature, outcome, or route search
is permitted.

## 3. New causal calibration boundary

At task step 10 the controller must select candidate index zero and perform
only exact current-target hold. No transport action is allowed. The plant is
observed through task step 12. This completed transition is interval zero and
is the sole calibration transition available before the first transport
decision.

Interval zero is not deleted or declared accurate by assumption. Its cold
prediction, original R8R43 full tube, support, finiteness, exact-hold Card15
refresh, current, and visible pre-action safety gates remain required. The
reason it is outside the adapted-performance validation is causal: its
endpoint becomes a measurement before any R8R46 transport action is chosen.

This does not repair or weaken R8R37. R8R37 evaluated a different identity
whose interval-zero prediction was part of its full cold/adapted model gate.
R8R46 instead predeclares interval zero as an executed measurement-only
calibration hold and independently validates only future predictions that
actually consume that completed innovation.

## 4. Exact bounded same-rollout innovation

All visible outputs use the unchanged normalized order:

```text
[R/0.03, Z/0.03, Ip/10000, vR, vZ]
```

Velocity is reconstructed only by backward differencing completed visible
samples. Let `r_k` be the normalized five-component residual at the final
completed sample of interval `k`, computed from that rollout's previously
issued prediction and the now-visible measurement. Controller state is reset
to zero at every authentic restart:

```text
b_0 = 0
b_(k+1) = clip(0.5*b_k + 0.5*r_k, -B_k, +B_k)
```

`B_k` is the applicable training-only, pre-1.25-reserve componentwise tube
for interval `k`. It is recomputed inside each outer fold; a held pair or held
schedule never contributes. The update is first legal after interval zero is
complete at task step 12.

For the next interval, add the full current `b` to every forecast sample.
For a hypothetical interval `h` decisions beyond the next one, add
`0.5^h * b`, with `h=0` for the immediate next interval. Future unobserved
innovations are always zero in planning. At each real decision, discard the
old suffix, update from the newly completed measured interval, and replan.

Innovation clipping, update count, causal source samples, prediction digest,
measurement digest, and reset digest must be recorded. Pair/history label,
source outcome, future measurement/action, evaluator result, another
rollout, hidden simulator state, and wire/vessel current are forbidden.

## 5. Post-calibration outer validation

Teacher-force only already completed innovations within each immutable
trajectory. Evaluate intervals 1 through 5 in all eight leave-one-whole-pair
folds and all 35 leave-one-whole-schedule folds. The held fold contributes to
neither cold model, neighbor set, innovation cap, residual tube, support
threshold, tie break, nor usefulness decision.

Build the post-calibration residual tube with the unchanged nested refits,
`1.25` reserve multiplier, componentwise absolute maximum, physical floors,
and no clipping. Combine whole-pair and whole-schedule tubes by componentwise
maximum. The selected adapted predictor must pass:

```text
finite / forbidden inputs                                      100% / 0
whole-pair and whole-schedule support                              100%
whole-pair and whole-schedule containment                           100%
maximum R/Z point error                                  <=0.015 m each
maximum Ip point error                                      <=3000 A
maximum vR/vZ point error                              <=0.05 m/s each
maximum R/Z tube half-width                             <=0.025 m each
maximum Ip tube half-width                                <=5000 A
maximum vR/vZ tube half-width                         <=0.08 m/s each
innovation clipping rows                                           0
```

Usefulness is separately required over post-calibration held predictions:

```text
adapted/cold aggregate normalized squared error ratio           <=0.95
whole-pair folds strictly improved                                >=6/8
maximum whole-pair adapted/cold ratio                             <=1.05
whole-schedule aggregate adapted/cold ratio                       <=0.95
```

There is no cold fallback PASS route. If bounded innovation does not pass
these gates, the architecture is rejected before controller execution.

## 6. Frozen controller and two-certificate safety rule

After calibration, decisions are exactly:

```text
[12,14,16,18,22]
```

Use the inherited 17 candidates, canonical order, beam width 512, cost,
ties, support hulls, dynamic exact Card15 search radius 16, and first-action-
only receding execution. The measured task-step-12 state and currents start
the first search; a predicted state never substitutes for a measurement at a
later real decision.

Every candidate first action must satisfy both certificates:

1. hard issue certificate: exact Card15 issue/refresh, incremental action
   `<=0.25`, total action `<=1.0`, current utilization `<=0.55`, desired/
   applied cosine `>=0.98`, off-basis residual `<=0.10`, finite values, no
   clipping/saturation, observed state and action-transition support, and
   stop before any failed plant advance;
2. immediate uncertainty certificate: the next executed interval is checked
   with the componentwise maximum of the unshrunk R8R43 cold tube and the
   independently validated post-calibration tube. Innovation may never
   reduce this immediate safety reserve.

The full remaining suffix is ranked and accepted for formal performance with
the independently validated post-calibration adapted tube. Use the immutable
formal evaluator:

```text
slew 1.0/1.1   arrive by 250 ms, hold/evaluate through 350 ms
slew 0.9       arrive by 270 ms, hold/evaluate through 370 ms
R/Z            0.03 m
speed          0.1 m/s
Ip             10000 A
arrival streak 3
```

Execute only the first action of a robust-formal plan. A best failing plan is
diagnostic and forbidden. Missing support, no robust plan, model exception,
non-finite value, timeout, empty safe set, innovation violation, or Card15
failure selects exact current-target hold when that hold is safe; otherwise
stop before the next plant advance. Preserve all six inherited fault-
injection exact holds.

## 7. Zero-TSC preflight gate

R8R46 passes only if primary and a structurally independent implementation
both establish:

```text
exact R8R43 and final R8R44 authentication                       PASS
exact 560/35/3360 bank and three digests                          PASS
interval-zero q0 calibration cold/support/tube/safety            16/16
post-calibration model/tube/support/usefulness gates              PASS
complete safe searches from measured task step 12                16/16
robust-formal repairs among ten failed baselines                  >=1/10
robust-formal regressions among six baseline passes                  0/6
fallback-plus-plan predicted oracle                               >=7/16
nonzero safe first transport action selections                       >=1
fault-injection exact holds                                          6/6
primary/independent discrete selection and route                    exact
maximum scaled model/prediction/tube/metric/planning difference     1e-9
Ray / gotsc / TSC / plant step / raw / snapshot                         0
```

The baseline classification is evaluator-only and may count gates after
planning; it may not enter any feature, innovation, action, tie break, or
fallback decision.

## 8. Frozen routes

```text
R8R43/R8R44 source authentication or causal-evidence failure
  Q0_CALIBRATION_CAUSAL_INNOVATION_PREFLIGHT_BLOCKED_BY_SOURCE

post-calibration innovation/model/tube/support/usefulness failure
  Q0_CALIBRATION_CAUSAL_INNOVATION_MODEL_INSUFFICIENT_NO_TSC

model passes but search/safety/fault binding fails
  Q0_CALIBRATION_CAUSAL_INNOVATION_SAFETY_FAIL_NO_TSC

all integrity/safety gates pass but frozen authority gate fails
  Q0_CALIBRATION_CAUSAL_INNOVATION_AUTHORITY_INSUFFICIENT_NO_TSC

all model, safety, authority, and dual gates pass
  Q0_CALIBRATION_CAUSAL_INNOVATION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

Any failure ends R8R46 with zero new TSC and does not prove global plant
unreachability. A PASS authorizes only a separately prospectively frozen
fresh real-controller safety sentinel; it does not authorize that execution.

## 9. Packaging, evidence, and Gate A boundary

Before execution require project-virtual-environment compilation, focused
and full Windows-shim tests, exact manifest/hashes, a fresh empty direct-copy
tree, direct uncompressed SSH transfer, server preflight, existing server
virtual environment, staging/installed hashes, every declared `bash -n`,
compilation, focused/full tests, and dual zero-TSC audit. Large model/detailed
evidence remains on the server; download only compact audit evidence.

Every R8-family trajectory remains controller-development evidence and is
forbidden from expert data, BC, DAgger, residual RL, or any other learning
dataset. R8R46 cannot establish real control, continuous robustness,
independent long hold, residual authority, or Gate A. Gate A and all learning
remain blocked.
