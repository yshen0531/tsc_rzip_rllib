# R_geo/Z_geo 1 ms post-NR2R2B0 deep route review

Status: documentation-only architecture decision on 2026-08-13
Asia/Shanghai.

Decision route:

```text
POST_NR2R2B0_DEEP_REVIEW_COMPLETE_SOURCE_SHOOTING_SNAPSHOT_AND_RECOURSE_DISCRIMINATORS_REQUIRED
```

This review was requested as a pause for deep analysis. It changes no code,
signal, actuator, queue, controller, reward, termination, Card15 or TSC state
semantics. It ran no server command, TSC, plant advance, snapshot/replay,
model fit, training, optimization or data generation.

## 1. Evidence and authorization boundary

The review uses the repository source and tracked compact evidence through
checkpoint `5de0a4d`, including NR0/NR1R2, NR2R1, NR2R2A and NR2R2B0. Large
B0 raw remains server-side and was not read. The invalidly opened NR2R1
holdout was not used to choose a route, feature, threshold, action or model.

The new NR1R2 hash cross-check was a zero-server, zero-TSC, read-only
recomputation from these six tracked records under
`docs/codex/audits/rgeo_zgeo_1ms_nr1r2_result_20260813_8580ac1/`:

```text
hold_primary.json       hold_replay.json
pattern_a_primary.json  pattern_a_replay.json
pattern_b_primary.json  pattern_b_replay.json
```

For each primary/replay pair it compared, state by state, the five
`artifact_sha256` entries, the recorded actions and the paired-boundary,
Ip, 14-coil and 48-wire fields. No server raw or holdout entered this
descriptive check.

The unchanged physical contract is:

```text
takeover time                                  1100 ms
control period                                    1 ms
per-coil single-turn current step             <= 0.3 A
equality at +/-0.3 A                             allowed
R_geo                  (boundary_R_min + boundary_R_max) / 2
Z_geo                  (boundary_Z_min + boundary_Z_max) / 2
boundary source                  same valid boundary and same time
missing/invalid boundary                    fail closed; no fallback
R_mid             (inner_limiter_midplane + outer_limiter_midplane) / 2
side                       HFS iff R_geo < R_mid; otherwise LFS
R_mid crossing                     belief/history never resets
Ip                       coupled observation plus soft/hard constraint
```

The review authorizes no implementation, server raw read, deployment, new
TSC, branch experiment, model, controller, MPC, RL or data generation. It
records the successor order that a separately prospective stage may follow.

## 2. Bottom-line judgment

The high-level architecture remains the right one:

> exact actuator and causal belief, followed by uncertainty-aware constrained
> rolling control and an independent hard safety/recovery interface.

It should not be replaced by a larger recurrent network or immediate online
RL. The immediate route must, however, be changed again after B0. The next
problem is not model capacity. It is to establish:

1. whether complete replay from the canonical 1100 ms source is a finite,
   deterministic and affordable shooting tool;
2. whether an active nominal source hold is available;
3. whether that nominal path can be surrounded by a bounded contingency tube;
   and, independently,
4. what fresh-snapshot restart equivalence means when `sprsina` bytes differ.

The snapshot question need not block canonical-source shooting. Only the
source replay -> nominal hold -> finite recourse chain may unlock the first
response/position/history stage that NR2R1 lacked.

## 3. Which earlier choices were correct

The following decisions remain valid and should not be rolled back:

1. NR0's paired same-boundary `R_geo/Z_geo` definition and fail-closed
   behavior;
2. the fixed 1100 ms takeover and the 1 ms, per-coil `<=0.3 A` hard slew;
3. one belief identity through repeated HFS/LFS crossings;
4. NR1R2's separation of command and readback coordinates, exact Card15
   action and direct issue-to-successor effect timing;
5. exact actuator/queue propagation outside any learned residual;
6. whole-history evidence separation and the refusal to tune on the consumed
   NR2R1 holdout; and
7. B0's decision to measure q0 rather than assume it was equilibrium or
   recovery.

Fixed 1100 ms was not the mistake. It is the user's required source. The
mistake was to treat one restart point and its short common continuation as a
qualified operating domain.

