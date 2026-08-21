# ID2Z35 fresh event-set qualification result

Date: 2026-08-21

## Result

ID2Z35 completed its preregistered calibration layer and stopped before the
blind layer, exactly as required by the staged contract.

- implementation revision: `2b6adb1c311da59b66537c4f6d8a49f72d58a627`
- server focused tests: `6/6`
- server complete one-millisecond regression: `703/703`
- calibration/replay rollouts: `6/6`
- verified plant advances: `438/438`
- reparsed states: `444`
- required artifacts: `2,220` files / `26,148,458,256` logical bytes
- raw inventory digest:
  `5259c835a8581b794c70f6076d8a77a3bef497ace1806b5972c39bc89a27da37`
- primary result SHA-256:
  `f7e29710d19ffe230d8b523f431cd4d3063c61e96b911a8985acf2a17125d077`
- independent audit SHA-256:
  `dbd92d91d2497cab21ce79e80474220d6d7d955214952fa1fa494b49a5d3200b`
- independent raw audit: PASS, zero failures
- final route:
  `ONE_MS_ID2Z35_FRESH_CALIBRATION_FAIL_STOP_BEFORE_BLIND`

The phase-54 blind family was not run and remains unread.

## Scientific failure

The frozen ID2Z34 payload contained one set-valued cell,
`q_r:minus/effect-age 13`. The single phase-52 observation was not contained
by that three-output box, so calibration failed `0/1` for the event cell.
The response was:

```text
R_geo  +0.2838485 mm
Z_geo  +0.0132810 mm
Ip     +1.4540 A
```

The frozen event interval was:

```text
R_geo  [-0.4011362, +0.3032517] mm
Z_geo  [+0.0224244, +0.1294766] mm
Ip     [+1.6480, +9.4138] A
```

Thus R was contained, while Z missed the lower edge by about `0.0091434 mm`
and Ip missed it by `0.194 A`. This is a real qualification failure; the box
may not be widened retrospectively and the result may not be changed to PASS.

The failure is also narrow. Across the other 67 response cells, the maximum
absolute errors were only `0.021134/0.034790 mm` R/Z and `2.23235 A` Ip.
Exact q_Z-plus replay, execution, prefix, Card15, raw and independent-audit
gates all passed. The evidence therefore rejects the particular two-phase,
componentwise min--max event box. It does not show runtime randomness, a
generic smooth-response failure, loss of all task-plane authority, or a
controller failure.

## Data and authorization boundary

ID2Z35 was a qualification identity. Its four calibration branches and replay
retain zero fit weight under this route; they must not be used to refit or
resize the frozen ID2Z34 payload. The unopened phase-54 values are not inferred
or reported. No feedback, Authority-L0, capture, recovery, Recourse-L1,
waypoint/path or R_mid-crossing execution is authorized.

After byte-for-byte compact recovery and the independent raw PASS, only the
remote run's `rollouts/` subtree was removed. The removed filesystem size was
`26,552,858,293` bytes. Top-level compacts, result, audit and log remain on the
server and in the tracked audit directory.

## Next route

Do not rerun ID2Z35 and do not tune its event interval from the calibration
miss. A successor may use the failure only as route/design evidence. The next
bounded step is one new-identity, prospectively frozen robust-event model whose
minimum event widths come from pre-existing engineering caps rather than the
observed miss, followed by entirely fresh calibration and blind phases. One
candidate only; no width search. If either fresh layer fails, close this
point-plus-sparse-event-box route instead of opening another adjacent-phase or
capacity ladder.
