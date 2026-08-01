# Stage4.2R3c3T13S4 lattice-aligned transition holdout design

## 1. Prospective status and scientific question

This document is frozen after T13S3 completed and before T13S4 code, specs,
Card15 lattice choices, or results exist. T13S4 is the only real-TSC
continuation authorized by the T13S3 outcome:

```text
INTERFACE_COMPLETE_HOLDOUT_REQUIRED
```

T13S4 asks whether a causal, exactly serialized, lattice-resolved two-step
transition primitive trained on one member of two existing matched pairs can
predict the other member inside a non-vacuous prospective tube. It also
provides the first independent real-trajectory check of the retrospective
T13S2R1 readback nominal and its nonzero T13S3 interval.

It is not a real MPC, full identification campaign, new-history campaign,
observer certification, expert-data campaign, or robustness result.

## 2. Frozen evidence split

T13S1 used only nullspace direction `q1`. T13S4 uses the two `q2` pairs that
were never used by T13S1 probes or the T13S2R1 bias fit:

| Stratum | Offline role | Pair/history | Target | Delay/slew | Snapshot manifest SHA-256 |
|---|---|---|---|---|---|
| hard | development | `p5_q2_a0p900_gap2_settle4` / `plus_first` | `RZ_p10_m10` | 2 / 0.9 | `e40bc1f02a6559eef6f677683d5e0011e013f67ed5c4c6649f08824b02d030da` |
| hard | blind holdout | `p5_q2_a0p900_gap2_settle4` / `minus_first` | `RZ_p10_m10` | 2 / 0.9 | `11ba0651e04c5cc3cb16482f0f5bb7e6430425ff5a9886fd5bdca349727b8735` |
| easy | development | `p9_q2_a0p750_gap2_settle4` / `plus_first` | nominal | 0 / 1.0 | `b931836adcc4486454a470ee75981d76ca79664da72487a8151110a84bbec05d` |
| easy | blind holdout | `p9_q2_a0p750_gap2_settle4` / `minus_first` | nominal | 0 / 1.0 | `96554811c713b35cc42aa12914e2b4af41cf7ff1e58ae7ae015873855ee1edb8` |

The split is fixed before either new trajectory is run. Model construction
may open only the two development members. It must write and hash the frozen
model/tube before the evaluator opens either holdout member. The evaluator
records the exact input-open order.

These snapshots and task combinations were used in R3c1 controller
development. They are held out only from T13S1/T13S2R1 transition and
actuator development. Passing is not independent new-history or end-to-end
controller generalization.

Pair/history/prefix labels are experiment metadata only. They are forbidden
from every controller action, actuator calculation, causal feature, fitted
predictor input, hypothesis selector, and future MPC.

## 3. Exact rollout matrix

Each of the four contexts receives:

```text
fresh zero-instrumentation baseline                         1
3 modes x 2 signs x 2 issue windows                       12
fresh rollouts per context                                13
```

The complete campaign is:

```text
development trajectories                                  26
blind holdout trajectories                                26
fresh controller processes                                52
fresh TSC processes                                       52
total real trajectories                                   52
real MPC trajectories                                      0
```

The horizon ends at each task's unchanged formal hold endpoint: state 35 for
slew 1.0 and state 37 for slew 0.9. No 500 ms or long-hold claim is made.
Formal arrival remains state 25 or 27, respectively.

Probe trajectories are identification/holdout evidence and are forbidden
from every expert dataset.

## 4. Causal issue schedule

The physical effect states remain the source-authenticated schedule:

| Actuator setting | transport issue/cancel | effects | braking issue/cancel | effects |
|---|---:|---:|---:|---:|
| delay 0 / slew 1.0 | 2 / 3 | 3 / 4 | 16 / 17 | 17 / 18 |
| delay 2 / slew 0.9 | 0 / 1 | 3 / 4 | 14 / 15 | 17 / 18 |

At an issue step, the wrapper first obtains the current-run causal baseline
controller action. It then applies the exact T13S3 quantized-actuator
primitive to the current measured 14-coil state and that action. The result
defines the center Card15 fields. No future action, future measurement,
source action/result/current, wire/vessel current, or label is available.

