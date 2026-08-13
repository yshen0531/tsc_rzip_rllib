# R_geo/Z_geo 1 ms post-NR2R1 architecture reassessment

Status: documentation-only architecture decision on 2026-08-13
Asia/Shanghai.

Decision route:

```text
POST_NR2R1_REASSESSMENT_COMPLETE_NR2R2A_DESIGN_AUDIT_REQUIRED
```

This report changes no signal, actuator, runner, queue, controller, reward,
termination, Card15 or TSC state semantics.  It ran no server command, TSC,
plant advance, model fit, training, optimization or data generation.  It does
not authorize NR3 or a new real-TSC campaign.

## 1. Evidence and claim boundary

The reassessment used the tracked source and reports at local checkpoint
`fe7d9fb`, plus read-only descriptive parsing of the locally retained NR2R1
compact trajectory records.  New numerical checks below use only the valid
NR2R1 development and calibration partitions.  The erroneously authorized
holdout remains diagnostic-only and is not used to choose a successor model,
feature, action, horizon or threshold.

The exact compact-record input inventory, hashes, scalar definitions and
reproduced values are recorded in
`docs/codex/audits/rgeo_zgeo_1ms_post_nr2r1_reassessment_20260813/`.
NR2R1 development/calibration is thereby consumed as architecture-development
evidence and cannot serve as blind NR2R2 calibration or holdout evidence.

Historical campaigns are used only as immutable architecture evidence.  They
are not relabelled, refitted or admitted into the new route's learning data.

The accepted hard contract remains:

```text
fixed takeover time                         1100 ms
control period                                 1 ms
per-coil single-turn current step          <= 0.3 A absolute
equality at either endpoint                  allowed
Card15 serialization unit                 kA-turn
R_geo/Z_geo source            one valid same-step plasma boundary
boundary invalid                           fail closed
Ip                                coupled observation and safety state
R_mid crossing                 continuous history, never a mode reset
```

## 2. Bottom-line judgment

The overall recommendation remains sound:

> history-conditioned, uncertainty-aware constrained receding-horizon
> control, with an independent hard actuator/safety boundary.

The implementation order did not remain faithful to that architecture.  NR2
started a model-class bake-off before establishing that its experiment could
separate operating point, arrival history, autonomous drift, action age and
signed action response.  The appropriate correction is therefore not a
larger GRU/LSTM and not immediate NR3.  It is to move contextual
identifiability, explicit memory and moving-prefix replay qualification in
front of the next model comparison.

The user's intuition is directionally correct: the effect of a coil command
can depend on position and history.  The precise current statement is:

> The local input/output map should be conditioned on continuous operating
> point, coil-current baseline and a causal belief over passive/history state.

Existing evidence does **not** yet prove that a particular coil's R response
changes sign between two positions.  Prior frozen finite experiments provide
direct counterexamples to treating a globally odd, context-independent
response map as universally valid in their tested contexts/action families.
NR2R1 adds descriptive evidence that its instantaneous representation is
poorly supported, but it did not independently separate position from
history or establish a safety theorem.

## 3. What was correct before NR2

The following decisions should not be rolled back:

1. NR0's paired same-boundary `R_geo/Z_geo` definition and fail-closed parser;
2. one belief/history identity through every `R_mid` crossing;
3. NR1's exact separation of Card15 command, actual readback, 1 ms effect
   timing and the closed `0.3 A` single-turn step limit;
4. NR2R1's exact structural propagation of the actuator coordinate;
5. complete-trajectory splitting, future-field rejection and free recursive
   evaluation;
6. correction of the interval-statistics bug and refusal to treat the opened
   holdout as qualification evidence.

NR2R1 completed 576/576 authentic advances without a runtime, solver,
saturation, boundary, slew or structural-current failure.  Its outcome is a
model/uncertainty qualification failure inside a poorly covering experiment,
not a TSC or global control-authority failure.

## 4. What NR2R1 actually covered

Read-only development/calibration recomputation gives:

| Quantity | Observed finite envelope |
|---|---:|
| trajectories / states | 28 / 476 |
| distinct physical 1100 ms starts | 1 |
| `R_geo` span | 9.5274 mm |
| `Z_geo` span | 11.9430 mm |
| `R_geo-R_mid` span | -92.7923 to -83.2649 mm |
| HFS states | 476/476 |
| mean 16 ms endpoint change | -9.4848 mm R, +11.8776 mm Z, -165.44 A Ip |

