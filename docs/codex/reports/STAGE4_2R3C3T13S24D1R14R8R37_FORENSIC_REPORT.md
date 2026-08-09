# Stage4.2R3c3T13S24D1R14R8R37 forensic report

## Verdict

R8R37 completed its fixed zero-new-TSC training-only diagonal innovation-gain
preflight with exact primary/independent scientific agreement. Its final
route is:

```text
TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_MODEL_FAIL_NO_TSC
```

This is a finite model/adapter-design failure. It is not a runtime,
deployment, source-authentication, raw-corruption, reporting, controller,
real-MPC, formal-control, restart, plant-reachability, or Gate A result.

## Frozen identity and validation

```text
design checkpoint          7bc61c0
implementation checkpoint  46fa888
package checkpoint         44a94ed
design SHA-256              6433312711b9b107a218bb5701ef6070a0dfbc482fd492d983437c32637fb843
package manifest SHA-256    821a5e07c25bcd6665c051655287478f8d2dc4eaa65024df87d98ad4cca5472b
SHA256SUMS SHA-256          bd56c9962408abdc4d0516271e9008e87c7171deed030473a394f177359687a2
```

Local source and empty-directory direct-copy validation, server staging, and
installed validation passed:

```text
declared hashes                               1189/1189
initial physical package files                 1191
JSON including manifest                         140
Python compilation                              464
server bash -n                                  447
focused tests                                  11/11
full tests                                  1463/1463
server isolated-evidence skip                     1 expected
```

Transfer used direct `scp -r` with no local archive operation. Local work
used the project venv and server work used only the existing server venv.

## Server execution boundary

Accepted run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r37_runs/
stage4_2r3c3t13s24d1r14r8r37_training_only_diagonal_innovation_gain_schedule_generalizing_preflight_20260809_44a94ed_v1
```

Primary, independent, and finalizer wrapper exit codes were `0 / 0 / 0`.
Their server logs are preserved with SHA-256:

```text
primary      a8dee8ec1e170890d1e4601eed7dcaef0d1adf2c91e7056a0a6a4891cbb5adfa
independent  c2ad8aaa43095b66637680cd51c766892606dd9aa2182582aca2122417b8b41d
finalizer    70c9da774cb3bd8f78bdff79cb6fb0d23701144d65ffe4376f17a53aa69d4f6a
```

The final stage contains exactly eight files and zero JSON.GZ raw or
snapshots. It executed zero Ray, `gotsc`, TSC, controller, or plant steps.

## Source and fit authentication

Both implementations independently reconstructed:

```text
trajectories                                      560
physical pairs                                      8
history contexts                                   16
schedules                                          35
interval records                                 3360
cardinality heads                           1161/1161
minimum training rows per head                    210
whole-pair state support                          8/8
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

The 43 exclusion folds produced 1,075 scalar gains. Across them the minimum,
mean, and maximum were `0.3050632893 / 0.7783460704 / 1.0`. Projection states
were 517 interior and 558 projected upper, with no lower or denominator-floor
projection.

## Exact model result

```text
whole-pair maximum point
  [0.0107254697,0.0181541107,149.299444,0.0578928250,0.0830865845]
whole-pair maximum tube
  [0.015,0.0226926383,3000,0.0723660313,0.103858231]
whole-pair containment                         72785/72800

whole-schedule maximum point
  [0.0112621299,0.0250644243,168.329283,0.0692899234,0.107082218]
whole-schedule maximum tube
  [0.015,0.0313305304,3000,0.0866124043,0.133852773]
whole-schedule containment                     72800/72800
```

The model and combined-tube gates failed. Pair Z/vR/vZ and schedule Z/vR/vZ
point or tube limits remained outside the frozen caps.

Aggregate adapted/cold normalized L1 ratios were `0.4190173318` for
whole-pair and `0.6883697917` for whole-schedule. Every pair fold improved,
but the schedule no-regression gate failed:

```text
R8R28_g2_UUUU  1.3099695898
R8R28_g2_VVVV  1.3316953648
```

Thus both the absolute model gate and the all-fold usefulness gate reject the
fixed architecture.

## Independent agreement

```text
maximum bank absolute difference        0.0
maximum scaled gain difference           7.8876037276e-15
maximum scaled prediction difference     6.1062266354e-15
maximum scaled tube difference           2.7755575616e-15
maximum scaled metric difference         2.7755575616e-15
bank / neighbor / projection / route     exact
```

All values pass the frozen `1e-9` dual gate. The FAIL is therefore scientific,
not numerical reproducibility failure.

Final server file hashes are:

```text
primary summary  aa0657b445df0210b8457ee09f28ac97e348e54ae31a083f0079f3525fdc8b54
primary detailed 1d14491644965724a85755dea533866fa5cffbd3ea993a733237e675a52211c1
model artifact   743b79d97bb3d7a1d948859d26e0bd8b5b510ff2700e8a73dd59b977f4205b7d
independent      0677d6c02da3bef19b630d4bb6c32e1ca4a7ed42c76fc63e63605236d64227f2
compact audit    5ab03b69c032f184331e69abe69ff02a7cc0fb91d051015704fe18e89fa8dac2
final report     56b327b04d798e3645ce0d6dd2e3f85ebfd57831403588e948426047e264efa9
stage state      a16bcb9769185eed3a7550a08e8fad6710978873ab1f9093e93d262f6d1965ff
stage manifest   46bddcee86d12fb490197a7505e8e66fb6762b258468e6d92f1a7cfc5b92656b
```

## Causal boundary and next direction

Post-result read-only interval decomposition found that the maximum
whole-pair vR and vZ tubes already occur at interval 0, where the strict
causal innovation correction is necessarily zero. No alternative gain can
repair that part of the model gate. Pure gain tuning is therefore closed as
the next route.

Before any R8R37 result was opened, conditional R8R38 was frozen at
checkpoint `7aa9383`, document SHA-256
`d2c86894db9f48969a96e1b8e8ebec265a598a12aaef058f74aefbf757b88caa`.
Its source requires an exact R8R37 PASS, so it is blocked and must not be
implemented.

The next eligible design question is a zero-new-TSC cold-predictor
discriminator using the complementary authenticated axes: R8R31's global
expanded ridge passed whole-pair but failed whole-schedule, while the local
k64 model passed its original primary whole-schedule gate but failed
whole-pair and later required numerical repair. Any fusion must be frozen
under strict held-fold isolation and independently recomputed before use.

That exact next question was frozen before any ensemble computation as
R8R39 at checkpoint `3fa8397`, document SHA-256
`f6005ee27d87c0a72043fc8bdc75d16bd074baa9d405a1d72e545e72f0003bbb`.
It fixes a response-blind `0.5/0.5` global-ridge/local-constant cold ensemble
inside every exclusion fold, with no weight, gain, feature, ridge, neighbor,
distance, or outcome search.

Gate A, expert data, BC, DAgger, residual RL, and every other learning route
remain blocked. All R8-family trajectories remain forbidden from learning.
