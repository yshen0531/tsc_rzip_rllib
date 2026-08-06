# Stage4.2R3c3T13S24D1R14R8R1 forensic report

## Result

R8R1 is final as:

```text
FIXED_CANDIDATE_SHORT_HORIZON_FAIL_CAUSAL_INNOVATION_REQUIRED
```

The primary and structurally independent zero-new-TSC recomputations agree
exactly.  The fixed R8-selected cold-start candidate failed every tested
common horizon.  The 80, 100, and 120 ms controller-useful candidates passed
only 788, 770, and 763 of 912 whole-pair response rows.  The 40 and 60 ms
horizons were diagnostic only and also failed.

This is a short-horizon response-center/model-design failure.  It is not a
runtime, deployment, source-authentication, raw-corruption, restart,
causality, real-controller, TSC, MPC, formal-control, or plant-reachability
result.

## Code and package identity

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
prospective design checkpoint
  bd7acfa
initial implementation checkpoint
  21c3087
initial deployed package checkpoint
  c2ed69f
independent state-path repair checkpoint
  ea4b404
accepted audit package checkpoint
  892ac7c
design SHA-256
  0502e26ef7c6388ff107482946a81bfdd1696e5739f866365bb0a49e57927751
accepted PACKAGE_MANIFEST.json SHA-256
  aaf66412a6787ef73fcef72f0087b1038286fadb32222129fc2c22e79599bfa2
accepted SHA256SUMS SHA-256
  a059ad97c3b4e9834f9fc9a8e5420958076cf8ccad21e8b651c328f2f0fc1e71
declared package files
  921
```

The focused repair changed only two references from the nonexistent
`paths["state"]` entry to the inherited real path
`paths["stage"] / "stage_state.json"`, plus the corresponding assertions.
It changed no source raw, fixed candidate, fold, horizon, gate, controller,
action, or scientific result.

## Validation and deployment

The accepted local boundary used only the repository virtual environment:

```text
py_compile of changed files                              PASS
compileall of package/config/script/test/audit sources   PASS
focused unittest                                         7 / 7
full Windows-shim unittest                           1157 / 1157
package hashes                                          921 / 921
strict package JSON                                     101 / 101
empty direct-copy focused unittest                         7 / 7
empty direct-copy full unittest                     1157 / 1157
empty direct-copy expected isolated-data skip                 1
```

The Windows full suite loaded the repository's existing `tests/conftest.py`
`resource` compatibility shim before discovery.  The earlier unshimmed 27
Linux-only import errors were an invalid Windows entrypoint, not a regression.

The package was transferred as individual files without an archive.  Server
preflight confirmed the canonical project and existing simulation virtual
environment.  The accepted server validation then passed:

```text
package hashes                                          921 / 921
bash syntax and package verifier                              PASS
targeted Python compile and import                            PASS
strict package JSON                                     101 / 101
focused unittest                                         7 / 7
full unittest                                        1157 / 1157
expected isolated-data skip                                   1
```

The server validation log SHA-256 is
`2710d405bfce254e1e2734fb00d928601f8fb0a35bb3b9ffab470f0cf5e462fe`.
Neither local nor server validation used global Python.

## Remote evidence

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
R8 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8_runs/
  stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_20260804_5e57f60_v2
R8R1 output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r1_runs/
  stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator_20260805_c2ed69f_v1
primary log
  logs/nohup/stage4_2r3c3t13s24d1r14r8r1_primary_20260805_c2ed69f_v1.log
preserved failed independent log
  logs/nohup/stage4_2r3c3t13s24d1r14r8r1_independent_20260805_c2ed69f_v1.log
accepted independent log
  logs/nohup/stage4_2r3c3t13s24d1r14r8r1_independent_20260806_892ac7c_v2.log
server validation log
  logs/stage4_2r3c3t13s24d1r14r8r1_server_validation_20260806_892ac7c.log
```

Large R8 raw remains on the server.  Compact R8R1 evidence is retained at:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r8r1_20260806_892ac7c/
```

## Immutable source boundary

The accepted postcheck authenticated and strictly parsed the full R8 training
extension directly from its gzip JSON raw:

```text
fresh R8 training raw                         624 / 624
fresh training raw bytes                     19,725,920
fresh training inventory digest
  b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762
