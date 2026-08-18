# ID-2Z1 late-action macro utility result

## Identity and execution

- Frozen design/config commit: `8de743bc`.
- Plant implementation commit: `ecb43246de07186d7d2bcd4d0cdc5951c6398685`.
- Reporting-only raw-current compatibility repair: `5d83301d`.
- Remote run directory:
  `artifacts/server_runs/rgeo_zgeo_1ms_id2z1_20260819_ecb43246`.
- Main route:
  `ONE_MS_ID2Z1_LATE_MACRO_UTILITY_PASS_ROLLING_SEQUENCE_DESIGN_ONLY`.

Server validation passed 9/9 focused tests and 394/394 complete one-ms
tests before plant execution.  After the reporting repair it passed 10/10
focused and 395/395 complete one-ms tests.  The explicit offline preflight
reported seven streams, 97.6 A minimum absolute-current headroom, and zero
reset, plant advance, `gotsc`, model fit, calibration, or holdout read.

The real campaign completed exactly:

| quantity | result |
|---|---:|
| canonical resets | 7 |
| attempted / `gotsc` / verified advances | 511 / 511 / 511 |
| retained states | 518 |
| required raw artifacts | 2,590 |
| required raw bytes | 30,506,534,632 |
| raw inventory SHA-256 | `85376c20f157ef5df12d89be50e2bb9ac3b3570afd5cabbe59b8b7715d36abff` |
| complete branches | 7/7 |
| guarded safe stops | 0 |

All paired-boundary, Ip, Card15, issued/readback current, slew, absolute
current, clock, common-prefix, raw inventory, and forbidden-data gates pass.

## Independent audit and reporting repair

The first independent audit attempt happened after all 511 real advances and
failed while recomputing a descriptive current-headroom field.  Primary
compact states retain both `actual_current_a_tsc` and exact decimal current;
the structurally separate raw parser retains the exact decimal form only.
The new diagnostic had incorrectly required the float alias and raised
`KeyError`.  Commit `5d83301d` accepts either representation, checks an exact
14-coil width, and changes no action, state, threshold, route, or plant result.

The zero-new-TSC full-raw rerun then passed with no failures and reproduced
the primary route, counters, prefix checks, utility metrics, file count,
byte count, and inventory digest exactly.  The original background-wrapper
exit-code helper contains the two literal bytes `1n` because of shell quoting;
the main `result.json`, exception log, repaired audit exit code, and all raw
are intact.  This is an outer ledger-format defect, not a TSC or scientific
failure, and the original helper file is preserved.

## Measured macro utility

All values below compare states66--73 with the matched p03-level64 hold
baseline.  Distance improvement is hold distance minus candidate distance.

| arm | peak RZ response (mm) | max paired Ip (A) | persistent improved states | terminal distance improvement (mm) | eligible |
|---|---:|---:|---:|---:|---|
| p03 forward 4 | 0.9798 | 145.0614 | 4/4 | 0.9465 | yes |
| p03 unwind 4 | 0.9574 | 146.9599 | 0/4 | -0.9192 | no |
| p04 minus 4 | 0.6198 | 205.0367 | 4/4 | 0.5281 | no: paired Ip |
| p04 plus 4 | 0.5972 | 202.9571 | 0/4 | -0.5280 | no |
| p07 minus 4 | 0.6853 | 107.5340 | 4/4 | 0.4778 | yes |
| p07 plus 4 | 0.6023 | 109.2830 | 0/4 | -0.0180 | no |

The selected arm is `p03l64_p03forward4_hold4`.  At the decision state65 its
source RZ distance was 24.2238 mm.  Four p03-forward increments kept it at
24.2239 mm at state69, whereas the hold baseline had moved to 24.7199 mm.
After four held issues, state73 distance was 24.6361 mm versus 25.5826 mm for
the baseline.  The selected state73 source offsets were -20.6541 mm R,
+13.4294 mm Z, and +1,220.0705 A Ip.

This proves finite, persistent control utility for two macros at this exact
prefix; it does not prove hold, recovery, two-axis positive span, an arbitrary
sequence, a controller, waypoint tracking, position generalization, or
reachability.  In particular the selected branch still moves about
0.35 mm per final-window step and begins drifting again after its four active
increments.  It is a transport macro, not a terminal hold.

## Route

The single-layer macro screen is complete.  The successor is a prospectively
bounded two-decision rolling branch search.  It replans after the four active
effects at state69 rather than waiting until state73, repeats the same seven
exact macro alternatives, then repeats once more from the selected state73
prefix.  Sibling branches provide exact same-prefix repeatability, and the
selection objective must keep absolute R/Z/Ip reserve as well as reduce
source distance.  This replaces another hand-chosen depth ladder and remains
zero-model route evidence.
