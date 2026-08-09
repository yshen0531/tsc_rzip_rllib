# Stage4.2R3c3T13S24D1R14R8R51R3 single-transport return-hold formal authority audit design

Status: prospectively frozen on 2026-08-10 after final R51R2 model evidence,
but before computing or viewing any R51R1 candidate formal metric, candidate
formal pass, repaired-context mapping, or candidate oracle result.

Before this freeze, the already public R8R7 aggregate `6/16` baseline formal
pass count was known. For source-structure inspection only, the last R/Z/Ip
values of two R51R1 files in one context were viewed; no target difference,
formal metric, pass boolean, repair mapping, oracle, or cross-candidate result
was computed. This disclosure cannot change the gates below, which reproduce
the earlier R8R9 authority thresholds.

## 1. Frozen question and source gate

R51R2 proves a highly accurate causal model only for the first physical
transport interval, states 13 and 14. It does not model the remaining
state-14-to-horizon evolution. Before designing a selector or optimizer, R51R3
asks the narrower empirical authority question:

```text
Does any one of the 13 actually executed q0 -> single transport -> exact
return -> hold schedules produce a full-horizon formal repair of any failed
R8R7 baseline context?
```

R51R3 is authorized only if final R51R2 primary and independent agree on:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_WHOLE_PAIR_CAUSAL_MODEL_COMPLETE_CONTROLLER_PREFLIGHT_REQUIRED
```

It binds R51R2 primary/independent/compact/final/state/manifest hashes and the
authenticated R51R1 and R8R7 inventories. Any other R51R2 outcome blocks it.
R51R3 runs zero Ray, `gotsc`, TSC, controller, plant step, snapshot, new raw,
model fit, model selection, or optimization.

## 2. Immutable trajectories and formal contract

Strictly parse all source trajectories in place:

```text
R8R7 matching zero-action baselines              16
R51R1 candidates       8 pairs x 2 histories x 13 = 208
total full-horizon formal rows                    224
```

Authenticate every specification, context identity, target, slew, horizon,
restart/source prefix, q0 event, candidate event, issue-plus-one effect, exact
return, forbidden-input trace, and complete finite R/Z/Ip trajectory. No row,
context, candidate, outcome, or failure may be excluded.

Reconstruct the unchanged evaluator from the authenticated source context:

```text
slew 1.0/1.1: arrive no later than step 25; hold through step 35
slew 0.9:     arrive no later than step 27; hold through step 37
R/Z tolerance                                      0.03 m
speed threshold                                  0.1 m/s
Ip threshold                                    10,000 A
arrival streak                                      3 steps
arrival-deadline expansion                              forbidden
metric comparison absolute tolerance                 1e-12
```

For every trajectory report formal pass, minimum signed margin, mean signed
margin, and chosen arrival time. Primary uses the existing compact formal
evaluator. The independent path must recompute the full metric algebra from
raw R/Z/Ip without calling the primary row function. All pass/arrival values
must agree exactly and all finite metric values within `1e-12`.

## 3. Frozen context aggregation

Group only by the public physical key `(pair_id, history_member)`. For each
of 16 contexts report:

```text
matching R8R7 baseline formal result and margins
all 13 actual R51R1 candidate formal results and margins
best candidate by minimum margin, then mean margin, then candidate index
best-candidate minimum-margin gain over baseline
whether any candidate repairs a failed baseline
oracle result over baseline plus all 13 candidates
```

The baseline remains a do-nothing oracle option, so the oracle cannot regress
the known six formal passes. Candidate schedules are evaluated as measured;
no R51R2 prediction, interpolation, extrapolation, composition, counterfactual
suffix, or context exclusion is permitted.

## 4. Prospective gates and routes

Integrity gates:

```text
R51R2 route/hash/evidence authentication                         PASS
R51R1 source/hash/raw/spec/restart/action authentication      208/208
R8R7 baseline source/hash/raw/spec authentication               16/16
strict finite full-horizon trajectories                         224/224
primary/independent formal pass and metric agreement             exact
known R8R7 baseline formal count                                  6/16
failed R8R7 baselines                                                10
source/row exclusions                                                  0
new TSC/raw/snapshot/controller/plant/model/optimization    0/0/0/0/0/0/0
```

Scientific authority gate:

```text
failed baselines repaired by at least one actual candidate        >= 1
baseline-plus-candidate measured oracle formal contexts           >= 7/16
```

Routes are frozen as:

```text
R51R2 route/hash/evidence source gate fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_FORMAL_AUTHORITY_AUDIT_BLOCKED_BY_SOURCE

parse, trajectory, action, formal-equivalence, or integrity failure
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_FORMAL_AUTHORITY_AUDIT_EXECUTION_FAIL_STOP

integrity passes but zero actual repair or oracle below 7/16
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_SINGLE_TRANSPORT_RETURN_HOLD_AUTHORITY_INSUFFICIENT_SEQUENTIAL_MODEL_REQUIRED

at least one actual repair and oracle at least 7/16
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_FORMAL_AUTHORITY_PRESENT_MODEL_SELECTED_CONTROLLER_PREFLIGHT_REQUIRED
```

The authority route is a measured finite-envelope diagnostic. It cannot prove
a causal selector can choose the winning candidate. The insufficient route
rejects only this single-transport/exact-return/hold action family; it does not
prove global plant unreachability.

## 5. Safety, learning, and Gate A boundary

R51R3 is read-only and preserves the immutable formal timing contract. It is
not real controller execution, MPC, closed-loop qualification, continuous-
parameter, noise, disturbance, long-hold, or restart-robustness evidence.
Neither route is Gate A. A scientific PASS may authorize only a separately
frozen zero-new-TSC model-selected controller preflight; a scientific FAIL
requires a sequential model/action redesign.

All R8/R51/R51R1 trajectories remain probes forbidden from expert data, BC,
DAgger, residual RL, or any other learning data. Gate A, all learning, and
Gate B remain blocked.
