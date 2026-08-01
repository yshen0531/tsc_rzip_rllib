# Stage4.2R3c3T13 finite-horizon restart MPC architecture specification

## 1. Status and route

This document completes the no-new-TSC T13 architecture deliverable. It is a
controller specification and evidence map, not controller code and not a
real closed-loop result.

The V4 time-resolved audit vetoed the fixed Stage3.4 lifted Jacobian as an
unqualified restart predictor in all 1,504 comparisons. The final T13 route
is therefore:

```text
MINIMAL_SENTINEL_REQUIRED
```

The separately frozen T13S1 sentinel must identify the missing local
transition object before this architecture may be implemented. T13S1 PASS
would authorize only offline model work. It would not authorize a real MPC,
a full identification campaign, R3c4, or expert-data collection.

## 2. Immutable task clock and indices

Let `k` denote the formal task state index after authentic restart. It is
always initialized as:

```text
k = 0 at the loaded restart snapshot
```

An action `u_k` is issued after observing state `k` and can first affect a
future state according to the authenticated actuator queue. Formal time may
not be inferred from a nearest visible R17 phase.

The immutable endpoints are:

| Actual slew | Arrival deadline `H_arr` | Hold endpoint `H_hold` |
|---:|---:|---:|
| 1.0 or 1.1 | state 25 / 250 ms | state 35 / 350 ms |
| 0.9 | state 27 / 270 ms | state 37 / 370 ms |

The arrival streak is exactly three states. The formal constraints remain:

```text
|R - R_target| <= 0.03 m
|Z - Z_target| <= 0.03 m
sqrt(vR^2 + vZ^2) <= 0.1 m/s
|Ip - Ip_target| <= 10,000 A
```

The local model coordinate `xi_k` is separate:

```text
xi_k = Phi(causal current-run state estimate, queue, target, uncertainty)
```

`xi_k` may choose a local model, trust region, or uncertainty set. It may
never change `k`, `H_arr`, `H_hold`, or the three-state arrival streak.

## 3. Causal controller state

At formal state `k`, the controller state is

```text
c_k = (
  k,
  y_0:k,
  xhat_k,
  P_k,
  e_k,
  eta_k,
  delta_u_previous,
  Icoil_k,
  q_k,
  Theta_k,
  W_k,
  r_target,
  r_nominal_0:H_hold,
  previous_certified_plan
)
```

where:

- `y_0:k` is only the current-run causal measurement history;
- `xhat_k` contains R, Z, Ip, estimated vR/vZ, and any observer state that is
  inferable without hidden labels;
- `P_k` bounds estimation error, including the unknown first-sample velocity;
- `e_k` is target-relative error;
- `eta_k` is the controller integral/anti-windup state;
- `delta_u_previous` is the previous physical three-mode correction;
- `Icoil_k` is the measured/current-run 14-coil state;
- `q_k` is the exact queue of commands already issued in this run;
- `Theta_k` is a causal set of actuator/model hypotheses;
- `W_k` is a bounded additive model-error/tube set;
- `r_nominal` is a deployed target-conditioned prior, not a looked-up source
  result or future source action;
- `previous_certified_plan` exists only if a prior solve in this same run was
  independently checked as robustly feasible.

At restart, unavailable velocity is not silently set to known zero. It is
initialized as an interval/covariance consistent with the first causal
finite difference. Integral, previous correction, and the command queue are
restored only when authenticated current-run checkpoint fields exist;
otherwise their explicit fresh-start values and uncertainties are traced.

Hidden vessel/eddy currents are never estimated from a pair/history label.
If causal observations do not identify them, their effect remains inside
`Theta_k`/`W_k` as a multi-hypothesis or tube uncertainty.

## 4. Decision variable and actuator dynamics

For each candidate arrival state `a <= H_arr`, solve for a full remaining
sequence

```text
U_k = {delta_u_j|k in R^3 : j = k, ..., H_hold - 1}
```

in the authenticated three physical modes. These are per-issue-step
commands, not coefficients of an R3c3/T1--T11 whole-episode probe bank.

The optimizer must include the complete actuator mapping inside the problem:

```text
q_{j+1|k}       = Queue(q_{j|k}, delta_u_{j|k}, d)
u_effective_j   = GainSlew(q_{j|k}, g, s, delta_u_{j|k})
DeltaIcoil_j    = M14x3 u_effective_j
Icoil_{j+1|k}   = Icoil_{j|k} + DeltaIcoil_j
```

