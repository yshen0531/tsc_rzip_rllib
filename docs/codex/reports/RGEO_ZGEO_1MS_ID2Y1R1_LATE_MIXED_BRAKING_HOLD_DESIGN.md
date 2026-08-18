# ID-2Y1R1 late mixed-braking hold design

## Repair identity

ID-2Y1R1 is a fresh zero-plant action-matrix repair after ID-2Y1 failed its
unchanged 95 A absolute-current-headroom gate.  It does not resume or reinterpret
ID-2Y1.  ID-2Y1 executed zero reset, `gotsc`, plant advance or raw trajectory.

## Frozen streams

All branches replay q0 at issue0 and exact p03-minus stride-one levels1--64.
States0--65/actions0--64 must reproduce the independently audited ID-2W3R1
prefix.  Beginning at issue65, exactly one residual direction is incremented
per issue:

1. p04-minus depth6, then hold (minimum headroom 97.0 A);
2. p04-minus depth12, then hold (95.2 A);
3. p04-minus depth6 then p07-plus depth4, then hold (95.8 A);
4. p04-minus depth8 then p07-plus depth4, then hold (95.2 A).

The horizon remains 104 issues and the terminal window remains states96--104.
Exact Card15 enumeration must reproduce the quoted headrooms and every per-
coil step must remain `<=0.3 A`.  The runner's clipping cannot be used.

## Gates and route

All ID-2Y1 runtime, observability, boundary, Ip, current, queue/effect,
successor-cap, preissue clearance, raw, storage and nominal-hold gates remain
unchanged.  A branch may allow the next independent reset only for the frozen
preissue `PULSE_CLEARANCE_R/Z/IP` reasons; any other failure aborts.

At least one branch must complete and satisfy the states96--104 nominal hold
gate.  PASS is only a finite Nominal-H1 candidate requiring fresh
repeatability and bounded-tube recourse qualification.

A clean scientific FAIL ends the manual ramp-depth route.  The successor must
be an explicit bounded sequence/control-utility optimizer or measured-feedback
design, not another ramp-depth repair, micro-probe ladder, or larger neural
model.  Model fitting, calibration, blind holdout, expert/BC/DAgger/RL/fixture
use, controller deployment, recovery, waypoint, crossing and adaptation are
forbidden in ID-2Y1R1.

