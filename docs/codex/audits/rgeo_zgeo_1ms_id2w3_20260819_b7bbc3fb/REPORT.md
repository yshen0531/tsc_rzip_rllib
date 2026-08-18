# ID-2W3 p03 braking/hold result

Date: 2026-08-19

Implementation revision: `b7bbc3fb98a462425212007bf37bad2da63b8c28`

Official route: `ONE_MS_ID2W3_EXECUTION_OR_INTERFACE_FAIL_STOP`

## Result

The server completed the `p03_level52_hold` prefix through issue 78 and
retained 80 states (1100--1179 ms), 79 issued actions and 400 required raw
artifacts. The independently parsed raw audit passed with no discrepancies.

Before issue 79, the exact/noiseless current state had reached

- `R_geo - R_geo(source) = -0.0253510045 m`;
- `Z_geo - Z_geo(source) = +0.0184870145 m`;
- `Ip - Ip(source) = +507.3725 A`.

The preregistered 25 mm per-axis novel-issue clearance therefore produced
`PULSE_CLEARANCE_R`. Issue 79 and every later action were refused. The last
issued Card15 target equalled the preceding target, the issued delta was zero,
and the observed 14-coil current delta was zero. This is not an actuator,
queue, Card15, readback, solver, raw or reporting failure.

The second preregistered `p03_level64_hold` branch was not started because the
implementation stops the campaign after the first incomplete rollout. Hence
ID-2W3 did not reach its terminal states 88--96 and did not produce a
scientific p03 hold PASS or FAIL. It is a finite empirical-envelope stop.

## Route consequence

ID-2W3 is consumed and must not resume or rerun. Its unstarted level-64 branch
may be executed only under a new identity with the same already-frozen action
stream, envelope and terminal hold gates. That separate run does not repair or
reinterpret ID-2W3.

No model was fitted, and no calibration, holdout, controller, expert, BC,
DAgger, RL or fixture data was produced. Raw remains on the server and is
represented locally only by the compact/result/audit/log evidence in this
directory.
