# Stage4.2R3c3T13S24D1R14R8R31 forensic report

## Conclusion

R8R31 is final as:

```text
ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_PREFLIGHT_FAIL_NO_TSC
```

The aligned explicit-q4 model passed the complete whole-physical-pair point,
support, and reserved-tube gate, but failed the prospectively frozen
leave-one-complete-schedule-out point/tube gate.  Planning therefore remained
closed.  This is a finite schedule-generalization/model-and-uncertainty design
failure.  It is not a runtime, source, raw, restart, causality, controller,
real-MPC, formal-control, plant-reachability, or Gate A result.

## Identity and checkpoints

```text
branch                         codex/stage4_2r3c3t13s24-sequential-transition
design checkpoint              728c235
design SHA-256                  eee31b04fe57fcf2d4da4a397657ff8d26b76c83db9f42bb13b3275b2ea4ed8e
initial implementation          53858ea
primary package                 96c232e
accepted independent package    3bc46b8
finalizer implementation        cf18359
finalizer package               0768826
PACKAGE_MANIFEST.json SHA-256   fb8c12216161e2e497fe3fa8a64d47ea505e7a29c2c44ae51bfc1c67585794d8
SHA256SUMS SHA-256              ac0c96793aac9121abb0a88602177fc10bb7f0a0dd344fccd4365f6879887428
```

The primary scientific computation was created by package `96c232e`.  The
later packages changed only independent auditing, an empty-tail audit runtime
fix, and final evidence sealing.  They did not change the bank, feature,
model, threshold, prediction, route, controller semantics, or physical action.

## Exact server evidence

Run directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r31_runs/
stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel_20260809_96c232e_v1
```

Stage directory:

```text
<run>/stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
```

Accepted logs:

```text
logs/r8r31_offline_primary_96c232e_v1.log
logs/r8r31_offline_independent_3bc46b8_v3.log
logs/r8r31_finalize_retry2_0768826_v4.log
logs/r8r31_staging_validation_0768826_v4.log
logs/r8r31_installed_validation_retry_0768826_v4.log
```

The compact final evidence was copied without an archive to:

```text
artifacts/server_audits/r8r31_20260809_96c232e_v1_final_0768826/
```

Final server file hashes:

```text
analysis/compact_audit.json  ef0d8d168e30716d5d6f18ec46502baea5b887988526b15dc75cabda7f3d3466
analysis/final_report.json   9ebbd35d2839b8d3cf905f4297c521bbdfb122e74bf0359cf88d1d565fb2735a
stage_state.json             f9bcdb27769845dc517f6a8461b9298d4d588a905f68476c48151cbf62ef2fd7
stage_manifest.json          ff4dff239fd573cf1bc52096b44952ac4db8a1a5af0986f11b3022d635fe59da
```

Load-bearing immutable source/output hashes:

```text
bank digest                  a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest               80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest                0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
primary summary              efe9a2873f126c0c8746f4dd0340df460850700b037687a15fe478431fef0dfd
primary detailed             b9a4c3402cb309f7f3c9a3cf4304f10f6a08f67e59221519a4787d681362a0c2
model artifact               88d2b3bc15e563a5ea2b70720dcd7e4f6acf95c4690613ac297c7dfdfcf95d04
independent audit            3253b93fedbbfa2bf86abc24c3e7ad555202c1835420f90e704b37210d40ffc8
```

The 17.4 MB model and all large source evidence remain on the server.

## Expected and actual scope

```text
aligned source trajectories           560 / 560
schedule identities                    35 / 35
six-interval records                3,360 / 3,360
whole-pair folds                         8 / 8
whole-schedule folds                    35 / 35
new Ray tasks                              0
new gotsc/TSC trajectories                 0
controller executions                     0
plant advances                            0
new raw files                             0
new snapshots                             0
```

The bank is exactly R8R23 `432` plus the six non-U/V R8R14 schedules `96`
plus R8R28 g2 `32`.  All g3 rows were excluded by their prospectively frozen
grid identity, not by outcome.

## Recomputed model result

The whole-pair gate passed:

```text
maximum absolute physical error
  R / Z / Ip / vR / vZ
  0.0009875911 / 0.0028532654 / 85.2103003 / 0.0176964736 / 0.0304243255

