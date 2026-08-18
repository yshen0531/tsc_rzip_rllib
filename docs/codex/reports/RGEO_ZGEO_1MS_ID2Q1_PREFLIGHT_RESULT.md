# ID-2Q1 zero-model preflight result

ID-2Q1 v1 stopped before model fitting as an input-coordinate design FAIL.
The exact p04/p07 plus/minus Card15 vectors across K1 and P1 have numerical
rank three, while the frozen loader required rank two. Server recomputation
found singular values `6.53890256`, `5.79770069`, and `0.38075656 A`.
For each named direction, the odd component norm is `1.09227083 A` and the
common even component norm is `0.05000000 A` (`4.58%` of the odd norm).

This is not a data-integrity, runtime, model, calibration or control result.
The preflight fit zero models and executed zero TSC calls, resets and plant
advances. ID-2Q1R1 retains the same cells, folds, candidates and gates but
uses the full rank-three executed action subspace. It does not silently
discard the even Card15 component or introduce evaluator labels.
