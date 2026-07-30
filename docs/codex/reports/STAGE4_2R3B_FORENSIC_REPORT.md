# Stage4.2R3b final forensic report

Date: 2026-07-30 Asia/Shanghai

## 1. Executive conclusion

Stage4.2R3b completed its entire preregistered real-TSC campaign:

```text
state-generation rollouts                  72/72
authentic snapshot inventories             72/72
candidate hidden-history pairs             36/36
selected pairs                               4/4
fresh restart control rollouts             32/32
```

The state-generation phase genuinely passed. It found 34 pairs above the
prospective hidden-current gate, 16 visible-matched pairs, and 14 pairs that
met both requirements. Selection was completed before control and chose
exactly one pair from each prefix-by-direction stratum.

The control phase genuinely failed: 0/32 fresh closed-loop rollouts preserved
the immutable formal contract. This is not a runtime, deployment, raw-data,
snapshot, plant-restart, or controller-causality error. All 32 TSC
environments completed, all 32 restart states were bit-exact in visible and
full-wire state, and all 32 controller traces were causal.

The failure is a real finite-envelope closed-loop control failure caused by a
controller-design mismatch. R3b reset the new task clock and fresh controller
to step zero, but also reset the time-indexed R17 nominal reference to phase
zero. Raw initial states were instead closest to R17 visible phases 12--20.
The first issued plant actions remained almost the R17 phase-zero actions,
not the actions near the current-state phase:

```text
first action max difference from R17 phase 0      0.0000--0.0163
first action max difference from nearest phase    0.9019--1.4371
```

For all nominal-target cases, the restart state was already inside the 30 mm
R/Z box. The offset-target cases entered it by 50--80 ms. All cases then left
the box by 80--110 ms and diverged to 149--223 mm terminal box error. Position
was the limiting formal component in 32/32 cases; speed constraints also
failed in 32/32. Current utilization remained only 0.382--0.392, so the
failure is not explained by a coil-current envelope limit.

The original-start R17 sources for the same target/actuator specifications
still recompute as 32/32 formal PASS with signed margins
0.0163309832--0.451793337. Therefore R3b refutes transfer of the frozen
time-indexed controller to these different initial states; it does not refute
plant restart fidelity or the original R17 finite baseline.

R3b does not validate hidden-history robustness. The plus/minus members had
no pass/fail disagreement only because both members suffered the same
dominant controller failure. Their trajectories and actions were not
identical, but that sensitivity is masked at the formal outcome level.

## 2. Exact identities

```text
local branch
  codex/stage4_2r3b-confirmatory-history

implementation commit
  8fb1534

controller revision
  confirmatory_hidden_history_initial_state_mpc_v42r3b

package revision
  r42r3b_confirmatory_hidden_history_v1

PACKAGE_MANIFEST.json SHA-256
  2fcd4e5a5e9d9d69512e56dcb4b614ed93e5496c72887df3d29befc0adbb5c37

SHA256SUMS SHA-256
  fb8b008fc8baac8bb5606fe7376b9520087eac9efe18c97c7b8e5025c82ad194

resolved config SHA-256
  b20c69455278ed1ae97a481cc68cc127816a4ee6a3334896038efbdeb2a01513

R3b controller module SHA-256
  edf6188581a01dbe6f726e6dbd941e0c9a35770e57e599d57962d832a51fbf71

deployed package fingerprint
  ec848862b1bd77576452a67e9e596266d1c15322876edece977b55304e8cae59

source fingerprint
  4ee32cd099b19aa3fd4b0a99be31cf3c4e53edc2f626bd3b578bb63f595fa015

R3a calibration fingerprint
  367782ca436a023ab3ba3117c145aed4d40e280c6627977a72ca0f411356386b
```

Authenticated prefix source:

```text
source experiment
  s41r11_076c2e2752cc8914bcf9

prefix-5 action digest
  6abb946a40dfb78554f0bff835e466d3d6261b2fde2597febd233b94eedb454d

prefix-9 action digest
  20847e482d2e619a8b5d66aa0235a4bbe6f937bf6b9117f85ab0116dfd1f8f0f
```

Remote paths:

