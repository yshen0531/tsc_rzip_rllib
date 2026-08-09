# Stage4.2R3c3T13S24D1R14R8R48 forensic report

## Verdict

R8R48 completed its exact zero-new-TSC q0-to-transport causal-bridge support
audit with primary/independent agreement. Final route:

```text
Q0_CALIBRATION_TO_TRANSPORT_CAUSAL_BRIDGE_SUPPORT_ABSENT_FRESH_SENTINEL_REQUIRED
```

The authenticated 560-trajectory bank contains the exact q0 reference in all
16 contexts, but contains zero physical trajectories that preserve that q0
prefix through task step 12 and then issue any of the 16 fixed nonzero
transport candidates. This is an experiment-coordinate/support result. It is
not a runtime, deployment, source, raw, restart, reporting, model-accuracy,
controller, formal-control, real-MPC, plant-reachability, or Gate A failure.

The prospectively frozen conditional R8R49 source gate is satisfied. R8R48
authorizes only that fresh finite bridge-identification sentinel, not a model
fit or real controller.

## Identity and package validation

```text
R8R48/R8R49 conditional design checkpoint       8427bfe
R8R48 design SHA-256
  23fa8ac8f0c6ea73e34b40aa5680bfe79061451099ba2e0d89c2354fa291f7de
conditional R8R49 design SHA-256
  16f321003e7801ac36a5bc97bdb66928a37f469ffb01b31aa09136c2e4a46173
R8R48 implementation checkpoint                 b80a50a
R8R48 package checkpoint                        b2870d7
PACKAGE_MANIFEST.json SHA-256
  e592a8aa843bcacc0813763028884e7f0d6d455680f76701cab3d1333e1891fc
SHA256SUMS SHA-256
  4a7d55304f1fa32bb2caa1e82c8d15bcc16d79c3f1d0d1dbff9bd8307b9b6f2e
```

Local project-venv source validation passed focused `9/9` and full
Windows-resource-shimmed `1533/1533`. A fresh empty direct-copy tree initially
contained 1,234 physical files: 1,232 declared files plus manifest and sums.
It passed:

```text
declared hashes                                  1232/1232
strict JSON including manifest                          146
Python compilation                                      482
focused tests                                           9/9
full tests                                      1533/1533
expected isolated-package skips                           1
```

The first empty-tree validation wrapper built its checksum dictionary with
digest/path reversed and raised an assertion even though a subsequent
diagnostic found zero missing, extra, or bad hashes. The corrected fail-fast
wrapper reproduced every check above. This was a local validation-wrapper
error, not a package or code error.

Transfer used direct `scp -r` of a fresh cache-free tree. No local or server
archive was created or extracted. Server staging and installed validation
both passed:

```text
declared hashes                                  1232/1232
strict JSON including manifest                          146
Python compilation                                      482
bash -n                                                 453
focused tests                                           9/9
full tests                                      1533/1533
expected isolated-package skips                           1
```

The server validator reached its final explicit PASS, but the local
PowerShell capture pipeline returned nonzero after wrapping unittest stderr
progress as `NativeCommandError`. Later commands used separate stdout/stderr
and the real SSH exit codes. This was a local log-capture error after complete
server validation, not a server/test/deployment failure. Local execution used
only the project venv; server execution used only:

```text
/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python
```

## Exact server result

Run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r48_runs/
stage4_2r3c3t13s24d1r14r8r48_q0_to_transport_causal_bridge_support_audit_20260809_b2870d7_v1
```

Both primary and independent authenticated final R8R46's eight exact hashes
and rebuilt the exact bank:

```text
trajectories / contexts / schedules / intervals       560 / 16 / 35 / 3360
bank digest       a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest    80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest     0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

Physical bridge enumeration produced:

```text
q0 reference contexts                                      16/16
nonzero candidates                                             16
required context/candidate cells                              256
exact authentic physical bridges                            0/256
missing cells                                             256/256
metadata-only cells                                            0
later-interval substitute cells                                0
exact-prefix trajectories per context                          1
q0 prefix digest
  25d1c029291ddfc038e143e9d34588d03afea19bb43e2cc5c7ff16fdc19a720a
bridge matrix digest
  3c53eb06a8657e8ce3ad82989ccbedb4ef3a89a1011943d19ac27c8859a7a80f
```

Every context's one exact-prefix trajectory is its R8R7 q0 baseline itself.
No other immutable trajectory shares that physical prefix through step 12.

The deliberately separate geometric diagnostics were:

```text
44D feature-supported cells                              256/256
global 8D transition-hull-supported cells                 32/256
authentic physical bridge cells                            0/256
geometric diagnostic digest
  1447b8bd55c141f6cffa73857c82318a0eb0b63a83b2be10b76251e7ce40e011
```

Thus feature support was universal while physical support was absent. The
global hull supported only a subset and could not substitute for executed
q0-prefix transitions.

## Independent agreement and final evidence

Independent reconstruction agreed on source, bank, prefix, bridge matrix,
geometry, route, and outcome. Maximum geometric distance difference was
exactly `0.0`.

Final server hashes:

```text
primary summary   b8a9109cf8bed6871fa9887915b9f662b423c9e243505367fda473c5c1f4e42d
primary detailed  ded77dab02c856c22199afbd58dffacdd0225958e8ec8546eec0c9a5567db5ca
independent       9501976b7dc4e4fee1b256611741006310b1cdbfa3913b3c4e3869eae66bb263
compact audit     25af6f5057ca6fc4fb1d18d7f220779a1d4408275f60cb22cc400c2d93acaf58
final report      a80a00e660cf188bb00ce9f68734cd4c4f87d086bbab672187f4e3e82eca0e47
stage state       7e6fa3b9d3a4714e21afba1155f131c847d4918a90d339ec3b1a236602824e14
stage manifest    781403f9d2ff5f48be56ea04f0f46a6cd89302efea0984fc05fe7b7112d0010c
```

The final stage contains exactly seven files totaling 440,250 bytes and zero
raw, JSON.GZ, snapshot, or spec files. It executed zero fit, optimizer, Ray,
`gotsc`, TSC, controller, or plant step. Compact evidence was copied directly
to:

```text
artifacts/server_audits/r8r48_20260809_b2870d7_v1_final/
```

## Scientific boundary

R8R48 shows that R46's q0-calibrated controller architecture was being judged
with a development bank that lacked its exact first transport coordinate.
This does not retroactively change R8R46's failed frozen usefulness gate and
does not establish that a fresh bridge model will work. It identifies the
next missing evidence rather than tuning another gain on unsupported rows.

R8R49 is conditionally frozen as 16 contexts by all 16 nonzero candidates,
with q0 at step 10, causal measurement through step 12, one transport issue,
and exact stored-center return. A R8R49 PASS may authorize only a separately
frozen zero-TSC bridge model/tube preflight. Gate A, expert data, BC, DAgger,
residual RL, and Gate B remain blocked. Every R8-family trajectory remains
forbidden from learning data.
