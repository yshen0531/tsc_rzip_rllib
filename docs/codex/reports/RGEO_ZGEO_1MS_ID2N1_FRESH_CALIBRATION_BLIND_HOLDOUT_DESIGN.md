# R_geo/Z_geo 1 ms ID-2N1 fresh calibration and blind holdout design

Date: 2026-08-18 Asia/Shanghai

## Purpose

ID-2M1 selected and froze a source-local development predictor. ID-2N1 is
its first fresh data test. It runs one prospectively frozen TSC campaign with
two strictly ordered roles:

1. four calibration whole-history families construct finite 1--8 ms error
   tubes without changing model coefficients or features;
2. only after the calibration artifact is written and hashed, four blind
   whole-history families are executed and opened against that frozen model
   and tube.

This is model/tube validation, not authority, recovery or closed-loop
control.

## Campaign

All trajectories start from the canonical 1100 ms source, use a 1 ms issue
period and run 34 advances. The frozen p03-minus active nominal is unchanged.
Every family contains one baseline and two matched-prefix probes, one p04 and
one p07. Conditioner composition, duration, issue time, probe sign and probe
time differ from ID-2K1. Four preregistered cells have a second exact replay.

The campaign therefore contains 24 unique cells plus four replay cells:
`28` resets, at most `952` advances and `980` retained states. Calibration
and holdout each contain four independent whole-history families; siblings
never cross roles.

All targets are exact translated Card15 targets already admitted as p04/p07
action values. Every adjacent per-coil issue remains at or below `0.3 A`.
Novel compositions/times are explicitly TSC-only empirical identification
exposures: current exact R_geo/Z_geo/Ip is checked before every issue, paired
boundary failure is closed, the existing inner/outer/Ip/current/slew gates
apply, and any failed successor stops before the next issue. These checks do
not convert empirical thresholds into a plant theorem.

## Frozen model and tube

The selected ID-2M1 model file and hashes are immutable inputs. Calibration
does not refit it. For every calibration cell, exact truth is used only as a
prediction origin, then the frozen model predicts endpoints at horizons
1--8 using the known future Card15 schedule.

For output `j` and horizon `h`, the calibrated finite tube is

```text
tube[h,j] = max(floor[j], 1.25 * max_calibration_abs_error[h,j])
```

with floor `0.05 mm / 0.05 mm / 5 A`. Tube caps are prospectively frozen at
`1.5 mm / 1.5 mm / 100 A` for horizons 1--4 and
`3 mm / 3 mm / 150 A` for horizons 5--8. This is a finite maximum-over-four-
families tube, not a population coverage claim.

Calibration also requires all eight paired probes to exceed the signal
floor, remain below the Ip-response cap, have positive R/Z peak direction,
and achieve combined paired-response NRMSE at most `0.75`.

## Blind holdout gates

The holdout is not read, executed or evaluated unless calibration passes and
its artifact exists. It cannot change the model or tube. PASS requires:

- every holdout endpoint at horizons 1--8 lies inside the frozen tube;
- R/Z/Ip endpoint p95 is within the prospectively frozen horizon caps;
- every family has paired-response NRMSE below `0.90`, combined NRMSE is at
  most `0.75`, and at least seven of eight peak directions are positive;
- all matched-prefix, exact Card15, current, raw-integrity and four replay
  checks pass.

Any calibration failure leaves the blind phase unopened. Any blind failure
freezes the model/tube route as insufficient; it cannot be repaired using the
holdout. A PASS authorizes only a separately frozen source-local authority
and recovery discriminator. It does not authorize a controller, NMPC,
transport, R_mid crossing, adaptation or RL.

## Storage

Raw TSC evidence is retained uncompressed. The run requires at least 135 GB
free before launch, reserves a 65 GB estimate and requires at least 70 GB
estimated free afterwards. A storage failure occurs before any reset.
