# ID2Z37 fresh engineering-event qualification result

Date: 2026-08-21

## Final route

`ONE_MS_ID2Z37_FRESH_CALIBRATION_FAIL_CLOSE_EVENT_BOX_ROUTE`

ID2Z37 completed the prospectively frozen phase-48 calibration and exact
replay layer, then stopped before opening phase-54 blind validation. This is a
clean finite model-qualification failure, not a runtime, package, interface,
raw-data, replay, controller, Authority-L0, capture or Recourse-L1 result.

## Execution and integrity

- implementation revision:
  `d552379737c9541e8f41770a0a1af9e0bfa6dab7`;
- server validation before execution: focused `6/6`, complete one-ms suite
  `712/712`, offline preflight PASS with zero plant advances;
- calibration/replay execution: `6/6` complete rollouts, `438/438` attempts,
  TSC calls and verified advances, `444` states;
- raw inventory: `2,220` required artifacts, `26,148,458,256` logical bytes,
  digest `9ec32962eaac03627924aa4eb343dd4db4bf0ee9abae9c8ac656d8c39da12ffd`;
- exact q_Z-plus replay PASS; all prefix, Card15, execution and raw gates PASS;
- structurally independent raw audit PASS with no failures and the same route;
- phase-54 blind rollouts: `0`; model fits or updates: `0`; ID2Z35 fit rows: `0`.

Primary and independent SHA-256 are respectively
`1a14f7013726a55b13714d223102c6b2fa45a50b4ec58c3d50e3cc5c767b206d`
and
`d4acb6bc64d4ba120d5e8325c9f7d2c74843e50e8e72855a0e3bbe8f6e57aacc`.

## Scientific failure

The fixed q_R-minus/effect-age-13 engineering event box contained its sole
fresh event observation (`1/1`). The failure was instead in cells frozen as
ordinary point responses:

- maximum non-event R error: `0.639621250 mm > 0.050 mm`;
- maximum non-event Z error: `0.111249500 mm > 0.050 mm`;
- maximum non-event Ip error: `7.10555 A < 25 A`.

The largest R and Z residuals occurred in the minus branches. The computed
would-be non-event half widths, before application of the frozen caps, were
`0.800526563 mm`, `0.140061875 mm` and `8.88294 A`. Thus the failure is not a
small miss of the already enlarged event cell: the sparse decomposition
itself does not transfer to the fresh phase-48 family.

No observed value may be used to widen the box, refit the payload or open the
blind family. ID2Z37 rows retain zero fit weight.

## Route decision and cleanup

Per the preregistered stop rule, the ID2Z34--ID2Z37 sparse event-box route is
closed. No adjacent phase, wider box, third point/event model or retrospective
use of calibration data is authorized. The project pauses for a higher-level
route review before any new model or TSC identity.

After compact recovery and independent audit PASS, only this run's exact
`rollouts/` subtree was removed from the server, releasing
`26,552,831,713` filesystem bytes. The server retains the top-level compacts,
offline evidence and log; the same files were recovered locally with matching
SHA-256 under
`docs/codex/audits/rgeo_zgeo_1ms_id2z37_20260821_d5523797_v1/`.

The final goal remains unchanged: causal, safe, history-continuous two-axis
R_geo/Z_geo waypoint/path tracking from the fixed 1100 ms takeover, with exact
per-cycle R_geo/Z_geo/Ip observations, hard Card15/current/slew/Ip constraints,
qualified fallback/recourse, and eventually bidirectional repeated R_mid
crossing. ID2Z37 does not qualify any part of that controller.
