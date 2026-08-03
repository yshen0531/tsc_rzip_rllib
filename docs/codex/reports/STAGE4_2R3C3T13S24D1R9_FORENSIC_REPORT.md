# Stage4.2R3c3T13S24D1R9 forensic report

## Result

Stage4.2R3c3T13S24D1R9 passed its preregistered zero-TSC central-row
replacement preflight. Two independent official executions produced five
byte-identical JSON outputs. The primary and independently implemented audits
agreed exactly. No Ray actor, `gotsc`, TSC controller, plant step, or new raw
trajectory was executed.

The accepted route is:

```text
CENTRAL_ROW_REPLACEMENT_PREFLIGHT_PASS_EXACT_ROW_SENTINEL_DESIGN_REQUIRED
```

This pass authorizes only design of D1R10, a separate real-TSC safety sentinel
for the seven matrix rows without exact dynamic evidence. It does not authorize
D1R10 execution, the full replacement identification campaign, MPC, expert
data, BC, DAgger, or RL.

## Exact revisions and package

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
D1R9 implementation commit
  3c16081 Implement D1R9 central row preflight
D1R9 package commit
  a4547d5 Package D1R9 central row preflight
package revision
  r42r3c3t13s24d1r9_central_row_replacement_preflight_v1
package declared files
  740
PACKAGE_MANIFEST.json sha256
  0d1c0f5fa490b93323c633c48a148b80717070bdfa207271796a515023f8edd9
SHA256SUMS sha256
  cb6699834e0edae620d88dab4057cbdded180436bf6a4c775edb4bbb48f0c182
design sha256
  06addede44305d2dfb946bcc3395c74dae448cfa11922f2f94e1ec208f3fd62c
config sha256
  c86c755e6af70edbb76f12647ff20ab88b026f52331e7ba6fdf7058249d66bf7
primary implementation sha256
  d0560cef097145f795a8e3871e51c265e4feb45ff3ad57c378b989e4e9c7c3be
independent implementation sha256
  0dcb7e510d2d3a36a74b2241b1ab6dc32128cd3569c4fe0b42212caab3768b82
```

## Server paths

```text
staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s24d1r9_a4547d5
installed project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
official run 1
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r9_audits/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_20260803_a4547d5_v1
official run 2
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r9_audits/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_20260803_a4547d5_v2
server acceptance
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r9_audits/d1r9_server_acceptance_a4547d5.json
```

Only four compact files totalling 14,644 bytes were downloaded to the local
repository temporary area. The 1,586,858-byte D1R10 candidate table and all
large historical raw trees remain on the server.

## Source authentication and inventories

D1R9 re-read and authenticated the following existing raw inventories without
copying or modifying them:

```text
S24 raw                                     600
D1R2 raw                                     54
D1R6 raw                                      9
D1R8 raw                                    108
D1R8 raw bytes                        6,468,042
D1R8 raw inventory digest
  8fd08fd0e8c6c216f4a98c3a6a113f0f6c29aea16dfae92f52cc857e2a801ec2
new D1R9 raw                                  0
new TSC or plant steps                        0
```

Both official output directories contain the same five files. Their bytes and
hashes are identical across the two executions:

```text
central-row detailed JSON         255,889 bytes
  d9be8c7959e9831fba00ea45039dde4870ea792c3e40115e0d3890e56b61647f
D1R10 candidate specs JSON      1,586,858 bytes
  93ee3961dc5a439a6eec76c84d87b5535e3d4c84fc4b0173ad9703a6344e906e
independent forensics JSON          9,788 bytes
  0a76ba9ae2b63d9edf827de2b4003e3b6303bf976ac9555e2b7ca42289550114
manifest JSON                         970 bytes
  537c97c06c1fff528ceb19e18104fc6ccf22b1e0c52ea3df287092ee62aa3a57
summary JSON                           951 bytes
  bba59e757de0146773aaa9b986915c8f4b7874d5c762ce1926e66844de47bb34
server acceptance JSON               2,935 bytes
  81b12a9391a928495b24884e6aa7deac3416bda796ea9ac063d17f5b1b415563
```

All JSON parsed strictly. The independent implementation reported
`primary_output_exact_match=true`.

## Exhaustive selection and static replay

D1R9 enumerated every `C(16,8) = 12,870` central-primary set. Exactly 495
sets passed all preregistered structural constraints. The frozen prospective
selection objective chose:

```text
sorted central primary indices
  [0, 1, 3, 4, 5, 7, 8, 9]
