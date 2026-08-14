# R_geo/Z_geo 1 ms NR2R2C2a nominal-hold search result

Date: 2026-08-14 Asia/Shanghai

Final route:

```text
ONE_MS_NR2R2C2A_SEARCH_NO_NOMINAL_HOLD_CANDIDATE_REDESIGN
```

## Execution and integrity

The frozen implementation at `3c03cf4` executed two canonical-source 32 ms
search trajectories, 64/64 authentic 1 ms plant advances and 66 states. Both
completed without runtime, boundary, limiter, Card15, command/readback slew,
absolute-current, Ip, inner-margin or empirical successor-bound failure.

The independent V2 raw audit passed all 64 action reconstructions and all 330
required final-raw files:

```text
required bytes                  3,886,932,984
inventory SHA-256  30075aa96216d845f2de1c09d97411fbb8c504c486a1daf7cfe5e2546935f6c1
primary result SHA-256 a96bfffd0f8a115e9d42a50aed2c58de637a3bc6d38a321b6f32db44f3421021
```

The largest observed successor changes remained below the prospective
`2 mm / 2 mm / 100 A` bound:

| candidate | max R step | max Z step | max Ip step |
|---|---:|---:|---:|
| p04 plus constant dwell | 0.790055 mm | 0.8430715 mm | 20.3751 A |
| p07 plus constant dwell | 0.8058375 mm | 0.8394165 mm | 15.6010 A |

## Scientific result

Neither fixed 0.15 A-offset target produced a nominal hold:

| metric | p04 plus | p07 plus | frozen gate |
|---|---:|---:|---:|
| endpoint R from source | -17.6557 mm | -17.7786 mm | diagnostic |
| endpoint Z from source | +23.5228 mm | +23.4158 mm | diagnostic |
| endpoint Ip from source | -358.139 A | -345.140 A | diagnostic |
| terminal max source-axis displacement | 23.5228 mm | 23.4158 mm | <=5 mm |
| terminal max axis step | 0.80355 mm | 0.79895 mm | <=0.1 mm |
| terminal net axis drift | 5.80532 mm | 5.78064 mm | <=1 mm |

The q0 comparator endpoint is -17.601295 mm R, +23.4419245 mm Z, and
-335.723 A Ip. Thus the long dwell trajectories remain essentially on the
q0 drift path rather than providing persistent authority.

Both candidates did show isolated q0-relative transients near states 5 and
12: roughly `+0.70 mm R / -0.35..-0.39 mm Z`. Between those events the
deviation returned near zero even though the Card15 target was unchanged.
For p07, the mean `(Delta R-Delta Z)` improvement over states 3..16 was only
`0.08145 mm`, with positive sign at 2/14 states. The earlier four-step peak
therefore cannot be treated as a static gain or extrapolated into a hold.

This is an action-schedule/finite-authority search FAIL, not a runtime,
interface, current, raw, model-training, controller, MPC, recovery or global
plant-reachability failure. It specifically rejects only these two constant
0.15 A-offset schedules.

## Audit correction and next boundary

The first independent audit is preserved as FAIL. It compared a raw wire
tuple directly with the equivalent JSON list, so all 66 states failed only on
container type. Commit `d170be7` normalized both sides to tuples; V2 then
passed with zero new TSC and no physical-action change.

No candidate is frozen for fresh validation; Nominal-H1 and C2b remain
blocked. The next admissible discriminator must not enlarge a neural model.
It may only test a separately frozen, still-supported cumulative/current-
level primitive to determine whether the 0.15 A constant-cell failure is an
amplitude/schedule-authority limitation. Any new current level must obtain
its own pre-result successor envelope and remains development-only.
