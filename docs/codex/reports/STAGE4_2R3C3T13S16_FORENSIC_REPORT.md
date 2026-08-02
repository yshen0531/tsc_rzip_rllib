# Stage4.2R3c3T13S16 final forensic report

## Outcome

Stage4.2R3c3T13S16 is frozen as:

```text
ORTHOGONAL_FIXED_BASIS_IDENTIFICATION_FAIL_BELIEF_MPC_REDESIGN
```

The deterministic QR excitation repaired S15's pre-action geometry and the
complete 144-trajectory authentic campaign executed correctly.  The failed
object is the frozen point-estimator plus provisional residual tube.  This is
an identification/model and uncertainty-set design failure, not a runtime,
deployment, restart, causality, raw-corruption, statistics/reporting, real-MPC,
or global plant-reachability failure.

## Exact execution identity

```text
local design commit
  8118d9a Freeze S15 failure and S16 orthogonal basis

local implementation commit
  8487951 Implement S16 orthogonal fixed-basis sentinel

package revision
  r42r3c3t13s16_orthogonal_fixed_basis_identification_v1

package digest recorded by the run
  9437a6b09945da5ee843def84b614ce8f7f81d1082e02ed18a629add6e70f461

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s16_runs/
  stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_165232

baseline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_165521.log

response log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_170802.log
```

The package declared and verified 367 source files.  Server shell syntax,
package verification, import, compile, and the 10 focused tests passed.  The
installed complete suite passed 791/791 with one expected skip.  Its log is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/validation/
stage4_2r3c3t13s16_full_unittest_8487951_20260802.log
SHA-256 e3ec76b44578fa44632f91d050e1067fadf1d1b36ee156e086ec04f1947234a7
```

The local complete discovery ran 768 tests: 767 passed and one collection
failed only because the local interpreter lacks `gymnasium`.  The isolated
empty-package S16 suite passed 10/10; the server environment ran the complete
suite and therefore closes that local environment limitation.

## Pre-action and phase gates

The mandatory no-plant preflight called the real controller action interface
in every context without calling `env.step`.  It passed 16/16:

```text
physical basis rank                                            4
normalized condition                               1.0245902744
minimum native projection cosine                   0.9980519705
maximum native projection residual                 0.0623880135
maximum incremental normalized action              0.2157091024
maximum current utilization                         0.3940000000
raw / plant advances / real TSC                          0 / 0 / no
```

The 16 baselines then passed the frozen execution, restart, causality,
Card15, zero-net, current, local-design, and native-response-lattice gates.
Only then were the 128 response probes opened.

## Complete raw and independent recomputation

```text
expected / actual raw                                   144 / 144
strictly parsed raw                                      144 / 144
raw bytes                                                8,188,964
raw inventory digest
  b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668
runtime or environment errors                                    0
restart-fidelity failures                                        0
controller-causality failures                                    0
actuator or exact-zero-net failures                              0
statistics or reporting errors                                   0
calibration pulse pairs / trace events                   576 / 1,152
zero-net groups / response trace events                    704 / 256
```

The independent server postprocessor parsed every raw JSON.GZ, recomputed
the event counts and all reported gate totals, and matched the saved final
report exactly.  Large raw, payload, environment-variant, and snapshot
evidence remains immutable on the server; only compact identities are
recorded locally.

## Frozen model result

Every response had a full-rank, supported, causal local fit:

```text
rank-seven design / response projection                 128 / 128
maximum local design condition                         2.529381
maximum fixed-basis condition                       1.0245902744
center error <= 0.10                                    120 / 128
tube containment                                         82 / 128
tube cap                                                  40 / 128
all model gates jointly                                  14 / 128
maximum scaled center error                       0.2134489601
```

The center misses are localized to four signed rows in each of the two
histories for the `p5_q2_a0p600_gap2_settle4` context.  The broader failure is
the provisional componentwise tube:

```text
component                         R          Z         vR         vZ        Ip
maximum tube                 0.000431   0.000373   0.026748   0.029738    85.318
median tube                  0.000333   0.000128   0.008506   0.017505    43.429
tube-cap exceed rows                 0          0         48         88         0
containment-failure rows             2         12         22          4        26
maximum absolute error        0.000269   0.000273   0.009829   0.021345    72.814
```

Thus QR conditioning and point prediction improved materially, but a single
`3 * maximum regression residual` box is simultaneously too broad in the
velocity components and still not a valid response set for all outputs.  It
cannot be made successful by changing the multiplier or caps after seeing
the result.

## Evidence hashes

```text
pre-action basis preflight
  e9c89bbae2d929ec3d2fbad493c2ceac20d1094a0a793cee97001e3ad4c711fc
offline preflight
  c85dbd677c516ea4747c84b3b0433c8afda9598692c710ecfc6d19dd51568c43
baseline gate
  d39a62bd71871693d5e9ee034a8213b41f3719a6f8882d34fce029c8932dc378
probe execution
  4321414bbaa97fbba1bfe6990d094770603ff78736df4055dee62df224abeea1
frozen local estimators
  e0b5e96ccb7c6ec9eab1b2dc00ad36d43c28d9bf11155ad8638f265cc2ccac24
final model audit
  2184e326078a45cfb72868b3cfb791815f38662d1631d1c4fbecebb4c56764a4
final result
  c7da6d257bc361c8cdfa3a0da9af7a353172d2c73ed258147f4fce99f50a0ed6
independent postprocess
  dbe9ea6050cfaf71501bda0afb0077028719fe76df407282270986533bc4e231
run manifest
  088a8b7c8f6c63e44414d143b636abc3b7bd110829cab5c653a3560c5b888c83
state
  07e79d3b8d622de264c22cb59fe22e0dc043c8886cf0375798f01a00eda03ffd
baseline / response logs
  a680bc19802d202ef74058b753b074a2a10b26ce087508dec06dc9f005a8d353
  95c979c2a4b09d54272261443578c97a1be8c6d31bddd85115211343f9ee89d6
```

## Error classification and frozen scope

```text
runtime/environment error                              no
packaging/import/deployment error                      no
raw/snapshot corruption                                no
statistics/reporting error                             no
test not run                                           no for server requirements
identification/model or tube design failure            yes
real plant restart failure                             no; exact 144/144
real closed-loop MPC conclusion                        none; no MPC ran
```

Formal tracking is diagnostic for these probes and does not change the
250/270 ms arrival or 350/370 ms hold contract.  S16 identifies only this
finite clean development envelope.  It does not validate independent hidden
histories, unseen targets, continuous parameters, plant/model mismatch,
measurement noise, disturbance recovery, or long hold.  Its trajectories are
forbidden from expert datasets.

## Next route

The S16 FAIL route requires a causal plant-state belief before robust
finite-horizon MPC.  The separately frozen S17 preflight therefore uses only
causally available same-trajectory calibration and settling observations to
construct a fixed multi-hypothesis response set.  It runs zero new TSC and
cannot itself authorize a controller or expert data.  Only a complete S17
development pass may authorize a separately preregistered fresh whole-pair
identification campaign.

