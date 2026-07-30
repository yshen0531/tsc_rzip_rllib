# Stage4.2R3c1 final forensic report

Date: 2026-07-30 Asia/Shanghai

## 1. Executive conclusion

Stage4.2R3c1 completed its offline gate and ultimately produced 32 successful
authentic TSC restart controls. Independent server-side recomputation of all
final raw JSON.GZ gives:

```text
expected / final control raw                    32 / 32
environment success                             32 / 32
exact plant restart                             32 / 32
causal controller trace                         32 / 32
valid phase trace                               32 / 32
formal control pass                             16 / 32
both pair members pass                           8 / 16 groups
runtime or environment errors after resume            0
plant-restart failures                                0
controller-causality failures                         0
real formal closed-loop control failures              16
```

R3c1 therefore failed its frozen 32/32 development gate. Its final 16/32
result is real, not a verdict-only conclusion.

Three non-scientific incidents were separately repaired and audited:

1. The initial run completed 28 trajectories, while four phase-20 tasks
   raised `ValueError('terminal feedback requires at least two trajectory
   states')` at task step zero. The four failures and the complete 32-file
   pre-hotfix inventory were preserved before a semantics-preserving resume.
2. The first resume launcher lacked its executable bit after Windows-to-Linux
   direct transfer. It exited before TSC and changed no raw file.
3. The original postprocessor compared the preserved initial deployment
   fingerprint directly with the active runtime-hotfix package. A
   reporting-only patch authenticated the initial-to-runtime-to-audit package
   chain. It changed neither the controller nor raw results.

After those repairs, the exact 28 previously successful raw hashes were
unchanged and only the four preserved runtime-failure experiment IDs were
recomputed. All four then passed. The remaining 16 failures are therefore
controller-design/closed-loop failures.

The authenticated R17 visible-manifold selector did not improve any failed
R3c case and regressed four previously passing cases. R3c to R3c1 transitions
were:

```text
pass -> pass                                      16
fail -> fail                                      12
pass -> fail                                       4
fail -> pass                                       0
```

The four regressions are the prefix-9, offset-target, delay-2/slew-0.9
cases. R3c used phase 12 and passed them with margins about 0.047--0.052;
R3c1 selected phase 13 or 14 and failed with margins about
-0.078 to -0.082.

This disproves the R3c1 design hypothesis that static nearest R/Z/Ip phase
matching alone is a sufficient restart controller. Plant restart itself
remains exact. Hidden-history robustness remains inconclusive because all
16 pair groups had the same pass/fail outcome within each pair, but eight
groups failed both members under a common-mode controller failure.

## 2. Exact identities

Local branch and commits:

```text
branch
  codex/stage4_2r3c1-visible-manifold

implementation
  be3065b feat(stage4.2r3c1): add authenticated visible-manifold phase MPC

runtime hotfix
  35e725c fix(stage4.2r3c1): resume phase20 damping causally

resume-package audit
  0898b28 fix(stage4.2r3c1): audit compatible resume package chain

independent raw-forensic tool
  1e3772d chore(stage4.2r3c1): add server raw forensic audit
```

Experiment identity:

```text
stage
  Stage4.2R3c1

controller revision
  authenticated_visible_manifold_phase_mpc_v42r3c1

package revision
  r42r3c1_authenticated_visible_manifold_phase_mpc_v1

resolved config SHA-256
  cbfa7388d0ad4af45d20327617e529af73e656a10866777b6481f3286304b3eb
```

Package chain:

```text
initial deployment digest
  3ea8456d0cb5cc13ba0771e6b8d571aef62da9fe08f678c09d962969eeba9ede

initial controller source SHA-256
  961f075c04f3c9f7eea812c12fb4a8fdc21971c31298108184201f3ed41c80b9

active runtime-hotfix package digest
  c78beb6649543512d3d54649c3001b1c870256929470f09fccaf082b7e087a99

active runtime controller source SHA-256
  4ee7eda0e06d7c771322f33bec9f0bb31c5593937821b494d81fa6c615eaa76d

reporting/audit package digest
  61f31875d9ecbef70ecf46b6acbf1600cd877c66345db8cd7ce07bbb6e9f038a

reporting script SHA-256
  4111b860229d3cbc5a03bff909c3d2a36bae143c91e75305922c557f56cfd1ea
```

