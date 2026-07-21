# Stage2.1 JSON-safety audit

## Triggering failure

The supplied log shows that all eight generations completed successfully
(1536/1536 optimization evaluations), after which confirmation started with 15
rollouts.  The driver then failed while writing the first returned raw
confirmation result:

```text
ValueError: Out of range float values are not JSON compliant: nan
```

The exception occurred in the strict gzip writer in
`stage1_controllability.py` (`allow_nan=False`).  That writer was behaving
correctly; the payload was already invalid.

## Root cause

The failure path was:

1. Stage2.1 generation summaries retained `linear_prefilter_score`, but did not
   retain `predicted_terminal_R_error_m`, `predicted_terminal_Z_error_m`, or
   `predicted_terminal_Ip_error_A`.
2. Confirmation selected rows from those summaries and called
   `_as_float(row.get(...))` for each absent prediction.
3. `_as_float` used NaN as its default, so the confirmation spec contained
   three NaN values.
4. `run_validation_experiment` embeds the complete spec in the returned result.
5. The first completed confirmation result was passed to the validated strict
   Stage1 gzip writer, which rejected the NaN token.

The Stage2.1 standalone package supplied immediately before this audit still
contained the same logical path, so an update was necessary.

## Direct correction

- Confirmation now recomputes all linear prediction diagnostics from the
  selected 15-dimensional vector and decoded action sequence.  It does not
  depend on optional historical row metadata.
- Generation summaries now persist the three terminal linear predictions.
- Confirmation specs are strict-JSON validated before Ray or TSC starts.

## Similar latent cases corrected

- A disabled velocity surrogate formerly inserted NaN predictions into
  candidate manifests/specs.  Missing optional predictions are now JSON `null`.
- Stage2.1's own JSON writers formerly allowed Python NaN/Infinity tokens.
  Every Stage2.1 JSON artifact now uses the shared strict serializer.
- Empty confirmation statistics formerly used NaN.  They now use JSON `null`.
- Legacy Stage2.1 files containing permissive NaN tokens are normalized to null
  on read, allowing the completed failed run to continue to confirmation.
- Every TSC state scalar, current vector and action vector is checked for finite
  values before it is appended to a trajectory.
- Every Stage2/Stage2.1 evaluation spec is checked before workers are launched.
- If an unexpected worker result is still not serializable, that candidate is
  persisted as a standards-compliant failed result and the remaining wave
  continues; the whole population is not aborted.
- Failed atomic writes remove their temporary files.  Evaluation directories
  also remove stale `*.json.gz.tmp.*` files before a new wave.
- An undefined Stage1 reachable-set hull distance now uses null rather than NaN.

## Scientific invariants

This correction does not change:

- the 30 mm strict gate;
- the 40 mm relaxed gate;
- velocity or Ip thresholds;
- the 3-mode/5-node/15-variable parameterization;
- population size, archive sizes, family quotas or number of generations;
- any Stage2.1 objective weight or proposal distribution.

It is a runtime/data-integrity correction, not a new optimization experiment.

## Validation performed

- Python compilation: passed.
- All shell scripts: `bash -n` passed.
- Stage2 synthetic test: passed.
- Stage2.1 synthetic test: passed.
- Stage2.1 unit/regression tests: 14 passed.
- Complete pytest suite: 18 passed.
- Exact missing-historical-prediction confirmation regression: passed.
- Disabled-surrogate JSON regression: passed.
- All-confirmation-repeats-failed/null-summary regression: passed.
- Non-finite TSC state rejection: passed.
- Non-serializable result isolation: passed.
- Legacy NaN read compatibility: passed.
- Atomic temporary-file cleanup: passed.
- Completed Stage2 source data reloaded: 1536 usable records.
- Rebuilt archives: 64 damped and 32 precise candidates.
- First patched generation manifest: 192 unique candidates and strict-JSON-safe
  specs.
- Clean extraction in a directory without `.git`: package verifier passed.

The package was not run here against the user's gotsc binary.  The 15 real-TSC
confirmation rollouts remain the final server-side runtime check.
