# Stage4.2R3c3T13S24D1R14R8R51R4D3 center-bridged two-pulse schedule preflight design

Status: prospectively frozen on 2026-08-10 after final corrected R51R4D1
forensics, but before any R51R4D3 schedule was constructed, before any D3
eligibility or coverage result was computed, and before any successor TSC,
controller, plant step, response, model, or optimization.

## 1. Scientific question and source boundary

R51R4D1 rejected a direct first-target-to-second-target transition at task
step 16: only 68/250 ordered pairs passed unchanged action geometry, and no
context met the frozen coverage gate. D1 does not test a sequence that returns
through the exact q0 center between two independently safe pulses.

R51R4D3 asks only:

```text
Can all frozen ordered target pairs be represented as two individually exact,
safe Card15 pulses separated by an exact q0-center return and hold?
```

D3 is zero-new-TSC. It must authenticate:

1. the final corrected R51R4D1 run and route;
2. corrected D1 audit PASS, 68/250 eligibility, 0/10 context coverage, and
   frozen action-stream digest;
3. the final independently accepted R51R4 evidence and its exact source
   inventories;
4. the unchanged R51R1/R8R7 action and actuator contracts inherited by D1.

R51R4D2 required D1 PASS and remains blocked and unrun. D3 is a new schedule
identity, not a relabeling or weakening of D1.

## 2. Frozen matrix and task clock

Use the same ten failed physical contexts and complete ordered product:

```text
candidates = d0m, d1p, d2m, d3p, u1p50
10 contexts x 5 first pulses x 5 second pulses = 250 specifications
```

The complete task clock is fixed before construction:

```text
source semantic prefix                                  task steps 0..9
shared exact Card15 q0 issue                            task step 10
q0 observation hold                                    task step 11
first authenticated candidate issue                    task step 12
exact first-target holds                                task steps 13..15
first exact stored-center return                        task step 16
exact q0-center bridge hold                             task step 17
second authenticated candidate issue from q0            task step 18
exact second-target holds                               task steps 19..21
second exact stored-center return                       task step 22
exact q0-center refresh                                 through state 35/37
```

An equal ordered pair is two physically separated pulses with an exact center
return and hold between them. Its second issue is therefore required to
reproduce the authenticated nonzero q0-to-candidate issue; D1's equal-pair
zero-increment predicate applied only to its direct same-target dwell and does
not apply to this new schedule.

## 3. Frozen construction rule

Each q0-to-candidate issue and candidate-to-q0 return must be reconstructed
from the immutable candidate coordinate, exact Card15 actuator boundary, and
the causal current at that task step. No direct target-to-target transition is
allowed. No interpolation, response fit, formal outcome, per-row D1 result,
candidate ranking, adaptive timing, target relabeling, or future state may
select or alter a path.

For every event require the unchanged gates:

```text
q0 integration normalized Linf <= 1e-5
nonzero incremental normalized action Linf <= 0.25
total normalized action absolute value <= 1.0
predicted current utilization <= 0.55
desired/applied current cosine >= 0.98 for nonzero transitions
relative off-basis residual <= 0.10 for nonzero transitions
exact Card15 target and exact stored q0-center reconstruction
no clipping, saturation, forbidden input, nonfinite value, or row exclusion
```

The post-return componentwise-zero command representation remains diagnostic
only. Exact Card15/current reconstruction and the unchanged event gates are
scientific. All 250 rows must remain in the report, including failures.

## 4. Independent implementation and PASS gate

Primary and structurally independent scalar implementations must separately
construct all schedules. The independent path may share exact actuator/Card15
primitives but may not call the primary schedule constructor, primary
eligibility function, or primary coverage function. It must implement its own
scalar geometry projection and coverage algebra.

The frozen D3 PASS gate is:

```text
source and corrected-D1 authentication                         PASS
specifications constructed/reported                        250/250
every specification passes every frozen event/safety gate  250/250
all five candidates supported in each position              10/10 contexts
all 25 ordered pairs eligible                                10/10 contexts
eligible pair set equal within each physical history pair      5/5
primary/independent event, criterion, eligibility agreement   exact
primary/independent numerical difference                    <= 1e-10
new TSC/raw/plant/controller/model/optimization                    0
```

The 250/250 gate may not be weakened after construction. D1 response and
formal outcomes are authentication evidence only and are forbidden from path
selection or eligibility.

## 5. Routes and next authorization

```text
source, corrected-D1, hash, or independent integrity fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D3_BLOCKED_BY_SOURCE_OR_INTEGRITY

any exact schedule, safety, geometry, coverage, or agreement gate fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D3_CENTER_BRIDGED_TWO_PULSE_GEOMETRY_INSUFFICIENT_NO_REAL_TSC

all frozen gates pass
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D3_CENTER_BRIDGED_TWO_PULSE_SCHEDULE_PREFLIGHT_COMPLETE_R51R4D4_DESIGN_REQUIRED
```

A PASS authorizes only prospective freezing of an R51R4D4 real response
sentinel. It does not authorize that sentinel until its matrix, response
question, safety stop, raw/independent gates, and no-learning boundary are
separately frozen. It never directly authorizes a model-selected controller.

## 6. Scientific and learning boundary

D3 is action geometry only. It is not a response, authority, observer,
controller, MPC, formal-control, robustness, plant-reachability, or Gate A
result. All R51R4/D1 and any future pulse trajectories are probes forbidden
from expert data, BC, DAgger, residual RL, or other learning. Gate A and Gate B
remain blocked.