combined R2/R4/R6/R8 responses                912
complete physical pairs                        12
pair-history contexts                          24
R8 calibration raw                              0
R8 holdout raw                                  0
heldout_outcomes_opened                     false
```

The fixed candidate remained exactly PCA rank 4, RBF median-distance
multiplier 2.0, and ridge 0.1.  All twelve outer folds held out one complete
physical pair.  Forbidden predictor input count remained zero.

## Frozen horizon result

The primary aggregate reconstructed from raw is:

| Horizon | Role | All response gates | Max relative L2 | Min cosine | Peak-ratio range | Point max | Tube |
|---:|---|---:|---:|---:|---:|---:|---|
| 40 ms | diagnostic | 832/912 | 1.6042950615 | -0.0896228746 | 0.2515140683--2.1303641273 | 0.0346914290 | PASS |
| 60 ms | diagnostic | 804/912 | 1.5913495610 | -0.1505668246 | 0.1785241117--2.1303641273 | 0.0508113501 | FAIL |
| 80 ms | useful candidate | 788/912 | 1.5875164675 | -0.0957882142 | 0.1785241117--2.1303641273 | 0.0508113501 | FAIL |
| 100 ms | useful candidate | 770/912 | 1.5504662206 | -0.1190657030 | 0.1785241117--2.1303641273 | 0.0508113501 | FAIL |
| 120 ms | useful candidate | 763/912 | 1.5319201747 | -0.1523734347 | 0.1785241117--2.1303641273 | 0.0508113501 | FAIL |

Actual and predicted signal passed 912/912 at every horizon.  Predicted
canonical and operational geometry passed all 192 branches at every horizon.
Actual 40 ms geometry failed only the unchanged condition gate, with maxima
21.4608013148 and 20.7541023938; actual geometry passed at 60--120 ms.
Therefore shortening did not repair response direction or relative amplitude,
and the 40 ms diagnostic also lacked complete measured condition margin.

The formal 250/270 ms arrival deadlines and 350/370 ms hold endpoints were
not changed.  R8R1 did not run formal tracking or a controller.

## Independent audit and repaired defect

The initial independent invocation stopped before fitting or output with
`KeyError: 'state'`.  Its complete 740-byte log SHA-256 is
`9cd7d740a38063bbe992ce0e0751b319a70a29f2bea57823f26b4860b2bbc1ea`.
This was an audit-tool path/runtime defect only.

After the focused repair, the independent audit ran under a new log identity
in the same immutable output directory.  It did not rerun or alter R8 raw and
did not run an R8R1 trajectory.  Its contract is:

```text
independent audit passed                              true
scientific_gate_passed                               false
primary numerical agreement                           true
primary outcome agreement                             true
model artifact presence/contract agreement            true
selected horizon                                      none
new raw                                                   0
Ray / gotsc / TSC / plant advances                0 / 0 / 0 / 0
model artifact                                      absent
route
  FIXED_CANDIDATE_SHORT_HORIZON_FAIL_CAUSAL_INNOVATION_REQUIRED
```

The independent JSON and accepted log are byte-identical, SHA-256
`3f378dba6eb1304422397b44a347e34d35827624ca6ea61791e85f16e7a5341c`.
The primary detailed and summary hashes are respectively
`bd0041c3e16b56fce28abb80526bb5f1628ee74f6f5b52a70aaa07019e86a1ee`
and `5d6c2eb4282dba1ba29e25624b147af8b760c8cfbe5fd085374cf54110de6204`.
The final 504-byte stage state hash is
`3f25e7070fd56243b1581b7da17cb433e0876821437bc9e7e098cdf4626d869f`.

## Classification and authorization boundary

```text
runtime/environment error in source R8 raw                 no
accepted package/import/deployment error                   no
source/raw/snapshot corruption                             no
initial independent audit-tool path defect                yes, repaired
primary/independent reporting disagreement                 no
restart or causality failure                               no
fixed cold-start short-horizon model/design failure       yes
real controller / MPC / formal-control result             none; not run
plant reachability conclusion                              none
calibration / holdout result                               none; unopened
```

R8R1 is immutable and may not be reinterpreted by tuning another cold-start
candidate after the result.  The next authorized direction is a separately
prospectively frozen causal online innovation/adaptation study or a new
identification design.  A development pass can authorize only a fresh
authentic interaction sentinel.  MPC, expert data, BC, DAgger, bounded
residual RL, and Gate A remain blocked.  Every probe trajectory remains
forbidden from expert datasets.
