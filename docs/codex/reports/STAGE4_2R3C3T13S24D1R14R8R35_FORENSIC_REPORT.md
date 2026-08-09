# Stage4.2R3c3T13S24D1R14R8R35 forensic report

## Final classification

R8R35 is final as:

```text
CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_MODEL_FAIL_NO_TSC
```

The fixed response-blind `k=64` local-constant predictor plus a unit-gain,
one-completed-interval last-innovation correction substantially reduced
aggregate held error, but did not pass the unchanged whole-pair or whole-
schedule point/tube gates. Its separately frozen schedule no-regression
usefulness gate also failed in three schedules.

This is a finite causal model/adapter-design failure. It is not a runtime,
deployment, source-authentication, raw, restart, causality, numerical-
reproducibility, reporting, controller, real-MPC, formal-control, plant-
reachability, or Gate A result.

## Prospective identity and implementation

The design was frozen before R8R34 detailed metrics were opened:

```text
design checkpoint          7c83240
design SHA-256             ad451b7b14ea1e3dcd84c029042b58068a4879f891e0cbcedd69f546f623fbbf
implementation checkpoint  ff2340e
package checkpoint         70236b3
```

The implementation used no slope, response weight, search, clipping, decay,
or cross-trajectory state. Every held interval was predicted before reading
any target from that interval. Only the previous completed interval's final
measured innovation updated the next prediction, with fixed gain one and
memory one.

Before any R8R35 exit code, state, summary, prediction, metric, gate, or route
was opened, the conditional R8R36 controller-preflight design was frozen at
checkpoint `f0eb69f`, SHA-256
`0c2f3e6b048d05b087a9ce9c746df057f2f70eab5dfdfafefe7e10ac10aa4ac9`.
Because R8R35 did not pass its source scientific route, R8R36 is blocked by
its own prospective source gate and was not implemented or executed.

## Package and validation evidence

The final package declared 1,181 source files and was copied directly into a
fresh local empty directory. No local or server archive was created or
extracted.

```text
package manifest SHA-256  3247a888f883e32cba91c07937791e69c3b3132eced101c8835b0e841ad59d83
SHA256SUMS SHA-256         b851a7fa557f210680ad017ea3e81adea83ad2b35b80b9592ac33d519eb7fa5a
declared hashes            1181/1181
physical package files     1183
JSON files                 139 including PACKAGE_MANIFEST.json
Python files compiled      461
declared shell bash -n     446/446 on server
focused tests              11/11
full tests                 1452/1452
```

Local source validation had zero skips. The isolated empty-copy, staging, and
installed server validations each had one expected isolated-evidence skip.
Both hosts used only the existing project/server virtual environments.
Staging and installed manifests and hash tables reproduced the exact SHA-256
values above.

## Exact server execution identity

R8R35 used this new zero-TSC output root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r35_runs/
stage4_2r3c3t13s24d1r14r8r35_causal_last_innovation_local_constant_schedule_generalizing_preflight_20260809_70236b3_v1
```

Primary, independent, and finalizer each ran only as a new log identity in
that output. Their wrapper exit codes were all zero. The final stage contains
eight files and no raw, JSON.GZ, or snapshot:

```text
primary summary       267c3017f7116ce5d29dabd51130632f851780ace600c01b79c8147c1ad56b17
primary detailed      4e73579a96f7c889348738cade4ccafc91e6afec55b0f83e7e5fb7a316743ab4
preflight model       6f9b48e6b68a79861e1d16dfb896ea5f922effb79fb3085ab1d4ea2a9eb00d4e
independent audit     e5d69358316447ec971e2dc5bd200441e431250e05f63cdc43bd500c38403aed
compact audit         3c564fb062df957409d9da1d7079fc46be9b3ceba4c40526e4946cea0066e8cb
final report          26f58434d666b9762846833e14b1b8bdb91b5ac6ef122361a23c0c4880d880fa
stage state           2f3c8fd9087260b1bc2f789e3061ed9199250b30d22db91f728a6da1e6cd4946
stage manifest        2b51b3cd853aab81bce955d0b73eb13b6b0bf5ab42fd92d9fc4e667820c92a95
```

## Source bank and integrity gates

Primary and independent paths independently authenticated and rebuilt the
same finite bank:

```text
trajectories                                      560
history contexts                                   16
schedules                                          35
interval records                                 3360
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

