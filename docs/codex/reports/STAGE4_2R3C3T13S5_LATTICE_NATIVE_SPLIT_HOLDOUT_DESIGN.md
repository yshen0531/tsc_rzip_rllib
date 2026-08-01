# Stage4.2R3c3T13S5 lattice-native split-direction holdout design

## 1. Status and purpose

This design is frozen before T13S5 implementation or real TSC output. It is
a new experiment identity after the final T13S4 offline design failure. It
does not modify or reinterpret T13S4.

T13S5 asks whether a finite, quantization-aware local two-transition model
can be identified and held out when the input directions respect the exact
Card15 topology. Even a complete PASS authorizes only an offline robust
finite-horizon MPC prototype and a separately preregistered minimal real-MPC
sentinel.

## 2. Evidence and design-only preflight

The exact zero-TSC route audit is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s4_route_audits/
t13s5_arm_steps_20260801_21df2dc/
t13s5_split_return_first_feasibility.json
```

```text
SHA-256
  378ff7d945a10b4d5c544460ed733cdbe0c25004d07b651af9f03a5c1f5a478b
context/window actuator preflights                         8/8 PASS
four-direction input rank                                 4/4 in 8/8
maximum input condition                                 7.9547833 <= 15
maximum issue incremental normalized Linf               0.1028397 <= 0.25
maximum selected cancel incremental normalized Linf     0.1873576 <= 0.25
selected exact return-to-stored-center cancellations        48/64
selected exact current-center negative cancellations        16/64
raw / plant / TSC steps                                      0/0/0
```

This is only action/serialization/input-geometry feasibility. It contains no
new plant response and cannot count as identification or MPC evidence.

## 3. Independent evidence split

Reuse the same four q2 source restart contexts because no T13S4 TSC raw was
created:

```text
development
  p5 plus_first, delay 2, slew 0.9, RZ +10/-10 mm
  p9 plus_first, delay 0, slew 1.0, nominal target

blind holdout
  p5 minus_first, delay 2, slew 0.9, RZ +10/-10 mm
  p9 minus_first, delay 0, slew 1.0, nominal target
```

The model builder must open and authenticate all 34 development raw files,
write and hash the model/tube artifact, and only then open any of the 34
holdout raw files. Pair, history, prefix, source ID, result, action, hidden
wire current, and future values are forbidden model/controller inputs.

## 4. Lattice-native input directions

At each issue state authenticate the exact three physical mode vectors. Form
four fixed, label-independent directions in native TSC coil order:

```text
d0_rest
  physical mode 0 with coil index 8 set to zero, then unit-normalized

d0_coil8
  the signed coil-index-8 component of physical mode 0 as a unit vector

d1
  authenticated physical mode 1

d2
  authenticated physical mode 2
```

The span contains the original three-mode controller space; the split is an
identification coordinate, not a fourth MPC actuator. A later controller may
still command only the authenticated three physical modes.

For `d0_rest`, `d1`, and `d2`, choose the smallest exact symmetric Card15
displacement with at least one local formatter step on every significant
coil. For `d0_coil8`, choose the smallest exact symmetric integer displacement
whose physical current magnitude is at least `0.08 A`. The exact achieved
magnitude, local step, integer count, and field string must be traced.

For every issue candidate require prospectively:

```text
exact target-field central symmetry                         true
minimum significant local steps                               >= 1
coil-space cosine                                            >= 0.98
relative off-direction residual                              <= 0.15
incremental normalized action Linf                           <= 0.25
total normalized action abs                                  <= 1.0
current utilization                                          <= 0.55
action saturation/current clipping                               0
```

The one-step floor is not a retrospective T13S4 PASS. T13S4 remains failed
at four steps. T13S5 replaces the per-arm four-step heuristic with exact
formatter separation plus the unchanged measured-current signal gate below.

## 5. Causal return-first cancellation

At issue time store only the current-run exact Card15 center fields and the
issued displacement. At the adjacent cancel step, after computing the normal
causal R3c1 baseline action:

1. Construct the exact action returning to the stored issue-center fields.
2. If and only if it reproduces every stored field exactly and passes the
   unchanged incremental, total-action, current, clipping, and utilization
   bounds, select it.
3. Otherwise construct the exact negative issued displacement relative to
   the current causal baseline center and select it only if every same bound
   and exact-field gate passes.
4. If neither passes, fail closed before `env.step`.

The selector may not use direction outcome, sign counterpart, pair/history,
prefix, source trace, wire current, or future information. Trace the selected
method and both candidate gate results. The model input is the measured
two-transition 14-coil current displacement; it may not assume ideal zero net
when the selected method differs.

## 6. Schedule and exact matrix

The physical effect states and formal horizons remain:

```text
delay 2 transport: issue 0, cancel 1, effects states 3 and 4
delay 2 braking:   issue 14, cancel 15, effects states 17 and 18
delay 0 transport: issue 2, cancel 3, effects states 3 and 4
delay 0 braking:   issue 16, cancel 17, effects states 17 and 18
```

```text
per context
  1 fresh formal-end baseline
  + 4 directions * 2 signs * 2 windows
  = 17 trajectories