## 4. The earliest substantive mistake

The earliest substantive route error was the NR2 ordering:

```text
ARX/GRU/LSTM/TCN model comparison
before
q0/passive baseline + response-tail/lag support + position/history factorization
```

NR2R2A has now made the shortfall explicit. The 28 usable development/
calibration trajectories contain one physical start, one HFS path, no
independent all-q0 baseline, no cumulative command-center migration and no
matched position/history contrasts. Their lag-8 input blocks are rank
deficient. This rejects the old campaign as support for an arbitrary
eight-lag model; it does not prove a seven-millisecond plant memory, reject
all structured low-order models or select a recurrent architecture.

The better original order would have been:

```text
NR0 exact signal contract
  -> NR1 exact actuator/effect contract
  -> source q0/passive-evolution baseline
  -> finite canonical-source replay qualification
  -> nominal active-hold and finite-recourse discriminators
  -> minimal response-tail and lag/context identifiability
  -> minimal multi-position/multi-history response geometry
  -> model comparison
```

### 4.1 Judgment on position dependence and online learning

The user's intuition is plausible and important, but the current 1 ms
evidence does not yet isolate a pure position-dependent coil gain. Position,
absolute time, passive evolution and action history moved together along one
short HFS path. Prior finite evidence does falsify a universally odd,
context-independent response rule in its tested contexts, and NR2R1 shows
large successor spread associated with different causal prefixes even when
the current q0 coil readback and zero increment match. Neither result proves
that a specific coil's local differential gain reverses between two
positions, or that hidden state is intrinsically unobservable.

The right response is not to assume a global fixed map, and not to train a
deep network online from scratch. The atlas must deliberately separate
position, time and arrival history. The eventual controller should update its
belief every 1 ms; only prospectively fixed low-dimensional bias/gain/time-
constant or mixture weights may adapt, initially in shadow mode and only
under excitation, innovation, projection and uncertainty-floor gates. Global
GRU/LSTM/TCN weights remain frozen within a run. This is constrained adaptive
MPC/observer behavior, not online RL.

## 5. What B0 proves, and what it does not

B0 completed six independently reset q0-command trajectories, 192 authentic
advances and 198 recorded states inside its outer boundary/Ip/current/slew
envelope. The checked physical observables, serialized input and non-`sprsina`
artifact comparisons were exact across resets:

```text
paired R_geo/Z_geo/R_mid                         exact
Ip                                                exact
14 coil-current readbacks                         exact
48 wire-current diagnostics                       exact
serialized Card15 fields                          exact
inputa/geqdsk/coil/wire artifact hashes            exact
```

This wording is intentionally limited to the fields that were compared;
`outputa` was not part of the frozen five-artifact comparison.

The q0 short-hold failure is genuine within the 32 ms source envelope:

```text
maximum |R_geo-R0|                         17.601295 mm
maximum |Z_geo-Z0|                         23.441925 mm
maximum |Ip-Ip0|                            335.723 A
terminal maximum one-step R/Z drift   0.617677/0.805788 mm
terminal-window R/Z net drift         3.943637/5.822385 mm
```

Thus q0 is not a qualified standalone source hold, backup or recovery
continuation. It is only a finite q0-command baseline and a safe observed
continuation inside the tested outer envelope. B0 did not perturb the plasma,
so it did not run a
perturbation-recovery test. It also does not prove that active feedback,
time-varying feedforward or branch-searched hold is impossible; nor does it
prove global instability, insufficient PF authority or unreachability.

The first q0 target differs from the source command by at most exactly
`1e-5 A` single-turn current. It is therefore not a literal zero command
delta, but B0 cannot attribute the much larger observed evolution to that
tiny difference. The evolving scenario is an observation; the possibility
that a time-varying nominal feedforward is needed is an inference for C2a to
test. A successor should not subtract a post hoc "natural drift" from old
probe data.

## 6. B0's artifact gate was conservative but semantically overcombined

B0's frozen exact-all-artifact route remains FAIL and may not be relabelled.
Its `sprsina` hash differed from the reference reset at every successor state
1--32. `sprsina` is a real load input to the next TSC step, so the difference
cannot be silently declared metadata or canonicalized away.

