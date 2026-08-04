# Stage4.2R3c3T13S24D1R10 forensic report

## Result

Stage4.2R3c3T13S24D1R10 completed its preregistered exact-row safety
sentinel. All 126 fresh authentic TSC trajectories passed restart, causality,
calibration, issue/cancel execution, current, action-margin, raw-integrity,
and full-horizon gates. Independent server-side recomputation over every raw
JSON.GZ agreed with the official aggregation.

The accepted route is:

```text
EXACT_ROW_COMPLETION_SENTINEL_PASS_FULL_REPLACEMENT_IDENTIFICATION_DESIGN_REQUIRED
```

This is a finite probe-schedule safety result, not a target-tracking or MPC
pass. Formal tracking was diagnostic only and passed 28/126. D1R10 authorizes
only prospective design of a separate full replacement identification
campaign. Its 126 probe trajectories may not be fitted into that campaign's
new-identity model and are forbidden from every expert dataset.

## Exact revisions and fingerprints

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
D1R10 design commit
  0f2d08a
D1R10 implementation commit
  8c7628f
D1R10 execution package commit
  2ece6df
standalone-forensics hotfix commit
  9068bf0
hotfix package commit
  280513c

D1R10 design sha256
  1fd2480087736348a0be0e3fb9e7be04448e2c1d2d746ecf00c4f346a9c435b2
execution-package declared-file digest
  0f87a005c37a2dbeffed14d0313f083476cb8abbe15fdf93db1ad0dd56757311
execution config sha256
  9d3cbdc6839e8aef6c8777b4c1f4d7e8dd09d81d23c853729ed0fe0a123a6b05
execution implementation sha256
  754dc9f7ac44f7159ed005a8cd34f36957911d571a5cf5170235359ef468e6c2
execution-time forensics sha256
  6895d36f5ab92e4a65e5e7a588072245654ec2c0dee0a8a9966d7154b5d8e978
D1R9 ordered spec digest
  52ac8dc95272caef7670df4c94d764ffc244e2630320371d1124a566b1a7a12c
D1R9 requested-matrix digest
  106dfed384febb16019e4d39ce1da03762ad9dbb5e8e69120a4a9d9acdebc30b
context digest
  58cf5ab4c5548d5c2bfe5b4d40622392219911a635d1b954badd0814c3305a42
base-S24 config sha256
  ff307a45d067e82d9db506cbb618b2912f35715f2760d6298e34e0c64ac4b2fa
base-S24 implementation sha256
  29283348f004f90eeea5e563ae2e5397397e324bfb6b51ecff3436398938c6e9
```

The post-run entrypoint hotfix changed only repository-root discovery in the
independent audit script and its cwd-independent regression test. It did not
change the controller, specs, task matrix, gates, raw data, or official
aggregation. The hotfix package fingerprints are:

```text
PACKAGE_MANIFEST.json sha256
  06885d3528616f0c2511302c64eb312cae0df6d36bfca7d5760c0953df301864
SHA256SUMS sha256
  81ad13a805f37fd2af60ae98fc9af11b26d2004edb891c559048c9917867ba1d
declared source files
  753
```

## Server paths

```text
official run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r10_runs/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel_20260804_2ece6df_v1
stage directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r10_runs/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel_20260804_2ece6df_v1/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel
offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r10_offline_2ece6df_v1.log
rollout log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r10_rollout_2ece6df_v1.log
postprocess log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r10_postprocess_2ece6df_v1.log
independent-audit directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r10_audits/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel_20260804_2ece6df_v1
hotfix staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s24d1r10_hotfix_280513c
installed project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Large raw and snapshot evidence remains on the server. Only the 44,963-byte
hash-bound compact acceptance was downloaded to
`.codex_tmp/d1r10_280513c_compact/`.

## Expected and actual inventory

```text
expected specs / fresh TSC tasks                         126 / 126
strict raw JSON.GZ                                      126 / 126
successful full-horizon trajectories                    126 / 126
authentic TSC / causal / physical / phase prefixes      126 / 126
restart / causality / calibration                       126 / 126
issue events                                            504 / 504
cancel events                                           504 / 504
issue/cancel/margin gates                               504 / 504 each
forbidden controller-use count                            0
failed action applied count                               0
plant advance after failed action count                   0
raw bytes                                         7,617,161
raw inventory digest
  0e148a2fe9c975ef710dfad4f063e7564dd9a8c067bb82b6d3bae2a35a1c2eb6
maximum cancel incremental normalized action L-infinity
  0.20245088117122614
maximum current utilization
  0.392
formal tracking diagnostic                               28 / 126
```

Every replacement row `3, 7, 11, 15, 20, 21, 22` passed 18/18 trajectories
and 72/72 issue/cancel/margin events. Each row passed the diagnostic formal
tracking metric in only 4/18 contexts. Every one of the 18 pair/history
contexts passed all seven safety trajectories. The only diagnostic formal
passes were both histories of `p9_q1_a0p900_gap4_settle4` and
`p9_q2_a0p750_gap4_settle4`, each 7/7; the remaining fourteen contexts were
0/7. This pattern is evidence against treating the safety result as reliable
transport control.

The top-level selected snapshot audit passed 18/18. A nested inherited helper
reports `expected=40`, `actual=18`, and `passed=false` because it retains the
original fixed-40 S24 contract. D1R10 deliberately reaggregates this helper
over its selected 18-snapshot subset and its unit test fails if any selected
snapshot fails. This is expected inherited diagnostic detail, not a snapshot
or summary defect.

## Independent recomputation

The independent server audit parsed every raw file and reproduced strict
identity, restart, causality, calibration, authentic TSC prefixes, schedule
events, action/current margins, formal diagnostics, and the final route. Its
authoritative output is:

```text
stage4_2r3c3t13s24d1r10_server_audit.json
bytes
  219,930
sha256
  acebaff491b58e59e54b4365d1981a1a9b6e4798c3cfe99b8f54983a6d204371
```

After the standalone-entrypoint hotfix, the same audit was run from `$HOME`
without `PYTHONPATH`. The v3 output was byte-identical to the pre-hotfix v2
output and retained the same SHA-256. Therefore the hotfix repaired invocation
only and did not alter scientific semantics or statistics.

Additional exact result hashes are:

```text
official final_result.json
  26a265ec1307f09043855d3a957cc30415545b24cd8ff61d2213be89e30f7b3d
official internal audit
  72ab4383def939882ff6991c50152fc9966e24d9b8fe5b77f7f23794eaa818ad
postprocess log
  26c843543adf64a3b9dd9e3667764ea670e9a304d7b4af88cc546d6adf5b876e
compact acceptance
  623e64b0a5b33d247127f0b8ecceba610a4b6d1673af4d2ea2d031d1d98f76da
```

## Errors and corrections

The following incidents are preserved and classified separately:

1. The first D1R10 staging validation rejected `SHA256SUMS` because its line
   endings were CRLF. Nothing was installed and no offline audit, Ray actor,
   TSC process, raw file, or plant step ran. Regenerating the same checksums
   with LF changed packaging only.
2. The first post-run direct independent-audit invocation from outside the
   repository failed before output with `ModuleNotFoundError:
   tsc_rzip_rllib`. It ran no TSC and changed no raw. Commit `9068bf0` made
   repository-root discovery independent of the caller's cwd and added a
   regression test. The hotfixed audit is byte-identical to the already
   successful audit.
3. The first hotfix SFTP attempt had not created every remote ancestor
   directory, so transfer stopped partway through staging. The incomplete
   staging tree was never validated or installed. The retry created all
   ancestors and directly transferred all files without archives.
4. Direct Windows `unittest discover` without the repository's existing
   `tests.conftest` portability shim produced 27 import errors because the
   Unix `resource` module is absent. The authoritative complete suite loaded
   that shim and passed. This is a test-invocation/environment issue, not a
   source or experiment failure.

None of these incidents changed the experimental identity, controller
semantics, physical actions, source fingerprints, raw results, task matrix,
or formal gates. Therefore no TSC rerun was scientifically required or
performed.

## Validation actually run

Every local Python command used `venv/Scripts/python.exe`; every server Python
command used
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`.

```text
local JSON parse                                      1,511 files
local compileall                                      pass
local focused hotfix tests                            11 / 11
local complete authoritative tests                 1,015 / 1,015
empty-direct-copy declared hashes                    753 / 753
empty-direct-copy focused tests                       23 / 23
empty-direct-copy complete tests                   1,015 / 1,015 (1 skip)
server staging declared hashes                       753 / 753
server staging focused tests                          23 / 23
server staging complete tests                      1,015 / 1,015 (1 skip)
server installed declared hashes                     753 / 753
server installed focused tests                        23 / 23
server installed complete tests                    1,015 / 1,015 (1 skip)
official offline specs/source/snapshot checks         126 / 126
official real TSC rollout                             126 / 126
independent complete-raw recomputation                126 / 126
post-hotfix cwd-independent audit byte match             1 / 1
```

Server preflight, exact-path guards, shell syntax, package verification,
imports, compile, JSON parsing, source authentication, fixed Ray capacity,
run/log capture, strict raw parsing, and compact-evidence hashing passed. No
local or remote archive was created or extracted.

The authoritative server validation-log hashes are:

```text
hotfix staging validation
  756de67ee438ce4e832fbc01749b4d4ed16fba68c97dc9f0f1ffb7aae68acb3e
hotfix installed validation
  adf8140dadc7e9547b0aa811ec9072c5d22f295cab8a309f848e00ac18177ebd
```

## Scientific classification

- Runtime/environment error in the real campaign: none.
- Packaging/import/deployment error: the pre-run CRLF package rejection and
  post-run standalone audit import failure above; both occurred outside real
  rollout semantics and were corrected without rerunning TSC.
- Raw or snapshot corruption: none detected.
- Statistics/reporting error in official or independent results: none.
- Design defect against D1R10's safety-sentinel gate: none; all 126 passed.
- Real closed-loop tracking conclusion: poor diagnostic coverage, 28/126;
  D1R10 was not designed or gated as a tracking controller.
- Authentic plant-restart conclusion: exact for this finite clean 126-case
  probe grid.
- Reliable MPC conclusion: not tested and not authorized.

D1R10 freezes only finite, same-source, discrete-schedule safety evidence for
seven previously unknown rows. It does not validate a learned transition
model, finite-horizon transport MPC, unseen targets, continuous actuator
variation, plant/Jacobian error, noisy sensing, disturbance recovery,
independent long hold, or deployment robustness.

## Next action

Freeze and execute a new-identity full replacement identification campaign
using the D1R9 24-row matrix over the original S24 20 whole-pair/40-context
split. It requires 1,000 fresh authentic trajectories: 600 training, 200
calibration, and 200 fresh holdout. The original S24 model family, fitting
order, tube construction, forbidden-input boundary, and phase-opening rules
remain unchanged; only the prospectively selected schedule matrix and all
new identities change.

D1R10 raw is authentication and safety evidence only. It must not enter the
new fit, calibration tube, holdout, MPC expert data, BC, DAgger, or RL. A
full identification pass may authorize only a separately preregistered
zero-TSC robust finite-horizon feasibility/controller design. RL remains
blocked.
