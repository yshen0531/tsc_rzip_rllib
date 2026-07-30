# Stage4.2R3c3 final forensic report

Date: 2026-07-31 Asia/Shanghai

## 1. Result

Stage4.2R3c3 passed its preregistered identification gates.

This conclusion is not based on the saved verdict. It was reproduced from
all 256 server-side raw JSON.GZ trajectories by both the stage postprocessor
and a separate raw-response forensic tool.

```text
expected / parsed raw                         256 / 256
environment success / completed               256 / 256
exact plant restart                            256 / 256
causal and exact probe execution               256 / 256
central-symmetry groups                        128 / 128 PASS
matched-hidden-history groups                    64 / 64 PASS
full-rank conditioned response groups            32 / 32 PASS
maximum current utilization                   0.3904 <= 0.55
formal-contract pass                           125 / 256
formal-contract failure                        131 / 256
```

Formal tracking was prospectively declared diagnostic-only for this
identification stage. The 131 formal failures are real outcomes of perturbed
probe trajectories, but they do not invalidate a passed response-identification
gate and none of these trajectories may enter an expert dataset.

## 2. Exact identity

Local branch:

```text
codex/stage4_2r3c3-restart-response-id
```

Runtime implementation checkpoints:

```text
b01d523  add restart local-response identification
e98f78d  canonicalize Linux package checksums
57789c3  retain explicit causality audit counts
8623bcf  separate empty-package and installed suites
```

Independent forensic-tool checkpoint:

```text
83e78e4  add independent raw response forensics
```

Runtime identity:

```text
stage
  Stage4.2R3c3

package revision
  r42r3c3_restart_task_clock_local_response_identification_v1

controller revision
  restart_task_clock_local_response_probe_v42r3c3

runtime and audit package fingerprint
  1ba40b276a6a998e266e68d044c8ad3e819d86b6f7c8e52c7c60c6000a05a661

control-spec digest
  141e2d167424ad1ab4ddfc6a68ac3a795abcfa1ecc775f4e30a18857d28ae56f

visible-reference-manifold digest
  538e081d0212174c00ac921b2fd1ce9cf7df4b69e6810892fa9aaf7202e47f9a
```

Selected source fingerprints:

```text
R3b
  5c5b6707908cf8777889ef2b00aeef93e7f516d8ac6915687efe7777fa280cee

R3c
  dcf614361bec4bd8d8cdede3c034c728563c84ca298523b9f641a90698dc95f4

R3c1
  6da08914bd42b4975cab45744699f53b8213c761f297272592f28801b1c12b33

R3c2
  18294397178aa23afb706f39f9963b485c362f0343d3f53166943e744567c39e
```

Load-bearing runtime package file hashes include:

```text
PACKAGE_MANIFEST.json
  26ce9dc16a0bac00e73542bd52325ab2adb54ed4d453570e850099e5f1012ee4

resolved config source
  7181bde6b18a52e54d386094a8da48c0eb8d2507bb9feab0c2507a08eaf2e793

R3c3 diagnostic module
  766b50a819d188e529fbe034babef47128db6f361b0ad8368fb2bf5562fe6a77

server postprocessor
  b60e8f0564d3fd5d9b2712a7028aed15a724edc76b488029179aa6ac671fec00
```

The later independent audit script was not part of the runtime package
fingerprint. Its local and server SHA-256 was:

```text
0e08a876c34efbfccc50e3144e475be5c65d804d9dd403c04a373bd7d8d3eb54
```

## 3. Remote execution and evidence

Remote project:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Exact run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3_runs/
stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427
```

Exact real-run log:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182632.log
```

Exact audit directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3_audits/
stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427
```

The real campaign used the fixed 128-CPU Ray capacity in two batches of 128.
The exact driver PID was `1383534`. It stopped naturally after all 256 tasks;
no process was killed and no raw task was rerun.

Run inventory:

```text
1048 files
25,371,364 bytes
ef377ce1367d7a969b8f90cdb247445106f50b8706146f4c97b312892e909754
```

Raw inventory:

```text
256 JSON.GZ files
8,933,607 bytes
88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563
```

Audit evidence:

```text
server audit SHA-256
  5172fc54a8446418bbcccd31c84515f62ad2594a52904b831a3b2064d52a44b4

independent raw-response forensics SHA-256
  1a1d1acb2b6401a726a5e313301d9a37643cf023b4d2013a9f9c37e23f8a097b

