# Stage4.2R3c3T13S24D1R14R8R51 forensic report

Date: 2026-08-09 Asia/Shanghai

Final route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_SENTINEL_IMPLEMENTATION_GATE_FAIL_NEW_IDENTITY_REQUIRED
```

R8R51 is final, immutable, and must not resume or rerun. Its 208 raw files
are identification probes and are forbidden from expert, BC, DAgger,
residual-RL, or any other learning data.

## 1. Identity, package, and execution

```text
design checkpoint          a82effc
implementation checkpoint  274e970
package checkpoint         04d3250
run directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r51_runs/
  stage4_2r3c3t13s24d1r14r8r51_reduced_q0_transport_bridge_identification_sentinel_20260809_04d3250_v1
```

Local project-venv validation passed focused `10/10` and full shimmed
`1553/1553`. Fresh empty direct-copy validation passed 1,248 declared
hashes, 149 strict JSON files, 488 Python compilations, focused `10/10`, and
full `1553/1553`. Server staging and installed validation repeated those
gates and passed 455 `bash -n` checks, with one expected isolated-package
skip. Transfer was direct `scp -r`; no local archive was created or
extracted. Both hosts used only their existing virtual environments.

Primary and independent offline construction passed all 208 frozen cells and
agreed exactly. The single authorized real campaign completed all 208 worker
tasks, each as a structured controller action-gate stop.

## 2. Immutable raw evidence

```text
raw files                                        208
raw bytes                                  5,155,700
raw inventory SHA-256
  ea6ba731534adc810adac98172971aed031a42355ac8c443a3aceab6831751dd
primary / independent raw agreement              true
primary raw route
  REDUCED_Q0_TRANSPORT_BRIDGE_SENTINEL_SAFETY_FAIL_REDESIGN
```

The primary raw route above is preserved as the original program output. The
source-aware post-result classification below is more specific: no intended
R8R51 action was applied, so this is not a physical action/current/plant
safety result.

Independent strict parsing and authenticated R8R7 comparison reproduced:

```text
spec identity                                  208/208
completed structured failures                  208/208
authentic restart state 0                      208/208
source semantic states 0..10                   208/208
source semantic trace 0..9                     208/208
trace differences limited to wrapper metadata 208/208
calibration prefix exact                       208/208
forbidden controller inputs absent             208/208
trajectory length exactly 11                   208/208
controller trace length exactly 10             208/208
```

Every task stopped while computing the task-step-10 q0 event. State 10 still
contains the source task-step-9 action; there is no task-step-10 trace row and
no state 11. Therefore:

```text
intended q0 actions applied                         0
candidate actions constructed                       0
candidate actions applied                           0
physical response states opened                     0
tracking / MPC / Gate-A outcomes opened              0
```

The original `stage_state.json` field
`response_outcomes_opened=true` is a reporting bug caused by the generic
failure finalization path. It is not evidence against the raw lengths and was
not rewritten.

## 3. Exact cause

The frozen design required an exact Card15 hold at the visible current, not a
binary64 all-zero normalized action. Offline construction called the shared
Card15 refresh calculation and accepted its exact representable action. The
real controller then added an implementation-only predicate:

```text
q0_zero_target = array_equal(action_norm_tsc, zeros(14))
```

and recomputed `passed`. Card15 reconstruction of the current readback needs
a tiny nonzero grid refresh. Across all 208 tasks:

```text
q0 incremental normalized action Linf
  3.3333333296544274e-06 .. 3.7037037048793097e-06
predicted current utilization
  0.36545 .. 0.3907
q0_zero_target=false                            208/208
actuator prediction passed                      208/208
exact fields / exact target                     208/208
finite / incremental / total action             208/208
current utilization / no clipping               208/208
no saturation                                   208/208
```

Thus the only false criterion was the undeclared exact-zero predicate; every
frozen Card15, action, current, clipping, saturation, and finite-value safety
criterion passed. The offline and real paths evaluated different gates.

This is an implementation/integration and offline/real gate-parity failure
before q0 application. It is not a TSC runtime, deployment, restart,
causality, raw-integrity, physical q0-response, candidate-authority, tracking,
MPC-feasibility, plant-reachability, or Gate A conclusion.

## 4. Evidence hashes

```text
raw primary
  330c572182048cc3360b9061a153ab995b508263d45de666ffcf3bb76d9f0b55
raw independent
  0468f446ed8cfb3a21e985c0006e2293bfbb218892458107f37513d49e8b6472
partial-prefix independent forensics
  daf7018de334fe0f7ee5bae561d4f26df02de569033ffe953526244d43ead414
failure compact audit
  e376c5b4c1f1e8654d8dd5fd985d55a3efad0de64139e65c48c5c97a11f0a086
failure final report
  41b2c79591c3a4dafe522dad994a14ddcc3b0cb5395bbe01afab747044dc8d2c
stage state
  1307d2f8cda12ae43c1beffa4f088640bf21025ef24720b7356ba43097d7dcae
stage manifest
  80eeec45e7816d97d635dec070f0e3eef4199443be84a95885a2e1c49a2dd994
implementation source
  4a936b7577585d5dc5ee66f9a4a35f93bd043c6198ba66b016983c1eac62be0a
config
  4dd3bbee2bc83560f2319807b91939373014690141ab977bc7d82ff0f0962b30
PACKAGE_MANIFEST.json
  9691caaec8a43b2d1bc8eedb941bbea43f378aece9911a635fee264b8ccefb64
SHA256SUMS
  530586ce8fc291f508d673bd6adfb969c1cdadef2512a5c0a3ea24513ff58dc8
```

Downloaded compact evidence is under
`artifacts/server_runs/r8r51_failure_04d3250_v1/`. Large raw remains on the
server.

## 5. Disposition

The existing conditional R8R52 design requires an exact R8R51 PASS and is
permanently blocked. Correcting controller source changes the experiment
identity even though it restores the originally frozen action semantics.
Only the separately frozen R8R51R1 q0-gate integration sentinel may execute
the unchanged 16-context by 13-candidate campaign. Its conditional R8R51R2
model design is also frozen before R8R51R1 implementation or response
inspection.

Neither R8R51 nor either conditional successor is Gate A. All learning and
Gate B remain blocked.
