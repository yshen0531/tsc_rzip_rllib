# Stage4.2R3c3T13S2R1 readback-residual forensics design

## 1. Status and reason

T13S2 completed its frozen read-only audit and reconstructed 36,400 Card15
target-current components from exact source semantics. Only 13,000 matched
the subsequently observed `coil_currents.csv` current within `1e-9 A`; the
maximum difference was `1.0000000003174137e-5 A`. T13S2 therefore correctly
routed to `ACTUATOR_MAPPING_IMPLEMENTATION_GAP`.

This T13S2R1 design is frozen before its code or output exists. It is a
separate read-only forensic of the unresolved target-versus-readback layer.
It does not modify or rerun T13S2, change its gate, or reinterpret its result.
It runs no controller, Ray, `gotsc`, TSC, or plant step.

## 2. Immutable inputs

T13S2R1 authenticates the same 52 T13S1 raw files, exact environment files,
run inventory, package fingerprint, `inputa.py`, and `coil_order.py` used by
T13S2. It also authenticates the exact T13S2 report and manifest:

```text
T13S2 report
  9ef183d20f3354d11bb70c2324bade6829879f00c05dd96b99c1312bcfd53d58
T13S2 manifest
  564569ec948399792d2db49c4d5742e70a2b20c9ad48efaad7eda34f95f096dd
```

Raw remains server-side and immutable.

## 3. Fixed residual representation

For each T13S2 Card15 target and observed next current, compute in TSC units:

```text
residual_kAt = (target_A - observed_A) * turns / 1000
output_grid_units = residual_kAt / 1e-6
```

The `1e-6 kA-turn` grid is not a replacement acceptance threshold. It is the
observed CSV readback resolution being tested. Report:

- maximum distance from an integer grid unit;
- signed unit histogram;
- per-coil/turn unit support;
- whether each coil's residual unit is constant across all 2,600 transitions;
- requested-action, clipping, and current-value dependence diagnostics.

No plant output is used to select a residual model.

## 4. Baseline-only calibration and probe holdout

To test whether the residual is a fixed readback/actuation bias rather than a
probe-outcome fit:

1. use only the four extended baseline runs (200 transitions, 2,800 coil
   components) to identify a per-coil integer residual unit, but only if that
   unit is exactly constant within every baseline sample;
2. freeze those 14 units in memory;
3. predict the observed next currents for all 48 signed probe runs (2,400
   transitions, 33,600 coil components);
4. report exact equality and the unchanged `1e-9 A` numerical comparison.

This split is a retrospective development-set diagnostic because the
aggregate T13S2 residual was already inspected. It is not an independent
scientific holdout and cannot certify future contexts, noise, continuous
parameters, or a point plant model.

## 5. Route

```text
baseline per-coil residual not constant
or signed-probe holdout not within 1e-9 A
  -> UNRESOLVED_STATE_OR_VALUE_DEPENDENT_ACTUATOR_READBACK

baseline per-coil residual constant
and signed-probe holdout all within 1e-9 A
  -> FIXED_DEVELOPMENT_READBACK_BIAS_IDENTIFIED
```

Both routes require a quantized multi-hypothesis/tube actuator interface.
The second route permits implementing the fixed development bias as a traced
nominal term surrounded by a nonzero uncertainty set. It does not permit
setting uncertainty to zero or authorizing a real MPC/TSC campaign.

## 6. Output and prohibitions

The new output identity is `Stage4.2R3c3T13S2R1`. It writes one compact
report and one manifest in a new directory. The manifest records raw copied
or modified `0` and controller/Ray/`gotsc`/TSC/plant steps `0`.

T13S1 remains `SENTINEL_FAIL_STOP_IDENTIFICATION`; T13S2 remains
`ACTUATOR_MAPPING_IMPLEMENTATION_GAP`. Formal timing, physical gates,
forbidden controller inputs, probe exclusion, and all BC/DAgger/RL blocks
remain unchanged.
