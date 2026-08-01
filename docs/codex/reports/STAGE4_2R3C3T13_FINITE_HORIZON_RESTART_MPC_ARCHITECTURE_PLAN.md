# Stage4.2R3c3T13 finite-horizon restart MPC architecture plan

## Status

Stage4.2R3c3T13 is the active no-new-TSC architecture and evidence-mapping
stage after the completed T12 route discriminator. This document freezes the
scope and stopping rules for the architecture analysis. It does not yet
freeze controller gains, a prediction model, an optimizer, a sentinel action
schedule, or a real experiment identity.

T13 may inspect local source and compact evidence and may perform read-only
server-side postprocessing of large existing raw files. It may not launch
Ray, `gotsc`, TSC, a plant step, a controller rollout, a new snapshot, or a
full identification campaign.

## Evidence that changes the route

The route is no longer “repair response conditioning and then build R3c4.”
T12 proved:

```text
formal FAIL while T11 condition PASS                         13/32
formal PASS while T11 condition FAIL                          4/32
failed baselines repaired by a measured T11 single probe      0/16
best measured gap coverage                              0.47%--11.46%
```

R3c1 and R3c2 already isolate two controller defects:

1. A static visible R/Z/Ip phase label does not reconstruct velocity,
   controller memory, or pending actuator state.
2. Zero-nominal target regulation discards the transport plan and becomes a
   local damping controller. It passed 12/32 and failed all 16 prefix-5
   cases.

T3--T11 further show that adding fixed whole-episode response bases,
quadratic fits, interaction terms, larger amplitudes, or better condition
numbers did not repair any of the sixteen failed baselines. The next design
must therefore begin from the causal finite-horizon control problem rather
than from another probe family.

## Architecture that T13 must specify

T13 must produce an exact interface for a restart-integrated,
target-conditioned, delay-aware finite-horizon MPC with these non-negotiable
properties.

### Independent clocks

```text
formal task clock
  always starts at zero after restart and determines the unchanged
  250/270 ms arrival deadline and 350/370 ms hold endpoint

local model coordinate
  selects or constructs the response/Jacobian appropriate to the current
  state and may not shorten, shift, or reinterpret the formal horizon
```

### Causal controller state

The specification must state how the controller constructs, updates, and
uncertainty-bounds:

- current R/Z/Ip and causally estimated velocities;
- target-relative error;
- integral and previous-correction memory;
- measured coil currents;
- issued-command and delay queues created in the current run;
- actuator delay/gain/slew hypotheses;
- latent vessel/eddy-history uncertainty not directly visible to the
  controller.

Pair/history/prefix labels, hidden wire currents, source future actions,
source results, source wire/coil-current traces, and current-run future values
remain forbidden controller inputs. If the allowed observations are
insufficient to distinguish a required latent state, T13 must route to a
causal observer or robust multi-hypothesis/tube formulation; it may not use a
development label as a shortcut.

### Target-conditioned transport and braking

The controller must retain target-conditioned nominal transport while using
the measured restart state as a causal residual. It must represent transport,
deceleration, arrival, and hold as different parts of one finite-horizon
problem. A zero-nominal terminal regulator and a static phase replay are both
excluded.

The decision variable must be a bounded time sequence applied through the
actual actuator delay/slew/current mapping. Coefficients of a fixed
whole-episode T3--T11 probe bank are not an acceptable controller decision
space.

### Formal constraints and safety

The architecture must encode, without relaxation after results:

- 30 mm R/Z tolerance;
- unchanged Ip threshold and arrival streak;
- 0.1 m/s speed threshold;
- arrival no later than 250 ms for slew 1.0/1.1 and 270 ms for slew 0.9;
- hold/evaluation through 350/370 ms;
- actuator delay, gain, slew, command, and coil-current limits;
- a trust region/model-validity constraint;
- deterministic infeasibility and solver-failure fallback;
- trace fields sufficient to audit causality, model phase, formal time,
  queue state, constraints, and applied action.

Velocity/deceleration must appear as an explicit deadline and post-arrival
constraint or robust constraint, not only as a soft terminal penalty.

## Required evidence map

T13 must build a source-hash-backed table for each architecture component:

| Required component | Existing evidence to inspect | Required T13 conclusion |
|---|---|---|
| finite clean target-conditioned transport | R17 and its R14/R16 source chain | what can be reused without replay semantics |
| exact plant restart | R1c | state-load contract only |
| persistent controller restart | R2 | which controller/queue states are reproducible |
| authentic fresh restart failures | R3c1 and R3c2 | initial-state and clock defects |
| local signed responses | R3c3, T1--T3, T6, T9, T11 | which state/time/action neighborhoods are actually measured |
| interaction | T9/T10 | where superposition is invalid or exact only at measured corners |
| formal-gap alignment | T12 | which model metrics are task-relevant |
| current headroom | T8/T11 | safety envelope, not reachability proof |
| hidden-history pairing | R3c3/T1/T11 matched-history gates | finite response consistency only, not robustness certification |

No old derived bank may be silently promoted to a validated predictor. Exact
raw/source/config hashes and the physical meaning of every feature and action
must be recorded.

## T13 deliverables and gates

T13 is complete only when all of the following exist:

1. A mathematical controller-state, decision-variable, dynamics/prediction,
   constraint, objective, clock, and queue specification.
2. A causality table listing every allowed input and every forbidden input.
3. A source-code call graph showing which R17/R3c1/R3c2 components are reused,
   replaced, or prohibited.
4. An evidence-coverage matrix with exact hashes and no verdict-only claims.
5. A model-gap table separating measured support, interpolation, and
   extrapolation for every context/time/action dimension.
6. A solver/fallback and trace-audit contract.
7. One of two prospective route decisions:

```text
OFFLINE_ARCHITECTURE_COMPLETE
  existing evidence is sufficient to implement and unit-test the controller
  offline, but this does not authorize real TSC

MINIMAL_SENTINEL_REQUIRED
  one specific missing task-relevant response prevents a defensible model;
  freeze a small sentinel with an explicit fail-stop/full-campaign veto gate
```

The sentinel decision must precede its action schedule and all real results.
A sentinel may not be expanded into a 32-context campaign automatically.

## Stop rules

T13 must stop and redesign rather than proceed when:

- the proposed state requires a forbidden source or hidden-history label;
- formal task time is inferred from visible manifold phase;
- the proposed controller removes target-conditioned nominal transport;
- the prediction model relies on a T11 bank or an invalid T6/T7/T10/R16
  extrapolation;
- constraints are checked only after optimization rather than represented in
  the controller and independently audited;
- a missing response is answered by post-hoc condition normalization,
  threshold relaxation, or amplitude-only rescaling;
- the proposed sentinel cannot prospectively distinguish “architecture
  viable” from “stop and redesign.”

## Scientific scope

Even a successful T13 architecture and later development controller would
not validate independent hidden histories, unseen targets, continuous plant
or actuator parameters, noise, disturbance recovery, or long hold. Those
remain sequential prerequisites before expert-data collection.

R3c4, BC, DAgger, and bounded residual RL remain unauthorized.
