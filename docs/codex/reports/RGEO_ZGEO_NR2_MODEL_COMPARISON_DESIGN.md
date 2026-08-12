# R_geo/Z_geo NR2 causal model comparison design

Status: prospectively frozen before any NR2 TSC plant advance on 2026-08-13.

## 1. Scope

NR2 may collect a new, explicitly identified finite dataset and compare four
causal model classes for eight-step prediction from the fixed 1100 ms start:

1. standardized affine ARX with explicit four-step state/action memory;
2. GRU residual model;
3. LSTM residual model; and
4. causal TCN residual model.

Every model receives the same causal fields: time since takeover, the paired
same-step `R_geo/Z_geo`, same-step `Ip`, all 14 actual coil-current readbacks,
all 14 quantized next Card15 target currents, validity mask, and four-step
history. There is no hidden LFS/HFS mode, future state, outcome label, source
trajectory result, magnetic-axis/centroid fallback, or reset at `R_mid`.
The existing runner remains direct-effect and has an explicit empty software
queue. NR2 changes no runner, reward, termination, Card15, current, slew, or
queue semantics.

NR2 is identification/model qualification only. It does not run a controller,
MPC, RL, Oracle search, or create expert data.

## 2. Evidence identity and split

The campaign identity is `rgeo_zgeo_nr2_causal_models_v1`, with
`intended_use=identification`, declared before collection. NR0/NR1 and every
old probe/sentinel/raw tree remain forbidden from fitting, calibration, or
evaluation.

The complete matrix has 30 deterministic base sequences and exact sign pairs,
for 60 independent restarts and 480 maximum authorized plant advances:

| split | base pairs | trajectories | role |
|---|---:|---:|---|
| development | 16 | 32 | fit and candidate selection inside each class |
| calibration | 6 | 12 | interval scale only; never gradient/model fit |
| fresh holdout | 8 | 16 | final frozen-candidate evaluation only |

No transition-level random split is allowed. All eight transitions and nine
states of a trajectory remain in exactly one split. Fresh holdout TSC is not
authorized until development/calibration raw passes integrity/safety gates
and every fitted candidate, normalization statistic, seed, weight hash, and
interval rule is frozen.

## 3. Prospective excitation

Each base sequence is generated without TSC results from SHA-256 bits over its
split/pair/event/coil identity. Each of the 14 TSC-order components is `+1` or
`-1`; the paired sequence negates every component. The action generator must
prove rank 14 separately in development, calibration, and holdout before TSC.

Targets are exact existing `.3E` Card15 values around the representable 1100
ms center `q0`. Normalized amplitudes alternate prospectively between `0.20`
and `0.35`, corresponding nominally to `0.6 A` and `1.05 A` before Card15
rounding under the unchanged `3 A/step` limit. Sequences alternate between:

- four one-step pulses, each followed by exact `q0`; and
- two two-step persistent pulses, each followed by two exact `q0` steps.

Every trajectory has exactly eight 10 ms advances and ends at 1180 ms. There
is no adaptive excitation. Any target that is not representable, violates
absolute current/slew, or fails exact-return construction vetoes the campaign
offline rather than being clipped or replaced.

## 4. Safety and raw gates

NR1's fail-closed state and target interface is reused unchanged at every
step. The finite campaign stop limits remain:

- paired valid boundary/limiter and same-state Ip;
- no TSC abnormal/nonzero return/solver/saturation condition;
- existing absolute-current and `3 A/step` slew limits;
- `R_geo` between same-state limiter midplane radii;
- `|R_geo-R_geo(1100)| <= 0.05 m`;
- `|Z_geo-Z_geo(1100)| <= 0.05 m`;
- source Ip sign retained and `|Ip-Ip(1100)| <= 10% |Ip(1100)|`.

A violation stops the current trajectory before any later advance and stops
the phase. It remains a failed trajectory even though abort worked. There is
no automatic amplitude reduction or replacement run under this identity.

For every state, preserve `geqdsk`, `inputa`, `sprsina`, coil and wire CSV,
parsed boundary/limiter/Ip/current fields, exact target fields, timestamps,
and file hashes. An independent raw audit must reproduce the spec, action,
safety, count, and split gates before fitting or holdout authorization.

## 5. Fair model protocol

All models predict the next normalized delta of `(R_geo, Z_geo, Ip)` and are
evaluated by recursive eight-step rollout. Input/output normalizers use only
development trajectories. Neural candidates use PyTorch CPU, deterministic
algorithms, five fixed seeds, at most 10,000 trainable parameters, identical
Adam learning rate/epoch/patience/gradient-clip budgets, and no model-specific
feature. ARX uses the same four-step padded history and five deterministic
trajectory bootstraps. Candidate selection sees development only.

Calibration may only choose one nonnegative multiplier applied to ensemble
absolute residual quantiles. It may not change weights, architecture, input,
or point prediction. The frozen point predictor is the five-member ensemble
mean. Model and uncertainty evaluation is trajectory-recursive, never
teacher-forced on calibration or holdout.

Scaled point errors use prospective scales:

```text
R_geo: 0.005 m
Z_geo: 0.005 m
Ip:    500 A
```

A model class is holdout-eligible only if calibration has at least 90% joint
coordinate coverage for its nominal 95% interval and maximum half-width no
larger than `0.02 m / 0.02 m / 2000 A`. Final model qualification requires on
fresh holdout:

1. zero invalid/non-finite recursive predictions;
2. at least 90% joint point rows with all three scaled errors `<= 1`;
3. 95th-percentile maximum-coordinate scaled error `<= 1`;
4. at least 90% joint interval coverage; and
5. the same interval half-width caps.

Among classes that pass, choose the lowest holdout mean squared scaled error.
A neural class can displace affine ARX only if its mean squared scaled error
is at least 15% lower and it is not worse on joint coverage or 95th-percentile
scaled error. Otherwise choose ARX. If no class passes, return
`CAUSAL_MODEL_COMPARISON_FAIL_REDESIGN`; do not enlarge a network or collect
more data under this identity after seeing the result.

## 6. Stage order and claims

1. commit design and immutable spec generator;
2. pass local/server offline rank, Card15, current, slew, return, count, and
   hash gates;
3. collect only development/calibration (352 advances maximum);
4. independently audit raw; fit and freeze all candidate ensembles;
5. only if at least one candidate is calibration-eligible, collect the 16
   fresh holdout trajectories (128 advances maximum);
6. independently audit and evaluate once; record all candidates, including
   failures.

An NR2 PASS establishes only finite same-source eight-step prediction. It
does not establish different-start/history robustness, long horizon,
cross-`R_mid` behavior, control authority, recursive feasibility, safety of a
planner, or real-device validity. NR3 may use only the actually qualified
model and the stated finite envelope.
