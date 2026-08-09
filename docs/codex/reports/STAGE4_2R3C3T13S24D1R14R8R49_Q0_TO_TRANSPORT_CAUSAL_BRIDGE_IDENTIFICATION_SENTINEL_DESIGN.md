# Stage4.2R3c3T13S24D1R14R8R49 q0-to-transport causal-bridge identification sentinel design

Status: conditionally and prospectively frozen on 2026-08-09 after final
R8R46, but before any R8R48 numerical bridge result was generated or opened
and before any R8R49 config, source, offline construction, package, deployment,
Ray, `gotsc`, TSC, controller, plant step, raw, or snapshot.

## 1. Conditional source gate and purpose

R8R49 is authorized only if final primary/independent R8R48 agrees exactly on:

```text
Q0_CALIBRATION_TO_TRANSPORT_CAUSAL_BRIDGE_SUPPORT_ABSENT_FRESH_SENTINEL_REQUIRED
```

If R8R48 has any other route, R8R49 is permanently blocked. Its source config
must later freeze the exact final R8R48 file hashes before implementation or
execution.

R8R49 creates the missing finite experiment coordinate only. It asks whether
the exact q0 calibration prefix can be followed safely and causally by each
fixed transport candidate in every authenticated context. It does not fit or
select a model, optimize tracking, run a receding controller, or qualify MPC.

## 2. Frozen matrix and provenance

Use exactly the 16 R8R31/R8R46 authenticated `(pair_id, history_member)`
contexts and their authentic restart state/snapshot, target, horizon, slew,
delay, actuator, Card15, coil limits, and fixed four-coordinate basis. Use the
canonical matrix digest:

```text
c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
```

Use the exact canonical 17-candidate order and exclude only index zero. No
amplitude, direction, context, or outcome selection is allowed:

```text
16 contexts x 16 nonzero candidates = 256 authentic trajectories
```

Every trajectory is an identification/safety probe and is permanently
forbidden from expert, BC, DAgger, residual-RL, or any other learning data.

## 3. Frozen causal action schedule

Each trajectory starts from its authentic restart and uses only completed
visible R/Z/Ip, completed 14-coil current readback, target, task clock, and
causal controller memory reset at restart. Hidden state, wire/vessel current,
pair/history label as a control input, future data, evaluator outcome, and
another rollout are forbidden.

The schedule is:

```text
task step 10  exact Card15 current-target hold (q0 calibration issue)
steps 11-12  observe; no transport action
task step 12  construct and issue the assigned fixed nonzero candidate
steps 13-14  observe the first two physical-effect samples
task step 14  exact stored-pretransport-center return
later steps   exact current-target refresh/hold through the original 35/37
              horizon; no additional transport action
```

At task step 12, save the exact Card15 center fields representing the measured
pretransport current, then construct the candidate with the inherited dynamic
exact-search radius 16. At task step 14, use the existing exact-stored-center
inverse; do not approximate a negated floating action. A failed issue or
return gate stops before applying the failed action and before any later plant
advance. The rejected command and full causal prefix remain auditable.

The q0 prefix through completed task step 12 must be exactly identical across
all 16 candidates within each context, including visible state, coil current,
issued fields, action trace, and controller state. The candidate first
physical effect is `issue_step + 1`; software-delay reinterpretation is
forbidden.

## 4. Unchanged hard action and current gates

Both issue and exact-center return must satisfy before plant advance:

```text
exact Card15 issue and refresh                         required
incremental normalized action L-infinity              <= 0.25
total normalized action absolute value                <= 1.0
maximum current utilization                           <= 0.55
desired/applied current cosine                        >= 0.98
relative off-basis residual                           <= 0.10
finite values, no action saturation, no current clip required
```

The stored-center return must reproduce all 14 stored Card15 fields exactly.
All later holds must preserve the last accepted exact target and remain inside
the same current/utilization limits. No gate can be relaxed after a structured
stop.

## 5. Integrity and identification gates

R8R49 PASS requires primary plus independent server-raw recomputation to
establish:

```text
strict raw files and complete successful trajectories             256/256
authentic plant/controller restart                                 256/256
causal trace and forbidden-input gate                              256/256
exact q0 issue and within-context prefix through step 12           256/256
fixed candidate identity and canonical coordinate                 256/256
safe exact Card15 candidate issue                                  256/256
first physical effect at issue+1                                   256/256
finite measured states/currents at states 13 and 14                256/256
safe exact stored-center return                                    256/256
exact stored Card15 center recovery                                256/256
full original horizon                                              256/256
candidate/context bridge coverage                                  256/256
runtime / solver / saturation / current / forbidden-input errors         0
maximum current utilization                                        <=0.55
primary/independent discrete identities, counts, hashes, route       exact
```

Record signed physical response at states 13 and 14 relative to the q0
reference for later model design, but do not impose a post-outcome response-
size threshold and do not fit a model in R8R49. Exact zero or small plant
response remains evidence to be reported, not relabeled as runtime failure.
Formal tracking is diagnostic only because these are probes and the schedule
is not a feedback controller.

## 6. Frozen routes

```text
R8R48 source route/hash or inherited evidence fails
  Q0_TO_TRANSPORT_BRIDGE_SENTINEL_BLOCKED_BY_SOURCE

offline matrix/action construction fails before any plant advance
  Q0_TO_TRANSPORT_BRIDGE_SENTINEL_OFFLINE_FAIL_NO_REAL_TSC

runtime, raw, restart, causality, or evidence-integrity failure
  Q0_TO_TRANSPORT_BRIDGE_SENTINEL_EXECUTION_FAIL_STOP

any hard issue/return/current/saturation gate safely rejects a trajectory
  Q0_TO_TRANSPORT_BRIDGE_SENTINEL_SAFETY_FAIL_REDESIGN

all 256 finite authentic bridges and all integrity/safety gates pass
  Q0_TO_TRANSPORT_BRIDGE_IDENTIFICATION_COMPLETE_MODEL_PREFLIGHT_REQUIRED
```

Structured safe stops are not plant-control failures. A PASS certifies only
the finite q0-to-first-transport bridge dataset and authorizes only a new,
prospectively frozen zero-TSC model/tube preflight. It does not authorize a
real controller.

## 7. Formal timing and scientific limits

The original horizon remains 35 steps for normal slew and 37 for weak slew.
Nothing changes the immutable formal contract:

```text
slew 1.0/1.1  arrive by 250 ms; hold/evaluate through 350 ms
slew 0.9      arrive by 270 ms; hold/evaluate through 370 ms
R/Z           30 mm
speed         0.1 m/s
Ip            frozen 10 kA threshold
arrival       frozen three-sample streak
```

R8R49 is not an arrival/hold qualification, long-hold test, disturbance test,
controller, MPC, global reachability, or Gate A result. It may not weaken
R8R46 or reuse R8R47. After packaging, direct-copy deployment, server
preflight, package/hash/`bash -n`/compile/full-test validation, any real TSC
run requires a separate authorization step that authenticates the exact final
R8R48 route and this frozen design. Gate A and all learning remain blocked.
