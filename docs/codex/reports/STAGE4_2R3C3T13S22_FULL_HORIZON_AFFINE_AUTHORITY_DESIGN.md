# Stage4.2R3c3T13S22 full-horizon affine authority discriminator design

## Status and purpose

This design is frozen after the complete S21 campaign and its retrospective
single-probe route forensic, but before S22 implementation or any four-
direction combination result. S22 runs zero new TSC, Ray tasks, controller
rollouts, snapshots, or plant advances.

S22 asks one deliberately narrow question:

```text
Can a bounded affine combination of the four real S21 state-10 impulse
responses satisfy the unchanged formal tracking gate in all 40 contexts?
```

This is a model-class/authority discriminator. It is not a controller and
does not assume that an affine combination is physically realizable. T9's
measured interaction result remains binding.

## Exact source contract

S22 must authenticate:

```text
S21 execution package commit
  98dc353
S21 run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s21_runs/
  stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353
raw files / bytes / digest
  360 / 21,083,271 /
  8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4
training model
  a685d428eebcef10d7f6a36e3e6c8ada1b4c7177b6a94d52a516b390a2c997fd
calibrated tube
  eff9d987f46b824714456f75a2d4a602ca3f144a3009e2904c9023a33a0ade20
final result
  e72e66318836c11dac025b66a74682e8459d0c336dac5d0d27e54d5353c5e233
independent server postprocess
  d6bc5c3690cda4610586db6f03cf21c22d35b37d7cd82f3709572c45e5b7172e
```

All 40 contexts and all 8 signed probes per context are mandatory. No failed
context may be dropped or reassigned.

## Frozen response construction

For each context, let `y0(k)` be the baseline output and let `y_i+(k)` and
`y_i-(k)` be the actual plus/minus trajectories for the four frozen QR
directions. Outputs are:

```text
y(k) = [R(k), Z(k), vR(k), vZ(k), Ip(k)]
```

Velocity uses the exact 10 ms backward difference used by the frozen formal
metric. For states from the first response effect through the formal hold
endpoint, define:

```text
r_i+(k) = y_i+(k) - y0(k)
r_i-(k) = y_i-(k) - y0(k)
g_i(k)  = (r_i+(k) - r_i-(k)) / 2
h_i(k)  = (r_i+(k) + r_i-(k)) / 2
```

`g_i` is the odd affine response. `h_i` is reported as measured even/non-
affine residual and may not be silently discarded from the model-validity
conclusion.

The only decision is:

```text
alpha in [-1, 1]^4
y_affine(k, alpha) = y0(k) + sum_i alpha_i g_i(k)
```

Coefficients are one bounded state-10 issue/cancel family, not per-step MPC
commands. No coefficient outside `[-1,1]`, response rescaling, new basis,
target-specific threshold, or source future action is allowed.

## Frozen formal and numerical gate

The synthetic affine trajectory is evaluated by the exact existing formal
metric and timing policy that generated S21's diagnostic counts. The
250/270 ms arrival deadlines, 350/370 ms hold endpoints, 30 mm R/Z box,
0.1 m/s speed limit, 10 kA Ip threshold, and three-state arrival streak are
unchanged. Longer observation may not move the arrival deadline.

For each context S22 must deterministically maximize the exact frozen minimum
signed formal margin over `[-1,1]^4`. The implementation must use:

```text
fixed differential-evolution seed                     4201322
population multiplier                                      16
maximum generations                                        300
absolute / relative convergence tolerance        1e-10 / 1e-10
polish                                                      yes
independent forward evaluation of the returned trajectory   yes
coefficient bound tolerance                              1e-10
formal pass tolerance                                    1e-12
```

The unmodified baseline and all eight measured nodes must first reproduce
their raw formal results exactly. Any mismatch is a code/reporting failure,
not scientific infeasibility.

The primary gate requires:

```text
source/raw authentication                               360 / 360
baseline formal reproduction                             40 / 40
measured-probe formal reproduction                      320 / 320
finite four-direction construction                        40 / 40
optimizer completion                                      40 / 40
independent coefficient/formal check                      40 / 40
optimistic affine formal feasibility                      40 / 40
```

The even residual is reported in physical units and against the unchanged
S21 component caps `[0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]`. It is
a model-validity diagnostic, not a relaxed substitute for 40/40 formal
feasibility.

## Routes

If all primary gates pass:

```text
AFFINE_STATE10_AUTHORITY_PASS_COMBINATION_SENTINEL_REQUIRED
```

This authorizes only a separately preregistered, small real-TSC combination
sentinel that measures interaction and action execution. It does not
authorize a real MPC.

If any context is infeasible or the frozen optimizer/model check fails:

```text
AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED
```

This vetoes the frozen single-issue affine model class. It does not prove
global plant unreachability. The next design must identify task-relevant
multi-step/state-conditioned transitions rather than enlarge coefficients or
relax timing.

If raw, identity, formal-reproduction, or implementation checks fail, S22
has no scientific route until that error is repaired without changing the
model or gate.

## Claim boundary

S22 may never be described as a real controller, plant-restart campaign,
hidden-history robustness test, unseen-target test, noise test, disturbance
test, or long-hold test. Probe raw remains forbidden from expert datasets.
BC, DAgger, and bounded residual RL remain prohibited on either route.

