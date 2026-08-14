# R_geo/Z_geo 1 ms ID-0 vector/tail result

Date: 2026-08-14 Asia/Shanghai

Frozen identity: `rgeo-zgeo-1ms-id0-vector-tail-v1`

Implementation revision: `38b3a22ebc22e87b1c22b4422316bd50fe985855`

Package revision: `25e393ea` with installed payload digest
`db61529bca8962f4d15aa0c94a19c7b8957569647c6c0dfd68631637d3fc8d57`.

## Result

The final route is:

```text
ONE_MS_ID0_TAIL_HORIZON_INSUFFICIENT_REDESIGN
```

This is a clean finite identification-design result. It is not a runtime,
deployment, Card15, current, boundary, raw-integrity, repeatability, vector-
authority, controller, recovery, MPC or plant-unreachability failure.

The complete fresh attempt produced:

```text
rollouts / reset calls                         20 / 20
advance attempts / gotsc / verified       400 / 400 / 400
raw states                                           420
required artifacts                              2,100
required artifact bytes                24,735,028,080
raw inventory SHA-256     ecce4ee398b99cce3c4bc822ba14f9a232f9ba7c9afcac4538f3a2af79e1b6ef
execution / raw / repeatability              PASS / PASS / PASS
signed signal / Ip / vector geometry         PASS / PASS / PASS
tail closure                                                FAIL
```

Independent server-side reparse of all 420 states and 2,100 artifacts passed
with zero failures and reproduced the exact primary route and metrics.

## Vector evidence

The six actual early signed response columns have R/Z rank 2. The best
two-column pair is `p03:plus` with `p07:minus`, condition
`2.0870211406380474`. The maximum angular gap of the six normalized response
rays is `132.32694820821953 deg`, below the frozen `170 deg` cap. Every arm
exceeded the `0.02 mm` signal floor, and maximum q0-relative Ip response was
only `17.235--28.2981 A`, far below the `150 A` cap.

These are source-local descriptive response-cone results. They do not prove
superposition, global controllability, position dependence, controller-safe
action tubes or recovery.

## Exact tail failure

At state20 every early arm already satisfied the absolute terminal R/Z norm
cap (`0.05 mm`) and terminal Ip cap (`10 A`). The only failed tail clause was
the frozen terminal/peak ratio `<= 0.20`:

```text
p03 plus     0.2449686034     FAIL
p03 minus    0.1918341629     PASS
p04 plus     0.2120169068     FAIL
p04 minus    0.1457176063     PASS
p07 plus     0.1871750643     PASS
p07 minus    0.2149836096     FAIL
```

The failed ratios are close to the gate but the gate is not weakened after
observation. ID-0 therefore cannot yet freeze an adequate memory/tail window
or authorize model fitting. The next discriminator should extend the same
early pulse-return histories with fresh matched q0 baselines rather than add
model capacity or new action directions.

## Interrupted deployment attempt

The first launcher attempt lost its SSH orchestration session after two
complete q0 baselines. It has no result, was not merged into the final
campaign, and remains preserved remotely as deployment-attempt evidence. Both
baseline rows were individually complete (`20/20` verified advances, no
reasons), so this is an incomplete deployment/orchestration attempt rather
than a TSC or plant failure. The final attempt reran the unchanged committed
code/config from a fresh output identity and completed all 20 rows.

## Evidence identity and data role

Local compact directory:

```text
docs/codex/audits/rgeo_zgeo_1ms_id0_result_20260814_38b3a22e/
```

Its 23 JSON files match the remote compact set at aggregate SHA-256
`787ba9c2ab44f57a4cb29cf4da2bd1e3a00f3714df10f3e86394ec634ab7f5a8`.
Primary result SHA-256 is
`e8191c6dd253f0d528f9db4d9e028d7cfda53a07390c265cbd12f670e8951c4d`;
independent audit SHA-256 is
`b6151817990e07c2ba56906c280f911d6a889df2554c8826c9fa66ff30146356`.

Raw remains on the server and was not downloaded. Because the complete
scientific gate did not pass, ID-0 remains consumed design evidence only. It
may guide the prospective longer-tail experiment, but it is not model-fit,
calibration, holdout, expert, Oracle, fixture, BC, DAgger, RL, controller-
safety or recourse data.

## Next route

Freeze a small ID-0T1 longer-tail campaign: two fresh q0 baselines plus one
fresh replay of each of the six early signed arms, identical pulse at issue2
and exact q0 return at issue3, extended to state32. It must reproduce the
ID-0 prefix through state20 at the frozen repeatability tolerances, retain all
hard execution/raw gates, and evaluate the unchanged tail closure criteria at
state32. This is a tail-window discriminator only; it does not add action
directions or authorize model fitting unless it passes.