The reporting package changed only `PACKAGE_MANIFEST.json`, `SHA256SUMS`,
and the postprocessor. The controller source remained exactly the active
runtime-hotfix source.

Authenticated sources:

```text
R3b snapshot source
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526

R3b source fingerprint digest
  5c5b6707908cf8777889ef2b00aeef93e7f516d8ac6915687efe7777fa280cee

R3c result source
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c_runs/
  stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807

R3c source fingerprint digest
  dcf614361bec4bd8d8cdede3c034c728563c84ca298523b9f641a90698dc95f4

visible reference-manifold digest
  538e081d0212174c00ac921b2fd1ce9cf7df4b69e6810892fa9aaf7202e47f9a
```

## 3. Remote run, logs, and evidence

```text
remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c1_runs/
  stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_143218

offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_143218.log

initial real-TSC log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_144049.log

permission-error resume log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_151300.log

valid four-task resume log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_151450.log

server audit directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c1_audits/
  stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_143218

pre-hotfix preserved evidence
  <remote run>/stage4_2r3c1_runtime_bug_evidence/
  pre_hotfix_20260730_145053
```

The first real launch used fixed Ray capacity 128 with 32 actors. The valid
resume used the same capacity with exactly four pending tasks and four
actors.

## 4. Validation and safe resume

Before the initial real TSC run:

```text
Python compile and repository JSON parse             PASS
focused R3c1 tests                          13 / 13 PASS
complete local unittest discovery          499 / 499 PASS
empty direct-copy package simulation                 PASS
server staging and installed verification            PASS
server complete unittest discovery          499 / 499 PASS
offline source/action/causality gate                  PASS
offline real TSC executions                              0
```

The offline audit reproduced four original-start source controllers exactly,
selected phase zero there, tested all 32 development selections, and proved
that source actions, source coil/wire currents, current-run future values,
and hidden wire currents were not controller inputs.

Runtime-hotfix validation:

```text
focused tests                                16 / 16 PASS
complete local tests                        502 / 502 PASS
repository JSON                              35 / 35 parse
package checksums                           143 / 143 verified
import closure                               47 modules
empty direct-copy complete tests            502 / 502 PASS
server staging complete tests               502 / 502 PASS
server installed complete tests             502 / 502 PASS
offline resume pending/complete                 4 / 28 exact
offline resume real TSC executions                    0
```

The hotfix only defines the unavailable first finite-difference velocity as
zero when a fresh task enters damping at step zero, matching the already
frozen causal convention in the main-control measurement path. At the second
current-run sample and later it delegates to the existing terminal
measurement implementation.

The valid resume was authorized because experiment IDs, task matrix, source
fingerprints, action semantics for the 28 successful tasks, controller
revision, package revision, and formal gate were unchanged. The exact known
runtime failure alone was pending.

Reporting-hotfix validation:

```text
complete local tests                        503 / 503 PASS
repository JSON                              36 / 36 parse
package checksums                           144 / 144 verified
server staging complete tests               503 / 503 PASS
server installed complete tests             503 / 503 PASS
new TSC executions                                    0
raw changes                                            0
```

## 5. Raw and manifest integrity

Final run inventory:

```text
files                                                   166
bytes                                             3,409,736
digest
  5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f
```

Independent raw-control forensics:

```text
tool
  docs/codex/audit_tools/stage4_2r3c1_raw_control_forensics.py

result SHA-256
  29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd

server audit SHA-256
  0d81cbe3e0d9b67d72cf093143edd8a825a3b60ea5e3c449cf29de7cf0cc7712

raw expected / parsed                              32 / 32
raw byte inventory digest
  3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e
manifest/package/source compatibility                 PASS
```

Pre-hotfix evidence:

```text
manifest SHA-256
  30303cc7a907a4ff2cd4c7680f3164990db39ac0495a6b978b9f4cac38a69cc9

control raw                                            32
successful trajectories                               28
preserved runtime failures                              4
each preserved failure raw hash/size match             yes
```

After the valid resume, all 32 raw files were parseable and successful. The
28 prior-success hashes were unchanged. Exactly these four preserved failure
IDs changed:

```text
s42r3c1_1158eec2af85a1687c50
s42r3c1_4b8dc85c34b4b10adc6c
s42r3c1_6ec081eb0f5408a0e934
s42r3c1_9f56bf3403ed25612e1f
```

Each now contains a complete weak-actuator trajectory with 38 states and 37
controller traces.

