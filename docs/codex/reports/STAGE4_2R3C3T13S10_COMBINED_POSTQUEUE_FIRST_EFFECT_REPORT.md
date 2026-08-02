# Stage4.2R3c3T13S10 combined post-queue first-effect report

## Final result

T13S10 authenticated and read all 136 immutable T13S5/T13S9 raw files and
completed its frozen zero-new-TSC audit. Its exact final route is:

```text
UNIFIED_POSTQUEUE_Q1_Q2_FIRST_EFFECT_INSUFFICIENT_OBSERVER_REDESIGN
```

Unified post-queue excitation repaired the earlier input-coordinate support
failure: every one of 128 held transitions had all three same-stratum
training hypotheses supported. The static local-map bank nevertheless
failed its response gates. This is a finite causal transition-model design
failure, not a runtime, deployment, raw, restart, causality, reporting,
controller, or real-MPC failure.

## Exact implementation and evidence

```text
branch
  codex/stage4_2r3c3t13s1-transition-sentinel
T13S9 result / T13S10 design checkpoint
  4503626  Finalize T13S9 and preregister T13S10
T13S10 implementation and executed package checkpoint
  723c6bf  Implement T13S10 combined first-effect audit

preregistered design SHA-256
  ecac014c21bebb04ec8940e7de41f1e82eb294638c500809767d66b40174497c
audit implementation SHA-256
  b65a0b39492df80d9e63903739ae3962d2d5bd831610ea209fcf151a95ad0a82
PACKAGE_MANIFEST SHA-256
  6c791d4d9931107f392835fde8b7ceb0be4fb1e2ee648761af9f58c3ad1f3ff4
SHA256SUMS SHA-256
  6bb17baedc6ada3ed6968fcaeb52dcd282ee9785832d2db3c4672f1bd489a87f
```

Remote paths:

```text
staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s10_723c6bf
q1 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s9_runs/
  stage4_2r3c3t13s9_unified_postqueue_q1_identification_20260802_2f5138a
q2 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s5_runs/stage4_2r3c3t13s5_real_20260802_d048686
audit directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s10_audits/
  stage4_2r3c3t13s10_combined_postqueue_first_effect_20260802_723c6bf
```

Compact evidence hashes:

```text
main audit JSON
  f24768f7b4899c73f68fd0a4e3991f524239951883abf3d2809461b5ab82509b
audit log
  84448055bc8fe6dddea21d8d7d881f2a7a4995cac2337413b129dcb5e1dfb7a3
staging validation log
  6de5954a90caeb8345a3e2fbcdceb5aef9ac145a67ed049e9f4d9f0bbf2d857b
installed validation log
  704238226238c045ff12fa40741f1d11fcd13add8a7fd8b5e3a5349761086820
```

## Source and execution integrity

```text
q1 T13S9 raw files / bytes                       68 / 3,610,295
q1 raw digest
  9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
q1 independent source audit SHA-256
  df4d7982f98a6216997d89ac5adea9ca2e3b2bf367451c3412d5458ccc5c60e0
q2 T13S5 raw files / bytes                       68 / 3,610,097
q2 raw digest
  09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
q2 independent source audit SHA-256
  dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033
combined raw / trace identity                         136 / 136
post-queue first-effect contracts                       64 / 64
signed single-transition extraction                   128 / 128
pre-effect causality                                   128 / 128
forbidden feature or trace inputs                              0
```

The audit ran in the foreground with the existing server virtual
environment. It created one compact JSON and one log. It did not start Ray,
`gotsc`, TSC, a controller, an optimizer, a plant step, a snapshot, or any
new raw trajectory. Source raw files were not rewritten.

## Recomputed model result

```text
contexts / LOCO folds                                      8 / 8
local maps / signal pass                                 16 / 16
rank and condition pass                                  16 / 16
non-vacuous tube pass                                    16 / 16
maximum condition                                      7.9547833
maximum tube/cap ratio                                 0.1471975
held input support                                      128 / 128
componentwise union containment                         107 / 128
scaled relative error <= 0.10                           110 / 128
both frozen response gates                               92 / 128
maximum finite scaled relative error                    0.9307636
exact feature/input collisions with disjoint responses           0
```

The failure is distributed across both campaigns and both windows:

```text
held subset                 both gates
q1 T13S9                    44 / 64
q2 T13S5                    48 / 64
easy stratum                53 / 64
hard stratum                39 / 64
transport                   46 / 64
braking                     46 / 64
```

The coil-8 component direction was the most consistent at 30/32, but the
other directions passed only 19/32, 23/32, and 20/32. This is not one bad
context or one bad sign. The nearest visible-feature hypothesis satisfied
both gates only 64/128, and even an oracle that selected one hypothesis
which passed both gates reached only 72/128. Therefore a label-free static
selector cannot repair the result; a causal state update or active
calibration is required.

The source audits independently authenticate each source campaign. The
T13S10 audit itself reread and hashed every raw file. A separate compact
recomputation verified all 128 reported predicates, all 16 model gate
counts, the 92/128 conjunction, and the final route exactly. A second fully
independent implementation of the combined numerical fit was not run; this
is recorded rather than overstated.

## Validation and scope

Local validation passed 17 focused tests, all 730 repository tests, strict
parsing of 1,616 JSON files, a 341-file checksum/import closure check, and a
complete empty-directory direct-copy simulation with 730 tests and one
expected skip. Both server staging and installed packages passed 730 tests
with one expected skip, `bash -n`, `compileall`, strict JSON, checksums, and
the T13S10 import guard.

There were no runtime/environment, deployment, raw/snapshot, restart,
causality, statistics, or reporting errors in the executed audit. The real
finding is limited to the consumed finite q1/q2 first-effect development
envelope. No controller, MPC, q3 history, new target, continuous parameter,
noise, disturbance, or independent long hold was tested. Probe trajectories
remain forbidden from expert data. BC, DAgger, and bounded residual RL
remain blocked.
