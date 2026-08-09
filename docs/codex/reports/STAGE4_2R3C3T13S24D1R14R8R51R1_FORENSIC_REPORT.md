# Stage4.2R3c3T13S24D1R14R8R51R1 forensic report

Date: 2026-08-10 Asia/Shanghai

Final route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_COMPLETE_R51R2_MODEL_PREFLIGHT_REQUIRED
```

This route is the result of a reporting-only dual audit of immutable real raw.
The original primary, original independent, stage state, controller, and all
208 raw files remain byte-identical.

## 1. Frozen identity and checkpoints

```text
R51R1/R51R2 design checkpoint                       ce66bb7
R51R1 implementation checkpoint                     bbb83b3
R51R1 executed package checkpoint                    1baf670
reporting-hotfix contract/implementation checkpoint  1dc42f8
reporting-hotfix package checkpoint                  c5a1311
```

The prospective R51R1 design SHA-256 is
`9f8b68063c69e7ff973e0a8aae4e5cdfc0274340b3d7303fc109b5ed01ec4e76`.
The reporting-hotfix contract was frozen after the original failure and its
ULP-only cause were known, but before any corrected hotfix output was
produced; its SHA-256 is
`862f2a7646736d26e0a228e0fbafa9a2dc0abc4516912de120c147af2e1cae81`.

Executed run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r51r1_runs/
stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel_20260809_1baf670_v1
```

Executed package/source identity:

```text
package fingerprint
  d1d8aa2acde5b7013b2e87a0cdee1a05bde209e3f6435d2970aba377170b46ae
executed package manifest
  cd210e76f2b0acdebb1128740fc345995ffd0a88f04dc46f6488c89370898d7e
executed SHA256SUMS
  4e1a23afa0ecb7b49d505289b6900130a516026e2eb7fc4c2247b384df2cdd39
config
  a40569191b5d4fc3f8b2663e52f188ed0cf3f211280574d1889750ae6d516c4f
controller/primary module
  cfb026f5547ea98d3af0edb9b459e50c1b2826f51ab88b048e8f57af3ce2ccb0
original independent module
  a60bd077e4c4774e44385a1fcc335d11c8b6c4d50f8f662e5c0465661953b1d2
stage manifest
  c58148f603913c70d5e35626f72dc3541892ad4ec2a919db139a45b51feaa076
```

## 2. Packaging and validation

The original R51R1 source/package passed local project-venv compile, focused
`12/12`, and Windows-shimmed full `1565/1565`, then fresh empty-copy and
server staging/installed validation. A first direct-copy staging attempt had
Windows CRLF bytes in `SHA256SUMS`; Linux checksum verification stopped before
code or tests. Canonical LF bytes were transferred directly under a new
staging identity and passed. No plant process was started by that packaging
format error.

The reporting hotfix passed:

```text
local source focused                                      6/6
local source Windows-shimmed full                     1571/1571
fresh empty-copy declared hashes                       1260/1260
fresh empty-copy physical files                        1262
fresh empty-copy strict JSON                           150
fresh empty-copy Python compile                        494
fresh empty-copy focused                                18/18
fresh empty-copy Windows-shimmed full                 1571/1571
server staging declared hashes                         1260/1260
server staging Python compile / bash -n                494 / 456
server staging focused / full                          18/18 / 1571/1571
server installed declared hashes                       1260/1260
server installed Python compile / bash -n              494 / 456
server installed focused / full                        18/18 / 1571/1571
```

The isolated empty/server suites had one expected skip. Transfer was direct
`scp -r`; no local archive was created or extracted. Local and server work
used only their existing project/server virtual environments. The hotfix
package manifest/SHA256SUMS hashes are:

```text
0d0f263a1dd7e793d55a0e1ac85e4f6cb11470920cd6dc1de0dce4370d49feac
54d768f88f162f59f4e3f0df3ed92885ea91ea624031ca4332d5694e2e776f84
```

## 3. Offline and real execution

Primary and independent offline construction passed and agreed exactly on all
208 fixed cells. The single authorized real R51R1 campaign then completed:

```text
strict raw / runtime success / full horizon             208/208
authentic restart                                        208/208
source prefix states / trace / wrapper-only differences 208/208 each
calibration / forbidden-input gate                       208/208
exact q0 event / offline parity                          208/208
within-context q0 prefix                                 208/208
candidate/event/issue+1 effect/finite response/return    208/208 each
maximum current utilization                              0.3924
runtime failures / safety stops / forbidden traces       0 / 0 / 0
plant steps                                               7488
```