Large final raw JSON.GZ and snapshot trees were not downloaded. They remain
on the server and were opened there by the independent Python audit. The
local compact evidence is:

```text
docs/codex/audits/stage4_2r3c1_result_20260730_143218/

files excluding local inventory                         53
bytes                                            1,317,002
local compact inventory digest
  2906317fb9089579eb3fce881d86f947c433135eac086d6a9a8afdec0ee846a3
```

## 6. Formal closed-loop result

The immutable contract remained:

```text
slew 1.0: arrival <= 250 ms; hold through 350 ms
slew 0.9: arrival <= 270 ms; hold through 370 ms
R/Z tolerance: 30 mm
speed threshold: 0.1 m/s
Ip thresholds and arrival streak: frozen baseline values
```

No formal clock was shifted. Recomputed result:

```text
formal pass                                           16 / 32
formal fail                                           16 / 32
minimum signed margin                    -0.36178536666666794
unavoidable position violations                       16
unavoidable final-speed violations                     4
unavoidable post-speed violations                      4
solver failures                                         0
saturated action elements                               0
```

Grouped outcome:

| Group | Pass |
|---|---:|
| nominal target | 12/16 |
| offset target `RZ_p10_m10` | 4/16 |
| delay 0 / slew 1.0 | 12/16 |
| delay 2 / slew 0.9 | 4/16 |
| prefix 5 | 4/16 |
| prefix 9 | 12/16 |
| phase 11 | 0/4 |
| phase 12 | 10/18 |
| phase 13 | 2/4 |
| phase 14 | 0/2 |
| phase 20 | 4/4 |

All 16 failures have an unavoidable position violation under every allowed
formal endpoint. Four prefix-5, delay-0, offset-target cases also have
unavoidable final/post-window speed violations.

The failure shapes are physical and structured:

- Prefix-5 weak nominal cases start inside the R/Z box, leave it around task
  step 10, and finish near -30.1 mm R error.
- Prefix-5 weak offset cases never enter the box and finish near -38.7 mm R
  error.
- Prefix-5 normal offset cases enter late and then leave, ending near
  +33.5 mm Z error with terminal speed near 0.1 m/s.
- Prefix-9 weak offset cases selected phase 13 or 14 and end near -31.1 mm R
  error.

These are not corrupt trajectories, failed solvers, bad endpoint selection,
or an over-restrictive summary calculation.

## 7. Design diagnosis

R3c1 used a static nearest point on a target/actuator-conditioned R17
R/Z/Ip manifold. Selected phases were:

```text
phase 11                                                4
phase 12                                               18
phase 13                                                4
phase 14                                                2
phase 20                                                4
```

The closest R17 R/Z/Ip phases under the independent forensic metric ranged
from 12 to 20. R3c1's first actions were close to its selected source phase
and far from source phase zero:

```text
first-action max difference from phase zero    1.1114--1.8940
first-action max difference from selected      0.0186--0.1226
```

Thus R3c1 did not repeat R3b's phase-zero reset. The failed hypothesis is
more specific: a single static R/Z/Ip phase label does not reconstruct the
dynamic controller state needed after a restart. The fresh controller still
lacks initial velocity/history, integral, previous correction, and a
measured pending-action queue. A visible point can lie near an R17 sample
without sharing its direction of motion or feedback state.

The phase-20 cases are informative but not a validation of a universal
repair: they entered target-error damping immediately and all four passed.
That supports prospectively testing a causal target-state regulator from task
step zero, while retaining visible phase only for frozen model lookup and
delay-queue initialization. It does not justify post-hoc phase overrides or
claim that hidden state has been identified.

The no-TSC controller diagnostic for that prospective architecture is:

```text
result
  docs/codex/audits/stage4_2r3c1_result_20260730_143218/audit/
  stage4_2r3c1_restart_regulation_diagnostic.json

SHA-256
  9a278b5e97416ae2d98d05b4cff7ad2328ddd0a1ec8f3d14ded0421b184c124d

development first actions finite / solver success       32 / 32
step-zero velocity initialized causally to zero          32 / 32
hidden-wire variant exact                                32 / 32
current-run future/source action/source wire use               0
original-start phase zero and exact action                 4 / 4
plant advances / real TSC                                      0
```

