# ID-2Z17 full-F transient remaining-basis beam design

Date frozen: 2026-08-20

## 1. Decision and evidence boundary

ID-2Z16 is final.  Its exact two-layer `H/B/F` beam and any third round,
wider beam, extra `F` rate, nearby root, model fit, controller issue or relaxed
capture gate remain closed.  The selected `f100__f8__f8` path had a useful
transient at state 48 (`23.2073 mm`, `0.2180 m/s`) but its held terminal tail
rebounded to `28.254919 mm / 0.416472 m/s`; exact fresh replay and independent
raw audit passed.  This is evidence of finite transport authority and missing
terminal capture, not evidence of recovery or global unreachability.

This stage is the one finite new-basis discriminator permitted by the
post-ID-2Z16 route.  It uses no fitted model and reads no holdout.  It asks
whether five previously screened but not late-cumulative development
directions provide finite capture utility at the exact state-48 transient.
It does not reopen the closed `B/F/p04/p01/p09` grammar.

The direction labels `p02`, `p05` and `p08` originally belonged to switch
schedules containing several event vectors.  Here each label means exactly
the first signed Card15 event recorded by ID-1C0, not the complete historical
switch schedule.  The actual 14-vector Card15 target is authoritative.

## 2. Zero-TSC action audit

At the exact selected ID-2Z16 state 48, translate the ID-1C0 first-event
Card15 increments around the active command.  Use the signed first events of
`p00`, `p02`, `p05`, `p06` and `p08`:

- `p00` and `p06` use their exact full-amplitude increments, at most `0.3 A`
  per coil per issue;
- `p02`, `p05` and `p08` use their exact half-amplitude increments, at most
  `0.15 A` per coil per issue;
- plus/minus are separate exact Card15 arms; no odd-symmetry assumption is
  allowed;
- the five plus increment columns have rank five and condition
  `3.9078097544` in the unscaled 14-coil current coordinate;
- together with the measured `F/B` increment columns they have rank seven and
  condition `4.2949448294`;
- the first translated targets have at least `103.6 A` absolute-current
  headroom and obey the exact per-issue slew contract.

These numbers establish actuator-space novelty and static representability
only.  They do not establish response rank, position invariance, a transition
tube or safety of an unknown successor.

## 3. Frozen causal schedule

Every rollout authenticates and exactly replays the canonical source prefix
through issue 47/state 48 of `f100__f8__f8`.  Current same-step paired-boundary
`R_geo/Z_geo` and same-step `Ip` are exact/noiseless observations before each
issue; all takeover-era observations and controller-owned action/current
history are available.  The next state remains unknown before issue.

Round 0 at issue 48 contains eleven fixed arms:

1. `h4`: hold the state-48 active command for four issues;
2. for each of `p00/p02/p05/p06/p08`, one plus and one minus arm, applying
   the same exact translated increment cumulatively for four issues.

All arms then hold their issue-51 target through issue 64.  If any complete
round-0 arm already satisfies capture, select the best captured arm and skip
round 1.

Otherwise select the two best complete non-hold round-0 arms from distinct
base direction IDs.  Ranking is capture first, then frozen terminal score,
then arm ID.  From each selected parent at state 52, evaluate exactly three
round-1 children: `h4`, the first selected signed arm, and the second selected
signed arm.  Each child applies four issues and holds through issue 64.
This is six round-1 branches.  No third direction, child, layer or adaptive
amplitude may be introduced after seeing a response.

Finally execute one fresh canonical-source replay of the selected complete
path.  Maximum real budget is therefore `18` resets, `1170` advance attempts
and calls, `1188` retained states and `5940` required artifacts.  No retry is
allowed after any advance attempt.

Offline construction must validate all eleven round-0 schedules and every
ordered parent/child combination over the ten signed actions plus hold,
not only the eventually selected paths.

## 4. Safety and execution contract

The campaign is a prospectively frozen TSC-only empirical exploration.  It
does not pretend that the `2 mm / 2 mm / 150 A` post-successor trip is a
pre-action plant bound.  Before each issue it must enforce exact Card15,
absolute-current, `<=0.3 A` slew, limiter/current, paired-boundary, `Ip`,
clock/effect, source-prefix, run-root and artifact gates.  It must reject
before the runner if the requested target would be clipped.

The unchanged empirical development shell is `45 mm / 45 mm / 9% Ip`; the
hard outer envelope is `50 mm / 50 mm / 10% Ip`.  After a successor, the
frozen empirical trips are `2 mm / 2 mm / 150 A`.  A listed branch-only safe
stop terminates that branch before its next issue and may not be called a
pre-action safety proof.  Any other interface, prefix, raw, runtime or
artifact failure aborts the campaign and cannot become a scientific FAIL.
The hold branch must complete.  At least two distinct-direction non-hold
round-0 arms must complete before round 1 can be interpreted.

## 5. Scientific gate and routing

Capture is unchanged: every one of states 60--65 must have source-relative
`R/Z` distance `<=25 mm`, one-step `R/Z` speed `<=0.1 m/s`, and absolute
source-relative `Ip <=5%`.  Exact selected-path fresh replay is mandatory.

- **Capture PASS:** at least one complete candidate satisfies all six states
  and its fresh replay is exact.  This authorizes only a separately frozen
  Recourse-L1 design around that finite path.
- **Scientific FAIL:** execution and evidence integrity pass, the frozen
  search/replay are complete, but no candidate captures.  This closes only
  the exact state-48 two-layer cumulative-first-event grammar.  It forbids a
  third layer, denser amplitude grid or nearby root and routes to a bounded
  physical-action/reachability redesign, not a claim of global plant
  unreachability.
- **Inconclusive/implementation failure:** any missing hold, insufficient
  distinct complete parents, non-whitelisted stop, prefix/interface/raw or
  replay failure stops without a plant/controller conclusion.

Every trajectory has zero fit weight and is forbidden from calibration,
holdout, expert, BC, DAgger, RL, controller qualification and fixtures.

## 6. Stop rule and final-goal relation

This campaign is deliberately the last hand-enumerated two-layer search at
the full-F transient.  A scientific FAIL must not trigger another manual
direction ladder.  A later route must instead change the reachability/action
construction materially (for example a prospectively bounded joint Card15
allocation or a new earlier nominal), with its own evidence and limits.

The final goal remains fixed-1100-ms, 1-ms, exact-observation, slew-limited,
safe two-axis waypoint/path tracking and later repeated bidirectional
`R_mid` crossing with continuous belief.  ID-2Z17 alone cannot qualify hold,
recovery, a controller, position/history generalization, a waypoint or a
crossing.
