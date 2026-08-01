# Stage4.2R3c3T13S4 lattice transition holdout final report

## 1. Final result

T13S4 stopped at its mandatory offline dynamic-lattice gate before Ray,
`gotsc`, TSC, or any plant step. Its final route is:

```text
LATTICE_PREFLIGHT_FAIL_NO_REAL_TSC
```

The frozen four-local-step design is infeasible at the selected authentic
R3c1 controller states:

```text
offline specifications                              52/52 audited
complete offline specifications                     11/52
frozen lattice design failures                      41/52
  issue failures                                    40/52
  cancellation failures                              1/52
raw JSON.GZ                                             0
plant advances                                          0
real TSC executed                                    false
```

The 11 complete specifications are four uninstrumented baselines and seven
p9/mode-1 signed probes. No scientific transition trajectory was produced.
This is a prospective identification-design failure, not a runtime,
deployment, restart, raw-corruption, reporting, plant-control, or MPC
failure. T13S4 may not be relabelled as a real holdout result.

## 2. Exact revision and server evidence

```text
local branch
  codex/stage4_2r3c3t13s1-transition-sentinel

frozen design commit
  5c14577
initial implementation commit
  1762862
validated preflight package checkpoint
  586cc8a
offline aggregation hotfixes
  ec5410b, 21df2dc08057759dce813bb6e4ec25c95e442e3e

package revision
  r42r3c3t13s4_lattice_transition_holdout_v1h2
campaign identity
  quantized_lattice_two_step_blind_holdout_v1
controller revision
  quantized_lattice_transition_probe_v42r3c3t13s4_v1
```

Remote paths:

```text
staging
  /home/yangshen0711/tsc_software/
  stage4_2r3c3t13s4_lattice_holdout_21df2dc

installed project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

offline run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s4_runs/
  stage4_2r3c3t13s4_lattice_transition_holdout_20260801_21df2dc

offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/
  stage4_2r3c3t13s4_offline_21df2dc.log
```

Load-bearing hashes:

```text
offline lattice audit
  1e60d04dfc7a9b5a26558aff9bee3cfd40ece0f1deed95988b592b0af8a8e6d2
state
  cb35c89129ce1a01be4f34c7b2aac08f900146f5585db8b07f45b4fb61da684d
manifest
  7fdc0a6f705e99d22f60e9a54f05059de61ea79312d0824297eb372871604ca2
offline log
  4aa8995722b3f1a0ebbc08cf1394cfaa835342d5a247b53557574f0c329d757d
installed validation log
  1bbc3aa354e0b6ed2f611c4633af675d3705965f8e020773781cb3f9f870d01b
config
  e30e99743758f41c87d3429599e962af68bbe73e1aa5f993dbee7250c37a5a63
implementation module
  46d2280873d688258070b003d2569674a6b44541c8b64d0535d2cfb82e626bbe
PACKAGE_MANIFEST.json
  ead15c895d8266b5f02b8ddd1185410a3fd83129e0220f498f0ae7f27147861b
SHA256SUMS
  813530ec8799b5e190616709c796ed21f81f865497e304b0e924bee9df14d54d
```

The compact offline audit was copied directly and uncompressed to
`docs/codex/audits/stage4_2r3c3t13s4_offline_20260801_21df2dc`. There is no
large raw tree to download.

## 3. Forensic separation

| Class | Result | Conclusion |
|---|---:|---|
| runtime/environment | 0 | no TSC runtime was entered |
| packaging/import/deployment | 0 | staging and installed packages verified |
| raw/snapshot corruption | not applicable | raw count is zero; source snapshots were only read |
| statistics/reporting | 2 preflight aggregation defects, repaired | first issue failure and then inverse failure originally escaped before state/audit finalization |
| identification design | FAIL | frozen lattice cannot satisfy all prospective action/field gates |
| plant restart | not tested anew | no plant load or step occurred |
| real closed-loop control/MPC | not tested | no controller trajectory occurred |

The `v1h1` and `v1h2` changes only aggregate already-frozen issue and
cancellation failures and write a terminal offline state. They did not alter
the action selector, thresholds, context matrix, formal timing, physical
schedule, or experiment identity. Each repaired attempt used a fresh zero-raw
run directory.

## 4. Exact design conflict

All 40 issue failures used the first allowed multiplier with at least four
local Card15 steps on every significant coil. Their metrics were:

```text
incremental normalized action Linf        0.264604 .. 0.403766  > 0.25
coil-space cosine                         0.999938 .. 0.999977 >= 0.98
relative off-mode residual                0.006751 .. 0.011171 <= 0.15
total normalized action                   0.277779 .. 0.840279 <= 1.0
predicted current utilization             0.371900 .. 0.389900 <= 0.55
current bounds                                                40/40
exact issue target symmetry                                   30/40
```

All p5 signed probes and all p9 mode-0/mode-2 probes failed at issue. The
ten non-exact issue cases also demonstrate a Card15 exponent/rounding
boundary; the action conflict alone already vetoes all 40.

Seven of the eight p9 mode-1 signed probes completed the full issue/cancel
preflight. The remaining development transport negative-sign case passed
the issue gate but its negative displacement was not exactly representable
around the next Card15 center. Its cancellation action magnitude and current
bounds passed; exact field inversion failed.

These are genuine conflicts in the preregistered discrete action design.
Changing four steps to a smaller number under T13S4 would be a post-result
gate change and is forbidden.

## 5. Validation actually run

```text
local focused tests                                  10/10 PASS
local compile / all JSON / checksums                    PASS
staging focused tests                                10/10 PASS
staging complete Linux tests                        664/664 PASS, 1 skip
installed focused tests                              10/10 PASS
installed complete Linux tests                      664/664 PASS, 1 skip
staging/package checksums                            292/292 PASS
shell syntax and isolated import/package checks          PASS
offline specification audit                           52/52
raw / plant / TSC steps                                0/0/0
```

Two SSH-timeout commands left only two exact read-only `grep` shells. Their
PIDs and complete command lines were verified before they were stopped. No
Python, Ray, `gotsc`, or TSC process was broadly terminated.

## 6. Frozen conclusion and next action

T13S4 is final as a pre-execution design FAIL. It neither invalidates the
T13S3 actuator/tube interface nor supplies a plant model. Its planned 52
probe trajectories remain unrun, and no T13S4 data can enter an expert
dataset.

A separate zero-TSC route audit showed that a new lattice-native design can
retain all action/current bounds without changing T13S4: split physical mode
0 into a non-coil-8 component and a separately scaled coil-8 component,
retain modes 1 and 2, and use a causal return-first hybrid cancellation.
That new identity is frozen prospectively as T13S5. It still requires real
TSC holdout validation before any offline robust MPC prototype.

Formal timing and all tolerances are unchanged. Real MPC, expert data, BC,
DAgger, and bounded residual RL remain blocked.
