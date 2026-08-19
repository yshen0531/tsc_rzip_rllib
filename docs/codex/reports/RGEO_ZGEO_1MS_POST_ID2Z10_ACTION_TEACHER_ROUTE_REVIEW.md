# R_geo/Z_geo 1 ms post-ID-2Z10 action/teacher route review

Date: 2026-08-19 Asia/Shanghai

## Decision

ID-2Z10 is final as
`ONE_MS_ID2Z10_FIVE_CONTEXT_MODEL_FAIL_ACTION_BASIS_CONTROL_REVIEW`.
The user accepted the following route correction:

```text
one prospectively frozen action-grammar redesign
-> one bounded truth-recentered exact-TSC capture teacher
-> fresh selected-path replay
-> only after teacher/capture PASS, new value/reachability data and two small models
```

The current low-capacity response-model line is closed. No larger recurrent
network, calibration, blind holdout, policy fit, controller issue, Recourse-L1
claim or waypoint execution is authorized by ID-2Z10.

## Evidence that drives the change

ID-2Z9 measured real, repeated local utility. From the first state-49
matched-hold score `4.407678` to the five-macro selected path, the frozen
terminal score fell to `2.983667`, an improvement of `1.424011` or `32.31%`.
The final path nevertheless failed capture:

```text
terminal maximum source R/Z distance        26.767972 mm
terminal maximum 1 ms R/Z speed              0.2983667 m/s
terminal maximum source-relative Ip fraction 0.0369719
```

The score was speed-limited: `0.2983667 / 0.1 = 2.983667`. Therefore the
existing B/F/H grammar has nonzero finite braking/transport utility, but even
the measured best branch at every one of five decisions did not produce a
capture seed.

ID-2Z10 cleanly rejected both frozen candidates. The stable model and its
GRU4 residual both chose `b4` in all five folds, while measured best arms were
`f4 -> b2f2 -> f2b2 -> b2f2 -> f2b2`. Every fold exceeded the frozen
`0.3 mm` R p95 gate; the GRU changed no ranking and worsened the maximum R
p95 from `0.726041` to `0.873908 mm`. No artifact exists.

The failure has three distinct layers which must not be collapsed:

1. The four-step B/F/H candidate grammar has not demonstrated capture or
   recourse, even with exact TSC branch selection.
2. The five roots are nested states on one selected causal lineage. They are
   distinct decision contexts, but not five independent arrival-history
   families.
3. The fitted target is paired response relative to a measured held sibling.
   The terminal score is dominated by 1 ms speed, whereas the main fit gates
   are position-response errors. The evaluator may use the measured held
   future for development comparison, but a deployable planner cannot know
   that future.

The exact B/F input basis itself is rank two with condition `1.24348`; this is
not a numerical rank failure. ID-2Z10 therefore does not prove that the
physical basis, recurrent learning, two-axis control or the plant is globally
incapable.

## Frozen design principles for the successor

The next design is one finite capture-teacher campaign, not another manual
depth ladder or a sequence of one-action micro-probes.

- Keep exact/noiseless same-step paired-boundary R_geo/Z_geo and Ip direct at
  every decision. Belief represents only unobserved memory and future
  response, never current or past R/Z/Ip measurement uncertainty.
- Keep H/B/F as measured baselines. Add at most two complementary signed
  primitives selected before TSC from already measured, exact-Card15 cells.
  No arbitrary 14-D continuous action search and no post-result primitive
  additions are allowed.
- Use short capture-oriented candidate sequences and truth-recenter at each
  issue. Branch futures are teacher labels; the logical path commits only
  the frozen first action/chunk before observing the next true state.
- Use at least one main and one non-nested causal arrival history. Siblings
  remain grouped by complete prefix; replay has zero fit weight.
- Preserve separate capture, simulator-development and hard-envelope
  contracts. Development safe-stop is not recovery or safety certification.
- Freeze branch count, depth, common observation horizon, score, tie band,
  storage budget and stop routes before TSC. Do not change them after seeing
  candidate outcomes.

The teacher objective must directly report six-state capture and the separate
distance, 1 ms speed, Ip/current and continuation margins. A relative-score
improvement alone is not scientific PASS.

## Required routes

Teacher PASS requires all of:

1. a selected logical path satisfies the frozen six-state capture gate;
2. the selected path replays exactly under a fresh identity;
3. a non-nested history supplies prospective support for the same action
   grammar rather than a single-path coincidence;
4. exact Card15, slew, absolute current, Ip, boundary, prefix, effect timing,
   runtime, raw and independent-audit gates pass; and
5. all required complete causal windows exist without deleting hard cases by
   safe-stop.

Teacher FAIL closes the one frozen source-local grammar. It routes to an
action-authority, nominal/takeover or reachability review. It does not
authorize a deeper hand ladder, wider network, gate relaxation or holdout.

## Machine-learning boundary after teacher PASS

The learned object changes from paired trajectory response to a causal
candidate value/reachability object:

```text
Q(causal history, current exact RZI/current/queue state, candidate sequence)
  -> distance / explicit 1 ms speed / Ip and current margins
  -> capture or reachability value
  -> calibrated uncertainty and support status
```

Trajectory response may remain an auxiliary task, but future matched-hold
truth is forbidden at deployment. Only two candidates may be compared: a
support-gated structured value model and the same backbone plus a small
persistent recurrent residual. Whole-history top-K teacher recall, regret,
margin calibration and fresh TSC shortlist utility replace response MAE as
the primary selection axes. Failure of both models stops capacity growth.

## Final-goal boundary

The final goal remains fixed-1100-ms, 1-ms, exact-RZI, full-causal-history,
exact-Card15 two-axis waypoint/path control under independent hard safety and
recovery, eventually including bidirectional repeated R_mid crossing without
belief reset. The next teacher is only a source-local capture/authority
discriminator and prospective data source; it is not that controller.