However, whole-file byte identity and physical/behavioral state identity are
not the same proposition. A new read-only cross-check of the tracked NR1R2
compact records found the same pattern in all three primary/replay pairs:

```text
pair                       state 0             states 1..4
hold primary/replay        all hashes equal    only sprsina differs
pattern A primary/replay   all hashes equal    only sprsina differs
pattern B primary/replay   all hashes equal    only sprsina differs
```

NR1R2 simultaneously found zero parsed difference in paired boundary
geometry, Ip, 14 coil currents and 48 wire currents along those frozen native
continuations. An analogous observation separately holds along B0's q0
native continuation to 32 ms. This is finite native-continuation checked-
output evidence, not fresh-restart behavior or hidden-state equality.

The correct successor therefore splits the old compound gate into three
independent questions:

1. **Representation:** where do the bytes differ, and do documented
   records/fields identify metadata versus state payload?
2. **Restart behavior:** can independently generated `sprsina` files with
   matching checked observables be freshly restarted and reproduce several
   prospectively frozen common suffixes?
3. **Branch utility:** can a snapshot or exact replay of a growing prefix
   generate finite, repeatable branch predictions at acceptable cost?

Without an authoritative decoder, a byte-localization audit may classify the
difference only as localized or pervasive/unknown. It may not infer semantic
benignity. A common-suffix match can qualify only finite behavioral
equivalence over its tested prefix/time/action/history envelope, never an
arbitrary hidden-state Oracle.

The retired 10 ms R1c route is a useful but limited prior: authentic
filesystem `sprsina` restart and the frozen same-action suffix reproduced
visible state, action, all 14 coils and all 48 wire currents in 18/18 finite
R17 cases. This proves that the snapshot mechanism has worked in that old
same-source envelope. It does not establish semantic equality for the current
1 ms B0 successor files, a new-action branch or an arbitrary restart Oracle.

## 7. Current architecture dilemma

There is a real bootstrap problem:

- an atlas probe should have a qualified backup/recovery;
- designing active recovery needs controlled-response evidence; and
- q0 is not that recovery.

Requiring a fully deployable recovery controller before every simulator
identification action would create a circular deadlock. Treating the B0
unperturbed q0 continuation as action-conditional containment, return or
fallback would be equally wrong.

The route should separate these report-local safety levels without reusing
the repository's frozen Stage4.2R1/R2 names:

```text
Safe-L0       pre-issue refusal / structured stop; no new action is applied
Nominal-H1    finite active-hold/feedforward candidate from one source path
Recourse-L1   finite-horizon contingency from a frozen state/current/belief
              tube, satisfying every hard constraint and reaching a smaller
              qualified terminal hold/recoverable set within H steps
Recourse-L2   recursively feasible hold/recovery set for continued replanning
```

Safe-L0 does not undo an already issued action or its delayed effect. A
Recourse-L1 claim therefore needs a feedback/contingency tree or an equivalent
policy over its declared tube; one nominal serialized sequence is only a
finite nominal continuation. If no smaller qualified terminal set is reached,
call the result finite safe continuation rather than recovery.

A very small TSC-only discriminator may start before Recourse-L1 only if each
issued primitive already has an independent one-step successor bound inside a
prospectively frozen outer envelope. Stop-before-advance and immediate
termination protect later steps but do not make the current successor safe.
This is finite simulator experimentation, not a deployable backup. Position
transport and atlas probing require at least Recourse-L1 at the source
and then at each admitted anchor. A controller whose operating time exceeds
its Recourse-L1 horizon requires Recourse-L2. A reference governor is an
alternative only if it proves the same recursive property: every possible
successor retains a full H-step contingency, transitions between recovery
tubes are covered, and a qualified fallback can be selected atomically after
solver timeout.

The first active-recovery candidate cannot use its own expected learning or
posterior shrink to establish safety. Candidate safety is evaluated with the
pre-action uncertainty set and assumes zero information gain.

## 8. Another implementation gap that must precede a real controller

NR0 introduced the correct boundary contract as a separate pure interface,
but the legacy core runner still defaults to:

```text
state_rz_source = "magaxis"
```

and `read_state()` assigns `xmag/zmag` (or legacy `rc/zc`) to its generic
`R/Z` fields. NR1/NR2/B0 evidence scripts recomputed paired-boundary
`R_geo/Z_geo`, so those records do not violate the new signal definition.
Nevertheless, NR0 has not yet been proven end-to-end at the future controller
observation port.

Before any online planner/controller, adapter or safety claim can be called an
`R_geo/Z_geo` action,
an integration gate must prove that the actual environment observation,
reference governor, observer, constraint checker and logger all consume the
paired-boundary signal and fail closed, including atomic action refusal on an
invalid boundary. No legacy `magaxis`, `rc/zc` or split-axis fallback may
remain on that path. Likewise, the 48-wire vector stays a behavioral
diagnostic and cannot enter a safety tube or controller state until deployment
availability is proved.

There is an equally important action-side blocker. `runner.step_current_a()`
silently clips requested absolute currents, and `step_delta_current_a()`
silently clips increments. NR1/NR2/B0 remained safe because their outer
scripts prevalidated commands and audited serialized/applied/readback values;
that does not make the generic runner a fail-closed controller boundary. The
future path must reject an out-of-contract request before any plant advance
and prove requested, serialized, applied and readback identities. Silent
clipping may not change controller intent behind the hard interface.

## 9. Revised successor order

The development order is now frozen as a recommendation, not execution
authorization.

The dependency graph is intentionally not a serial C0 -> C1 -> C2 chain:

```text
C1a canonical-source full-prefix replay/shooting -> C2a nominal hold
                                                 -> C2b finite recourse

C0 sprsina representation/semantics ---------\
                                              > finite snapshot envelope
C1b common-suffix restart behavior ----------/    / fast moving-prefix tool

C2b Recourse-L1 ----------------------------------> D response/tail stage
```

C0, C1b and C1a/C2a may be designed as separate prospective identities. C0
does not have to PASS before C1b is designed or run; their independent claims
converge only when bounding a snapshot envelope. No arrow in this
recommendation is execution authorization.

### 9.1 NR2R2C1a: canonical-source full-prefix replay/shooting

Qualify a finite source-origin tool by resetting every candidate to the same
canonical 1100 ms directory, replaying the complete prospectively declared
causal prefix, and only then appending a candidate suffix. This avoids using
an independently generated successor `sprsina` as a new source. It does not
qualify arbitrary suffixes, snapshots or horizons.

The C1a interface qualifier itself should reuse only already observed finite-
safe q0/NR1R2-style prefix families; it must not smuggle a new exploratory
plant campaign into a replay test. A later novel C2a suffix still needs its
own pre-action hard filter and independent successor support. If that initial
support cannot be constructed without assuming the candidate's own result,
C2a remains blocked even when replay mechanics pass.

Freeze several already observed q0/NR1R2-style exact prefixes/suffixes and
compare paired boundary, Ip, actual currents, issued/serialized/applied
actions, effect age and available passive diagnostics. Measure mechanics,
determinism, history integrity, failure/timeout rate, worst-case turnaround,
replay error versus prefix length and storage cost. C1a PASS does not qualify
a novel C2a action envelope. If a candidate leaves an independently supported
prefix/action cell, it first needs a pre-result one-step bound; without one,
C2a is blocked rather than enlarging C1a to explore it. A slow source replay
may be an offline shooting/search or teacher tool; it is not a 1 ms online
Oracle.

### 9.2 NR2R2C0 and C1b: parallel `sprsina`/snapshot qualification

C0 is a zero-new-TSC representation/semantic audit using existing B0 and
NR1R2 evidence without modification. Any byte/record localization requiring
server raw must be separately authorized as a minimal read-only operation.
Freeze expected files, times, hashes, byte/record diagnostics and routes
before opening bytes. If no documented schema or trusted decoder exists,
classify only `LOCALIZED_UNKNOWN` or `PERVASIVE_UNKNOWN`; never whitelist
changing bytes post hoc.

