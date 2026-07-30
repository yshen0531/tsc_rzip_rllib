# Stage4.2R3c2 final forensic report

Date: 2026-07-30 Asia/Shanghai

## 1. Result

Stage4.2R3c2 is a completed and permanently failed controller-development
result:

```text
expected / final raw controls                         32 / 32
environment success                                  32 / 32
fresh controller / fresh TSC                         32 / 32
exact visible and full-wire plant restart            32 / 32
causal and valid controller trace                    32 / 32
complete restart-regulation trace                  1152 / 1152
formal contract pass                                 12 / 32
real closed-loop formal failures                     20
```

The conclusion was recomputed from all 32 server-side raw JSON.GZ files. It
does not rely on the saved verdict.

The failed hypothesis was:

```text
for a nonzero visible restart phase, discard the R17 nominal transport
trajectory and regulate directly around the terminal target from task step 0
```

This produced a valid causal regulator, but not a reliable finite-horizon
transport controller. It repaired none of R3c1's 16 failures and regressed
four R3c1 passes:

```text
R3c1 -> R3c2
pass -> pass    12
fail -> fail    16
pass -> fail     4
fail -> pass     0
```

R3c2 must not be resumed or relabelled. A controller that restores
target-conditioned nominal transport and an explicit formal-deadline
velocity objective requires a new controller/package/experiment identity.

## 2. Exact identity

Local branch and implementation checkpoint:

```text
branch
  codex/stage4_2r3c2-restart-regulation

implementation commit
  c4b9143 feat(stage4.2r3c2): add restart target-state regulation MPC
```

Runtime identity:

```text
stage
  Stage4.2R3c2

controller revision
  restart_target_state_regulation_mpc_v42r3c2

package revision
  r42r3c2_restart_target_state_regulation_mpc_v1

deployed and audit package digest
  b35ef6df933d3e268705584834b1ffff5b7b6172fb882d82f4c338b75e06f1cd

controller source SHA-256
  0e5c487276d13ed72500cc9a8d904499092a236ba232c5b3046142d49454534e

PACKAGE_MANIFEST.json SHA-256
  90245028eb145335290ff50f611eb28775eeb253b43c7b11d15b7ea4bada29ba

SHA256SUMS SHA-256
  c246d0bd3bc6364d861030b46c82ea99a39b58f3cf819720de6babd45d1cde41
```

The runtime and postprocessing package digests are identical. There was no
runtime-package drift and no semantics-changing resume.

Remote paths:

```text
validated staging
  /home/yangshen0711/tsc_software/stage4_2r3c2_c4b9143

canonical project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c2_runs/
  stage4_2r3c2_restart_target_state_regulation_mpc_20260730_164616

runtime log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c2_restart_target_state_regulation_mpc_20260730_164717.log

server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c2_audits/
  stage4_2r3c2_restart_target_state_regulation_mpc_20260730_164616
```

## 3. Validation and execution

Local/repository validation completed before deployment:

```text
focused Stage4.2R3c2 tests                         13 / 13
complete repository tests                        516 / 516
Python compile                                      PASS
all repository JSON parse                          PASS
import closure                                      PASS
package manifest and checksums                      PASS
source fingerprint and resume compatibility         PASS
empty-directory direct-copy simulation             516 / 516
packaged inventory files                            150
undeclared source-tree dependency                      0
```

The tests used the repository environment. A bare local Python invocation
initially lacked project dependencies such as `gymnasium` and `resource`;
this was a local interpreter-selection issue, not a package or controller
failure. Re-running through the repository environment and the same
empty-directory package passed.

Server validation completed in both the staging and canonical trees:

```text
exact HOME/PWD/project/virtualenv preflight           PASS
bash -n for declared shell scripts                    PASS
executable-bit checks                                 PASS
package and checksum verification                     PASS
Python import and compile in existing venv             PASS
complete repository tests in staging                516 / 516
complete repository tests after install             516 / 516
Git/network/package installation used                    no
```

