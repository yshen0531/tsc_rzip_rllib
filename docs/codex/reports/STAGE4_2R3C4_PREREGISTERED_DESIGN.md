# Stage4.2R3c4 preregistered design gate

## 1. Status

Stage4.2R3c4 was evaluated prospectively before controller implementation or
real TSC execution.

The required bounded-response feasibility precondition failed. Therefore:

```text
R3c4 controller implementation        not authorized
R3c4 offline launch                   not run
R3c4 real TSC launch                  not run
R3c4 raw task count                   0
formal gate                           unchanged
```

This file freezes the rejected candidate and the pre-execution stop decision.
It is not a favorable controller result and does not reserve a PASS.

## 2. Authenticated response bank

The bank was recomputed on the server from all immutable R3c3 raw and the
exact 32 R3c1 baselines:

```text
R3c3 raw                                          256/256
R3c1 baselines                                      32/32
signed response groups                             128/128
matched-hidden-history comparisons                   64/64
rank/condition contexts                              32/32
```

Exact source:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3_runs/
stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427
```

Fingerprints:

```text
R3c3 raw inventory
  88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563

audit response bank SHA-256
  51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32

controller-facing bank SHA-256
  6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0

bank manifest SHA-256
  a17322dcfc1d019de0455950c95e45b0b7d0f8f29fc3c68a22211481f261a066

bank provenance digest
  5ec49166e59df915105d4411df36a9901db56f365594b83ff08bbc6abf3751f6
```

The controller-facing file contains 32 numeric samples. Its recursive schema
check found zero keys containing pair, history, source, experiment, raw,
result, wire, pass, or fail. It contains only allowed initial R/Z/Ip, 14 coil
currents, target offsets, actuator parameters, selected visible phase, and
the four bounded response bases.

The audit bank separately retains source identities and R3c1 trajectories.
Those fields are for offline audit only and are forbidden from controller
construction.

## 3. Rejected candidate controller

The candidate identity was:

```text
restart_integrated_bounded_response_deadline_mpc_v42r3c4_candidate
```

It retained the exact R3c1 target-conditioned nominal controller. Its only
new optimization variables were four R3c3 response coefficients:

```text
alpha = [
  early_mode0,
  early_mode1,
  deadline_mode0,
  deadline_mode1
]

-1 <= alpha_i <= 1
```

One unit is exactly the authenticated `0.0075` physical-mode probe. The
candidate could not enlarge the amplitude, repeat a basis, alter its timing,
or infer a new response outside the frozen bank.

The prospective model was the most favorable audit-only upper bound:

```text
predicted trajectory
  = exact completed R3c1 baseline
  + sum(alpha_i * authenticated odd response_i)
```

This is more informative than a causal runtime predictor because it is given
the exact baseline outcome. It was used only to reject an infeasible design;
the baseline outcome was never eligible as a controller input.

## 4. Frozen feasibility gate

Before implementation, every one of the 16 R3c1 failed contexts had to admit
at least one bounded coefficient vector satisfying the unchanged formal
contract under the optimistic model. The 16 existing R3c1 passes also had to
remain feasible.

The evaluator exactly reproduced all 32 saved R3c1 formal PASS values and
minimum margins:

```text
formal PASS agreement                         32/32
maximum absolute minimum-margin error             0
```

The search used:

1. an exhaustive bounded four-dimensional grid with local refinement;
2. an independent per-arrival-endpoint convex epigraph feasibility solve;
3. all original allowed arrival endpoints through 250/270 ms;
4. the original hold horizons through 350/370 ms;
5. unchanged 30 mm, 0.1 m/s, arrival-streak, and Ip constraints.

Result:

```text
R3c1 baseline feasible                         16/32
bounded optimistic oracle feasible             16/32
failed contexts repaired                        0/16
baseline passes regressed                        0/16
best remaining failed margin              -0.0603147
worst remaining failed margin             -0.3585158
```

The dominant active constraints were R transport through the hold horizon
and post-arrival speed. The largest single authenticated basis changed R/Z
position by only `0.00036588835 m`, while even the closest failed context
needed at least about `0.00180944 m` of additional normalized position
margin.

As a diagnostic only, linear coefficient bounds 2, 4, and 6 repaired zero
failed contexts. Those calculations are unvalidated extrapolation and do not
authorize a larger controller envelope. At bound 6, the best remaining
failed margin was still `-0.0223400`.

Machine-readable evidence:

```text
docs/codex/audits/stage4_2r3c4_response_bank_20260730/
stage4_2r3c4_offline_feasibility.json
```

## 5. Classification

No new plant/control experiment was run, so this is not a real closed-loop
failure.

```text
runtime/environment error                    no
deployment/package error                     no
raw/snapshot corruption                      no
statistics/reporting error                   no
plant-restart failure                        no
real R3c4 control conclusion                 not run
pre-execution design flaw                    yes
```

The design flaw is specific: four short, zero-net local pulses identify
local damping directions but do not provide enough target transport authority
over the formal hold horizon. A causal optimizer cannot outperform an
infeasible oracle that already knows the exact baseline.

## 6. Advancement decision

R3c4 remains reserved for restart-integrated deadline MPC, but it may not be
implemented or launched from the present four-basis bank.

The next stage is Stage4.2R3c3T1, a new prospectively frozen,
long-separation zero-net transport-response identification. It keeps the
per-step amplitude at the authenticated `0.0075`, introduces new temporal
transport shapes rather than silently scaling the failed local shapes, and
must pass its own central-symmetry, matched-history, conditioning, current,
restart, and causality gates.

Only if the combined local-plus-transport bank makes all 32 development
contexts feasible may R3c4 implementation resume.

No formal timing or threshold changes. R3c3 probe trajectories remain
forbidden from expert, BC, DAgger, or RL datasets.
