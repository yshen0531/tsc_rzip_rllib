# Stage4.2R3c3T13S24D1R14R8R51R3 forensic report

Date: 2026-08-10 Asia/Shanghai

Final route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_SINGLE_TRANSPORT_RETURN_HOLD_AUTHORITY_INSUFFICIENT_SEQUENTIAL_MODEL_REQUIRED
```

R51R3 is a clean zero-new-TSC full-horizon authority FAIL for the 13 already
measured single-transport/exact-return/hold candidates. It is not a runtime,
deployment, raw, restart, action-integrity, reporting, controller, MPC, or
global plant-reachability failure.

## 1. Frozen identity and checkpoints

```text
R51R3 prospective design checkpoint                1a2cb6d
R51R3 implementation checkpoint                    9bdcddb
R51R3 executed package checkpoint                  06e4728
```

Prospective design:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R51R3_SINGLE_TRANSPORT_RETURN_HOLD_FORMAL_AUTHORITY_AUDIT_DESIGN.md
SHA-256
7f65a14032131ef24a8fb3bb337ec33b3485c8a416fc401d034b96ad1cf93e40
```

The design was frozen before any R51R1 candidate formal metric, pass, repair
mapping, or oracle was computed. It disclosed the prior source-structure
inspection of two terminal R/Z/Ip triples without target differencing or
formal evaluation.

Accepted run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r51r3_runs/
stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit_20260810_06e4728_v1
```

## 2. Packaging and validation

The project-venv source and a fresh empty direct-copy package both passed:

```text
declared hashes / physical empty-copy files             1272 / 1274
strict JSON / Python compile                              151 / 500
focused tests                                                   9/9
Windows-shimmed full tests                                  1589/1589
```

Server staging and installed copies reproduced:

```text
declared hashes                                             1272/1272
strict JSON / Python compile                              151 / 500
bash -n                                                        458
focused / full tests                           9/9 / 1589/1589
expected isolated-package/server skip                              1
```

Transfer was direct `scp -r`; no local archive was created or extracted.
Local and server validation used only their existing virtual environments.
Package hashes were:

```text
PACKAGE_MANIFEST.json
  175e15c0061e0d9f690c3ad9955793877be97db95f5e5c7894bbfe1fa5af2750
SHA256SUMS
  084deb1d37699ee0a54c9b85fd38e554fa0cf8c89f9890e3d7457740a0a1158a
```

An initial shell invocation attempted to redirect the primary log beneath a
parent directory that did not yet exist. Redirection failed before the common
launcher or Python started; the intended run path remained absent. Creating
only the allowed stage-root directory and retrying the same frozen identity
produced the accepted result. This was a log-path invocation error with zero
stage files and no scientific outcome.

## 3. Sources and immutable formal computation

Primary and independent paths authenticated final R51R2, all 208 R51R1 raw,
and all 16 matching R8R7 baselines. Inventories remained:

```text
R51R1  208 files / 6,692,740 bytes
  0ce9ac9211c00b403f0ef7235cfde81a1e42751fa230d245cd2dc396fc3e3d33
R8R7 baseline  16 files / 487,298 bytes
  46df626a462dfdbfe7cdf9138a50b6b19c03f0ae5e8bb18cf18c6fcbe05c01a5
```

All 224 trajectories were strict, finite, full horizon, and retained. The
unchanged 250/270 ms arrival deadlines, 350/370 ms hold endpoints, 30 mm
position tolerance, 0.1 m/s speed threshold, 10 kA Ip safety threshold, and
three-sample arrival streak were applied without expansion. NumPy primary and
scalar `math`/`fsum` independent implementations agreed exactly on all pass,
arrival, aggregation, and route outcomes; maximum numerical difference was
`4.440892098500626e-16`.

## 4. Authority result

```text
strict full-horizon rows                                  224/224
matching baseline formal PASS                                6/16
candidate formal PASS                                      78/208
contexts with at least one candidate PASS                    6/16
failed baseline contexts                                       10
failed contexts with strict minimum-margin improvement       10/10
failed baselines repaired                                     0/10
baseline-plus-candidate measured oracle                       6/16
source or row exclusions                                          0
```

Every one of the 78 candidate passes occurred in one of the same six contexts
whose matching zero-action baseline already passed. All ten failed contexts
improved their best minimum signed margin, but the gains were only:

```text
minimum  0.00012208172194427824
median   0.0007190166666670716
maximum  0.00342862847187142
```

Their best candidate margins remained negative, ranging from approximately
`-0.2481` to `-1.1393`. The authority gate therefore failed exactly as
preregistered: repair `0 < 1` and oracle `6 < 7`.

The five candidates that won at least one failed context were:

```text
d0m  d1p  d2m  d3p  u1p50
```

This is development evidence for a successor design, not a causal selector or
qualification result.

## 5. Artifact identity and execution boundary

```text
primary detailed       8c1f8e1d1ac900401f7ef22293e0f63726b2752c483f66b16893ba29280293ce
primary summary        f0323cb8fc2d5fb1ab0579e0c6da2e4f392eac5faf1f33113adb29a04c1a2cea
independent            87eaa727e5e9396214ae006e62a6c487937317f6e65ba307dfb55fad44a6b0ff
compact audit          fc83d57516fa324dc53c8402bb38b826ae8023d80d73b3355fdc9b1f47189abe
final report           e1070b8eadb6e3d4959225b7ed617b49df02941eebfd39000104254ed547bc7f
stage state            f0152febd2f69be70af89cc787ac8765a4153175a119fed58ce6523ca7bb0d69
stage manifest         7c3e7cef1916f589cd5c4ca81d00dc70ff1efdf298b25f6a8c2768e9e6c63621
source authentication  9c984c38ac80e3ac2a25a2420f2e8f86647112df65de35f5ec7d1b13e712f556
server final evidence  15023c597e042d43bb96a648800eb2b5bc88bd2295a109a8635554b1ff065664
formal metric digest   b9f9ae61c6e1093fbaa10d22239da3bb82ce56bf4c38023c8cea0924c129b0d0
context outcome digest fb7359cfa38f7750edeaa9f522ec903cbf22dc81b821a63a9205b803901af2d8
```

The R51R3 stage contains nine files and zero JSON.GZ, raw, or snapshot files.
It executed zero new TSC, controller, plant step, model fit, model selection,
or optimization.

## 6. Classification and successor

R51R3 rejects selecting one already measured short transport pulse followed
by exact return and hold. The result does not reject sustained or genuinely
sequential transport action, nor prove that the plant cannot reach the target.
The best-margin gains are real but far too small to close the failed-context
formal gaps.

The successor must be a new-identity, prospectively frozen sustained/sequential
action design with an exact dual offline safety gate before any real TSC. It
may use the five disclosed development candidates above, but it must not call
that post-result selection independent validation. Any new trajectories remain
probes forbidden from learning.

Gate A, expert data, BC, DAgger, residual RL, and Gate B remain blocked.
