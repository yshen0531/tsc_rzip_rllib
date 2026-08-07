# Stage4.2R3c3T13S24D1R14R8R11 sustained exact-target-refresh authority sentinel design

Frozen prospectively on 2026-08-07 after final R8R10 primary/independent
agreement, but before opening R8R10 context-level detailed outcomes, before
R8R11 implementation or specification generation, and before any R8R11
offline construction, raw trajectory, formal metric, or TSC plant advance.

## 1. Question and boundary

R8R9 showed that two authentic canonical four-pulse schedules repaired none
of ten failing R8R7 baselines. R8R10 then showed on consumed development
contexts that isolated direction-zero 1.5x pulses improved the minimum margin
for all sixteen failed baselines but repaired none. Both campaigns returned
to the stored center at the task step immediately after issue.

R8R11 asks one new finite authority question:

```text
Does causally refreshing the exact 1.5x direction-zero Card15 target for one
additional plant interval provide any unchanged-formal-gate repair on the 16
accepted R8R7 contexts while preserving every hard action and safety gate?
```

R8R11 is a fresh authentic safety and measured-authority sentinel. It is not
a model fit, causal selector, MPC, robustness qualification, long-hold test,
Gate A, expert-data campaign, BC, DAgger, or RL stage. Its retrospective
oracle is not available to a controller. Every R8R11 trajectory is permanently
forbidden from expert and learning datasets.

## 2. Immutable sources

Before any R8R11 TSC execution, primary and structurally independent paths
must authenticate the exact accepted R8R7 run:

```text
run
  stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel_20260807_d8d231e_v1
stage
  stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel
route
  FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_PASS_MPC_DESIGN_REQUIRED
final / manifest / state SHA-256
  9ca6afce52442c1b7470cb8ff13a2eac4aab32de1e05a898d206f5fe76e01005
  ae89fb2df01cd6758676baa895880e2005a1f8967c62ea4ae671ab61ea771e24
  04f643e09f414c5d5a305f1a3584450e12e5a39e8d062d454480df3c8d95fe7e
baseline raw
  16 files / 487298 bytes
  46df626a462dfdbfe7cdf9138a50b6b19c03f0ae5e8bb18cf18c6fcbe05c01a5
multipulse raw
  32 files / 1068664 bytes
  d8435c8cd61fd082e143d79a3628ad2274780faefc6b676367df917355f49e31
```

The R6/R8 replacement direction-zero coordinate and action constructor must
also authenticate exactly. Its float64 matrix digest is:

```text
69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8
```

R8R11 inherits the exact R8R7 restart snapshots, source specs, physical
prefix, calibration, coil order/turns, Card15 quantizer, current limits, and
35/37-state episode endpoints. It may not repair, replace, resume, or relabel
any source raw. Any source mismatch stops before TSC.

## 3. Frozen contexts and two-phase matrix

Use both authenticated histories of exactly the eight R8R7 physical pairs,
for sixteen contexts. Pair/history identities are evaluator-only and are
forbidden controller inputs.

The safety phase is frozen to the first two physical pairs in the published
R8R7 ordering, both histories:

```text
p5_q1_a0p900_gap3_settle4
p5_q2_a0p750_gap3_settle4
```

The qualification phase contains both histories of the remaining six pairs:

```text
p9_q1_a0p900_gap3_settle4
p9_q2_a0p750_gap3_settle4
p5_q1_a0p750_gap4_settle4
p5_q2_a0p900_gap4_settle4
p9_q1_a0p750_gap4_settle4
p9_q2_a0p900_gap4_settle4
```

For each context execute direction zero at issue task steps `[14,18,22]` and
both fixed signs. The phase matrix is:

```text
phase 1 safety:        4 contexts * 3 issue steps * 2 signs = 24
phase 2 qualification:12 contexts * 3 issue steps * 2 signs = 72
maximum fresh authentic R8R11 trajectories                       96
```

There is no new baseline. The exact matching R8R7 baseline is authenticated
and used only by the evaluator. Phase 2 is not authorized until all 24 phase-1
raw files pass primary and independent execution/action/safety audits. Formal
tracking outcomes are not computed or opened during phase-1 authorization.
No sign, time, context, or stopped member may be removed or replaced.

## 4. Causal sustained action contract

Every rollout uses a fresh controller and fresh TSC process, authentic restart,
and the exact inherited physical action/trace prefix through task step 9. The
future R17 controller is never executed.

For scheduled issue step `s`:

```text
task steps 10..s-1    exact zero incremental normalized action
task step s           construct and issue the fixed signed 1.5x direction-0
                      exact Card15 target from current measured coil currents;
                      store both issue center and exact target fields
state s+1             first authentic post-issue observation
task step s+1         causally reconstruct an action to the same stored exact
                      Card15 target using only current visible coil currents
state s+2             second authentic interval under the refreshed target
task step s+2         causally return to the stored issue-center Card15 fields
state s+3 onward      exact zero incremental action to state 35 or 37
```

