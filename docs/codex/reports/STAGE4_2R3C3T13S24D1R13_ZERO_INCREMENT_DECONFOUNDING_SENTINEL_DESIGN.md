# Stage4.2R3c3T13S24D1R13 zero-increment deconfounding sentinel design

## Status and question

This design is frozen after the final D1R12 development failure and before
D1R13 implementation, package construction, output, Ray task, `gotsc`, TSC,
or plant execution.

D1R13 asks one narrow safety question: after reproducing the authenticated
D1R11 active-calibration prefix through state 10, can the same restarted
plants remain finite through their unchanged formal horizons when every
subsequent commanded coil-current increment is exactly zero?

D1R13 is a safety/deconfounding sentinel. Formal tracking is diagnostic only.
It is not transition identification, a model fit, MPC, control validation,
long hold, expert collection, BC, DAgger, or RL.

## Immutable sources

Authenticate the exact final D1R11 training boundary:

```text
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r11_runs/
  stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_20260804_571b932_v1

raw count / bytes
  600 / 35,511,922

raw inventory digest
  8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7

execution code / package checkpoints
  027f555 / 05c8521
```

The D1R11 calibration and fresh-holdout outcomes do not exist and may not be
opened or synthesized. D1R13 uses only the eight named training baseline raws
and their authenticated R3b restart snapshots as source evidence.

## Frozen eight-case matrix

The sentinel contains exactly eight fresh controllers and eight fresh TSC
processes. Each row is a D1R11 baseline identity; sequence/probe rows are not
eligible.

```text
normal, zero target, prefix-5
  plus_first   s42r3c3_e574ecc025deeddc5117
  minus_first  s42r3c3_55747cb1e2dcccbf3eb7

normal, shifted target, prefix-5
  plus_first   s42r3c3_6d928c4f7114b0f1344c
  minus_first  s42r3c3_88b51ffa3aede4eabdc1

weak slew, zero target, prefix-9
  plus_first   s42r3c3_79899b70dcebd962c190
  minus_first  s42r3c3_b441b17c5dd5fb4f5140

weak slew, shifted target, prefix-9
  plus_first   s42r3c3_7e1a653a8d2ac1c0ba96
  minus_first  s42r3c3_08f34cdaca588ec030cd
```

Coverage is fixed at four 35-step delay-0/slew-1.0 cases and four 37-step
delay-2/slew-0.9 cases, with four zero-target and four
`(+0.01 m, -0.01 m, 0 A)` target-offset cases. Both hidden-history members
are present in every pair. Pair/history/target/delay/slew labels define the
offline matrix only and are unavailable to the online controller.

## Controller contract

For task steps 0 through 9, D1R13 must execute the unchanged D1R11 controller
and cumulative exact-Card15 calibration. Its physical state/action/trace
prefix through state 10 must reproduce the matching D1R11 baseline, excluding
only non-semantic runtime timing fields.

For every task step from 10 through `horizon - 1`, the new-identity controller
must return exactly:

```text
action_norm_tsc = [0.0] * 14
```

The zero action is a zero coil-current increment under the environment action
contract. It is not a frozen nonzero action and not a fixed physical-mode
increment. No R17 solve, R17 nominal/reference advance, terminal regulator,
Card15 issue/cancel, source action, or probe action may run after task step 9.

The zero branch may read only the current task-step index needed to enforce
the boundary. It may not read pair/history/partition/prefix, target/delay/slew
labels, source results/actions/currents, coil or wire currents, hidden state,
future values, phase/manifold, or matched baselines. Controller history may
still advance for complete causal bookkeeping but cannot affect the zero
action.

## Immutable timing and execution

The formal timing contract is unchanged:

```text
slew 1.0: arrive by state 25, evaluate through state 35
slew 0.9: arrive by state 27, evaluate through state 37
R/Z tolerance 30 mm; speed threshold 0.1 m/s
Ip threshold and arrival streak unchanged
```

Every rollout must use one fresh controller and one fresh authentic TSC
process from the exact R3b snapshot. Ray capacity is fixed before launch.
There is no early success exit. A TSC abnormality or unsafe action causes a
structured per-task failure and stops that task without broad process cleanup.

## Preregistered gates

Before real execution:

- authenticate the complete D1R11 training inventory and all eight selected
  raw SHA-256/size/identity records;
- authenticate all eight restart snapshot manifests and exact source states;
- require eight unique specs and four cases per formal horizon;
- require the unchanged prefix controller/config/source fingerprints;
- prove by unit test that task steps 0--9 delegate unchanged and every later
  action is bit-exact zero;
- reject all forbidden controller inputs and any future schedule/action; and
- complete local, empty-package, and installed-server validation.

After real execution, pass requires:

```text
strict raw / exact identity                              8 / 8
fresh controller / fresh TSC                             8 / 8
restart snapshot and state-0 exact                       8 / 8
physical state/action/trace prefix through state 10      8 / 8
causal calibration complete                              8 / 8
full formal horizon                                      8 / 8
post-prefix zero actions                     all 208 expected actions
post-prefix coil-current increments exactly zero         all
finite R/Z/Ip, coil and wire-current records              all
TSC abnormal / solver / saturation / clipping errors        0
forbidden controller inputs / future values                 0
raw, snapshot, manifest, inventory corruption               0
```

The expected post-prefix count is
`4 * (35 - 10) + 4 * (37 - 10) = 208`.

Formal arrival/hold verdicts must be recomputed from raw and reported, but
they cannot fail this safety sentinel and cannot be called controller success.
Current utilization must remain within the unchanged `0.55` envelope. Any
unexpected post-prefix coil-current movement, even if TSC remains finite,
fails the action-semantics gate.

## Frozen routes

```text
ZERO_INCREMENT_DECONFOUNDING_OFFLINE_FAIL_NO_TSC
ZERO_INCREMENT_DECONFOUNDING_RUNTIME_OR_PREFIX_FAIL_STOP
ZERO_INCREMENT_DECONFOUNDING_PLANT_FINITE_FAIL_STABILIZING_SCAFFOLD_REQUIRED
ZERO_INCREMENT_DECONFOUNDING_SENTINEL_PASS_EXCITATION_SENTINEL_DESIGN_REQUIRED
```

A pass authorizes only prospective design of a separate bounded
zero-baseline excitation sentinel. It does not authorize a full
identification campaign, transition model, MPC, expert dataset, BC, DAgger,
or bounded residual RL.
