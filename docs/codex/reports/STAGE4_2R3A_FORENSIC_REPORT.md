# Stage4.2R3a final forensic report

Date: 2026-07-30 Asia/Shanghai

## 1. Executive conclusion

Stage4.2R3a completed all 72 preregistered real-TSC state-generation
rollouts and produced 72 valid authentic snapshots. Delayed
counter-pulses increased the largest observed matched-history full-wire
difference from R3's 0.048 A to 0.527 A, but no pair reached R3a's frozen
absolute gate of 1.0 A. The conditional control phase was therefore
correctly `not_run`.

R3a remains failed under its preregistered gate. The result was not changed
after inspecting the data.

The failure is an experimental-design and threshold-calibration failure.
It is not a runtime, deployment, import, raw-data, snapshot, summary, plant
restart, or closed-loop controller failure. R3a provides no control evidence
because no control rollout ran.

Independent raw recomputation also establishes two useful design facts:

1. the common-prefix mechanism generated authenticated initial states
   different from the frozen start in 36/36 pairs and separated the
   prefix-4 and prefix-8 groups; and
2. the generated hidden differences were real and repeatably above raw
   quantization, but were smaller than the frozen 1.0 A absolute gate.

These facts motivate a separately preregistered confirmation experiment.
They do not retroactively validate R3a.

## 2. Exact identities

```text
local branch
  codex/stage4_2r3a-delayed-history

implementation commit
  8a3eb670e9db210594f21260c2391cea0a32a255

controller revision
  delayed_counterpulse_hidden_history_initial_state_mpc_v42r3a

package revision
  r42r3a_delayed_counterpulse_hidden_history_v1

PACKAGE_MANIFEST.json SHA-256
  e9a5eb5582b8d0de3570d60d216bdd70b657f097d22b543f4f7db9cd4649088c

SHA256SUMS SHA-256
  f9454a40316755ae419b4f1efe4cdc28de77dafff47b2c61340398bfed34080a

deployed package fingerprint
  b56c45d947c8afc0c43a9257a634c977345fbf86825c139b69ea244d9d910590

source fingerprint
  4ee32cd099b19aa3fd4b0a99be31cf3c4e53edc2f626bd3b578bb63f595fa015

resolved config file SHA-256
  8b718e3236f897205d32fcbbe24b91950a41645ea801978774e658e3f98b82b0

canonical resolved-config digest
  6d8e9cc86a05efdfe85dbc9060987567a0c4d95a4f9a33126c842e3abdb8fb41

R3a controller module SHA-256
  e2964936d84ecee1502a3333293e9aeb0329159a830c168405481b4341964994

state-generation specification digest
  5140fd568f989729bcd095c468a0cb77e31ab971e9389abbbbd64c4237536ecf
```

The authenticated common-prefix source was:

```text
source experiment
  s41r11_076c2e2752cc8914bcf9

target / actuator case
  nominal / delay 0 / slew 1.0

prefix-4 action digest
  81868c745a90d3fee26bb5ce6683196145c76371f016570dfb2ea32e85f82060

prefix-8 action digest
  ffec30c36c653d48ae6be086313ea3dbd1fd6a103414fe4491b43ed91d058be6
```

Remote paths:

```text
canonical project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

staging package
  /home/yangshen0711/tsc_software/stage4_2r3a_package_8a3eb67

predeployment backup
  /home/yangshen0711/tsc_software/stage4_2r3a_predeploy_backup_8a3eb67

source R2 run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r2_runs/
  stage4_2r2_persistent_controller_checkpoint_replay_20260730_082250

R3a run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3a_runs/
  stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_20260730_110128

offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3a_offline_20260730_110128.log

real-TSC log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_20260730_110200.log

server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3a_audits/
  stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_20260730_110128
```

## 3. Validation actually run before real TSC

Local/repository validation:

```text
focused R3a tests                             12/12 passed
complete unittest discovery                  459/459 passed
Python compile                               passed
all JSON parse                               passed
import closure                               passed
package file inventory/hash                  124/124 passed
source-fingerprint/resume guard tests        passed
empty-directory deployment simulation        459/459 passed
undeclared source-tree dependency            none found
```

Staging and canonical installed server validation:

```text
exact remote path preflight                  passed
declared shell bash -n                       passed
package file inventory/hash                  124/124 passed
Python compile/import with existing venv     passed
complete unittest discovery                  459/459 passed
Git/network dependency                       none
server virtualenv modification               none
fixed Ray campaign capacity                  128 CPUs
```

