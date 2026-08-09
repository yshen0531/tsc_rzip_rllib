# Stage4.2R3c3T13S24D1R14R8R39 forensic report

Date: 2026-08-09 Asia/Shanghai

Branch: `codex/stage4_2r3c3t13s24-sequential-transition`

## 1. Final classification

R8R39 is final as:

```text
FIXED_EQUAL_GLOBAL_LOCAL_COLD_ENSEMBLE_MODEL_FAIL_NO_TSC
```

The fixed response-blind equal blend of the R8R31 global expanded ridge
expert and the R8R37 local-constant cold expert failed both whole-pair and
whole-schedule model gates. Source authentication, bank identity,
cardinality, finite prediction, forbidden-input, support, package, runtime,
reporting, and primary/independent integrity all passed.

This is a finite model-architecture FAIL. It is not a runtime, deployment,
source, raw, restart, causality, reporting, controller, real-MPC, formal-
control, plant-reachability, or Gate A result. R8R39 executed zero Ray,
`gotsc`, TSC, controller, plant step, raw, or snapshot.

## 2. Frozen identity and checkpoints

```text
design checkpoint                                  3fa8397
implementation checkpoint                          56712ae
package checkpoint                                 40e2c22
design SHA-256
  f6005ee27d87c0a72043fc8bdc75d16bd074baa9d405a1d72e545e72f0003bbb
config SHA-256
  0205f221124834573edaa4b5ce7af718ca2d39909e8d9c28536019b4fbbd5ba2
PACKAGE_MANIFEST.json SHA-256
  fbbda2ff22c423c3c176ec4aad3e8c3846937dc32c81c3a9357be73ec052b1a2
SHA256SUMS SHA-256
  06b4a5cc3b9234b2318c60aa32ec1550cca5b92a85f1efce37ee880747d7377e
```

Before any R8R39 computation, conditional R8R40 was frozen at `61c4185`,
design SHA-256
`48802fa45048caab7219a593b5bdbbb776d71bcf7a5895c0dfb6a42287c3ef90`.
Its source gate requires a final R8R39 PASS. The actual R8R39 route is FAIL,
so R8R40 is blocked without implementation or execution.

## 3. Package and deployment validation

The package declares 1,197 source files and contains 1,199 physical files
including `PACKAGE_MANIFEST.json` and `SHA256SUMS`. Local source validation,
a fresh empty direct-copy tree, server staging, and the installed server tree
passed:

```text
declared hashes                              1197/1197
physical files in empty/staging tree           1199
strict JSON including manifest                  141
declared Python compilation                     467
declared shell bash -n                          448
focused tests                                  11/11
full tests                                  1474/1474
expected isolated/server skip                     1
```

Local Python work used only `venv/Scripts/python.exe`. Server work used only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`. The package
was copied directly with `scp -r`; no archive was created or extracted. The
`tsc-airgap` alias remained unresolved, so the documented user-authorized
fixed endpoint/key invocation was used without reading the identity or SSH
configuration.

One repository-wide local JSON scan encountered two preserved historical
evidence exceptions: an untracked UTF-16 PowerShell capture with a `.json`
suffix and a tracked zero-byte historical audit excluded from the package
inventory. Neither was modified. All 141 declared package JSON files parsed
strictly on the empty copy, staging, and installed tree.

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

Every held fold independently refit the exact 238D centered ridge-`1e-4`
global expert and the exact 62D/k64 local-constant cold expert. Every
prediction was the fixed `(global + local) / 2`. Innovation, gains, slopes,
gating, weight search, feature search, ridge search, neighbor search,
response weighting, and clipping were absent.

## 5. Scientific result

Frozen point and tube caps were:

```text
point caps     [0.015,0.015,3000,0.05,0.05]
tube caps      [0.025,0.025,5000,0.08,0.08]
```

Whole-pair results:

```text
maximum point error
  [0.0070887590,0.0171723491,80.0548413,0.0277353930,0.0515295995]
maximum reserved tube
  [0.015,0.0214654363,3000,0.05,0.0644119994]
reserved containment                         72758/72800
state support                                         8/8
```

R, Ip, and vR point caps passed. Z and vZ point caps failed, and 42
components lay outside their eligible leave-one-pair tubes. Tube caps and
support passed, but the all-or-nothing whole-pair gate failed.

Whole-schedule results:

```text
maximum point error
  [0.0068229050,0.0119713949,121.256060,0.0527403880,0.0985732689]
