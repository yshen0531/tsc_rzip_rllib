# Stage4.2R3c final forensic report

Date: 2026-07-30 Asia/Shanghai

## 1. Executive conclusion

Stage4.2R3c completed its offline gate and all 32 authentic TSC restart
controls. Independent server-side recomputation of every raw JSON.GZ gives:

```text
expected / actual control raw                    32 / 32
environment success                             32 / 32
exact plant restart                             32 / 32
causal controller trace                         32 / 32
valid phase trace                               32 / 32
formal control pass                             20 / 32
both pair members pass                          10 / 16 groups
runtime or environment errors                         0
plant-restart failures                                0
controller-causality failures                         0
formal closed-loop control failures                  12
```

R3c therefore failed its frozen 32/32 development acceptance gate. This is
not a runtime, packaging, raw-data, snapshot, plant-restart, or reporting
failure. It is a genuine finite-development-set closed-loop control failure.

The result is highly structured:

```text
common prefix 9                                 16 / 16 PASS
common prefix 5                                  4 / 16 PASS
```

Visible-state phase alignment repaired the dominant R3b phase-zero reset
error enough to recover all prefix-9 cases, but the R3c phase estimator used
the ideal target-conditioned nominal trajectory rather than the authenticated
actual R17 closed-loop visible trajectory. It selected phases 11--13 while
the restart states were nearest to actual R17 visible phases 12--20. The
underestimate was most severe for the delayed weak-slew cases.

R3c does not validate hidden-history robustness. Ten pair groups had both
members pass, but six groups had both members fail, so those six groups mask
history sensitivity. There was no pass/fail disagreement within a pair.

The next action is a new development revision, Stage4.2R3c1. It will match
the current visible R/Z/Ip only against an authenticated, frozen R17 actual
closed-loop visible-state reference manifold for the same target and
actuator case. It will not receive R17 actions, current-run future values,
snapshot labels, or hidden wire currents. The 32-case matrix and formal
acceptance gate remain unchanged. Even a Stage4.2R3c1 PASS will still require
independent R3d histories before advancement.

## 2. Exact identities

Local source checkpoint:

```text
branch
  codex/stage4_2r3c-phase-aligned-mpc

implementation commit
  e8856f8 feat(stage4.2r3c): add visible-state phase-aligned MPC

authenticated-source-contract hotfix
  a5513e9 fix(stage4.2r3c): honor authenticated R3b snapshot contract
```

The hotfix changed only validation of the existing authenticated R3b snapshot
row: R3b encodes the complete snapshot validation contract in `success`.
The failed pre-hotfix offline attempt stopped before manifest creation and
before any real TSC execution. It did not alter controller or experiment
semantics.

Final deployed identity:

```text
stage
  Stage4.2R3c

controller revision
  visible_state_phase_aligned_mpc_v42r3c

package revision
  r42r3c_visible_state_phase_aligned_mpc_v1

PACKAGE_MANIFEST.json SHA-256
  06eb17e432f7cdfcabee34fef88a06df149b7161afadad27dc3a3c5a30c761ae

SHA256SUMS SHA-256
  0f3720a867bead753981fcce6c4b0dc273174332e9117e79e172c56361fa43e5

main diagnostic source SHA-256
  aedee8e2d3e98f21aae0cdc6b7c5d44241a48f7a62dcdf52f5716fbfc096bae2

resolved config SHA-256
  8ff400b34e440f0323c264a004722263ff47fdc2fd772850d5d26d8b980bbe34

deployed package fingerprint digest
  0d99b9e3f300575415e8e9d31953d329abcd12a79a78141687f3f4a940e99dc0
```

Authenticated R3b source:

```text
source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526

R3b full run inventory digest
  301a3ad2be01c83209d8e260c1a8c80f090d01afafb9c173f63cf9219caac8fc

R3c source fingerprint digest
  5c5b6707908cf8777889ef2b00aeef93e7f516d8ac6915687efe7777fa280cee

selected snapshot-source digest
  dc1fc09ff5614a86e0d4645b3e448043ce6332061c615e0200d8b174f5a9d113
```

Final run and logs:

```text
remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c_runs/
  stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807

offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807.log

real-TSC resume log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132936.log

server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c_audits/
  stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807

compact local evidence
  docs/codex/audits/stage4_2r3c_result_20260730_132807/

compact evidence inventory
  25 files / 774,954 bytes

compact evidence inventory digest
  b71d57754e8fb631eb5d85859bc63b0ed9a93ff2b50e256204f0baabcc497146
```

## 3. Validation, deployment, and execution

Final local validation after the hotfix:

```text
Python compileall                                  PASS
all repository JSON parse                         PASS
focused R3c tests                         13 / 13 PASS
complete unittest discovery             486 / 486 PASS
empty direct-copy package simulation              PASS
empty-package file hashes                   136 verified
empty-package complete tests             486 / 486 PASS
local archive operations                              0
```

Final server validation:

