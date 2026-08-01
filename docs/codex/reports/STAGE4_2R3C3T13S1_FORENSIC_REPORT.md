# Stage4.2R3c3T13S1 final result and transition forensics

## 1. Final result

Stage4.2R3c3T13S1 completed its only authorized real campaign. All 52/52
fresh authentic `gotsc` trajectories completed, but the frozen scientific
sentinel gates failed:

```text
official route                              SENTINEL_FAIL_STOP_IDENTIFICATION
execution                                      52 / 52 PASS
pre-effect causality                            24 / 24 PASS
signal                                          24 / 24 PASS
local response matrix                            4 / 4 PASS
central symmetry                                0 / 24 PASS
matched hidden-history response                  0 / 12 PASS
maximum normalized condition number                9.17194264627853
maximum current utilization                         0.3904 <= 0.55
```

This is a clean identification/model/action-resolution design failure. It is
not a runtime, deployment, restart, snapshot, raw-corruption, statistics, or
reporting failure. T13S1 did not implement or test a real MPC, so it is also
not a real closed-loop MPC failure and does not prove plant unreachability.

The official verdict and thresholds are unchanged. The run must not be
resumed, rerun, or enlarged under the same identity. Its probe trajectories
remain forbidden from expert data.

## 2. Exact identities

```text
local branch
  codex/stage4_2r3c3t13s1-transition-sentinel

implementation commit
  898b559ba5d2f716f4e2e255f9a570b87af3bbb2
package-closure commit deployed for the real run
  ecc05f61838e5c9214bad75fe0a61295429f7a33
initial immutable-raw forensic checkpoint
  34a3a213f2bcbabc634c8c1b431b966eca1b52d8
Card15 resolution audit checkpoint
  0fe3077b7b9ce6f66dd0859bab89906c964d40dd
zero-command forensic fix and final forensic source
  9b8353da0dde5f1de3a996b679270f6991decea6

package revision
  r42r3c3t13s1_minimal_transition_sentinel_v1
controller revision
  single_step_transition_probe_v42r3c3t13s1_v1
underlying controller
  authenticated_visible_manifold_phase_mpc_v42r3c1
campaign identity
  restart_issue_time_single_step_transition_sentinel_v1
```

Remote evidence:

```text
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s1_runs/
  stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_ecc05f6

log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_110302.log

official audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s1_audits/
  stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_ecc05f6

read-only transition forensics
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s1_forensics/
  stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_ecc05f6_9b8353d
```

## 3. Raw, snapshot, manifest, and report integrity

```text
expected / actual raw files                  52 / 52
raw bytes                                  2,463,366
raw inventory digest
  de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603
successful/completed raw                     52 / 52
declared / actual unique restart states         4 / 4
snapshot identity checks                        4 / 4
extended-baseline prefix reproduction           4 / 4
baseline formal reproduction                    4 / 4
package exact                                      yes
summary exact on independent recomputation          yes
raw/manifest integrity                              yes
```

Load-bearing hashes:

```text
state
  c07890533574dfc4e852af64091524b5786601b8aba195548ea31fd4765e05cc
manifest
  971f0b1fa0d5b13f17696e7f601acce750822b5a89afc6859bea222c6c972dd9
summary
  ecc463834e4b6818277ee704032d85405b5775107f10935f334008252fca4486
raw inventory JSON
  be33af274c6f9a96b14fe113e9da7cf8d4e7d21c1905aa985fed4cd4dfff5985
run inventory JSON
  b5ce7f65747a9ba085e9c8aa731e004070ec2428f09a27a908c23ea716c91eca
server audit
  5695dd9ff5fbcc901182d7f3b3c86cedf9d3375ec12dbebf63152e2d03ba8951
snapshot audit
  e2bb3fa8fc186a87d635dff7e8220f32a3338828cfdb4226da4fc22bc46b6853
log
  7f713e1a91f37dea199be15af8ccf7f02059a3532367a385652ea8ea61c7cdf7
transition forensic report
  4f852c632b0d62e1298e8684427870815b853d20af41b7e684cda5159532c84e
transition forensic manifest
  6e069165ca55f775f160b73e374736e07c65a1a1fd9962189676ca6e14657453
```

Only 20 compact evidence files were copied directly and uncompressed into
`docs/codex/audits/stage4_2r3c3t13s1_result_20260801_9b8353d`. The 52 raw
JSON.GZ files remain on the server. All 19 downloaded JSON files parse; 13
run files match the downloaded official run inventory and the other seven
files match their separately recorded remote hashes. See
`TRANSFER_MANIFEST.json` in that directory.

## 4. Error classification

