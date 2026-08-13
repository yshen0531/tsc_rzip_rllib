# R_geo/Z_geo 1 ms NR2 result

Status: frozen fail-closed interface/design failure on 2026-08-13.

## Identity and execution

```text
source commit       9b559ee
contract            rgeo-zgeo-1ms-nr2-v1
campaign            rgeo_zgeo_1ms_nr2_structural_residual_v1
remote run          /home/yangshen0711/tsc_all/tsc_rzip_rllib/
                    rgeo_zgeo_1ms_nr2_runs/
                    rgeo_zgeo_1ms_nr2_structural_residual_20260813_9b559ee
planned maximum     36 trajectories / 576 plant advances
executed            1 incomplete trajectory / 1 plant advance
holdout             not authorized and not run
training/fitting    not run
```

Installed-server tests passed 1,671/1,671 with one expected skip and the
zero-TSC offline gate passed before collection. Collection then stopped after
the first q0 issue in `development_p00_plus`; no later action was issued.

## Failure

The frozen structural actuator formula was:

```text
bias = source_readback - source_active_Card15_command
predicted_readback[k+1] = issued_target[k] + bias
```

At the source, command and readback are identical at their fine decimal
resolution, so this formula predicted zero bias. The q0 Card15 serialization
was coarser by up to `1e-5 A` per turn. At 1101 ms, actual readback retained
the fine source values while active `inputa` contained q0. The maximum exact
prediction error was therefore `0.00001 A`, above the frozen `1e-9 A` gate.

This is an actuator-coordinate/interface-design failure. It is not a TSC
runtime, solver, saturation, raw-corruption, geometry, Ip, slew, learned-model
or closed-loop-control failure. The attempted q0 command was within the exact
`0.3 A` step limit; observed current change was zero. The paired-boundary
signal remained valid.

Read-only NR1R2 evidence independently shows that the persistent readback
offset is relative to q0, not the finer source `inputa` command:

```text
bias = source_readback - q0_command
```

That relation explains both the unchanged q0 readback and every previously
audited 0.3 A pulse/return transition. NR1R2 remains interface-validation
evidence only and is not eligible for fitting.

## Frozen route

```text
ONE_MS_NR2_SAFETY_FAIL_STOP
```

NR2 cannot resume under a changed structural formula. Its one incomplete
trajectory remains immutable and forbidden from model or expert data. A new
prospective identity is required before any further TSC.

