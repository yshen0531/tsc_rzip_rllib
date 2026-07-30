# Stage4.2R3c3T1 final forensic report

## 1. Result

Stage4.2R3c3T1 completed all 128 preregistered real-TSC
identification tasks. The raw trajectories are complete and internally
consistent, the restart and causal-execution checks pass, and the central
symmetry, matched-hidden-history, transport-only conditioning, and current
utilization gates all pass.

The stage nevertheless fails its frozen primary gate because the old four
R3c3 responses plus the two new transport responses exceed the preregistered
combined velocity condition-number limit in 5 of 32 contexts:

```text
real TSC tasks                                      128/128
runtime/environment errors                               0
plant-restart fidelity failures                           0
causality failures                                        0
probe execution/solver/clipping failures                  0
central symmetry                                      64/64
matched hidden-history                                 32/32
transport-only rank/condition                          32/32
combined rank 6                                        32/32
combined condition <= 25                               27/32
worst combined condition                         29.2962711
maximum current utilization                         0.3904
```

This is an identification-design failure. It is not a runtime failure, a
plant-restart failure, a real MPC control failure, or a summary/reporting
failure.

## 2. Exact identities

Local implementation branch and checkpoints:

```text
branch
  codex/stage4_2r3c3t1-transport-response

preregistered design
  b8e66da

implemented and deployed package
  ba8c455
```

Remote project:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib
```

Exact real run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_runs/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441
```

Exact runtime log:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441.log
```

Exact server audit directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_audits/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441
```

Runtime package fingerprint:

```text
cea1e49470afed77387cdf3d636de38541c47998846a817edc32dafd9b60f44a
```

Relevant deployed-file hashes:

```text
PACKAGE_MANIFEST.json
  109f986b82ac7275be86041830f5005c67a101da544b201d75c97b0f3f3dd809

SHA256SUMS
  d3068494626a3cd2832f497a83852d992df4823ee2bce0cd4db5ef0c6e5fa274

config
  b6b8133977e6682a5fd7df70aa94142bd6a16a941ff3533cebd98ff88ae62746

diagnostic module
  bc7eed20c70c98944ae3e5fa53825c397ebfe8098c57cad8fb076d00f7f36c1d
```

The load-bearing package identity is the full runtime package fingerprint.

## 3. Raw evidence and integrity

The complete raw tree remains on the server. In accordance with the
large-result policy, it was postprocessed in place and was not downloaded
locally.

```text
expected raw                                  128
actual raw                                    128
JSON.GZ parse success                         128
experiment-ID set exact                       yes
spec set exact                                yes
raw and manifest integrity                    yes
raw total bytes                         4,505,015
raw inventory digest
  f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f
```

The full run inventory is:

```text
files                                         532
bytes                                  12,861,181
inventory digest
  159ee8f85fc07fec52280cb0f153a75d5f24b8bf69629502f8177b7810567c52
```

Server-side independent audit:

```text
stage4_2r3c3t1_server_audit.json
  0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd
```

The reported summary agrees exactly with recomputation from all 128 raw
files. Runtime and audit package fingerprints are identical.

Compact local evidence is at:

```text
docs/codex/audits/stage4_2r3c3t1_result_20260730_204441/
```

No raw trajectory or snapshot tree was downloaded.

## 4. Execution, restart, and causal checks

Each task started a fresh TSC plant from the authenticated Stage4.2R3b
snapshot and ran the exact R3c1 visible-manifold baseline plus one
prospectively fixed signed probe. All 12 requested nonzero probe corrections
were applied exactly and their requested/applied physical coefficient sums
were zero.

```text
fresh TSC / exact initial restart               128/128
controller trace causal                         128/128
requested/applied probe schedule exact          128/128
hidden wire used by controller                        0
source action/current/result used                     0
pair/history label used                              0
future current-run state used                         0
```

The identification run therefore contains authentic restarted-plant
responses. It does not restore or validate a new controller architecture,
and it is not an independent hidden-history control campaign.

## 5. Response statistics

All preregistered response-fidelity gates pass:

```text
maximum central even velocity RMSE         0.00148217 m/s  <= 0.004
maximum central even position RMSE         0.00016733 m    <= 0.0005
maximum central even Ip RMSE               3.3699 A        <= 20

maximum matched-history odd velocity RMSE  0.00381279 m/s  <= 0.006
maximum matched-history odd position RMSE  0.00035605 m    <= 0.001
maximum matched-history odd Ip RMSE        3.5125 A        <= 40

transport-only worst condition             3.28415053      <= 25
```

Formal tracking of the probe trajectories was diagnostic-only and was not an
identification acceptance gate:

```text
formal tracking diagnostic pass/fail             56/72
```

No formal deadline or threshold was changed.

## 6. Combined-condition failure

Every context has rank six. Five contexts exceed condition number 25, all
from the `p9` hidden-state pair:

```text
p9 q1 minus / nominal              25.63536
p9 q1 plus  / RZ_p10_m10           29.29627
p9 q2 minus / RZ_p10_m10           25.91772
p9 q2 minus / nominal              25.37492
p9 q2 plus  / RZ_p10_m10           27.64826
```

