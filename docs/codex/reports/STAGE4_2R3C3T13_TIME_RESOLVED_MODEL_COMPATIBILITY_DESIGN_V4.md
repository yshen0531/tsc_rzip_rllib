# Stage4.2R3c3T13 time-resolved model compatibility design V4

## Status

V4 is a raw-schema correction frozen before any Jacobian multiplication or
prediction result. It inherits V3 completely and changes only the accepted
full raw trajectory/trace lengths for R3c3 and T1.

The first complete V3 invocation authenticated model/source hashes and began
raw authentication, then stopped at the first weak-slew R3c3 member:

```text
file                         s42r3c3_03e6dd8084d0f1b44a9a.json.gz
success / completed          true / true
forbidden-input checks       all clean
actual trajectory / trace    38 / 37
incorrect code expectation   36 / 35
Jacobian multiplications     0
output directory created     no
```

The exact all-raw length inventory is:

```text
R3c3  delay 0 / slew 1.0       128 x (36 trajectory, 35 trace)
R3c3  delay 2 / slew 0.9       128 x (38 trajectory, 37 trace)
T1    delay 0 / slew 1.0        64 x (36 trajectory, 35 trace)
T1    delay 2 / slew 0.9        64 x (38 trajectory, 37 trace)
T2                                  160 x (51 trajectory, 50 trace)
T6                                  224 x (51 trajectory, 50 trace)
T9                                  224 x (51 trajectory, 50 trace)
T11                                 416 x (51 trajectory, 50 trace)
```

The 38/37 weak-slew length is the authentic unchanged 370 ms formal hold,
not an extra or inconsistent trajectory. V3's single fixed 36/35 expectation
was a schema bug.

## Sole V4 change

Authenticate each full raw member against the exact actuator-conditioned
length above. Then, for every stage and actuator case, use only:

```text
states 0 through 35       36 rows
action steps 0 through 34 35 rows
```

as the Stage3.4 350 ms feature/input. States 36/37 and 36/37 action rows in
the weak raw remain authenticated and preserved but are not silently fed to
the 175-by-105 model.

No evidence identity, action reconstruction, numerical threshold,
prediction metric, comparison count, causality gate, formal timing, route
rule, or prohibition changes. The complete audit must use a new V4 output
identity.
