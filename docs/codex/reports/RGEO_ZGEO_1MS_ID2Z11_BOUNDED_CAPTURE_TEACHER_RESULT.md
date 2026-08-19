# R_geo/Z_geo 1 ms ID-2Z11 bounded capture teacher result

Date: 2026-08-20 Asia/Shanghai

## Verdict

ID-2Z11 is final as:

```text
ONE_MS_ID2Z11_BOUNDED_GRAMMAR_NO_CAPTURE_AUTHORITY_REVIEW
```

This is a clean finite action-grammar/capture FAIL. It is not a runtime,
package, prefix, Card15, raw, independent-audit, replay, controller,
recovery, waypoint or global plant-reachability failure.

## Execution and evidence integrity

The server executed exactly the frozen identity at source revision
`fc926090d57259d9410cd051b94cb26b0d5d036a`:

```text
reset calls / rollouts                       17 / 17
verified plant advances                  1309 / 1309
required raw artifacts                    6630
required raw bytes                         78,092,017,224
raw inventory SHA-256                      dc9c13f0e0e7e44fcfdb1a098713fcfe06616bcf11072f34331276acdc0061e2
execution integrity                        PASS
raw integrity                              PASS
independent raw audit                       PASS, zero failures
```

The fresh selected-path replay was exact. No model was fitted, no
calibration or holdout record was read, and no retry or extra branch ran.

## Measured teacher decisions

At state 49 the selected arm was `b8`:

```text
hold score                                  4.175530
b8 score                                    3.954112
b8 improvement                              0.221418
```

Only the first four `B` issues were committed. At the resulting main state
53, the selected arm was `b4f4`:

```text
hold score                                  4.240327
b4f4 score                                  3.316339
b4f4 improvement                            0.923988
```

The non-nested state-53 history was produced by the preregistered `f8`
parent rule. The same `b4f4` arm improved its matched hold score by
`0.360163`, so the measured utility was not confined to the selected arrival
history. This remains support for one finite action grammar, not history
generalization.

The signed complements did not rescue capture. At the root, `u4h4` and
`p4h4` worsened the score by `0.393720` and `0.554299` relative to hold. At
the main state, `u4h4` worsened by `0.012714` and `p4h4` improved by only
`0.019066`, below the frozen `0.02` nomination gate.

## Capture failure

The selected main `b8 -> b4f4` path did not satisfy any six-state capture
claim. Over terminal states 72--77 its maxima were:

```text
source R/Z distance                          29.665859 mm  (limit 25 mm)
one-step R/Z speed                            0.331634 m/s (limit 0.1 m/s)
absolute source-relative Ip fraction          0.027448     (limit 0.05)
```

The score was speed-limited. The exact replay shows that the path briefly
reached `25.880440 mm / 0.141940 m/s` at state 61, but thereafter accelerated
again; states 72--77 remained around `0.298--0.332 m/s` while distance grew
from `28.216` to `29.666 mm`. This is not evidence of an unobserved late
settling trend inside the measured horizon.

## Route decision

The frozen manual H/B/F/U/P macro grammar is closed. In particular:

- do not add another hand-selected depth or one more adjacent root;
- do not fit the rejected response/value models to explain away no capture;
- do not open calibration/holdout or claim Recourse-L1;
- do not infer that all B/F physical authority, arbitrary sequences, two-axis
  control or the plant are globally incapable.

The next stage is a bounded zero-new-TSC authority/nominal/reachability audit.
It must jointly reconsider takeover-to-capture timing, speed and distance,
enumerate the exact feasible signed Card15 allocation polygon rather than
single-token macros, and freeze at most one algorithmic branch-search
campaign. The next real campaign, if authorized, must be algorithmic and
budgeted rather than another manual ladder.

## Claim boundary

The final goal remains fixed-1100-ms, 1-ms exact-RZI, full-causal-history,
exact-Card15 two-axis waypoint/path control under independent hard safety and
recovery, eventually including bidirectional repeated `R_mid` crossing with
continuous belief. ID-2Z11 proves only that this one source-local bounded
macro teacher did not produce a capture seed.
