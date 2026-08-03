# Stage4.2R3c3T13S24D1R10 exact-row completion safety-sentinel design

## Frozen status and purpose

This design is frozen after the two byte-identical D1R9 passes and before
D1R10 implementation, package construction, run-directory creation, Ray
startup, or any new TSC trajectory.

D1R10 asks one narrow dynamic question: do the seven selected matrix rows that
still lack exact-vector real-TSC evidence execute all four causal issue/cancel
pairs through the immutable formal horizon on each of the 18 authenticated
D1R2 restart contexts while preserving the existing action, current, restart,
causality, calibration, and controller-blindness gates?

D1R10 is a development-set safety sentinel. It does not fit a model, implement
or run MPC, change the formal timing contract, validate the full 24-row
identification matrix, or produce expert data.

## Frozen identity

```text
stage
  Stage4.2R3c3T13S24D1R10
run name
  stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel
campaign identity
  exact_row_completion_safety_sentinel_v1
controller revision
  sequential_exact_row_completion_card15_probe_v42r3c3t13s24d1r10_v1
probe primitive revision
  sequential_exact_row_completion_card15_probe_v42r3c3t13s24d1r10_v1
package revision
  r42r3c3t13s24d1r10_exact_row_completion_safety_sentinel_v1
```

The controller is the exact S24 sequential online-action primitive plus the
already frozen D1R2/D1R8 cancellation-margin check. No action, controller,
plant, target, schedule, or timing gate is weakened.

## Immutable D1R9 source

The only D1R10 spec source is the first accepted D1R9 output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r9_audits/
stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_20260803_a4547d5_v1/
stage4_2r3c3t13s24d1r9_d1r10_candidate_specs_v1.json
```

It and its enclosing result must authenticate exactly:

```text
D1R9 implementation / package commits
  3c16081 / a4547d5
D1R9 design sha256
  06addede44305d2dfb946bcc3395c74dae448cfa11922f2f94e1ec208f3fd62c
D1R9 forensic report sha256
  6fd678cc2a8157cd17086bd8cc96d9f00eea839c5d24c09dd1f5ce29a296ba94
D1R9 config sha256
  c86c755e6af70edbb76f12647ff20ab88b026f52331e7ba6fdf7058249d66bf7
D1R9 primary implementation sha256
  d0560cef097145f795a8e3871e51c265e4feb45ff3ad57c378b989e4e9c7c3be
D1R9 independent implementation sha256
  0dcb7e510d2d3a36a74b2241b1ab6dc32128cd3569c4fe0b42212caab3768b82
D1R9 detailed output sha256
  d9be8c7959e9831fba00ea45039dde4870ea792c3e40115e0d3890e56b61647f
D1R9 candidate file sha256 / bytes
  93ee3961dc5a439a6eec76c84d87b5535e3d4c84fc4b0173ad9703a6344e906e
  1,586,858
D1R9 ordered candidate digest
  52ac8dc95272caef7670df4c94d764ffc244e2630320371d1124a566b1a7a12c
D1R9 independent output sha256
  0a76ba9ae2b63d9edf827de2b4003e3b6303bf976ac9555e2b7ca42289550114
D1R9 manifest sha256
  537c97c06c1fff528ceb19e18104fc6ccf22b1e0c52ea3df287092ee62aa3a57
D1R9 summary sha256
  bba59e757de0146773aaa9b986915c8f4b7874d5c762ce1926e66844de47bb34
D1R9 server acceptance sha256
  81b12a9391a928495b24884e6aa7deac3416bda796ea9ac063d17f5b1b415563
D1R9 official run-1 log sha256
  612b9656d9f8715f99de3881df7b9632e640922a86ca89f2516f3f2bd16cfe01
requested matrix digest
  106dfed384febb16019e4d39ce1da03762ad9dbb5e8e69120a4a9d9acdebc30b
```

The D1R9 route must be exactly
`CENTRAL_ROW_REPLACEMENT_PREFLIGHT_PASS_EXACT_ROW_SENTINEL_DESIGN_REQUIRED`.
Both official D1R9 output trees must remain byte-identical. Any mismatch stops
before Ray or TSC.

## Exact 126-spec campaign

The candidate file is already normalized to the D1R10 identity; no field is
renamed or rewritten. Its ordered spec digest is immutable.

```text
matrix row indices
  [3, 7, 11, 15, 20, 21, 22]
