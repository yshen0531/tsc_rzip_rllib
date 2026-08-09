# Stage4.2R3c3T13S24D1R14R8R33 forensic report

Date: 2026-08-09 Asia/Shanghai
Branch: `codex/stage4_2r3c3t13s24-sequential-transition`

## 1. Final classification

R8R33 is final as a dual-layer zero-new-TSC failure:

```text
accepted overall route
  UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP

primary scientific route
  UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC

overall failure classification
  independent_numerical_reproducibility_gate_failure
```

The fixed rank-12 representation passed, but the primary causal model failed
the unchanged whole-pair and whole-schedule response/tube gates. Independently
rebuilt data, route, and scientific outcome agreed, but the prospectively
frozen absolute `1e-12` dual-solver numerical gate did not. The exact tolerance
was not changed after the result. Planning remained closed.

This is not a runtime, deployment, source-authentication, raw-corruption,
restart, real-controller, real-MPC, plant-reachability, formal-control, or Gate
A result. R8R33 executed zero Ray, `gotsc`, TSC, controller, plant step, raw,
or snapshot.

## 2. Immutable identity and checkpoints

```text
design checkpoint                         82d1307
initial implementation                    cd66c4a
initial package                           9c777c7
failure-finalizer implementation          c5cf429
final package                             d1d266d
config SHA-256
  cb6672acfd16583f96b6b9aa711b0b04a855df65e454de5c5e7cbac6c859d838
design SHA-256
  51063dc6f2ecede5d42a0cbf5cde6aa4736628ed38f27d3a5edaeba95a368189
final PACKAGE_MANIFEST.json SHA-256
  a4c05f621ba450f40850f610064e3f4fb401130a5dae2e67f90095b4c609e46a
final SHA256SUMS SHA-256
  cf7089285a9028bd826f3836253865811a0e28cfca618a0d4b18f7aa18ca519d
```

The finalizer hotfix changes no bank, feature, rank, solver, fit, prediction,
residual, tube, support, tolerance, route definition, or primary result. It
only validates and seals the already-preserved `independent_failure.json` as
an explicit failed terminal state.

## 3. Package and validation evidence

Initial implementation validation passed focused `8/8` and full Windows-
resource-shimmed `1429/1429`. The final failure-finalizer package declares
1,168 source files and contains 1,170 physical files including
`PACKAGE_MANIFEST.json` and `SHA256SUMS`.

The fresh empty direct-copy tree and both server staging and installed trees
passed:

```text
declared hashes                              1168/1168
JSON parses                                    137/137
Python compilation                             455/455
declared shell bash -n                         444/444
focused tests                                      9/9
full tests                                    1430/1430
expected isolated-evidence skip                       1
```

Only the existing project virtual environment was used locally and only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python` was used on
the server. Transfer was a direct `scp -r` directory copy with no local
archive operation.

Two stopped staging-validation wrappers are non-scientific deployment-log
events. The first lost nested `python -c` quoting before Python started. The
second completed every validation successfully but PowerShell appended a CR
blank line after the success marker, producing exit 127. The unchanged v3
script then reproduced all validations with exit 0 before installation.

## 4. Authenticated bank and representation result

Primary and independent paths rebuilt the frozen bank from immutable server
sources:

```text
trajectories                                      560
history contexts                                   16
schedule identities                                35
interval records                                 3360
bank digest
  a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest
  80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest
  0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

The feature-only PCA gate passed all 1,161 whole-pair and whole-schedule
heads at fixed retained rank 12; the minimum independently reproduced
numerical rank was 13. R8R32's rank-32 representation failure was therefore
repaired under the separately frozen R8R33 identity.

## 5. Primary model result

The unchanged outer physical caps are:

```text
point caps     [0.015,0.015,3000,0.05,0.05]
tube caps      [0.025,0.025,5000,0.08,0.08]
```

Primary whole-pair results were:

```text
maximum point error
  [0.0052639383,0.0038722137,322.794103,0.0768159912,0.178382915]
maximum reserved tube
  [0.015,0.015,3000,0.0960199890,0.222978643]
reserved containment                         72793/72800
state-support folds                                  8/8
```