The prospective first action differs from the observed R3c1 action by
0--0.9414 in normalized action coordinates. It is therefore a new controller
semantics and must use a new experiment identity; it is not eligible for
another R3c1 resume. The diagnostic establishes implementability and
causality only, not a counterfactual closed-loop PASS.

## 8. Hidden-history interpretation

For 16 matched-visible pair-control groups:

```text
both pass                                                8
both fail                                                8
one pass / one fail                                      0
```

Paired trajectories and actions were not identical; maximum paired action
difference reached about 0.578 and wire-current differences remained
measurable. Nevertheless, identical pass/fail classifications do not prove
robustness. The eight both-fail groups mask any history sensitivity behind a
common-mode controller failure.

Therefore:

```text
authentic different hidden histories present          yes
plant restart exact                                    yes
hidden-history robustness validated                     no
observer/history identification validated               no
```

## 9. Required error classification

```text
runtime / environment error
  initial four-task first-sample exception; fixed and safely resumed
  final 32-file run has zero runtime/environment errors

packaging / import / deployment error
  one missing executable bit stopped a resume before TSC
  corrected by explicit permission validation; no raw changed

raw-data or snapshot corruption
  none detected

statistics / reporting error
  original postprocessor did not understand the authenticated runtime-hotfix
  package chain; reporting-only fix recomputed raw integrity as PASS

test not run
  no required R3c1 validation omitted

plant-restart fidelity failure
  none; exact 32/32

controller-causality failure
  none; causal trace 32/32 and forbidden-input counts all zero

controller-design failure
  yes; static visible-manifold phase selection is insufficient

real closed-loop control failure
  yes; 16/32 violate the immutable formal contract
```

## 10. What remains frozen and unvalidated

Still frozen:

- Stage4.1R17 finite static grid: 18/18.
- Stage4.2R1c authentic plant restart: 18/18.
- Stage4.2R2 causal exact controller-state restart: 18/18.
- R3b authentic snapshot bank and four selected development pairs.
- R3c failed development result: 20/32.
- R3c1 failed development result: 16/32.
- Formal timing and all physical thresholds.

Not validated:

- development closure on different initial states;
- independent hidden-history robustness;
- a hidden-state observer;
- unseen targets;
- continuous delay, gain, or slew;
- plant/Jacobian/model error;
- measurement noise;
- disturbance recovery;
- independent long hold;
- reliable MPC expert-dataset readiness.

BC, DAgger, and bounded residual RL remain blocked.

## 11. Next action

Do not proceed to independent R3d because the development controller failed.
Do not tune the phase metric or assign per-group phases from observed
pass/fail outcomes.

The next development revision should test one prospective architectural
change supported by the raw failure shapes: start causal target-state MPC
regulation at task step zero. It may retain the authenticated visible phase
only for frozen response-model phase and delay-queue initialization. The
feedback measurement must use current target error, initialize unavailable
step-zero velocity to zero, and use only current-run finite differences
thereafter. Formal task time remains zero, and the 32-case development matrix
and 32/32 acceptance gate remain unchanged.

Before a new TSC campaign, an offline/server-side diagnostic must verify the
existing raw phase/transition evidence and a no-TSC first-action computation
for all 32 cases. The new controller and experiment require a new identity,
complete tests, package validation, and a preregistered design. If the new
development revision passes, independent prospective histories remain
mandatory before advancing to targets or continuous uncertainty.

## 12. Commands and operations actually used

Local/repository operations included:

```text
git rev-parse --show-toplevel
git status --short
git branch --show-current
git log
python -m compileall
python -m unittest
JSON parsing over repository JSON files
package checksum and import-closure verification
empty-directory direct-copy deployment simulation in .codex_tmp
SHA-256 verification of every compact and preserved failure artifact
```

Server operations used the user-authorized fixed endpoint and canonical
project paths:

```text
non-destructive HOME/PWD/project/virtualenv preflight
direct scp transfer without archives
bash -n and executable-bit checks on declared scripts
package checksum/import/compile/full-test verification
offline gate and offline resume-compatibility audit
initial real TSC run with fixed Ray capacity 128
same-identity four-task semantics-preserving resume
server-side postprocessing of all final raw JSON.GZ
independent raw-control forensic Python audit in place
compact-only result/log transfer
```

No local archive operation occurred. No final large raw JSON.GZ or snapshot
tree was downloaded. No server Git, network access, package installation,
root action, broad process kill, or simulation-virtualenv modification was
performed.