Across trajectories, the between-time sum of squares divided by the total
sum of squares is `99.883%` for R, `99.977%` for Z and `97.273%` for Ip.  This
descriptive fraction uses strongly correlated deterministic rows; it is not a
significance test or causal variance decomposition.  Because the campaign had
no independent full-horizon all-q0 baseline, the common time trajectory
cannot be cleanly separated into autonomous scenario drift and even/nonlinear
action response.

The signed-pair half-difference is much smaller than that common trajectory:
its largest observed absolute R/Z value over development/calibration was
approximately `0.3753/0.2193 mm`.  Thus the dataset mainly samples one narrow
time-parametrized path near one HFS start, not a two-dimensional position
domain.  This half-difference is a descriptive odd component, not a
zero-baseline local Jacobian.

All targets were confined to `q0 +/- 0.30 A` or `q0 +/- 0.15 A`.  This obeys
the hard contract, but it does not exercise the separately allowed case of
successive same-direction steps, each no larger than `0.3 A`, that move the
Card15 current center and plasma through a larger finite domain.

Static command rank 14 was real but insufficient.  It proves only that the
chosen command rows span the instantaneous 14-coil input space.  It does not
prove plasma-response signal, lagged-regressor support, local controllability,
history observability or coverage of a position-dependent Jacobian.  Dense
random 14-coil directions also make attribution and nonlinear interaction
hard when development contains only ten signed trajectory pairs comprising
forty scheduled event directions and their sign mates.

## 5. Direct evidence that history cannot be treated as incidental

Within the valid development/calibration records, the twelve impulse paths
at step 11 have the same q0 coil-current readback and issue a zero command
increment.  Their current visible states are close but not identical:

```text
current-state span       0.1457 mm R / 0.1041 mm Z / 25.18 A Ip
next-delta span          0.8316 mm R / 0.3495 mm Z / 13.55 A Ip
maximum wire-current component span                     10.403 A
```

These paths differ in preceding signed impulses.  The comparison shows a
large successor spread associated with different causal prefixes, consistent
with action-tail/context effects; specifically, the **spread among their next
increments**, not the magnitude of any one increment, is quoted above.  It
does not prove an exact observational alias, isolate a pure hidden-history
contribution or quantify causation, because the visible states are not exactly
equal and the full wire-current vector is different.  It shows that position,
Ip, current command and instantaneous coil current as represented here do not
support a unique deterministic point prediction at this tested origin.

Wire/passive current may be used as an offline diagnostic or auxiliary label.
It may enter a deployable controller only if the future deployed interface
really provides it; otherwise the causal observer must infer the relevant
belief state without a silent TSC-only field.

Historical evidence points in the same direction without proving a pure
position effect.  It comes from the retired route under different finite
contracts/time scales and is methodological evidence only for the 1 ms route:

- S5/S6/S10 rejected a single static cross-history transition map;
- D1R14R2 applied physically symmetric signed actions but found four genuine
  context/sign-dependent response-symmetry failures;
- R8R2 could not qualify its causal no-action baseline forecast, so its online
  update was never reached;
- R8R6 later qualified a static observer, while its one-step innovation
  adapter made aggregate error `7.81%` worse and was correctly disabled.

The last point does not predict which observer will win in the new domain.  It
does show that online adaptation is a hypothesis that must earn its place
against a frozen baseline, not an automatic improvement.

## 6. The earlier design mistake

The earliest substantive error was not fixed 1100 ms, NR0 or NR1.  It was the
NR2 ordering:

```text
model-class comparison
before
state/history/action identifiability and work-domain coverage
```

Specific consequences were:

1. **One start was treated as a work domain.**  Every trajectory independently
   reset to the same snapshot.  Position, absolute time and common drift were
   almost collinear.
2. **No matched context experiment existed.**  The campaign did not repeat
   the same primitive at multiple reached positions and did not construct
   close visible-state twins with different causal arrival histories.
3. **No full zero-action baseline existed.**  q0 intervals after a pulse still
   contain its tail; signed averaging cannot replace a baseline because even
   and sign-dependent responses have already been observed.
4. **The intended explicit memory was omitted.**  The implemented backbone was
   an eight-frame ARX plus a small residual network, not exact actuator plus a
   stable low-order passive-memory state-space model plus residual.
