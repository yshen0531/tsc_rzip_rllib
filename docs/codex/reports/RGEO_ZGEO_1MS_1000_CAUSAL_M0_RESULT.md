# Fixed-1000 causal M0 result

M0 executed no TSC. It fit one frozen standardized ridge on the 25 eligible
fixed-1000 B0/D0R1/D1/N0 primary trajectories and evaluated six whole
schedule/phase folds against an action-blind comparator.

M0 failed without emitting a model artifact. R one-step p95 was
`0.468--0.596 mm` in every fold, above the `0.35 mm` gate. Z p95 remained
below `0.032 mm` and Ip p95 below `7.5 A`. Mean paired-response NRMSE was
`0.929989`, only `1.078%` better than the blind model's `0.940124` and above
the `0.8` gate. Several held families had wrong peak direction.

A deterministic refit of the identical frozen model, used only for
attribution, found 146 rows above `0.35 mm` R error and 50 sign flips. Errors
cluster at recurring effect states 5, 9, 12, 16, 20, 26 and 39 across multiple
families. Some top failures have close standardized training neighbors,
whereas deep N0 rows also show large support distance. This supports one
explicitly event-aware causal successor; it does not justify retuning ridge,
adding nearby TSC data, widening gates or claiming general hidden-state
unobservability.

M0 remains a development FAIL. No calibration, holdout, Authority, Recourse,
feedback or controller stage is authorized.
