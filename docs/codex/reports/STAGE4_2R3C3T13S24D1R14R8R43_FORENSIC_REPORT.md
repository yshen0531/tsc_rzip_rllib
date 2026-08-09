# Stage4.2R3c3T13S24D1R14R8R43 forensic report

Date: 2026-08-09 Asia/Shanghai

Branch: `codex/stage4_2r3c3t13s24-sequential-transition`

## 1. Final classification

R8R43 is final as:

```text
FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED
```

The prospectively fixed response-blind `0.25` global expanded-ridge plus
`0.75` local-affine cold ensemble passed the complete whole-pair and
whole-schedule point, tube, containment, support, cardinality, finite,
forbidden-input, source, package, and dual-implementation gates.

This is a finite model-architecture PASS on a repeatedly used development
bank. The R8R41 result informed the architectural direction, although the
single exact-binary weight and all gates were frozen before R8R43
computation. R8R43 is not an independent holdout, controller, real-MPC,
formal-control, plant-reachability, or Gate A result. It authorizes only the
separately frozen zero-TSC R8R44 controller preflight. R8R43 executed zero
Ray, `gotsc`, TSC, controller, plant step, raw, or snapshot.

## 2. Frozen identity and checkpoints

```text
design checkpoint                                  849d2fa
implementation checkpoint                          b87a5c6
package checkpoint                                 64a035c
design SHA-256
  7586aa8315d7f099c631e852d4178a859850cbc25d0646feae5f5296b227cb61
config SHA-256
  2ed837f7eacec22991009757d35f001d9894d7b56915457e1ecd0545fbdbed55
PACKAGE_MANIFEST.json SHA-256
  9e2b249dc796aa65f2e96e82a1262ae097852f97f9a62b406025ecff8243e5bd
SHA256SUMS SHA-256
  2b21a1b0df550b050d64fb24108dc595f989cc901d518755ba09f56cab1d5f13
```

The config hash above is recomputed from the final packaged config. Before
any R8R43 result was opened, conditional R8R44 was frozen at `5af9163`,
design SHA-256
`8151ee6f9cf086b134f83f4b4ab8cb84d065a204cd5bef928843ae5d41befad6`.
No R8R43 numerical result informed its candidates, costs, fallbacks, safety
gates, authority gates, or routes.

## 3. Package and deployment validation

The package declares 1,209 source files and contains 1,211 physical files
including `PACKAGE_MANIFEST.json` and `SHA256SUMS`. Local source validation,
a fresh empty direct-copy tree, server staging, and the installed server tree
passed:

```text
declared hashes                              1209/1209
physical files in fresh empty/staging tree     1211
strict JSON including manifest                  143
declared Python compilation                     473
declared shell bash -n                          450
focused tests                                  12/12
full tests                                  1498/1498
expected isolated/server skip                     1
```

Local Python work used only `venv/Scripts/python.exe`. Server work used only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`. The package
was copied directly with `scp -r`; no archive was created or extracted. The
documented fixed endpoint/key invocation was used without reading the
identity or SSH configuration.

The first staging validation completed all checks successfully but a CR
appended by the Windows-to-SSH script pipe produced a final
`bash: $'\\r': command not found` and wrapper exit 127. A retry stripped CR
at the remote shell boundary and reproduced all checks with exit zero. The
intervening retry first stopped before validation because controlled
`py_compile` caches made the one-time fresh-tree physical count larger than
1,211; the final retry counted package files while excluding those known
caches. No package source changed. These are validation-wrapper/newline and
cache-counting errors, not compilation, test, model, or scientific failures.

## 4. Authenticated bank and fixed model

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

Every held fold refit the exact 238D centered ridge-`1e-4` global expert
and the exact 62D/k64 centered augmented local-affine ridge-1 expert from
eligible training trajectories. Primary and independent each owned its
stable neighbors and augmented least-squares construction. Every prediction
was the fixed `0.25 * global + 0.75 * local`. Weight/ridge/feature/neighbor
search, innovation, gain, gating, expert fallback, held-target influence,
response weighting, clipping, and outlier deletion were absent.

## 5. Scientific result

Frozen point and tube caps were:

```text
point caps     [0.015,0.015,3000,0.05,0.05]
tube caps      [0.025,0.025,5000,0.08,0.08]
```

Whole-pair results passed:

```text
maximum point error
  [0.0075667034,0.0148517210,132.147183,0.0354888583,0.0473959764]
