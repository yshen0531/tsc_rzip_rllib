# ID-2Z19R1 zero-fit attribution result

## Identity and integrity

The attribution implementation was frozen after the ID-2Z19R1 scientific
FAIL and before row-level attribution was emitted. Server validation passed
`4/4` focused tests and `589/589` complete one-millisecond regression tests.
The accepted output SHA-256 is:

```text
9d6982ccda50f7ef8981aaff1341f321c945712ccbec1316c5ff9ec415bbf882
```

It authenticated the frozen result, independent audit and `9,408`-row OOF
ledger by SHA-256. It fit or updated zero models, read zero calibration or
blind-holdout records, and made zero TSC calls, resets or plant advances.

## Attribution

The terminal failure is common to both candidate classes and is not explained
only by held-family support:

```text
                                             structured       + TCN
terminal velocity FAIL folds                       8/8          8/8
terminal increment FAIL folds                      8/8          8/8
support PASS folds                                 7/8          7/8
R terminal-increment rows above 0.5 mm             196          197
informative paired R/Z wrong-direction cells        18           22
```

The over-cap rows recur at 17 endpoint issues:

```text
19, 20, 30, 31, 37, 41, 42, 43, 44, 46, 53, 55, 56, 59, 60, 63, 65
```

The largest structured-model R terminal misses are `0.732 mm` at the
supported `d00_minus` endpoint 30, `0.705 mm` at supported `d05_minus`
endpoint 30 and `0.698 mm` at supported `d03_minus` endpoint 30. The TCN
counterparts are `0.734`, `0.701` and `0.710 mm`. Thus the accepted support
coordinate cannot turn the failure into a single OOD-family explanation.

The negative paired-direction cells include early event cells in d00--d04
and a longer cluster across d05 origins/horizons. The attribution reports the
observed issue/horizon pattern but does not assign an unobserved physical
mechanism. Aggregate response NRMSE and positive-direction fractions are
therefore insufficient qualification statistics for the terminal control
target.

The TCN relative gate remains failed: worst paired-response improvement is
`-0.1420213` and maximum componentwise critical regression is `0.3586143`.
This rejects the claim that the fixed nonlinear residual repaired the shared
terminal/event error.

Final route:

```text
ONE_MS_ID2Z19R1_ATTRIBUTION_COMMON_TERMINAL_INCREMENT_MODEL_CLASS_FAIL_AUTHORITY_AXIS_AND_TARGETED_REDESIGN_REQUIRED
```

## Consequence

ID-2Z19R1 calibration and blind holdout remain closed. The two candidates,
a third model, larger network, grid search and post-result gate changes are
closed. The result does not prove global unpredictability or plant
unreachability. It says the current development support and these two frozen
model forms do not qualify the control-relevant terminal increment/speed map.

The next decision must return control utility to the foreground. A bounded
exact-TSC authority/recovery discriminator should be designed independently
of the failed model and should produce matched, prospectively fit-eligible
sequence-outcome evidence only if its action grammar shows sustained control
utility. Any later predictor should target terminal increments/event phase
and candidate value under that grammar, with fresh whole-history
development/calibration/holdout identities. It must not reuse c00--c03 or
v00--v03 under the failed ID-2Z19R1 identity.

