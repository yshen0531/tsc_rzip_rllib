# R_geo/Z_geo 1 ms ID-2H1 fresh whole-history calibration design

Date: 2026-08-17 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2h1-fresh-whole-history-calibration-v1`

## Purpose

ID-2G1R1 selected one causal TCN on three grouped development contexts.  The
weights, feature order, normalization, three seed members and recursive
prediction semantics are frozen.  ID-2H1 does not select, fit, fine-tune or
adapt a model.  It creates fresh TSC histories solely to calibrate finite
multi-step absolute-state and matched-response error widths for that exact
artifact.

This stage is still simulator identification/evaluation, not controller
safety qualification.  Its empirical exploration contract permits the
prospectively declared finite TSC transitions below; it does not turn their
post-successor stops into pre-action transition bounds.

## Frozen campaign

Every rollout starts from the canonical 1100 ms source and uses the exact
one-ms Card15/queue contract.  Issues 0--15 reproduce the held
`p03_minus_stride1` active nominal.  Ten whole-history groups are used.  Each
group contains one conditioner-matched baseline cell and one assigned probe
cell, and each cell has two exact replay members.  Thus the maximum campaign
is 40 resets, 1,360 advances and 1,400 retained states.

| group | conditioner before issue 22 | assigned issue-22 probe |
|---|---|---|
| c00 | none | p04 plus, duration 2 |
| c01 | p04 plus, issue 17, duration 1 | p04 minus, duration 4 |
| c02 | p04 minus, issue 17, duration 1 | p07 plus, duration 2 |
| c03 | p07 plus, issue 17, duration 1 | p07 minus, duration 4 |
| c04 | p07 minus, issue 17, duration 1 | p04 plus, duration 4 |
| c05 | p04 plus, issue 19, duration 2 | p04 minus, duration 2 |
| c06 | p04 minus, issue 19, duration 2 | p07 plus, duration 4 |
| c07 | p07 plus, issue 19, duration 2 | p07 minus, duration 2 |
| c08 | p07 minus, issue 19, duration 2 | p04 plus, duration 1 |
| c09 | p04 plus at issue 17 and p07 minus at issue 20, each duration 1 | p07 minus, duration 1 |

The baseline receives the same conditioner but no issue-22 probe.  A
conditioner or probe is always returned exactly to the held nominal after
its declared duration.  Directions are complete translated 14-dimensional
Card15 targets; virtual labels are metadata and never executor truth.

Every current R_geo/Z_geo/Ip observation is exact and available before its
issue.  The successor is unknown until the TSC advance.  Per-step Card15,
0.3 A/turn slew, absolute current, paired-boundary, Ip, inner-clearance,
outer-envelope and 2 mm/2 mm/100 A empirical successor-stop checks remain
fail closed.  Any failure stops before the next issue and preserves raw.

## Frozen calibration calculation

The predictor is the arithmetic mean of the three frozen TCN seed members.
No gradient, optimizer, fitting, model selection or parameter update is
allowed.  Each exact replay pair is averaged only after raw and repeatability
gates pass.

For every whole-history group and output axis, compute:

1. the maximum absolute recursive state error over both baseline and probe
   cells and states 17--34;
2. the maximum absolute matched probe-minus-baseline response error over
   states 23--34.

The statistical unit is the complete group, never a step.  With ten groups
and nominal group coverage 0.90, the finite-sample order index is
`ceil((10 + 1) * 0.90) = 10`; therefore each reported simultaneous width is
the maximum of the ten group scores for that axis.  This is a finite sampled-
family calibration statement, not a global or distribution-free plant
theorem.

The frozen usefulness gates are:

- absolute recursive group-max width no greater than
  `1.5 mm R / 1.5 mm Z / 75 A Ip`;
- matched-response group-max width no greater than
  `1.0 mm R / 1.0 mm Z / 50 A Ip`;
- aggregate matched-response NRMSE strictly below the action-blind value
  `1.0`;
- positive R/Z peak-direction cosine in at least 8 of 10 groups.

Calibration failure cannot tune the artifact or choose another candidate.
It routes to model/data review.  A complete PASS authorizes only a separately
frozen blind whole-context/history holdout design.  It does not authorize a
transition tube, authority, recourse, controller, MPC, crossing, adaptation,
expert data or RL.

## Evidence and data roles

- ID-2F1R1 raw remain development-fit evidence only.
- The exact ID-2G1R1 model SHA-256 is
  `14502175c95d1d0b5b36846a35af249af0041405eb6c013f099caa4dd18d176b`.
- ID-2H1 raw are calibration-only and forbidden for training, tuning,
  fixtures, expert/Oracle/BC/DAgger/RL data and controller qualification.
- ID-2C2 and every future blind holdout remain unopened.
- Siblings from one conditioner group are one atomic statistical unit.

Primary execution, a structurally separate raw reparse, primary calibration
and an independent calibration recomputation are all required.  The server
raw tree remains immutable and only compact results are copied locally.
