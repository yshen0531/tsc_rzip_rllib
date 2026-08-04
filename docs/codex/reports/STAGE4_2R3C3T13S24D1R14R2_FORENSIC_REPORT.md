# Stage4.2R3c3T13S24D1R14R2 forensic report

Finalized 2026-08-04 after the frozen 72-task authentic campaign, primary raw
postprocessing, and structurally separate server raw/snapshot recomputation.

## Identity and evidence

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition
design checkpoint                                           5f7fb80
implementation checkpoint                                   e7fe6c8
package checkpoint                                          ca2815a
design SHA-256
  5344a7436277c18d3a85a750d5516c69595c6d84090d47f9cc01af85b888896a
PACKAGE_MANIFEST SHA-256
  79fb42b5066c722066fa99c0b63668b1497ff8edd558650a7a79bb50a8c163f1
SHA256SUMS SHA-256
  9c067fc5b6edf5d0cbb905a27a1d14b942b64741fb46f3f5e05bbb447c82c0c3
fixed mixed-matrix digest
  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
spec digest
  ff5e29f1ebb94dd2c8b9602d85021938ad578be37765a297d6d7df562e39bb35
```

Remote evidence remains at:

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r2_runs/
  stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_20260804_ca2815a_v1
installed verification log
  logs/stage4_2r3c3t13s24d1r14r2_ca2815a_installed_verify.log
offline / real / postprocess logs
  logs/nohup/stage4_2r3c3t13s24d1r14r2_{offline,real,postprocess}_20260804_ca2815a_v1.log
```

The 72 raw JSON.GZ files and all restart snapshots remain on the server. Their
inventory is 72 files, 2,254,876 bytes, digest
`c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649`.
Only the 13 compact outputs/logs under
`docs/codex/audits/stage4_2r3c3t13s24d1r14r2_20260804_ca2815a/` were copied
directly and uncompressed. Local sizes and hashes match the server manifest.

## Validation and execution

Before server execution, all 503 repository JSON files parsed, compileall
passed, focused D1R14R2 tests passed 15/15, and the complete repository suite
passed 1072/1072. A 543-file empty-directory deployment simulation passed
checksums, JSON, compile, import closure, package fingerprint, and 15/15 tests.

The installed server package passed all 543 hashes, `bash -n`, server-venv
compile/import, scientific guards, and 15/15 focused tests. Its verification
log SHA-256 is
`f6f81fef4dd80c0961974b2a1fb470b2446c4068c760bb749b9e4aaafcc1bf04`.
No global Python was used locally or remotely.

The zero-plant offline gate authenticated the exact R1A output, all 8 D1R13
raw, all 600 D1R11 raw, and 8/8 snapshots. It generated exactly 72 unique
specifications: 8 zero baselines and 64 signed probes, split 36/36 over the
35/37-step horizons. Offline raw and TSC counts were zero. The real Ray phase
then used fixed capacity 72 and produced 72/72 successful full-horizon raw.

## Primary and independent result

Primary and independent results agree exactly:

```text
strict raw / safety pass                                  72 / 72
exact state and trace prefix                              72 / 72
fresh zero-baseline reproduction                            8 / 8
exact mixed-basis issue                                   64 / 64
exact causal stored-center cancellation                   64 / 64
finite full-horizon records                               72 / 72
snapshot authentication                                     8 / 8
runtime / prefix / plant failures                               0
solver / saturation / clipping errors                          0
forbidden-input rows / reporting mismatches                    0
maximum current utilization                         0.3904000000
formal tracking diagnostic                                18 / 72
```

Formal tracking is diagnostic only and establishes neither success nor
failure for this identification sentinel.

The frozen response geometry was evaluated only after every safety gate
passed:

```text
signal                                                       32 / 32
central symmetry                                             28 / 32
rank four                                                      8 / 8
condition <= 20                                                8 / 8
minimum odd peak                                  0.005466000000009519
maximum even/odd ratio                           0.8528017842241936
maximum condition                                8.802962394477525
```

The final route is:

```text
MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED
```