maximum reserved physical tube
  0.015 / 0.015 / 3000 / 0.05 / 0.05

reserved containment
  72,800 / 72,800 = 1.0
```

The whole-schedule gate failed:

```text
maximum absolute physical error
  0.0031825394 / 0.0038637885 / 157.5748424 / 0.0547769867 / 0.1072493982

maximum reserved physical tube
  0.015 / 0.015 / 3000 / 0.0684712333 / 0.1340617477

containment
  72,800 / 72,800 = 1.0
```

The frozen point caps are
`[0.015, 0.015, 3000, 0.05, 0.05]`; vR and vZ failed.  The frozen tube caps
are `[0.025, 0.025, 5000, 0.08, 0.08]`; the vZ tube failed.  No cap was
relaxed and no residual was discarded or clipped.  The combined pair/schedule
tube therefore failed with maximum half-width
`[0.015, 0.015, 3000, 0.0684712333, 0.1340617477]`.

Planning did not run.  Its zero plan, repair, oracle, and nonzero-action
fields are fail-closed sentinel values, not controller outcomes.  All six
fault injections selected exact-target-hold fallback, but that reporting gate
cannot override the model failure.

## Independent agreement

The structurally independent audit rebuilt the 560-trajectory bank, all
features/targets, outer models, schedule jackknife, planning auxiliaries, and
the 17.4 MB model artifact.  It reported `passed=true`, the same FAIL route,
and exact agreement:

```text
maximum bank difference             0.0
maximum fit difference              0.0
maximum outer difference            0.0
maximum schedule difference         0.0
maximum auxiliary difference        0.0
maximum model-artifact difference   0.0
all eight agreement booleans        true
```

## Validation and error classification

Final local project-venv validation passed focused `11/11` and the
Windows-resource-shimmed full suite `1411/1411`.  A fresh empty direct-copy
tree contained exactly 1,155 files and passed 1,153 declared hashes, 135 JSON
files including the manifest, 449 Python compilations, focused `11/11`, and
full `1411/1411` with one expected isolated-evidence skip.  Server staging and
installed validation passed the same checks plus `bash -n` for 442 shell
files, again with full `1411/1411` and one expected skip.  Only the project
and server existing virtual environments were used.

The first completed independent implementation encountered an audit-only
zero-size `np.max` on a legitimate empty normal-horizon tail group.  It wrote
no accepted independent file.  Checkpoint `346b808` guarded the empty group
and added a synthetic regression; the accepted audit then reproduced every
primary value exactly.  This was an independent-audit runtime error, not a
model or experiment result.

The final deployment also exposed command-wrapper errors after successful
hash validation: a CRLF here-document terminator, an omitted project cwd in
one test invocation, CRLF on a stdin Bash launcher, and a non-executable root
script mode after Windows transfer.  The accepted paths used direct venv
Python, explicit project cwd/sys.path, and `bash <launcher>`.  All accepted
validation and finalization commands exited zero.  None of these invocation
errors changed primary/independent files, model hashes, gates, or the route.

## Frozen claims and next boundary

R8R31 is immutable and may not be resumed or tuned.  It validates only the
whole-pair layer of this finite consumed development bank and rejects the
fixed 238D/ridge-`1e-4` model under whole-schedule exclusion.  It does not
show that a controller was implemented or executed and does not establish
real MPC, formal tracking, restart robustness, continuous parameters, noise,
disturbance recovery, long hold, or Gate A.

Before any next fit, tube, plan, controller action, or TSC, freeze a new
identity which targets schedule generalization without relaxing the observed
point/tube caps.  Every R8-family source and sentinel trajectory remains
forbidden from expert, BC, DAgger, residual-RL, or any other learning data.

## Commands actually run

The accepted workflow used the project venv for `py_compile`, focused tests,
and shimmed full tests; constructed two manifest-only direct-copy trees inside
`.codex_tmp`; verified every declared SHA/JSON/Python file; copied the clean
tree directly with `scp -r`; used the server venv for staging/installed
hashes, JSON, compilation and tests; invoked `bash -n` on all declared shell
files; ran the independent audit and reporting-only finalizer in the same
zero-TSC stage directory; and copied only four compact JSON files back with
`scp`.  No archive, global Python, server Git, Ray, `gotsc`, TSC, controller,
plant advance, new raw, or new snapshot was run.
