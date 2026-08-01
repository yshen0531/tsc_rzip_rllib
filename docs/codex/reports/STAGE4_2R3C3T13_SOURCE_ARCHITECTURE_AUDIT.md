# Stage4.2R3c3T13 source architecture audit

## Status

This is the first T13 evidence-mapping checkpoint. It is a read-only audit of
the current local source and frozen result reports. At this checkpoint no
controller code, prediction model, optimizer, sentinel schedule, or
experiment had been created. The later V4 audit and final T13 architecture
documents supersede the route-open statement below.

## Authenticated local source identity

The following hashes describe the exact current files inspected for this
checkpoint. The short commit is the latest local commit touching the file; it
is provenance metadata, not a substitute for the file hash.

| Source | SHA-256 | Last commit |
|---|---|---|
| `stage4_1r3_control_aware_robustness.py` | `d2439a6a84107ff3b3024f7e544381f99b6d4c29396c9bc9c67ff0c957b50509` | `6cc3826` |
| `stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc.py` | `c632e1e73ab6e00bfa25f6811f85ea0433e8a942250f6ae74e549ae1dcf8a2f9` | `0c87297` |
| `stage4_1r17_original_deadline_one_sided_robust_braking_closure.py` | `207be3971727f7eab393d36fd1c7b1669d793eb94bc4e09eeb120d1d2485989c` | `0c87297` |
| R17 config | `efa0d74bdd4c3e374214df31df086f8d6377cf3ec7d5ae6d3e9ba4a7d06ebd16` | `db04bbc` |
| `stage4_2r2_persistent_controller_checkpoint_replay.py` | `8dffdc6f6a9b851577e3a4bc98102893d8abbb418be6381d14fc54d611bf711c` | `84962ef` |
| `stage4_2r3b_confirmatory_hidden_history_initial_state.py` | `edf6188581a01dbe6f726e6dbd941e0c9a35770e57e599d57962d832a51fbf71` | `8fb1534` |
| `stage4_2r3c1_authenticated_visible_manifold_phase_mpc.py` | `4ee7eda0e06d7c771322f33bec9f0bb31c5593937821b494d81fa6c615eaa76d` | `35e725c` |
| R3c1 config | `cbfa7388d0ad4af45d20327617e529af73e656a10866777b6481f3286304b3eb` | `be3065b` |
| `stage4_2r3c2_restart_target_state_regulation_mpc.py` | `0e5c487276d13ed72500cc9a8d904499092a236ba232c5b3046142d49454534e` | `c4b9143` |
| R3c2 config | `2d61388b4acbdbb7ae77ac5d049424c612dfc528ba8f2eeb8e5326cdf8262f0c` | `c4b9143` |
| T9 interaction source | `ea674921f19e97ff3eefefc1c6d49060e433328fbf5700b80caf501c5e4ae6c9` | `b489acc` |
| T11 persistent-step source | `dde7f246be5f9ea805944a3cdef4020e87fcda4b64af46b93c27cc0114c6b942` | `322ade2` |
| T12 audit implementation | `cbdf844d2b3eb0664d6f44358a30822cb1d4ed0e0c7682d39d2bd3118681a1cd` | `386c051` |

The result evidence remains tied to its historical package commits and run
hashes. The current file hashes above are used only to describe the source
being considered for a future architecture.

## Actual controller call graph

The restart controller is not a standalone R17 function. Its active path is:

```text
R3c2 RestartTargetStateRegulationTaskController
  or R3c1 AuthenticatedVisibleManifoldPhaseTaskController
    -> R3b FreshTaskController
      -> R2 PersistentController
        -> Stage4.1R3 solve_delay_aware_physical_correction
        -> Stage4.1R3 PhysicalCoilScheduler.solve_command
        -> Stage4.1R9 streaming delay queue
        -> Stage3.4 target interpolation / nominal trajectory
```

R17 is the finite evidence/controller-source closure around this chain. Its
four weak-slew paths add a preregistered one-sided braking schedule: 6x for
delay 1 and 7x for delay 2. R17 itself explicitly does not validate a
bidirectional model, restart robustness, unseen targets, or continuous
actuator parameters.

## What the existing solver actually optimizes

`solve_delay_aware_physical_correction` uses one fixed normalized lifted
Jacobian from the Stage3.4 bundle. At each step it:

1. chooses future rows from `current_step`;
2. fixes delayed pending coefficients;
3. solves a bounded weighted linear least-squares correction over the
   remaining three-mode sequence;
4. applies ridge, sequence smoothness, and first-action continuity terms;
5. clips only the first returned correction to a rate limit;
6. passes the desired three-mode coefficient to a separate nonlinear
   14-coil scheduler.

This is a useful finite baseline, but it is not the required T13 constrained
restart MPC:

- formal arrival/hold constraints are soft weighted features rather than
  hard or robust constraints in the solve;
