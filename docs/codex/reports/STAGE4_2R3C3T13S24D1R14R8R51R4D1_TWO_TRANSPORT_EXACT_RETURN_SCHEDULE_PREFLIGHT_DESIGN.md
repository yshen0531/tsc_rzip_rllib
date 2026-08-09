# Stage4.2R3c3T13S24D1R14R8R51R4D1 two-transport exact-return schedule preflight design

Status: prospectively frozen on 2026-08-10 after the final aggregate R51R4
route, repair count `0/10`, and measured-oracle count `6/16` were known, but
before any R51R4 per-row, per-candidate, or per-timing formal result was read,
before any successor construction was generated, and before any successor
TSC, controller, plant step, raw response, or optimization.

## 1. Question and immutable source boundary

R51R4 proved that one fixed transport current sustained from task step 12
until exact return at task step 16 or 18 repairs none of its ten failed
contexts. This rejects that single-transport/dwell family only. R51R4D1 asks
the narrower action-geometry question:

```text
Can a fixed two-transport causal schedule be represented exactly and safely
for a sufficiently diverse set of ordered transport pairs before any new
physical response is requested?
```

R51R4D1 is zero-new-TSC. Its immutable sources are the final independently
agreed R51R4 hotfix artifacts, the exact R51R4 100-file raw inventory, the
R51R4 offline construction, and the same authenticated R51R1/R8R7 source
contracts. It must require the exact final route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_INSUFFICIENT_LONGER_SEQUENTIAL_REDESIGN_REQUIRED
```

R51R5 and its conditional R51R6 controller route remain blocked and unrun.
No old campaign may rerun. No source or future R51R4D1 artifact may enter
expert, BC, DAgger, residual-RL, or any other learning data.

## 2. Frozen contexts, actions, and task clock

Use exactly the ten failed physical contexts already frozen by R51R4 and the
same five development action identities, without response-based ranking:

```text
d0m  d1p  d2m  d3p  u1p50
```

Enumerate the complete ordered Cartesian product, including equal pairs:

```text
10 contexts x 5 first transports x 5 second transports = 250 specifications
```

The schedule is fixed before construction:

```text
source semantic prefix                                  task steps 0..9
shared exact Card15 q0 target issue                     task step 10
q0 observation hold                                    task step 11
first authenticated transport target issue             task step 12
exact first-target zero-increment holds                 task steps 13..15
second authenticated transport target issue            task step 16
exact second-target zero-increment holds                task steps 17..19
exact stored q0-center return                           task step 20
exact center refresh                                    through state 35/37
```

For an equal ordered pair, the step-16 event is an exact zero increment and
therefore represents a longer single-target dwell. For a distinct pair it is
one direct exact Card15 target-to-target transition. No interpolation,
response fit, outcome lookup, target relabeling, or adaptive timing is
allowed.

## 3. Exact construction and eligibility rule

Primary and structurally independent scalar implementations must construct
all 250 specifications and agree exactly on every Card15 field, action,
current, criterion, eligibility decision, event stream, and digest. Every
specification remains in the report; an ineligible specification is never
silently dropped.

Eligibility is determined only from the prospectively fixed exact event
geometry and the unchanged safety limits:

```text
shared q0 issue and q0 normalized Linf <= 1e-5
each nonzero incremental normalized action Linf <= 0.25
each total normalized action absolute value <= 1.0
predicted current utilization <= 0.55 at every event
desired/applied current cosine >= 0.98 for nonzero transitions
relative off-basis residual <= 0.10 for nonzero transitions
equal-pair step-16 increment exactly zero
stored-center return and every later refresh exactly reconstruct q0
no clipping, saturation, forbidden input, nonfinite value, or row exclusion
```

The first and second target coordinates must be the immutable R51R1 values
for their candidate identities. Pair/history labels, formal outcomes,
post-step-12 measured states, wire/vessel current, another rollout, and any
R51R4 response value are forbidden construction inputs.

## 4. Frozen coverage gate

The preflight PASS gate is deliberately about action support, not response:

```text
all 250 specifications constructed and reported                 250/250
all exact source/authentication/forbidden-input gates            250/250
eligible ordered pairs per context                                  >= 10
each of five candidates eligible as a first target per context       5/5
each of five candidates eligible as a second target per context      5/5
eligible ordered-pair identity set equal within each history pair     5/5
at least one eligible distinct second target for each first target    5/5
primary/independent eligibility and event-stream agreement            exact
```

No minimum is weakened after construction. Eligibility may not be selected
using R51R4 formal margin, candidate rank, timing result, or any physical
response.

## 5. Routes and next authorization

```text
R51R4/source/hash/raw/final-independent authentication fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_BLOCKED_BY_SOURCE

construction, exactness, safety, coverage, or independent gate fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_TWO_TRANSPORT_SCHEDULE_GEOMETRY_INSUFFICIENT_NO_REAL_TSC

all frozen gates pass
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_TWO_TRANSPORT_SCHEDULE_PREFLIGHT_COMPLETE_R51R4D2_DESIGN_REQUIRED
```

A PASS authorizes only prospective freezing of an R51R4D2 real two-transport
response-identification sentinel over the complete eligible set. It does not
itself authorize Ray, `gotsc`, TSC, a controller, a plant step, model fitting,
formal-control claims, or a model-selected controller.

## 6. Scientific and qualification boundary

R51R4D1 is an offline exact-action feasibility and coverage test. It is not a
response-model, authority, controller, MPC, formal-control, robustness,
long-hold, independent-holdout, plant-reachability, or Gate A result. Gate A,
expert data, BC, DAgger, residual RL, and Gate B remain blocked.