```text
canonical project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

staging package
  /home/yangshen0711/tsc_software/stage4_2r3b_package_8fb1534

predeployment backup
  /home/yangshen0711/tsc_software/stage4_2r3b_predeploy_backup_8fb1534

source R2 run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r2_runs/
  stage4_2r2_persistent_controller_checkpoint_replay_20260730_082250

calibration R3a run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3a_runs/
  stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_20260730_110128

R3b run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_runs/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526

offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526.log

real-TSC resume log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115620.log

server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3b_audits/
  stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526
```

## 3. Validation and execution

Before real TSC, the following validation passed:

```text
focused R3b tests                              14/14
complete repository tests                    473/473
Python compile                                passed
all JSON parse                                passed
import closure                                passed
package file inventory/hash                  130/130
source fingerprint and resume guards          passed
empty-directory deployment simulation        473/473
undeclared external source dependency         none
server bash -n                                passed
server import/compile with existing venv      passed
staging and installed server tests            473/473
fixed Ray campaign capacity                   128
```

The no-gotsc gate completed first in the final run directory:

```text
frozen-controller cases                         4/4
maximum action difference                       0.0
future actions read                               0
future states read                                0
real TSC run                                  false
```

The same run was safely resumed because experiment identity, controller
semantics, task grid, source fingerprints, and physical action semantics were
unchanged. The resume completed 72 state tasks and 32 control tasks.

One staging-validation shell invocation returned a Windows-native-command
status of 1 because unittest progress was emitted on stderr; its remote log
showed all tests and package checks passing, and a separate explicit server
recheck exited 0. This was a local log-capture/tooling issue, not a failed
server validation.

The first independent forensic-tool launch omitted `PYTHONPATH` and stopped
immediately with `ModuleNotFoundError`. It read or changed no experimental
data. The corrected read-only launch completed. This is a postprocessing
launch error and is not counted as an experiment runtime error.

## 4. State-generation result

Independent recomputation from all 72 state raw JSON.GZ files produced:

```text
state raw success                              72/72
snapshot payload inventories valid             72/72
candidate pairs                                36/36
visible-matched pairs                          16/36
hidden-separated pairs                         34/36
accepted pairs                                 14/36
selected pairs                                   4/4
prefix-by-direction coverage                     4/4
selected different-initial-state centroids       4/4
prefix-group separation                         pass
```

The four selected pairs, chosen before control, were:

```text
p5_q1_a0p900_gap2_settle4
p5_q2_a0p900_gap2_settle4
p9_q1_a0p750_gap2_settle4
p9_q2_a0p750_gap2_settle4
```

Their state-generation hidden separation ranges were:

```text
48-wire maximum absolute difference       0.334--0.401 A
48-wire RMS difference                    0.165--0.201 A
relative wire RMS difference             0.0904--0.1619
```

Their visible matching and material hidden-state gates all passed. Prefix-5
and prefix-9 selected centroids were separated by 3.701 mm in R, 0.221 mm in
Z, 158.767 A in Ip, and 1.040 A coil-current RMS. The preregistered different
initial-state gate passed through R separation.

This validates authentic state construction and selection. It does not by
itself validate control from those states.

## 5. Raw, snapshot, and transfer integrity

The server postprocessor hashed the complete run in place:

```text
run files                                      874
run bytes                            8,538,932,691
run inventory digest
  301a3ad2be01c83209d8e260c1a8c80f090d01afafb9c173f63cf9219caac8fc

state raw expected/actual                    72/72
control raw expected/actual                  32/32
raw experiment-ID sets exact                   yes
raw specifications exact                       yes
strict raw parse complete                      yes
snapshot valid                               72/72
manifest compatibility checks              all true
runtime/environment errors                       0
raw/snapshot corruption                          0
```

Large raw JSON.GZ and snapshot files remain on the server. Only 1,252,403
bytes in 27 compact run/result/log files and the compact server audit were
downloaded. All 24 downloaded files that belong to the run matched the
server inventory in both size and SHA-256. All 24 downloaded JSON files
parsed successfully. The separately downloaded log and audit hashes also
matched server-side `sha256sum`.

