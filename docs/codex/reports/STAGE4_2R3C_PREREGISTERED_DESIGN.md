# Stage4.2R3c preregistered design

Date frozen: 2026-07-30 Asia/Shanghai

## 1. Purpose and status

Stage4.2R3c is a controller-development experiment. It tests whether causal
visible-state phase alignment repairs the specific different-initial-state
failure observed in R3b.

R3c is not an independent hidden-history confirmation because its controller
design was chosen after inspecting R3b and it reuses the exact four selected
R3b snapshot pairs. Even a complete PASS must be followed by R3d on new,
unseen, prospectively generated histories.

Planned identities:

```text
stage
  Stage4.2R3c

package revision
  r42r3c_visible_state_phase_aligned_mpc_v1

controller revision
  visible_state_phase_aligned_mpc_v42r3c
```

## 2. Locked source evidence

R3c may use only the exact R3b run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/
stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526
```

Required source fingerprints:

```text
R3b implementation commit
  8fb1534

R3b package revision
  r42r3b_confirmatory_hidden_history_v1

R3b controller revision
  confirmatory_hidden_history_initial_state_mpc_v42r3b

R3b run inventory digest
  301a3ad2be01c83209d8e260c1a8c80f090d01afafb9c173f63cf9219caac8fc

R3b server audit SHA-256
  f1e907888e19846d07099714d4b581e26aac80c5675a373364d396db78130831

R3b raw control forensics SHA-256
  975205eff41f62d319e4f6e22643bb687461e42d3c73c1d09f0424f2a7c5cf32
```

Required selected pairs:

```text
p5_q1_a0p900_gap2_settle4
p5_q2_a0p900_gap2_settle4
p9_q1_a0p750_gap2_settle4
p9_q2_a0p750_gap2_settle4
```

The eight selected snapshot directories and their manifests must be
authenticated against R3b raw state-generation results and the full run
inventory. Snapshot payloads are read in place on the server and are not
copied locally.

## 3. Frozen development matrix

For every selected pair:

```text
history members
  plus_first
  minus_first

targets
  nominal
  RZ_p10_m10

future actuator cases
  delay 0 / slew 1.0
  delay 2 / slew 0.9
```

Expected rollouts:

```text
4 pairs × 2 members × 2 targets × 2 actuator cases = 32
```

No case may be added, removed, or selected by R3c outcome.

## 4. Causal phase-selection algorithm

At fresh task state index zero, the controller computes a nominal phase using
only the current visible vector:

```text
current R
current Z
current Ip
```

The 48-wire current vector is forbidden. Current-run future measurements,
future actions, snapshot pair labels, and the other pair member are
forbidden.

For the target-conditioned frozen nominal R17 trajectory, evaluate integer
candidate phases 0 through 20 inclusive. For candidate `k`, compute:

```text
((R - nominal_R[k]) / 0.03 m)^2
+ ((Z - nominal_Z[k]) / 0.03 m)^2
+ ((Ip - nominal_Ip[k]) / 2000 A)^2
```

Choose the minimum-cost phase. An exact tie selects the earlier phase. The
candidate range, scales, and tie rule are frozen before any R3c real-TSC
control result.

Phase selection is performed independently by each fresh controller. A
paired member's state or selected phase is not available.

## 5. Phase-aligned controller semantics

The controller keeps two clocks:

```text
task step
  begins at 0 and is the only clock used for causality and formal timing

reference/model phase
  begins at the selected phase and advances monotonically with task steps
```

The selected reference/model phase must consistently govern:

- nominal R/Z/Ip and nominal velocity;
- nominal physical mode coefficients;
- time-indexed response/Jacobian model lookup;
- delay-aware MPC effect phase;
- nominal delay-queue priming;
- anticipatory braking transition translated into task-relative time;
- terminal-feedback transition when the reference trajectory ends.

The formal clock is never shifted. Arrival is still required by task
250/270 ms and hold is evaluated through task 350/370 ms.

Fresh-state semantics remain:

```text
integral state                         zero
previous correction                    zero
measurement history                    current visible state only
plant TSC process                       fresh
controller actor                        fresh
hidden wire input                       forbidden
future action/measurement               forbidden
online action computation               required
```

## 6. Offline gates

Before real TSC, all must pass:

1. The exact R3b source run, inventory, audit, forensics, pair IDs, snapshot
   manifests, and specifications authenticate.
2. Original-start R17 states select phase zero for all four target/actuator
   source cases.
3. Streaming the original-start R17 visible trajectory through a fresh R3c
   controller reproduces the frozen online actions at machine tolerance.
4. No current-run future action or measurement is used.
5. No full-wire value enters phase selection, controller state, or actions.
6. Task-step and reference-phase traces are monotonic and separately
   recorded.
7. Expected real-TSC raw count remains zero in the offline phase.

Failure of an offline gate stops the campaign.

## 7. Formal acceptance

R3c development PASS requires:

```text
environment success                         32/32
fresh TSC process                           32/32
fresh controller                            32/32
initial visible restart exact               32/32
initial full-wire restart exact             32/32
causal controller trace                     32/32
future action replay                             0
future measurement use                           0
hidden-wire controller input                     0
formal contract pass                        32/32
both members pass in every pair group       16/16
```

The formal thresholds and timing are unchanged. The gate may not be weakened
after observing R3c.

## 8. Required reporting semantics

Every result must separately report:

- runtime/environment error;
- deployment/import/package error;
- raw/snapshot corruption;
- plant-restart fidelity failure;
- controller causality failure;
- phase-selection or phase-transition design failure;
- real formal closed-loop control failure;
- hidden-history paired sensitivity;
- development success versus independent confirmation.

For a pair control group:

```text
both pass
  assessed development-set pair success

one passes and one fails
  history-sensitive outcome

both fail
  common-mode failure; hidden-history robustness assessment is masked
```

`observer_or_history_identification_failure_count` must not report zero as a
success signal when all relevant groups are masked by common-mode failure.

## 9. Advancement

R3c PASS freezes only a development-set visible-state phase-aligned MPC
repair. It does not validate hidden-history generalization.

The next experiment must be R3d with new preregistered prefix lengths,
history-generation parameters, snapshot identities, and no control-based
selection. Only R3d independent success may unblock new targets.

BC, DAgger, and residual RL remain prohibited.