The no-gotsc offline gate was run before state generation:

```text
required frozen-controller cases             4/4
maximum online-action difference             0.0
future-action reads                          0
future state persisted                       0
real TSC executed                            false
state raw files                              0
snapshot files                               0
```

The offline run was then safely resumed in the same run directory because
the controller semantics, experiment identity, source fingerprints, state
matrix, and physical action semantics were unchanged.

## 4. Expected versus actual execution

```text
state-generation rollouts expected           72
state-generation rollouts actual             72
successful real-TSC state rollouts           72
candidate pairs expected                     36
candidate pairs actual                       36
visible-matched pairs                        24
different-initial-state pairs                36
hidden-separated pairs under frozen gate      0
accepted/selected pairs                       0
conditional control expected if selected    16-32
conditional control actual                    0
```

Zero control tasks is the specified conditional behavior. It is neither a
missing run nor a control failure.

## 5. Raw, snapshot, manifest, and transfer integrity

The independent server postprocessor read and hashed the large run in
place:

```text
run files                                    739
run bytes                                    8,535,699,130
run inventory digest
  9be432ee725035b31cee32f9415298aacd1fa576e24190588b8ef2c2be08eae7

state raw expected/actual                    72/72
state raw success                            72/72
raw experiment-ID set exact                 yes
state specifications exact                  yes
strict raw parse complete                   yes
snapshot manifests/payload sets valid       72/72
runtime/environment errors                   0
raw/snapshot corruption                      0
manifest compatibility checks               all true
```

The server audit's `passed=true` means the integrity and recomputation audit
passed. It does not mean that the scientific R3a gate passed. The independently
recomputed primary result is `false`.

Large raw JSON.GZ and snapshot payloads remain on the server. The downloaded
compact audit is:

```text
docs/codex/audits/stage4_2r3a_result_20260730_110128/
```

The server-declared compact inventory contains 23 files and 964,455 bytes,
with digest:

```text
d7c12be4dafef9fbc97d6512d258d0045a01bc8a14324c0aba27b81af1a44608
```

All 23 local files matched their declared sizes and SHA-256 values. Including
the compact inventory and the locally generated checksum list, the tracked
directory contains 25 files and 971,284 bytes. Its load-bearing audit hashes
include:

```text
server audit
  3e270647c51b67f6160be2b26ad903b73811dce15b973028228e39b94d640f90

independent raw forensics
  3889ef0df2220a4ada253761535945c143f80bca1e0351e7ece0c380abc61e23

run inventory document
  23954a28ab455fa27b8fd837180ddab99c014a4726828c3d48e96dafd5a28699
```

## 6. Independent raw metric recomputation

### 6.1 Frozen R3a gate

For the 36 preregistered plus-first/minus-first pairs:

```text
visible-matched pairs                        24/36
relative hidden gate >= 0.05                 20/36
absolute hidden gate >= 1.0 A                 0/36
full frozen hidden gate                       0/36

wire max absolute difference range
  0.082 to 0.527 A

wire relative RMS difference range
  0.02054244265454698 to 0.20857868118314551

visible maximum normalized ratio range
  0.18374800000020564 to 2.8549006000000015
```

Only R and Z caused visible-gate failures:

```text
R threshold failures                         7
Z threshold failures                        10
Ip / vR / vZ failures                        0 / 0 / 0
coil maximum / RMS failures                  0 / 0
endpoint action failures                     0
```

The independent same-clock cross-pair search considered 540 pairs:

```text
same-clock cross pairs                      540
visible-matched                             322
visible-matched absolute >= 1.0 A             0
visible-matched relative >= 0.05              81
visible-matched full frozen gate              0
largest visible-matched wire difference       0.487 A
```

Thus the result was not caused by a mistake in the original within-pair
matching algorithm.

### 6.2 Authentic different initial states

All 36 pair centroids passed the frozen-start different-initial-state gate.
Across all generated states, endpoint full-wire RMS ranged from
1.2255881241265354 A to 2.981651066663122 A.

The prefix-4 and prefix-8 group centroids were mutually separated:

```text
R difference                                 0.008874114805555777 m
Z difference                                 0.002090778647222225 m
Ip difference                                37.63050277778166 A
14-coil RMS difference                       1.4719908267538921 A
```

