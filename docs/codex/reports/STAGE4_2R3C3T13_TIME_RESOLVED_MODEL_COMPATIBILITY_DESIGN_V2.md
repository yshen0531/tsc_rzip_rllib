# Stage4.2R3c3T13 time-resolved model compatibility design V2

## Status

This V2 design is frozen before any Stage3.4-Jacobian prediction error is
computed. It inherits every evidence identity, comparison, prediction metric,
threshold, route rule, timing constraint, scientific limitation, and
no-new-TSC prohibition from
`STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_DESIGN.md`, except for the
applied-input reconstruction explicitly replaced below.

The first V1 invocation stopped on the first R3c3 raw file before creating an
output directory or multiplying the Jacobian. It observed:

```text
trajectory-current / trace-command difference       0.0476826407 A
trajectory-current three-mode residual               0.0403534492 A
Jacobian prediction comparisons executed                        0
Ray / gotsc / TSC / controller / optimizer executed             0
```

That event invalidated one V1 field-semantics assumption. It produced no
model PASS/FAIL and is not evidence for or against the plant, restart,
controller, Jacobian, or route.

## Source-backed reason for the correction

The exact current source inspected is:

| Source | SHA-256 | Last commit |
|---|---|---|
| `core/runner.py` | `304e412d86220b871011c409b4e9c899149341c2c48499b1bbabfcafadbc0021` | `2c7a184` |
| `core/inputa.py` | `33760858ae0f80efa0cd5c418707261e1cdab60c0c78707002406db5335b6767` | `ee1a8f5` |
| `envs/rzip_env.py` | `6bfe266533424d0a671369578bcd0458ce3a9823233ce2ef02df109d49a3b270` | `0d51ab4` |
| `diagnostics/stage1_controllability.py` | `7214dea9d93364bd4cacd3d324f2156879fcf255a75c9a5ac7423e02d6acbb58` | `15ad9e7` |

The source contract is:

1. the controller records the exact 14-coil normalized action passed to
   `env.step` in `controller_trace[k].action_norm_tsc`;
2. the environment multiplies that action by its actual
   `max_delta_current_a_per_step`, which is `3.0 A * slew_scale` here;
3. the runner forms the requested next coil current;
4. the runner converts A to kA-turn and writes TSC Card 15 through
   `format_number(value)`, which uses `.3E` fixed-width formatting;
5. `trajectory[k+1].currents_a_tsc` is reconstructed from TSC's
   `coil_currents.csv`, after that finite-precision input path.

Therefore adjacent trajectory-current differences are authentic observed
TSC states but are not an exact copy of the pre-Card-15 command increment.
Requiring bitwise equality or exact membership in the three-mode command
subspace was a V1 audit-design error.

The Stage3.4 Jacobian was identified with changes to the 35-by-3 control
coefficient vector decoded into action commands and sent through this same
runner/TSC path. Its native independent variable is the command coefficient,
not a post-format finite difference inferred from `coil_currents.csv`.

## Corrected primary input

For run `r` and action step `k = 0..34`, define:

```text
a_r[k]          = controller_trace[k].action_norm_tsc
DeltaI_cmd_r[k] = a_r[k] * 3.0 A * spec.slew_scale
u_r[k]          = (DeltaI_cmd_r[k] / 3.0 A) @ M
epsilon_cmd[k]  = DeltaI_cmd_r[k] - 3.0 A * (u_r[k] @ M.T)
```

`M` remains the exact authenticated orthonormal 14-by-3 Stage3.4 mode matrix.
Because `a_r` is recorded after the delay queue, actual gain, actual slew,
nonlinear scheduler, current-limit scaling, and feedback action choice, this
uses the total command actually submitted for the plant step. It does not use
the requested probe schedule, pair/history/prefix label, source action,
future value, or hidden wire current.

The corrected input-authentication gates for all 1,408 raw files are:

```text
trace action shape                                     35 x 14
trace and trajectory values                              finite
maximum command out-of-three-mode residual            <= 1e-9 A
reported delay/effect-state mapping                       exact
```

The old V1 `trajectory-current / trace-command <= 1e-9 A` gate is removed,
not relaxed. It tested equality between different source-defined quantities.

## Secondary observed-current diagnostic

The audit must still report, without using it to select the better predictor:

```text
DeltaI_obs_r[k] = trajectory[k+1].currents_a_tsc
                  - trajectory[k].currents_a_tsc

maximum |DeltaI_obs - DeltaI_cmd|
maximum post-observation three-mode residual
distribution by slew and coil
```

These values quantify the Card-15/TSC observed-current path. They are not an
input-reconstruction acceptance gate and are not subtracted from output
errors. Finite-precision and any plant-side input discrepancy therefore
remain part of the measured model error faced by the predictor.

## Comparisons and route rule

All V1 comparison counts and formulas remain unchanged:

```text
signed differential comparisons                         576
same-run baseline-relative finite nodes                  896
T9 four-node Walsh interactions                           32
```

For each formula, `delta_u` now uses the corrected `u_r` above. The predictor
is still evaluated only once, with the prospective absolute, relative, and
causality gates. No V1 model result exists to tune against.

An input/schema/source-authentication failure still makes the audit invalid.
A valid prediction-tier failure still vetoes the frozen Stage3.4 Jacobian as
an unqualified restart-envelope predictor and routes T13 toward one specific
state- and issue-time-conditioned minimal sentinel. It never authorizes a
full identification campaign or a real controller.

Formal arrival remains 250/270 ms and hold remains through 350/370 ms. The
Stage3.4 predictor still ends at state 35 and does not model the weak-slew
state-37 hold endpoint.