Raw inventory:

```text
count  208
bytes  6,692,740
digest 0ce9ac9211c00b403f0ef7235cfde81a1e42751fa230d245cd2dc396fc3e3d33
```

All trajectories are strict, successful, full-horizon authentic TSC
trajectories. The response and prefix digests are:

```text
response 819aedc050f52372f2945ed14a7dd81e29a3d7a8bd26802a8599a5052e5cee0a
prefix   10df05337d3d0d862880e40a05a4c1521bf211feee2132fd78c131a509273331
```

## 4. Original reporting failure

The original primary and original independent both reported only `39/208`
for `q0_first_effect_at_issue_plus_one` and selected the execution-failure
route. Their hashes are:

```text
original raw primary
  925dbed532e4dcda721592fe409158c7defd89636d94affef9157646df5981a1
original raw independent
  bd7f4a35fbb011abfe282e386080967449f6695486954f2614f4957a12908a4b
original stage state
  3ba2068fdeae0e4a508e648381a080d49c35c933c9f37c76f1b1fb8e4ac34b54
```

The only false row field was the q0 first-effect field. State-11 applied
action equaled task-step-10 trace action `208/208`; state-10 applied action
equaled task-step-9 trace action `208/208`; state-11 physical current equaled
state-10 current exactly `208/208`. The audit nevertheless compared the
state-11 current to a binary64-reconstructed nominal readback with
`numpy.array_equal`.

Only three contexts happened to reconstruct byte-identical values, producing
`3 contexts x 13 candidates = 39`. Across all 2,912 coil components the
maximum discrepancy was `2.842170943040401e-14 A`. This is binary64
reconstruction roundoff, not a Card15, action, actuator, plant, restart,
causality, runtime, raw, or controller failure.

## 5. Reporting-only correction and independent result

The executed package had already frozen numerical metric equivalence at
`rtol=0`, `atol=1e-12`. The repair retained exact action comparisons and
changed only the reconstructed-current reporting comparison to that existing
absolute tolerance. Primary used NumPy; independent used scalar
`math.isclose` without calling the primary calculation.

```text
original binary-exact count                              39/208
corrected current numerical equivalence                 208/208
state-11 action exact                                    208/208
state-10 prior action exact                              208/208
state-11 current unchanged exact                        208/208
maximum current difference              2.842170943040401e-14 A
bridge coverage                                         208/208
primary/independent inventory/row/numeric/route agreement exact
new TSC / new raw / plant steps by hotfix                 0 / 0 / 0
```

Accepted artifact hashes:

```text
hotfix primary
  fe7edca96abbbb204216c61a92a40e2ffbded762c9c153804deef7e53bc9d151
hotfix independent
  b5c2f4d0acf23ef9d3874c2404bbb0495541e75f1903ef51bf5f407b2fc7a02b
hotfix compact audit
  4f3d922d1f855e5ebe12b96bb844e8d4538296e41ad535d96adfeb997f12641d
hotfix final report
  38b87b3e4ffd082b018944f12e36c4b2bcd70c900e09007e816a357c2c9e7efd
row digest
  25f63d64a8a41e72e516635de1ee795a0f9cb526adf03d135eb02ba4fe40b9a2
```

The original reports and state were deliberately not rewritten. The new
final artifact is the authoritative correction while preserving the exact
history of the reporting error.

## 6. Classification and successor boundary

R51R1 is a finite q0-to-first-transport identification-integrity PASS. The
old failure route was a summary/statistics reporting bug. It was not a
runtime/environment error, deployment error, raw/snapshot corruption,
restart or causality failure, controller/action-design failure, safety stop,
real MPC result, formal-control PASS, plant-reachability conclusion, or Gate A.

R51R1 must not rerun. Every R51/R51R1 trajectory is an identification probe
and remains forbidden from expert, BC, DAgger, residual-RL, or any other
learning data.

R51R2 was frozen at checkpoint `ce66bb7`, before R51R1 implementation or
response inspection:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R51R2_REDUCED_Q0_TRANSPORT_BRIDGE_WHOLE_PAIR_CAUSAL_MODEL_PREFLIGHT_DESIGN.md
SHA-256
8955235246fb79bc7e855abde79b32e0269f24774e1452bf380e77966eeab095
```

The corrected R51R1 route authorizes only that zero-new-TSC whole-pair causal
model/tube preflight. Gate A, expert data, BC, DAgger, residual RL, and Gate B
remain blocked.