The primary final SHA-256 is
`3df193e52ee0ce8fe72620af9f72597f58af4419c6386c37d62fb051bcefd79a`.
The independent forensic SHA-256 is
`68f21e95694c607084b9cc7d39732bcda05d57a14f6f3cc4f1e78e8941e7e2df`;
it completed successfully, reproduced the same route, and matched every saved
geometry aggregate.

## Failure localization

All four symmetry failures occur in the matched hidden-history pair
`p9_q2_a0p900_gap3_settle4`:

```text
context                       history      direction    even/odd
s42r3c3_39edf644f2fdf0ee6c5a minus_first  pooled_1     0.7740503
s42r3c3_39edf644f2fdf0ee6c5a minus_first  pooled_3     0.8528018
s42r3c3_b72b7cdb52af15409a54 plus_first   pooled_2     0.5262727
s42r3c3_b72b7cdb52af15409a54 plus_first   pooled_3     0.8386252
```

The dominant even term is late `vR` (state 21 or 35). Direct raw
reconstruction found exact central symmetry of the actual issued coordinate
and physical field for all 32 signed pairs. Thus the failed even response is
not caused by asymmetric Card15 quantization, issue construction, saturation,
or cancellation. It is a genuine context- and sign-dependent closed-loop
plant response within this finite envelope.

This invalidates the shared odd-only local-response assumption used by the
planned linear time-distributed route. It does not prove plant
uncontrollability and is not an MPC/control failure, because no MPC was built
or run.

## Post-result architecture diagnostic

A separately labelled post-result development diagnostic did not change the
R2 verdict. It treated positive and negative responses as distinct local
branches rather than averaging them into one odd model. All 16
context-by-sign branches had four-direction signal at least
`0.005310999999896815`, rank 4, and condition at most `9.55784063525667`.
All 32 physical issue pairs remained exactly central. Its SHA-256 is
`2a843ca4f9d05e1f5fbb7036313652fce2093062bf7a4b1fa969ad599f406f61`.

This is only architecture-selection evidence. It is neither a validation
pass nor authorization to fit a model or run a new campaign. It motivates a
prospectively frozen, zero-new-TSC sign-split feasibility audit before any
time-shifted identification design.

## Classification and scientific boundary

```text
runtime/environment error                         no
packaging/import/deployment error                 no
raw/snapshot corruption                          no
summary/statistics/reporting error                no
restart/prefix/causality failure                  no
action/current/safety failure                     no
plant abnormal execution failure                 no
response-geometry design failure                 yes
real closed-loop MPC/control conclusion           none
```

D1R14R2 is frozen and will not be resumed or reinterpreted. It establishes
finite authentic issue/cancellation safety and sign-dependent local authority
only for the eight clean source contexts and four fixed mixed directions. It
does not validate time shifting, a transition model, hidden-history feedback
robustness, new targets, continuous delay/gain/slew, model error, noise,
disturbance recovery, long hold, MPC, or expert data. BC, DAgger, and bounded
residual RL remain blocked.

## Command/audit exceptions

Three diagnostic tooling events did not affect the experiment:

1. The first pre-launch read-only audit compared two `Counter.values()` view
   objects and stopped before the real launcher. The corrected count check
   passed; no real log or TSC existed before correction.
2. A post-result exploratory pooled SVD attempted to concatenate the 35- and
   37-step horizons. Per-context rows had already printed, but no official
   output was written. The saved sign-split diagnostic evaluates each horizon
   independently.
3. The first local package-import check lacked the repository's Windows
   `resource` compatibility shim. The shimmed check and full suite passed.

The multi-source compact `scp` wrapper reached its client timeout only after
all 12 requested files had arrived. Strict local JSON parsing and exact remote
size/SHA verification passed for every file; the thirteenth posthoc JSON was
then transferred and verified separately.

## Next action

Freeze and independently implement a zero-new-TSC sign-split response
feasibility audit. It must authenticate all R2 evidence, reproduce the R2
geometry FAIL unchanged, and prospectively test fixed positive/negative
rank-four response branches. A pass may authorize only design of a fresh
time-shifted safety/identification campaign. It may not authorize model
fitting, MPC execution, expert data, BC, DAgger, or RL.
