# Stage4.2R3c3T13S24D1R14R5 final forensic report

## Result

D1R14R5 is a zero-new-TSC static exact-action preflight PASS. The fixed
global `1.5x` direction-0 candidate passed all 48 signed issue constructions
and all 24 exact positive/negative antipodal pairs. The final route is:

```text
GLOBAL_DIRECTION0_GAIN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

This pass authorizes only a separately frozen fresh 48-probe authentic TSC
sentinel. It does not validate plant response, online cancellation, a
transition model, MPC, formal control, robustness, expert data, BC, DAgger,
or RL.

## Revisions and paths

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition

design checkpoint
  0260c6b

initial implementation checkpoint
  e1ca97e

launcher hotfix checkpoint
  2706262

primary report-comparison hotfix checkpoint
  57b8e39

independent report-comparison hotfix checkpoint
  e7b550a

final package checkpoint
  a4c43bb

final package revision
  r42r3c3t13s24d1r14r5_global_direction0_gain_preflight_v4_independent_comparison_hotfix

final staging
  /home/yangshen0711/tsc_software/
  stage4_2r3c3t13s24d1r14r5_a4c43bb_v4

server output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r5_audits/
  stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight_20260804_bb829f3_v3
```

The primary output was completed under package `bb829f3`. The only remaining
work was a structurally independent report comparison. Package `a4c43bb`
changed no candidate, raw input, action construction, threshold, or route and
resumed only that independent audit.

## Source authentication

Both final implementations read the complete source raw in place on the
server and authenticated:

```text
R4 raw count / bytes                         200 / 6,285,765
R4 inventory digest
  44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9

R2 raw count / bytes                           72 / 2,254,876
R2 inventory digest
  c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649
```

The official R4 geometry was recomputed exactly: signal `254/256`, rank
`64/64`, condition `64/64`, minimum signal `0.00429800000001368`, maximum
condition `11.570074108693706`, and the same two failed experiment IDs and
peaks. The frozen R4 independent implementation produced its own report in a
different branch order and omitted the primary-only `first_response_state`
field, but reproduced all 17 frozen gate metrics and the exact failure route.

## Frozen candidate and gates

The candidate matrix digest was:

```text
69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8
```

Only column 0 was multiplied by `1.5`; columns 1--3 were byte-for-byte the R4
values. The same candidate was used for every context, issue time, and sign.
No pair/history label, signed source outcome, future trajectory value, source
action, source/current wire current, or hidden vessel state selected the
candidate.

Final independent results were:

```text
contexts                                                     8
issue task steps                                      14,18,22
signed static constructions                               48/48
coordinate/physical-field antipodal pairs                  24/24
maximum issue increment                         0.17481481481481495
maximum ideal stored-center return increment     0.17481481481481495
maximum predicted current utilization                        0.3799
maximum relative off-basis residual              0.05794563546539851
new raw / plant steps / controller / Ray / gotsc / TSC       zero
```

The frozen limits were respectively `0.25`, `0.24`, `0.55`, and `0.10` for
the corresponding maxima. Exact Card15 center/target, target reproduction,
total action, no saturation/clipping, and minimum cosine gates also passed
for 48/48.

## Attempt history and classification

Four pre-final failures are preserved rather than hidden:

1. `cdba0e5` stopped before Python because a Windows direct copy did not set
   the Linux executable bit on a shell wrapper.
2. `c0f1bb4` re-read the raw but rejected the source because the new primary
   authenticator required an exact dictionary match against the differently
   ordered old independent report.
3. `bb829f3` completed and saved the passing primary output; the new
   independent audit then made the symmetric ordering/schema comparison
   error.
4. The first `a4c43bb` independent-only resume stopped before import because
   the direct command omitted `PYTHONPATH`; the corrected command used the
   server virtual environment and explicit project `PYTHONPATH`.

These are launcher/environment or statistics/report-comparison errors. They
did not change an action, run a plant step, create raw, alter the candidate,
or observe a new outcome. The primary results were preserved and only the
unchanged independent audit was resumed.

Final classifications are:

```text
runtime/environment error in final audit                   none
packaging/import/deployment error in final audit           none
raw or snapshot corruption                                 none
statistics/reporting error in final accepted outputs       none
design gate failure                                        none
real control failure                              not evaluated
real restart conclusion                           not evaluated
finite static exact-action result                          PASS
```

## Hashes and inventories

```text
primary detailed SHA-256
  deb57e9c774ef792ed9f8464987e4528b69f3876a09dcd7ff4ca55ea8d9dedc9
primary summary SHA-256
  fc9d1fded5bf63e2658ad0c8da5aca642011006edd04ae1ee8aaaec58051a213
primary manifest SHA-256
  be2b358bbe35f5fff1029f4cb94b8a1638fd7e5b2c3bb244fe51fb1de0fd0d35
independent result SHA-256
  306fd16a65ad44bea1972fb37f4ce316363eeff8a3834ceea8973afe1f42f3cb
compact evidence SHA-256
  930a36087efca7fb1a6ffa7ce31f76835db48ffd56154a38bd282f7316c2d6ad
final package manifest SHA-256
  258b67e14558f158907e0163ac6fc2be188cc54485e50a55ad2ee8379cedce2a
final SHA256SUMS SHA-256
  48f05daa2de6c69315c114c9cf95dc1b52ff9fceee9f02cd5ea2ba7b598c3875
```

The final package declared 575 files. Staging and installed validation each
passed all declared hashes, Linux shell syntax, server-virtualenv import and
compile checks, JSON parsing, and 13/13 focused tests. Locally, compile/JSON,
13/13 focused tests, 1108/1108 complete tests, and a fresh 575-file empty-tree
deployment simulation passed.

The 272 source raw files and both detailed row-level results remain on the
server. Only the compact evidence, summaries, and short logs were copied
directly and uncompressed to:

```text
docs/codex/audits/stage4_2r3c3t13s24d1r14r5_20260804_a4c43bb/
```

## Scientific boundary and next action

The ideal return in R5 is a static stored-center calculation. It does not
prove that a real issued pulse reaches that center or that the next causal
command cancels the actual plant/current state. The immutable arrival
deadlines and hold endpoints were not evaluated and did not change.

The next action is a new-identity fresh 48-probe authentic sentinel. It must
validate real issue/cancellation safety for the fixed direction-0 candidate,
then replace only R4 direction 0 at times 14/18/22 in the combined response
bank. Only a complete 256/256 signal, 64/64 rank/condition, and 128/128 issue
antipodality result can authorize a separately frozen transition-model fit.

