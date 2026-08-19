# R_geo/Z_geo 1 ms ID-2Z14 early remaining-basis capture result

Date: 2026-08-20 (Asia/Shanghai)

## Final classification

ID-2Z14 is final as
`ONE_MS_ID2Z14_REMAINING_MEASURED_BASIS_NO_CAPTURE_CLOSE_SOURCE_LOCAL_GRAMMAR`.
This is a clean finite action-grammar/scientific FAIL. It is not a runtime,
TSC, prefix, Card15, raw-integrity, replay, reporting, controller, global-
reachability or plant-unreachability failure.

The executed implementation identity is
`cfc2697a714a8431c132b3c8139063619286abd1`; the frozen config SHA-256 is
`a7084ee9817eb3fb6e7567f812b3909cb84215a471ab10f44a4126e8af19ca31`.
Before any plant advance, server testing exposed and repaired a reporting
implementation defect: the first implementation inherited ID-2Z11's
hard-coded 78-state completeness rule, while the frozen ID-2Z14 horizon
requires 66 states. No TSC identity had been consumed. The corrected code
derives state count and capture thresholds from the frozen ID-2Z14 config.

## Execution and evidence

- server focused tests: `10/10` PASS;
- all server one-ms tests: `512/512` PASS;
- zero-TSC static action matrix: `9/9` PASS;
- authentic rollouts: `10/10` complete, with zero guarded stops;
- resets / verified advances / states: `10 / 650 / 660`;
- required artifacts: `3300`, `38869329840` bytes;
- raw inventory digest:
  `7d9059039eb9329c52c08edbdd0ddb0a2aff4efe96eb8c8a4df11166d0a770d1`;
- selected-arm fresh replay: exact PASS;
- independent raw reparse: PASS with no failures and the same final route.

The primary result SHA-256 is
`6544885e271e2a93a03a50e65da72aedca0f305319a63b700121398c78f3711c`.
The independent raw audit SHA-256 is
`72d39e2793f928d038776aa066a97192a0b2ce69780b4033c480a498e6025532`.
All 14 downloaded compact/log files matched their server SHA-256 values.

## Scientific result

The matched hold's six-state terminal worst normalized score was
`5.465720293`. Four B/F arms improved that score, but none captured:

| arm | score | max distance | max speed | max source-Ip offset |
|---|---:|---:|---:|---:|
| `b8` | 5.095659 | 34.157259 mm | 0.509566 m/s | 1.36602% |
| `f8` | 5.153868 | 31.120736 mm | 0.515387 m/s | 1.66800% |
| `b4f4` | 5.036251 | 32.342966 mm | 0.503625 m/s | 1.51674% |
| `f4b4` | **4.906280** | **32.258942 mm** | **0.490628 m/s** | **1.51172%** |

`f4b4` was selected and its fresh replay was exact. All six terminal states
had to satisfy `25 mm`, `0.1 m/s` and `5%`; the selected arm remained far
outside both geometric and speed gates.

The two newly admitted action directions did not improve hold. P01-plus
`i4h4` scored `5.779083`, P01-minus `j4h4` scored `5.472867`, p09-plus
exact-return `k4r3` scored `5.648199`, and p09-minus exact-return `l4r3`
scored `5.458305`. These observations reject only the frozen cumulative-p01
and dwell/return-p09 macros at the exact state-33 history. They do not prove
that every 14-D action, time-varying nominal, longer feedback law or global
two-axis path is unreachable.

## Route decision

The measured source-local B/F/p04/p01/p09 macro family is closed. Do not add
nearby roots, more depth, a second decision, a denser mixture, a larger model
or a relaxed capture gate. The next work is a bounded zero-new-TSC nominal,
authority and reachability review that treats all ID-2Z1--Z14 results as
design evidence. It must choose a materially different construction or
state a finite blocker before any further TSC. Model fitting, calibration,
holdout, controller issue, Recourse-L1, waypoint/path and R_mid crossing
remain blocked.

## Retention

After the independent audit and all server/local compact hashes matched,
only the exact remote ID-2Z14 `rollouts/` subtree was removed. That raw tree
was `39471264843` bytes and is not recoverable from the server. The server
compact files, local compact copies, inventory digest and audit remain.
Server free space after cleanup was `118108672000` bytes.