The other 27 contexts pass. Removing the five contexts, changing the
condition-number gate, or reweighting the strata after inspection is
forbidden.

## 7. Post-run design diagnostics

An authenticated server-side amplitude scan used the immutable raw and bank:

```text
diagnostic SHA-256
  23cbfb745aef6b43c48de3379e086c8e39da90f0f7a4e26bf0a5eddd1a7365b7

mode0 scale 0.85, mode1 scale 1.00:
  combined condition pass                    32/32
  worst condition                         24.9678522
```

This proves only that response-column scaling can repair conditioning. It
does not validate a new real-TSC response amplitude.

The corrected six-basis optimistic formal-feasibility diagnostic then used
the exact R3c1 trajectories and all six authenticated odd responses:

```text
diagnostic SHA-256
  e7bc8f0168ff1d2019f1a9a232b5152a27d46a66a92f9542d31d80c6942c3164

formal evaluator reproduction                   32/32
maximum saved-margin error                           0

mode0 scale     condition pass     formal pass     repaired failures
1.00                 27/32             16/32               0/16
0.85                 32/32             16/32               0/16
0.80                 32/32             16/32               0/16
0.75                 32/32             16/32               0/16
0.70                 32/32             16/32               0/16
```

At original amplitude, the closest remaining failure margin improves from
the old four-basis `-0.0603147` to `-0.0458576`, but the worst remains
`-0.3456933`. The new bases add some authority but do not close one failed
context.

Therefore an amplitude-only T2 is rejected before execution. Fixing the
condition number alone cannot produce the required MPC envelope.

## 8. Postprocessing-tool incident

The first six-basis feasibility diagnostic accidentally evaluated the
condition number from R/Z/Ip position-response arrays rather than the frozen
R/Z velocity-response arrays. It produced an impossible 0/32 condition
result and was immediately treated as invalid.

The invalid output is preserved, not overwritten:

```text
stage4_2r3c3t1_six_basis_feasibility_diagnostic_invalid_v1.json
  a19169f1aa7bf38547216ec4536ef06e8b97d34a784036af2c0551eb87845f4f
```

The corrected v2 adds an exact guard against the certified T1 combined
condition count and maximum. It reproduces `27/32` and `29.296271086222426`
before reporting feasibility.

This was a read-only audit-tool/statistics implementation error. It did not
alter raw data, the T1 summary, the T1 verdict, controller semantics, or any
TSC run. No server experiment was resumed or rerun.

## 9. Classification

```text
runtime/environment error                    no
packaging/import/deployment error             no
raw/snapshot corruption                      no
T1 summary/reporting error                    no
audit-only diagnostic v1 bug                 yes, corrected and preserved
test not run                                 no required T1 test omitted
plant-restart failure                         no
real closed-loop MPC failure                  not tested
identification-design failure                 yes
finite-envelope identification success        partial gates only; stage FAIL
unvalidated extrapolation                     amplitude scaling and six-basis
```

## 10. Validation actually run

Local/repository validation:

```text
Python compile                                pass
all repository JSON parse                     pass
focused T1 tests                              9/9
complete tests in project venv              538/538
manifest/checksum/import closure              162 files, pass
empty-directory direct-copy simulation        pass
empty-copy compile/import/self-test            pass
```

The system interpreter lacked `gymnasium` and caused one collection error;
the required complete suite was then run with the repository environment and
passed 538/538. This is not a code failure.

Server validation:

```text
remote path/venv preflight                     pass
shell syntax                                   pass
staging package verification                  pass
installed package verification                pass
installed complete tests                    538/538
offline finite action audit                    128/128
offline raw / plant advance / real TSC         0 / 0 / false
real campaign                                  128/128
server raw postprocessing                      pass
independent summary recomputation              exact
```

One staging-only attempt to run historical root-script tests from a package
that intentionally omitted two old root launchers produced 536/538. The
canonical installed project retained those historical launchers and passed
538/538; the staging result is a validation-harness scope issue, not a T1
runtime or packaging failure.

## 11. Frozen and unvalidated claims

Frozen:

- Stage4.1R17 finite clean static grid: 18/18.
- Stage4.2R1c authentic plant-state restart: 18/18.
- Stage4.2R2 causal controller-state restart: 18/18.
- Stage4.2R3c3 four-basis local identification: 256/256.
- Stage4.2R3c3T1 raw and all passing sub-gates.
- T1 primary result: FAIL because combined conditioning is 27/32.

Still unvalidated:

- a reliable restart MPC expert;
- independent hidden histories and different initial states;
- unseen targets;
- continuous actuator and plant/Jacobian variation;
- noise and observer robustness;
- disturbance recovery;
- independent long hold.

BC, DAgger, and bounded residual RL remain prohibited.

## 12. Next action

Do not run an amplitude-only T2 and do not implement R3c4 from the present
six responses.

The next identification design must alter temporal support so that its odd
response retains authority through the immutable 350/370 ms hold endpoint.
It must keep the 250/270 ms arrival deadlines, use bounded causal actions,
neutralize the probe after the formal hold, and validate the response with
new real TSC before any controller uses it.
