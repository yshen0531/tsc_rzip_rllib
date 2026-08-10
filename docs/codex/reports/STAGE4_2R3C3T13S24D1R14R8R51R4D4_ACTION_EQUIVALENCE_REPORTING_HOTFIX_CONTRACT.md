# Stage4.2R3c3T13S24D1R14R8R51R4D4 action-equivalence reporting hotfix contract

Status: frozen on 2026-08-10 after the fresh runtime-hotfix campaign
completed all 250 trajectories and both original raw audits reported the
execution-failure route, and after read-only event forensics localized the
only failed predicate to binary64 reconstruction of normalized actions, but
before any corrected raw audit or any formal R/Z/Ip response artifact was
produced.

## 1. Preserved evidence and authorization boundary

This is a zero-new-TSC raw-integrity reporting repair. It must not run Ray,
`gotsc`, TSC, a controller, a plant step, or any R8, R8R1, R51, R51R1,
R51R3, R51R4, R51R4D4, or other trajectory. It must not alter, replace, or
delete any raw gzip file, spec, payload, source reference, manifest, offline
construction, original raw audit, or original execution log. All R51R4D4
trajectories remain probes forbidden from expert, BC, DAgger, residual RL,
or any other learning data.

The repair is fail-closed against the following immutable server evidence:

```text
fresh run parent
  stage4_2r3c3t13s24d1r14r8r51r4d4_runs/
  stage4_2r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse_response_sentinel_20260810_6cdff6e_v2_runtime_hotfix1/

executed config
  3d1d1f93dc82fd4bde8339b37d97938532f1954347a9208100e0e106004f2d57
executed controller / primary raw-audit module
  31ebe532c453b6f491f8878e9a4a061fc705defb7587090af87f8a306b96f5bd
executed independent module
  5f76a6b2bb03c6adee981fc6583ea871b88cbffd76e810da238a1717a24a8d77
executed launcher
  d75bbf6e9b4bd85783fecf036464d58c0c5a46859eff86973b570024d4b00093
stage manifest / pre-repair stage state
  09ed7f369e2cf4429d9622a86bc59223dd1f23643900e3e3544e55c3966487c8
  0eeee7fb3281e72056157570969498527106d3471829c8a7023e4e37d10e6362
offline construction / primary / independent
  284405dd2b4f59c94f8bd2df0cf409ce704513cab6f0f48652ab852cc8022765
  61b505caaa6306a8d22a2de133b20a947445854d3a576365d609fb3c80c8238a
  b1707984dd76646fb87bff33404f60a68ea392ebb50569255a8ae706d53feb09
original raw primary / independent
  e58a2827b65fd63d7619ee3650a93fbd85c4cb5e25ef82928098bcb1ee10d3e4
  45e4026fa87f5b59afcb87e1de3318a79ab72da446d074bb90e576ae043f66f0
executed package digest
  d1d8aa2acde5b7013b2e87a0cdee1a05bde209e3f6435d2970aba377170b46ae
raw inventory
  count 250 / bytes 8,328,505
  b64203a08abd0db6735d120b43e2f2ee2529726283703708ab5dd4ca293cb609
plant steps / new raw / real TSC
  9,050 / 250 / true
formal response opened
  false
```

The original state and raw reports are preserved as the historical evidence
of the reporting defect. Corrected raw results must use new filenames. The
stage state may advance only after both corrected raw reports pass and agree;
that state transition must keep `response_outcomes_opened=false`, the raw
inventory exact, and `plant_step_count=9050`.

## 2. Exact original failure and read-only diagnosis

The fresh campaign completed 250/250 successful full-horizon trajectories.
The original primary and independent audits agree on the real event-stream
digest
`49f15d2f7b1e25212beb91ae13da73e06ff48928e17f731e6e29f5fad5b89a79`
and on `passed_count=0`. The primary nevertheless reports 250/250 for strict
parse, runtime success, full horizon, authentic restart, source state/trace
prefix, calibration, event sequence, event gates, event action/detail/trace/
effect equality, nominal-current numerical equivalence, both issue-plus-one
effects, causal-prefix equality, finite state, current limit, and forbidden-
input rejection. Runtime failures, safety stops, and forbidden traces are all
zero. Maximum current utilization is `0.3924`, below the frozen `0.55` cap.

