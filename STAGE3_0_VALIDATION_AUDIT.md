# Stage3.0 validation audit

## Inputs used

- Complete standalone Stage2.2 code package.
- Uploaded completed Stage2.2 run directory containing the six-generation 100 ms corner search.
- Stage2.2 source result: 576/576 successful real-TSC evaluations, no 30 mm strict pass, 153 relaxed passes, and confirmed relaxed-only verdict.

## Static validation

- Stage3.0 Python module and CLI compile successfully.
- All package Python sources compile with `compileall`.
- All JSON configs parse.
- All shell scripts pass `bash -n`.
- No Stage3.0 launcher contains a Git, network, or external source-tree recovery dependency.
- Strict JSON writers reject NaN/Infinity and remove failed temporary files through the inherited JSON-safe base.

## Unit tests

The final package passes **43 tests** in the complete Stage2/Stage2.1/Stage2.2/Stage3.0 suite. **16 tests are Stage3.0-specific**. Coverage includes:

- fixed 15-step/150 ms design validation;
- 120 ms and 150 ms arrival;
- persistence rejection after arrival;
- distinct endpoint and RMS speed thresholds;
- actual relaxed/strict gate endpoint reporting;
- 12 unique tail templates;
- exact frozen first-nine mode coefficients and physical actions;
- 30-feature layout;
- 72 unique two-center finite-difference probes;
- adaptive inward probes at coefficient bounds;
- JSON-safe partial Jacobians with unavailable denominators stored as `null`;
- unavailable Jacobian variables frozen in the SLSQP subproblem;
- 12 bounded SLSQP proposals per center;
- enforced 3/2/2/1 source-nominal category quotas;
- strict JSON rejection of nonfinite values.

## Completed Stage2.2 source integration

Using the uploaded completed Stage2.2 result tree, Stage3.0 successfully:

- validated the source target, 10-step/100 ms horizon, three-mode action space, `[0,2,4,6,9]` nodes, 10 ms interval, and unchanged hard gate;
- recovered the three-mode matrix and initial 14-coil current vector;
- selected exactly:

```text
corner         3
speed_safe     2
gate           2
position_front 1
```

- generated 96 unique screen candidates;
- generated 96 unique strict-JSON-safe real-TSC specs;
- decoded every spec to 15 actions × 14 TSC coils;
- confirmed that all templates for a nominal share exactly the same first nine physical actions.

## End-to-end no-gotsc integration

A deterministic mock evaluator was used only to exercise program flow, not to claim a control result. The code completed:

```text
96-candidate screen
72 finite-difference probes
24 SLSQP proposals
36 controller-identification probes
category-aware confirmation
analysis and report generation
```

The test produced 228 optimization/identification records, exported an 18-row batch gain, and successfully reread every generated JSON and compressed JSON artifact.

## Honest runtime boundary

No real 150 ms gotsc candidate and no 96-worker real Stage3.0 wave was executed in this environment. Therefore this audit does not establish:

- that the current TSC restart chain reliably reaches 1250 ms on the server;
- that the extended horizon yields a 30 mm strict trajectory;
- that the local Jacobian remains accurate across the trust region;
- that the exported batch gain works in causal closed loop;
- robustness to changed initial state, target, noise, or plant parameters.

Those claims require the user's server run and subsequent perturbation tests.