for every active hypothesis `(d, g, s) in Theta_k`. Already issued queue
entries are immutable decision constants. New decisions may affect only
unissued slots. The 14-coil command, current, and slew constraints are
checked jointly; a nonlinear scheduler may not rescale the first action
after an otherwise unaware lifted solve.

The existing 14-by-3 mode map can be reused only after exact hash
authentication. The scheduler code may be reused as a constraint/evaluation
implementation, but not as a post-solve safety substitute.

## 5. Prediction contract

The required predictor is state- and issue-time-conditioned:

```text
z_{j+1|k} = f_theta(z_{j|k}, u_effective_j, xi_{j|k}) + w_j
theta in Theta_k
w_j in W(xi_{j|k}, u_effective_j)
```

with output

```text
h(z_j) = (R_j, Z_j, vR_j, vZ_j, Ip_j, Icoil_j)
```

The exact implementation may be a locally affine state-space model, a
causal FIR model with explicit state realization, or a nonlinear local model
only after prospective identification/holdout validation. In every case it
must expose:

1. the state and issue-time support used for each prediction;
2. interpolation versus extrapolation status;
3. a bounded residual set `W` derived without current-run future outcomes;
4. a trust-region test before the action is accepted;
5. a continuation through weak-slew state 37.

The frozen Stage3.4 Jacobian may be retained as a diagnostic prior or warm
start. It may not provide the certified constraint prediction: it failed
576/576 signed, 896/896 finite-node, and 32/32 interaction relative gates
and ends at state 35.

The target-conditioned R17/Stage3.4 nominal trajectory may be used as a
finite reference and warm start. It may not be replayed as source future
actions and may not replace feedback from the authentic restart state.

## 6. Hard robust constraints

For each enumerated candidate arrival state `a`, the solve must require the
following for every model/actuator hypothesis and every tube realization.

### Physical and actuator constraints

```text
three-mode issue-command bounds
14-coil command bounds
14-coil current bounds
per-step slew bounds
exact delay-queue dynamics
gain/slew uncertainty bounds
model trust-region membership
```

### Arrival and hold constraints

The three-state arrival streak is enforced at `a-2, a-1, a`. From state `a`
through `H_hold`, require robustly:

```text
|R_j - R_target| <= 0.03 m
|Z_j - Z_target| <= 0.03 m
sqrt(vR_j^2 + vZ_j^2) <= 0.1 m/s
|Ip_j - Ip_target| <= 10,000 A
```

The last issue decisions must include every queue effect that can occur by
`H_hold`. No action whose effect arrives after the formal endpoint may be
credited with satisfying an earlier deadline.

No slack variable may relax these formal or actuator constraints. Candidate
arrival times are enumerated from the unchanged allowed set; the optimizer
does not move the deadline.

## 7. Objective hierarchy

Only after hard robust feasibility is established may the controller
minimize a secondary objective such as

```text
J = sum_j ||h(z_j) - r_nominal_j||_Q^2
  + sum_j ||delta_u_j||_R^2
  + sum_j ||delta_u_j - delta_u_{j-1}||_S^2
  + terminal_margin_penalty
  + uncertainty/tube_size_penalty
```

The target-conditioned nominal preserves transport direction. The objective
may trade tracking, control effort, braking smoothness, and robustness only
inside the hard feasible set. It may not convert arrival, deceleration,
hold, current, queue, or trust-region requirements into soft evidence.

## 8. Solver, certification, and fallback

At every step:

1. update the causal observer and exact already-issued queue;
2. enumerate allowed candidate arrival states not later than `H_arr`;
3. solve the robust sequence problem for each viable candidate;
4. independently forward-check the selected sequence, all hypotheses, all
   actuator limits, and every formal margin;
5. issue only the first newly certified command;
6. store the remaining sequence as a same-run fallback candidate.

Fallback order is deterministic:

```text
1. preserve already-issued queue entries exactly;
2. shift the previous same-run certified plan if it still passes a fresh
   independent robust-feasibility check;
3. otherwise issue zero incremental correction/current hold within actuator
   limits, mark the solve infeasible, and terminate the scientific rollout
   as a control failure after the safe step.
```

At fresh restart there is no previous certified plan. A solver timeout,
numerical failure, model-support violation, or independent-check mismatch
must therefore be visible as an explicit control failure. It may not fall
back to a source future action, a hidden label, or an untraced nominal replay,
and it may not be reported as a formal pass.

