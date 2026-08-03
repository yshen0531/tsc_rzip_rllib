# Stage4.2R3c3T13S24D1R1 final forensic report

## Result

Stage4.2R3c3T13S24D1R1 completed its prospectively frozen, zero-TSC Decimal
grid search. Independent server-side parsing and assertions reproduced the
saved result:

```text
route       GEOMETRY_RESTORING_AMPLITUDE_SEARCH_PASS_REAL_SENTINEL_REQUIRED
source S21 raw authenticated                                      360 / 360
selected ++-- amplitude                                             0.290
selected +--+ amplitude                                             0.360
complete issue / cancellation gates                         3840 / 3840 each
finite constructions                                             7680 / 7680
central-sign checks                                              1280 / 1280
global rank-16 contexts / slot rank-4 blocks                       40 / 160
late-novelty contexts                                                40 / 40
selected sentinel specifications                                    54 / 54
new raw / snapshots / Ray / gotsc / TSC / plant / controller       all zero
```

The first passing amplitudes were selected exactly in the frozen order. For
`++--`, 0.285 failed all 960 occurrences on off-basis residual with maximum
`0.1006621536`; 0.290 passed all 960 with maximum `0.0955601468`. For `+--+`,
0.355 failed all 960 on off-basis residual with maximum `0.1094270921`; 0.360
passed all 960 with maximum `0.0998036448`. The selected requested matrix has
rank 16, normalized condition `2.0364675298`, maximum slot condition `1.44`,
and minimum late-column residual `0.9428090416`.

This is a finite static action-construction PASS only. It contains no plant
response, restart-control, transition-model, MPC, or robustness evidence.

## Exact execution identity and evidence

- Local branch: `codex/stage4_2r3c3t13s24-sequential-transition`
- Deployed/final package checkpoint: `8486837`
- Package revision:
  `r42r3c3t13s24d1r1_geometry_restoring_amplitude_search_v1`
- Remote output:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r1_audits/stage4_2r3c3t13s24d1r1_geometry_restoring_search_20260803_145327`
- Complete log:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/stage4_2r3c3t13s24d1r1_offline_20260803_145327.log`
- Source S24 active raw inventory:
  `fae5f62671296c837e00158fe204a1630fc70aace87be650ad13d75928f20c70`
- Source S21 raw inventory:
  `8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4`
- Provenance digest:
  `adc8e90daf26eeb42af3fe931c33edb3cac823a47cacfe0a1ac3b0dd3c113ea2`

Exact output inventory:

```text
stage4_2r3c3t13s24d1r1_geometry_restoring_search_v1.json
  bytes 11881840
  sha256 81168e646f2b40e443fa85f535193474651eb899ac8a74e1c9cd282b4f66ff98
stage4_2r3c3t13s24d1r1_summary_v1.json
  bytes 1752
  sha256 0ec97157184ba85c70507adcc9978f9c2f87afbaa462af58152bccc008e145a0
stage4_2r3c3t13s24d1r1_selected_sentinel_specs_v1.json
  bytes 791786
  sha256 61574900383ae91083173065561ea8f2a80a96a4c6935f3a965ef7ce43215c46
stage4_2r3c3t13s24d1r1_manifest_v1.json
  bytes 1035
  sha256 d6f42befe92b170226ea19f73bebbe8623191debde756b61500d6daa22ea7b9f
complete log
  sha256 89eb453af423ed9a7b4cb48122e0228b99ec1a8b3335865f7d6cf4f1bb59eb2e
```

All four JSON files strictly parsed. Manifest-listed sizes and hashes were
recomputed from bytes. The 54 rows have 54 unique experiment IDs and 54 unique
environment IDs, balanced histories `27/27`, the exact allowed S24 failure
class, no controller access to source result/action/current/wire-current or
pair/history/partition labels, and the frozen 0.24 prospective cancellation
margin.

## Error and conclusion separation

- Runtime/environment error: none. The stage intentionally executed no Ray,
  gotsc, TSC, controller, or plant step.
- Deployment/package error: none in the final installed execution.
- Raw/snapshot corruption: none found in the authenticated sources; D1R1
  created no raw or snapshot.
- Statistics error: none in the search or full-replay metrics.
- Reporting/metadata defect: the reused D1 `_sentinel_rows` helper hard-coded
  the older `s24d2` token into experiment, environment, kind, run-family,
  raw-family, state, manifest, log-family, Ray-prefix, and package-label
  strings. Each row's authoritative `stage`, campaign, and controller fields
  correctly say D1R2, and all 54 identifiers are fresh and unique. The defect
  does not change the selected contexts, snapshots, amplitudes, action maps,
  formal timing, gates, or controller-visible data, but the mixed labels must
  not be deployed unchanged.
- Design result: the frozen bounded geometry-restoring search passed.
- Real control/plant/restart result: not tested.

The metadata defect was found before any sentinel TSC execution. The D1R1
result and source artifacts remain immutable. The next design must
deterministically normalize only the stage-derived identity strings under a
new D1R2 package identity and prove every scientific field unchanged before
opening TSC.

## Commands and validation actually run

- Local repository boundary, branch, status, and HEAD checks: passed.
- Remote canonical-project and virtualenv preflight: passed as user
  `yangshen0711` on host `master`.
- Server virtualenv strict JSON parsing and byte/hash recomputation: passed.
- Independent assertions over selected minima, complete gate counts, source
  provenance, 54 unique specs, forbidden controller inputs, and manifest:
  passed.
- Complete log inspection: passed; it records the zero-plant execution and
  the same final route/hashes.

No real sentinel, replacement identification campaign, transition model,
MPC, expert-data collection, BC, DAgger, or RL was run in this stage.

## Frozen next action

Freeze and implement Stage4.2R3c3T13S24D1R2 as a 54-rollout real-TSC safety
sentinel. It must use the exact selected contexts and action schedules, fresh
TSC/controller processes, the complete 35/37-state horizon, every original
Card15/action/current/restart/calibration/causality/no-label/zero-net gate,
and the additional online cancellation margin `<= 0.24`. A pass may authorize
only a separately frozen full replacement transition-identification campaign.
It does not authorize MPC or RL.
