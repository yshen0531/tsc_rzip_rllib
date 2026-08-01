# Stage4.2R3c3T13 time-resolved model compatibility design

## Status and authority

This design is frozen before computing any Stage3.4-Jacobian prediction
error on the restart evidence. It is a no-new-TSC, read-only server audit of
immutable existing raw trajectories. It does not authorize a controller,
optimizer rollout, Ray, `gotsc`, TSC, plant step, snapshot, R3c4, expert-data
collection, BC, DAgger, or residual RL.

The audit asks one necessary architecture question:

```text
Can the frozen Stage3.4 175 x 105 lifted Jacobian predict the measured
time-resolved differential response to the total action actually applied in
the authentic restart experiments, without using labels or future values?
```

A favorable answer is not a real-control result and is not sufficient by
itself to close T13. An unfavorable answer is a prediction-model/design gap,
not a runtime, restart, solver, reporting, or closed-loop plant failure.

## Frozen source and model identity

The exact server bundle is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage3_4_runs/stage3_4_late_arrival_continuation_mpc_350ms_20260724_030829/
stage3_4_identification/full_horizon_bundle.json
```

Authenticated identities:

| Object | SHA-256 or exact value |
|---|---|
| Stage3.4 bundle | `7b307e82c35bc12beea51be303be90d0a5dd7554f54156e3684b167f37ee8987` |
| Stage3.4 resolved config | `6d705aaad12bc6872af776a0adf041041cbda38a4d545581017ad5ecdc7b34b4` |
| Stage3.4 resolved environment | `a0ed368a4aeb93b0073ff46f90583a8d63c3ef076eeef6400460ec0cb50c546a` |
| Stage3.4 manifest | `f66b84d59f53ecc665571337726f2ad6c77a749059abc06ff96995589e9af460` |
| current Stage3.4 source | `a6097b8dea3293bdccf0e742ee86dc9df65b5318f2bd700ee4e5e81d72968f27` |
| current Stage3.4 config | `6d705aaad12bc6872af776a0adf041041cbda38a4d545581017ad5ecdc7b34b4` |
| current R17 guard config | `efa0d74bdd4c3e374214df31df086f8d6377cf3ec7d5ae6d3e9ba4a7d06ebd16` |
| Jacobian shape | `175 x 105` |
| control shape | `35 x 3` |
| output order | `R[1:35], Z[1:35], vR[1:35], vZ[1:35], Ip[1:35]` |
| nominal coil increment scale | `3.0 A` |
| 14-by-3 mode matrix float64 digest | `a6438d4d32cb00a391e0f4f1f9341b8ba162aeddf75cacb599ac433fe4af0b54` |
| maximum mode Gram error from identity | `9.992007221626409e-16` |
| bundle online-feedback validated | `false` |
| bundle robustness validated | `false` |

The current source hashes document the implementation inspected during T13.
The historical bundle and resolved-run hashes, rather than the current Git
tree alone, define the numerical predictor under audit.

## Immutable raw evidence matrix

All large raw remains on the server. The audit reads the following exact run
identities in place:

| Stage | Raw | Bytes | Raw inventory digest | Primary comparisons |
|---|---:|---:|---|---:|
| R3c3 | 256 | 8,933,607 | `88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563` | 128 signed pairs |
| T1 | 128 | 4,505,015 | `f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f` | 64 signed pairs |
| T2 | 160 | 7,404,198 | `e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f` | 64 signed pairs, 128 baseline nodes |
| T6 | 224 | 11,124,363 | `594b4333eb848c762aec557744fe2dcef9101e1cc495f8713ed8bbe2f2913f61` | 96 signed pairs, 192 baseline nodes |
| T9 | 224 | 11,204,025 | `e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2` | 32 standalone pairs, 192 baseline nodes, 32 Walsh interactions |
| T11 | 416 | 19,273,198 | `f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3` | 192 signed pairs, 384 baseline nodes |
| total | 1,408 | 62,444,406 | stage digests above | 576 signed pairs, 896 nodes, 32 interactions |

T3 is not listed as raw evidence because T3 was an offline feasibility audit
and produced zero real trajectories. It may provide provenance or a route
conclusion, but it may not be represented as measured time-series data.

Every grouping key includes:

```text
pair_id, history_member, target_id, action_delay_steps, slew_scale
```

The pair/history values are development-audit grouping fields only. They are
never exposed as controller or predictor inputs. Within a comparison, the
restart snapshot, context, and every non-sign specification must match.

## Actual applied-input reconstruction

The Stage3.4 Jacobian differentiates output with respect to physical
three-mode coefficients at each of 35 action steps. T13 will not substitute
the requested probe schedule or the source action for the action actually
applied.

For raw trajectory `r`, action step `k = 0..34`, nominal increment scale
`dI_nom = 3.0 A`, and authenticated orthonormal mode matrix `M` with shape
`14 x 3`, define:

```text
DeltaI_r[k] = currents_a_tsc[k+1] - currents_a_tsc[k]
u_r[k]      = (DeltaI_r[k] / dI_nom) @ M
epsilon_r[k]= DeltaI_r[k] - dI_nom * (u_r[k] @ M.T)
```

Thus `u_r` already contains actual delay, gain, slew, queue, nonlinear
scheduler, saturation, feedback-divergence, and current-limit effects. The
primary model test uses `u_r`, not only the exogenous probe delta.

The independent trace identity is:

```text
DeltaI_r[k]
  == controller_trace[k].action_norm_tsc
     * 3.0 A * spec.slew_scale
