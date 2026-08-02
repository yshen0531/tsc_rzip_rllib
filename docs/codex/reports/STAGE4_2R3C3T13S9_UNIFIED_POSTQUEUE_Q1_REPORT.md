# Stage4.2R3c3T13S9 unified post-queue q1 identification report

## Final route

T13S9 completed exactly its frozen 68-rollout authentic identification
campaign and ends as:

```text
UNIFIED_POSTQUEUE_Q1_IDENTIFICATION_COMPLETE_COMBINE_Q2_REQUIRED
```

This is an identification completion result, not a controller or MPC pass.
It proves that the four q1 restart contexts can be excited through the same
post-queue Card15 coordinate as T13S5 q2, with correct immediate effects and
four locally identifiable first-effect maps. It does not establish a
cross-history model: the diagnostic q1 history split failed containment and
relative-error gates.

## Exact identity and evidence

```text
branch
  codex/stage4_2r3c3t13s1-transition-sentinel
preregistered design checkpoint
  4e57a3b  Finalize T13S8 and preregister T13S9
implementation checkpoint
  4dc6c18  Implement T13S9 unified q1 identification
package-closure checkpoint
  e4859b7  Fix T13S9 package import closure
executed launcher/package checkpoint
  2f5138a  Make T13S9 launch transfer-safe
package revision
  r42r3c3t13s9_unified_postqueue_q1_v1
PACKAGE_MANIFEST SHA-256
  d88ed4e3718f90abfbe066d78cf651a25d7bceebc06a66927b15d9a4880f80f9
SHA256SUMS SHA-256
  47a1107a2d2b4333e29810d994fa5d82bb95876ec9e7f9e5f2f60fff4ce72e1d
config SHA-256
  76e95c3e83195d1d0630fccabbaf845a3a5778782691162a3baaff9b4cff6783
diagnostic implementation SHA-256
  b52d685fafb62c17ef66fba547708339003a55f041d7602856eea335db8b3e97
```

Remote paths:

```text
staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s9_2f5138a
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s9_runs/
  stage4_2r3c3t13s9_unified_postqueue_q1_identification_20260802_2f5138a
campaign log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s9_unified_postqueue_q1_identification_20260802_050746.log
server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s9_audits/
  stage4_2r3c3t13s9_unified_postqueue_q1_identification_20260802_2f5138a/
  stage4_2r3c3t13s9_server_audit.json
```

Compact evidence hashes:

```text
server audit                         df4d7982f98a6216997d89ac5adea9ca2e3b2bf367451c3412d5458ccc5c60e0
raw inventory                        858f1d13680a21d795c7c2c1e3b5da4f791ba378474d7b27104439a8c05bfb4d
run inventory                        db0e952ea5f2d23ed7d344da1abd0c0043c67708c7c5434d03c730aa9c166fbe
snapshot audit                       f3fcce4837eb9d89ceae81fc9a0ee0908bbb651e1ca46f8481c984bc2a4500c6
campaign log                         0179d97b98a9c33d5653a6a77eca3e7c9a13e04f54f2ab7a9e61cabd0eb53dfd
server postprocess log               c5598d2c9d0888439c84f4ddf2c300a52a4330a5a9dbaa09432aeb5e4fd69d19
```

## Raw, snapshot, and execution audit

Independent server-side postprocessing parsed and rehashed every raw file
and recomputed the reported summary exactly.

```text
expected / actual authentic rollouts                         68 / 68
raw JSON.GZ files / bytes                            68 / 3,610,295
raw inventory digest
  9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
run inventory files / bytes                         295 / 8,469,039
run inventory digest
  e4dbef249beeba52de433f1112cf894d6d930daf1856dd4b66143f188a6be8b2
raw identities exact                                           68 / 68
unique authenticated restart snapshots                           4 / 4
snapshot manifest failures                                           0
execution / fresh restart / controller causality                68 / 68
runtime, solver, saturation, serialization failures                    0
statistics or reporting errors                                        0
```

The four snapshot digests exactly match the preregistered q1 identities:
`4add3b...`, `0c4141...`, `1edbbc...`, and `2af7ae...`. Each snapshot has
one exact identity and eight manifest files. The large snapshot and raw
trees remain on the server; only compact audits and logs were downloaded.

## Recomputed scientific gates

```text
zero-plant offline specifications                               68 / 68
offline lattice events                                         128 / 128
plant advances / raw during offline gate                           0 / 0
real execution                                                 68 / 68
Card15 fields exact                                      34,272 / 34,272
current readbacks inside frozen intervals                34,272 / 34,272
clip or rescale events                                                0
target field central symmetry                                   32 / 32
observed first-effect current signal                             32 / 32
observed first-effect current symmetry                           32 / 32
pre-effect causality                                             32 / 32
development signal                                              16 / 16
development local rank/condition                                  4 / 4
development non-vacuous tube                                      4 / 4
maximum development condition                               7.9547833
maximum tube/cap ratio                                      0.1471975
maximum current utilization                                    0.3904
forbidden controller/model inputs                                   0
```

The plus-first development model was hashed before any minus-first raw was
opened. Its model SHA-256 is
`c958c044cd4818909160c67309f07aa6487d7a86a882e8b735f60e09263bde51`.
This split is diagnostic only because every T13S9 rollout is consumed
development evidence for the next combined q1/q2 audit.

The diagnostic minus-first result was:

```text
pre-effect causality                                            32 / 32
componentwise containment                                       15 / 32
scaled center relative error <= 0.10                            20 / 32
maximum scaled relative error                                 1.7167681
```

Thus unified input geometry and local identifiability passed, while a
single cross-history q1 model did not. T13S9's positive route deliberately
does not hide or reinterpret that failure; it requires the prospectively
frozen combined q1/q2 hypothesis-bank audit.

## Error classification and workflow defects

Before real TSC, an empty-directory deployment test exposed missing audit
tool/document dependencies in `PACKAGE_MANIFEST.json`. Commit `e4859b7`
fixed only package/import closure. The first offline shell attempt then
failed before Python because Windows transfer did not preserve executable
bits. It created no run directory, PID, raw, snapshot, plant advance, Ray,
`gotsc`, or TSC output. Commit `2f5138a` made the wrappers invoke `bash`
explicitly and added a regression test. Neither repair changed experiment
semantics.

```text
pre-execution package/import closure error                       repaired
pre-execution launcher deployment-mode error                     repaired
real campaign runtime/environment error                                no
raw/snapshot/restart/causality corruption                              no
statistics/reporting error                                             no
cross-history diagnostic model failure                                yes
real controller or MPC conclusion                                    none
```

Validation actually run included `compileall`, all JSON parsing, focused
tests, complete empty-directory deployment simulation, local 724-test
discovery, direct uncompressed transfer, server `bash -n`, package checksum
verification, and complete installed Linux tests (724/724 with one expected
skip). The real campaign used fixed Ray capacity 68 and was monitored by its
exact PID through 68/68 completion. Server postprocessing then independently
recomputed the compact result from raw.

No real MPC, q3 holdout, new target, continuous-parameter test, noise test,
disturbance recovery, or independent long hold ran. Probe trajectories are
forbidden from expert data. BC, DAgger, and bounded residual RL remain
blocked.