rows                                               7
authenticated pair/history restart contexts       18
specs per row                                      18
total specs                                       126
unique snapshots                                   18
normal 350 ms horizons                             56
weak 370 ms horizons                               70
```

Each selected row occurs once on every context. Every spec must retain:

```text
stage                         Stage4.2R3c3T13S24D1R10
campaign identity             exact_row_completion_safety_sentinel_v1
controller/probe revision     sequential_exact_row_completion_card15_probe_v42r3c3t13s24d1r10_v1
source outcomes visible       false
pair/history label visible    false
partition label visible       false
source actions visible        false
source coil currents visible  false
source wire currents visible  false
hidden wire currents visible  false
future action count           0
future measurement count      0
expert-dataset eligibility    false
```

The controller may use only the same causal current/visible-state information
available to the S24 primitive. Schedule identity, row index, source outcome,
pair/history label, and partition label are audit metadata, not controller
inputs.

## Frozen schedule and safety gates

```text
issue task steps                                  10, 13, 15, 17
cancel task steps                                 11, 14, 16, 18
issue physical effect states                      11, 14, 16, 18
cancel physical effect states                     12, 15, 17, 19
dynamic exact search radius                       16
maximum absolute coordinate error                 0.07
minimum active absolute coordinate                0.18
minimum desired/applied-current cosine            0.98
maximum relative off-basis residual               0.10
maximum incremental normalized action L-infinity  0.25
maximum online cancel incremental L-infinity      0.24
maximum total normalized action magnitude         1.00
maximum current utilization                       0.55
exact stored-center cancellation                  required
exact-zero target-jump net                        required
saturation or current clipping                    forbidden
```

The 0.24 cancellation margin is checked before applying the candidate cancel
action. A structured action-gate failure is a complete immutable safe-stop raw
result: the failed action is not applied and the plant is not advanced after
it. Resume may schedule only missing or byte-invalid raw; it may not rerun a
valid structured safe stop.

## Authentic restart, execution, and raw contract

```text
fresh TSC process/controller required             126 / 126
strict JSON.GZ raw required                       126 / 126
initial authentic restart required                126 / 126
causal prefix/trace required                      126 / 126
phase alignment and calibration required          126 / 126
full formal horizon required for PASS             126 / 126
issue events required for PASS                    504 / 504
cancel events required for PASS                   504 / 504
forbidden controller-use count                      0
Ray campaign capacity                              96
TSC timeout per task                              180 s
```

The first wave may use at most 96 actors and the remaining 30 tasks reuse the
fixed campaign capacity. Every rollout receives a fresh actor-side TSC process
and controller. A Ray completion line, `success=true`, or summary verdict alone
is insufficient; acceptance must be recomputed from all 126 raw files and the
complete log.

## Immutable formal timing

```text
slew 1.0 or 1.1: arrive no later than 250 ms; hold/evaluate through 350 ms
slew 0.9:        arrive no later than 270 ms; hold/evaluate through 370 ms
R/Z tolerance:  30 mm
speed threshold: 0.1 m/s
Ip threshold:   10,000 A
arrival streak: 3 steps
```

D1R10 does not change any deadline. Formal tracking metrics are diagnostics in
this safety sentinel; D1R10 PASS certifies safe causal schedule execution, not
closed-loop target tracking or MPC quality.

## Frozen routes

```text
offline/source authentication failure
  EXACT_ROW_COMPLETION_SENTINEL_PREFLIGHT_FAIL_NO_TSC
runtime/solver/corruption failure
  EXACT_ROW_COMPLETION_SENTINEL_RUNTIME_FAIL_STOP
structured action/current-margin failure
  EXACT_ROW_COMPLETION_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED
126/126 full safety pass
  EXACT_ROW_COMPLETION_SENTINEL_PASS_FULL_REPLACEMENT_IDENTIFICATION_DESIGN_REQUIRED
```

Any runtime, raw corruption, restart, causality, calibration, forbidden-use,
action, current, issue-count, cancel-count, or full-horizon failure prevents
PASS. The failure class must be reported separately; no failed or unrun phase
may be reinterpreted as a control failure.

## Independent acceptance

After execution, an independent raw reader must recompute from all raw
JSON.GZ and the complete log:

- exact name/size/SHA-bound raw inventory;
- strict parsing and spec identity;
- initial restart and snapshot identity;
- causal trace, phase, calibration, and authentic `gotsc` prefix;
- issue/cancel event counts and every frozen action/current gate;
- structured safe-stop prefixes, including proof that the failed action was
  not applied and no later plant step occurred;
- runtime, solver, saturation, clipping, forbidden-use, and corruption counts;
- full-horizon and formal diagnostic counts;
- consistency among state, manifest, final result, raw aggregation, and route.

Large raw remains on the server. Only compact hash-bound audit outputs may be
downloaded locally.

## Scientific authorization boundary

D1R10 PASS authorizes only prospective design of a separate full 24-row
replacement identification campaign. It does not authorize that campaign's
execution, transition-model acceptance, MPC implementation or execution,
expert-data creation, BC, DAgger, or RL.

The full identification stage may be designed only after exact D1R10 raw
forensics pass 126/126. Reliable MPC, authentic restart transport, hidden
history, unseen targets, continuous actuator variation, plant/model error,
noise, disturbance recovery, and independent long hold remain required before
any RL confirmation point.