5. **History initialization was artificial.**  ARX left-pads a short history
   by repeating its first observed frame.  This is causal bookkeeping, not a
   measured pre-1100 history or a calibrated set-valued prior.
6. **Memory lengths were chosen before measuring the tail.**  ARX sees at most
   eight frames, the TCN has a shorter receptive field, and GRU/LSTM see the
   growing 1--16 frame sequence.  The comparison therefore also mixes memory
   availability with model class.
7. **The time feature can become a shortcut.**  `step/16` is causal, but in a
   single-start experiment it can reproduce the common drift without learning
   a transferable state-conditioned mechanism.
8. **Training and intended use were imperfectly aligned.**  Neural residuals
   were optimized on one-step residuals and selected by recursive rollout.
   Recursive selection is correct, but this did not test a rollout-aware
   recurrent model trained for the planning use case.
9. **Calibration was too thin for a safety tube.**  Eight trajectories became
   128 correlated horizon rows for the 90% multiplier.  A successor needs
   family/block-wise, time-uniform and context-wise calibration rather than a
   row aggregate alone.

The model scores reinforce the diagnosis.  Development selection favored the
simple ARX at about `1.111`, versus `1.171` for GRU, `1.147` for LSTM and
`1.120` for TCN.  Every class's largest calibrated R/Z interval occurred at
horizon 13.  For impulse paths this is the state after the step-9 full pulse
and the step-10--12 q0 commands, immediately **before** the new step-13 full
issue; that issue first affects horizon 14.  The location is consistent with
a delayed-tail/recursive-history support problem, but it is not a completed
causal attribution.  It gives no basis for merely enlarging a recurrent
network.

The frozen 4 mm cap remains failed and must not be relaxed post-result.  A new
stage may define different prospective accuracy/tube gates only after they
are derived from its controller horizon, constraint tightening and finite
work domain.

## 7. Revised model concept

The user's R1/C1 versus R2/C1 intuition should not be implemented as an
independent model at every coordinate.  A more defensible local description
is:

```text
observable context xi_k =
  (R_geo, Z_geo, Ip, 14 actual currents, time, R_geo-R_mid, queue/action age)

belief b_k = causal posterior over passive/history state

Delta y_{k+1} = drift(xi_k, b_k)
                + response(xi_k, b_k, signed/amplitude action)
                + bounded residual
```

The local gain is therefore a smoothly scheduled object `B(xi_k,b_k)`, not a
single constant Jacobian and not a table keyed only by R.  Magnitude, lag,
cross-coupling and signed nonlinear response/non-oddness may vary with
position, Ip, current baseline and passive state.  Literal differential-gain
sign reversal remains to be measured.

The recommended backbone is now explicit:

1. exact Card15/readback and queue/effect propagation;
2. a separately identified common-drift component;
3. a stability-constrained low-order state-space observer for velocity,
   passive-current and innovation memory;
4. continuous LPV/local-expert scheduling over supported R/Z/Ip/current and
   belief context;
5. a small GRU/TCN or other nonlinear residual only if it gives prospective
   whole-family benefit;
6. calibrated ensemble/set-valued uncertainty that expands outside support.

HFS/LFS remains a deterministic label, never a hidden controller mode.  A
single belief continues through `R_mid`; local heads may mix smoothly across
the corridor only after both sides have support.

The 14-coil interface remains exact, but online estimation should not attempt
an unconstrained `3 x 14` Jacobian from each new three-output transition.  An
offline contextual prior should identify a small, control-relevant local
input subspace or structured gain family.  Online updates may adjust only its
low-dimensional coefficients.  This does not resurrect any old fixed global
basis; the subspace must be qualified across anchors and may be scheduled.

## 8. Safe meaning of probe-learn-probe

The proposal should be adopted in a guarded, multi-timescale form rather than
as online deep-RL or per-millisecond neural backpropagation.

### 8.1 Fast loop

At every 1 ms step:

- parse one valid paired boundary and Ip;
- update the causal belief and exact action/queue state;
- solve or refresh a constrained plan if computation permits;
- pass only an actually representable Card15 action through the independent
  current/slew/Ip/boundary/recovery interface;
- execute the first 1 ms action and retain complete causal evidence.

The 1 ms actuator period does not force a 16 ms planning horizon.  Observer
memory and planner horizon must be chosen from measured response tails and
the reference governor's negotiated time scale.