Position and Ip point caps passed, but both velocity point caps and both
velocity tube caps failed; containment also missed seven components.

Primary whole-schedule results were:

```text
maximum point error
  [0.0356034203,0.222100359,3879.07206,0.500309357,1.27386076]
maximum reserved tube
  [0.0445042754,0.277625449,4848.84007,0.625386696,1.59232595]
containment                                  72800/72800
```

Whole-schedule R, Z, Ip, vR, and vZ point caps all failed. R, Z, vR, and vZ
tube caps failed; only the Ip tube cap remained within 5,000 A. The scientific
model gate therefore failed before planning. All zero planning, repair,
oracle, and nonzero-action counts are phase-closed sentinels, not successful
or failed controller trials.

## 6. Independent numerical failure

The independent raw-bank construction and augmented-least-squares path agreed
exactly on the bank, discrete route, and scientific outcome. It did not meet
the frozen unscaled absolute `1e-12` numerical contract:

```text
maximum bank difference                              0.0
maximum direct prediction difference       1.0359713087e-11
maximum model aggregate difference          4.7445336548e-09
maximum outer aggregate difference          1.1119993815e-08
maximum schedule aggregate difference        2.5826511774e-06
maximum planning-field difference            2.5826511774e-06
```

Consequently model, outer, schedule, and planning numerical agreements are
false even though bank, route, and outcome agreements are true. The overall
integrity gate fails closed. This numerical failure does not rescue or alter
the primary model failure.

## 7. Exact server evidence

Run directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r33_runs/
stage4_2r3c3t13s24d1r14r8r33_uniformly_supported_rank12_schedule_generalizing_feedback_preflight_20260809_9c777c7_v1
```

Stage evidence:

```text
primary_summary.json       2121 bytes
  2e7be2c391ee479c88ae61eaf12b43a38ac24bece8cdd2259cab98494acab729
primary_detailed.json    717640 bytes
  b56f9501a3d636852a39e6d468ee4ef34fec13d9bef0e8d98332c530e641b60a
preflight_model.json   26938251 bytes
  a98252f0da26181a01316d46fe314189a88b4a71006a1dcd4820dab5fbc9f2fd
independent_failure.json 389969 bytes
  34a460988d4874c77687f0825d16bcd2f3b090210f9fe13c70c5e9ea64209dba
compact_audit.json       517940 bytes
  19da7f0a282ae982b5c3f9ce8685562a6449703507fff70453f2693a595101ba
final_report.json        518026 bytes
  2fbb46d1efc8fa709158d76dab8ff7b1264b17e0076236bb940c4f1a11d1523c
stage_state.json            651 bytes
  0ae69ae938f5f6b2020af3a73488f12b6468e579f99d22f31eb06e60626828a8
stage_manifest.json        1198 bytes
  e4a151398f35154ea4c28aa7046302fb1c0d0838976cb0bbe23b825629ceebd6
```

Server enumeration found zero `*.json.gz` raw and zero snapshot files in the
R8R33 stage. The four downloaded compact/state/manifest files reproduce their
server hashes exactly. The 26.9 MB model and larger detailed evidence remain
on the server.

## 8. Frozen continuation

Before inspecting any R8R33 failed-row identity or computing a next-stage
model, R8R34 was frozen at checkpoint `1380fe1`:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R34_CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZING_FEEDBACK_PREFLIGHT_DESIGN.md
SHA-256
21d86f169cd92ede5263e2a9c6a4fc189e070f5cbfa1bd4dbd7d493fabf8f0c2
```

R8R34 is a new zero-new-TSC identity with a fixed response-blind 64-neighbor
causal local affine ridge model and a prospectively scaled dual-implementation
numerical gate. It does not reinterpret R8R33. A complete R8R34 pass may only
authorize a separately frozen fresh real-controller sentinel design. Gate A,
expert data, BC, DAgger, and residual RL remain blocked.
