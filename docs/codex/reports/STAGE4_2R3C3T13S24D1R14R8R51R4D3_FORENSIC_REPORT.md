# Stage4.2R3c3T13S24D1R14R8R51R4D3 forensic report

Date: 2026-08-10 Asia/Shanghai

Final route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D3_CENTER_BRIDGED_TWO_PULSE_SCHEDULE_PREFLIGHT_COMPLETE_R51R4D4_DESIGN_REQUIRED
```

## 1. Scope and conclusion

R51R4D3 was a zero-new-TSC action-geometry preflight over ten immutable
R51R4 failed contexts and the complete ordered product of five frozen targets:

```text
10 contexts x 5 first pulses x 5 second pulses = 250 specifications
```

Unlike the failed direct target-to-target D1 schedule, D3 returned exactly to
the stored q0 center at task step 16, held that center with an exact zero
increment at step 17, issued the second independently reconstructed pulse at
step 18, and returned exactly at step 22. Primary NumPy and structurally
independent scalar implementations passed all 250 schedules and agreed on
every event digest, criterion, eligibility decision, and coverage set.

This is a finite center-bridged two-pulse action-geometry PASS only. It is not
a measured response, authority, observer, controller, MPC, formal-control,
robustness, plant-reachability, learning, or Gate A result.

## 2. Frozen checkpoints and package

```text
prospective design checkpoint                         bdfeeae
implementation checkpoint                             80e7059
accepted package checkpoint                           602c8a4
```

Frozen design and SHA-256:

```text
docs/codex/reports/
  STAGE4_2R3C3T13S24D1R14R8R51R4D3_CENTER_BRIDGED_TWO_PULSE_SCHEDULE_PREFLIGHT_DESIGN.md
7e0a76f36f889f3dbd31e43c30be85b989120e584ac9e8d145c63109c66f84c0
```

Accepted package fingerprints:

```text
PACKAGE_MANIFEST.json  ccc485bea6fc71033da46cd26845722781dad933375f684d359e6c91f4f2a877
SHA256SUMS             cd0246ad266b6865f1ddcd53da6f352ec8df85dcfe47b9d6ce8dfe70142095a8
```

## 3. Validation and direct deployment

Local validation used only `venv/Scripts/python.exe` and loaded the existing
`tests/conftest.py` Windows `resource` shim before unittest discovery. Server
validation used only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`.

```text
declared hashes                                      1299 / 1299
fresh empty-copy physical files                      1301
manifest JSON                                         154
package JSON including PACKAGE_MANIFEST               155
Python files compiled                                  512
server bash -n                                       461 / 461
focused tests                                           8 / 8
full source tests                                    1626 / 1626
full empty-copy/server tests                         1626 / 1626
expected isolated-package/server skip                    1
```

The first staging wrapper returned a local PowerShell `NativeCommandError`
after the remote suite had printed `FULL_UNITTEST=PASS`; unittest progress was
written to stderr and was misclassified by the local capture layer. The same
non-destructive validation was immediately repeated with remote stderr merged
into stdout and exited zero. This was a logging/transport wrapper error, not a
test, package, or code failure.

The fresh package was transferred with direct `scp -r`; no archive was made
or extracted. Installation copied only the 1,299 manifest-declared files and
did not delete or alter any server run directory or raw evidence.

## 4. Accepted server run and integrity

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r51r4d3_runs/
  stage4_2r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_schedule_preflight_20260810_602c8a4_v1/
  stage4_2r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_schedule_preflight/
```

Primary and independent execution each authenticated the corrected final
R51R4D1 source and exact inherited R51R4 evidence. The stage contained eight
authenticated files totaling 1,136,316 bytes before the server evidence log
was added. It contained zero raw or snapshot files.

```text
source authentication                                  PASS
specifications constructed/reported                    250 / 250
eligible specifications                                250 / 250
context coverage                                        10 / 10
history-pair eligible-set equality                       5 / 5
every frozen criterion                                  250 / 250
primary/independent discrete agreement                     exact
primary/independent coverage agreement                     exact
primary/independent action-stream agreement                exact
maximum numerical difference               2.220446049250313e-16
action-stream digest               fa186ce6d9363ef6513f0bdd6d529d645570b0c05caeb335a49d75381c6e9339
new TSC/raw/plant/controller/model/optimization       0 / 0 / 0 / 0 / 0 / 0
```

## 5. Frozen geometry result

```text
maximum incremental normalized action                  0.2111111111111112
maximum current utilization                            0.3912
minimum second-transition cosine                       0.9999999999999999
maximum second-transition relative off-basis residual  0.09907590194856301
```

The maximum off-basis residual is below, but close to, the prospectively
frozen `0.10` cap. No cap was changed after construction.

The post-return componentwise-zero command diagnostic was `0/250`. As frozen
before D3 construction and inherited from the independently audited D1
reporting repair, this is not an eligibility predicate. Exact Card15 target,
exact stored-center physical current, fixed clock, return, event, action,
current, and post-return center gates all passed `250/250`. The exact step-17
center bridge zero increment separately passed `250/250`.

## 6. Artifact hashes

```text
specs/all_specs.json                 151c36f8f8f704eced670ce43cc33c6d60efe1ebcfe1df7a4a0e343ec58a8864
source_authentication.json           832f3b0cc89ce506569b403ca19e74018ece835fdff789c99d879befa7b37e79
offline_primary.json                 4b27a34b9463103347851c2536e7d005fbd289ba09a2208eac96eb0adb8de845
offline_construction_primary.json    8ed721f7d2d2dc4f83a150c92fc6388f8f4f3279466080f7814f81b9787e86e3
offline_independent.json             ee5df277fcd673513a1fe90bd483394d4f5bfba9b45258a2c30b2bcdea7e2abe
final_report.json                    38ab60f8978f60797fdc128c7d9d2de6da00f240a292413255a781ec6f24ee5c
stage_state.json                     ea5762971f69b8e44157fd21cdc438352e3a7774ae038d552c22cfe00b71ea8e
stage_manifest.json                  60b9fb04af84f05cbb81e981f9225996a1f016fbffe6562d0ce5230cadb82a20
final_server_evidence.json           012ba4817b38a59060faec299eba9494fe9ec282562b0d7b29d04e9b61ba8d51
```

Only six compact files were downloaded under
`artifacts/server_audits/r51r4d3_20260810_602c8a4_v1/`; all six reproduced
the server hashes. The detailed 250-row construction and independent outputs
remain on the server.

## 7. Next boundary

R51R4D3 authorizes only prospective freezing of R51R4D4's real response
sentinel. Before any new TSC, D4 must separately freeze its matrix, task
clock, safety stop, raw/restart/causality/Card15/current gates, response
question, independent audit, route, and no-learning boundary. It may not use
future response to alter an action path and it may not rerun any existing
R8/R51/R51R4 trajectory.

All R51R4-family trajectories are probes forbidden from expert data, BC,
DAgger, residual RL, or any model-selection leakage into learning. Gate A and
Gate B remain blocked.