C1b is a separate behavioral test. First authenticate each selected raw state
directory as a complete restart input and freeze its exact time/action/effect
state. Then use matching-time restart candidates whose checked observables
match and whose `sprsina` bytes differ, with several prospectively frozen
common suffixes. A finite behavioral PASS can coexist with unknown byte
semantics; it retains an uncertainty floor and cannot claim hidden-state
identity. C0 and C1b are independent inputs to the finite snapshot-envelope
claim. C1b may give limited behavior with semantic bytes unknown; C0 may
explain bytes without proving behavior. Snapshot-based fast moving-prefix
branching retains both limitations. Canonical-source full replay remains an
independent alternative.

### 9.3 NR2R2C2a/C2b: nominal hold, then finite recourse

If C1a passes, use its source-origin tool to search a small set of actual
Card15 continuations from the canonical 1100 ms source. This is not model
fitting or a controller campaign. C2a asks only whether active time-varying
commands can materially reduce B0 terminal drift while preserving boundary,
Ip, absolute current and slew margins.

Keep development search, fresh qualification and any later teacher use as
different evidence identities. Search offline, freeze one candidate, then
use fresh repeats that did not select it. Search timeout means no candidate
and no issue; there is no online solver in that sentinel. A C2a PASS establishes
only a Nominal-H1 finite active-hold/feedforward continuation.

C2b separately tests a prospectively frozen state/current/belief tube or
bounded perturbation set around that nominal path. Each candidate and each
prefix recourse must pass the independent hard filter using pre-search/pre-
action uncertainty; branch optimality cannot prove its own safety. Recourse-
L1 requires a contingency policy/tree that satisfies constraints throughout
and reaches its declared smaller terminal hold/recoverable set. Online
rolling-Oracle timeout and atomic fallback belong to a later qualification.

If branch/replay is unavailable, an alternative may use only a very small
primitive with an already independent one-step worst-case successor bound;
the outer envelope and immediate stop alone are insufficient. If neither
route can obtain controlled-response evidence safely, stop at source
observation; do not invent a recovery model.

If no active continuation reduces drift inside the hard actuator envelope,
the next architecture review must consider whether the 1100 ms scenario
requires a known time-varying nominal feedforward, another actuator or a
revised finite command envelope. This would be an authority/interface
question, not a neural-model failure.

For the fixed source, the Nominal-H1 object may be a time-indexed nominal
feedforward plus a feedback residual. Absolute time is causal and legitimate for that
frozen scenario, but it must not become a shortcut claimed to transfer across
new anchors or arrival histories.

### 9.4 NR2R2D: minimal response-tail discriminator, then atlas

Only after a C2b Recourse-L1 source continuation exists, measure a minimal
structured response set with matched all-command-baseline continuations,
non-overlapping effect windows, repeated same-prefix trials and sparse/
structured signed directions. First establish response SNR, Card15 resolution,
tail length, output rank/condition and repeatability. Do not jump directly to
a broad fourteen-dimensional campaign.

For every later anchor:

- before issuing transport, freeze the target anchor tube's provisional
  recourse and use prior independent evidence to cover the entire transition
  tube plus every possible prefix successor with reserved Recourse-L1;
- only then execute a fresh bounded sentinel to confirm repeatability,
  settle/action-age, transition coverage and target-anchor admission; this
  confirmation may admit the anchor but may not create its first backup after
  arrival;
- begin any anchor probe only after that admission PASS;
- repeat the same primitive under multiple positions and arrival histories;
- include matched-time/different-position and matched-position/different-
  time/history contrasts;
- treat every cumulative staircase level as a new prefix/anchor; and
- keep whole anchor/history/sibling-branch families in one evidence split.

Begin with a first qualification domain inside a small connected HFS region;
this stages, rather than reduces, the user's final domain. R_mid crossing and
bidirectional return remain required later qualifications, and belief never
resets.

### 9.5 Structured model, static controller and adaptation

The first model remains:

```text
exact actuator/queue
  + active nominal continuation
  + context-conditioned residual dynamics
  + stable low-order belief/observer state
  + smooth LPV/local scheduling over supported context
  + optional small residual only after prospective benefit
```

