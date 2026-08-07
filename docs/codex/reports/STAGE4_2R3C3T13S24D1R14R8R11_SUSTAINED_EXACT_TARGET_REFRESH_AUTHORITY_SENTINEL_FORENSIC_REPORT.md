# Stage4.2R3c3T13S24D1R14R8R11 forensic report

## Result

R8R11 is final as:

```text
SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_INSUFFICIENT_ASYMMETRIC_SEQUENCE_REDESIGN_REQUIRED
```

The accepted server stage is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r11_runs/
stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel_20260807_863692b_v1/
stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel
```

R8R11 executed exactly 96 fresh authentic TSC trajectories in its frozen
two-phase order. All 96 passed the execution, restart, causal-prefix,
calibration, exact Card15 issue/refresh/cancel, current, finite-state,
full-horizon, forbidden-input, and raw-integrity gates. The formal authority
gate nevertheless failed: none of the ten failed baselines was repaired and
the held oracle remained at the baseline coverage of `6/16`.

Every R8R11 trajectory is permanently forbidden from expert, BC, DAgger, and
RL datasets.

## Prospective identity and validation

The sustained-action question, matrix, safety stops, formal gate, and routes
were frozen before implementation or outcome inspection at checkpoint
`d53d38d`. The design-document SHA-256 is:

```text
43a2ad925c78c4656a68e27a7243daf952edab1170c811c85c3d679ca1ab1707
```

Implementation and initial package checkpoints were `3eefac8` and `863692b`.
The reporting-only source-prefix hotfix was implemented and packaged at
`41001a7` / `c2c206e`; its qualification extension was implemented and
packaged at `41b184f` / `96e6174`. The primary controller module remained
byte-identical throughout at:

```text
dd4ed57184d7ce6543b2e93f1425c7a95c31e86df0948a922c8d06e99190fafd
```

Validation used only the project virtual environment locally and the existing
server virtual environment. The final accepted package contained 1,032
declared files and passed:

```text
local project-venv focused / full                       9/9 / 1252/1252
empty direct-copy focused / full                        9/9 / 1252/1252
server staging focused / full                           9/9 / 1252/1252
installed server focused / full                         9/9 / 1252/1252
expected isolated-evidence skip                                      1
declared package hashes                                      1032/1032
```

The package was transferred as an ordinary directory tree, without local
archive creation or extraction. One per-item SSH transfer attempt timed out
and changed no scientific state; a single direct recursive copy then
completed. An initial remote install command was rejected by shell argument
parsing before installation; the explicit manifest-path copy completed and
both staging and installed validation passed. These were deployment
interruptions, not experiment failures.

## Authentic execution and safety evidence

The frozen safety phase completed before qualification authorization:

```text
safety raw                              24 files / 759481 bytes
  137fc4024b720b3bd105671051758d8f8ea26014250ce72a9431702af17428da
runtime / full horizon / causal prefix                          24/24
calibration / event / exact center-target                       24/24
maximum issue / cancel increment                   0.1740740740740743
maximum refresh increment                         0.0000037037037048793
maximum current utilization                                     0.3920
```

Only after primary and structurally independent safety agreement was the
qualification phase authorized. It then completed:

```text
qualification raw                       72 files / 2288228 bytes
  82958eb8c4e49ff278c4223b8d2d21df9080cfadae02fd65596c727787832a09
