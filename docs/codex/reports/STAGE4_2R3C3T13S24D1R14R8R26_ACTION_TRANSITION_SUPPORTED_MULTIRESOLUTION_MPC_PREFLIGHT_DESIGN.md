# Stage4.2R3c3T13S24D1R14R8R26 action-transition-supported multiresolution MPC preflight design

Frozen prospectively on 2026-08-09 Asia/Shanghai after final R8R25 evidence,
compact audit, forensic report, route, and checkpoint `ad6df5c` were sealed,
and before any R8R26 schedule-held-out error, tube, hull, search, plan,
formal metric, or route was computed.

## 1. Activation and scientific question

R8R26 activates only for the exact final R8R25 route:

```text
TRAINING_CARDINALITY_MATCHED_TUBE_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED
```

Required R8R25 fingerprints are:

```text
primary detailed  8ab38c412b94984de5eac7f9ef5009eb5ac93886cae2324258cbe650bc33d1d5
primary summary   acc666b16489cfcd815b5b5375e8c3967d32704ae58fa1cb100ac0b3ceac8eea
independent       2729ae940c7727becaded17a8a8f0826803f2120cf09d909d54a57bcff7e4b25
final report      d651bd7aaa1a6de2794263215e4c5928a23fcb7334bd59c85b6219182498af50
model evidence    b1487f5efc17d3fe1cd83d60faedd758c9e2ba2c83c92bd160f0a1f4d259aefc
stage manifest    d9ac7247a8cccc2581c1378784119cd8bc99608c078d8c32616b012d1c8f3406
stage state       e8e61e6628f0c9c2de3a4b43f5429d5c380d39876eb28081dc8af79fabfe83ce
compact audit     ecfbbe93f46dbb27448fe03499b68927e258be410277e19db88429fe19478bb8
```

R8R25 established a finite whole-pair point-model and uncertainty PASS but
found no robust-formal sequence in the complete `11^4` action tree. R8R26
asks whether a prospectively finite, interpolation-supported refinement of
the same two-dimensional cumulative U/V coordinate contains at least one
robust-formal repair while remaining inside the exact action boundary.

This is a development preflight, not a controller or plant result. It makes
no global-optimality, continuous-domain completeness, or plant-reachability
claim.

## 2. Immutable evidence and zero-TSC boundary

Authenticate without modification or rerun:

1. all seven official R8R25 files and its compact audit;
2. R8R25's exact R8R24/R8R23 and transitive source authentication;
3. the exact 432-trajectory, 27-schedule-per-context development bank;
4. R8R25's all-eight planning model, outer-jackknife planning tube, state
   support thresholds, action construction, and formal evaluator; and
5. the frozen R8R25 result that the original eleven-level tree has zero
   robust-formal sequences in all 16 contexts.

R8R26 executes zero Ray, `gotsc`, TSC, controller, plant advance, snapshot,
or raw creation. It does not modify any source stage. Every R8-family
trajectory remains forbidden from expert, BC, DAgger, residual-RL, or other
policy-learning data.

## 3. Point model and pair-generalization tube remain unchanged

The final planning point predictor remains exactly R8R25's all-eight-pair
133-feature multi-output ridge model with intercept and penalty `1e-4`.
Primary must reproduce its model digest, predictions, point metrics, pair
tube, support, and original eleven-level plan within absolute tolerance
`1e-12`. No innovation, online bias correction, feature selection, PCA,
hyperparameter search, future field, or outcome label may enter the model.

The R8R25 all-eight planning outer tube remains an immutable lower bound on
uncertainty. It retains componentwise maximum, reserve `1.25`, physical
floors `[0.015 m, 0.015 m, 3000 A, 0.05 m/s, 0.05 m/s]`, no clipping, and
the unchanged caps.

## 4. Frozen action-schedule jackknife reserve

The bank contains exactly 27 complete schedule identities in every one of
the 16 contexts. Define 27 leave-one-whole-schedule-out fits. For held
schedule identity `s`:

1. remove every trajectory with schedule identity `s` across all eight
   physical pairs and both histories;
2. fit the unchanged ridge model to the other 26 complete schedules;
3. predict every held-`s` trajectory using the exact causal feature and
   masked horizon; and
4. retain absolute residuals by fixed decision interval, lead index, and
   output component.

No row-level random split is allowed. At each interval and lead, define the
schedule-jackknife tube as:

```text
max(
  1.25 * componentwise maximum absolute schedule-held-out residual,
  unchanged physical point-error floor
)
```

Require all 27 held schedules, all 432 trajectories, all 11,232 points, and
all 56,160 output components with zero exclusions. Schedule-held-out point
errors must pass the unchanged R8R25 point caps. Its reserved tube must
contain 100% of held components and pass the unchanged R8R25 tube caps.

The planning tube is the componentwise maximum of the immutable R8R25
all-eight outer tube and this schedule-jackknife tube. It may never be
clipped, quantiled, outcome-selected, or reduced after inspection.

## 5. Observed action-transition convex-hull support

The refined action is still the same cumulative two-coordinate vector
`q=(q_u,q_v)`. Define the candidate integer lattice prospectively as:

```text
q_u = u / 16
q_v = v / 16
u,v are integers
u >= 0, v >= 0, u + v <= 24
```

This gives 325 finite lattice levels including zero; it is not treated as a
continuous or globally complete domain.