### 8.2 Within-run adaptation

The initial online adapter keeps all deep/global weights frozen.  Only a
small projected parameter vector may update, such as local gain correction,
bias, a few time constants, mixture weight or latent context.  RLS, Kalman/
MHE, Bayesian or set-membership updates are candidates, not preselected
winners.

An update is accepted only after the relevant physical effect window has
completed and excitation, innovation, support and conditioning gates pass.
The first identification version uses non-overlapping probe/observe windows.
A later controller may act continuously only if its state-space estimator
explicitly attributes the complete overlapping input sequence; it may not
verbally "wait for an effect" while assigning a mixed response to one action.
Insufficient excitation freezes the parameter.  OOD or abnormal innovation
must expand uncertainty or stop adaptation.  Uncertainty may not shrink below
a calibrated floor, and crossing the `R_mid` corridor does not reset belief;
early versions should freeze parameter learning there.

The adapter first runs in **shadow mode**: it predicts but cannot change an
action.  It enters the controller only if a fresh whole-history comparison
shows preregistered benefit over the frozen prior, no unacceptable per-context
regression and preserved uncertainty coverage.

### 8.3 Active probing

The first controller should learn only from actions already needed for
tracking.  It may later choose the more informative member among nearly
equivalent safe control allocations.  Dedicated main-path micro-probes are a
still later feature and require all of:

- a prospectively bounded amplitude, energy, duration and time penalty;
- Card15, `0.3 A` step, absolute-current, Ip and boundary compliance;
- a previously qualified finite-envelope recoverable tube and backup
  continuation after every step;
- adequate distance from OOD, hard constraints and the crossing corridor;
- an effect window that prevents assigning a delayed response to the wrong
  action;
- measured uncertainty/control benefit versus a no-probe comparator.

Using less than `0.3 A` for an information probe is a voluntary action choice,
not a hidden reduction of the hard limit.  A qualified controller remains
free to use the full `0.3 A` only when the pre-action hard filter and
pre-action recoverability proof support it.

The initial probe state machine is explicit:

```text
TRACK/HOLD
  -> pre-authorized PROBE primitive
  -> OBSERVE through its non-overlapping complete effect window
  -> shadow UPDATE proposal
  -> accept/reject posterior and tube
  -> replan
```

The current probe and its backup must be safe under the **pre-probe**
uncertainty set while assuming zero information gain.  Any accepted posterior
shrink can affect only a later planning cycle.

Random dense 14-dimensional exploration, online deep-weight updates and
reward-only safety are excluded.

### 8.4 TSC branch probing

Richer candidate scans should preferentially occur in cloned TSC branches,
because the target plant is TSC and wall-clock time is negotiable.  NR1,
however, qualified only a few fixed-source prefixes.  Before calling this an
Oracle, a small prospective gate must show, within a frozen finite
prefix/time/action/history envelope, that the current prefix can be restored
by snapshot or exact replay, that the branch point and a frozen future
continuation match in boundary geometry, Ip, coil/passive currents and action
state, and that cost is usable.  Full TSC snapshot/state identity is preferred;
finite visible equality plus one continuation establishes only finite
behavioral equivalence, not equality of every hidden state.

If this gate passes, branch probing can help choose safe anchor prefixes,
screen candidate actions and benchmark/teach the surrogate without exposing
the main path.  It remains subject to the independent hard filter and cannot
prove its own prefix or recovery safety.  If it is inexact or prohibitively
slow, the structured model route remains primary.  Oracle records require a
declared use before generation and sibling branches stay in one split.

## 9. Revised development order

The next stage is not NR3.  A successor design should enforce this order:

1. **NR2R2A zero-new-TSC design audit.**  Use only NR2R1 development/
   calibration to bound what is and is not identifiable, freeze deployable
   fields, a finite first HFS domain, candidate windows for **prospective tail
   measurement** and exact stop routes.  The present 16 ms data supplies only
   a memory lower bound and cannot prove a truncation adequate.  Do not fit a
   successor or use the consumed holdout.
2. **Source baseline, repeatability and recovery gate.**  Under a separately
   authorized identity, collect independent q0-command baselines long enough
   to separate source-to-q0 settling, drift and response tail within hard stop
   bounds.  Repeated same-prefix runs must establish a non-vacuous uncertainty
   floor.  Establish an active hold/backup/recovery continuation; returning
   coil current to q0 is not by itself a plasma hold.
