# ID-2W3R1 level-64 hold result

Date: 2026-08-19

Implementation revision: `37c031679925dba50f73e6fecb312faca70f8050`

Official route: `ONE_MS_ID2W3R1_EXECUTION_OR_INTERFACE_FAIL_STOP`

## Result

The one authorized level-64 branch completed 86 plant advances and retained
87 states (1100--1186 ms) plus 435 required raw artifacts. The independent
full-raw audit passed and reproduced the counters, inventory and route.

Before issue 86, the exact current source-relative state was

- `R_geo = -0.0253166755 m`;
- `Z_geo = +0.0134718540 m`;
- `Ip = +736.7572 A`.

The frozen 25 mm R pre-issue clearance therefore returned
`PULSE_CLEARANCE_R`; issue86 and all later actions were refused. The last
issued target equalled the preceding level-64 target and both issued and
observed 14-coil deltas were zero. No Card15, queue, readback, current,
runtime, TSC, solver, raw or reporting defect was found.

The branch stopped before states88--96, so it did not produce a terminal hold
PASS. Together with ID-2W3's level-52 clearance stop, it closes the frozen
p03-only nominal/hold route. This is a finite source-envelope result, not a
global authority, recovery, controller, path or reachability conclusion.

No model was fitted and no calibration, holdout, expert, BC, DAgger, RL or
fixture data was produced. The raw tree remains on the server; this directory
contains only compact/result/audit/log evidence.
