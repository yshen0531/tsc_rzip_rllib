# R_geo/Z_geo 1 ms ID-2H1 whole-history calibration result

Date: 2026-08-17 Asia/Shanghai

## Verdict

ID-2H1 is final as
`ONE_MS_ID2H1_GROUPED_CALIBRATION_PASS_BLIND_HOLDOUT_DESIGN_ONLY`.

The real server campaign completed 40/40 rollouts, 1,360/1,360 verified
one-ms plant advances, 1,400 states and all ten atomic whole-history groups.
Every one of the 20 baseline/probe cells had two exact replays.  The primary
and independent raw parsers agreed on the 7,000-file, 82,450,093,600-byte
inventory and digest
`e1d0f21c48949b0b4c2c2aaba41a623f9b8d42ba62c2c3267a70cd96b6b8e66d`.
Maximum checked replay differences in geometry, Ip, 14 coil currents and 48
wire currents were zero.

## Frozen-model calibration

No model was fitted, retrained, tuned or reselected.  The selected ID-2G1R1
causal TCN artifact retained SHA-256
`14502175c95d1d0b5b36846a35af249af0041405eb6c013f099caa4dd18d176b`.
Using each complete conditioner family as one calibration unit, the tenth
(maximum) score among ten groups produced:

- simultaneous absolute-recursive half-width:
  `0.593642 mm R / 0.240511 mm Z / 24.047694 A Ip`;
- simultaneous matched-baseline response half-width:
  `0.695069 mm R / 0.238259 mm Z / 7.717859 A Ip`;
- matched-response NRMSE: `0.729530984`;
- positive peak-response direction: `10/10` groups.

All preregistered width, response-NRMSE and direction gates passed.  The
independent implementation re-extracted the full raw tree and recomputed the
calibration with maximum numeric difference zero.

## Scientific meaning

This is evidence that the frozen TCN generalizes with finite, small errors to
these fresh conditioner/probe histories around the same source-local active
nominal.  It is stronger than a development-fold score because the histories
were generated after model selection and no parameters were updated.

It is not yet a blind holdout: these ten groups set the reported widths.  It
also does not establish two-axis authority, a controller-grade transition
tube, recovery, recursive feasibility, path tracking, R_mid crossing, online
adaptation or global reachability.  The only unlocked action is a separately
frozen blind whole-context/history holdout of the unchanged model and widths.

ID-2C2 remained unread, and the new raw is forbidden for training, tuning,
selection, fixtures, expert data, BC, DAgger or RL.
