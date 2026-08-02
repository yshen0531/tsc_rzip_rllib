# Stage4.2R3c3T13S16 orthogonal fixed-basis local-identification design

## Status and question

This design is frozen prospectively before S16 controller code, raw, TSC, or
route selection. The S15 contexts and pre-action geometry are development
evidence, so S16 remains a development sentinel rather than an independent
holdout.

S16 asks the unchanged S15 within-trajectory identification question after
removing the known physical-field collinearity by a deterministic causal
change of basis. It does not weaken or reinterpret S15's failed condition
gate.

## Contexts and task matrix

S16 uses the same 16 factor-selected authenticated development contexts:

```text
16 orthogonal-basis calibration baselines
16 contexts x 4 native response directions x 2 signs = 128 probes
144 new authentic trajectories total
```

Every rollout starts from its exact authenticated R3b snapshot with a fresh
controller and fresh TSC process. No S15 failure raw is reused as a successful
trajectory. S16 trajectories are identification probes and are forbidden
from expert datasets.

## Frozen causal field-basis construction

At task step zero, before any plant effect, construct the four exact S15
native symmetric field increments in this global order:

```text
mode0_without_coil8
mode0_coil8_component
mode1
mode2
```

Let those 14-dimensional Card15 field columns be `D`. Require `rank(D)=4`.
Compute the reduced float64 QR decomposition `D=QR`, and flip each QR column
whose corresponding diagonal of `R` is negative, so the sign convention is
unique. Let `n_i` be the norm of native column `i`. The desired orthogonal
field columns are frozen as:

```text
q0 * n0
q1 * n1
q2 * n2
q3 * (0.6 * n3)
```

The `0.6` factor is a new prospective S16 safety amplitude. It is not a
post-hoc S15 threshold change. Each desired field column is converted to the
nearest exactly symmetric Card15 integer-grid displacement using deterministic
round-to-nearest counts and the existing center-exact repair search with
radius 16. No response value or plant effect enters this computation.

The final exact basis must satisfy in every baseline before response raw:

```text
physical rank                                             4
normalized condition                                <= 1.10
desired/exact field cosine                           >= 0.98
desired/exact relative off-direction residual        <= 0.15
positive and negative exact Card15 actions             both
incremental normalized action                        <= 0.25
current utilization                                  <= 0.55
```

The basis is immutable for that trajectory. Pair, history, prefix, regime,
source result/action, hidden wire/current, current-run future state, and
future response values are forbidden. QR depends only on the current-run
step-zero visible currents, the causal underlying action, fixed coil turns,
and the globally frozen four directions.

## Schedule and local estimator

The S15 schedule is unchanged:

```text
steps 0,2,4,6    + exact orthogonal columns 0,1,2,3
steps 1,3,5,7    - the same stored exact columns
steps 8--9       no calibration deviation
step 10          native response issue
step 11          native response cancel
```

The eight calibration codes remain the fixed adjacent `+e_i,-e_i` code.
Together with constant, normalized linear time, and centered quadratic time,
the frozen design remains rank seven with condition approximately 2.52938
and must pass `<=3.0` in every trajectory.

Only states 1--8 and already issued actions 0--7 enter the local estimator.
The four estimated input coefficients correspond to the exact orthogonal
columns. At step 10, the native response increment is projected into that
exact basis. The projection must have cosine at least 0.98 and relative
off-basis residual at most 0.15. Current-readback uncertainty is propagated
through the same linear map.

The authentic state-11 response is evaluated only offline against its matched
S16 baseline after all raw exists. The frozen point and provisional tube gates
remain:

```text
maximum scaled center-relative error                  <= 0.10
component tube multiplier                                  3
tube caps              (0.003 m, 0.003 m, 0.010 m/s,
                         0.010 m/s, 1000 A)
```

## Phase gates

The 16 baselines run first. The 128 probes may open only if all baseline and
zero-TSC lattice gates pass:

```text
success / fresh process / exact restart / causality       16 / 16
exact orthogonal field basis and geometry                 16 / 16
rank-seven drift-plus-input design                        16 / 16
eight exact calibration events                            16 / 16
four exact requested-zero-net pairs                       64 / 64
Card15/action/current/slew gates                           16 / 16
native response projection coverage                      128 / 128
```

Final execution and response gates are:

```text
all raw parse/success/restart/causality                  144 / 144
pre-response semantic equality                          128 / 128
response issue/cancel and exact zero net                 128 / 128
response projection support                              128 / 128
center relative error <= 0.10                            128 / 128
provisional tube containment and cap                     128 / 128
forbidden inputs, clipping, open-order violations                  0
maximum current utilization                                    <=0.55
```

Formal tracking remains diagnostic. Arrival is still due by 250/270 ms and
hold evaluation ends at 350/370 ms. This is not a long-hold test.

## Routes

```text
ORTHOGONAL_FIXED_BASIS_IDENTIFICATION_PASS_FRESH_CAMPAIGN_REQUIRED
  all gates pass; authorize only a separately frozen whole-pair
  training/calibration/fresh-context identification campaign.

ORTHOGONAL_FIXED_BASIS_IDENTIFICATION_FAIL_BELIEF_MPC_REDESIGN
  any gate fails; stop this local point-estimator route and design a causal
  multi-hypothesis plant-state belief and robust finite-horizon MPC route.
```

Neither route authorizes an MPC expert, expert data, BC, DAgger, or bounded
residual RL.

