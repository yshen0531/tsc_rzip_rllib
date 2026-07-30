# Stage 1.1 — controllability supplement report

- Verdict: **PASS_DAMPED_HOLD_40MM**
- Interpretation: No candidate passes the ±30mm precise-hold gate, but at least one passes the damped ±40mm gate.
- Successful candidate validations: `9`

## Identification reliability

- Successful scan experiments: `563`
- Failed scan experiments: `0`
- Reliability verdict: `True`
- Recommended mode count: `3`

## Zero-action reference

- Terminal R error: `-46.185` mm
- Terminal Z error: `73.528` mm
- Terminal Euclidean R/Z error: `86.830` mm
- Terminal velocity: `0.701` m/s

## Best Stage1.1 real-TSC candidate

- Candidate: `svd04_target1p00`
- Sequence scale: `0.75`
- Terminal R error: `-28.911` mm
- Terminal Z error: `37.210` mm
- Terminal Euclidean R/Z error: `47.122` mm
- Terminal velocity: `0.069` m/s
- Late velocity RMS: `0.072` m/s
- Terminal distance reduction vs zero action: `45.7`%

## Candidate comparison

| Candidate | Scale | Terminal error (mm) | Terminal velocity (m/s) | Late velocity RMS (m/s) | trailing ±30 mm steps | Reduction vs zero |
|---|---:|---:|---:|---:|---:|---:|
| svd02_target1p00 | 0.75 | 48.451 | 0.071 | 0.076 | 0 | 44.2% |
| svd02_target1p00 | 0.85 | 43.543 | 0.157 | 0.117 | 0 | 49.9% |
| svd02_target1p00 | 1.00 | 36.185 | 0.306 | 0.237 | 1 | 58.3% |
| svd03_target1p00 | 0.75 | 47.267 | 0.070 | 0.071 | 0 | 45.6% |
| svd03_target1p00 | 0.85 | 42.234 | 0.161 | 0.124 | 0 | 51.4% |
| svd03_target1p00 | 1.00 | 34.785 | 0.309 | 0.251 | 2 | 59.9% |
| svd04_target1p00 | 0.75 | 47.122 | 0.069 | 0.072 | 0 | 45.7% |
| svd04_target1p00 | 0.85 | 42.133 | 0.158 | 0.124 | 0 | 51.5% |
| svd04_target1p00 | 1.00 | 34.560 | 0.307 | 0.252 | 2 | 60.2% |

## Gate rules

- Step 0 is excluded from reach and consecutive-stay metrics.
- Precise pass: terminal and required trailing steps inside ±30 mm, terminal velocity ≤0.10 m/s, late velocity RMS ≤0.10 m/s.
- Relaxed damped pass: the same damping requirements inside ±40 mm.
- Position-only means the trajectory reaches/stays in the position tube but is still moving too quickly.
- Real TSC is the source of truth; local-linear predictions are diagnostic only.

## Read-only Stage1 reference

The original full14/SVD5/SVD6/SVD8 real-TSC results were re-scored with the same strict metrics and are stored at:

`source_reference/validation_summary_strict.csv`
