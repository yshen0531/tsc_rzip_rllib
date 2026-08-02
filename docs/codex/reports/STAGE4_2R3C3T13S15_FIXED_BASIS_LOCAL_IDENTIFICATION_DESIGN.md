# Stage4.2R3c3T13S15 fixed-basis local-identification sentinel design

## Status and question

This design is frozen prospectively before S15 controller code, raw, TSC, or
route selection. S14 is used as development evidence, so S15 is itself a
development sentinel and cannot be called an independent holdout.

S15 asks whether one causal trajectory can identify its own four-direction
immediate response when the physical calibration basis is frozen before any
calibration effect and the natural drift is explicitly separated. It does
not ask whether a learned cross-history label predictor can generalize.

## Contexts and rollout count

S15 reuses exactly the 16 factor-selected authenticated S14 contexts only to
make a controlled excitation comparison:

```text
16 fixed-basis calibration baselines
16 contexts x 4 response directions x 2 signs = 128 probes
144 authentic trajectories total
```

All trajectories start from the exact authenticated R3b snapshots with fresh
controllers and fresh TSC processes. The 144 new S15 raw files are distinct
from S14 raw. S14 and S15 probe trajectories are forbidden from expert data.

## Frozen causal calibration

At task step zero, before observing any calibration effect, the controller
computes the same four native S14 lattice directions around the underlying
controller's initial Card15 center:

```text
mode0_without_coil8
mode0_coil8_component
mode1
mode2
```

The four exact integer Card15 field-increment vectors are then immutable for
the trajectory. No pair, history, prefix, source-result, source-action,
source/current wire-current, future state, or future response value may enter
their construction or subsequent selection.

The fixed signed schedule is:

```text
task step 0   + mode0_without_coil8
task step 1   - mode0_without_coil8
task step 2   + mode0_coil8_component
task step 3   - mode0_coil8_component
task step 4   + mode1
task step 5   - mode1
task step 6   + mode2
task step 7   - mode2
task steps 8--9   no calibration deviation
task step 10      response issue
task step 11      response cancel
```

Every signed calibration target is the contemporaneous underlying-controller
center plus or minus the stored initial field increment. The negative member
is not replanned and is not a return to an old moving center. Each direction
therefore has exact requested net zero. All Card15 fields must be exact,
unsaturated, inside action/slew/current limits, and below 0.55 current
utilization. Any physical infeasibility is a design failure, not permission
to reduce amplitude after seeing raw.

The fixed 8-by-4 sparse code has one `+1` and adjacent `-1` per direction.
Together with normalized constant, linear-time, and centered quadratic-time
columns, its ideal design has rank seven and condition approximately
`2.45713`. The observed requested-field design must have physical rank four;
the complete drift-plus-input design must have rank seven and condition no
greater than 3.0 in every context.

## Frozen within-trajectory estimator

Only states 1 through 8 and actions already issued at steps 0 through 7 may
be used. For each trajectory and each output component
`(R, Z, vR, vZ, Ip)`, fit the fixed seven-column least-squares design:

```text
constant
normalized linear task time
normalized centered quadratic task time
four fixed signed calibration coordinates
```

The four input coefficients are that trajectory's causal immediate-response
estimate. The step-10 response field increment is projected into the frozen
four-vector field basis. Projection must have rank support, coil-space cosine
at least 0.98, relative off-basis residual at most 0.15, and finite
coordinates. Current readback intervals propagate through the same fixed
linear map.

Prediction is compared with the authentic first physical response at state
11 relative to the matched fixed-basis baseline. No future response, matched
baseline result, pair/history/prefix label, or hidden wire value is available
to the online estimator or controller. Matched baselines are used only by the
offline evaluator after raw completion.

The frozen point gate remains maximum scaled center-relative error `<=0.10`.
The provisional component tube is the numerical floor plus three times the
maximum eight-row in-trajectory regression residual plus exact interval-linear
input-radius propagation. It must contain every response and stay below:

```text
(0.003 m, 0.003 m, 0.010 m/s, 0.010 m/s, 1000 A)
```

## Phase gates

The 16 baselines run first. Before any response raw, all must pass:

```text
raw success/fresh process/exact restart/causality       16 / 16
fixed field-basis rank and condition                    16 / 16
drift-plus-input rank seven and condition <= 3          16 / 16
eight exact calibration events                          16 / 16
four exact requested-zero-net signed pairs              64 / 64
Card15/action/current/slew gates                         16 / 16
zero-TSC response lattice coverage                     128 / 128
```

Only then may the 128 response trajectories run. Final gates are:

```text
all raw parse/success/restart/causality                 144 / 144
pre-response semantic equality                         128 / 128
response issue/cancel and exact zero net                128 / 128
response basis projection support                       128 / 128
center relative error <= 0.10                           128 / 128
provisional tube containment and cap                    128 / 128
forbidden inputs, clipping, open-order violations                0
maximum current utilization                                  <=0.55
```

Formal tracking is diagnostic only. The 250/270 ms arrival deadlines and
350/370 ms hold endpoints are unchanged. The 350/370 ms horizons are not
long-hold tests.

## Routes

```text
FIXED_BASIS_LOCAL_IDENTIFICATION_PASS_FRESH_CAMPAIGN_REQUIRED
  every frozen gate passes; authorize only a separately frozen partitioned
  training/calibration/fresh-context campaign and robust-MPC feasibility.

FIXED_BASIS_LOCAL_IDENTIFICATION_FAIL_REDESIGN
  any gate fails; stop before MPC and redesign the excitation/state estimator
  or move to a causal multi-hypothesis plant-state belief formulation.
```

Neither route authorizes a controller, MPC expert, expert dataset, BC,
DAgger, or bounded residual RL.
