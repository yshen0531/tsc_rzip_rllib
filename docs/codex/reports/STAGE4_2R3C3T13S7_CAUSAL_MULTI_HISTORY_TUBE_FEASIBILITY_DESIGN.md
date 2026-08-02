# Stage4.2R3c3T13S7 causal multi-history tube feasibility design

## Status and purpose

This design is frozen after the final independently certified T13S6 result
and before any T13S7 response, feature-distance, model, tube, collision, or
validation output is computed. T13S7 is read-only and runs zero controller,
Ray, `gotsc`, TSC, plant step, or snapshot creation.

T13S6 proves that an immediate-effect map fitted in one q2 history does not
transfer as a point predictor to the other q2 history. T13S7 tests a narrower
question before authorizing more plant identification: can the already
observed q1/q2 response variation be covered by a causal, visible-state
conditioned set of local transition hypotheses without using history labels
or hidden currents?

No T13S1 or T13S5 raw remains blind. T13S7 is a retrospective feasibility
gate only. Even a complete pass requires a new prospective q3 history
holdout before a controller.

## Immutable evidence

```text
T13S1 run
  stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_ecc05f6
raw files / bytes                                  52 / 2,463,366
raw digest
  de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603
official server audit SHA-256
  5695dd9ff5fbcc901182d7f3b3c86cedf9d3375ec12dbebf63152e2d03ba8951

T13S5 run
  stage4_2r3c3t13s5_real_20260802_d048686
raw files / bytes                                  68 / 3,610,097
raw digest
  09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
official independent audit SHA-256
  dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033

combined contexts                                            8
combined baselines                                           8
combined signed probes                                     112
combined raw                                                120
```

T13S1 contains q1 plus/minus histories with three physical-mode directions.
T13S5 contains q2 plus/minus histories with four lattice-native directions.
Both use the same two physical windows and the same R3c1 underlying
controller. The official S1/S5 results and gates remain unchanged.

## Corrected raw transition contract

For both campaigns, the probe wrapper changes the already post-queue Card15
action. T13S7 therefore uses:

```text
first measured current/effect state       issue_step + 1
cancel measured current/effect state      cancel_step + 1
input                                     two states x 14 measured coil-current displacement
output                                    two states x (R, Z, causal vR, causal vZ, Ip) displacement
baseline                                  same-context unprobed trajectory
```

Velocity is the causal backward difference. At restart step zero it is
unknown, represented by zeros plus an explicit `velocity_known = 0`; no
future state may initialize it.

## Allowed causal selector feature

At each issue step, construct a numeric feature from the same-context
unprobed trajectory using only information a restarted online controller
could possess at that time:

```text
current R, Z, Ip
causal backward vR, vZ and velocity-known flag
current 14 measured coil currents
previous-to-current 14 coil-current difference and history-known flag
target R/Z/Ip offsets
formal issue time divided by the unchanged formal horizon
finite actuator delay divided by 2
(slew - 1.0) divided by 0.1
```

Fixed feature scales are the formal tolerances for R/Z/v/Ip, each coil's
declared current half-range from the authenticated payload for coil current
and current difference, the formal target tolerances, and unit scale for the
flags/time/normalized actuator fields. The Euclidean distance is divided by
the square root of the feature dimension.

Pair, q1/q2, history-member, prefix, source experiment ID, source action or
result, wire/vessel current, current-run future state, future action, future
measurement, and future probe schedule are forbidden from the feature,
distance, hypothesis fit, support test, or prediction. Labels may be used
only after prediction to audit the leave-one-context-out split.

## Model and leave-one-context-out contract

Evaluate `easy/hard x transport/braking` separately. Each stratum has four
consumed contexts: q1 plus/minus and q2 plus/minus. Perform four folds per
stratum; hold out one complete context and use the other three only.

For every training context/window:

1. fit a minimum-norm local map from odd measured two-state current input to
   odd two-state plant output;
2. retain its exact input row space and signed-fit residual tube;
3. use the unchanged numerical floors, `1.5` residual multiplier, and T13S6
   component caps;
4. mark q1 maps rank three and q2 maps rank four without pretending the q1
   maps span the lattice split direction.

For each held-out signed probe:

1. choose the two nearest training contexts by the allowed causal feature,
   including all exact-distance ties;
2. discard a candidate map only when the held-out measured input has relative
   row-space projection residual greater than `0.15`;
3. require at least one supported hypothesis;
4. predict with every supported hypothesis and its own frozen residual tube;
5. pass only if at least one hypothesis contains every component and the
   nearest hypothesis has scaled center-relative error `<= 0.10`.

Selection occurs before inspecting the held-out response. Tube radii,
feature scales, neighbor count, support threshold, and response threshold may
not be tuned per fold or after validation.

## Collision and non-vacuity gates

Report exact duplicate allowed features. An exact feature/input collision
whose response tubes are disjoint is an observed causal alias and forces
FAIL. Absence of an exact collision is only finite clean separability, not
hidden-state observability.

Every candidate tube must remain within the unchanged per-two-state caps:

```text
R/Z                         3 mm
vR/vZ                       0.01 m/s
Ip                          1000 A
```

The audit must authenticate:

```text
S1 raw identity and official audit                    52 / 52
S5 raw identity and official audit                    68 / 68
corrected trace/effect extraction                    112 / 112
forbidden feature/model inputs                               0
leave-one-context-out folds                                   8
held-out signed predictions                                 112
supported-hypothesis coverage                       112 / 112
componentwise multi-hypothesis containment           112 / 112
nearest scaled relative error <= 0.10                112 / 112
non-vacuous candidate tubes                           all / all
disjoint exact causal aliases                                0
```

Formal tracking remains diagnostic. The 250/270 ms arrival deadlines and
350/370 ms hold endpoints do not change.

## Outcome routes

```text
FINITE_CAUSAL_MULTI_HYPOTHESIS_CANDIDATE_Q3_HOLDOUT_REQUIRED
  every frozen gate passes;
  authorize only a prospectively split, independent q3 history holdout.

CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN
  any gate fails;
  redesign the observer/state/history excitation or transition set before
  any new physical campaign.
```

Neither route authorizes a controller, real MPC, expert data, BC, DAgger, or
bounded residual RL. All S1/S5 probe trajectories remain forbidden from
expert datasets.
