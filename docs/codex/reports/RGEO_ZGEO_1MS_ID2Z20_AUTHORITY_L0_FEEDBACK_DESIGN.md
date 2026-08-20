# ID2Z20 Authority-L0 feedback design

## Identity and purpose

ID2Z20 is one bounded simulator-development Authority-L0 and capture-
feasibility campaign. It fits zero models. It first measures an exact signed
rank-four Card15 pulse/return library at two causal phases, then applies a
prospectively frozen deterministic selector in two low-dimensional feedback
candidates that read the exact current R_geo/Z_geo/Ip before each decision.

The stage may establish finite sustained Authority-L0 and may nominate a
repeated six-state nominal capture seed. It cannot establish Recourse-L1, a
transition tube, controller safety, waypoint/path tracking or R_mid crossing.
The finite-return trajectory is a simulator observation, not recovery.

## Frozen roots and horizon

All paths use the authentic 1100 ms source and a 1 ms issue/effect contract.
The common terminal state is 65.

- development root: the authenticated ID2Z18 `baseline_full_f` prefix through
  issue 31 / state 32;
- validation root: the authenticated, distinct ID2Z18 `d04_plus` prefix
  through issue 31 / state 32;
- root center: the active Card15 target after issue 31;
- terminal window: states 60--65 inclusive.

The validation prefix was previously development evidence, but the selected
feedback actions and their responses at that prefix are new. It is therefore
a finite different-history validation, not an unseen-history blind holdout.
Future ID2Z18 c00--c03/v00--v03 records remain unopened.

## Exact rank-four coordinate

The executed ID2Z18 signed action alphabet has numerical rank four. ID2Z20
uses four fixed, full-scale, exactly representable Card15 field-increment
coordinates:

```text
b0 = F
b1 = A
b2 = 2 E
b3 = 3 (A + a)
```

`b3` isolates the measured p06 non-odd closure direction. Each coordinate has
maximum single-coil current increment exactly 0.3 A; both signs are executed.
The four-row current-space matrix must have numerical rank four, condition at
most 5.0 and exact Card15 reconstruction. No odd symmetry is assumed.

Every pulse target is `center +/- bj`; the next issue returns exactly to the
center and all remaining issues hold that center. Static preflight must prove
every pulse and return against both roots before any TSC call. No clipping or
software queue is allowed.

## Sequential population and budget

Phase A contains seventeen development paths:

```text
dev_hold
phase32_b0_plus/minus ... phase32_b3_plus/minus
phase40_b0_plus/minus ... phase40_b3_plus/minus
```

The phase-32 pulse is issued at 32 and returned at 33. The phase-40 pulse is
issued at 40 and returned at 41. Every path then holds through issue 64.

Only if Phase A execution, raw, signal and geometry gates pass may Phase B
run two development feedback candidates:

- `policy_h4`: decisions at issues 32, 36, 40 and 44; each decision executes
  one selected pulse, exact return, then two holds;
- `policy_h8`: decisions at issues 32 and 40; each executes one selected
  pulse, exact return, then six holds.

Only if one Phase-B candidate passes the preliminary utility gate may Phase C
run four zero-fit paths:

1. selected full-F-root fresh replay;
2. validation-root matched hold;
3. validation-root selected feedback policy;
4. validation-root finite-return tail, which follows the selected policy only
   until its first non-hold pulse, returns to center on the next issue and
   holds through issue 64.

The hard maximum is 23 resets, 1,495 advance attempts/calls/verified advances,
1,518 retained states and 7,590 required artifacts if all paths complete.
There is no retry after any advance attempt.

## Deterministic feedback selector

The selector is frozen before Phase A outcomes. For each phase and signed
coordinate, it forms paired response tables against `dev_hold` at horizons 4
and 8:

- R/Z/Ip displacement;
- terminal one-millisecond R/Z velocity response;
- matched-hold drift and velocity change.

At each feedback decision, the selector reads only the current exact same-step
R_geo/Z_geo/Ip, the previous exact state needed for 1 ms velocity, the current
active Card15 target, causal action history and the frozen response table. For
each of hold and the eight signed pulses it predicts the selected horizon's
source distance, terminal speed and Ip fraction by adding the matched finite
response to the current truth. It minimizes

