# Stage4.2R3c3T13 time-resolved model compatibility design V3

## Status

This V3 numerical-contract correction is frozen before the complete raw scan
and before any Stage3.4-Jacobian multiplication. It inherits V2 in full and
changes exactly one input-authentication tolerance.

V2 was deployed and passed tests, but no V2 audit/output identity was
started. A one-file, input-only preflight of the already frozen V2 formula
reported:

```text
file                                s42r3c3_6a335fb38ada7124650e.json.gz
command modal residual              3.8114525424681744e-08 A
observed-current modal diagnostic   0.041245240058860266 A
observed/command diagnostic         0.047641941346228123 A
Jacobian multiplications            0
```

No output trajectory feature, prediction error, comparison, or tier verdict
was computed. This is not a model or scientific outcome.

## Source-derived floating-point bound

`stage4_1r3_control_aware_robustness.py` converts the scheduler's 14-coil
action to `np.float32` before `env.step`. Each normalized action component is
bounded by magnitude one. The maximum componentwise round-to-nearest error is
therefore bounded by approximately `2^-24`. Multiplication by the maximum
`3.0 A` command step gives less than `1.79e-7 A` per coil. A conservative
14-component Euclidean bound is:

```text
sqrt(14) * 3.0 A * 2^-24 < 6.7e-7 A
```

The V2 `1e-9 A` residual gate incorrectly treated a recorded float32 command
as an exact float64 vector in the mode subspace.

## Sole V3 change

Replace:

```text
maximum command out-of-three-mode residual <= 1e-9 A
```

with the source-bounded numerical gate:

```text
maximum command out-of-three-mode residual <= 1e-6 A
```

The new ceiling is above the source-derived `6.7e-7 A` worst-case bound and
is only `3.33e-7` of the 3 A nominal step. It is not a plant/model prediction
threshold and cannot make a Jacobian comparison pass.

All of the following remain bit-for-bit or numerically unchanged from V2:

- 1,408 immutable raw identities and hashes;
- trace-command input definition;
- 576 signed, 896 finite-node, and 32 interaction comparisons;
- all R17-derived absolute output-error gates;
- relative response L2 `<= 0.10`;
- causality and effect-state gates;
- formal arrival and hold times;
- route interpretation and no-new-TSC/non-learning prohibitions.

The complete audit must use a new V3 output identity. Any later input/schema
failure again invalidates the audit; it may not be reclassified as a model
failure.
