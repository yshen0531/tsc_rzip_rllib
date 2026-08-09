# Stage4.2R3c3T13S24D1R14R8R34 forensic report

Date: 2026-08-09 Asia/Shanghai  
Branch: `codex/stage4_2r3c3t13s24-sequential-transition`

## 1. Final classification

R8R34 is final as a dual-layer zero-new-TSC failure:

```text
accepted overall route
  CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP

primary scientific route
  CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC

overall failure classification
  independent_numerical_reproducibility_gate_failure
```

The fixed response-blind 64-neighbor cardinality and whole-schedule model
gates passed. The primary whole-pair model failed its Z/vZ point limits and
100% containment gate, so planning remained closed. Independently rebuilt
bank, tube, planning state, route, and scientific outcome agreed, but the
prospectively frozen dimensionless `1e-9` prediction/metric agreement gate
did not. The tolerance was not changed after the result.

This is not a runtime, deployment, source-authentication, raw-corruption,
restart, real-controller, real-MPC, plant-reachability, formal-control, or
Gate A result. R8R34 executed zero Ray, `gotsc`, TSC, controller, plant step,
raw, or snapshot.

## 2. Immutable identity and checkpoints

```text
design checkpoint                              1380fe1
initial implementation                         366dd55
initial package                                335373f
centered-intercept numerical hotfix             b3d2ab9
centered-intercept package                      8531fad
failure-finalizer implementation                24a7851
final package                                  fbf2848
config SHA-256
  f6d0d115f6d43bc01fc546ef96855a28079bec0a44855e9caa1331beb51e4ca9
design SHA-256
  21d86f169cd92ede5263e2a9c6a4fc189e070f5cbfa1bd4dbd7d493fabf8f0c2
final PACKAGE_MANIFEST.json SHA-256
  d13375f54c4b7706b8374389d1cfef7a3294cdb86760bf2b0965d47b36bc8e1e
final SHA256SUMS SHA-256
  dba230808d114d52097b76afe3a1f79b3408baade404823cbe98293f28861df7
```

The centered-intercept hotfix analytically eliminates the unpenalized local
intercept and sets mathematically inactive centered columns to their exact
zero ridge optimum. It preserves the frozen neighbor geometry, responses,
ridge, objective, tube, support, tolerance, and routes. The failure finalizer
changes no calculation; it validates and seals the already-written
`independent_failure.json`.

## 3. Package and validation evidence

The initial package passed focused `9/9` and full Windows-resource-shimmed
`1439/1439`. The centered hotfix added its singular-geometry regression and
passed `10/10` and `1440/1440`. The final failure-finalizer package declares
1,174 source files and contains 1,176 physical files including
`PACKAGE_MANIFEST.json` and `SHA256SUMS`.

The final fresh empty direct-copy tree and both server staging and installed
trees passed:

```text
declared hashes                              1174/1174
JSON parses                                    138/138
Python compilation                             458/458
declared shell bash -n                         445/445
focused tests                                    11/11
full tests                                    1441/1441
expected isolated-evidence skip                       1
```

Only the repository virtual environment was used locally and only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python` was used on
the server. Both packages were transferred as direct `scp -r` directory
trees with no local archive operation.

Non-scientific wrapper events were kept separate: `tsc-airgap` did not
resolve in the Codex process, so the documented fixed key endpoint was used;
one first `scp` attempt stopped before upload because SFTP did not expand a
literal `$HOME`; and one staging validation completed all checks before a
PowerShell-added trailing CR changed the wrapper exit to 127. Absolute paths
and CR stripping then produced clean exit-zero repetitions before install.

Representative local validation-log hashes are:

```text
centered staging validation
  7918a8e954bab12a5b26aa39d02969e82fa5fee716e1b78b3676c82395c6ff78
centered installed validation
  8e27a78b24ef57162cf72fb518020aba42c370c5a2a215445f697f0e3b0397d7
finalizer installed validation
  ca687260974d2efb8513ad16d4086c64d99e2da331c4f1e79e2424c3861cc61e
failure finalization control log
  a7b8e5bf581aa83730b5515d1f5495b959282108b97887dd022ad9c36ac012c8
```

## 4. Preserved first implementation attempt

The initial R8R34 primary completed under the preserved `_335373f_v1`
directory. Its independent normal-equation path stopped with
`numpy.linalg.LinAlgError: Singular matrix`. The direct 63-column
`[intercept,D]` system combined an unpenalized intercept with constant
approximately `1e12` query-offset columns produced by the frozen scale floor.

This was a numerical implementation failure before an accepted independent
result, not a scientific model conclusion. The stopped output and log remain
unchanged. No TSC or raw was created. The centered hotfix was separately
reviewed, tested, committed, packaged, and executed in the new valid v2
directory rather than overwriting v1.

## 5. Authenticated bank and local-cardinality result

Primary and independent v2 paths rebuilt the immutable consumed-development
bank:

```text
trajectories                                      560
history contexts                                   16
schedule identities                                35
interval records                                 3360
bank digest
  a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest
  80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest
  0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