```text
max(distance / 25 mm, speed / 0.1 m/s, |Ip-Ip_source| / (5% |Ip_source|))
```

subject to exact target/current/clearance gates. Ties use lower current
excursion and then the frozen arm order. Future TSC state, recorded future
current, family labels and matched future truth are forbidden.

This is a fixed finite response-table feedback rule, not a learned model and
not a qualified runtime predictor.

## Data roles

All complete Phase-A and Phase-B causal windows are prospectively eligible
for a later, separately identified event/candidate-value development stage.
The selected replay, validation hold, validation policy and finite-return tail
have fit weight zero. Incomplete or safe-stopped future windows are censored,
not labels. No calibration, blind holdout, model, expert, imitation-learning
or RL data are opened in ID2Z20.

## Hard execution gates

Before every issue and after every successor, fail closed on:

- authentic source and exact frozen prefix;
- paired-boundary R_geo/Z_geo and same-step Ip;
- issue k to state k+1 timing and complete causal history;
- exact Card15 serialization, applied/readback current and no clipping;
- per-coil issue and observed slew at most 0.3 A;
- absolute current, limiter, finite values and Ip envelope;
- 45 mm / 9% simulator-development preissue shell;
- 50 mm / 10% hard outer envelope;
- empirical one-successor caps 2 mm R, 2 mm Z and 150 A Ip;
- complete raw inventory and independent recomputation.

The empirical caps and post-successor stop are simulator exploration guards,
not pre-action controller-grade bounds. Any execution/interface/raw/prefix
failure is not an Authority-L0 scientific result.

## Scientific gates

Phase-A signal and geometry pass requires:

- every signed arm peak R/Z response at least 0.05 mm;
- every signed arm has a three-consecutive-state median R/Z response at least
  0.02 mm;
- in each phase, at least two consecutive common response states have maximum
  angular gap at most 180 degrees and a 64-direction weakest-best projection
  at least 0.02 mm;
- paired Ip response at most 400 A.

For each root, the feedback utility gate compares terminal states 60--65 with
its matched hold. It requires:

- worst normalized capture score improvement at least 15%;
- worst terminal speed improvement at least 0.05 m/s;
- worst source distance no more than 0.5 mm above matched hold;
- every one of the six per-state normalized capture scores no worse than its
  matched-hold counterpart;
- all hard gates and at least one non-hold feedback decision.

The selected full-F policy, its fresh replay and the different-history policy
must all pass their applicable execution, replay and utility gates. The
finite-return tail must be hard-safe, return the active Card15 command exactly
to its root center, and finish within 2 mm R, 2 mm Z and 350 A Ip of the
validation hold terminal state.

A nominal capture seed additionally requires the selected full-F policy and
fresh replay each to satisfy all six terminal states at distance <= 25 mm,
speed <= 0.1 m/s and Ip deviation <= 5%.

## Routes and stopping

- input, storage or static-action failure: zero TSC;
- any runtime/interface/prefix/raw failure: stop, preserve raw, no scientific
  Authority-L0 claim;
- complete Phase-A signal/geometry failure: stop before feedback policies and
  close this coordinate/phase grammar;
- complete Phase-B no-utility result: stop before replay/validation and close
  this feedback selector;
- replay, different-history utility or finite-return failure: Authority-L0
  FAIL; do not add a nearby arm, gain, phase or third model;
- Authority-L0 PASS without capture: authorize only a new prospectively
  frozen event/candidate-value development identity;
- capture-seed PASS: additionally authorize a separate Recourse-L1 design;
- neither outcome authorizes a controller.

## Wall-clock and final goal

One millisecond is the simulated plant issue period. Canonical-source replay
is allowed as a wall-clock-slow development teacher/planner, not an arbitrary-
state snapshot Oracle. The final goal remains safe approximate two-axis
waypoint/path tracking from fixed 1100 ms takeover, followed by multiple
positions/histories and repeated bidirectional R_mid crossing with continuous
belief.