The group gate passes through R and Z. This proves that the common-prefix
state-generation mechanism moved the plant to different authenticated
initial states. Because no hidden-history pair passed the frozen absolute
gate and no control ran, it does not prove different-initial-state closed-loop
robustness.

### 6.3 Exploratory threshold sensitivity

This subsection is diagnostic only and does not change R3a's result.

Six R3a pairs would satisfy the conjunction:

```text
visible match
wire maximum absolute difference >= 0.25 A
wire RMS difference >= 0.10 A
wire relative RMS difference >= 0.05
```

They cover both prefix lengths and both nullspace directions. Their wire
maximum differences are 0.270-0.337 A, wire RMS differences are
0.131-0.175 A, and relative RMS differences are 0.0547-0.1209. A 0.30 A
absolute threshold would leave only three; 0.35 A would leave none.

The 0.25 A scale is 250 times the observed 1 mA raw wire-current increment,
while the RMS and relative gates require a distributed vector effect rather
than one changed element. Since this calibration used R3a results, it may
only be tested prospectively in a new experiment on a new state grid.

## 7. Error and scientific-result classification

### 7.1 Runtime/environment

None. All 72 real-TSC state tasks completed successfully.

### 7.2 Deployment/package/import

None. Staging and installed package verification, compile, import closure,
`bash -n`, and all 459 server tests passed.

### 7.3 Raw/snapshot corruption

None. The 72 raw results and 72 snapshot inventories parsed, hashed, and
matched their exact experiment specifications.

### 7.4 Summary/statistics/reporting

No final reporting defect changed the result. The saved summary says
`visible_match_pair_count=24`, `hidden_separation_pair_count=0`, and
`control not_run`; independent raw recomputation agrees.

The field `server audit passed=true` is an integrity-audit result only.
Treating it as the experiment verdict would be a reporting interpretation
error, but the tracked scientific verdict does not do that.

### 7.5 Experimental-design defect

The R3a delayed-pulse mechanism materially improved hidden-history separation,
but the preregistered 1.0 A absolute threshold was too high for the
visible-matched states it generated. Increasing amplitude or pulse gap often
increased hidden difference while pushing R/Z outside the visible-match
window. This is the measured design tradeoff.

There is no evidence of an ampere/kiloampere conversion bug: endpoint wire
currents, pair differences, raw resolution, and snapshot values are mutually
consistent.

### 7.6 Observer/history identification

Not tested. No accepted snapshot pair reached the controller phase.

### 7.7 Real control and plant restart

Not tested. No fresh-TSC control restart was launched from an R3a selected
pair, so there is no R3a evidence for or against restart fidelity, hidden-
history control, or formal tracking.

## 8. Frozen conclusions and unvalidated axes

Still frozen:

- R17 finite clean static-grid baseline, 18/18;
- R1c authentic same-action plant restart, 18/18;
- R2 causal persistent-controller restart, 18/18;
- immutable 250/350 ms and 270/370 ms formal timing;
- the R3 and R3a failures under their original gates;
- no BC, DAgger, or residual RL.

Not yet validated:

- matched-visible/different-hidden closed-loop robustness;
- closed-loop robustness from different authenticated initial states;
- new targets;
- continuously varying actuator parameters;
- plant/Jacobian error;
- measurement noise and observer robustness;
- disturbance recovery;
- independent long hold.

## 9. Next action and why

Stage4.2R3b is a new, prospectively gated confirmation experiment. It uses
new common-prefix lengths and new pulse amplitudes rather than relabeling or
reusing R3a pairs. Its material hidden-history gate is calibrated from the
frozen R3a raw evidence and adds an absolute vector RMS requirement. R3b must
complete its entire new state grid before selecting pairs, and its controller
phase remains conditional.

This directly advances the reliable-MPC-expert roadmap. It does not begin
BC, DAgger, or residual RL.

## 10. Commands run and work not run

Commands actually run included:

```text
local:
  Python compile/JSON/import/package verification
  focused and complete unittest discovery
  empty-directory deployment simulation
  local SHA-256 and compact-inventory verification

server:
  path/virtualenv preflight
  staging and installed package verification
  bash -n and complete unittest discovery
  Stage4.2R3a offline command
  safe resume of the same R3a run with Ray capacity 128
  read-only server postprocessor
  independent read-only raw-forensics script
  final read-only run/inventory/PID recheck
```

No R3a control rollout, unseen-target test, continuous-parameter test,
plant/Jacobian mismatch test, noise test, disturbance-recovery test,
independent long-hold test, BC, DAgger, or RL was run.
