# Stage4.2R3c3T13S24D1R14R1 forensic report

Date: 2026-08-04

## Final result

D1R14R1 authenticated and recomputed all 72 immutable D1R14 v2 raw files,
reproduced the frozen 60,000-candidate search and its predicted response
geometry, and evaluated all 64 proposed exact static Card15 issue actions. The
search/geometry gate passed, but only 48/64 issue constructions passed the
complete frozen gate. The final route is:

```text
POOLED_MIXED_BASIS_PREFLIGHT_FAIL_REDESIGN_REQUIRED
```

This is a prospective mixed-basis quantization-margin design failure. It is
not a runtime, deployment, raw, summary/reporting, restart, plant, control, or
MPC failure. R1 executed zero controller calls, plant steps, Ray, gotsc, and
TSC, and created no raw or snapshots.

## Identity, package, and paths

```text
branch                  codex/stage4_2r3c3t13s24-sequential-transition
implementation commit   7c4002c
package commit          36f0d41
package revision        r42r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_v1
manifest SHA            218746a2a9c1840779345f6c129f4b8d051d6943327bc8a89e2f67321131ac45
SHA256SUMS SHA           6378f837e7ece02b4c5fb4d0705a2a5fac4476a65b6d5cf72460fc8eaeb8883f
declared files           522
```

```text
staging:
/home/yangshen0711/tsc_software/stage4_2r3c3t13s24d1r14r1_36f0d41_package

output:
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r1_audits/
stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_20260804_36f0d41_v1

installed verify log:
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/
stage4_2r3c3t13s24d1r14r1_36f0d41_installed_verify.log

execution log:
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t13s24d1r14r1_offline_20260804_36f0d41_v1.log
```

## Source and search authentication

The immutable D1R14 v2 inventory reproduced exactly: 72 gzip JSON files,
2,239,479 bytes, digest
`0433a64ebaea73186bb193d5102686721497219acfcbecbb721e7fad62e8d7a3`.
All files matched the source final inventory by name, size, and SHA; all parsed
strictly and reported complete/success. The official D1R14 geometry was
recomputed exactly before redesign values were read.

The frozen NumPy seed `140042`, 60,000 QR candidates, pooled Gram whitener,
objective, and tie order selected zero-based candidate `35377` as required.
The recomputed matrix matched the frozen matrix within tolerance. Linearized
prediction passed:

```text
minimum odd peak                  0.005999999999999252
maximum unit-column condition     3.7020780011896957
required                          >= 0.006 (floating tolerance), <= 4.0
```

This remains a calculation on consumed development responses, not a fresh
plant validation.

## Exact static issue failure

Every proposed issue action passed exact center/target, target reproduction,
saturation, clipping, incremental action, total action, current utilization,
direction cosine, and the inherited actuator gate except for one criterion:

```text
construction pass                  48 / 64
failed constructions               16 / 64
failure criterion                  off-basis residual only
failed mixed direction             column 2, both signs, all 8 contexts
maximum off-basis residual         0.1359745441
frozen maximum                     0.10
minimum direction cosine           0.9903210774
maximum issue action               0.1161111111
linearized cancel diagnostic       0.1161111111
online cancel proved               false
```

Thus the mixed direction itself is safe in action/current terms, but its
Card15-quantized displacement is not close enough to the intended fixed-basis
span under the preregistered 0.10 residual limit. The limit is not weakened.

## Development diagnostic and next stage

After freezing R1 as FAIL, a read-only `1.000` through `2.000` scale grid in
steps of `0.025` was run as development diagnosis on the failed third column.
The first 64/64 static-feasible grid point was `1.275`; it gave maximum
off-basis residual `0.099075902`, maximum issue and idealized cancel action
`0.140185185`, and retained action/current headroom. This grid is not R1
validation and is not reported as a pass.

The next task is a separately frozen zero-TSC D1R14R1A preflight with the
third-column multiplier fixed at `1.275` before implementation. It must
authenticate this R1 FAIL, reproduce the exact revised matrix/digest, repeat
all 64 static constructions, and preserve the original real-R2 geometry and
safety gates. Only an R1A pass may authorize a fresh real-TSC D1R14R2 design.

No transition model, MPC, expert dataset, BC, DAgger, or RL was run or
authorized.
