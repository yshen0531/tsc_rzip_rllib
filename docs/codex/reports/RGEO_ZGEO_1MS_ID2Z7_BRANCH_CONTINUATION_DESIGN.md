# R_geo/Z_geo 1 ms ID-2Z7 fresh later-round branch continuation design

Date: 2026-08-19

## 1. Identity and purpose

ID-2Z6 and ID-2Z6R1 are consumed and may not resume. ID-2Z7 is a new
simulator-only empirical-development identity. It preserves the independently
audited ID-2Z6 round-0 five-arm matrix and its frozen `f4` selection, then
generates fresh, complete state-53 and state-57 sibling matrices and one fresh
zero-fit replay.

ID-2Z7 is not a retry of the interrupted round-1 branches. The old
`r1__hold4`, `r1__b4` and partial `r1__f4` are bound as route evidence and
have zero fitting and selection weight. They are not used to choose an arm,
calibrate a tube, or validate the successor.

The final goal remains safe, causal, approximate two-axis waypoint/path
tracking from the fixed 1100 ms takeover, eventually including repeated
bidirectional R_mid crossing with uninterrupted belief. This stage is only a
finite source-local branch-teacher and development-data discriminator.

## 2. Frozen inherited evidence

The following ID-2Z6 facts are inputs, not recomputed scientific outcomes:

- the corrected independent audit passed the retained 493-state raw tree;
- round 0 completed `hold4`, `b4`, `f4`, `b2f2`, and `f2b2`;
- all five round-0 causal prefixes passed;
- the frozen selector chose `f4` with terminal score `3.6768265246995937`;
- the matched hold score was `4.407677636593896`;
- the old interrupted round-1 paths have zero successor weight.

ID-2Z7 must hash-bind the ID-2Z6 config, final result, corrected independent
audit, result report, and all five round-0 compact trajectories. A mismatch
stops before runner construction, reset, or plant advance.

## 3. Fresh experiment matrix

The inherited logical parent is the exact constructed `f4` round-0 stream.
The fresh decision roots are:

```text
round B  logical state 53  issues 53--56
round C  logical state 57  issues 57--60
```

At each root, ID-2Z7 evaluates exactly five four-issue macros:

```text
hold4  HHHH
b4     BBBB
f4     FFFF
b2f2   BBFF
f2b2   FFBB
```

Every branch is reconstructed from the canonical 1100-ms source, replays the
entire selected causal prefix, applies its four-issue macro, and holds the
attained exact Card15 target through issue 68. Every branch therefore retains
states 0--69, while fitting uses only the declared complete causal state-49--69
window.

The selected round-B parent is chosen only from the five fresh round-B
siblings. The selected round-C parent is chosen only from the five fresh
round-C siblings. The final replay reconstructs the exact selected
`f4 -> round-B winner -> round-C winner` stream and has fit weight zero.

The new run is capped at:

```text
fresh branch rollouts                    10
fresh zero-fit replay                     1
reset calls                              11
advance attempts / gotsc calls          759
verified successors                     759
retained states                         770
required artifacts if complete        3,850
estimated raw budget                     50 GB
```

Retry after any plant-advance attempt is forbidden.

## 4. Mandatory run-root isolation

Before real TSC, both implementation tests and the installed zero-TSC
preflight must prove:

1. the runner's `run_root` equals `<new-output>/rollouts` before runner
   construction;
2. every expected rollout directory resolves under that exact root;
3. the historical generic `rgeo_zgeo_1ms_nr1_runs` root is not selected;
4. no output, compact, metadata or raw path already exists;
5. a fake runner creates no path outside the injected temporary output;
6. early failure cannot silently fall back to a default run root.

Any mismatch is `OFFLINE_OR_INPUT_FAIL_NO_TSC`. A real attempt that writes
outside the frozen output is an execution/interface failure; the identity is
consumed and must stop without retry.

## 5. Unchanged physical and scientific gates

ID-2Z7 inherits ID-2Z6's exact action and observation semantics:

- exact/noiseless same-step paired-boundary R_geo/Z_geo and Ip before issue;
- complete post-takeover causal observation and owned action history;
- future successor and future actual current forbidden;
- exact absolute Card15 targets, issue `k` to state `k+1`;
- each coil's requested and readback step change at most 0.3 A;
- no reliance on runner clipping;
- exact prefix, actual current, full 48-wire diagnostic, Ip, boundary,
  runtime, solver and abnormal-state checks.

The three envelopes remain distinct:

```text
capture     six terminal states 64--69 within 25 mm / 0.1 m/s / 5% Ip
development preissue shell       35 mm per R/Z axis / 7.5% Ip
hard envelope                    50 mm per R/Z axis / 10% Ip
```

Post-successor empirical trips remain 2 mm R, 2 mm Z and 150 A Ip. They are
simulator-development stops, not qualified tubes or recovery guarantees.

Round selection remains capture-first, then minimum terminal worst-normalized
score, with the same 0.02 improvement-over-hold eligibility threshold. Final
teacher utility requires capture or at least 0.25 improvement over the frozen
ID-2Z6 round-0 all-hold score.

## 6. Data readiness and split role

The only development-eligible external records are the five complete audited
ID-2Z6 round-0 windows. The ten fresh ID-2Z7 sibling windows are eligible only
if each path completes and the final full-raw audit passes. The replay is
zero-weight. Thus the maximum and required development-window count is
exactly fifteen.

The seven later ID-2Z6/R1 records are zero-weight. ID-2Z5 remains zero-weight.
No calibration, holdout, expert, BC, DAgger, RL, controller qualification or
safety data is read or created by this stage.

The fifteen windows represent three nearby decision roots with shared family
structure, not fifteen independent plasma histories. A later model comparison
must group siblings by root/history and remain a small sequence-outcome
discriminator. It may not claim broad history, position or waypoint
generalization.

## 7. Routes

- Input, hash, action-matrix, storage or run-root isolation failure: zero TSC.
- Prefix, Card15, readback, raw, runtime, boundary or hard-interface failure:
  stop the whole new identity; no scientific verdict.
- Missing complete fresh sibling, no eligible arm, replay mismatch, or final
  utility failure: close this exact B/F/H teacher route and enter the already
  recorded bounded action-basis/authority review.
- Utility PASS with fewer than fifteen eligible windows: teacher progress only;
  no model.
- Complete utility, data-readiness and replay PASS: authorize only a separately
  frozen small sequence-outcome model comparison and fresh replay/Recourse-L1
  design.

No ID-2Z7 result is itself hold, recourse, controller, waypoint, crossing,
adaptation or reachability evidence.
