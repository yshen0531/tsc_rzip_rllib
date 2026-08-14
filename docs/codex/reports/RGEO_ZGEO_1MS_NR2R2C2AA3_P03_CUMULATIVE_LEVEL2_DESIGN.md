# R_geo/Z_geo 1 ms NR2R2C2aA3 p03 cumulative-level2 discriminator

Date: 2026-08-14 Asia/Shanghai

Prospective identity:

```text
rgeo-zgeo-1ms-nr2r2c2aa3-p03-cumulative-level2-v1
```

## Question

C2aA2 remains a formal FAIL, but its independently audited p03-minus path
opposed q0 at all 14 authority states and passed the mean/sign/Ip gates. C2aA3
does not relax the failed C2aA2 maximum gate. It asks a different question:
does one additional exact p03 increment, accumulated under the user's
`<=0.3 A` per-coil per-step rule, safely produce persistent total opposition
and positive incremental gain over the frozen level1 trajectory?

This is the first controlled expansion beyond componentwise `q0 +/- 0.3 A`.
Level2 reaches at most `0.6 A` from q0, while each adjacent transition remains
at most `0.3 A`. It is a finite simulator safety/authority sentinel, not a
model, controller or hold experiment.

## Frozen action and repetition

Two identical fresh canonical-source 32 ms replays use:

```text
step 0       q0
step 1       p03 level1 (already measured, <=0.3 A from q0)
steps 2..15  p03 level2 (same exact increment again, <=0.6 A from q0)
step 16      p03 level1
steps 17..31 q0
```

In the exact Card15 field coordinate,
`level2-q0 = 2*(level1-q0)`. The previously measured p03 level1 trajectory and
the tracked q0 trajectory are immutable comparators. No calibration or
invalid holdout is read.

## Pre-result safety support

The novel level1-to-level2 issue repeats the same exact increment that was
already applied q0-to-level1. C2aA2 observed maximum p03 successor changes of
`0.790281 mm R / 0.805596 mm Z / 31.3998 A Ip`; all earlier supported-cube
evidence remained below `0.855951 mm / 0.855951 mm / 45.9948 A`. The
prospective per-step bound remains the independently specified
`2 mm / 2 mm / 100 A`, within the unchanged `25/50 mm` geometry and `5/10%`
Ip source envelopes. This is a bounded adjacent-level extrapolation, not an
assumption of global linearity.

The implementation must refuse before plant advance on invalid paired
boundary, limiter geometry, exact Card15 mismatch, requested/readback slew
above `0.3 A`, absolute-current or Ip breach, unavailable successor reserve,
or a current state outside the inner envelope. It must stop immediately after
an abnormal successor, outer-envelope breach or successor-bound breach.
Legacy runner clipping may not be relied on.

## Frozen scientific gates

For states 3--16, define total opposition against q0 as before and incremental
opposition against the tracked C2aA2 p03 level1 path:

```text
total[k]       = (R_level2[k]-R_q0[k]) - (Z_level2[k]-Z_q0[k])
incremental[k] = total[k] - total_level1[k]
```

Both replays and their exact checked-state comparison must pass. Each replay
must also satisfy:

```text
mean total opposition                  >= 0.50 mm
positive total fraction                 = 1.0
maximum total opposition               >= 0.75 mm
mean incremental opposition            >= 0.15 mm
positive incremental fraction          >= 0.75
maximum |Ip_level2-Ip_q0|              <= 100 A
```

These thresholds are frozen before implementation and real outcome. They do
not change C2aA2's route or retroactively make its p03 level eligible.

## Audit and routing

The final independent audit must reparse paired boundary geometry, R_mid, Ip,
all 14 coil currents, all 48 wire currents, exact issue/effect history,
Card15 fields and required artifact inventory. `sprsina` remains diagnostic.

- PASS route:
  `ONE_MS_NR2R2C2AA3_P03_CUMULATIVE_LEVEL2_PASS_TIME_VARYING_C2A_DESIGN_ONLY`.
  It authorizes only a separately frozen time-varying C2a nominal-hold search
  inside levels q0--2.
- Scientific FAIL route:
  `ONE_MS_NR2R2C2AA3_P03_CUMULATIVE_LEVEL2_FAIL_REDESIGN`.
- Any execution, repeatability or support failure stops under a separate
  fail-closed route.

Even PASS is not Nominal-H1, Recourse-L1, an atlas, a model, MPC, online
adaptation, RL, closed-loop control or global reachability evidence.
