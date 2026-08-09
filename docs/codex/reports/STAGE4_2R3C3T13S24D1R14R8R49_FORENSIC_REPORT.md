# Stage4.2R3c3T13S24D1R14R8R49 forensic report

## Verdict

R8R49 stopped at its prospectively frozen offline action-construction gate.
Final route:

```text
Q0_TO_TRANSPORT_BRIDGE_SENTINEL_OFFLINE_FAIL_NO_REAL_TSC
```

Primary authenticated every source and constructed 256/256 requested
context/candidate specifications, but only 208/256 passed all exact Card15,
direction, return, action, and current gates. Independent offline
recomputation reproduced the complete construction object exactly. The
failing 48 cells were never authorized for real execution, so R8R49 created
zero raw files and executed zero Ray, `gotsc`, TSC, controller, or plant step.

This is an exact-action/experimental-design failure caused by insufficient
Card15 direction fidelity for three redundant small-amplitude candidates. It
is not a runtime, deployment, source, raw, restart, causality, reporting,
controller, formal-control, real-MPC, plant-reachability, safety, or Gate A
result.

## Frozen identity and implementation history

```text
R8R49 design checkpoint                         8427bfe
design SHA-256
  16f321003e7801ac36a5bc97bdb66928a37f469ffb01b31aa09136c2e4a46173
initial implementation checkpoint               6fd0610
source-locator hotfix checkpoint                 06c7020
R8R48-hash authentication hotfix checkpoint      e76a797
final package checkpoint                         3966426
PACKAGE_MANIFEST.json SHA-256
  5c2a6aab035ef0d12e0f0ff17ad3b942e0c95f94c4260ca913e23fcb34e57579
SHA256SUMS SHA-256
  7627d2a426e8c02464c11d3a0e832be9a2c007389439c0f9c64368b519295906
```

The first source-locator attempt failed before module execution because the
runner called seven nonexistent imported shell-function names. The hotfix
changed only those names to the already exported D1R11 locators. A later
offline attempt authenticated six of seven final R8R48 files and failed
closed because the configured `primary_detailed` SHA-256 had only 63
characters. Direct server hashing identified the omitted `8`; the second
hotfix corrected only this source fingerprint and added a 64-lowercase-hex
config invariant. Neither defect ran TSC or changed a candidate, controller,
physical action, gate, or scientific interpretation. All stopped attempt
directories and logs remain preserved.

## Validation and deployment

The final hotfix passed local project-venv compilation, focused `10/10`, and
Windows-resource-shimmed full `1543/1543`. A newly empty direct-copy package
contained 1,241 files: 1,239 declared files plus manifest and sums. It passed:

```text
declared hashes                                  1239/1239
strict JSON                                             146
Python compilation                                      485
focused tests                                         10/10
full tests                                      1543/1543
expected isolated-package skips                           1
```

A second fresh cache-free tree was transferred with direct `scp -r`; no
archive was created or extracted. Server staging and installed validation
each passed the same gates plus `bash -n` for 454 shell files, using only:

```text
/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python
```

## Exact final server evidence

Run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r49_runs/
stage4_2r3c3t13s24d1r14r8r49_q0_to_transport_causal_bridge_identification_sentinel_20260809_3966426_v2
```

Primary result:

```text
sources authenticated                                  true
specifications                                      256/256
offline construction passes                         208/256
maximum issue increment                  0.2111111111111112
maximum return increment                 0.2111111111111112
maximum predicted current utilization                 0.3912
raw files / plant steps / real TSC                    0 / 0 / false
```

Independent result:

```text
source route authenticated                              true
design authenticated                                    true
primary agreement                                       true
construction digest
  d9ac2bb9e5ad372f37a78a6245ab8908ce4b9d6f30718975d13c215d27e70968
spec digest
  3f277ac282c2d7d05888e602299ab291981517885645ec5013581a097b91a4e5
```

Final server hashes:

```text
offline primary       8258e0369de1b79814efec2e3ec85bd843e37bc387b0d21fa4996e32de68d655
offline independent   d1dec48db8e915d673d2db7a4b5ea95ed316ba838cdc404cbbb2a1ad91c302f9
offline construction  fd112e5fdb1527059003cccf5bd2219e6f0fd175306aafe8edf71a4073a41002
all specs             fb4164bbe109a0994f5fd7c163d19e788be093d8b69e0adc37bbc5389f6f4afc
source authentication 75aeb74cbc70e4bc392dd9b1250c41d2768274bf7845252f7b020c8bcbf6aa9b
stage state           8afbfec8f9ba33cf7763cef8fe7bd06425f5a06890309892f9de251b97790962
stage manifest        a71349895dc20e17fb529bb1842f07d45bf6d1737a072e40420cc1bf90484044
```

Only the four compact primary/independent/state/manifest files were copied
directly to `artifacts/server_audits/r8r49_offline_3966426_v2/`. The 3.36 MB
spec file, 179.6 kB construction detail, 129.7 kB source authentication, and
all source evidence remain on the server.

## Read-only failure classification

The post-result forensic did not change or reinterpret the frozen gate. The
48 failures were exactly three candidates in every one of 16 contexts:

```text
u0p50                                                 16/16 fail
u0p75                                                 16/16 fail
v0p50                                                 16/16 fail
all other 13 nonzero candidates                      208/208 pass
```

For every failed cell, the only failed inner criterion was the unchanged
`relative_off_basis_residual <= 0.10`, at both issue and exact return. All
cosine, exact Card15, action, current, clipping, saturation, identity,
observation, and later-refresh criteria passed. Exact ranges were:

```text
candidate  issue cosine       issue off-basis       return off-basis
u0p50      0.988338--0.988360 0.137722--0.138006    0.137722--0.138006
u0p75      0.989848--0.989857 0.132895--0.133428    0.132895--0.133428
v0p50      0.992784--0.992897 0.104011--0.104611    0.104011--0.104611
```

The compact retrospective classification is recorded at
`docs/codex/audits/stage4_2r3c3t13s24d1r14r8r49_offline_compact_audit_20260809.json`,
SHA-256
`17d78d25e7db51242ee0fdbf51994c269e4e1516ec09a1120b10458144e499ef`.

## Scientific boundary and next route

The frozen 0.10 gate must not be weakened after seeing these values. R8R49
may not be resumed with the three candidates removed, and its real phase is
permanently unauthorized. The conditional R8R50 design requires exact R8R49
PASS, so it is blocked without implementation or execution.

The 13 passing candidates still include all four independent canonical
directions; the rejected small amplitudes are repeated samples of two of
those directions. This development result permits only a new-identity,
prospectively frozen reduced-candidate bridge sentinel with its own offline,
real, and independent gates. It does not permit a model fit, controller, MPC,
Gate A, expert data, BC, DAgger, residual RL, or Gate B. Every R8-family
trajectory remains forbidden from learning.
