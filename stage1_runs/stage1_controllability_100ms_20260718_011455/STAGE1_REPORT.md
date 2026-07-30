# Stage 1 — TSC/RZIP controllability and 100 ms reachability report

- Verdict: **PASS_TERMINAL_1X**
- Interpretation: At least one real-TSC sequence is inside the 1x R/Z target tube at 100 ms.
- Real-TSC validations: 12 successful / 12 total

## Baseline

- Initial state: `{'R': 0.743600216, 'Z': 0.0162365614, 'Ip': 31286.4059}`
- Zero-action terminal state: `{'R': 0.703815205, 'Z': 0.0735284023, 'Ip': 30730.6695}`
- Baseline repeat spread: `{'R': 0.0, 'Z': 0.0, 'Ip': 0.0, 'vessel_current_total_a': 0.0, 'vessel_current_abs_sum_a': 0.0}`

## Local system identification

- Recommended spatial coil-mode count: `8`
- Singular values: `[0.0823342052677587, 0.0675369580562071, 0.011445662248024376, 0.0019501544957699658, 0.0015453813169868974, 0.0007406720680757118, 0.0004818375473464739, 0.00030431551848401835, 0.00021319969002988863, 0.00017407744735988803, 0.00015273316687873365, 0.00010736281037323859, 7.262263154627507e-05, 6.361925773587243e-05]`
- Median response-fit nonlinearity residual: `0.07867930621279634`

## Best nonlinear TSC validation

- Candidate: `full14_target1p00`
- Sequence scale: `1.0`
- Terminal R error: `-0.02038313199999997` m
- Terminal Z error: `0.0209815834` m
- Minimum normalized R/Z distance: `0.2181538882527314`
- Terminal normalized R/Z distance: `0.3656541467229866`
- First step within 2x tube: `0`
- First step within 1x tube: `0`
- Terminal velocity: `0.32019543477574086` m/s

## Interpretation rules

- PASS_TERMINAL_1X: a real-TSC candidate is inside the 1x tube at 100 ms.
- PASS_REACHED_1X_TRANSIENT: a candidate reaches the 1x tube but does not remain there.
- PROMISING_REACHED_2X: a candidate reaches the 2x tube.
- PROMISING_LARGE_REDUCTION: substantial real-TSC distance reduction without tube entry.
- FAIL_OR_INCONCLUSIVE: current local model/action limits/horizon do not produce enough progress.

The real-TSC validation is the source of truth; the local linear prediction is diagnostic only.