All 1,161/1,161 local-cardinality heads passed, with minimum training count
210. All eight held whole-pair state-support folds passed. No forbidden input,
nonfinite prediction, source mutation, runtime exception, TSC, controller,
plant step, raw, or snapshot occurred.

## Whole-pair result

The held whole-pair adapted model failed the unchanged point/tube and exact
containment gates:

```text
maximum physical point error
  [0.0107254697, 0.0181541107, 149.299444, 0.0578928250, 0.0830865845]

maximum reserved physical tube half-width
  [0.015, 0.0226926383, 3000, 0.0723660313, 0.103858231]

reserved containment                         72786/72800
reserved containment rate                    0.9998076923
state support                                      8/8
```

Against caps `[0.015,0.015,3000,0.05,0.05]`, Z, vR, and vZ point errors
failed. Against tube caps `[0.025,0.025,5000,0.08,0.08]`, vZ failed. Four
components missed reserve in held pair `p9_q1_a0p900_gap3_settle4` and ten
missed in `p9_q2_a0p900_gap4_settle4`; all other held-pair components were
contained.

## Whole-schedule result

The held whole-schedule adapted model also failed:

```text
maximum physical point error
  [0.0112621299, 0.0250644243, 168.329283, 0.0692899234, 0.107082218]

maximum reserved physical tube half-width
  [0.015, 0.0313305304, 3000, 0.0866124043, 0.133852773]

containment                                      72800/72800
```

Containment passed, but Z, vR, and vZ point caps and tube caps failed. The
combined pair/schedule tube was
`[0.015,0.0313305304,3000,0.0866124043,0.133852773]`, so the combined tube
cap failed.

## Adaptation usefulness result

The fixed causal update had substantial aggregate effect over all 13,440
post-initial rows:

```text
whole-pair cold normalized L1                 24249.4195822
whole-pair adapted normalized L1               9111.91056024
whole-pair adapted/cold ratio                     0.375757883
whole-pair no-regression folds                         8/8

whole-schedule cold normalized L1             10304.4815344
whole-schedule adapted normalized L1            7618.37053380
whole-schedule adapted/cold ratio                  0.739325944
whole-schedule no-regression folds                    32/35
```

Both aggregate ratios beat the frozen `0.95` threshold. The schedule family
failed only the separately required every-fold no-regression gate:

```text
R8R14_d0_p       1.03581115934
R8R28_g2_UUUU    1.12480205858
R8R28_g2_VVVV    1.13977924958
```

This is evidence that causal innovation is measurably useful in this finite
bank, but a fixed unit gain is not uniformly schedule-safe or accurate enough
for the unchanged model gates. It does not authorize controller execution.

## Independent reproduction

The independent implementation passed every frozen integrity comparison:

```text
maximum bank absolute difference                    0.0
maximum scaled prediction difference                7.2164496601e-15
maximum scaled tube difference                      2.7755575616e-15
maximum scaled metric difference                    2.7755575616e-15
neighbor identities                                 exact
route and scientific outcome                        exact
frozen scaled tolerance                             1e-9
```

Unlike R8R34, R8R35 has no independent numerical-reproducibility failure.
The final artifact's `passed=true` means execution/integrity completion, not
scientific qualification; `scientific_gate_passed=false` and the model-fail
route are authoritative.

## Authorization boundary

R8R35 authorizes no R8R36 execution, controller, TSC sentinel, Gate A,
expert data, BC, DAgger, or RL. The next eligible causal-model design must
retain the exact whole-pair/schedule, point, tube, containment, support,
formal, independent, zero-TSC, and learning-prohibition gates. It may use the
prospective evidence that a bounded training-only gain is needed; it may not
weaken caps or tune against held R8R35 rows.

All R8-family trajectories remain forbidden from learning data.