Load-bearing compact hashes:

```text
server audit
  f1e907888e19846d07099714d4b581e26aac80c5675a373364d396db78130831

run inventory document
  f4e9c9d91f5d9439769adca9176431243ebf8d5a430a29cb54a5b15d2b5d6407

snapshot checks
  a979757e4a62ece89635754a2885308549dbd0b8b88f8e849b03f0e648e0b927

independent raw control forensics
  975205eff41f62d319e4f6e22643bb687461e42d3c73c1d09f0424f2a7c5cf32

independent forensic tool
  8265bdb935440e81de67a71e163d39df2f2760c30352f3849e5d23cdab428b73
```

Compact local evidence:

```text
docs/codex/audits/stage4_2r3b_result_20260730_115526/
```

## 6. Closed-loop formal result

Every one of the 32 control raw files was independently re-evaluated against
the frozen 250/350 ms or 270/370 ms timing policy:

```text
environment success                           32/32
fresh controller                              32/32
fresh TSC process                             32/32
initial visible restart exact                 32/32
initial full-wire restart exact               32/32
causal controller trace                       32/32
future action replay                              0
future measurement use                            0
hidden wire controller input                      0
formal contract pass                           0/32
formal signed margin range       -6.447296-- -3.960849
```

Constraint decomposition at the best allowed formal endpoint:

```text
position violated                             32/32
endpoint speed violated                       32/32
endpoint late-speed RMS violated              32/32
post-arrival speed RMS violated               32/32
final speed violated                          32/32
Ip terminal violated                          11/32
Ip hold RMS violated                           4/32
Ip safety maximum violated                     0/32
Ip sustained tracking violated                 0/32
```

Position was the most negative component in all 32 cases. Group failure was
uniform across both targets, both actuator cases, both prefix lengths, both
nullspace directions, and both history orders.

The restart trajectories initially approached or already occupied the target
box, but did not hold:

```text
nominal, prefix 5:
  first entry step 0; first exit step 8; longest streak 8

nominal, prefix 9:
  first entry step 0; first exit step 9; longest streak 9

RZ_p10_m10, prefix 5:
  first entry step 7 or 8; first exit step 9; longest streak 1--2

RZ_p10_m10, prefix 9:
  first entry step 5; first exit step 10 or 11; longest streak 5--6
```

Thus this is not a hidden later arrival. The controller drove every case out
of tolerance long before the formal 250/270 ms arrival deadline and failed
to decelerate or hold through 350/370 ms.

## 7. Controller-design diagnosis

The directly observed mechanism is:

```text
fresh plant/task state index                    0
fresh controller trace first step               0
nominal reference start phase                   0
nearest R17 visible phase                  12--20
solver failures                                 0
maximum current utilization             0.382--0.392
```

R3b's `FreshTaskController` initialized its nominal trajectory, delay queue,
integrals, previous correction, and measurement history as a new phase-zero
task. This satisfied the intended causality restriction, but the controller
remained a time-indexed trajectory follower built for the original R17
initial state. It had no causal state-to-phase alignment or state-aware
replanning.

The raw action comparison is especially discriminating:

```text
first action versus R17 phase-zero action
  max absolute difference                 0.0000--0.0163

first action versus action at nearest visible R17 phase
  max absolute difference                 0.9019--1.4371

whole-horizon action versus same R17 timeline
  max absolute difference                 0.1225--0.1527
```

The restart state differed from the original source start by
15.36--19.50 mm in R, 2.28--2.96 mm in Z, 812--972 A in Ip, and
7.86--8.28 A coil-current RMS. Yet its normalized distance to the nearest
R17 phase was roughly four times smaller than its distance to phase zero.

This is strong raw and code evidence that phase-zero replay is the dominant
failure mechanism. It is not yet proof that one particular phase-alignment
algorithm is sufficient; that requires a new controller identity and new
real-TSC rollouts.

## 8. Hidden-history interpretation and reporting issue

Across the 16 plus/minus control groups:

```text
pass/fail disagreement groups                       0
formal-margin absolute difference        0.00206--0.01570
maximum action difference              0.000018--0.003864
maximum R difference                    0.381--0.465 mm
maximum Z difference                    0.349--0.531 mm
maximum Ip difference                    5.67--14.69 A
maximum full-wire difference             0.334--1.012 A
```

The members are therefore not numerically identical, and their hidden
histories remain physically distinct. However, both members fail every
formal group under the much larger common-mode controller mismatch. Zero
pass/fail disagreement is consequently inconclusive, not evidence that
hidden history has been handled.

The saved summary field
`observer_or_history_identification_failure_count=0` is a reporting-design
defect: it is currently aliased to pass/fail disagreement count. Under a
common-mode 0/32 failure, zero does not mean observer/history success. This
field did not alter task execution, raw data, formal metrics, primary
verdict, or the conclusion. The R3b run will not be post-hoc relabeled or
resumed under changed code. The next stage must report masked/inconclusive
history assessment explicitly.

## 9. Required classification

```text
runtime/environment error
  none in the 104 real-TSC tasks

deployment/package/import error
  none in the deployed experiment

raw/snapshot corruption
  none

statistics/reporting error
  observer/history failure count is semantically misleading under common-
  mode failure; verdict and formal result remain correct

experimental-design/controller-design flaw
  yes: time-indexed R17 reference reset to phase zero at a different initial
  state, with no causal phase alignment or state-aware replanning

plant-restart fidelity failure
  none; 32/32 visible and full-wire initial states exact

controller causality failure
  none; 32/32 causal, no future action/measurement and no hidden-wire input

real closed-loop control failure
  yes; 0/32 immutable formal-contract pass

finite-envelope hidden-history success
  not established

unvalidated extrapolation
  unseen targets, continuous parameters, plant/Jacobian mismatch, noise,
  disturbances, and independent long hold remain unvalidated
```

## 10. Frozen claims and next action

Still frozen:

- Stage4.1R17 is 18/18 only on its finite original-start clean static grid.
- Stage4.2R1c authentic plant restart is 18/18 for exact expert suffix replay.
- Stage4.2R2 causal controller-state restart is 18/18 for exact checkpoint
  continuation.
- R3b authentic state construction passed for the four selected pairs.
- The formal arrival and hold times are unchanged.

Not frozen:

- fresh-controller control from different initial states;
- hidden-history robustness;
- a causal observer/history identifier;
- unseen targets or continuous plant/actuator variation;
- noise, disturbance recovery, or independent long hold.

The next stage is Stage4.2R3c, a development-stage controller repair:

1. lock the exact R3b run inventory and selected snapshot identities;
2. use only visible R/Z/Ip and coil-current information;
3. choose a causal nominal phase from the current visible state;
4. align nominal reference, delay-queue priming, and phase transitions;
5. keep controller task time and the formal arrival clock at zero;
6. run the unchanged 32-case R3b development matrix under a new controller
   and experiment identity;
7. report hidden-history outcome as inconclusive if a common-mode failure
   masks pair sensitivity.

Because R3c reuses snapshots after observing R3b, even a 32/32 R3c result
would be controller-development evidence, not independent hidden-history
confirmation. A successful repair must be followed by Stage4.2R3d on newly
generated, preregistered, unseen histories and initial states before advancing
to new targets.

BC, DAgger, and residual RL remain prohibited.

## 11. Commands actually run

The executed command classes were:

```text
git rev-parse --show-toplevel
git status --short
git branch --show-current
git log

repo venv Python compile/compileall
focused unittest discovery with the Windows resource shim
full repository unittest discovery
JSON parse and package inventory/hash checks
empty-directory package verification and tests

ssh/scp/sftp using the fixed authorized public-key endpoint fallback
remote HOME/PWD/project/venv preflight
remote bash -n, package verification, import/compile, and tests
offline no-gotsc launch
safe same-directory resume
PID/log/state monitoring
server-side raw/snapshot postprocessing
server-side independent raw control forensics
direct uncompressed compact-file transfer
local SHA-256 comparison against the server run inventory
local strict JSON parse
```

No local archive operation, large-result download, server Git operation,
network installation, virtualenv modification, broad process kill, formal
gate change, or experimental rerun after seeing the result was performed.