The refresh is not a copied source action and is not an open-loop repeated
normalized vector. It is newly constructed from current measured coil
currents and controller-owned past target fields. Issue, refresh, and cancel
are each verified against the resulting actuator readback before the
corresponding plant advance.

The controller may use only the fixed schedule/sign/coordinate, current and
past visible observation, current measured coil currents, allowed target,
causal clock fields, and its own stored center/target. Pair/history/target ID,
partition, source outcome, matched baseline future, source action/current,
wire or vessel current, future action/measurement, and post-advance telemetry
are forbidden.

## 5. Offline construction and fail-closed gates

Before phase 1, reconstruct all 96 issue candidates from the authenticated
R8R7 baseline current centers without opening any counterfactual outcome.
Every construction must pass exactly. Refresh and cancel depend on new causal
readback and are therefore checked online.

Before each issue, refresh, or cancellation plant advance require:

```text
finite exact construction and actuator readback                  true
exact requested/stored Card15 target reproduction                true
no action saturation or current clipping                         true
maximum issue/refresh incremental normalized L-infinity        <= 0.25
maximum cancellation incremental normalized L-infinity         <= 0.24
original cancellation cap                                      <= 0.25
maximum total normalized action absolute value                 <= 1.0
maximum current utilization                                    <= 0.55
issue desired/applied current cosine                           >= 0.98
issue relative off-basis residual                              <= 0.10
exact center-to-target-to-center Decimal net                      zero
```

Before applying the refresh or cancellation, the currently observed R/Z/Ip,
coil currents, and wire currents must be finite; solver, actuator, and plant
abnormal flags must be clear; and all current limits must remain valid. An
unrepresentable or out-of-envelope candidate is rejected before plant advance,
the member records a structured safe stop, and no later action or plant step
may occur. Any structured stop fails the corresponding phase and is classified
as an action-schedule/safety result rather than a formal-control miss.

All executed members must additionally pass exact restart/snapshot/spec,
physical prefix, calibration, Card15 target/readback, issue/refresh/cancel
clock, zero-before/after action, finite raw, full expected horizon, no
forbidden input, and primary/independent raw-inventory gates.

## 6. Frozen formal authority computation

Formal tracking is computed only after both phases complete and authenticate.
The unchanged contract is:

```text
slew 1.0/1.1: arrive no later than state 25, hold through state 35
slew 0.9:     arrive no later than state 27, hold through state 37
R/Z <= 0.03 m, speed <= 0.1 m/s, Ip <= 10000 A, arrival streak 3
```

The longer action hold does not move either arrival deadline. For each of the
16 contexts, independently recompute the matching R8R7 baseline and all six
R8R11 trajectories through both the compact algebraic evaluator and the
complete tracking-metric implementation. Pass, selected arrival, minimum
signed margin, and mean signed margin must agree at absolute tolerance
`1e-12`.

Candidate ranking is fixed by minimum signed margin, then mean signed margin,
then `(issue_step, sign)`. Define a retrospective do-nothing-safe held oracle
as the baseline plus its six measured R8R11 rows. This oracle is evaluator-only
and is not causal controller evidence.

The scientific authority gate requires all of:

```text
matching R8R7 baseline formal pass reproduction                    6/16
failed baseline count                                                10
at least one failed baseline repaired by an R8R11 trajectory       >= 1
held oracle formal pass                                             >= 7/16
held oracle formal pass strictly greater than baseline                  true
primary/independent numerical, scientific, and route agreement          true
```

Every miss remains a miss. No post-result time, sign, amplitude, duration,
margin threshold, or formal deadline may be changed.

## 7. Routes

```text
source/package/spec/offline-construction mismatch before TSC
  SUSTAINED_EXACT_TARGET_REFRESH_SOURCE_OR_PREFLIGHT_FAIL_NO_TSC

any runtime/raw/restart/issue/refresh/cancel/current/safety failure
  SUSTAINED_EXACT_TARGET_REFRESH_EXECUTION_OR_SAFETY_FAIL_STOP

all integrity and safety gates pass but the formal authority gate fails
  SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_INSUFFICIENT_ASYMMETRIC_SEQUENCE_REDESIGN_REQUIRED

all integrity, safety, formal-equivalence, and authority gates pass
  SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_PRESENT_CAUSAL_SELECTOR_DESIGN_REQUIRED
```

A PASS authorizes only a separately frozen causal selector/controller design
and cannot itself authorize more TSC, MPC claims, robustness qualification,
Gate A, or learning. A FAIL cannot be tuned under the R8R11 identity and must
move to a genuinely asymmetric or multi-direction sustained sequence. All
R8/R8R1/R8R7/R8R8/R8R9/R8R10/R8R11 evidence remains forbidden from expert
data, BC, DAgger, and RL.