## 9. Trace-audit contract

Every action row must record at least:

```text
formal task step and wall-clock timestamp
local model coordinate and support/interpolation/extrapolation class
measurement indices used and causal velocity estimate
state estimate, uncertainty/covariance, and active hypotheses
integral and previous-correction state
14-coil current and queue before/after issue
target-conditioned reference identifier/hash
desired three-mode command
14-coil commanded and predicted applied increments
actual trace command after the current step
candidate arrival state and formal time-to-go
predicted nominal trajectory and robust tube bounds
all formal, actuator, current, slew, trust, and model-validity margins
solver identity/status/iterations/time/objective
independent certification status
fallback level and reason
source/hidden/future-input prohibition flags
```

The raw trajectory must separately record the resulting observed coil and
plant state. Trace command and finite-precision observed current difference
must not be conflated.

## 10. Causality and input policy

| Candidate information | Controller use | Rule |
|---|---|---|
| current/past R, Z, Ip | allowed | current run only |
| causal finite-difference/observer velocity | allowed | uncertainty traced |
| current/past measured coil currents | allowed | current run only |
| commands already issued in current run | allowed | exact queue state |
| controller integral/previous correction | allowed | authenticated same-run state |
| target R/Z/Ip | allowed | task definition |
| deployed target-conditioned nominal prior | allowed with limits | reference/warm start only; hash traced |
| bounded actuator/model hypotheses | allowed | derived prospectively from allowed evidence |
| source action or source future action | forbidden | no replay shortcut |
| source result/formal verdict | forbidden | no outcome input |
| source/current wire or vessel currents | forbidden | not observable controller state |
| current-run future measurements/results | forbidden | causal online control only |
| pair/history/prefix/development-case label | forbidden | development metadata only |
| nearest visible R17 phase as formal time | forbidden | local coordinate cannot alter task clock |
| probe schedule/result in expert data | forbidden | identification-only evidence |

An experiment wrapper may apply a prospectively frozen sentinel intervention
at its issue time. That schedule is instrumentation, not an input to the
underlying baseline controller and never enters an expert dataset.

## 11. Source call graph and disposition

The inherited active chain is:

```text
R3c1/R3c2 task controller
  -> R3b FreshTaskController
  -> R2 PersistentController
  -> Stage4.1R3 fixed-J least-squares solve
  -> Stage4.1R3 post-solve PhysicalCoilScheduler
  -> Stage4.1R9 queue
  -> Stage3.4 target nominal/lifted model
```

| Component | Exact inspected source SHA-256 | Disposition |
|---|---|---|
| R17 closure | `207be3971727f7eab393d36fd1c7b1669d793eb94bc4e09eeb120d1d2485989c` | evidence/reference only; no weak-slew patch replay as general MPC |
| R14 target-conditioned solve | `c632e1e73ab6e00bfa25f6811f85ea0433e8a942250f6ae74e549ae1dcf8a2f9` | reuse target-conditioned reference concept; replace solver semantics |
| Stage4.1R3 solver/scheduler | `d2439a6a84107ff3b3024f7e544381f99b6d4c29396c9bc9c67ff0c957b50509` | replace fixed-J soft solve and post-projection; reuse authenticated actuator utilities only inside joint constraints |
| R2 persistent checkpoint | `8dffdc6f6a9b851577e3a4bc98102893d8abbb418be6381d14fc54d611bf711c` | reuse causal controller-state/queue schema |
| R3b fresh restart | `edf6188581a01dbe6f726e6dbd941e0c9a35770e57e599d57962d832a51fbf71` | reuse authentic state-load and paired development contexts; replace zero-known-velocity assumption |
| R3c1 visible manifold | `4ee7eda0e06d7c771322f33bec9f0bb31c5593937821b494d81fa6c615eaa76d` | evidence baseline only; static phase selection prohibited as state reconstruction |
| R3c2 zero-nominal regulator | `0e5c487276d13ed72500cc9a8d904499092a236ba232c5b3046142d49454534e` | prohibited architecture; genuine local-damping failure evidence |
| T9 interaction probe | `ea674921f19e97ff3eefefc1c6d49060e433328fbf5700b80caf501c5e4ae6c9` | evidence of finite interaction only |
| T11 persistent-step probe | `dde7f246be5f9ea805944a3cdef4020e87fcda4b64af46b93c27cc0114c6b942` | evidence only; response bank prohibited |

