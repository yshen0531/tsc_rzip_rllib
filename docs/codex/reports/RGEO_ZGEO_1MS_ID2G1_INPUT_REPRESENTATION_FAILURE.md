# R_geo/Z_geo 1 ms ID-2G1 input-representation failure

Date: 2026-08-17 Asia/Shanghai

Final route: `ONE_MS_ID2G1_INPUT_OR_DATA_INTEGRITY_FAIL_NO_MODEL`

Server preflight passed with 78 raw rollout directories and zero reset, TSC
or plant calls.  Raw extraction then stopped before any fold or model fit
because the frozen rank-three Card15 projection gate measured a maximum
residual of `0.07937752868154746 A`, above its `1e-9 A` exactness threshold.

The virtual p03/p04/p07 coordinates describe the intended finite excitation
grammar, but cumulative Card15 quantization and actual readback do not lie in
one exact three-dimensional Euclidean current subspace.  Treating those
virtual coordinates as the exact executor state was therefore a design
mistake.  The gate remains failed; it is not weakened or relabelled.

ID-2G1 trained zero models and read zero ID-2C2, calibration or holdout
records.  This is an input-representation design failure, not a TSC,
runtime, predictive-model, controller or closed-loop result.

The prospective ID-2G1R1 repair retains the data, folds, candidates, metrics
and thresholds but supplies exact full 14-dimensional current readback and
issued Card15 vectors to every model.  Candidate future issued Card15 remains
known; future actual current remains forbidden.  The action-blind comparator
uses the exact time-matched active-nominal issued vector rather than zeroing
assumed virtual coordinates.
