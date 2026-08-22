# Fixed-1000 post-F1 high-level route decision

## Decision

The F1 deadband repair remains vetoed and the q0-relative threshold-repair
line is closed. The next active route is **absolute-viability / nominal
Authority first**, followed only on real Authority evidence by a
history-conditioned endpoint-value model and independent Recourse.

This is a route change, not a reinterpretation of F0. F0 remains
`ONE_MS_NR1000F0_FINITE_Q0_RELATIVE_TRACKING_FAIL_REDESIGN`: all six measured
position checkpoints were close to their commands, but the frozen controller
selected negative-predicted-progress actions at issue 48. F1 remains a
zero-TSC pre-execution design veto because its endpoint tolerance made the
first radial segment vacuous and it treated the unknown no-action tail as
zero.

## Evidence behind the route change

The finite fixed-1000 foundation is useful and retained:

- the restart/interface, exact paired boundary, exact Card15 action and
  one-ms issue/effect semantics are qualified;
- D0R1/D1 establish finite signed and cumulative two-axis response;
- V0 passed development, fresh calibration and mixed-history blind tests for
  four finite **differential** candidates;
- A0 demonstrated two causal observation-recentered decisions;
- F0 completed four clean real rollouts and measured six checkpoint errors of
  only `0.0073--0.1658 mm`.

The same evidence also proves that V0 is not an endpoint model. In F0, while
the active target was q0 between macro endpoints, the q0-relative state moved
by approximately `0.240/0.255 mm` over states 32--36, `0.135/0.148 mm` over
states 44--48 and `0.377/0.378 mm` over states 56--64 for the two paths. A0
and B1 independently contain no-action tails of comparable scale. These
tails are much larger than V0's maximum `0.045539 mm` response half-width.
Exact current observation therefore does not make future no-action response
zero.

More fundamentally, B0 q0 drifts `23.538658 mm` inward over 64 ms and remains
near `0.318 m/s` late in the run, whereas the currently qualified radial h8
macro effect is about `0.28--0.31 mm`. The fixed-1000 source is about
`60.24 mm` inside `R_mid`. A q0-relative residual controller is consequently
not an absolute nominal, hold, capture or connected-domain controller.

## Next active stage

The next stage is one bounded, prospectively frozen fixed-1000 teacher and
Authority discriminator. Its zero-TSC design/preflight must define:

1. a low-dimensional, exact-Card15 **sustained** nominal/allocation grammar,
   including matched nominal/no-action continuation, signed R/Z correction,
   braking/deceleration and a finite continuation candidate;
2. absolute task outcomes containing R/Z endpoint, terminal one-ms velocity,
   Ip, current/headroom, pending action/age and continuation margin;
3. whole-history matched branches and roles declared before TSC, with all
   development negatives retained and selected/replay rows kept zero-fit;
4. a fixed branch/search budget, fixed roots and fixed stop rules; TSC branch
   search is an offline teacher and may not be called a deployable controller;
5. non-vacuous acquisition gates relative to the matched no-action future,
   separately from endpoint tolerance and maintenance/continuation gates.

The teacher must first establish task-aligned Authority. At minimum, a
candidate must beat the matched continuation by a preregistered margin larger
than replay/model uncertainty, preserve all hard constraints, materially
reduce absolute drift or terminal speed, and retain a finite safe
continuation. A single-frame event, an input-space rank, command return, or a
q0-relative score improvement is insufficient.

If no admissible candidate family has absolute control-aligned Authority, the
stage stops before model training and redirects to nominal/action-basis
co-design. It must not be followed by a nearby phase, amplitude, deadband,
duration or third-network ladder.

## Learning route after Authority only

On Authority PASS, the same prospectively eligible matched branches may feed
at most two bounded endpoint-value candidates:

1. a factorized history-conditioned nominal/no-action tail plus the frozen
   differential candidate set;
2. the same backbone plus one small causal history-by-candidate residual.

The model observes exact current R/Z/Ip directly, together with current,
queue/action age, absolute time and compressed causal history. It predicts
finite h4/h8/h16 endpoint sets, terminal velocity, Ip/current/continuation
margins and support/refusal. It does not estimate the current truth, perform
unconstrained full-trajectory point rollout, train an end-to-end 14-D policy,
or reopen the point-model/network ladder.

Fresh calibration may calibrate only preregistered intervals/refusal; it may
not refit centers, features or ranking. An unopened whole-history blind test
follows. C0/B1/A0/F0 and all integrity replays remain zero-fit for the new
model.

## Control dependency and stop rules

```text
absolute nominal / Authority teacher PASS
        +-- matched branch data -> endpoint value/risk -> fresh cal/blind
        `-- terminal/continuation data -> independent Recourse-L1

model PASS AND Authority PASS AND Recourse PASS AND hard interface PASS
        -> one non-vacuous real feedback sentinel
```

- Endpoint tolerance, acquisition progress and maintenance are distinct.
- A mandatory path segment must fail under its real matched no-action future;
  otherwise the experiment is a vacuous tracking FAIL.
- No-action is selectable only inside a qualified continuation/invariant set;
  q0, exact command return and software stop are not Recourse.
- A candidate without a qualified continuation cannot execute in a controller.
- Failure of the bounded teacher closes the current grammar before fitting.
- Failure of both bounded models closes model expansion; no third model.
- Fresh calibration failure cannot widen/refit, and blind failure cannot flow
  back into development.
- Recourse failure blocks longer or more frequent in-loop execution.
- One teacher, at most two models, one calibration/blind sequence, one
  Recourse qualification and one feedback sentinel are the cap for this
  route.

## Final goal and remaining milestones

The final goal is unchanged: from the authentic fixed 1000-ms takeover, use
the exact/noiseless one-ms R_geo/Z_geo/Ip observation and continuous causal
history to safely follow finite two-axis waypoint/path commands under exact
Card15, per-coil `<=0.3 A/step`, current, Ip and Recourse constraints; then
hold, recover and repeatedly cross `R_mid` in both directions without
resetting belief.

The remaining major milestones are: absolute nominal/terminal Authority;
qualified endpoint value/risk and Recourse; a non-vacuous local absolute
feedback sentinel; overlapping multi-position anchors with hold/recovery;
then single and repeated bidirectional `R_mid` crossing. Fixed-1100 evidence
remains historical and is not training or qualification evidence.
