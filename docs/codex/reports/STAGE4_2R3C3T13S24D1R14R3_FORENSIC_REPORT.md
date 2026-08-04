# Stage4.2R3c3T13S24D1R14R3 forensic report

Finalized: 2026-08-04 after the frozen zero-new-TSC primary audit, a
source-fingerprint transcription hotfix, a fresh corrected audit output, and
structurally separate server-side raw recomputation.

## Identity and package

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
design checkpoint                                      343a516
initial implementation / package                  273a5cf / 85012c1
test-closure fix                                         487d746
source-hash erratum / final package                aa3325a / ca49a36
design SHA-256
  f76fc33243e8969cac1554da13d57af28fb3a197fdf8c89554d35f9907b9d207
erratum SHA-256
  720a9537f6f468c3131ccbf72f2d0e3cdce53a8ec310a76ad33e84270719a85f
final PACKAGE_MANIFEST.json SHA-256
  def0f5af75fb5290a448f519a8c6ff0fffd00f212391038352ad3da57ae44c4e
final SHA256SUMS SHA-256
  e32dbe03c7d59c51dc054578fb878fadc17d5febb6296a8c305b35aefc9c49b2
declared package files                                    553
```

The final package revision is
`r42r3c3t13s24d1r14r3_sign_split_response_feasibility_v2_source_hash_hotfix`.

## Validation

Local validation used only the repository virtual environment:

```text
strict repository JSON parse                            1,618 files
compileall                                                     PASS
focused R3 tests                                             7 / 7
complete repository tests                              1,079 / 1,079
empty-directory package hashes                           553 / 553
empty-directory replacement-tree closure                383 / 383
empty-directory import / compile / focused tests              PASS
```

The final server staging and installed package both passed all 553 hashes,
server-virtualenv import/compile, all JSON, `bash -n`, package guards, and
7/7 focused tests. Their verification logs have the identical SHA-256
`3823d0f0a173625a5bcc262e92a063a7776bf4b561a02aa747abb6a3f97e1fb2`.
No global Python, archive operation, Git, or server network dependency was
used.

## Remote evidence

The immutable R2 raw and restart tree remains at:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r2_runs/
stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_20260804_ca2815a_v1
```

The frozen initial and corrected R3 outputs are:

```text
v1
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r3_audits/
  stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_20260804_85012c1_v1
v2
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r3_audits/
  stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_20260804_ca49a36_v2
```

Complete logs are:

```text
logs/nohup/stage4_2r3c3t13s24d1r14r3_offline_20260804_85012c1_v1.log
logs/nohup/stage4_2r3c3t13s24d1r14r3_offline_20260804_ca49a36_v2.log
```

Large raw and snapshots were not downloaded. The eleven compact local files
are under
`docs/codex/audits/stage4_2r3c3t13s24d1r14r3_20260804_ca49a36/`; all nine
downloaded server files match the server compact manifest by size and SHA.
The server compact manifest SHA-256 is
`cd8c6c679cbe78b02141358a55928896be6623488b81de73b8bd876a5a6d546f`.

## Initial source-gate failure and correction

Both v1 implementations stopped at
`SIGN_SPLIT_RESPONSE_FEASIBILITY_SOURCE_FAIL_NO_TSC`. Their hashes are:

```text
v1 primary      945bb981df05940b26cd4087b3b9404583aa0adf2dd6d66036f9bf3bc1c46857
v1 independent  044564fb42c2741080f44fdf2a9f6c6202601adc3fc92aa2276c318171ca945d
```

The sole mismatch was an expected R2 `stage_state.json` hash copied as
`46552980d151...`; the authentic hash is `46552980c0cd...`. The correct value
was already committed in D1R14R2's `LOCAL_COMPACT_INVENTORY.json` at
checkpoint `73c5811`, before the R3 design and outcome. The remote source,
local compact copy, and both R3 computations all agreed. Every other source
hash and all raw/snapshot/safety checks passed.