Only `offline_event_semantics_exact` failed. Read-only comparison of all
6,550 actual/offline event pairs found:

```text
all non-action semantic fields exact             6,550/6,550
binary64-exact normalized action vectors         3,070/6,550
non-exact normalized action vectors               3,480/6,550
maximum absolute component difference       9.47505962578532e-15
minimum nonzero component difference        4.73232564246473e-15
differences greater than 1e-14                               0
differences greater than 1e-12                               0
```

The mismatch is between two online binary64 reconstructions of the same
normalized command. The exact Card15 target fields, requested coordinate,
candidate identity, event clock, criteria, nominal physical current, trace
action, and next-state applied action are unchanged. This is a raw-audit
comparison/reporting error, not a runtime, restart, causality, Card15,
physical-action, controller-design, plant, formal-control, or reachability
result.

## 3. Only authorized correction

The original comparator remains available for historical reproduction. The
corrected comparator may change only the `action_norm_tsc` member of the
actual/offline semantic event comparison from Python-list binary equality to:

```text
shape exactly 14
all values finite
relative tolerance 0
absolute tolerance 1e-12 normalized action
```

Every other semantic member remains exact:

```text
task step, event name, candidate identity, requested coordinate
all target/stored/q0/issue/center Card15 fields
passed flag and every criterion
```

The already separate physical-action gate remains binary exact across event
detail, controller trace, and next-state applied action. The nominal-current
gate remains at its previously frozen `rtol=0`, `atol=1e-12 A`. Restart,
causality, current, action-limit, formal-timing, and scientific gates do not
change.

Primary must use a NumPy vector comparison. Independent must use scalar
Python finite/difference comparisons without calling the primary comparator.
Both corrected reports must retain the old binary-exact count as a diagnostic,
report the maximum action difference, and agree exactly on inventory, row
identity, corrected predicates, event digest, route, and outcome.

## 4. Corrected artifacts and opening order

The only new raw artifacts are:

```text
analysis/raw_integrity_action_equivalence_primary.json
analysis/raw_integrity_action_equivalence_independent.json
```

The frozen order is:

```text
1. corrected primary raw audit
2. corrected independent raw audit
3. zero-TSC dual-raw authorization/state bridge
4. formal primary
5. structurally independent formal recomputation
6. compact/final report
```

Formal R/Z/Ip outcomes remain unopened through step 3. The dual-raw bridge
must fail closed unless the pre-repair state hash, original report hashes,
raw inventory, event digest, and every corrected integrity gate match this
contract. The procedural raw-pass route is the unchanged preregistered D4
pass route ending in `R51R4D5_MODEL_CONTROLLER_PREFLIGHT_REQUIRED`; it is
not yet the scientific route until formal response is opened.

After formal opening, the original preregistered scientific gate and routes
remain unchanged:

```text
repaired failed baselines >= 1 and measured oracle >= 7/16
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D4_CENTER_BRIDGED_TWO_PULSE_AUTHORITY_PRESENT_R51R4D5_MODEL_CONTROLLER_PREFLIGHT_REQUIRED

otherwise
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D4_CENTER_BRIDGED_TWO_PULSE_AUTHORITY_INSUFFICIENT_CAUSAL_FEEDBACK_REDESIGN_REQUIRED
```

R51R4D5 remains authorized only by an exact final D4 scientific PASS under
those unchanged gates. No D4 trajectory may be rerun.

## 5. Scientific boundary

This repair can establish raw integrity and then expose the already completed
finite development-envelope response. It cannot turn an integrity correction
into a controller, MPC, formal-control, long-hold, robustness, independent-
holdout, plant-reachability, or Gate A claim. Gate A, expert data, BC, DAgger,
residual RL, and Gate B remain blocked.
