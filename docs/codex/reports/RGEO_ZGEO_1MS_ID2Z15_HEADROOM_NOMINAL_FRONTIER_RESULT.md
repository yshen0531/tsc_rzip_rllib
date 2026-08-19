# R_geo/Z_geo 1 ms ID-2Z15 headroom nominal frontier result

Date: 2026-08-20 (Asia/Shanghai)

## Execution identity

- implementation revision: `168597c10b76be25aeeabe627e725269149ca0c2`
- server run: `rgeo_zgeo_1ms_id2z15_20260820_168597c1_v1`
- server focused tests: `11/11`
- server all-one-ms tests: `523/523`
- authentic rollouts: `7/7`
- verified plant advances: `336/336`
- retained states before audited cleanup: `343/343`
- required artifacts: `1715/1715`
- required artifact bytes: `20,200,272,932`
- inventory digest: `705dc016d5c2bddf07ea2ff3ebc1239773ddb3750067a299fecead8744208ac1`
- selected replay: exact
- independent full-raw audit: PASS, zero failures
- model/calibration/holdout reads: `0/0/0`

The result and independent-audit SHA-256 values are respectively:

```text
4041dd1443e1438a77074047643a709bc69abd88db5e63546b853c2f5a98f1e9
853836acb4af4e5ede983f00adeca0a924847957415e77df9cbaf36f9b320ae8
```

After compact/log hashes matched the server and the independent raw audit
passed, only this stage's exact `20,514,235,711`-byte remote `rollouts/`
tree was removed. Compact evidence and logs remain on both sides. Server
free space returned to `118,106,660,864` bytes.

## Frozen scientific result

All six branches completed without a guarded safe stop. Terminal worst
normalized score decreased monotonically with the effective p03-forward
allocation except that duty50 differed slightly from constant f50:

| arm | score | max distance | max speed | max Ip fraction |
|---|---:|---:|---:|---:|
| q0 | 9.526817 | 43.1326 mm | 0.952682 m/s | 1.48439% |
| f25 | 8.571508 | 39.6914 mm | 0.857151 m/s | 0.81761% |
| f50 | 7.496522 | 35.1377 mm | 0.749652 m/s | 0.24584% |
| f75 | 6.634835 | 31.4420 mm | 0.663483 m/s | 0.82972% |
| f100 | 6.131468 | 26.8068 mm | 0.613147 m/s | 1.73569% |
| duty50 | 7.292881 | 34.2307 mm | 0.729288 m/s | 0.22995% |

`f100` was selected and replayed exactly. It improved score over q0 by
`3.395349`, but improvement over the full-F endpoint is definitionally zero.
It failed six-state capture and cannot reserve fractional-F slew. No
fractional or duty arm beat both endpoints by the frozen `0.10` margin.

Final route:

```text
ONE_MS_ID2Z15_CONSTANT_HEADROOM_NOMINAL_INSUFFICIENT_SEQUENCE_REACHABILITY_REQUIRED
```

## Interpretation and route decision

This is not an execution, raw, replay, Card15, current or reporting failure.
It cleanly rejects the finite hypothesis that a constant fractional or 50%
duty p03-forward nominal can trade a little transport performance for a
better residual-identification corridor under the frozen endpoint utility.
It does not prove global unreachability or that full-F has no useful
time-varying continuation.

The evidence instead supports a sequence problem. Full-F is still the best
measured takeover transport, but its state-32-to-48 hold accelerates again;
the best f100 instantaneous normalized score occurs near state 35 rather
than the terminal window. The next stage may therefore use an algorithmic,
bounded sequence/reachability construction around the exact full-F prefix.
It may not add another constant fraction, reinterpret relative improvement
as capture, fit ID-2Z15 data, or reopen the closed late pulse ladder.

## Claim boundary

ID-2Z15 is finite canonical-source nominal evidence only. It is not a
controller, recovery policy, terminal set, waypoint/path result, R_mid
crossing result or global plant-reachability theorem.