One deployment command incident occurred before any R3c2 TSC run. The first
canonical install command removed only the explicitly named package code
directories, then stopped when Windows-side quoting caused a remote
`find -name "*.sh"` expression to be expanded incorrectly. No run, raw,
snapshot, audit, or log tree was touched. The exact target was checked, and
the canonical code was immediately restored from the already validated
staging tree using direct copy. Full canonical package verification and all
516 tests then passed. This is classified as a recovered deployment-command
error, not a runtime, data, or scientific result.

The mandatory no-TSC gate completed before real execution:

```text
original-source phase-zero/full-action exact           4 / 4
development nonzero restart regulator                 32 / 32
finite successful first-action solves                 32 / 32
zero-velocity causal bootstrap                        32 / 32
hidden-wire-invariant first action                    32 / 32
diagnostic scalar exact                               32 / 32
forbidden controller inputs                                0
control raw created                                        0
real TSC execution                                         0
```

The same new run identity was then continued into exactly 32 real TSC tasks
with a fixed Ray capacity of 128. All 32 finished successfully; no task was
rerun.

## 4. Inventory and integrity

Final run inventory:

```text
files                                                   147
bytes                                             3,287,591
digest
  2119d2edad615dbb9594ad4332b758a9cf7ffc2e62b988650c41297aace8cff2
```

Raw control inventory:

```text
raw JSON.GZ files                                        32
bytes                                             1,070,893
digest
  b01a07c9dc136677f323d292d0f9388904cc39663514bf4025f4fa4fed767653
parse failures                                             0
experiment-ID mismatch                                     0
manifest/package/source incompatibility                     0
```

Independent raw forensic output:

```text
tool
  docs/codex/audit_tools/stage4_2r3c2_raw_control_forensics.py

tool SHA-256
  e6a4099b5593bcda9f4816a16c8a4a9baa923e9bb7a73f838aa7603f4657809f

result SHA-256
  644da85280e03015732bb63deb1205bf5fcafeabc53b0f8a9e606565a27efbb2
```

The independent tool was transferred only under `docs/codex/audit_tools`
after the unchanged runtime package had finished. It was not an imported
runtime source and did not alter the deployed package fingerprint.

Large raw JSON.GZ and snapshot trees remain on the server. Only compact
postprocessed evidence was downloaded:

```text
local compact root
  docs/codex/audits/stage4_2r3c2_result_20260730_164616/

files excluding local inventory                         12
bytes                                              903,923
local compact inventory digest
  35ac2b2731047a7e2d5e67e63d28b9eb108b649c31cb712af012a20fd3a2f0b1
```

Every downloaded compact file matched its server-side SHA-256. Important
individual hashes include:

```text
server audit
  87461800e5fd9ea6f228d49e36269eb80ffbb537720fcf804c69812ed2ddf7cf

raw forensics
  644da85280e03015732bb63deb1205bf5fcafeabc53b0f8a9e606565a27efbb2

control specs
  d68ccbee7d5cf4f8df9473338ed705651f9b451da494ef8c0cc3ed23631e32d0

results
  a2d1cc175c00d810a2b053b135b00b41a6bc331f089644d074502b3ba2491fd9

runtime log
  be08f4a68966528da3d35f90d77b4fb013e4d439b28e3c6b4e052a62c91d349e
```

## 5. Formal closed-loop result

The immutable timing contract was unchanged:

```text
slew 1.0: arrival <= 250 ms; hold through 350 ms
slew 0.9: arrival <= 270 ms; hold through 370 ms
R/Z tolerance: 30 mm
speed threshold: 0.1 m/s
Ip thresholds and arrival streak: frozen baseline values
```

Raw recomputation:

```text
formal pass                                           12 / 32
formal fail                                           20 / 32
minimum signed margin                    -0.5203167999999989
maximum signed margin                     0.3234768666666674
unavoidable position violations                       20
unavoidable endpoint-late-speed violations             4
solver failures                                         0
saturated action elements                               0 / 16,128
```

Grouped outcomes:

| Group | Pass |
|---|---:|
| nominal target | 8/16 |
| offset target `RZ_p10_m10` | 4/16 |
| delay 0 / slew 1.0 | 8/16 |
| delay 2 / slew 0.9 | 4/16 |
| prefix 5 | 0/16 |
| prefix 9 | 12/16 |
| phase 11 | 0/4 |
| phase 12 | 6/18 |
| phase 13 | 2/4 |
| phase 14 | 0/2 |
| phase 20 | 4/4 |

Each history member passed 6/16. The chosen limiting component was position
in all 32 cases. Twenty cases could not satisfy the position gate at any
allowed formal endpoint, and four of those also had an unavoidable
endpoint-late-speed failure.

## 6. Raw trajectory diagnosis

The decisive split is prefix length:

```text
prefix 5    0/16, mean margin -0.31390057083333345
prefix 9   12/16, mean margin  0.13217178333333304
```

Representative matched R3c1/R3c2 rows show what changed:

```text
prefix-5, nominal target, normal actuator
  R3c1  pass, margin +0.0047383, max |action| 0.5459021
  R3c2  fail, margin -0.2366722, max |action| 0.0775065

prefix-5, offset target, normal actuator
  R3c1  fail, margin -0.2477291, reaches 27.26 mm before exiting
        max |action| 0.9163225
  R3c2  fail, margin -0.5158038, never enters the 30 mm box
        max |action| 0.0755169

prefix-5, nominal target, weak actuator
  R3c1  fail, margin -0.0680751, terminal box error 30.12 mm
  R3c2  fail, margin -0.1123569, terminal box error 32.01 mm

prefix-9, offset target, weak actuator
  R3c1  fail, margin -0.0795060, terminal box error 31.24 mm
  R3c2  fail, margin -0.0868067, terminal box error 31.27 mm

prefix-9, nominal target, normal actuator
  R3c1  pass, margin +0.1028171
  R3c2  pass, margin +0.3231582
```

R3c2's terminal target regulator can improve a state already close to a
useful late-phase trajectory, as seen in the passing prefix-9 nominal cases.
It is too weak and too local for the prefix-5 transport problem. In
particular, R3c2 deliberately passes zero nominal physical coefficients and
a zero nominal feature to the correction solver. The normal-actuator
prefix-5 cases therefore discard the target-conditioned feedforward
transport and act mainly as a local damping controller while the authentic
restart velocity continues to move the plant.

This is not actuator saturation: no action element saturated. It is not a
solver failure: all solves were finite and successful. It is a controller
objective/reference design error.

The earlier Stage4.1R14 diagnosis is directly relevant. That controller
retained a target-conditioned nominal physical/feature trajectory and added
an explicit deadline-velocity objective. Its source comments identify
discarding the target-conditioned nominal plan as a design flaw. R3c2
repeated that zero-nominal mistake specifically on restart states.

A second architectural issue remains: R3c1/R3c2 use the selected reference
phase both to choose a response-model slice and to advance/shrink the solver
horizon, while the immutable formal task clock starts at zero. The next
controller must separate:

```text
formal task clock
  how much time remains to arrive and hold

local response-model phase
  which calibrated Jacobian/response slice best describes the current plant
```

Selecting a late local model phase must not silently imply that the formal
task has less horizon or that the arrival deadline has moved.

## 7. Hidden-history interpretation

For the 16 matched-visible pair-control groups:

```text
both pass                                                6
both fail                                               10
one pass / one fail                                      0
```

The histories were physically different: paired wire-current differences
reached 8.333 A, action differences reached about 0.578, and R/Z
trajectories were not identical. Equal pass/fail labels nevertheless do not
prove robustness. Ten common-mode both-fail groups mask any history
sensitivity.

Therefore:

```text
authentic plant-state restart                          yes
different hidden vessel/eddy histories present        yes
hidden-history robustness validated                     no
observer/history identification validated               no
```

## 8. Required error classification