- `current_step` simultaneously selects model rows and shortens the lifted
  horizon;
- the fixed Jacobian is not authenticated as a state-conditioned predictor
  around the R3b restart states;
- future sequence rate/current/slew constraints are not all represented in
  the same optimization;
- the nonlinear scheduler may rescale the requested physical effect after
  the lifted solve;
- solver failure is recorded but there is no independent safe fallback action
  contract inside the controller.

R14 improved the source controller by retaining target-conditioned nominal
transport and increasing deadline-velocity weight, but still used the same
fixed lifted Jacobian and a soft least-squares objective. Its post-model tail
also changed semantics after the 35-state boundary. R17 closed only the
finite 18-case static grid with a one-sided patch.

## Fresh-restart state construction

R3b `FreshTaskController` initializes:

```text
visible history             current R/Z/Ip only
initial velocity            unavailable; first finite difference is zero
integral                    zero
previous correction         zero
delay queue                 nominal commands primed from phase zero
target transport            Stage3.4 target-conditioned nominal trajectory
hidden wire/vessel state    unavailable to controller
```

R3c1 changes the starting reference/model phase and primes the queue from the
selected phase. It preserves formal task step zero, but the selected phase
still drives both local model lookup and the remaining lifted rows.

R3c2 sends every nonzero-phase restart directly into a zero-nominal target
regulator. It therefore discards the nominal transport sequence and remains
in local damping. The observed 0/16 prefix-5 result follows the source
semantics and is not a solver or reporting anomaly.

## Reuse, replace, and prohibit boundaries

### Reuse with exact authentication

- R1c snapshot/state-load mechanism and restart fidelity audit.
- R2 explicit controller-state fields and exact persistent-state replay
  contract.
- current-run measurement history, issued command queue, and causal trace
  conventions.
- unchanged formal evaluator and physical timing thresholds.
- target-conditioned nominal trajectories as finite initial references, not
  as universal predictors.
- the three-mode-to-14-coil map and scheduler as a baseline actuator model,
  subject to joint-constraint redesign and validation.
- the R3b paired restart development contexts.

### Replace or redesign before real control

- static nearest visible phase as the controller-state initializer;
- zero-nominal restart regulation;
- one fixed Stage3.4 lifted Jacobian as an unqualified restart predictor;
- coupling model phase to formal time-to-go;
- soft-only formal timing and speed handling;
- post-solve actuator/current projection as the only safety mechanism;
- zero first-sample velocity treated as a known state rather than explicit
  uncertainty;
- absence of a deterministic safe action on optimizer/model-validity failure.

### Prohibit

- T11 response-bank or R3c4 construction after T11's failed design gate;
- source actions/results, source/current future values, hidden wire currents,
  or pair/history/prefix labels as controller inputs;
- post-hoc column normalization, condition-threshold relaxation, or
  amplitude-only repair;
- probe trajectories in expert datasets;
- direct transition to BC, DAgger, or residual RL.

## First model-gap conclusion

Existing raw evidence is rich enough to reject the old fixed-basis route, but
the current source audit has not yet shown that it supports an arbitrary
per-step, 105-variable restart action sequence. T3--T11 measure a finite set
of whole-schedule perturbations around R3c1. They do not automatically
identify a Markov/state-space or per-issue-step lifted model across the
restart envelope.

The next T13 analysis must therefore use the existing full time-series raw to
answer one precise question before choosing a sentinel:

```text
Can the frozen Stage3.4 lifted Jacobian, after a causal state/clock
reparameterization but without outcome tuning, predict the measured
time-resolved signed R3c3/T1/T2/T6/T9/T11 perturbations within prospective
task-relevant error bounds at the failed restart contexts?
```

T3 is deliberately absent from that raw list: it was an offline feasibility
audit with zero real trajectories. The exact prospective comparison,
actual-applied-input reconstruction, thresholds, and route interpretation are
frozen in
`STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_DESIGN.md` before any
prediction errors are computed.

If yes, T13 can specify an offline controller implementation and validation
plan without new TSC. If no, the missing object is a state- and issue-time
conditioned transition response, and T13 must design a small sentinel that
tests exactly that object.

## Final T13 resolution

The prospectively frozen V4 audit subsequently authenticated 1,408 raw files
and evaluated all 1,504 comparisons. Causality passed 1,504/1,504, but the
fixed Stage3.4 lifted Jacobian passed the relative response gate 0/1,504.
The final route is therefore:

```text
MINIMAL_SENTINEL_REQUIRED
```

The exact result, architecture, and prospective sentinel are recorded in:

```text
STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_REPORT.md
STAGE4_2R3C3T13_RESTART_MPC_ARCHITECTURE_SPEC.md
STAGE4_2R3C3T13S1_MINIMAL_TRANSITION_SENTINEL_DESIGN.md
```