ordered central primary indices
  [0, 4, 1, 5, 3, 7, 9, 8]
changed matrix rows
  [22]
requested matrix digest
  106dfed384febb16019e4d39ce1da03762ad9dbb5e8e69120a4a9d9acdebc30b
known contradicted selected rows
  []
exact-safe selected rows
  17
unknown selected rows
  [3, 7, 11, 15, 20, 21, 22]
```

The actual inherited static replay passed every required construction:

```text
contexts                                      40 / 40
finite constructions                      7,680 / 7,680
issue gates                               3,840 / 3,840
cancellation gates                        3,840 / 3,840
central sign gates                        1,280 / 1,280
global rank/condition contexts               40 / 40
slot rank/condition blocks                  160 / 160
late novelty contexts                        40 / 40
maximum actual global condition       2.0364010227807228
maximum actual slot condition         1.450668532237749
minimum actual late residual          0.9723253261475752
```

The deterministic D1R10 table contains 126 new-identity specs, with ordered
spec digest
`52ac8dc95272caef7670df4c94d764ffc244e2630320371d1124a566b1a7a12c`.

## Validation actually run

Every local command used `venv/Scripts/python.exe`; every server command used
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`.

```text
local focused tests                         23 / 23
local complete tests                     1,004 / 1,004 (1 skipped)
empty-directory focused tests               23 / 23
empty-directory complete tests           1,004 / 1,004 (1 skipped)
server staging focused tests                23 / 23
server staging complete tests            1,004 / 1,004 (1 skipped)
server installed focused tests              23 / 23
server installed complete tests          1,004 / 1,004 (1 skipped)
official zero-TSC executions                  2 / 2
byte-identical official output files          5 / 5
```

Checksums, strict JSON parsing, Python compile/compileall, shell syntax,
declared import closure, empty-directory direct-copy simulation, and installed
package verification all passed. No archive was created or extracted.

The Windows empty-directory complete-suite invocation initially used direct
`unittest discover`, which does not load `tests/conftest.py`; 27 imports then
failed because Unix `resource` is unavailable on Windows. Loading the existing
repository portability shim produced the authoritative 1,004/1,004 pass. This
was a local test invocation/environment error, not a code or experiment error.

Two ad hoc server acceptance attempts made after both official runs guessed a
wrong detailed filename and then treated the candidate wrapper as a list. They
failed before writing the acceptance file. The corrected server-venv script
used the actual inventory, wrote the hash-bound acceptance above, and changed
no official output. These were operator postprocessing errors, not D1R9
runtime, raw, statistical, reporting, or design failures.

Server validation and official-run logs contain no traceback or `ERROR:`
token. Their hashes are:

```text
staging validation
  0d8a4a9594cde5aca95aede5bb7ba274b47b97bc61db89e2088e3053e3027cbd
installed validation
  5caed0d120505c5007da6051052a3b0c479270bb22285059e9a68dd039f660a9
official run 1
  612b9656d9f8715f99de3881df7b9632e640922a86ca89f2516f3f2bd16cfe01
official run 2
  b707e93336e73910c2cb5bc9d93f88124dd708e0af7f888ca5af3f44306e894a
```

## Scientific classification

- Runtime/environment error: none in D1R9.
- Packaging/import/deployment error: none after authoritative validation.
- Raw/snapshot corruption: none detected in authenticated source evidence.
- Statistics/reporting error: none in either official implementation.
- Design defect: none against D1R9's frozen zero-TSC gate.
- Real closed-loop control result: not run and therefore neither passed nor
  failed.
- Plant restart result: not run; D1R9 only authenticated inherited evidence.
- Formal tracking result: not run; the 250/270 ms arrival and 350/370 ms hold
  contract remains unchanged.

D1R9 proves only that the replacement matrix is prospectively well
conditioned, statically safe on the inherited 40 contexts, free of already
observed exact-vector contradictions, and paired with a deterministic D1R10
sentinel table. The seven unknown rows still require authentic dynamic TSC
evidence. Even a D1R10 pass will not by itself validate a full transition
model, MPC, restart transport control, unseen targets, continuous actuator
variation, noise, disturbance recovery, or long hold.

## Next action

Freeze D1R10 before implementation. D1R10 must run exactly the 126
preregistered row/context combinations with the unchanged 0.25 incremental
cap, the stricter 0.24 online-cancellation cap, fresh TSC/controller instances,
authentic restarts, causal traces, and the immutable formal horizons. Only a
126/126 full-horizon safety pass may authorize design, but not execution, of a
full 24-row replacement identification campaign.