At the adjacent cancellation step, the same procedure is repeated using the
then-current measurement and then-current causal controller action. The
wrapper applies the exact negative of its own already-issued physical Card15
field displacement. It does not use a baseline run's future action.

## 5. Frozen dynamic Card15 lattice rule

The original fixed `0.0075` probe is not rescaled. It is retired as below
the active Card15 lattice in 304/336 T13S1 command components. T13S4 chooses
a field-lattice displacement directly.

For center field `c_i` on coil `i`, enumerate exact neighboring values that
round-trip through the unchanged ten-character `format_number`. For intended
orthonormal mode vector `m`, define significant coils prospectively as:

```text
|m_i| >= 0.10 * max_j |m_j|
```

Let `g_i` be the smallest local symmetric Card15 field step in kA-turn for
which both `c_i + g_i` and `c_i - g_i` serialize and parse exactly and remain
symmetric about `c_i`. Define:

```text
lambda_min = max over significant i of
             (4 * g_i * 1000 / turns_i) / |m_i|
candidate lambda = lambda_min * [1, 2, 4, 8]
```

For each candidate, round `lambda * m_i` to the nearest integer multiple of
the local symmetric current step. Use the first candidate satisfying all
input-only gates:

```text
every significant coil moves at least 4 local Card15 steps
positive and negative target fields are exactly symmetric
coil-space cosine with intended mode                     >= 0.98
relative off-mode residual                               <= 0.15
incremental normalized action L-infinity                 <= 0.25
total normalized action inside [-1,1]
no current-limit clipping or scheduler rescaling
predicted maximum current utilization                    <= 0.55
```

If no candidate passes, that spec fails the offline preflight and no TSC
campaign starts. Candidate choice uses only the current measured state,
current causal action, authenticated actuator constants, mode basis, and
this frozen rule. Plant outcomes cannot affect it.

The cancellation uses the exact negative kA-turn displacement stored from
the issue step and must independently satisfy the same bounds. Requested
issue plus cancellation displacement is exactly zero in kA-turn.

## 6. Actuator holdout gate

The exact T13S3 nominal is:

```text
Card15 target readback
- [2,2,2,2,2,2,2,1,0,0,0,1,0,0] * 1e-6 kA-turn
```

Every coil retains the frozen radius of at least one `1e-6 kA-turn` unit.
For all 52 trajectories and all transitions:

```text
expected current components                  52 * horizon * 14
observed current components inside interval                  all
Card15 field length                                             10
current clipping, saturation, or rescaling count                 0
```

The exact component total is resolved prospectively from the two frozen
horizons and must be recorded before execution. A component outside the
interval is an actuator-model/uncertainty failure, not a plant or control
failure. The interval may not be enlarged after seeing holdout values.

For every one of 24 signed mode/window/context groups, require at the first
physical effect:

```text
target-field central symmetry exact
observed-current odd signal >= 4 frozen readback radii in L2
observed-current even/odd L2 ratio                    <= 0.10
```

## 7. Causal two-step transition response

For each probe, compare its first-effect and cancellation-effect states with
the matching fresh baseline. Use:

```text
y = (R, Z, vR, vZ, Ip)
scales = (0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)
```

Velocity uses current-run backward finite differences only. The immediate
response is the concatenated scaled response at the two effect states. The
input is the two measured 14-coil current displacements from baseline,
projected into the authenticated three-mode basis. Off-mode current remains
an explicitly reported uncertainty diagnostic; it is never discarded from
the raw trace.

Pre-effect differences retain the frozen T13 causality gates:

```text
R/Z       <= 1e-9 m
vR/vZ     <= 1e-7 m/s
Ip        <= 1e-4 A
coil current <= one frozen readback radius per coil
```

Each development signed pair must have scaled odd-response norm at least
ten times the source-derived numerical floor. At each stratum/window, the
three development odd input rows must have rank 3 and condition number
`<= 15`.

## 8. Frozen model and tube construction

For each allowed target/actuator stratum and each issue window, form the
three development odd input rows `X` and three development odd two-state
output rows `Y`. Fit exactly one minimum-norm local map:

```text
J = least_squares(X, Y)
```

The model input contains only the measured current displacement, formal
task step/window, target, finite actuator setting, and current/past causal
visible state. The model is not keyed by pair/history/prefix or source ID.

For each output component, freeze the additive radius from development data
before opening holdout raw:

```text
r_j = numerical_floor_j
      + 1.5 * max_development_signed_abs_residual_j
```

The tube is non-vacuous only if every component radius is no larger than:

```text
(0.003 m, 0.003 m, 0.010 m/s, 0.010 m/s, 1000 A)
```

The model artifact records training raw hashes, source hashes, `J`, tube,
support bounds, and its own SHA-256 before any holdout file is opened.

## 9. Blind holdout gates

The two `minus_first` contexts are opened only after the model artifact is
immutable. They are classified as finite clean extrapolation from the
matched development member, never as measured support.

All 24 signed holdout responses must satisfy:

```text
componentwise containment in the frozen model plus tube       24/24
scaled center relative error <= 0.10                           24/24
pre-effect causality                                            exact
model/tube artifact hash fixed before holdout open              true
forbidden controller/model input count                             0
```

The relative denominator is the measured scaled response norm, lower-bounded
only by the frozen numerical signal floor. No outcome-dependent
renormalization, scalar refit, phase shift, history selector, or tube
enlargement is allowed.

## 10. Authenticity, runtime, and safety gates

A scientific result exists only after:

```text
expected/actual/unique raw                             52/52/52
success and completed                                  52/52
fresh controller and TSC process                       52/52
exact snapshot and full-wire restart                   52/52
exact causal trace and declared horizon                52/52
runtime/environment/solver error count                     0
forbidden input count                                      0
maximum current utilization                           <= 0.55
```

Probe formal metrics are diagnostic and not an acceptance gate. The
underlying zero-instrumentation baselines must reproduce their exact R3c1
formal result and trajectory prefix; a mismatch is a restart/package/runtime
failure, not a transition-model result.

## 11. Outcome and route

After 52/52 authentic tasks, exactly one scientific route is allowed:

```text
LATTICE_HOLDOUT_PASS_LOCAL_MODEL_ONLY
  actuator interval, lattice, causality, signal, rank/condition,
  development tube, and all blind holdout gates pass

  authorization:
    implement and validate an offline robust finite-horizon MPC prototype
    using the T13S3 fail-closed interface and this finite local model;
    then preregister a separate minimal real-MPC sentinel

  not authorized:
    full 32-context control, expert data, BC, DAgger, or RL

LATTICE_HOLDOUT_FAIL_REDESIGN
  any scientifically valid actuator, signal, model, tube, or blind
  holdout gate fails

  action:
    preserve raw and distinguish actuator uncertainty, insufficient
    signal, off-mode quantization, hidden-state dependence, and local
    model error before any further physical expansion
```

Runtime, package, raw, or report bugs with unchanged physical semantics are
fixed separately; successful raw may be resumed only under the repository's
source-fingerprint and identity rules.

## 12. Required implementation and pre-run validation

Before any TSC run:

- implement exact dynamic lattice enumeration and fail-closed preflight;
- implement the development-before-holdout open-order guard;
- test positive, negative, exponent-boundary, zero-center, current-boundary,
  and cancellation lattice cases;
- test tube freeze/hash before holdout access and inject a forbidden-label
  regression;
- run compile, JSON parse, focused and complete tests, import closure,
  package/checksum checks, resume/fingerprint tests, and an isolated
  empty-directory deployment simulation;
- run an offline 52-spec audit with zero plant steps;
- validate exact server paths, Bash syntax, installed venv imports, fixed Ray
  capacity, PID/run/log capture, and complete Linux tests.

Large raw and full postprocessing remain on the server. Only compact
manifests, route metrics, hashes, and validation logs are downloaded.

Formal timing, R/Z tolerance, speed threshold, Ip threshold, and arrival
streak are unchanged. R3c4, the T11 bank, real MPC, expert data, BC, DAgger,
and bounded residual RL remain blocked during T13S4.