local compact evidence inventory
  30 files / 1,871,530 bytes
  ed2443a8e3ea5d9559517a815df33bbb706263a3559f902953fcc940898cc957
```

Large raw JSON.GZ and generated environment variants remain server-side.
Only compact summaries, fingerprints, audits, derived rows, and complete
R3c3 logs were downloaded.

## 4. Offline gate

The offline phase ran before any R3c3 real TSC task and did not produce raw
trajectories.

```text
probe specs exact                             256 / 256
baseline contexts exact                         32 / 32
R3c1 baseline first action exact                32 / 32
probe first action preserved                    32 / 32
hidden-wire invariant first action              32 / 32
future action use                                      0
future measurement use                                 0
pair/history label use                                 0
source-result use                                      0
```

The same run identity was then safely resumed with the exact same runtime
package fingerprint for the real campaign.

## 5. Raw execution integrity

Every raw result had:

- the exact stage and controller revision;
- `completed=true` and `success=true`;
- a fresh controller and fresh TSC process;
- exact visible, coil-current, and full wire-current restart state;
- a complete controller trace;
- four task-clock-relative probe issues;
- requested and applied probe values equal within the frozen `1e-12`
  tolerance;
- zero requested and applied probe net within the same tolerance;
- the exact delay-relative first-effect state;
- no solver failure;
- no hidden-wire, source-action, source-coil-current, source-wire-current,
  future-current-run, pair/history-label, or source-result controller input.

Trajectory inventory:

```text
normal actuator: 64 trajectories of 36 states / 35 actions
weak actuator:   64 trajectories of 38 states / 37 actions
per batch, duplicated over two batches for 256 total trajectories
```

Across the first completed 128 raw files, the largest requested-versus-applied
probe delta was `6.94e-18` and the largest absolute zero-net residual was
`2.78e-17`, both far below `1e-12`.

## 6. Identification gates

### 6.1 Central symmetry

All 128 signed response groups passed.

```text
metric                              observed maximum       gate
even R/Z velocity RMSE              0.0012790224 m/s       0.004 m/s
even R/Z position RMSE              0.0001068371 m         0.0005 m
even Ip RMSE                        2.8750260 A             20 A
```

The worst velocity-symmetry group was the prefix-9 direction-1 pair,
`minus_first`, offset target, weak actuator, deadline mode 1. It still had
more than a factor of three margin to the preregistered velocity gate.

### 6.2 Matched hidden-history response

All 64 paired-history response groups passed.

```text
metric                              observed maximum       gate
odd R/Z velocity disagreement       0.0013169411 m/s       0.006 m/s
odd R/Z position disagreement       0.0001102332 m         0.001 m
odd Ip disagreement                 2.4495309 A             40 A
```

This means that, inside the exact development bank and the `0.0075`
two-mode probe envelope, changing the hidden vessel/eddy-current history
while keeping the selected visible restart context matched did not materially
change the measured local signed response.

It does **not** mean that hidden-history control robustness is independently
validated. The histories are the same four selected development pairs, and
the probe test measures local response agreement rather than successful
formal closed-loop tracking under new histories.

### 6.3 Conditioning

All 32 context response matrices had rank 4 and passed:

```text
selected velocity condition number
  minimum   1.8784648258
  mean      3.9844974198
  maximum   8.0983995652
  gate     25
