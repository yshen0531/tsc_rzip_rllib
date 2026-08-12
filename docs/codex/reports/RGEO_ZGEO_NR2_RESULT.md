# R_geo/Z_geo NR2 result

Final route: `CAUSAL_MODEL_COMPARISON_FAIL_REDESIGN`

NR2 completed its prospectively frozen same-source causal model comparison on
2026-08-13 Asia/Shanghai. Design, implementation, and portable-test
checkpoints were `8fa88bd`, `e69049c`, and `6cde02d`.

## Data and integrity result

The server offline gate passed before NR2 TSC:

```text
total trajectories / plant advances          60 / 480
development trajectories / advances          32 / 256
calibration trajectories / advances           12 /  96
fresh holdout trajectories / advances         16 / 128
quantized action rank by split                 14 / 14 / 14
maximum sequential target increment       1.10001 A
action-stream SHA-256                  5061e820...e631
```

Development/calibration collection completed 44/44 trajectories and 352/352
plant advances. Its independent audit passed 396 state checks, 352 Card15
checks, and 1,980 required raw-file checks. Fresh holdout was kept locked until
all model weights and normalization/calibration state were frozen. After four
model classes passed the calibration eligibility gate, holdout collection
completed 16/16 and 128/128. Its independent audit passed 144 state checks,
128 Card15 checks, and 720 required raw-file checks.

Across the complete campaign, every TSC/runtime/raw/Card15/current/slew/
boundary/Ip safety gate passed. Maximum development/calibration displacement
was `27.693925 mm R / 47.7865435 mm Z`; maximum holdout displacement was
`27.442895 mm R / 47.786343 mm Z`. Maximum Ip deviation was 1.86518%, and the
maximum target increment was 1.10001 A. There were 60 raw trajectory records,
480 plant advances, and 3,780 rollout files. No collector or `gotsc` process
remained after finalization.

## Frozen model comparison

Whole sign-paired trajectories stayed in one split/fold. CV selected:

```text
ARX  ridge 0.01
GRU  width 12
LSTM width 12
TCN  width 12
```

All four frozen ensembles passed calibration with 90.625% joint coverage and
geometry/Ip interval half-widths below `20 mm / 20 mm / 2000 A`. Frozen bundle
SHA-256 was
`ead32665a42d96f98f4a2c042110625312e571884149177eba4e15f7a3f7d9f9`.

The one authorized holdout evaluation produced:

| model | joint point | joint interval | p95 scaled R/Z/Ip | p95 coil error (A) | scaled MSE | pass |
|---|---:|---:|---:|---:|---:|---|
| ARX | 1.0000 | 0.9765625 | 0.490572 | 0.156770 | 0.00469203 | no |
| GRU | 1.0000 | 1.0000 | 0.475703 | 1.092573 | 0.0665154 | no |
| LSTM | 1.0000 | 1.0000 | 0.510981 | 1.034591 | 0.0670479 | no |
| TCN | 1.0000 | 0.9921875 | 0.530140 | 1.312610 | 0.132365 | no |

Every model passed the frozen geometry/Ip point and interval gates, but every
model failed the `<= 0.05 A` p95 recursive coil-readback gate. ARX was clearly
best but still exceeded that gate by 3.14 times. The recurrent/convolutional
models were materially worse than the simple causal baseline; there is no
qualified winner.

This is a model/state-propagation design failure, not a runtime, deployment,
raw, Card15, statistical-reporting, safety, geometry-signal, plant-authority,
controller, MPC, or global-reachability failure. In particular, it does not
invalidate the strong finite holdout result for `R_geo/Z_geo/Ip`; the stage
fails because its prospectively required learned actuator-readback recurrence
was not accurate enough.

## Evidence hashes and execution notes

```text
offline preflight                 1ebf1f4746ca7ce000acbd48a857b05f54ccbb885c8cb849258d557d091cdc9b
development/calibration summary  959e75e6954981fee215cc92dd7b399bade7e771b046312d165f65810fa1a4df
development/calibration audit    0fa10e29f9c61e4780a69001bd1585601a7f8ccb715df2400c44aef68d869fa5
fit/calibrate report             9ec1845b371f7118c2045ee901f0c3e23040e5d02925e883b6a9a7fca04d0e22
holdout authorization            e1d44282cc9d8689ddb1ab70ebc003d1d31d78c5a5c7a808b32548285a5608c3
frozen model bundle              ead32665a42d96f98f4a2c042110625312e571884149177eba4e15f7a3f7d9f9
holdout summary                  02f3456e14dbb007ad1aef95f461fb5d534de8e4fa9370780a685c074ae82107
holdout audit                    86715be0d15777c610f525257a37d0659399a15ed38ec14505a417b1fbc14baa
holdout evaluation               21610bf309102311268b5253fc46d6f8968d1d71714b4c53fc5703b9c11582af
```

One initial server staging test failed because its temporary directory assumed
the local `.codex_tmp` directory existed. The portable-test hotfix changed
only test temporary-directory selection and produced zero plant advances.
The later foreground holdout SSH call reached the local 2400 s tool timeout,
but read-only audit proved the remote collector had already completed and
written 16/16, 128/128, failure-free output; no resume or rerun occurred.

The complete server run is approximately 32.3 GB and remains in place. It was
not compressed, downloaded, renamed, or cleaned.

## Pause and redesign boundary

Frozen rules prohibit relaxing the current gate, adding capacity, or reusing
fresh holdout after seeing this result. NR3 is not authorized by this failure.

The most evidence-aligned redesign candidate is to separate deterministic
Card15/actuator/readback state propagation from the learned plasma residual,
rather than force one learned residual model to recursively predict both. A
new prospective NR2R1 would need an independently testable structural
actuator transition, explicit uncertainty for any remaining readback mismatch,
and a new untouched evaluation identity. This is a substantive architecture
decision, so work pauses here for user direction as requested.
