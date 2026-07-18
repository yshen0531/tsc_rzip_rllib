# Stage1.1 changes relative to Stage1

## Scope reduction

- Reuses the completed Stage1 scan instead of rerunning all 563 experiments.
- Retries only failed/missing experiment files.
- Generates only SVD2/SVD3/SVD4 full-target candidates.
- Runs exactly nine new real-TSC candidate validations.

## Runtime recovery

- Reduced retry concurrency: 12 workers, then 4, then serial.
- Retry TSC timeout increased from 120 s to 180 s.
- Source Stage1 directory remains untouched.
- Immediate kill and atomic per-experiment resume behavior retained.

## SVD analysis

- Replaced the old `max(energy count, singular-ratio count)` recommendation with a configurable rule.
- Stage1.1 uses the 99% energy-only rule, which selects 3 modes for the current data.
- Added bootstrap principal-angle stability analysis for 1/2/3/4/5/8-mode subspaces.

## Candidate selection

- Added strict explicit-only validation selection.
- Candidate labels are fixed to SVD2/SVD3/SVD4.
- Validation scales changed to 0.75/0.85/1.00.
- Prevented the previous automatic top-four selection from excluding low-dimensional candidates.

## Evaluation correction

- Excludes step 0 from reach and consecutive-stay metrics.
- Adds 20/30/40/80 mm position boxes.
- Adds longest and trailing streaks.
- Adds terminal Euclidean and box errors.
- Adds zero-action-relative terminal and late-RMS improvement.
- Adds terminal and late velocity requirements.
- Adds linear-prediction versus real-TSC terminal mismatch.

## Gate correction

- Replaces the loose `PASS_TERMINAL_1X` interpretation for Stage1.1.
- Adds precise ±30 mm and relaxed ±40 mm damped-hold gates.
- Separates position success from damping failure.

## Reference handling

- Original full14/SVD5/SVD6/SVD8 raw validation files are copied read-only.
- Original candidates are rescored under the corrected Stage1.1 metrics without rerunning TSC.

## Reachable-set reporting

- Increased sampled support directions from 72 to 144.
- Added target distance to the sampled convex-hull boundary and the nearest boundary point, avoiding an over-interpretation of a boolean inside/outside result near numerical boundaries.
