# Stage4.2R3c3T12 formal-gap route discriminator report

## 1. Result

Stage4.2R3c3T12 completed as a read-only retrospective audit of the exact
Stage4.2R3c3T11 evidence. It authenticated all 416 T11 raw `JSON.GZ` files in
place on the server and reproduced the frozen T11 formal and condition
results. T12 executed no Ray task, `gotsc`, TSC plant step, controller,
optimizer, or snapshot creation.

The result is:

```text
fixed condition-first response-basis route                     VETOED
T11 verdict changed                                                 no
T11 response bank or R3c4 feasibility model created                 no
full-size new identification campaign authorized                    no
real MPC / real closed loop tested by T12                            no
```

The decisive facts are:

```text
baseline formal PASS / condition PASS                              12
baseline formal PASS / condition FAIL                               4
baseline formal FAIL / condition PASS                              13
baseline formal FAIL / condition FAIL                               3

failed baselines repaired by any measured single probe           0/16
measured single-probe repairs in failed contexts                     0
best measured signed-margin gain                  0.0011652--0.0080656
best measured formal-gap coverage                    0.47%--11.46%
single-probe regressions around passing baselines                  1/192
```

Condition failure is neither necessary nor sufficient for formal failure,
and condition pass is not sufficient for formal control. Repairing the seven
T11 condition failures would directly overlap only three of the sixteen
authentic formal failures while spending effort on four cases whose baseline
already passes. None of the twelve real T11 signed probe corners repairs any
failed baseline.

This vetoes another condition-first fixed-basis campaign. It does not prove
global plant unreachability or rule out a state-conditioned, relinearizing,
finite-horizon MPC.

## 2. Exact code and package identity

```text
local branch
  codex/stage4_2r3c3t12-formal-gap-discriminator

frozen design commit
  595b81d

implemented and deployed package commit
  386c051

T11 source package commit
  40944f9
```

Load-bearing local hashes at execution were:

```text
config
  1bc7ad7b1878e1739888f906a967d80dc6e7b4fbdf0dece1d90b91bf121d15f3
audit implementation
  cbdf844d2b3eb0664d6f44358a30822cb1d4ed0e0c7682d39d2bd3118681a1cd
design document
  53f443b73790859ece50a55437dc09e039dd6df190c6bcb75da7d9e1200c8e43
focused test
  d9e28ea4a2be08c961da17c1e1311aa2452650b4b91089ba7de7c5836980e8fb
PACKAGE_MANIFEST.json
  a713aea29979ad65a2bc0baba3fd855f8d1248281481a5b7d5eafdebfffaace3
SHA256SUMS
  fc5a18d8478ae164571ae3be9d4a39110caf0c83ef26d0b0326049c5ebbc480c
```

The deployment package contained 252 declared files. It was copied directly
and uncompressed; no local archive operation was used.

## 3. Exact server paths

```text
validated staging package
  /home/yangshen0711/tsc_software/stage4_2r3c3t12_package_386c051

canonical project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

immutable T11 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t11_runs/
  stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9

immutable T11 source audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t11_audits/
  stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9

T12 compact output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t12_route_audits/
  stage4_2r3c3t12_formal_gap_route_discriminator_20260801_386c051

installed validation log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t12_installed_validation_386c051.log

T12 audit log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t12_formal_gap_route_discriminator_20260801_386c051.log
```

Only the compact T12 JSON files and the two small logs were downloaded. The
19,273,198-byte T11 raw inventory remains on the server.

## 4. Source authentication and inventory

Expected and actual source counts were:

```text
raw files                                                 416/416
unique experiment IDs                                    416/416
successful and completed                                 416/416
51-state trajectories                                    416/416
50-row causal controller traces                          416/416
forbidden-input contract clean                           416/416
raw-to-reported identity match                           416/416
contexts                                                   32/32
extended baselines                                         32/32
signed probes                                             384/384
new T12 plant rollouts                                        0/0
```

The exact T11 raw inventory digest was reproduced:

```text
f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3
```

The T11 independent audit, result, condition, manifest, config, state,
summary, verdict, raw inventory, matched-history, central-response, and
snapshot-audit hashes all matched the preregistered T12 source contract.
T12 copied or modified zero raw files.

## 5. Compact outputs and hashes

```text
stage4_2r3c3t12_audit_v1.json
  bytes   25,804
  sha256  3e5e8e4c52e5b7efb3e068146ceb012f3bb2dc2717c9b5f05107b51ed8fa2970

stage4_2r3c3t12_route_result_v1.json
  bytes   1,365
  sha256  9a334aadc45d118ebc8cb58acd6171876c2a9da9f5d2aadf3b46ae9ae1d0be25

stage4_2r3c3t12_manifest_v1.json
  bytes   663
  sha256  1efd48c7ce5be3cd3530fa8aa27c2478e661c9e8338b105fd73592515e7cec19

audit log
  sha256  f3b4fefa1564269f71328aa7c10d6c9b18cd4c62fcb62b839a327c195bbd3b7d

installed validation log
  sha256  36e5dff4d2e769c60a4a4a6afecf4644e4fd5b31797172d1ad51067e6694f9b9

provenance digest
  c071cb7ac88cb4fcd3b921568c1b481b57e2e7f29a58fdc02868ac1d5e020325
```

The downloaded copies are under:

```text
docs/codex/audits/
stage4_2r3c3t12_formal_gap_route_discriminator_20260801_386c051/
server_compact/
```

## 6. Failure structure and architecture implication

The sixteen baseline failures are structured:

```text
prefix 5                                                   12
prefix 9                                                    4
offset target RZ_p10_m10                                   12
nominal target                                              4
delay 2 / slew 0.9                                         12
delay 0 / slew 1.0                                          4
minus-first / plus-first histories                        8 / 8
```

All sixteen R3c1 failures have an unavoidable position violation at every
allowed formal endpoint; four prefix-5 normal-actuator offset-target cases
also have unavoidable final/post-window speed violations. The best T11
single-probe gains are too small by factors of roughly 9--213 when measured
against the existing signed gap. This is an observed-corner statement, not a
global authority bound.

The evidence therefore updates the route as follows:

1. Stop treating response-matrix conditioning as a proxy for formal task
   closure.
2. Stop expanding fixed episode-wide response bases before the controller
   architecture states exactly which time-local action authority it needs.
3. Preserve target-conditioned nominal transport. R3c2 proved that a
   zero-nominal terminal regulator is only local damping and loses the
   prefix-5 transport problem.
4. Separate the immutable formal task clock from the local model phase. A
   late-looking restart state must not silently shorten the available formal
   horizon.
5. Optimize a causal sequence through the actual delay queue, gain, slew,
   coil-current constraints, transport phase, braking phase, and hold phase;
   do not optimize coefficients of a fixed whole-episode probe schedule.
6. Make velocity/deceleration an explicit deadline and post-arrival
   constraint, not an incidental terminal penalty.
7. Reconstruct controller state causally: visible state, finite-difference
   velocity/history, integral/previous correction, applied coil currents,
   and the command queue. Pair/history labels, hidden wire currents, source
   future actions/results, and current-run future values remain forbidden.

Existing evidence is sufficient to veto another full condition-first
campaign, but it is not sufficient to certify a new prediction model. The
next stage is therefore architecture specification and offline evidence
mapping. A small real-TSC sentinel is allowed only after that stage identifies
a specific missing task-relevant response and freezes an explicit
stop/continue gate.

## 7. Required error classification

```text
runtime or environment error
  none

packaging, import, or deployment error
  none in the validated installed package

raw-data or snapshot corruption
  none detected in the authenticated T11 source evidence

statistics or reporting error
  none; T12 independently reproduced every frozen count and expectation

test not run
  no T12-required validation omitted

identification-design failure
  T11 remains failed at 25/32 unnormalized condition passes

route/design defect
  yes; condition-first fixed-basis expansion is misaligned with the formal gap

real plant restart conclusion from T12
  not tested; unchanged prior R1c/R2/R3c1/T11 evidence remains frozen

real closed-loop control conclusion from T12
  not tested; T12 ran no controller or plant

source closed-loop conclusion retained
  R3c1/T11 baselines remain genuine 16/32 controller failures, not runtime,
  restart, corruption, or reporting failures
```

## 8. Validation performed

Repository-side validation before deployment:

```text
focused T11 plus T12 tests                              14/14 PASS
complete tests with the repository Windows shim       624/624 PASS
Python compileall                                           PASS
all repository JSON parse                                  PASS
package hash verification                             252/252 PASS
empty-directory direct-copy package verification      252/252 PASS
empty-package complete tests                           624/624 PASS
empty-package compact-evidence test                         1 expected skip
import closure / scientific guards                         PASS
```

Real Bash was unavailable locally and was not claimed as locally tested.
Server staging and canonical validation used the existing server virtual
environment and included real Bash syntax, package checks, compile/JSON,
focused tests, and the complete Linux suite. Final canonical validation was:

```text
complete Linux tests                                   624/624 PASS
compact-evidence test                                        1 expected skip
```

After compact evidence download, all six focused T12 tests passed locally,
including exact compact hashes.

## 9. Commands and operations actually used

The workflow used repository-local Git/Python/PowerShell operations,
repository-local empty-package simulation, and direct `sftp`/`scp` transfer
without archives. Server commands performed the exact path preflight, Bash
syntax, package validation, complete unit tests, canonical installation, and
one guarded invocation of:

```text
STAGE4_2R3C3T12_PYTHON=<existing server venv python>
STAGE4_2R3C3T12_OUTPUT_DIR=<new exact T12 output>
bash run_stage4_2r3c3t12_offline.sh
```

Both the exact T12 output path and log path were required to be absent before
execution. The source T11 run and audit were opened read-only in place. No
server Git operation, network dependency, package installation, broad process
kill, archive operation, or cleanup of unrelated paths occurred.

## 10. Frozen facts, unvalidated scope, and next action

Frozen:

- Stage4.1R17 finite static grid remains 18/18.
- R1 means Stage4.2R1 authentic plant-state restart; R17 means the
  Stage4.1R17 finite controller source.
- R1c and R2 remain finite clean restart certifications.
- R3c1 remains 16/32 and R3c2 remains 12/32 real closed-loop development
  results.
- T11 remains a clean identification-design FAIL at 25/32 conditioning.
- T12 vetoes the condition-first fixed-basis route.
- The 250/270 ms arrival and 350/370 ms hold endpoints and all physical
  thresholds are unchanged.

Not validated:

- a new finite-horizon restart MPC;
- independent hidden-history robustness or an observer;
- unseen targets;
- continuous delay/gain/slew or plant/Jacobian mismatch;
- measurement noise;
- disturbance recovery;
- independent long hold;
- expert-dataset readiness.

The next action is a no-new-TSC architecture/evidence stage that freezes a
restart-integrated, target-conditioned, task-clock MPC interface and maps its
specific model/authority requirements to existing raw evidence. It must end
with either an implementable offline controller specification or one small,
separately preregistered sentinel design. It must not jump directly to a full
32-context campaign.

R3c4, BC, DAgger, and bounded residual RL remain unauthorized.
