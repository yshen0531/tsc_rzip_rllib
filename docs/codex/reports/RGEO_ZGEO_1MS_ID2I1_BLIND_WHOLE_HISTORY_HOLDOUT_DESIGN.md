# R_geo/Z_geo 1 ms ID-2I1 blind whole-history holdout design

Date: 2026-08-17 Asia/Shanghai

## Purpose

ID-2I1 is the first blind validation of the unchanged ID-2G1R1 causal TCN
and the unchanged ID-2H1 group-max widths.  It is not another model search,
calibration set or opportunity to tune the action matrix.  Development and
calibration records determine every feature, weight, width and gate before
any ID-2I1 TSC call.

## Frozen identities

- selected model SHA-256:
  `14502175c95d1d0b5b36846a35af249af0041405eb6c013f099caa4dd18d176b`;
- ID-2H1 calibration result SHA-256:
  `6e6e0f9fa1c263075d21169dc583bf3e23bb99fbd12afba047af93ad4f94a247`;
- ID-2H1 independent calibration SHA-256:
  `18936948e1a500776b04e8e0bc85e4842ef98c9f1c67cf70236eadb843782ea4`;
- absolute-recursive width:
  `[0.0005936422508353578, 0.00024051138515601006, 24.0476938080501]`;
- paired-response width:
  `[0.0006950692585707685, 0.00023825926428221178, 7.717859491567651]`.

No ID-2I1 state may change these values.  ID-2C2 remains unread.

## Blind family matrix

All paths start from the exact 1100 ms source.  Issues 0--15 replay the
frozen p03-minus stride-1 active nominal and subsequent non-event issues hold
that exact Card15 target.  Each group contains a baseline (conditioners only)
and a probe path (the identical conditioners plus its assigned probe), with
two exact replays per cell.

| group | conditioner history | blind probe |
|---|---|---|
| h00 | p04+ at issue 18 for 1 | p07- at issue 25 for 3 |
| h01 | p04- at issue 18 for 1 | p07+ at issue 25 for 3 |
| h02 | p07+ at issue 18 for 1 | p04- at issue 25 for 3 |
| h03 | p07- at issue 18 for 1 | p04+ at issue 25 for 3 |
| h04 | p04+ at 18 for 2; p07- at 21 for 1 | p04- at 25 for 1 |
| h05 | p04- at 18 for 2; p07+ at 21 for 1 | p04+ at 25 for 1 |
| h06 | p07+ at 18 for 2; p04- at 21 for 1 | p07- at 25 for 2 |
| h07 | p07- at 18 for 2; p04+ at 21 for 1 | p07+ at 25 for 2 |

The issue-18/21 conditioner timing, issue-25 probe timing, duration-three
probes and the two-conditioner histories were absent from ID-2F1R1 and
ID-2H1 as complete groups.  The physical primitives remain exact translated
full-14D p04/p07 Card15 actions, so the test changes history composition and
timing rather than introducing an unrelated actuator direction.

The campaign has 8 groups, 16 cells, 2 replays per cell, 32 rollouts, a
34-issue horizon and at most 1,088 plant advances.  State 16 is the frozen
recursive origin.  Absolute errors use states 17--34.  Paired response uses
states 26--34, beginning at the first effect of the issue-25 probe.

## Gates

The atomic statistical unit is the complete holdout group.  A group passes
calibrated containment only when every baseline/probe absolute error in all
three outputs is inside the frozen absolute width and every paired-response
error is inside the frozen response width.  At least 7/8 groups must pass
this joint containment gate.  This is an empirical blind check of the 90%
group calibration claim, not a new quantile estimate.

Additional gates are frozen before execution:

- matched-response NRMSE `< 1.0` over all eight groups;
- positive peak R/Z response cosine in at least 7/8 groups;
- every group must remain below the unchanged absolute caps
  `[1.5 mm, 1.5 mm, 75 A]` and paired caps `[1 mm, 1 mm, 50 A]`;
- exact Card15, maximum per-turn per-step slew `<= 0.3 A`, absolute-current,
  paired-boundary, Ip, limiter, empirical successor and outer-envelope gates;
- 16/16 replay pairs must be exact in checked geometry, Ip, coil and wire
  histories;
- an independent implementation must reparse all raw and recompute the
  blind metrics exactly.

Steps are never treated as independent holdout samples.  A scientific FAIL
does not permit retuning against these records.

## Storage and stopping

Before execution the server must have at least 220 GB free.  The prospective
raw estimate is 70 GB and must leave at least 150 GB.  The output path must be
new.  Any execution, boundary, action, current, raw or repeatability failure
stops before the next issue and preserves the partial raw; no retry is
allowed after an advance attempt.

## Data and claim boundary

ID-2I1 raw is blind evaluation evidence only.  It is forbidden for fitting,
retraining, tuning, model selection, recalibration, fixtures, expert data,
BC, DAgger and RL.  Current same-step R_geo/Z_geo/Ip remain exact noiseless
observations and the complete post-takeover causal history is available;
future successor state and future actual current remain unavailable.

A complete PASS authorizes only a separately designed source-local
controller-grade authority/tube/recourse stage.  It does not itself authorize
controller execution, MPC, path tracking, transport, R_mid crossing,
adaptation, RL or any reachability claim.