```

The exact source delay queue is checked separately: the command issued at
task step `k` may affect action step `k + delay`, and therefore state
`k + delay + 1`. `issued_desired_physical_mode_coefficients`,
`applied_command_mode_coefficients`, and `queue_after` are audit evidence for
that mapping, not replacements for `DeltaI_r`.

Input reconstruction is valid only if, for all 1,408 files and all relevant
steps:

```text
maximum current/trace identity error                 <= 1e-9 A
maximum out-of-three-mode coil residual              <= 1e-9 A
reported delay/effect-state mapping                    exact
non-finite values                                         zero
```

Failure here classifies the audit as invalid because of a schema,
reconstruction, or raw-consistency problem. It is not evidence against the
Jacobian and cannot trigger a scientific route decision until corrected.

## Output construction

For each successful trajectory, use states 0 through 35 only. The 500 ms
tails are not fed to the 350 ms Jacobian. With `dt = 0.01 s`:

```text
vR[0] = vZ[0] = 0
vR[s] = (R[s] - R[s-1]) / dt,  s = 1..35
vZ[s] = (Z[s] - Z[s-1]) / dt,  s = 1..35

y_r = concat(R[1:35], Z[1:35], vR[1:35], vZ[1:35], Ip[1:35])
```

This is the exact Stage3.4 `absolute_feature_from_result` convention.

## Frozen comparisons

### Signed differential comparisons

For each of the 576 exact plus/minus pairs:

```text
delta_y = (y_plus - y_minus) / 2
delta_u = (u_plus - u_minus) / 2
y_hat   = J @ vector(delta_u)
```

This is the primary local-model gate. It cancels the shared restart state
and does not require an inferred absolute nominal trajectory.

### Baseline-relative finite-node comparisons

For each of the 896 T2/T6/T9/T11 nonbaseline nodes with its exact same-run
baseline:

```text
delta_y = y_node - y_baseline
delta_u = u_node - u_baseline
y_hat   = J @ vector(delta_u)
```

This gate tests the finite measured amplitudes, including even effects and
feedback-induced action changes. It is not an extrapolation or optimized
combination.

### T9 interaction holdout

For each of the 32 exact T9 contexts, use the four actual factorial nodes:

```text
delta_y_int = (y_++ - y_+- - y_-+ + y_--) / 4
delta_u_int = (u_++ - u_+- - u_-+ + u_--) / 4
y_hat_int   = J @ vector(delta_u_int)
```

This distinguishes interaction already present in the applied input from
interaction left in the plant/output response. A linear Jacobian is not
credited with a zero prediction when the actual closed-loop input contrast
is nonzero.

## Frozen prediction metrics and gates

For every comparison, reshape actual and predicted response into the five
35-state blocks. Define errors directly in physical units. The first five
absolute gates are inherited unchanged from the R17 candidate-model guard:

```text
velocity-component RMSE over vR and vZ              <= 0.008 m/s
endpoint-late response-speed error                   <= 0.004 m/s
final response-speed error                           <= 0.010 m/s
position RMSE over R and Z                           <= 0.001 m
Ip RMSE                                              <= 30 A
```

Endpoint-late response speed is the RMS of
`sqrt(vR^2 + vZ^2)` over states 32 through 35; its error is the absolute
difference between actual and predicted values. Final response-speed error
is the absolute difference of those magnitudes at state 35.

To prevent a small response from passing on absolute tolerances alone, also
normalize by the immutable Stage3.4 output scales:

```text
s = concat(0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A), each repeated 35
relative response L2 = norm((y_hat - delta_y) / s)
                       / max(norm(delta_y / s), 1e-12)