## 12. Evidence coverage with exact identities

| Architecture claim | Raw-backed evidence | Exact identity | Supported conclusion |
|---|---|---|---|
| finite target-conditioned transport | R17 selected 18 cases | selected expert fingerprint `95ef2cdbdbbbecdf0a58b316b44cca4fb788613b1a87c1f9b48e897175b2c112` | finite two-target static-grid prior only |
| authentic plant restart | R1c snapshot bank | 18 manifests, 144 payload files, 2,133,646,442 bytes, zero mismatch | exact finite state-load mechanism |
| causal controller restart | R2 | input inventory `5d45bcb381624da2e428a080c0876bf2472f7f2598e05f84ebc78337ec0a0e81` | exact 18-case checkpoint/queue suffix |
| authentic restart controller failure | R3c1 | raw digest `3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e` | genuine 16/32 baseline result |
| zero-nominal local damping failure | R3c2 | raw digest `b01a07c9dc136677f323d292d0f9388904cc39663514bf4025f4fa4fed767653` | genuine 12/32; all prefix-5 failed |
| local signed schedule response | R3c3/T1/T2/T6/T9/T11 | six raw digests in the T13 report; 1,408 files | finite schedule responses, not Markov transitions |
| interaction | T9/T10 | T9 raw digest `e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2` | material interaction at measured corners |
| formal-gap alignment | T12 | T11 raw digest `f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3` | condition-first route veto; 0/16 repairs |
| fixed-J prediction | T13 V4 | audit `af644ef8e342e03b9b72215eb518b62ea9e7898842851681e5b0cc585d160b0d` | fixed Stage3.4 J vetoed on all 1,504 comparisons |
| current headroom | T8/T11 | T11 maximum observed utilization `0.3904` under gate `0.55` | finite headroom, not reachability |
| matched hidden-history response | R3c3/T1/T11 finite pairs | exact stage raw digests above | finite paired consistency only; no independent robustness |

## 13. Model-gap map

| Dimension | Measured support | Interpolation currently defensible | Extrapolation/unknown |
|---|---|---|---|
| restart state | four selected R3b pair states, two prefix strata | none for certified constraints | arbitrary restart state/manifold |
| hidden history | plus/minus matched development pairs | bounded finite pair comparison only | independent history, latent-state observer |
| target | nominal and RZ `+10/-10 mm` development targets | reference interpolation only, not certified dynamics | unseen/continuous R/Z/Ip targets |
| delay/slew | restart raw at `(0,1.0)` and `(2,0.9)`; R17 static finite grid | none for restart predictor | continuous delay/gain/slew, delay 1 restart coverage |
| issue time | whole-schedule effects beginning at states 3 and 17, plus other finite schedules | no isolated transition interpolation | arbitrary per-step transition response |
| action amplitude | finite signed amplitudes through the T11/T9 development envelope | small local interpolation only after a validated model | larger amplitudes and saturation boundary |
| action interaction | T9 measured two-factor corners | only those exact finite corners | arbitrary multi-step/multi-mode sequence interaction |
| prediction horizon | raw observed through state 50; Stage3.4 predicts through 35 | none beyond authenticated model support | weak states 36--37 certified prediction, longer hold |
| noise | deterministic clean sensing | none | measurement noise and observer robustness |
| disturbance | no independent recovery campaign | none | disturbance rejection/recovery |
| plant mismatch | same TSC source/twin | none | Jacobian/plant error and deployment shift |

The blocking gap is the isolated per-issue-step response at authentic
restart states and at both transport and braking issue times. Existing
persistent/held probes conflate many future increments and cannot be silently
converted into a state-space transition model.

## 14. Implementation boundary after T13

The only authorized next scientific design is the separately preregistered
T13S1 sentinel. Until its result is available:

- do not implement this controller;
- do not build a T11 response bank;
- do not fit the failed Stage3.4 predictor to outcomes;
- do not launch a 32-context identification campaign;
- do not run R3c4 or a real MPC;
- do not enter BC, DAgger, or bounded residual RL.

If T13S1 passes, the next task is an offline transition-model interface and
prospective holdout design. If it fails scientifically, stop and redesign
the observation/model/action resolution. Runtime or reporting defects are
handled separately and do not become scientific FAIL or PASS.
