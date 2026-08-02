# Stage4.2R3c3T13S15 final forensic report

## Outcome

Stage4.2R3c3T13S15 is frozen as:

```text
FIXED_BASIS_LOCAL_IDENTIFICATION_FAIL_REDESIGN
```

This is a pre-action identification-design failure. It is not a TSC runtime,
plant-restart, raw-corruption, statistics/reporting, or closed-loop control
failure. The response phase was never opened.

## Exact execution identity

```text
local implementation commit
  ca9344e Implement S15 fixed-basis local identification

package revision
  r42r3c3t13s15_fixed_basis_local_identification_v1

package digest recorded by the run
  99fdf4ea93685fcfc48a833ee3947e3dc22d100c38c7c82c8507b6de21ab16b6

SHA256SUMS
  d664c237b7ff0ade9b8f5024e2e91c2a408b93549c84f6c724d7739d369ea640

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s15_runs/
  stage4_2r3c3t13s15_fixed_basis_local_identification_20260802_161127

remote nohup log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s15_fixed_basis_local_identification_20260802_161532.log
```

The installed package contained 352 declared files. Server verification
passed every package hash, shell syntax, JSON parse, Python compile/import,
the 9 focused S15 tests, and the complete 781-test suite with one expected
skip. The full-test log is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/validation/
stage4_2r3c3t13s15_full_unittest_ca9344e_20260802.log
```

## Expected versus actual execution

The prospective matrix was 16 baselines followed, only after the baseline
gate, by 128 response probes. Offline preflight produced zero raw and passed.
The baseline invocation submitted all 16 baseline task functions at the
frozen Ray capacity of 128 workers.

Every task stopped inside the controller's first call, while constructing the
frozen physical field basis:

```text
expected baseline tasks                                  16
completed task functions                                 16
structured failure raw                                   16
successful TSC trajectories                               0
trajectory records                                        0
controller-trace records                                   0
environment step calls / plant advances                    0
response tasks opened                                      0
```

All 16 compressed raw files parse. They contain
`success=false`, `completed=true`, empty `trajectory` and
`controller_trace`, and the same caught exception:

```text
ValueError('T13S15 frozen physical basis failed rank/condition gate')
```

The raw inventory is 16 files and 54,386 bytes. Its canonical
`name size sha256` inventory digest is:

```text
02ff951b4dd99b4f53d74cb0689e94a182d5bede07c8e19ac32ea0442dc3dcde
```

## Independent pre-action recomputation

A server-side source-exact diagnostic reconstructed every controller from the
authenticated snapshot and called only the first controller action. It did
not call `env.step`. The result is:

```text
physical field-basis rank four                           16 / 16
condition <= preregistered 3.0                            0 / 16
minimum normalized condition                    4.1405792773
maximum normalized condition                    4.1409174542
plant advances                                             0
real TSC trajectory execution                              no
```

The two observed singular-value sets are approximately:

```text
[1.333733, 1.059784, 0.997125, 0.322113]
[1.333903, 1.059815, 0.996860, 0.322127]
```

The forensic JSON SHA-256 is:

```text
462960f746a9afdbedd584bf46097b4fa23f18a8cc2054146a5bbc909c88bca9
```

Other load-bearing hashes are:

```text
manifest             bdd596ea31fddcde80b2d5dabe940bc0e1bd4620b8c247475513dcbd4dd20d87
offline preflight     e0e5de43cd3512cef6bf65ad51e3c624f1dd75c9d802120dfafc2d12d6b19e7f
baseline gate         fd7eab5d5a15f57e84f4067fe92859695ad38b23d80e2b23e65027c67c5fcd1d
state                 37cc49937fe32c21c048cee3c31b2f81e581f1400729715e0bfaa3c9078c2666
nohup log             741ecd4425b44833093ad5681f674d6bb2a72adc73e4d75300fcdaff6c5e14cc
```

## Error classification

```text
runtime/environment error                 no
packaging/import/deployment error         no
raw/snapshot corruption                   no
statistics/reporting error                no
test not run                              no for required S15 validation
identification-design failure             yes
real plant-restart conclusion             none; no plant advance
real closed-loop control conclusion       none; no trajectory
```

The threshold cannot be relaxed after observing the result. S15 remains a
failed immutable identity, and its 16 structured failures are not resumable
as successful baselines.

## Prospective successor

A zero-TSC development preflight showed that a deterministic physical-field
QR basis spanning the same four native directions can remove the geometric
redundancy without relaxing S15. With the fourth orthogonal direction scaled
by 0.6 for the unchanged action envelope, all 16 development contexts passed
the pre-action feasibility checks:

```text
rank four / exact positive-negative actions              16 / 16
normalized condition                              1.0245902744
maximum native-direction projection residual       0.0623880135
minimum native-direction projection cosine          0.9980519705
maximum incremental normalized action               0.2157091024
maximum current utilization                          0.3940000000
plant advances                                                   0
```

This is design evidence only. It neither repairs S15 nor validates a response
model. The new identity is frozen separately as Stage4.2R3c3T13S16.

