# Stage-1 changes relative to B99.10

This is not another actor-transaction training version. It is a separate diagnostics and reachability package.

## Removed from the main workflow

- MPO actor/critic training;
- actor proposal and negative-alpha parameter line search;
- reward/dual optimization;
- checkpoint dependence on B99.9/B99.10 actors.

## Added

- independent zero-action baseline repeatability test;
- full time-indexed, channel-indexed, signed multi-amplitude current-increment scan;
- response tensor in physical units `d(R,Z,Ip)/dA`;
- fit nonlinearity, sign coverage, clipping-aware effective perturbation, and pre-injection leakage diagnostics;
- horizon-dependent controllability rank and singular values;
- 14-dimensional SVD spatial coil modes in both TSC and display order;
- U/L common/differential pair-mode ranking;
- local 100 ms R/Z reachable-set projection with exact slew/current bounds and an Ip band;
- constrained late-window open-loop sequence optimization in 2/3/4/5/6/8-mode and full-14-D spaces;
- nonlinear replay of selected sequences in the real TSC environment;
- explicit Gate-A verdict and resumable per-experiment atomic outputs;
- immediate hard-stop script without delayed shutdown.

## Purpose

The output determines whether the present target/horizon/actuator constraints are locally plausible before more RL work begins, and supplies the empirical response matrices needed for the next low-dimensional control stage.