3. **Finite moving-prefix replay and cost gate.**  Qualify or reject replay
   only over its frozen prefix/time/action/history envelope, using known-safe
   prefixes and interface-validation records forbidden from fitting.  This
   gate may be developed in parallel with the source gate, but cannot replace
   it or make an unsafe prefix safe.
4. **Minimal tail/response-geometry sentinel.**  Before a broad atlas, repeat
   a small set of matched-baseline structured actions to establish response
   SNR, Card15 resolution, output signal/rank/condition, lag support and the
   observation window.  Failure stops before multi-anchor expansion.
5. **Context/history atlas identification.**  Reach a small set of overlapping
   HFS anchors from the fixed 1100 ms source using audited safe prefixes.  At
   each anchor repeat the same signed/sparse or structured primitives, an
   independent baseline, different action ages/dwells and protected
   cumulative staircases.  Each staircase level is a new prefix/operating
   point, not one unchanged anchor.  Every anchor must first pass exact-prefix
   repeatability, settling/action-age definition and its own hold/backup/
   recovery gate before a probe.  Baseline and probe share the exact prefix.
   Design matched-time/different-position and matched-position/different-time/
   history contrasts so that position, absolute time and arrival history are
   not intentionally collinear.  Split complete anchor/prefix/history
   families, not steps or sibling branches.
6. **Structured model and uncertainty qualification.**  Compare the explicit
   state-space/LPV prior, simple baselines and optional small residuals on
   blind anchor/history families.  Require response signal, lag support,
   rank/conditioning, free rollout, pulse-edge behavior and family-wise
   calibrated tubes.  The online parameter dimension, regressor, minimum
   singular value, condition and persistent-excitation gates are frozen here.
7. **Static no-active-probe governor/NMPC.**  First qualify source hold, small
   same-side endpoints and slow two-dimensional paths with the frozen static
   model and independent recovery layer.  Compare against a qualified finite-
   envelope branch Oracle if available.
8. **Controller-distribution shadow adaptation.**  Run the frozen adapter
   beside, but not inside, that controller on fresh whole-controller-history
   families.  Prove material benefit, bounded parameters, no unacceptable
   context regression and preserved tubes.  A PASS authorizes only a separate
   adapter-in-loop safety sentinel, not immediate action influence.
9. **Domain expansion.**  Only after an adapter-in-loop gate may the route add
   deliberate information actions,
   `R_mid` crossing, return crossing and multiple waypoints.  Outer RL,
   recurrent student and ILC remain optional later competitors.

NR2R2A is only a local, zero-new-TSC, no-fit design/audit candidate.  A PASS
may authorize only the prospective design of separately identified source/
replay/sentinel campaigns; it does not authorize their execution.  Every
matrix, budget and numerical gate must be frozen before implementation or
TSC.  Replay qualification and identification use separate evidence
identities even if planned together.

## 10. Mandatory pause conditions

Stop for another architecture review rather than add probes or model capacity
if any of these occurs:

1. no safe active hold/recovery continuation exists at the 1100 ms source;
2. finite-envelope moving-prefix replay is not causal/exact and the surrogate cannot obtain
   adequate independent history coverage;
3. repeated same-context/same-action responses cannot be covered by a useful
   causal belief tube;
4. contextual output authority is absent or too ill-conditioned in the
   declared finite domain;
5. fresh whole-anchor/history intervals systematically under-cover or become
   too wide for constraint tightening;
6. shadow adaptation gives no material benefit or causes context regressions;
7. the planner cannot keep a recovery continuation while making finite
   progress under a negotiable time scale.

These outcomes must remain separated as interface, replay, identifiability,
observer/model, adaptation, planner or genuine closed-loop failures.  None may
be relabelled as global plant unreachability without corresponding evidence.

## 11. Current authorization boundary

This reassessment records a route correction only.  It authorizes no code,
server access or raw read, deployment, snapshot/branch replay, TSC, training,
Oracle experiment, model fit, MPC, RL or data generation.  The only next
candidate is a separately authorized local documentation/read-only compact-
evidence NR2R2A audit.  NR2R1 remains final as
`ONE_MS_NR2R1_CALIBRATION_FAIL_NO_HOLDOUT`; NR3 remains blocked.