```text
canonical path and virtualenv preflight            PASS
declared shell scripts bash -n                     PASS
package checksum verification                      PASS
Python compile and import closure                  PASS
scientific guardrails                              PASS
complete unittest discovery             486 / 486 PASS
```

The first staging validation at commit `e8856f8` exposed a CRLF
`SHA256SUMS`; the package was not installed or run. The file was normalized
to LF and all validation was repeated.

The first installed offline attempt then exposed the R3b snapshot-row field
assumption described above:

```text
failed run locator
  .../stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132324

failure point
  prepare -> recompute selected pairs

manifest created
  no

raw control created
  no

real TSC executed
  no
```

After `a5513e9`, validation was repeated. The final offline gate passed:

```text
R17 source cases                                    4 / 4
original-start phase zero                           4 / 4
exact original action reproduction                  4 / 4
maximum source-action absolute difference             0.0
hidden-wire-invariant first action                  4 / 4
valid source phase trace                            4 / 4
development phase selections                      32 / 32
selected phase values                           11, 12, 13
future action reads                                      0
future measurement use                                  0
hidden wire use                                         0
real TSC executed in offline phase                       0
```

The same prepared run identity was then resumed safely. All 32 planned real
TSC tasks completed.

## 4. Raw and manifest integrity

All large raw JSON.GZ and snapshot payloads remain on the server. Only compact
results, logs, manifests, fingerprints, inventories, and server-side
forensics were downloaded.

Server run inventory:

```text
files                                                   143
bytes                                             2,963,470
digest
  278395b364bb355c73b5f6de7461478b4bb239584a3f6bf9bf048aad12be9d13
```

Independent raw-control forensics:

```text
tool
  docs/codex/audit_tools/stage4_2r3c_raw_control_forensics.py

result
  docs/codex/audits/stage4_2r3c_result_20260730_132807/server_audit/
  stage4_2r3c_raw_control_forensics.json

result SHA-256
  395427285a5bad0de9611629df0a13ade037ddd4f0e30e993e475a56c3dbafaa

raw expected / parsed                              32 / 32
experiment-ID set exact                                yes
control specs exact                                    yes
manifest compatibility                                 yes
raw and manifest integrity                             PASS
```

The independent tool opened and recomputed all 32 raw JSON.GZ files in place
on the server. It did not rely on the top-level verdict for its formal result.

## 5. Formal closed-loop result

The immutable timing contract remained:

```text
slew 1.0: arrival <= 250 ms; hold through 350 ms
slew 0.9: arrival <= 270 ms; hold through 370 ms
R/Z tolerance: 30 mm
speed threshold: 0.1 m/s
Ip threshold and arrival streak: frozen baseline values
```

Recomputed outcome:

```text
formal pass                                           20 / 32
formal fail                                           12 / 32
minimum signed margin range             -0.2485163 to 0.2344120
mean minimum signed margin                      -0.0144181
position violation                                    12
post-window speed violation                            4
final-speed violation                                  4
Ip violations                                           0
solver failures                                         0
saturated action elements                     4 / 16,128
maximum current utilization range          0.38065--0.39040
```

The 12 failed trajectories have unavoidable violations under the frozen
endpoint search; they are not merely bad endpoint selection in the summary.

Grouped results:

| Restart group | Selected phase | Nearest actual R17 phase | Formal |
|---|---:|---:|---:|
| prefix 5, nominal, delay 0 / slew 1.0 | 12 | 13 | 4/4 |
| prefix 5, nominal, delay 2 / slew 0.9 | 12 | 18--19 | 0/4 |
| prefix 5, offset, delay 0 / slew 1.0 | 11 | 12 | 0/4 |
| prefix 5, offset, delay 2 / slew 0.9 | 11 | 14 | 0/4 |
| prefix 9, nominal, delay 0 / slew 1.0 | 13 | 14 | 4/4 |
| prefix 9, nominal, delay 2 / slew 0.9 | 13 | 19--20 | 4/4 |
| prefix 9, offset, delay 0 / slew 1.0 | 12 | 13 | 4/4 |
| prefix 9, offset, delay 2 / slew 0.9 | 12 | 16 | 4/4 |

The prefix-5 nominal normal-actuator group passed narrowly, with minimum
formal margins from about 0.00423 to 0.00532.

The prefix-5 nominal weak-actuator group failed position hold. Its initial
nominal state was inside the 30 mm box, then left at task step 10 or 11.
Terminal R error was about 30.1--30.3 mm and sustained box error reached
about 32.1 mm.

The prefix-5 offset normal-actuator group entered the box, but did not hold
position and speed. Terminal Z error was about 33.5 mm; terminal speed was
about 0.101--0.104 m/s and late RMS speed about 0.115--0.118 m/s.

The prefix-5 offset weak-actuator group never entered the 30 mm box and ended
with about 35.6--35.7 mm R error. Its speed metrics passed; position did not.

Ip had large positive margins in every case:

```text
terminal absolute Ip error                  159--209 A
hold RMS Ip error                           145--265 A
sustained maximum Ip error                  192--438 A
```

## 6. Phase-alignment diagnosis

