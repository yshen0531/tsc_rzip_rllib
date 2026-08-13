# R_geo/Z_geo 1 ms NR2R1 result

Status: frozen calibration/statistics implementation failure on 2026-08-13.

## Execution and integrity

```text
source commit              25f5b7e
campaign                   rgeo_zgeo_1ms_nr2r1_q0_structural_residual_v1
development/calibration    28/28 trajectories, 448/448 plant advances
fresh holdout               8/8 trajectories, 128/128 plant advances
total                       36 trajectories, 576 plant advances
remote run                 /home/yangshen0711/tsc_all/tsc_rzip_rllib/
                           rgeo_zgeo_1ms_nr2_runs/
                           rgeo_zgeo_1ms_nr2r1_q0_structural_residual_20260813_25f5b7e
```

Primary collection and structurally independent raw audits passed. Across
development/calibration, exact command and observed-current checks passed
448/448, structural current propagation passed 448/448 with maximum error
`1e-26 A`, and 2,380 required raw files were present. Holdout independently
passed the corresponding 128/128 checks, with 680 required raw files.

Maximum exact command and observed-current steps were both `0.3 A`, equality
allowed. Maximum finite-envelope excursions over all audited phases were
approximately `9.53 mm` R, `11.94 mm` Z and `0.55%` Ip. There were no runtime,
solver, saturation, Card15, boundary, safety, or raw-integrity failures.

## Calibration gate implementation error

The prospective design required the maximum interval half-width over every
one of the 16 recursive horizons to remain below:

```text
R_geo <= 0.004 m
Z_geo <= 0.004 m
Ip    <= 400 A
```

The implementation incorrectly checked only horizon 16. It consequently
marked GRU and LSTM eligible and created a hash-bound holdout authorization.
Independent post-result recomputation found their actual maxima over all
horizons were:

| model | max R half-width | max Z half-width | max Ip half-width |
|---|---:|---:|---:|
| GRU | 0.0089792772 m | 0.0045770103 m | 73.4889 A |
| LSTM | 0.0111644913 m | 0.0049881324 m | 86.7780 A |

Both recurrent classes therefore failed calibration before holdout. ARX and
TCN had already failed the same cap. The corrected scientific route is:

```text
ONE_MS_NR2R1_CALIBRATION_FAIL_NO_HOLDOUT
```

The executed holdout is preserved as an erroneously authorized diagnostic;
it is not valid qualification evidence, cannot be reused, and cannot be used
to tune or fit a successor. For completeness, its saved diagnostic metrics
also failed: GRU joint point/interval coverage was `0.8046875/0.84375` with
p95 scaled error `1.95154`; LSTM was `0.796875/0.875` with p95 `2.02336`.

This is first a statistics/gate implementation error and, after correct
recomputation, a real uncertainty/model qualification failure. It is not a
closed-loop controller, planning, or global plant-reachability result.
NR3 is not authorized by this evidence.