```

The four early/deadline, mode-0/mode-1 basis columns therefore remain
separable enough for the prospectively defined bounded local model.

### 6.4 Current envelope

The largest current utilization was `0.3904`, below the frozen `0.55` gate.
No current limit or action semantics were changed after observing results.

## 7. Formal tracking is separate

Formal outcomes of the perturbed probe trajectories were:

```text
all probes                125 / 256
nominal target             96 / 128
offset target              29 / 128
normal actuator            93 / 128
weak actuator              32 / 128
plus-first history         64 / 128
minus-first history        61 / 128
early mode 0               31 / 64
early mode 1               32 / 64
deadline mode 0            30 / 64
deadline mode 1            32 / 64
```

These numbers are scientifically real, but the probes were designed to
identify response, not to improve formal tracking. They neither certify an
MPC controller nor weaken the immutable arrival/hold contract.

## 8. Error classification

Final scientific run:

```text
runtime or environment errors                         0
packaging/import/deployment errors affecting run      0
raw or snapshot corruption                            0
statistics/reporting errors                           0
plant-restart failures                                0
controller-causality failures                         0
probe-execution failures                              0
solver failures                                       0
identification design failures                        0
real formal tracking failures                       131
```

The 131 formal failures are not R3c3 identification failures. R3c3 itself is
a finite development-envelope identification success.

Pre-run and audit incidents, kept separate from the scientific conclusion:

1. The first staging attempt exposed CRLF-sensitive SHA parsing. No tests or
   TSC ran from that staging tree.
2. A later staging tree contained compile-created `__pycache__` files and
   exposed an overly broad package test harness.
3. The `57789c3` package passed hashes/import guards, but its empty-package
   harness tried to run an old R3c2 test that correctly expected R3c2 root
   scripts absent from the R3c3-only staging tree. `8623bcf` separated focused
   empty-package tests from installed-project full tests.
4. One installed full-test command had a heredoc quoting syntax error, so
   tests did not run in that command. The corrected `unittest discover`
   command then passed 529/529 before TSC.
5. An early monitor queried the wrong R3c3 raw subdirectory and displayed
   zero while the correct directory already held files. This was a monitoring
   path error; the run and raw were unaffected.
6. A deliberately stricter Python-list equality diagnostic reported
   requested/applied probe inequality because of approximately `7e-18`
   floating-point roundoff. The preregistered `1e-12` comparison passed every
   trajectory.
7. A compact multi-`scp` download command exceeded its local tool timeout.
   Missing compact files were fetched over one direct SFTP connection and the
   final local inventory was fully verified.

None of these incidents changed the controller, experiment matrix, physical
actions, formal contract, or final raw results.

## 9. Validation actually run

Local/repository:

- repository root/PWD boundary check;
- Python compile of the independent forensic tool;
- all R3c3 focused unit tests, 13/13;
- complete unittest discovery with the repository Windows `resource` shim,
  529/529;
- all downloaded JSON parse;
- compact evidence size/hash/digest verification;
- independent synthetic probe-trace, central-symmetry, hidden-history, and
  condition-number checks;
- Git diff checks and focused checkpoints.

Final package validation completed before TSC:

- all repository JSON parse;
- compile/import closure;
- declared package inventory and 156 file hashes;
- source fingerprint and resume compatibility;
- empty-directory direct-copy simulation;
- no undeclared source-tree dependency.

Server:

- exact project and virtualenv preflight;
- final staging package hashes, `bash -n`, compile/import closure, scientific
  guards, and 13/13 focused tests;
- installed package verification and full 529/529 suite;
- offline no-TSC gate;
- exact safe resume of the offline run identity;
- fixed Ray capacity and actual PID monitoring;
- worker traceback/error checks;
- 256/256 real TSC completion;
- server-side raw/manifest postprocess;
- second independent server-side raw forensic recomputation;
- compact direct SFTP transfer and local hash verification.

The local virtualenv does not contain `pytest`; one attempted `pytest`
invocation therefore did not run tests. A bare Windows `unittest` invocation
also cannot import POSIX `resource`; the repository's existing portability
shim was loaded and the same focused and complete suites passed. No package
was installed to change either environment.

## 10. Advancement and limits

R3c3 supports one narrow advancement:

```text
freeze the authenticated bounded local response envelope
→ preregister Stage4.2R3c4 restart-integrated target-conditioned deadline MPC
```

R3c4 may use only visible state/current, target, actuator estimates, and the
authenticated bounded response model. It must retain the exact plant restart,
controller causality, current limits, and immutable formal timing contract.

Still not validated:

- a successful restart-integrated MPC expert;
- independent new hidden histories;
- independent different initial states;
- unseen targets;
- continuous delay/gain/slew;
- plant/Jacobian error;
- measurement noise and a validated observer;
- disturbance recovery;
- independent long hold.

Behavior Cloning, DAgger, and bounded residual RL remain prohibited.

## 11. Commands actually used

Command classes actually executed included:

```text
git status / branch / log / diff / commit
repo-venv Python compile and unittest discovery
local JSON and SHA-256 inventory verification

ssh/scp/sftp using the already authorized fixed public-key endpoint fallback
remote HOME/PWD/project/virtualenv preflight
remote bash package verification and unittest discovery
offline R3c3 launch
safe same-run resume
exact PID/raw/gotsc/Ray-log monitoring
server-side R3c3 postprocess
server-side independent raw-response forensics
direct compact file transfer without archives
```

No local archive was created or extracted. No large raw result tree was
downloaded. No Git, network dependency, root action, package installation,
or broad process kill was used on the server.