total
  4 contexts * 17 = 68 fresh authentic TSC trajectories
development / blind holdout = 34 / 34
signed response groups = 32
expected current components = 34*37*14 + 34*35*14 = 34272
```

The p5 horizon is state 37 and the p9 horizon is state 35. These are exactly
the immutable formal hold endpoints, not long-hold tests.

## 7. Actuator, causality, and signal gates

For all 68 trajectories and 34,272 action-transition current components:

```text
fresh controller and fresh TSC process                       68/68
exact authentic snapshot/full-wire restart                   68/68
exact causal trace and formal horizon                         68/68
T13S3 measured current inside frozen interval             34272/34272
runtime/solver/saturation/clipping/forbidden-input errors          0
maximum current utilization                                  <= 0.55
```

At every signed group first effect require:

```text
pre-effect R/Z difference                                <= 1e-9 m
pre-effect velocity difference                         <= 1e-7 m/s
pre-effect Ip difference                                  <= 1e-4 A
pre-effect coil difference                 <= one frozen radius/coil
measured-current odd signal             >= 4 frozen radii in L2
measured-current even/odd L2 ratio                       <= 0.10
```

No threshold may be enlarged after development or holdout output is seen.

## 8. Four-input local model and tube

For each development stratum and window, use the four measured odd input
rows and the scaled two-effect-state outputs:

```text
y = (R, Z, vR, vZ, Ip)
scales = (0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)
```

Require input rank 4 and condition `<= 15`, then fit exactly one minimum-norm
local map from the measured 14-coil/two-transition input coordinate to the
ten scaled output components. Do not discard measured off-direction current.

Freeze componentwise additive tube radii using only development residuals:

```text
radius = numerical floor + 1.5 * maximum development signed residual
caps = (0.003 m, 0.003 m, 0.010 m/s, 0.010 m/s, 1000 A) at each effect state
```

The model artifact must include all development raw hashes, source hashes,
exact direction definitions, achieved lattice counts, cancellation methods,
support bounds, fit, tube, and its own SHA-256 before holdout access.

## 9. Blind holdout gates

All 32 signed holdout trajectories must satisfy without refit:

```text
componentwise containment in frozen model plus tube              32/32
scaled center relative error <= 0.10                              32/32
pre-effect causality                                               exact
model/tube hash fixed before holdout open                           true
forbidden model/controller input count                                 0
```

The relative denominator is the measured scaled response norm bounded only
by the frozen numerical floor. No scalar normalization, sign-specific fit,
phase shift, history selector, tube enlargement, or outcome-dependent
direction change is allowed.

## 10. Outcome routes

```text
LATTICE_NATIVE_HOLDOUT_PASS_LOCAL_MODEL_ONLY
  every execution, restart, actuator, causality, signal, input-rank,
  development-tube, and blind-holdout gate passes

  authorization:
    implement and validate an offline robust finite-horizon MPC prototype
    using the T13S3 interface and the finite T13S5 local model;
    preregister a separate minimal real-MPC sentinel

LATTICE_NATIVE_HOLDOUT_FAIL_REDESIGN
  any scientifically valid gate fails

  action:
    preserve all raw and separate actuator uncertainty, input conditioning,
    signal, nonlinear interaction, hidden-history dependence, and local
    model/tube error before any physical expansion
```

Runtime/package/report defects with unchanged semantics are repaired under a
new package identity; completed successful raw may be reused only under the
repository resume rules. Probe trajectories are forbidden from expert data.

R3c4, full 32-context real MPC, expert collection, BC, DAgger, and bounded
residual RL remain blocked during T13S5. Formal timing and all tolerances are
unchanged.
