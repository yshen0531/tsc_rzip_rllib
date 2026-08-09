# Stage4.2R3c3T13S24D1R14R8R51R2 forensic report

Date: 2026-08-10 Asia/Shanghai

Final route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_WHOLE_PAIR_CAUSAL_MODEL_COMPLETE_CONTROLLER_PREFLIGHT_REQUIRED
```

R51R2 is a zero-new-TSC, fixed-model, whole-physical-pair validation PASS.
It certifies only the finite state-12 q0-to-state-13/state-14 response model
and its training-only tube. It is not a controller, MPC, formal-control, or
Gate A result.

## 1. Frozen identity and checkpoints

```text
prospective R51R2 design checkpoint                         ce66bb7
R51R2 implementation checkpoint                             eedf15e
initial package checkpoint                                  b0aeca1
source-authentication path repair checkpoint                 4863644
accepted package checkpoint                                  2e96b75
```

The prospective design SHA-256 is
`8955235246fb79bc7e855abde79b32e0269f24774e1452bf380e77966eeab095`.
It was frozen before R51R1 implementation or response inspection.

Accepted run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r51r2_runs/
stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight_20260810_2e96b75_v2
```

Accepted package hashes:

```text
PACKAGE_MANIFEST.json
  2c6d8d3dd269bfd6d3d02432e1644de901322beb496f97f81e77eeb750d86b02
SHA256SUMS
  84393457e63c3d32006b1749e0053382cf01dafd2a7ddc491df34a2ceb58c098
```

## 2. Packaging, validation, and stopped v1 attempt

The source implementation passed local project-venv focused `8/8` and
Windows-shimmed full `1579/1579`. Its first empty direct-copy package and
server staging/installed copies passed 1,265 declared hashes, 1,267 physical
files, 457/479 applicable shell parses, focused `8/8`, and full `1579/1579`,
with one expected isolated-package skip.

The first server invocation stopped during source authentication because both
audit paths named an R51R1 config without its actual `_370ms` suffix. The
actual server source hash matched the expected hash, and the stopped v1 stage
contained zero output files. This was a source-path implementation error
before model construction, not a source mismatch or scientific result.

The repair changed only those two source locators and added a regression test.
Local source and fresh empty-copy focused/full validation passed `9/9` and
`1580/1580`; server staging and installed validation reproduced `9/9` and
`1580/1580`, with one expected skip. Transfer used direct `scp -r`; no local
archive was created or extracted. Both hosts used only their existing virtual
environments.

## 3. Authenticated sources and immutable model

Final server evidence reauthenticated:

```text
R51R1 raw  208 files / 6,692,740 bytes
  0ce9ac9211c00b403f0ef7235cfde81a1e42751fa230d245cd2dc396fc3e3d33
R8R7 baseline raw  16 files / 487,298 bytes
  46df626a462dfdbfe7cdf9138a50b6b19c03f0ae5e8bb18cf18c6fcbe05c01a5
```

All 208 fixed rows were retained. The causal feature had 44 components from
completed visible states/current/readback and previous q0. The fixed 180D
representation was `[q/1.5, vec(whitened_feature outer q/1.5)]`, with no
intercept or feature-only term and fixed ridge `1e-4`. Eight whole-physical-
pair outer folds held out both histories and all 13 candidates. Seven nested
whole-pair fits in each outer fold formed training-only tubes using the frozen
physical floors and multiplier.

Evidence digests:

```text
bank      88a3652baff99795eba2e249d603c3c2e95924d8ecbbefc16df3e8bd3cbb5750
feature   4b835ddbb4b4ccf5610aae8aefcd82c4815cf74d4192f730b3eec30d9ba80ffa
response  46827f4c4961a418069e444e329094a7e88d16140047431f7328337557458f72
fold      042a5545a8a2997fb3426602225308f7136e7f498dfa79d2f62d89147e1536f4
```

## 4. Primary and independent result

```text
strict source / finite response / physical-prefix rows      208/208 each
outer-fold prediction coverage                               208/208
point-error floor gate                                       208/208
training-only nested-tube containment                        208/208
tube-cap passing folds                                           8/8
forbidden model inputs / excluded source rows                    0 / 0
primary-independent maximum numerical difference                  0.0
new TSC / raw / snapshot / controller / plant / selection   0/0/0/0/0/0
```

Maximum absolute physical errors at state 13 then state 14 were:

```text
[1.780870698162285e-05 m, 3.736242752193625e-06 m,
 5.993494138041089 A,     3.862420243622e-05 m,
 7.156778008633018e-06 m, 10.103048139910582 A]
```

Every maximum tube half-width was exactly its physical floor:

```text
[0.015 m, 0.015 m, 3000 A, 0.015 m, 0.015 m, 3000 A]
```

Primary and structurally independent recomputation agreed exactly on all
discrete outcomes, predictions, residuals, tubes, digests, and route.

Accepted artifact hashes:

```text
primary summary          697c8c4141d6a756aed7df372c7d3076d3adf0995d611cab1a95bdf7dcb2fb6f
primary detailed         79a6cfae4f9a45fae2baf6a73be7346ff4c8d1721091914253246319976ce435
independent              927502a402365667b89c0b20ca8a5b97ee0354e9eefd6207bb8df56eefd9e681
compact audit            f444e1a0c2cc43d12f121da8e6b4d8eb118c62474dd7222a611b8bbbb0168cbd
final report             31bf9c3ef346ca107931c3feb23eea9bdf7185cc4250f678df183a4c650ffcaa
stage state              1f3a87c3476f98ae0755f3c60d74201383773aba3edacda4b439663c46c4caac
stage manifest           3979a1a52daa24bc3ea5a043b78acdd4aaf4d065346f1189b95840e1950db45c
bank detailed            477f3301701e6a711475662cc869a82bf87c77862f98d2c15f391422cf033644
source authentication    cf28ef011aae6273f060dfbf9dab1bdf8a77a0ce32c263848f32a2f0fbbe13bd
server final evidence    ffd5fec8376a45c7ce43a4db4e11782331781b9e15f879fecadec2d97c8dc8c8
```

## 5. Classification and successor boundary

The accepted result is a finite local response-model PASS. The stopped v1
attempt was an implementation/source-locator error and produced no model or
scientific outcome. The accepted v2 result has no runtime, deployment, raw,
restart, causality, statistics, reporting, or model-design failure.

R51R2 did not evaluate full-horizon formal tracking and its model ends at
state 14. Therefore its PASS cannot by itself authorize real control. Before
any controller implementation, a separately frozen zero-new-TSC authority
audit must determine whether the 13 already executed single-transport,
exact-return, then-hold trajectories contain any full-horizon formal repair
of the ten failed R8R7 baseline contexts.

No R51/R51R1 trajectory may rerun. Every R8-family trajectory remains a probe
forbidden from expert, BC, DAgger, residual-RL, or other learning data. Gate A
and Gate B remain blocked.