maximum reserved tube
  [0.015,0.0185646512,3000,0.05,0.0592449705]
reserved containment                         72800/72800
state support                                         8/8
```

The smallest point margins were `0.000148279024254827 m` for Z and
`0.002604023621465368 m/s` for `vZ`, both in held pair
`p9_q1_a0p900_gap3_settle4`. These are narrow finite-development margins and
must not be overstated as robust control qualification.

Whole-schedule results passed:

```text
maximum point error
  [0.0012253368,0.0020013832,50.3765587,0.0151852998,0.0303342706]
maximum reserved tube
  [0.015,0.015,3000,0.05,0.05]
reserved containment                         72800/72800
```

The schedule `vZ` maximum occurred at `R8R28_g2_UUUU`. The componentwise
combined tube was
`[0.015,0.018564651219681465,3000,0.05,0.05924497047316829]`; all tube caps
passed without clipping.

## 6. Independent reproduction

The separately rebuilt implementation agreed exactly:

```text
maximum bank absolute difference                 0.0
maximum scaled model difference                  0.0
maximum scaled prediction difference             0.0
maximum scaled tube difference                   0.0
maximum scaled metric difference                 0.0
neighbors / counts / support / route / outcome exact
```

All agreement booleans passed under the frozen scaled `1e-9` gate.

## 7. Exact server evidence

Run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r43_runs/
stage4_2r3c3t13s24d1r14r8r43_fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_preflight_20260809_64a035c_v1
```

The stage directory is
`stage4_2r3c3t13s24d1r14r8r43_fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_preflight`.
Primary/independent/finalizer wrapper exit codes are `0/0/0`. It contains
exactly eight files and zero JSON.GZ, raw-named, or snapshot-named files:

```text
primary_summary.json          1994 bytes
  a8eff07664ab453a2cab4674de0449991e20bc732187ed488e8d952fb94b14d7
primary_detailed.json       522927 bytes
  458eac9c0120f4c04c96294b752a6c7a2a95edcaff89735dca441cf87c6d5012
preflight_model.json      94256379 bytes
  5a6ec1cd25303fd435d489415b05852fcb6f053db3bd8f651f9613b5f3b0d89b
independent.json            183590 bytes
  c19c672f99383ae9e55700bf109ee42c941f6f0aad163e2ad7f07ecdb133399d
compact_audit.json          277663 bytes
  75df2ea4defc3fb97a25e41e0dc0583ab769e832b94961f0455517cf94e66a80
final_report.json           277729 bytes
  97250e2ff2826be50b56c9c3b3dadf811ba01d71ecebf12600d1789011e42bb0
stage_state.json               584 bytes
  87813f54cfdef4176a0b602343b1d54edcd1d889b2c91c65ce932b7c9ae26ad1
stage_manifest.json            1095 bytes
  49e1b358258efcee47731cc3387b145ca1aeef6f2fc2c5d2ceb5901db2295689
```

Server execution-log hashes:

```text
primary      8d4d13d2371efdc8f552285a23b6a94ea86ae0a0bb4a2a6a85d6289db7d7cbfe
independent  50ee001d91958bfe9d38bf784fe4c80708eef92a9bcbcbb9312a30f9d5740ff0
finalizer    49742c0444ad0f29638d297f0ca3c878534da217da28ef79700485a892da4796
```

Six compact files totaling 742,655 bytes were copied directly to
`artifacts/server_audits/r8r43_20260809_64a035c_v1_final` and reproduce the
server hashes. The 94.26 MB model and detailed evidence remain on the
server.

## 8. Frozen continuation

R8R43 PASS satisfies the exact conditional source gate of the already frozen
R8R44 design:

```text
checkpoint  5af9163
SHA-256     8151ee6f9cf086b134f83f4b4ab8cb84d065a204cd5bef928843ae5d41befad6
```

R8R44 is a zero-TSC measurement-recentered controller preflight with frozen
actuator, safety, support, fault-injection, and finite authority gates. It
must authenticate this exact R8R43 evidence before planning. Even an R8R44
PASS may authorize only a separately frozen fresh real-TSC safety-sentinel
design, not that run itself.

Gate A, expert data, BC, DAgger, residual RL, and all other learning remain
blocked. Every R8-family trajectory remains forbidden from learning data.