The erratum changed only that expected fingerprint. It did not change a raw
file, trajectory, response formula, threshold, count, route, task, controller,
plant action, or scientific interpretation. v1 remains frozen as a reporting/
source-manifest failure; v2 used a fresh output directory. This was not an
experimental resume because R3 has no plant execution.

## Corrected primary and independent result

The corrected primary and independent outputs have SHA-256:

```text
primary      30755ebccee65a5bcfd08d04632368979ec1c309ac42d4a46df49b3b921cd590
independent  f138611d56b77839bb3d87744b49eb08df4c4409947038e25b520f8d43764d90
```

They independently strictly parsed the 72 immutable R2 raw files and repeated
the complete R2 source, package fingerprint, R1A, D1R13, D1R11, restart,
snapshot, prefix, causality, issue, cancellation, current, safety, forbidden-
input, log, and geometry audit. The source inventory remained 72 files,
2,254,876 bytes, digest
`c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649`.

The original shared odd-model failure was reproduced unchanged:

```text
signal                                                   32 / 32
central symmetry                                         28 / 32  FAIL
rank four                                                  8 / 8
condition <= 20                                            8 / 8
failed context/direction pairs                                4
minimum odd peak                              0.005466000000009519
maximum even/odd ratio                       0.8528017842241936
maximum condition                            8.802962394477525
```

The distinct preregistered sign-split architecture then passed:

```text
contexts / sign branches                                  8 / 16
direction signal                                          64 / 64
rank-four branches                                        16 / 16
condition <= 20 branches                                  16 / 16
exact opposite requested-coordinate pairs                 32 / 32
exact opposite actual physical-field pairs                32 / 32
minimum branch-direction peak                 0.005310999999896815
maximum branch condition                         9.55784063525667
```

Primary and independent branch rows, singular values, extrema, counts, source
hashes, route, and pass flag agree. The final route is:

```text
SIGN_SPLIT_RESPONSE_FEASIBILITY_PASS_TIME_SHIFT_SENTINEL_DESIGN_REQUIRED
```

## Classification

```text
runtime/environment error                                      no
packaging/import/deployment error                               no
raw/snapshot corruption                                        no
R2 restart/prefix/action/plant/safety failure                   no
initial R3 source-manifest/reporting transcription error       yes, corrected
R2 shared odd-model response-design failure reproduced         yes
sign-split finite branch feasibility failure                   no
new TSC/controller/plant/Ray/gotsc execution                    none
real closed-loop control or MPC conclusion                      none
```

The result establishes only finite local piecewise-sign response authority at
the single sampled issue time in eight clean development contexts. It does not
establish time-shift invariance, a predictive transition model, complementarity
handling, MPC feasibility, authentic control, hidden-history robustness, new
targets, continuous delay/gain/slew, model error, sensing noise, disturbance
recovery, long hold, expert data, or readiness for RL.

## Command exceptions

The first unshimmed Windows full-test invocation produced 27 collection errors
because Unix `resource` is unavailable. The documented Windows compatibility
shim then passed 1,079/1,079, including after the hotfix. A test-only hidden
dependency on a local historical compact result was found before empty-tree
deployment and replaced with a frozen inline fixture; both empty-tree tests
then passed.

The first installed-file loop stopped before copying because it had not
removed CR characters from the Windows `SHA256SUMS` path field. The corrected
whitelist loop normalized CRLF and installed/verified all files. No audit or
TSC had started. These were validation/deployment tooling events, not
experimental failures.

## Next action

A pass authorizes only prospective design of Stage4.2R3c3T13S24D1R14R4: a
fresh authentic time-shifted sign-split safety/identification sentinel with
independent zero baselines and causal stored-center cancellation. Its design
must be frozen before implementation or new raw. Model fitting and MPC remain
blocked until that time-shift boundary passes. Expert data, BC, DAgger, and
bounded residual RL remain blocked.

