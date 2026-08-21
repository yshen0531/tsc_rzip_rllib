# Fixed-1000 Authority A0 result

## Verdict

`ONE_MS_NR1000A0_SEQUENTIAL_AUTHORITY_PASS_FEEDBACK_RECOURSE_DESIGN_ONLY`

A0 completed all six authentic rollouts and all 360 preregistered one-ms
advances.  The independent raw audit reconstructed 366 states, 360 actions
and 354 observed-slew transitions with no failures.  The full positive path
replay was exact for checked R/Z/Ip, 14-coil, 48-wire and semantic artifacts.

## Sequential decisions

The frozen V0 nominator made decisions only from the current exact observation,
the causal history and the preregistered relative waypoint:

- positive path, issue 24: `even_minus`; measured h8 progress `0.283506 mm`;
- positive path, issue 36: `even_minus`; measured h8 progress `0.274585 mm`;
- negative path, issue 24: `odd_minus`; measured h8 progress `0.679603 mm`;
- negative path, issue 36: `even_minus`; measured h8 progress `0.277269 mm`.

All 24 h4/h8 R/Z/Ip components were contained by the frozen V0 intervals.
The second negative-path choice is important: after the observed first macro
and natural evolution, the remaining error pointed mainly toward positive R,
so the controller did not blindly execute the originally imagined negative-R
second action.

## Boundary of the result

This is a finite two-decision Authority-L0 PASS.  It proves that the fixed
model can nominate control-aligned, exact-return local actions twice in the
tested fixed-1000 histories.  It does not prove absolute waypoint tracking:
the q0 trajectory itself drifts by several millimetres while each radial
macro contributes only about 0.28 mm at h8.  It also does not prove capture,
hold, Recourse-L1, disturbance robustness, arbitrary paths, position
generalization or R_mid crossing.

The next control experiment must therefore track a prospectively reachable
time-indexed q0-relative path, use exact observations to replan at every macro
boundary, and retain an independent hard abort/continuation contract.  It
must not claim that these small local macros cancel the absolute q0 drift.

## Evidence identity and reporting correction

- execution revision: `7a945d7c77172437665195659d0acdda012ea0f0`;
- raw-audit boundary correction: `ca9e008a59b286af90a956dc66fc924ce090f649`;
- result SHA-256: `2fd2fadbbfed28d99ea9a73f153ebcfd41860f98b1373dfb9cc2e6a8399852e2`;
- independent SHA-256: `546ac5d1fe6cbadf0ad0f153bd054e198c84c6d38b6e5e07142d9657a7ae5fc7`.

The first independent audit incorrectly compared the final common-prefix
state directory's rewritten outgoing `inputa`.  Raw TSC and the primary
verdict were unchanged.  The failed audit was preserved on the server; the
reporting-only correction excludes only that outgoing file at the divergence
boundary and then passes all raw checks.

