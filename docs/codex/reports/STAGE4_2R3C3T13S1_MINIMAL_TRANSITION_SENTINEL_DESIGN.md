# Stage4.2R3c3T13S1 minimal transition sentinel design

## 1. Prospective status

This design is frozen before implementation and before any T13S1 action or
result exists. It is the sole sentinel allowed by the T13
`MINIMAL_SENTINEL_REQUIRED` route.

```text
controller implemented                         no
config/launcher implemented                    no
server project modified                        no
Ray/gotsc/TSC executed                         no
real rollout count                              0
```

T13S1 does not test a new MPC. It asks one narrower question:

```text
At authentic restart states, can an immediately neutralized single-step
three-mode intervention identify a causal, measurable, hidden-history-
consistent transition response at both transport and braking issue times?
```

This is the missing object exposed by the T13 V4 audit. T11 measured
persistent steps whose current offset remained active until late
cancellation. Those responses conflate many future state transitions and
cannot be promoted to a per-issue-step model.

## 2. Source and experiment identity

The prospective stage identity is:

```text
stage                 Stage4.2R3c3T13S1
campaign identity     restart_issue_time_single_step_transition_sentinel_v1
underlying controller authenticated_visible_manifold_phase_mpc_v42r3c1
purpose               identification-only development sentinel
```

The source snapshot, exact restart loader, R3c1 baseline, three-mode map,
formal evaluator, and 500 ms observation wrapper must be inherited from the
exact authenticated R3c1/T11 chain. Implementation may reuse T11 utilities,
but it must receive a new config, source, package, run, raw, audit, and log
identity. No T11 raw may be overwritten or resumed as T13S1.

Probe trajectories are forbidden from every expert dataset.

## 3. Frozen bookend contexts

Exactly four baseline contexts are used:

| Pair | History | Target | Delay/slew | Frozen baseline status and margin |
|---|---|---|---|---|
| `p5_q1_a0p900_gap2_settle4` | `minus_first` | `RZ_p10_m10` | 2 / 0.9 | FAIL, `-0.361785367` |
| `p5_q1_a0p900_gap2_settle4` | `plus_first` | `RZ_p10_m10` | 2 / 0.9 | FAIL, `-0.359605500` |
| `p9_q1_a0p750_gap2_settle4` | `minus_first` | nominal | 0 / 1.0 | PASS, `+0.096970100` |
| `p9_q1_a0p750_gap2_settle4` | `plus_first` | nominal | 0 / 1.0 | PASS, `+0.103787581` |

These are two deliberately separated development bookends:

- hard early-prefix, offset-target, delayed weak-slew restart;
- later-prefix, nominal-target, zero-delay normal-slew restart.

Both matched hidden-history members are retained. The target, prefix, and
actuator differences are intentionally not interpreted as independent
factor estimates; four contexts cannot support that claim.

## 4. Frozen single-step intervention

The observation horizon is state 50 / 500 ms. This does not change the
formal arrival or hold endpoints and is not a long-hold success test.

For mode `m in {0,1,2}` and sign `sigma in {-1,+1}`, use amplitude:

```text
a_m = 0.0075 for all three modes
```

At issue step `q`, add `sigma * a_m` to exactly mode `m`. At issue step
`q+1`, add `-sigma * a_m` to the same mode. All other intervention entries
are zero:

```text
delta_u_q     =  sigma * a_m * e_m
delta_u_(q+1) = -sigma * a_m * e_m
sum_j delta_u_j = 0 exactly
```

Because the controller action is a coil-current increment, this adjacent
inverse issue creates a one-physical-step current offset and then returns
the requested increment to baseline. It is not a persistent step and has no
late cancellation tail.

The physical effect schedule is:

| Actuator case | Transport issue/cancel | Physical effects | Braking issue/cancel | Physical effects |
|---|---:|---:|---:|---:|
| delay 0 / slew 1.0 | 2 / 3 | states 3 / 4 | 16 / 17 | states 17 / 18 |
| delay 2 / slew 0.9 | 0 / 1 | states 3 / 4 | 14 / 15 | states 17 / 18 |

The wrapper must compute the underlying R3c1 action online first and then
apply only the current issue-step intervention. The underlying controller
may not receive the future intervention schedule, pair/history/prefix label,
hidden wire current, source action, source result, or current-run future
measurement.

## 5. Exact rollout matrix

Per context:

```text
extended zero-probe baseline                         1
3 modes x 2 signs x 2 effect windows               12
rollouts per context                                13
```

Campaign total:

```text
baseline contexts                                    4
extended baselines                                   4
signed single-step probes                           48
total real rollouts                                 52
central-symmetry groups                             24
matched-history groups                             12
six-column local response matrices                  4
```

Every rollout requires a fresh controller and fresh TSC process. No rollout
may be sourced from T11 or another campaign, although old evidence may be
read by the prospective offline source-authentication gate.

## 6. Raw, restart, and causality gates

A scientific sentinel result exists only after all 52 members pass:

```text
expected/actual/unique raw                         52/52/52
success and completed                              52/52
fresh controller and fresh TSC                     52/52
exact visible and full wire restart                52/52
50 causal trace rows and 51 trajectory states      52/52
forbidden controller-input count                       0
runtime/environment error count                        0
solver failure count                                   0
```

The four baselines must reproduce their authenticated R3c1/T11 formal prefix
and the PASS/FAIL status shown above. Probe formal metrics are diagnostic and
are not an acceptance gate because the intervention intentionally perturbs
the baseline.

For every signed probe:

```text
requested schedule equals the frozen two-issue schedule
requested three-mode net                            <= 1e-12
applied probe trace matches the requested schedule
first physical effect state equals 3 or 17 exactly
first inverse/cancellation effect equals 4 or 18 exactly
no response before the first physical effect
command mode-subspace residual                     <= 1e-6 A
```

The independent pre-effect maxima retain the T13 gates:

```text
R/Z       <= 1e-9 m
vR/vZ     <= 1e-7 m/s
Ip        <= 1e-4 A
```

The maximum 14-coil current utilization must remain `<= 0.55`. Any
scheduler clipping, saturation, current-limit rescaling, or issue/cancel
mismatch is a scientific execution failure, not a usable weak response.

## 7. Frozen response definitions

For one context, mode, and effect window, let `y0`, `y+`, and `y-` denote the
baseline, positive, and negative output trajectories. Define:

```text
odd response   o = (y+ - y-) / 2
even residual  b = (y+ + y-) / 2 - y0
```

Use the task-scaled R/Z/vR/vZ/Ip vector from state 3 through the context's
unchanged formal hold endpoint:

```text
s = (0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)
```

repeated for each state. Values before a probe's physical effect remain in
the embedded vector and must be zero within the causality gates.

For `N` response states, define the source-derived scaled numerical floor:

```text
epsilon_N^2 = 2N (1e-9 / 0.03)^2
            + 2N (1e-7 / 0.1)^2
            +  N (1e-4 / 2000)^2
```

This floor is frozen before data and is derived only from the unchanged
causality thresholds.

## 8. Signal and central-symmetry gates

Every one of the 24 signed groups must satisfy:

```text
||o / s||_2 >= 10 * epsilon_N
||b / s||_2 <= 0.10 * ||o / s||_2
```

and the inherited absolute even-response gates:

```text
even velocity RMSE             <= 0.004 m/s
even position RMSE             <= 0.0005 m
even Ip RMSE                   <= 20 A
```

The first inequality prevents a numerically invisible pulse from being
called an identified response. The second is a prospective 10% local
linearity/SNR requirement aligned with the T13 relative prediction gate.

## 9. Matched hidden-history gate

For each pair/target/actuator, mode, and effect window, compare the odd
response from `minus_first` with the corresponding response from
`plus_first`. All 12 comparisons must satisfy:

```text
scaled relative response difference               <= 0.10
velocity-component RMSE                            <= 0.008 m/s
endpoint-late response-speed error                  <= 0.004 m/s
final response-speed error                          <= 0.010 m/s
position RMSE                                       <= 0.001 m
Ip RMSE                                             <= 30 A
```

This gate tests whether the allowed visible restart state supports a
label-free local response at these two finite bookends. Passing it is not
independent hidden-history robustness. Failing it stops a label-free local
model and routes back to observer/multi-hypothesis design; the controller may
not use the history label.

## 10. Local transition identifiability gate

For each of the four contexts, form six scaled odd-response columns:

```text
(transport state 3 x modes 0,1,2,
 braking state 17 x modes 0,1,2)
```

Embed each column over state 3 through the unchanged formal hold endpoint.
After every column independently passes the signal gate, normalize each by
its own scaled L2 norm for this prospective geometric diagnostic. Require:

```text
numerical rank                                        6
normalized six-column condition number             <= 15
```

This normalization is frozen before T13S1 data and is paired with an
independent signal floor. It does not revise, normalize, or repair T11's
failed unnormalized condition gate, and these six columns are not a
controller decision basis.

Transport-versus-braking column cosines and norm ratios must also be
reported without a pass threshold. They decide whether a later model shares
or separates time-local parameters; they may not be selected after seeing a
formal outcome.

## 11. Stop/continue decision

Runtime, deployment, raw, and reporting defects are classified before the
scientific gate:

```text
runtime/deployment/reporting defect with unchanged semantics
  preserve successful raw; fix and safely resume only missing tasks
  sentinel scientific result remains NOT_RUN until 52/52 authentic
```

After 52/52 authentic tasks, exactly one scientific outcome is allowed:

```text
SENTINEL_PASS_OFFLINE_MODEL_ONLY
  all restart, causality, safety, signal, symmetry, matched-history,
  rank, and condition gates pass

  authorization: build and unit-test one offline state/issue-time local
  transition interface and preregister its holdout validation

  not authorized: full 32-context campaign, real MPC, R3c4, expert data,
  BC, DAgger, or residual RL

SENTINEL_FAIL_STOP_IDENTIFICATION
  any scientifically valid signal, symmetry, matched-history, rank, or
  condition gate fails

  action: preserve raw, stop expansion, and redesign observer/model/action
  resolution; a larger identification campaign is vetoed
```

No threshold may be relaxed and no amplitude, context, effect state, output
window, scaling, or normalization may be changed after a T13S1 result.

## 12. Required implementation validation before any run authority

Implementation, if separately authorized, must complete and record:

- focused source/spec/schedule/evaluator tests;
- complete repository tests;
- Python compile/compileall and all JSON parse;
- exact source hashes and import closure;
- package manifest/checksum verification;
- resume compatibility and immutable raw preservation tests;
- empty-directory direct-copy deployment simulation;
- exact server path preflight, Bash syntax, existing-venv imports/compile,
  package verification, and complete Linux tests;
- an offline 52-spec audit proving exact issue/cancel steps, zero net, no
  forbidden input, no existing raw creation, and zero TSC execution;
- a conservative 14-coil current/slew preflight at all 48 interventions.

The server launcher must use fixed capacity, capture exact PID/run/log paths,
and refuse a pre-existing output identity. Large raw and detailed audits stay
on the server; only compact route/manifest evidence is downloaded.

This document alone does not grant run authority.
