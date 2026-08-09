# Stage4.2R3c3T13S24D1R14R8R41 forensic report

Date: 2026-08-09 Asia/Shanghai

Branch: `codex/stage4_2r3c3t13s24-sequential-transition`

## 1. Final classification

R8R41 is final as:

```text
FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_MODEL_FAIL_NO_TSC
```

The prospectively fixed response-blind equal blend of the R8R31 global
expanded-ridge expert and a freshly rebuilt R8R34-geometry local-affine
expert passed the complete whole-pair model gate, every tube cap, all
reserved containment, and all causal-state support. It failed one frozen
whole-schedule point component: maximum `vZ` error was
`0.053570131890090245 m/s` against the unchanged `0.05 m/s` cap.

This is a finite model-architecture FAIL. It is not a runtime, deployment,
source, numerical-reproduction, raw, restart, causality, reporting,
controller, real-MPC, formal-control, plant-reachability, or Gate A result.
R8R41 executed zero Ray, `gotsc`, TSC, controller, plant step, raw, or
snapshot.

## 2. Frozen identity and checkpoints

```text
design checkpoint                                  e132925
implementation checkpoint                          8e551b1
initial package checkpoint                         f26cea3
source-authentication hotfix                       aa5ae10
final package checkpoint                           2fb0766
design SHA-256
  445e3522839a36eb3ee403ceccfbe7909f50b9b031f5d5f2951361627f4a3362
final config SHA-256
  07728cfabcaab6dbefc47b3a5cbb7b506b88312ae6c064e854003ea1a78fd869
final PACKAGE_MANIFEST.json SHA-256
  41df344437d36e2bfdee91d856f8f394f24cf4aa2605f7bd0f0eaf69b7b15f5a
final SHA256SUMS SHA-256
  61b596666f797a66beefe93bb68111c36956d7c3873847bd864ceb5493ed665f
```

Before any R8R41 result was opened, conditional R8R42 was frozen at
`6921179`, design SHA-256
`7902135995b137f8b9ffc0b110c187c7ee86c60e631ead3c56fc6672a22efbea`.
Its source gate requires a final exact R8R41 PASS. The actual R8R41 route is
FAIL, so R8R42 is blocked without implementation or execution.

## 3. Authentication-only stopped attempt

The initial `f26cea3_v1` primary invocation stopped before any model fit or
prediction because eight configured R8R39 source hashes had been transcribed
with correct visible prefixes and suffixes but incorrect middle bytes. The
server directory contains only `analysis/primary_failure.json` and
`stage_state.json`; it contains no model, raw, snapshot, controller, or plant
result.

A direct read-only server hash audit established the complete source hashes.
Commit `aa5ae10` changed only those eight expected hashes. It did not change
the bank, features, experts, weights, folds, tubes, gates, routes, or any
scientific semantics. The stopped v1 directory and its logs were preserved.
The final computation ran under the fresh `2fb0766_v2` package and run
identity. The v1 event is a source-authentication transcription/deployment
error, not a scientific model result.

## 4. Package and deployment validation

The final package declares 1,203 source files and contains 1,205 physical
files including `PACKAGE_MANIFEST.json` and `SHA256SUMS`. Local source
validation, a fresh empty direct-copy tree, server staging, and the installed
server tree passed:

```text
declared hashes                              1203/1203
physical files in empty/staging tree           1205
strict JSON including manifest                  142
declared Python compilation                     470
declared shell bash -n                          449
focused tests                                  12/12
full tests                                  1486/1486
expected isolated/server skip                     1
```

Local Python work used only `venv/Scripts/python.exe`. Server work used only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`. The package
was copied directly with `scp -r`; no archive was created or extracted. The
documented user-authorized fixed SSH endpoint/key invocation was used without
reading the identity or SSH configuration.

An initial install wrapper copied the files successfully but its final
reporting expression lost shell quoting and raised `NameError`. A safe
reporting retry verified the installed copy. This was a deployment-wrapper
reporting error and did not execute or alter any scientific computation.

## 5. Authenticated bank and fixed model

Primary and independent paths rebuilt:

```text
trajectories                                      560
history contexts                                   16
schedule identities                                35
interval records                                 3360
five-component time rows                        14560
local heads passed                           1161/1161
minimum training rows per local head              210
whole-pair support folds                           8/8
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

Every held fold independently refit the exact 238D centered ridge-`1e-4`
global expert and the exact 62D/k64 centered augmented local-affine ridge-1
expert. Primary and independent each owned its stable neighbor selection and
augmented least-squares construction. Every prediction was the fixed
`0.5 * global + 0.5 * local`. Innovation, gains, gating, expert fallback,
feature/ridge/neighbor/weight search, held-target influence, response
weighting, and clipping were absent.