maximum reserved tube
  [0.015,0.015,3000,0.0659254850,0.123216586]
containment                                  72800/72800
```

R, Z, and Ip passed. vR and vZ point caps and the vZ tube cap failed. The
componentwise combined tube was
`[0.015,0.0214654363,3000,0.0659254850,0.123216586]`, so the combined gate
failed as well.

The equal blend did show limited complementarity. Relative to R8R31's global
schedule result, its vR/vZ point maxima decreased from
`0.054777/0.107249` to `0.052740/0.098573`, and tube maxima decreased from
`0.068471/0.134062` to `0.065925/0.123217`. That gain was insufficient and
the blend simultaneously regressed R8R31's passing whole-pair result: Z rose
from `0.002853` to `0.017172`, vZ from `0.030424` to `0.051530`, and
containment fell from `72800/72800` to `72758/72800`.

## 6. Independent reproduction

The independently rebuilt path agreed exactly:

```text
maximum bank absolute difference                 0.0
maximum scaled model difference                  0.0
maximum scaled prediction difference             0.0
maximum scaled tube difference                   0.0
maximum scaled metric difference                 0.0
neighbors / counts / support / route / outcome exact
```

All agreement booleans passed under the frozen scaled `1e-9` gate. Thus the
failure is not numerical or reporting disagreement.

## 7. Exact server evidence

Run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r39_runs/
stage4_2r3c3t13s24d1r14r8r39_fixed_equal_global_ridge_local_constant_cold_ensemble_preflight_20260809_40e2c22_v1
```

All primary/independent/finalizer wrapper exit codes are zero. The stage has
exactly eight files and zero JSON.GZ, raw-named, or snapshot-named files:

```text
primary_summary.json          1996 bytes
  3ff8d49c7562a6e38452b3fcc981aca021472dbc9a7913707824949e4a9d70f5
primary_detailed.json       511929 bytes
  8e1f2003f45a77838a7add75a32e07c16f4041cf045a385433b4ba50b1a329c8
preflight_model.json      94180646 bytes
  8f7f1455e14315a5c3130b29c85c8cc989fe5894a6317170bd98d8b886eea180
independent.json            181867 bytes
  0cf2b379a9a95f495c7a15d76c0e72de04466cdcf4538c26adb1c0a1b84bbc1e
compact_audit.json          277560 bytes
  06ea5e7fa3e08267d038f07cf9e8e0dd09c34ff2998bebf5792ea61e5043b594
final_report.json           277626 bytes
  c79b4ba619bdc17ba4069d088c3700c179848ad05b9cf128470805019d19dea1
stage_state.json               543 bytes
  5bdfb5ef71b305575c4f2290f344e6359aaa9c98d7bdd7b158a03646d544b585
stage_manifest.json            1066 bytes
  90bef621dd4634de1f8cf538511231bf9b1859562cf8258d918bac67e7c52c09
```

Server log hashes:

```text
primary      e330492c081d9581d7953b311f2c932dfc7b555a9d00368250de159073d3c7e5
independent  1179f61a3b0057281873234a6c76fcee2d8cb8cffcb48767d3222bd0372fd330
finalizer    fea3829bf4ba9a80890336942542dd35d1613e9025f5d97ac7e1b86375878648
```

Six compact files totaling 740,658 bytes were copied directly to
`artifacts/server_audits/r8r39_20260809_40e2c22_v1_final` and reproduce the
server hashes. The 94.18 MB model and detailed evidence remain on the
server.

## 8. Frozen continuation

R8R40 is blocked by its exact source gate and must not be implemented.

Before any R8R41 computation, the next zero-TSC architecture was frozen at
checkpoint `e132925`:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R41_FIXED_EQUAL_GLOBAL_RIDGE_LOCAL_AFFINE_COLD_ENSEMBLE_PREFLIGHT_DESIGN.md
SHA-256
445e3522839a36eb3ee403ceccfbe7909f50b9b031f5d5f2951361627f4a3362
```

R8R41 keeps the exact R31 global expert and fixed equal weights, but replaces
the rejected local-constant expert with the already specified R8R34 k64
centered local-affine ridge expert. R8R34's historical numerical independent
failure remains immutable; R8R41 must reimplement and independently pass the
new scaled gate under its own identity. R8R41 remains zero-new-TSC. Gate A
and all learning remain blocked.
