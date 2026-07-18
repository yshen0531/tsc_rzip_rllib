# Stage1.1 validation performed before release

## Static checks

- All Python files compiled with `py_compile` and `compileall`.
- All JSON files parsed successfully.
- All Bash scripts passed `bash -n`.
- ZIP contents were re-extracted and checked independently.

## Synthetic checks

- Original Stage1 synthetic response reconstruction and constrained optimization tests pass.
- Step 0 is excluded from new reach metrics.
- Trailing ±30 mm streak is counted correctly.
- Strict precise-hold verdict logic is tested.
- Explicit validation selection returns exactly nine specs:
  - SVD2 × 0.75/0.85/1.00
  - SVD3 × 0.75/0.85/1.00
  - SVD4 × 0.75/0.85/1.00

## Uploaded-run offline checks

The complete uploaded Stage1 run was copied into a local Stage1.1 dry run and reanalyzed without TSC.

Confirmed:

- 563 expected result files are recognized.
- 542 successes and 21 failures are reproduced.
- Baseline state and response tensor match the original Stage1 analysis.
- SVD singular values match the uploaded results.
- Energy-only recommended mode count is 3.
- Only SVD2/SVD3/SVD4 candidates are generated.
- 300-sample mode robustness analysis completes.
- Original full14/SVD5/SVD6/SVD8 validation JSON files are rescored with strict metrics.
- Report and CSV generation complete without requiring an environment instance when all validation files already exist.

## Not performed here

- No real `gotsc` retry was executed.
- No 192-worker or reduced-worker Ray/TSC integration was executed.
- No real SVD2/SVD3/SVD4 nonlinear validation was executed.
- Server library paths, Intel runtime, NetCDF, and HDF5 were not loaded locally.

The server run remains the source of truth for the 21 recovered experiments and nine new real-TSC trajectories.