R3c selected its phase by matching current R/Z/Ip to the ideal target-
conditioned nominal sequence. The raw trajectories independently show:

```text
selected phase count
  phase 11                                                8
  phase 12                                               16
  phase 13                                                8

nearest authenticated actual R17 R/Z/Ip phases
  12, 13, 14, 16, 18, 19, 20

first action difference from phase-zero action
  1.1602--2.0000

first action difference from selected-phase action
  0.0377--0.1226
```

This proves two distinct points:

1. R3c corrected the large R3b common-mode phase-zero mismatch. Its first
   action was far closer to the selected-phase controller action, and every
   prefix-9 case passed.
2. The ideal nominal trajectory is not an accurate enough phase manifold for
   the actual R17 closed loop, particularly under delay 2 / slew 0.9. A
   selected phase of 12 corresponded to an actual visible phase as late as
   19, and phase 13 corresponded to 19--20.

The next revision is therefore a phase-estimator design change, not a
summary correction. R3c must remain immutable and failed.

## 7. Hidden-history interpretation

For the 16 matched-visible pair-control groups:

```text
both pass                                               10
both fail                                                6
one pass / one fail                                      0
maximum paired action difference              0.0010--0.0195
maximum paired R difference                  0.381--0.465 mm
maximum paired Z difference                  0.348--0.674 mm
maximum paired wire-current difference           0.334--0.623 A
formal-margin absolute difference            0.00002--0.02146
```

The distinct hidden vessel/eddy-current histories caused measurable
trajectory and action differences, despite matched visible restart state.
However, no pair changed pass/fail outcome. The six both-fail groups are
common-mode control failures and make the hidden-history assessment
inconclusive there.

It would be scientifically invalid to report zero history-identification
failures as observer success: R3c has no hidden-state observer and did not
close the full development gate.

## 8. Required error classification

```text
runtime / environment error
  none in the final run

packaging / import / deployment error
  none in the final deployed run
  two pre-run validation defects were fixed and fully revalidated

raw-data or snapshot corruption
  none detected

statistics / reporting error
  none affecting the independently recomputed 20/32 result

test not run
  no required R3c validation omitted

plant-restart fidelity failure
  none; 32/32 exact

controller causality failure
  none; 32/32 traces causal, no future/hidden-wire input

controller-design failure
  yes; ideal-nominal phase matching is insufficient on prefix-5 states

real closed-loop control failure
  yes; 12/32 violate the immutable formal contract
```

## 9. What is frozen and what remains unvalidated

Still frozen:

- Stage4.1R17 finite static grid: 18/18.
- Stage4.2R1c authentic plant restart: 18/18.
- Stage4.2R2 causal controller-state restart: 18/18.
- R3b authentic snapshot bank and four selected development pairs.
- R3c raw evidence and failed 20/32 result.
- Formal timing and all physical thresholds.

Not validated:

- R3c development-set closure;
- independent hidden-history or different-initial-state robustness;
- a hidden-state observer;
- unseen targets;
- continuous delay, gain, or slew;
- plant/Jacobian/model error;
- measurement noise;
- disturbance recovery;
- independent long hold;
- MPC expert-dataset readiness.

BC, DAgger, and bounded residual RL remain prohibited.

## 10. Next action

Create Stage4.2R3c1 as a new controller and experiment identity. Its only
design change is the causal phase reference:

- freeze the actual R/Z/Ip samples from the exact authenticated R17 source
  control trajectories for each of the four target/actuator cases;
- expose that read-only visible calibration table, never source actions, to
  the fresh controller;
- select phase using only the current task's visible R/Z/Ip;
- retain task/formal time zero, fresh controller state, phase-aligned model
  and queue semantics, and the exact R3c 32-case development matrix;
- require the same 32/32 formal acceptance.

This is still same-digital-twin controller development based on inspected R3c
evidence. It is not independent confirmation. If it passes, R3d with new
prospective histories remains mandatory.

## 11. Commands and operations actually used

Local/repository operations included:

```text
git rev-parse --show-toplevel
git status --short
git branch --show-current
git log
python -m compileall
python -m unittest discover -s tests -v
focused unittest discovery for Stage4.2R3c
JSON parsing over repository JSON files
package hash verification
empty-directory direct-copy deployment simulation inside .codex_tmp
```

Server operations used only the authorized SSH endpoint and canonical paths:

```text
non-destructive HOME/PWD/project/virtualenv preflight
direct scp/sftp transfer without archives
bash -n on declared scripts
run_stage4_2r3c_verify_package.sh
run_stage4_2r3c_visible_state_phase_aligned_mpc_nohup.sh --offline
same-run --resume for real TSC control
run_stage4_2r3c_server_postprocess.sh
stage4_2r3c_raw_control_forensics.py on all raw JSON.GZ in place
compact-only result/log transfer
```

No local compression or extraction occurred. No large raw JSON.GZ or snapshot
tree was downloaded. No server Git, network access, package installation,
root action, broad process kill, or modification of the simulation virtual
environment occurred.
