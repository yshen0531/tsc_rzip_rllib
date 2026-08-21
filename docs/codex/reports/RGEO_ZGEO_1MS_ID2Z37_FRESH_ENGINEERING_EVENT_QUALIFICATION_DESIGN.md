# ID2Z37 fresh engineering-event qualification design

Date: 2026-08-21

## Frozen purpose

Qualify the immutable ID2Z36 payload on fresh phases. Run phase48 calibration
first; open phase54 blind only if calibration, replay, prefix, raw and
execution gates all pass. The model is never refit.

ID2Z35 calibration rows remain zero fit and are not input evidence for metric
calculation. Phase54 was not executed by ID2Z35 and remains unopened at design
freeze.

## Matrix and budget

- one matched moving-center baseline;
- phase48 q_R/q_Z plus/minus calibration branches;
- one exact phase48 q_Z-plus replay;
- four unopened phase54 q_R/q_Z plus/minus blind branches;
- each rollout: 73 advances / 74 states;
- maximum: 10 resets, 730 attempts/calls/verified advances, 740 states and
  3,700 required artifacts;
- no retry, no resume and no cleanup/return action after the frozen stream.

Each branch applies eight same-sign residual issues and eight exact opposite
issues around the corrected moving center. All streams, Card15 targets,
plus/minus separation, exact cumulative return and outer-margin checks must
pass before any TSC.

## Qualification

The fixed q_R-minus/effect-age-13 event cell uses the ID2Z36 half-width
`[0.375 mm, 0.075 mm, 30 A]`; it is not calibrated or widened. All other
effect-age 1--17 cells use the immutable point centers.

Calibration requires:

- all 68 response cells complete;
- event containment `1/1`;
- non-event maximum errors no greater than `0.05/0.05 mm/25 A`;
- exact q_Z-plus replay and all integrity gates.

The non-event blind half-width is then fixed to `1.25` times the larger of the
ID2Z34 development residual and fresh calibration residual, with the already
frozen floor and cap. Blind requires `68/68` containment, including the fixed
event box. No value observed in calibration or blind may modify the event box,
point centers, multiplier, floor or cap.

## Routes and stop rules

Any package/input/action-stream/storage failure stops before TSC. Any runtime,
prefix, raw or replay failure is an execution/integrity failure, not scientific
model evidence. Calibration FAIL stops before blind. Blind FAIL closes the
engineering-floor sparse-event model route; no adjacent phase, wider box or
third model follows. PASS authorizes shadow-only use and a separate
Authority/Recourse design, not in-loop feedback.
