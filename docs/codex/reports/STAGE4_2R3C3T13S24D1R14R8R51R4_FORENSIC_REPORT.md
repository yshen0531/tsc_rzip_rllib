# Stage4.2R3c3T13S24D1R14R8R51R4 forensic report

Date: 2026-08-10 Asia/Shanghai

Final route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_INSUFFICIENT_LONGER_SEQUENTIAL_REDESIGN_REQUIRED
```

R51R4 is a clean, authentic 100-trajectory development-envelope response
campaign and a scientific FAIL for its frozen single-transport sustained-
dwell/exact-return family. The original raw reports contained a reporting
bug in binary64 nominal-current equality. The separately frozen zero-new-TSC
repair restored raw integrity but did not change any action, physical state,
formal metric, or scientific gate.

## 1. Checkpoints and immutable run

```text
R51R4 design / implementation / authentication hotfix / accepted run package
b4fd256 / 938dbad / aba76c1 / 7b394cb

reporting-hotfix contract / implementation / package
4059e98 / 0a1d062 / 7be4a30

next longer-sequential design frozen before per-row result inspection
e1ddc9e
```

Canonical server run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r51r4_runs/
stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel_20260810_7b394cb_v2
```

The correction was written only as new
`current_equivalence_reporting_hotfix_` artifacts inside the existing stage
directory. Original raw, original primary/independent reports, stage state,
stage manifest, offline reports, controller source, and logs were not
overwritten.

Load-bearing immutable hashes are:

```text
executed config
6fb1c69b473a79d3889fe1dc725a564aeb256e45331f98b1834ccc4debeb4802
executed controller and original primary raw audit
32a433addb3890e17dec2888cfc2840c634490f105c1b56ad179f8ece404cdaf
original independent raw audit
10df4afe6bdf373f7aa47f5b5c8661ae9e1f805a818418fa64ddc50cfbae3314
original stage state
59c914a6e772c5b8333a62060ca2fec862736949c15077ee925fe200b90617d9
raw inventory, 100 files / 3,255,079 bytes
9227c93aae7a1819949bee9a57f9294c9b0f01620bcbbe193e32ca6823a15f3a
```

The original state hash was rechecked before deployment, after installation,
after both corrected raw audits, and after formal finalization. It remained
byte-identical.

## 2. Reporting repair and validation

The frozen repair changed only a comparison between real TSC current and a
nominal current reconstructed through binary64 arithmetic:

```text
old: binary array equality
new: finite, rtol = 0, atol = 1e-12 A
```

Exact equality remained mandatory for Card15 fields, actions, event names and
order, action effects, zero dwell increments, physical candidate-current
preservation, stored-center return, post-return center, raw identity, and
forbidden-input gates. Primary used NumPy; independent used scalar Python and
`math.isclose` without calling the primary measurement implementation.

Implementation hashes:

```text
primary reporting hotfix
3b57bdd9546a8a1127615c521ffd8d52f81416b1998a8c697a08033dd5a80c44
independent reporting hotfix
d408c34772ed2b99f66e3bbd6d68f0addf8e02db36f239a7739a4a914adaa747
launcher
31153007a2676dd0afaf61460151a000784fec7d2751d25944351faa08f7bd51
focused regression test
cb7641c9736a18ee36057a29d5ee618f319d83d6bac18c2fc5ffbff314f078b7
```

Local project-venv validation passed Python compilation, focused `19/19`, and
Windows-shimmed full `1608/1608`. A fresh empty direct-copy tree contained
1,284 declared and 1,286 physical files, with 1,284 hashes, 153 strict JSON,
506 Python compilations, focused `19/19`, and full `1608/1608` with one
expected isolated-package skip.

The package was transferred directly with `scp -r`; no local or remote archive
was created or extracted. Server staging and installed validation each passed:

```text
declared hashes     1284/1284
strict JSON           153/153
Python compile        506/506
bash -n               459/459
focused unittest        19/19
full unittest         1608/1608, one expected skip
```

The installed package hashes were:

```text
PACKAGE_MANIFEST.json
3638858f75ed57b3f228460266dc8d1823fe89662a016387a9802f72195a3e6d
SHA256SUMS
aae4d919722a61ac6f374b1255ac583c414a110376dca98daa87e9289d3d16f5
```

One first staging-validation wrapper stopped after successful `sha256sum -c`
because it searched for the substring `FAILED` and matched the legitimate
filename `...FAILED_CONTEXT...DESIGN.md: OK`. The corrected wrapper used the
checksum command's exit status and an end-anchored `: FAILED` predicate. This
was a validation-command reporting error, not a package/hash failure.

## 3. Authentic execution and corrected raw integrity

The already completed real campaign contained:

```text
controller executions       100
new authentic TSC raw       100
plant steps               3,620
strict full horizons        100/100
runtime/safety/forbidden failures 0/0/0
maximum current utilization 0.3924
```

The hotfix itself ran zero Ray, `gotsc`, TSC, controller, plant step, raw
generation, snapshot, optimization, model fit, or model selection.

Primary and scalar independent raw replay agreed on:

```text
semantic rows                                  100/100
q0 numerical-current equivalence               100/100
all event numerical-current equivalence      2,620/2,620
event action-detail trace exact              2,620/2,620
event next-state action effect exact         2,620/2,620
dwell zero increment exact                     400/400
dwell physical current unchanged exact         400/400
stored-center physical return exact            100/100
post-return physical center exact            1,820/1,820
maximum nominal-current difference   2.842170943040401e-14 A
```

For comparison, the invalid original binary predicates counted only `20/100`
q0 rows, `4/100` dwell rows, and `0/100` full byte-digest parity. The physical
actions and currents were exact; only nominal binary64 reconstruction differed.
Corrected raw primary and independent both selected:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_RAW_INTEGRITY_REPORTING_HOTFIX_COMPLETE_FORMAL_REQUIRED
```

Formal outcomes stayed unopened until both corrected raw audits passed and
agreed.

## 4. Formal result

The unchanged 30 mm R/Z, 0.1 m/s, 10 kA Ip, three-sample arrival streak,
250/270 ms arrival, and 350/370 ms hold evaluator produced 110 formal rows:
ten matching failed R8R7 baselines and 100 R51R4 candidates.

```text
failed-context baseline passes                           0/10
R51R4 candidate formal passes                           0/100
return-step-16 candidate passes                          0/50
return-step-18 candidate passes                          0/50
passes for each d0m/d1p/d2m/d3p/u1p50 candidate         0/20
failed baselines with a strict best-margin improvement 10/10
failed baselines repaired                                0/10
known all-context baseline oracle                        6/16
baseline-plus-measured R51R4 oracle                      6/16
```

Best per-context minimum-margin gains were positive but too small:

```text
minimum  0.00047969843635597975
median   0.002146486119223967
maximum  0.00853142717862454
```

Every row's best candidate used the longer return step 18:

| physical pair | history | best candidate | gain |
|---|---|---:|---:|
| p5_q1_a0p750_gap4_settle4 | minus | d3p | 0.0023254667 |
| p5_q1_a0p750_gap4_settle4 | plus | d3p | 0.0027882000 |
| p5_q1_a0p900_gap3_settle4 | minus | d0m | 0.0004796984 |
| p5_q1_a0p900_gap3_settle4 | plus | u1p50 | 0.0019675056 |
| p5_q2_a0p750_gap3_settle4 | minus | d2m | 0.0085314272 |
| p5_q2_a0p750_gap3_settle4 | plus | d1p | 0.0004813133 |
| p5_q2_a0p900_gap4_settle4 | minus | u1p50 | 0.0018147047 |
| p5_q2_a0p900_gap4_settle4 | plus | u1p50 | 0.0016626532 |
| p9_q2_a0p750_gap3_settle4 | minus | d3p | 0.0023640667 |
| p9_q2_a0p750_gap3_settle4 | plus | d3p | 0.0025973333 |

The structurally independent formal audit reproduced every discrete outcome,
the final route, repair count, and oracle count. Its maximum numerical
difference from primary was `4.440892098500626e-16`.

## 5. Classification and active route

The corrected final audit is an integrity PASS and scientific FAIL. It is a
genuine finite action-family/controller-design result: the tested single
transport, sustained dwell, and exact return sequence did not provide enough
formal authority. It is not a runtime, deployment, restart, causality,
Card15, safety, raw-corruption, reporting, solver, saturation, or formal-
evaluator failure. It does not establish global plant unreachability.

Conditional R51R5 required at least one repair and an oracle of at least
`7/16`; therefore R51R5 remains blocked and unrun. Before per-row outcomes
were inspected, R51R4D1 was frozen as a zero-new-TSC exact two-transport
schedule/coverage preflight:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R51R4D1_TWO_TRANSPORT_EXACT_RETURN_SCHEDULE_PREFLIGHT_DESIGN.md
ccc279be94ac230b86ebea80b07572fe057aab2110657989a261d37cd6988645
```

R51R4D1 is the active task. Gate A, expert data, BC, DAgger, residual RL, and
Gate B remain blocked. Every R51R4 trajectory is probe data forbidden from
learning.

## 6. Compact evidence

Downloaded compact JSON is under:

```text
artifacts/server_audits/r51r4_reporting_hotfix_20260810_7be4a30_v1/
```

Key server artifact hashes are:

```text
raw compact
c84f7e859389e427808e222fc871ca6ed1429ab0cbf6145c3617d2c62b62cab8
formal primary summary
c59e6b245f2c2e1697585b431b659bcf97c79a5ca6d5921e36dfe4503642b2e3
formal independent
79503d77d6e79a8d6dca093695ecbf6daec02aee6a682f5fea7ceba160d2a08e
compact audit
622b5ba2bd6c97a9363a179f7f2683297ae4462206c26863a3dd3ff9f73464fd
final report
50a4221f72ba5dc65ead17fdc8a5d43d170585bb7f11f734d51eeb195e8a84d8
server evidence
9dcd9636a2d18a52fde6be2db951d189a6af5cde1af8b7df8e3f37d5b058330a
```