All 1,161 whole-pair and whole-schedule local heads had at least the frozen
64 neighbors. The minimum training-row count was 210; failed heads were
`0/1161`.

## 6. Primary model result

The frozen physical caps were:

```text
point caps     [0.015,0.015,3000,0.05,0.05]
tube caps      [0.025,0.025,5000,0.08,0.08]
```

Primary whole-pair results were:

```text
maximum point error
  [0.0100858176,0.0197562473,151.184850,0.0465097729,0.0627917229]
maximum reserved tube
  [0.015,0.0246953091,3000,0.0581372162,0.0784896536]
reserved containment                         72217/72800
state-support folds                                  8/8
```

R, Ip, and vR point caps passed, while Z and vZ point caps failed. Every tube
cap passed, but 583 components lay outside their eligible reserved tubes, so
the all-or-nothing containment gate failed.

Primary whole-schedule results were:

```text
maximum point error
  [0.0018031180,0.0029403129,55.7966057,0.0143597728,0.0178805288]
maximum reserved tube
  [0.015,0.015,3000,0.05,0.05]
containment                                  72800/72800
```

All whole-schedule point, tube, and containment gates passed. The combined
tube cap also passed. The whole-pair failure nevertheless closed the complete
model gate before planning. Zero plans, repairs, oracle count, and nonzero
first actions are phase-closed sentinels, not failed controller trials.

## 7. Independent numerical failure

The independent path agreed exactly on bank identity, discrete route,
scientific outcome, and planning closure, and agreed on tubes far within the
frozen scaled tolerance:

```text
maximum bank absolute difference                         0.0
maximum scaled prediction difference          6.9176668560e-7
maximum scaled tube difference                4.8294701571e-14
maximum scaled metric difference              1.7420631368e-7
maximum scaled planning difference                       0.0
frozen maximum allowed difference                         1e-9
```

Prediction and metric agreements therefore failed even though bank, tube,
planning, route, and outcome agreements passed. The overall integrity gate
fails closed. This numerical failure neither rescues nor changes the primary
whole-pair model failure.

## 8. Exact server evidence

Valid run directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r34_runs/
stage4_2r3c3t13s24d1r14r8r34_causal_local_neighborhood_schedule_generalizing_feedback_preflight_20260809_8531fad_v2
```

Stage evidence:

```text
primary_summary.json          2068 bytes
  4daa6526eccc3b700e1ed08f558dfafe365e7840555f6934e3e5074b0c22c121
primary_detailed.json       460375 bytes
  a2cbe74967ab37a686c20ffc7de226a7115c623332901fa6e485f846e3c5e258
preflight_model.json       6966917 bytes
  e8cf8040e4e520c2e2a1a3684c0510318c59dec959db2016f5118abf74340af8
independent_failure.json    398096 bytes
  eda9e6047c48444a537032c748c4f0bbd48968ab72e76467d586db9ec826d67f
compact_audit.json          252313 bytes
  83db9a91719e2c967ef574ce962283f209e3223c33b17f7faf25e5ef0ddb7fce
final_report.json           252399 bytes
  ce2bf79b94a106ffe617052287626e102e228e5fe6ba62e4ae15c727954b73d3
stage_state.json               649 bytes
  ea1cee93df7d6ecffbe39a869ecfab2659dfe02155f00d0e5dff2dfe7b05cdd8
stage_manifest.json           1195 bytes
  1175004feff43d6f207259f2a8a0149b7762e8667479d062388770a8daa76a96
```

Server enumeration found zero `*.json.gz` raw and zero snapshot files; the
stage contains exactly these eight evidence files. The five downloaded
summary/compact/final/state/manifest files reproduce server hashes exactly.
The 6.97 MB model and detailed/independent evidence remain on the server.

## 9. Frozen continuation

Before opening the detailed R8R34 primary metrics or any failed-row identity,
R8R35 was frozen at checkpoint `7c83240`:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R35_CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_SCHEDULE_GENERALIZING_PREFLIGHT_DESIGN.md
SHA-256
ad451b7b14ea1e3dcd84c029042b58068a4879f891e0cbcedd69f546f623fbbf
```

R8R35 removes affine slopes and query-offset extrapolation. It keeps the
fixed response-blind 64-neighbor geometry, uses an unweighted local constant,
and adds exactly one unit-gain causal correction from the preceding completed
same-trajectory interval. Whole-pair and whole-schedule gates, a prospective
five-percent measurable improvement requirement, no-fold-regression gates,
and the scaled independent contract are frozen with no search.

R8R35 remains zero-new-TSC. Even a complete PASS authorizes only a separately
frozen measurement-recentered controller preflight design. Gate A, expert
data, BC, DAgger, bounded residual RL, and all other learning remain blocked.