For each of the four decision intervals, form the unique observed normalized
transition rows
`[previous_q_u, previous_q_v, q_u, q_v] / 1.5` from the immutable bank.
Compute their affine hull by centered SVD with singular-value tolerance
`1e-12`, project to the resulting rank, and compute the deterministic SciPy
convex hull in projected coordinates. A candidate transition is supported
only when:

```text
distance from the observed affine hull <= 1e-12
every projected convex-hull inequality <= 1e-10
```

No joggle option, learned distance, outcome field, residual field, or
context label may alter support. Every live planning node must also pass the
unchanged R8R25 causal visible-state support rule.

This support test makes the refined search an interpolation over observed
action transitions. It does not prove validity beyond the finite bank;
schedule-jackknife error supplies the additional frozen reserve.

## 6. Exact hard action boundary

Every candidate issue is constructed with the unchanged R8R25/R8R22 exact
Card15 actuator boundary at the current predicted current. Retain unchanged:

```text
maximum incremental normalized action L-infinity    0.25
maximum total normalized action magnitude            1.0
maximum current utilization                           0.55
minimum desired/applied-current cosine                0.98
maximum relative off-basis residual                   0.10
exact Card15 issue and refresh                         yes
finite / saturation / current-limit rejection         yes
safe stop before a rejected advance                    yes
```

An unsupported, nonrepresentable, saturated, clipped, over-current, or
otherwise rejected node is not expanded. No constraint may be softened by
the search.

## 7. Frozen multiresolution finite search

The search is deterministic and finite. It does not claim a global optimum.

### 7.1 Coarse candidate set and beam

The coarse level set is the sorted union of:

1. all lattice pairs `(u,v)` with both `u` and `v` divisible by four and
   `u+v<=24`; and
2. the exact eleven R8R25 levels represented in sixteenth-units.

After deduplication it must contain exactly 33 levels, ordered
lexicographically by `(u,v)`. Expand four decisions at task steps
`[10,14,18,22]` with beam width 256.

At nonterminal intervals rank supported hard-safe nodes by:

```text
integrated squared normalized R/Z/Ip error over the predicted prefix
maximum predicted current utilization
cumulative L1 movement in q
lexicographic integer q-token sequence
```

Keep the first 256 nodes, or all nodes if fewer exist. At the terminal
interval rank by the exact tuple:

```text
not robust_formal_pass
worst formal margin violation
integrated normalized R/Z/Ip error
cumulative L1 movement in q
maximum predicted current utilization
lexicographic integer q-token sequence
```

Retain the first 32 terminal seeds.

### 7.2 Fine deterministic coordinate refinement

Refine every retained seed independently. For step sizes `d=2` then `d=1`
sixteenth-units, examine the six triangular-lattice directions:

```text
(+d,0), (-d,0), (0,+d), (0,-d), (+d,-d), (-d,+d)
```

At each sweep evaluate every single-decision neighbor that remains in the
325-level lattice and passes transition, state-support, and hard-action
checks. Move to the strict minimum terminal ranking tuple if it improves the
current sequence. Stop at no improvement or after 16 sweeps for that step
size. Ties use decision index, direction order as listed above, and integer
token sequence. Select the strict minimum across all coarse seeds and their
refined results.

Primary and structurally independent implementations must agree exactly on
hulls, support decisions, searched/evaluated token digests, chosen tokens,
predictions, tubes, formal metrics, outcomes, and route; floating values must
agree within absolute tolerance `1e-12`.

## 8. Fail-closed causal baseline fallback

A context uses the refined plan only if its reserved prediction passes the
unchanged robust formal contract. Otherwise it selects the unchanged causal
baseline-controller continuation. The selection uses only the causal model,
fixed tube, and current visible/action history; it may not use pair ID,
history label, known baseline outcome, future state, or source formal label.

For this offline preflight, the immutable authentic baseline result is used
only to score the fallback outcome after the causal plan/fallback choice is
frozen. A best failing plan is never treated as deployable.

## 9. Immutable formal and scientific gates

Formal timing remains:

```text
slew 1.0/1.1: arrive by 250 ms, hold through 350 ms
slew 0.9:     arrive by 270 ms, hold through 370 ms
R/Z 30 mm; speed 0.1 m/s; frozen Ip and arrival streak
```

R8R26 passes only if all source, model, schedule-jackknife, combined-tube,
transition-support, state-support, finite, hard-action, and independent gates
pass, plus:

```text
contexts with a safely completed deterministic search          16/16
causally selected refined robust-formal repairs among failures   >=1
hybrid regressions among six baseline passes                       0
baseline-fallback-plus-refined-plan oracle                      >=7/16
```

Frozen routes are:

```text
source, causality, integrity, or independent failure:
  R8R26_INTEGRITY_FAIL_STOP

schedule-jackknife point/tube/cap or support failure:
  ACTION_TRANSITION_SUPPORTED_TUBE_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED

model pass but search/repair/oracle failure:
  ACTION_TRANSITION_SUPPORTED_MULTIRESOLUTION_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED

all gates pass:
  ACTION_TRANSITION_SUPPORTED_MULTIRESOLUTION_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED
```

## 10. Authorization boundary

Even a complete PASS authorizes only prospective design of a new-identity,
fresh, safety-first real-TSC controller sentinel. That later design must
freeze a limited initial safety partition, authentic restart and causal
state, exact package/raw/snapshot/formal audits, baseline fallback, and
stop-before-advance behavior before any trajectory is run.

R8R26 is not real MPC, practical MPC qualification, or Gate A. Expert data,
BC, DAgger, residual RL, and Gate A remain blocked.