```text
runtime / environment error
  none in the final 32-task campaign

packaging / import / deployment error
  one pre-run quoting/install command incident; canonical package restored
  from validated staging and fully revalidated before TSC

raw-data or snapshot corruption
  none detected

statistics / reporting error
  none detected in the final R3c2 outputs; independent raw recomputation
  agrees on 12/32 and all integrity/causality counts

test not run
  no required R3c2 validation omitted

plant-restart fidelity failure
  none; exact 32/32

controller-causality failure
  none; 1152/1152 regulator traces and every forbidden-use count is zero

controller-design failure
  yes; zero-nominal terminal regulation is not a finite-horizon restart
  transport MPC, and task horizon is conflated with local model phase

real closed-loop control failure
  yes; 20/32 violate the immutable formal contract
```

## 9. What is frozen and what is not validated

Frozen evidence:

- Stage4.1R17 finite static grid: 18/18.
- Stage4.2R1c authentic plant restart: 18/18.
- Stage4.2R2 causal exact controller-state restart: 18/18.
- R3b authentic development snapshot bank and four selected pairs.
- R3c failed development result: 20/32.
- R3c1 failed development result: 16/32.
- R3c2 failed development result: 12/32.
- Formal timing and every physical acceptance threshold.

Not validated:

- development closure on restart states;
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

## 10. Next action

Do not tune individual prefix/phase/target groups and do not weaken the
formal gate. Do not advance to independent R3d because the development
controller has not closed the frozen 32-case matrix.

The next eventual controller needs:

```text
restart-integrated target-conditioned deadline MPC
```

It must preserve target-conditioned nominal transport, use measured restart
error as a causal residual, keep the formal task clock independent of local
model phase, and optimize velocity at the unchanged deadline.

It is not scientifically safe to implement that controller directly from
the existing lifted model. R14 already retained the nominal plan and added a
deadline-velocity objective, but all 24 cases rebounded after the
35-state model boundary because delayed tail commands changed semantics.
R15B's successful small-signal model covers only the old late weak-slew
state-23 baseline, while R16's large-amplitude bidirectional model failed.
Those models cannot be silently extrapolated to the authentic R3b restart
states and task-relative 250/270 ms horizons.

The immediate next stage is therefore the identification-only R3c3 frozen
in:

```text
docs/codex/reports/STAGE4_2R3C3_PREREGISTERED_DESIGN.md
```

R3c3 retains R3c1's target-conditioned nominal baseline and applies bounded,
bidirectional, zero-net `0.0075` physical-mode probes at two task-clock
windows across every one of the 32 restart contexts. It tests local
linearity, conditioning, and matched-hidden-history response disagreement.
Probe formal outcomes are diagnostic only and may not enter an expert
dataset.

Only if R3c3 passes may R3c4 use the validated bounded response bank for a
new controller identity. If hidden-history response disagreement fails,
visible-only MPC is blocked and causal observer/history-state work comes
first.

## 11. Commands and operations actually used

Local/repository operations included:

```text
git rev-parse --show-toplevel
git status --short
git branch --show-current
git log -1
Python compileall
focused unittest discovery
complete unittest discovery
repository-wide JSON parsing
package checksum and import-closure verification
source-fingerprint and resume-compatibility tests
empty-directory direct-copy deployment simulation under .codex_tmp
SHA-256 verification of every downloaded compact file
independent comparison of R3c, R3c1, and R3c2 raw-derived rows
```

Server operations used the user-authorized fixed SSH endpoint and canonical
project paths:

```text
non-destructive HOME/PWD/project/virtualenv preflight
direct scp transfer without archives
staging and canonical bash/package/import/compile/full-test validation
offline no-TSC source/action/causality gate
one 32-task real TSC campaign with fixed Ray capacity
server-side postprocessing of every raw JSON.GZ
independent raw-control forensic Python audit in place
compact-only result/log transfer
```

No local archive operation occurred. No large final raw JSON.GZ or snapshot
tree was downloaded. No server Git, outbound network, package installation,
root action, broad process kill, or simulation-virtualenv modification was
performed.
