# Stage4.2R3c3T13S24D1R1 geometry-restoring amplitude search design

## Status and purpose

This design is frozen after the completed S24D1 static failure and before any
S24D1R1 implementation or candidate-amplitude evaluation. S24D1R1 is a
zero-new-TSC deterministic search for the smallest fixed amplitudes that
restore the unchanged Card15 cosine and off-basis geometry for the two failed
canonical H16 block patterns.

It does not simulate sequential plant response. It cannot use a favorable
static result to skip the required real-TSC sentinel.

## Immutable sources

S24D1R1 must authenticate in place:

- the exact complete S24 boundary and independent forensics;
- the exact S24D1 detailed, summary, empty sentinel table, and manifest;
- the exact successful S23R1 detailed, summary, and manifest;
- all 360 immutable S21 raw and their exact source code/config/provenance.

Required S24D1 source result:

```text
route                 CONTRACTED_AMPLITUDE_PREFLIGHT_FAIL_REDESIGN_REQUIRED
source applicability                                              true
contexts / events                                            40 / 3840
issue gate pass                                             1920 / 3840
cancellation gate pass                                      3840 / 3840
failed canonical patterns                         ++-- and +--+ only
failure criteria                                off_basis and/or cosine
new raw / plant / TSC / controller                                 zero
```

Any mismatch stops with `D1_SOURCE_AUTHENTICATION_CHANGED_STOP`.

## Fixed search space and order

The `++++` and `+-+-` canonical block amplitudes remain exactly 0.25. Only
`++--` and `+--+` are searched. Each pattern uses the same ordered Decimal
grid, inclusive at both endpoints:

```text
0.225, 0.230, 0.235, ..., 0.495, 0.500
```

The construction is exactly `Decimal("0.225") + k * Decimal("0.005")` for
integer `k = 0..55`. Binary floating accumulation, interpolation, continuous
optimization, adaptive grid refinement, and any amplitude outside this list
are forbidden.

For each of the two patterns independently and in the order `++--`, `+--+`,
S24D1R1 evaluates amplitudes from smallest to largest. An amplitude is feasible
for a pattern only if all 960 occurrences over all 40 authenticated contexts
pass every unchanged issue criterion. The selected amplitude is the first
feasible grid value. No weighted tradeoff or post-result preference is allowed.

If either pattern has no feasible grid value, stop with
`GEOMETRY_RESTORING_AMPLITUDE_SEARCH_FAIL_NO_CANDIDATE`.

## Unchanged per-issue gates

Every evaluated construction retains:

```text
finite values                                               true
exact 10-character target/reproduction                  14 / 14
maximum coordinate error                                  <= 0.07
maximum inactive coordinate                               <= 0.07
minimum active coordinate                                 >= 0.18
desired/applied physical-current cosine                   >= 0.98
relative off-basis residual                               <= 0.10
incremental normalized action                             <= 0.25
total normalized action                                   <= 1.00
predicted current utilization                             <= 0.55
no clipping, saturation, or hidden-label access             true
```

The failed D1 result may not weaken cosine, off-basis, active-coordinate,
action, current, or any other criterion.

## Full selected-candidate replay

After selecting the two independent minima, S24D1R1 constructs one fixed
24-by-16 H16 matrix using:

```text
++++   0.25
+-+-   0.25
++--   selected minimum for ++--
+--+   selected minimum for +--+
```

It then reruns the complete all-context S23R1 replay. All 3,840 issues, all
3,840 adjacent exact cancellations, all 1,280 Decimal central-sign checks,
all 40 global matrices, all 160 slot blocks, and all novelty checks must pass
the original thresholds:

```text
global rank                                               16
global normalized condition                              <= 3
slot rank                                                  4
slot normalized condition                                <= 3
minimum late residual                                    >= 0.5
exact stored-center cancellation                           true
exact zero target-field jump net                           true
```

The selected candidate and its complete detailed replay are immutable after
the search. The search may not be rerun with a changed grid under the same
identity.

## Sentinel-spec construction

On a full replay pass, S24D1R1 selects every one of the 54 S24 active
trajectories with the authenticated 0.50 cancellation incremental-action
failure. Each receives a fresh next-stage, campaign, controller, package,
environment, experiment, run, raw, state, manifest, log, and Ray identity.
It keeps the exact source snapshot, target, clean actuator regime, horizon,
history, and sequence index, but uses the selected fixed amplitude map.

S24 action/result/future state/current/wire-current values and pair, history,
or partition labels remain unavailable to the sentinel controller. Source
failure metadata is kept outside the controller spec.

## Required real-TSC sentinel after a pass

The following stage must execute all selected trajectories with a fresh TSC
process and fresh causal controller. Every trajectory must execute all four
issue/cancel pairs and its full 35/37-state horizon. All original 0.25 action,
current, Card15, restart, calibration, causality, no-label, and zero-net gates
remain required. The added prospective development gate remains:

```text
maximum online cancellation incremental normalized action <= 0.24
```

The 0.24 margin does not replace the formal 0.25 safety cap.

## Routes and scope

```text
D1 source mismatch
  D1_SOURCE_AUTHENTICATION_CHANGED_STOP

no feasible pattern amplitude or failed full replay
  GEOMETRY_RESTORING_AMPLITUDE_SEARCH_FAIL_NO_CANDIDATE

full pass
  GEOMETRY_RESTORING_AMPLITUDE_SEARCH_PASS_REAL_SENTINEL_REQUIRED
```

S24D1R1 runs zero raw, snapshots, Ray, gotsc, TSC, plant steps, controllers,
or MPC. A pass authorizes only the separately implemented real-TSC sentinel.
It does not authorize a replacement identification campaign, transition model,
MPC, expert data, BC, DAgger, or RL. The immutable 250/270 ms arrival and
350/370 ms hold timing remains unchanged.