relative response L2                              <= 0.10
```

The `0.10` ceiling retains the already frozen T9 linear-route tolerance; it
does not weaken an older gate. All absolute and relative gates must pass for
every comparison in a tier. Counts, maxima, quantiles, and the exact failing
context/family/metric are reported; an aggregate mean cannot hide a failed
context.

Causality is reported independently. If the first nonzero reconstructed
input difference is at action step `k`, then neither actual nor predicted
response may begin before state `k+1`. Pre-effect maxima must satisfy:

```text
R/Z       <= 1e-9 m
vR/vZ     <= 1e-7 m/s
Ip        <= 1e-4 A
```

The first affected state in the raw must also equal the preregistered
schedule after the exact delay shift. A causality failure is separated from
a magnitude/shape prediction failure.

## Cohort and structural reporting

Results are reported for all comparisons and separately by:

```text
stage / probe family
prefix stratum p5 versus p9
target nominal versus RZ_p10_m10
delay 0, slew 1.0 versus delay 2, slew 0.9
history member
R3c1 baseline formal PASS versus FAIL where a baseline exists
```

The audit must report that Stage3.4 predicts only through state 35. It may
not silently treat the weak-slew state-37 hold endpoint as modeled. Evidence
for a robust two-step terminal continuation, or its absence, remains a
separate T13 architecture item.

## Prospective route interpretation

After raw/schema/input reconstruction passes:

```text
signed tier PASS
  all 576 signed comparisons pass every prediction and causality gate

finite-node tier PASS
  all 896 measured nodes pass every prediction and causality gate

interaction tier PASS
  all 32 T9 Walsh contrasts pass every prediction and causality gate
```

All three tiers passing makes the Stage3.4 differential predictor eligible
for the remaining offline T13 architecture specification. It does not by
itself produce `OFFLINE_ARCHITECTURE_COMPLETE`.

Any scientifically valid tier failure vetoes the frozen Stage3.4 Jacobian as
the unqualified restart-envelope predictor. Under the already frozen T13
decision rule, T13 then proceeds toward `MINIMAL_SENTINEL_REQUIRED` for one
state- and issue-time-conditioned transition response; it does not tune the
Jacobian, choose a better reconstruction after outcomes, or launch a full
campaign.

## Required output and non-claims

Server-side postprocessing may write only a compact audit/result/manifest
under the canonical project. Large raw is neither copied nor downloaded.
The compact result must contain exact source/raw hashes, inventory counts,
all tier counts, worst-case metrics, failing strata, and the error
classification.

Regardless of outcome, this audit does not validate:

- a new controller or solver;
- absolute restart trajectory prediction;
- formal control feasibility or reachability;
- state 36/37 weak-slew hold prediction;
- arbitrary per-step action sequences outside measured support;
- hidden-history robustness beyond the finite paired development contexts;
- unseen targets, continuous actuator/plant variation, noise, disturbance
  recovery, or independent long hold.

Formal arrival remains 250/270 ms and hold remains through 350/370 ms.

