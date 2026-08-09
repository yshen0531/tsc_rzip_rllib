# Stage4.2R3c3T13S24D1R14R8R51R4D1 post-return refresh reporting-fix contract

Status: frozen on 2026-08-10 after the original dual R51R4D1 offline run
completed, but before recomputing corrected eligibility, per-context coverage,
or the corrected scientific route.

## 1. Immutable failed attempt

The original run is preserved at:

```text
stage4_2r3c3t13s24d1r14r8r51r4d1_runs/
  stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight_20260810_ba89426_v1/
  stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight/
```

Its immutable artifact hashes are:

```text
offline_primary.json                 957ee40d34324f2e110e2ddfd71b69f7838b0428fd812aa027f29f4b7457dfca
offline_construction_primary.json    96e524637fe36ac7adfcc75eb6c2aeb222fa1a0512f0d50eb2c2851e43f07a4e
offline_independent.json             37e9a7e7aa41863146e236a9844cb22cc6978bb2dcdbd9974802e1e7633cd650
final_report.json                    c203bd422ae33cbd4f2c7775ce25027877e68562c2f822deb1facdfcf44d7b6c
stage_state.json                     82d4fd903cffbb0dbf33a0211d3a35b4d4691305a0d75c8e984b2e8e0f36512f
stage_manifest.json                  3015de45ac4f826f330c4d6727cf2af1e2ad07277898817ed85fb4be302a281b
```

Primary and the structurally independent scalar implementation agreed on
all 250 action streams and eligibility decisions with maximum numerical
difference `3.3306690738754696e-16`. The attempt ran zero TSC, plant steps,
controllers, optimizations, model fits, raw trajectories, or response
lookups.

## 2. Classified implementation defect

The original implementation added this row-level eligibility predicate:

```text
post_return_refresh_zero_increment
```

It required the normalized command representation of every refresh after
the task-step-20 stored-center return to be componentwise binary64 zero.
This predicate failed 250/250 rows even though:

```text
stored-center current exact                         250/250
post-return center Card15/current exact             250/250
stored-center return event gate                     250/250
fixed task clock                                    250/250
q0 integration gate                                 250/250
```

The frozen R51R4D1 design requires the return and every later refresh to
reconstruct q0 exactly and pass the unchanged action/current gates. It does
not require the internal normalized command representation of a physically
unchanged exact Card15 refresh to be componentwise zero. The separate frozen
equal-pair task-step-16 zero-increment gate remains required and is not this
defect.

Therefore the published `0/250` eligibility count and geometry-fail route
from the original attempt are invalid reporting/eligibility results. They
are not a runtime, source-authentication, Card15, current-equivalence,
controller, plant, MPC, or scientific geometry conclusion.

## 3. Frozen one-predicate correction

The correction may do exactly the following:

1. remove `post_return_refresh_zero_increment` from row eligibility;
2. retain the same boolean as a diagnostic field outside eligibility;
3. reconstruct all 250 schedules under a fresh parent run identity;
4. independently reconstruct the same schedules with the scalar audit;
5. require the aggregate action-stream digest to remain exactly
   `d1607012ca5e39cca3b3113c269c569c754603c49704cef419b239d810ea7ccb`;
6. preserve the original failed attempt and all of its files unchanged.

The correction may not change any Card15 field, action, current, task step,
horizon, source hash, candidate identity, event gate, `0.25` incremental
limit, `1.0` total-action limit, `0.55` current limit, `0.98` cosine limit,
`0.10` off-basis limit, equal-pair zero-increment requirement, exact-return
requirement, coverage threshold, route string, or learning prohibition.

Primary and independent corrected results must agree on all discrete fields,
event-stream digests, eligible-pair sets, coverage gates, and numerical
values within `1e-10`. Any other difference is an integrity failure rather
than a scientific result.

## 4. Authorization boundary

This contract authorizes only a zero-new-TSC corrected R51R4D1 package and a
fresh dual offline reconstruction. It does not authorize R51R4D2, Ray,
`gotsc`, TSC, a controller, plant advance, response collection, model fitting,
formal tracking, expert data, BC, DAgger, residual RL, Gate A, or Gate B.

Only if the corrected frozen coverage gate passes may a later, separately
prospective design authorize an R51R4D2 response sentinel. If it fails, the
two-transport exact-schedule family is frozen as an action-geometry/support
design failure without any plant or global-reachability claim.
