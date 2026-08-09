# Stage4.2R3c3T13S24D1R14R8R32 forensic report

Date: 2026-08-09 Asia/Shanghai

## Final classification

```text
RANK_REGULARIZED_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC
```

R8R32 is a clean, finite representation-design FAIL. The prospectively fixed
fold-local PCA rank 32 was unavailable in 344/1,161 outer
fold/interval/offset heads. No regression, prediction, residual, tube,
support, planning, formal-plan, controller, or physical result was produced.

This is not a runtime/environment, package/import/deployment, source/raw,
restart/causality, statistics/reporting, real-MPC, formal-control,
plant-reachability, or Gate A conclusion.

## Frozen identity

```text
design checkpoint                         dc04452
design SHA-256
d5e1e5e51b75267420282379386b24653180493e5f3fc3f19b6d6624c7ca838f

initial implementation                    5fbf62a
initial package                           be82504
rank classification hotfix                2d95371
accepted package                          3328499

accepted PACKAGE_MANIFEST.json SHA-256
ef1d599f5af840fade5d276a47bc630b095cc9b7eab9fc7933bc9ff5199d7608
accepted SHA256SUMS SHA-256
04e1657615a6e3bbdf0122bc8ae39a9f053f9e3ef334501ee59860fe6b033865
```

The frozen model retained fold-local standardization, sign-canonical PCA32,
the exact 178D score/action/score-by-q representation, ridge 0.01, whole-pair
and whole-schedule exclusions, and all unchanged point/tube/support/safety/
formal gates. No model hyperparameter or gate changed after a result.

## Validation and deployment

The accepted package declared 1,160 files plus manifest and checksum files.
Only direct directory/file copying was used; no local archive operation
occurred. Local work used only the project venv and server work used only:

```text
/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python
```

Accepted v2 validation:

```text
manifest hashes                                   1160/1160
declared JSON parses                                      135
declared Python compilation                               452
server bash -n                                            443
local focused                                           10/10
local full Windows-shimmed                           1421/1421
empty-direct-copy focused                               10/10
empty-direct-copy full                              1421/1421  skip 1
server staging focused                                  10/10
server staging full                                 1421/1421  skip 1
server installed focused                                10/10
server installed full                               1421/1421  skip 1
```

The `tsc-airgap` alias remained unresolved in the Codex process. Transfer
used the user-authorized fixed endpoint and noninteractive public-key options
without inspecting the key or SSH configuration.

## Preserved first attempt and reporting hotfix

The first accepted-code attempt is preserved at:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r32_runs/
stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight_20260809_be82504_v1
```

It stopped at the first genuine `rank < 32` result before regression, but a
broad primary exception handler mislabeled that expected scientific gate as
the execution-fail route:

```text
primary_failure.json SHA-256
433d8de7e8f32ed7992ec0f8b719542d6969df2664c5534db2fc648a5a1b54cd

stage_state.json SHA-256
bcc8deccbc251e8ce075c5eefd804573e6fd677a00d793b912874aeda2280f3d
```

Hotfix `2d95371` changed only fail-closed control flow and reporting. It
precomputes the already frozen rank gate for every pair and schedule head,
routes a shortfall to the preregistered model-fail route, and marks all later
metrics phase-closed. It did not lower rank 32, change a tolerance, reassign a
row, fit a model, or inspect any later result. The fixed implementation ran in
a new v2 output directory; the v1 directory was neither overwritten nor
resumed.

The first staging validation also completed every check successfully but
PowerShell converted unittest's normal stderr progress into an outer
`NativeCommandError`. A retry captured child stdout/stderr inside server venv
Python and returned an unambiguous exit 0. This was a local log-wrapper issue,
not a test or package failure.

## Accepted server evidence

Run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r32_runs/
stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight_20260809_3328499_v2
```

Stage directory:

```text
stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight
```

Authenticated exact source bank:

```text
trajectories                                          560
physical pairs                                          8
history contexts                                       16
schedules                                              35
interval records                                     3360
bank digest
a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest
80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest
0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

Final artifact hashes:

```text
primary_summary.json
59316eea910420a6f5e7239c6d120757a91091eaf13cb65cecc93de13959b236
primary_detailed.json
ccf82c817984fa2f51ca157732af5037826a278883ed3804a6238e6b9a3d83e8
preflight_model.json
6c7c81f0dd73b1f3e726471b1278348aab8dfc084c310b18e04cd40d0386745a
independent.json
ba0a08ef3c63e36a04d70fe2794298b2ff2e26d84d7b91b0be187d7fc37bfcf0
compact_audit.json
ff976bab8fe9ec763d110862dd76c3b6fa9d6625c193025708b955f938a65456
final_report.json
f1aa3f8a0a6269d3fec8593affc60fc1e8121fa4d179d11dc208e4a8228e0e34
stage_state.json
3bcb721cd061ca0b2be2a4ccbdbed6836f0ab9f340f0c09c069c6716a09d1af8
stage_manifest.json
59c93fa2b33399f6f05cdd824eb266d1ceee45597d8fec783e55dcd4042e3e46
```

Only compact/final/state/manifest were downloaded. The detailed and model
artifacts remain on the server.

## Scientific result

```text
requested PCA rank                                  32

whole-physical-pair heads                     152 / 216
whole-physical-pair failed heads                     64
whole-physical-pair minimum numerical rank           13

whole-schedule heads                            665 / 945
whole-schedule failed heads                          280
whole-schedule minimum numerical rank                 15

all heads                                       817 / 1161
all failed heads                                     344
all-fold minimum numerical rank                       13
```

The rank gate precedes regression by design. Therefore:

```text
regression / prediction / residual / tube               not run
state or action support                                  not run
planning / formal-plan evaluation                        not run
fault-injection planning                                 not run
Ray / gotsc / TSC / controller / plant             0 / 0 / 0 / 0 / 0
new raw / snapshots                                    0 / 0
```

All zero maxima, containment counts, repairs, oracle counts, and plan counts
are explicit phase-closed sentinels. They may not be interpreted as passing
or failing physical/model metrics.

## Independent agreement

The independent path rebuilt the source bank through the independent R8R31
raw readers and recomputed every fold/head SVD with separate rank code.

```text
primary bank agreement                            true
primary model/rank agreement                      true
primary outer agreement                           true
primary schedule agreement                        true
primary planning phase agreement                  true
primary route agreement                           true
primary outcome agreement                         true

maximum bank absolute difference                   0.0
maximum model absolute difference                  0.0
maximum outer absolute difference                  0.0
maximum schedule absolute difference               0.0
maximum planning absolute difference               0.0
```

## Route consequence

R8R32 is immutable and cannot be relabeled by lowering its rank. A new R8R33
identity was frozen before any R8R33 calculation. It fixes rank 12—one below
the independently reproduced all-fold minimum rank 13—without searching any
R8R33 response outcome. It retains every other model, exclusion, point, tube,
support, safety, formal, fail-closed, independent, zero-TSC, and
learning-prohibition gate.

R8R32 did not reach Gate A. Expert data, BC, DAgger, residual RL, and all
other learning remain blocked; all R8-family trajectories remain forbidden
from learning data.