## 6. Scientific result

Frozen point and tube caps were:

```text
point caps     [0.015,0.015,3000,0.05,0.05]
tube caps      [0.025,0.025,5000,0.08,0.08]
```

Whole-pair results passed every gate:

```text
maximum point error
  [0.0050475893,0.0099471947,113.723112,0.0256763410,0.0333021214]
maximum reserved tube
  [0.015,0.015,3000,0.05,0.05]
reserved containment                         72800/72800
state support                                         8/8
```

Whole-schedule results were:

```text
maximum point error
  [0.0014886481,0.0019006051,84.7787968,0.0236891153,0.0535701319]
maximum reserved tube
  [0.015,0.015,3000,0.05,0.0669626649]
reserved containment                         72800/72800
```

R, Z, Ip, and `vR` point caps passed. Only `vZ` failed, by
`0.003570131890090245 m/s`. The componentwise combined tube was
`[0.015,0.015,3000,0.05,0.0669626648626128]`, so every tube cap passed.
The all-or-nothing whole-schedule point gate nevertheless failed.

The worst schedule `vZ` fold was `R8R28_g2_UUUU`; its maximum physical
component errors were
`[0.0004631789,0.0014423676,50.6103327,0.0213220763,0.0535701319]`.

## 7. Independent reproduction

The separately rebuilt implementation agreed exactly:

```text
maximum bank absolute difference                 0.0
maximum scaled model difference                  0.0
maximum scaled prediction difference             0.0
maximum scaled tube difference                   0.0
maximum scaled metric difference                 0.0
neighbors / counts / support / route / outcome exact
```

All agreement booleans passed under the frozen scaled `1e-9` gate. The
failure is therefore not a numerical or reporting disagreement.

## 8. Exact server evidence

Run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r41_runs/
stage4_2r3c3t13s24d1r14r8r41_fixed_equal_global_ridge_local_affine_cold_ensemble_preflight_20260809_2fb0766_v2
```

The stage directory is
`stage4_2r3c3t13s24d1r14r8r41_fixed_equal_global_ridge_local_affine_cold_ensemble_preflight`.
All primary/independent/finalizer wrapper exit codes are zero. It has exactly
eight files and zero JSON.GZ, raw-named, or snapshot-named files:

```text
primary_summary.json          1955 bytes
  54838f3732b787719c388d2ad4deec17ff1d4efe97f06af8fac4e2ab6b49af08
primary_detailed.json       522060 bytes
  2134bcd8b1a052716cd4721e597fcce18e52b735cd5903be57eba71d54aebc2d
preflight_model.json      94265156 bytes
  42b54d6763e9d3d123da297fc2d04120418e0231a62b0d48e17aec5308e8af98
independent.json            182745 bytes
  543044141a470c500b4e166777d2f4bde8f6a5bf7129835355041c0d263228a3
compact_audit.json          277554 bytes
  be407353998c8b2c5c1e4236a891e6a2588b0849a5391f20cc93f8578a7d325a
final_report.json           277620 bytes
  ace2776e2241f412015c53f254ee8c4a753a76a631804ac448659a3443b07015
stage_state.json               557 bytes
  d7ec67b822caa80d7c987301ab2c3983134d2ed97c6e542828c72b75e8d81a25
stage_manifest.json            1071 bytes
  8d60a81e6e7335c602c5af481eba296bb0f34184a3599dcf50e15b941cd947e7
```

Server log hashes:

```text
primary      c8a0511a4d258b386d6f1c1f0542bf3bdcfe4e8293333cf93a4ad4823c647763
independent  1433ea960a022a9b76d79aeadc6ab62ed6f2c35218b965da5246f6d8c362604d
finalizer    c72d772b9eaa5b8895226693ef8ad625e4dc25861a275291c219edda200cf56e
```

Six compact files totaling 741,502 bytes were copied directly to
`artifacts/server_audits/r8r41_20260809_2fb0766_v2_final` and reproduce the
server hashes. The 94.27 MB model and detailed evidence remain on the
server.

## 9. Frozen continuation boundary

R8R42 is blocked by its exact source gate and must not be implemented.
R8R41 nearly closes the fixed cold-model envelope but does not qualify it;
the schedule `vZ` failure may not be waived or reinterpreted after result.

Any next computation requires a separately frozen identity. It may use this
result to choose a new architecture, but it must retain the same immutable
bank, exclusion families, caps, support, forbidden-input, independent, and
zero-new-TSC boundaries. Gate A, expert data, BC, DAgger, residual RL, and
all other learning remain blocked. Every R8-family trajectory remains
forbidden from learning data.