| Class | Count/result | Conclusion |
|---|---:|---|
| runtime/environment | 0 | no failure |
| packaging/import/deployment | 0 | exact deployed package |
| plant restart fidelity | 0 | four authentic snapshots exact |
| controller causality | 0 | all forbidden-input checks clean |
| solver | 0 | no failure |
| scheduler/saturation/rescale | 0 | no failure |
| raw/snapshot corruption | 0 | inventories and snapshots exact |
| statistics/reporting | 0 | summary reproduced exactly |
| identification design | FAIL | symmetry and matched-history relative gates fail |
| real MPC control | not tested | no MPC conclusion is allowed |

The 26 formal passes among the 52 identification trajectories are recorded
only as trajectory diagnostics. Formal tracking was prospectively not the
probe acceptance gate, and probe rollouts cannot become expert data.

## 5. Requested command, actual current, and plant layers

The read-only forensic authenticated all 52 immutable raw files and executed
zero controller, Ray, `gotsc`, TSC, or plant steps. It separates four layers
that the official aggregate symmetry verdict alone cannot distinguish.

```text
requested first-issue command symmetry             24 / 24 PASS
observed first-effect coil-current symmetry          0 / 24 PASS
immediate plant-response symmetry                    3 / 24 PASS
plant symmetry through formal endpoint               0 / 24 PASS
matched-history immediate response                   6 / 12 PASS
matched-history response through formal endpoint     0 / 12 PASS
pre-effect exactness                                 24 / 24 PASS
```

The source-defined Card15 writer uses a ten-character `.3E` field. Across
the nonzero compared first-issue commands, 304/336 coil components were
smaller than one local Card15 formatter grid. Observed current increments
were on that grid to a maximum integer-grid residual of
`2.1032064978498966e-12`. Requested antithetic commands were therefore
exactly symmetric in controller space while their finite-precision physical
current realization was not.

This proves that action resolution is material. It does not explain away all
plant behavior: immediate plant symmetry still passed only 3/24 after the
actual current layer was separated, and all complete formal windows failed.
The remaining result includes genuine nonlinear/input-direction effects and
later closed-loop accumulation.

For matched histories, prefix-5 passed 6/6 at the first effect when compared
using the actual odd current response, but prefix-9 passed 0/6. The paired
histories also had small but nonzero causal visible-state/velocity
differences before effect, while their forbidden wire-current states were
different. The matched-history gate therefore cannot by itself isolate a
single hidden-current cause. A future controller must use current-run causal
state and measured coil current and retain unresolved latent effects as a
multi-hypothesis/tube uncertainty; it may not consume pair, history, prefix,
or wire-current labels.

## 6. Forensic tool validation

The final source hashes are:

```text
docs/codex/audit_tools/stage4_2r3c3t13s1_transition_forensics.py
  c2e927ea849c5dd9b8944bec11739d83a1a7b1c0ea0f7fa501f4fb4bae06a2f8
tests/test_stage4_2r3c3t13s1_transition_forensics.py
  eb0fbd29fedea693da76be9f3acd4d252f57dad9fc67e3e9c4b80411d689901a
```

Validation actually run:

```text
local py_compile                                      PASS
local direct focused forensic tests                    4 / 4 PASS
server source hash verification                             PASS
server py_compile                                           PASS
server direct focused forensic tests                    4 / 4 PASS
server canonical unittest discovery                  639 PASS, 1 skipped
server pytest                                              NOT RUN
  reason: the existing server virtualenv has no pytest module
```

The first server invocation at commit `0fe3077` stopped before creating an
output directory because the forensic code took a minimum over an empty
active-command array. Inspection of the real raw showed this case is valid:
some requested trace-command differences are exactly zero at Card15
resolution. Commit `9b8353d` fixed only the read-only forensic aggregation;
it changed no raw, experiment identity, controller, threshold, or scientific
result. The corrected invocation then completed as recorded above.

## 7. Frozen conclusion and next action

The immutable formal timing remains 250/270 ms arrival and 350/370 ms hold,
with the original tolerances and three-state arrival streak. The 500 ms
observation horizon is not a later deadline or an independent long-hold
success test.

The next task is a zero-new-TSC, source-and-raw-backed audit of the exact
Card15 quantized actuator mapping and the causal observable state available
at the two issue times. It must distinguish exact actuator reconstruction,
finite clean-state separability, observational aliasing, and unvalidated
noise/history extrapolation. It cannot reinterpret T13S1 as PASS, fit a T11
bank, authorize R3c4, or use forbidden hidden labels.

Until a quantization-aware causal state/set-valued transition interface and
prospective holdout are frozen and validated, no new real controller is
authorized. BC, DAgger, and bounded residual RL remain blocked.