runtime / full horizon / causal prefix                          72/72
calibration / event / exact center-target                       72/72
maximum issue / cancel increment                   0.1742592592592594
maximum refresh increment                         0.0000037037037048793
maximum current utilization                                     0.3924
forbidden trace rows                                                0
```

There were no structured safety stops, solver failures, saturation failures,
raw parse failures, or incomplete trajectories. No R8 or R8R1 trajectory was
rerun.

## Reporting-only source-prefix repair

The original phase audits compared source-only R4/R8R7 wrapper labels against
the new R8R11 trace. Those labels do not participate in execution, state,
action, restart, calibration, or physical-prefix semantics and are absent by
construction from the new wrapper. The initial audits therefore stopped with
false source-trace mismatches after the real trajectories had completed.

The accepted reporting repair excluded only those authenticated source-only
wrapper fields. It preserved every executable field and reported:

```text
phase             wrapper-only differences   non-wrapper differences
safety                                  3120                         0
qualification                            9360                         0
corrected exact prefixes               24/24                     72/72
new raw created by repair                  0                         0
formal outcomes opened by repair       false                     false
controller/action semantics changed    false                     false
```

The raw inventories were byte-identical before and after each repair, and the
primary controller hash above was unchanged. The independent auditor used a
separately written semantic projection and exactly reproduced both corrected
phase audits. This is a statistics/reporting defect, not a runtime, restart,
causality, plant, or controller defect; no TSC rerun was scientifically or
operationally warranted.

## Frozen formal-authority result

After all 96 raw files passed the dual integrity gates, the unchanged formal
contract was opened and recomputed through both frozen metric paths:

```text
contexts                                                        16
formal rows                                                     112
matching baseline formal pass                                  6/16
failed baselines                                                  10
candidate formal-pass trajectories                            36/96
strict best-margin improvement on failed baselines             10/10
best gain minimum                                  0.000249522056861
best gain median                                   0.000485133333335
best gain maximum                                  0.001795445790614
failed baselines repaired                                      0/10
held-oracle formal pass                                        6/16
maximum metric-path signed-margin difference                      0
```

All 36 candidate formal passes occurred in contexts whose unchanged baseline
already passed. Every failed baseline improved under at least one measured
candidate, but none crossed the unchanged formal gate. Extending the exact
direction-zero target by one additional plant interval therefore did not add
finite measured oracle coverage.

## Independent agreement and fingerprints

The structurally independent final audit separately rebuilt raw inventory,
formal metrics, row matching, held-oracle aggregation, scientific gate, and
route. It agreed with the primary on every outcome and numerical field, with
maximum absolute signed-margin difference zero. Accepted compact SHA-256
values are:

```text
primary detailed
  aecd3a9e19bc8349398d885b78f6ef6cdbb20974878571036f4062f7f8b71ce1
primary summary
  8214b9c0340f5562a181a42cb2d4e30ca2f1dd79900f1089fae3422ef3531e9b
independent
  13f4436fff270a5eba1e91790522e3a490df59a879d9bab7636a6c3dc32b7391
final report
  903cdb4f01ff0e124081230f92be2d473e38bde8d0cc0cdb082d71f900e8f3b5
stage manifest
  aaa8062421b9e1a5fa92641bffdf27684229a1db31f8a1a6d98bcde997aa8107
stage state
  d805d7de4822678f17b6a814b3cb095ad59b96001db4ae81fd8e047cf8659e24
safety reporting repair
  6d1948959288858d0e3c57f1bac7638dae696969c1b718396886c071ee7b8b7e
qualification reporting repair
  aab1f08bd6d2226287fedba3bc3b3bddacccc868c8d481cc8e4f6dde75e6b248
```

The compact audit mirror is under
`artifacts/server_audits/stage4_2r3c3t13s24d1r14r8r11_20260807_96e6174`.
Large raw trajectories remain only on the server.

## Classification and handoff

R8R11 is a finite sustained direction-zero action-authority design failure.
It is not a runtime, deployment, restart, causality, Card15, current, raw,
snapshot, solver, saturation, reporting, formal-evaluator, plant-restart,
real-MPC, safety, or global-reachability failure. The small favorable margin
movement does not justify weakening the formal timing or tolerance contract.

The R8R11 identity is immutable and may not be tuned, resumed, or enlarged.
The next design must use a genuinely asymmetric or multi-direction causal
sequence under the unchanged hard contracts and a new prospectively frozen
identity. A read-only or fresh sentinel PASS may authorize only a separately
frozen causal controller design; Gate A, expert data, BC, DAgger, and residual
RL remain blocked.