Compare it with simpler baselines on fresh whole-anchor/history families.
Only calibrated, useful uncertainty permits a reference governor and static,
recovery-backed constrained MPC. Its terminal/timeout paths must connect
directly to the already qualified recourse layer; a model tube cannot
substitute for hard recovery. With only finite Recourse-L1, each accepted
reference, total case horizon and latest abort time must fit inside its
remaining qualified horizon while every step retains the full declared
contingency. Sustained or arbitrarily repeated replanning requires Recourse-L2
or a governor with separately proved equivalent recursive feasibility. The
first controller uses no dedicated probe and no online parameter influence.

Run low-dimensional adaptation in shadow mode on fresh closed-loop histories
generated by that frozen controller, not only on identification schedules. A
PASS authorizes a separate adapter-in-loop safety sentinel; it does not
immediately change actions. Adapter mismatch must atomically fall back to the
static controller while preserving the static tube and recovery. Only after
that gate may the route consider active information actions, R_mid crossing,
outer RL, recurrent policy distillation or ILC.

## 10. Meaning of probe-learn-probe

The user's intuition should be preserved in this later form:

```text
TRACK/HOLD
  -> preauthorize one probe primitive or non-overlapping batch
  -> OBSERVE through the complete effect window
  -> propose a shadow low-dimensional update
  -> accept/reject posterior and uncertainty tube
  -> replan the next action
```

If actions overlap continuously, the estimator must explicitly attribute the
complete input convolution/state sequence; it may not assign a mixed response
to the last probe. Continuous overlap opens only after that attribution model
has been separately qualified. A single three-output transition cannot update
an arbitrary `3 x 14` gain. Parameter dimension, regressor, excitation,
minimum singular value, condition, projection set, uncertainty floor and OOD
expansion rule must be frozen prospectively.

Deep/global weights remain frozen inside a run. Start with passive learning
from necessary tracking actions, then information-aware selection among
near-equivalent safe allocations, and only finally dedicated micro-probes.
Every probe is safe under the pre-probe tube assuming no information gain.
Until the complete effect window and update audit finish, no uncertainty
shrink may influence any action; an accepted update affects only a later
planning cycle.

## 11. What must not happen next

Do not:

- enter NR3 or enlarge GRU/LSTM/TCN;
- reuse the opened NR2R1 holdout for design or calibration;
- call q0 return hold/recovery or B0 a perturbation-recovery test;
- call byte-different `sprsina` physical nondeterminism or silently metadata;
- call fixed-prefix replay an arbitrary/growing-prefix Oracle;
- fit an unrestricted online `3 x 14` Jacobian or update deep weights at 1 ms;
- use online RL, random dense 14-dimensional exploration or reward as safety;
- transport to an anchor before that prefix has admitted Recourse-L1;
- cross R_mid, expand the domain or add waypoints before same-side control;
- shrink the current action's safety tube using expected future learning; or
- let Oracle, MPC or RL bypass paired-boundary, Card15, current, slew, Ip,
  queue, timeout and recovery gates.

## 12. Pause and authorization boundary

The current pause is scientifically justified. The project is not blocked
because a more advanced neural model is needed. Model/controller execution is
blocked by missing active source recourse; snapshot-based moving-prefix work
awaits C1b finite behavioral qualification while any unresolved byte semantics
remain an explicit uncertainty floor and claim limitation.

The next separately authorizable design candidates are **NR2R2C1a canonical-
source full-prefix replay/shooting**, **NR2R2C0 read-only `sprsina`
representation semantics**, and **NR2R2C1b finite snapshot behavior**. They
are parallel identities; none is authorized by this report. Any C0 server-raw
read and any C1b TSC must be separately declared and limited. C1a PASS may
authorize only C2a's nominal active-hold design. C0 evidence and a separately
authorized C1b behavioral PASS may jointly bound only their finite snapshot
envelope. C2a Nominal-H1 PASS may authorize only C2b's
bounded-tube contingency design. Only C2b Recourse-L1 PASS may authorize the
minimal response-tail stage. No C-stage PASS directly authorizes an atlas,
model, NMPC, RL or learning-data campaign.
