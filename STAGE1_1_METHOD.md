# Stage1.1 method

## 1. Source preservation

Stage1.1 creates a new run directory and copies the source Stage1 `raw_experiments/*.json.gz`. Existing successful files are never rerun. The source directory remains read-only.

The exact source resolved train/environment configuration is adopted. The only operational change is `tsc_timeout_s: 120 -> 180` for retry robustness.

## 2. Identification recovery

The expected grid remains:

```text
3 zero-action baselines
+ 10 injection times × 14 coils × 2 signs × 2 amplitudes
= 563 experiments
```

A result is considered complete only when its JSON payload has `success=true`. Failed files are therefore automatically retried and atomically replaced only after the retry finishes.

The default retry plan progressively reduces concurrency to distinguish resource/time-out failures from repeatable physical failures.

## 3. Response reconstruction

For each injection time and coil, the local derivative is fitted from actual effective current changes, not requested normalized actions. Positive and negative perturbations are both required.

The response tensor is:

```text
G[t, output, injection_time, coil]
```

with outputs `R`, `Z`, and `Ip`.

## 4. SVD recommendation

The old Stage1 recommendation used the maximum of an energy rule and a loose singular-ratio rule, which mechanically returned 8 modes. Stage1.1 uses `mode_recommendation_rule=energy_only`:

```text
smallest k with cumulative squared-singular-value energy >= 99%
```

For the uploaded Stage1 data this returns 3 modes.

Stage1.1 also performs 300 bidirectional-pair resamples. For each resample it refits the response and measures principal angles between the reference and resampled mode subspaces. This quantifies whether SVD2, SVD3, and SVD4 are reproducible rather than merely high-energy.

## 5. Candidate construction

Only the full-target candidates are optimized:

```text
svd02_target1p00
svd03_target1p00
svd04_target1p00
```

The optimization objective and physical constraints are unchanged from Stage1:

- late-window R/Z/Ip tracking;
- late R/Z velocity penalty;
- per-step coil increment limits;
- cumulative coil-current limits;
- action and current-deviation regularization.

No full14 or 5/6/8-mode candidate is regenerated in Stage1.1.

## 6. Real-TSC validation

Each low-dimensional candidate is replayed at:

```text
0.75, 0.85, 1.00
```

for exactly nine real-TSC validation trajectories.

The original full14/SVD5/SVD6/SVD8 validation trajectories are not rerun. They are rescored from their stored raw JSON as a read-only reference.

## 7. Corrected metrics

For each tolerance `d` in 20, 30, 40, and 80 mm, Stage1.1 records:

- first entry after step 0;
- whether it is ever entered after step 0;
- terminal inclusion;
- late-window fraction;
- longest consecutive streak after step 0;
- trailing consecutive streak at 1200 ms.

It also records:

- terminal Euclidean R/Z error;
- terminal box maximum error;
- minimum error after step 0;
- terminal and late R/Z velocity;
- model-versus-real terminal error;
- terminal and late error reductions relative to zero action.

## 8. Verdict hierarchy

1. `PASS_PRECISE_HOLD_30MM`
2. `PASS_DAMPED_HOLD_40MM`
3. `PASS_POSITION_30MM_SPEED_FAIL`
4. `PROMISING_STRONG_DRIFT_SUPPRESSION`
5. `FAIL_OR_INCONCLUSIVE`

The primary pass requires the last three post-initial samples inside the ±30 mm box, safe Ip, terminal velocity ≤0.10 m/s, and late velocity RMS ≤0.10 m/s.

The verdict is based on real TSC only. Linear predictions remain diagnostics.
