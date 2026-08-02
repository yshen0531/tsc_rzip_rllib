# Stage4.2R3c3T13S11 causal calibration-conditioned braking report

## Final result

T13S11 completed its frozen zero-new-TSC development preflight. After a
semantics-preserving affine-rank reporting hotfix, its exact final route is:

```text
CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_INSUFFICIENT_PERSISTENT_OBSERVER_REDESIGN
```

The single causal coil-8 calibration signature is observable and supported,
but the frozen unwhitened interaction fit is severely ill-conditioned and
does not predict all later braking transitions. This is an observer/model
design failure. It is not a runtime, source-raw, restart, causality,
reporting, real-controller, or real-MPC failure.

## Exact revisions and paths

```text
branch
  codex/stage4_2r3c3t13s1-transition-sentinel
T13S11 design checkpoint
  e2c948c  Finalize T13S10 and preregister T13S11
non-vacuous support amendment before implementation
  ba67d17  Make T13S11 support gates non-vacuous
initial implementation
  75c2751  Implement T13S11 calibration-conditioned preflight
affine-rank reporting hotfix / final executed code
  c8ca408  Fix T13S11 affine rank audit

final staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s11_c8ca408
final audit directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s11_audits/
  stage4_2r3c3t13s11_causal_calibration_conditioned_braking_20260802_c8ca408
```

Exact hashes:

```text
amended preregistered design
  0289c514511afe8aeaa3d7db0c2ccb506c97728ba37477d31deb803cfa393e8d
final audit implementation
  a5fc84182a12a6004d93ebaa3db038f9593c3818f03afaf8bc4492182f0ba52d
final PACKAGE_MANIFEST
  dbd48be3660ba8232bb71ed9876502bdb7f727df2e537cb06b32a2a8d3fc3ac9
final SHA256SUMS
  c0f591ee39427f91ef34c8e5ae5401e03f32b92dc0a81de6177c6893dfe4f193
final audit JSON
  6e595fbd4e86276d449fc953edcb06b676bd282b6f0bd68d4e5ac3effe97ffbe
final audit log
  38dfc47da8a4e5cc900edb9f4e9215e3ab9a0acf8b6828f2705f2520e1534de1
final staging validation log
  27ae2e42e5a75fd166dfc62e93aa5a0cc71ffde422353703f812deba2bceedd6
final installed validation log
  8f8c07b10e5deab4594f045ecd0e4092fc7d809cb01f19bfb039ebb8a191f3d3
```

## Source, causality, and support

```text
T13S9 q1 raw / digest
  68 / 9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
T13S5 q2 raw / digest
  68 / 09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
combined source trace identity                           136 / 136
causal calibration signature / pre-effect causality         8 / 8
signed braking extraction / causality                      64 / 64
training calibration affine rank                            8 / 8
training braking-current basis rank                         8 / 8
held calibration affine support                             8 / 8
held braking-current support                               64 / 64
forbidden feature, trace, or model inputs                         0
exact disjoint signature/input aliases                           0
```

The signature used only the absolute same-trajectory issue-to-effect change
in R/Z/vR/vZ/Ip, measured coil-8 current, and known delay/slew. It did not
use a no-probe counterfactual, pair/history/q labels, wire/vessel currents,
future values, or outcomes.

## Final model result

```text
folds / interaction rank 12                               8 / 8
interaction condition <= 30                              0 / 8
minimum finite condition                              23,065.6
maximum finite condition                              91,958.0
non-vacuous tube pass                                     8 / 8
maximum tube/cap ratio                                 0.1471975
componentwise containment                               56 / 64
scaled relative error <= 0.10                           44 / 64
both response gates, ignoring invalid condition         36 / 64
formal passed rows                                        0 / 64
maximum finite scaled relative error                    1.7226245
```

The response failure is not caused only by the condition-number gate. The
single calibration transition does not supply a sufficient latent state for
the braking response even under the optimistic separate-trajectory
development construction.

## Hotfix classification

The initial `75c2751` output reported calibration rank only 4/8 because it
computed numerical rank after subtracting a floating mean. With exactly
three training signatures, an affine hull cannot exceed rank two, but tiny
mean-cancellation residue appeared as a third singular direction in the
hard folds. The `c8ca408` hotfix computes the equivalent affine rank from two
training differences. It changes no signature, PCA basis, model matrix,
fit, tube, support, prediction, threshold, raw input, or route.

```text
preliminary JSON SHA-256
  6297d8719547e6b7e817af80b053498aa19f34bfde3a3bfe978fa858732c2355
preliminary reported affine-rank pass                         4 / 8
final reported affine-rank pass                               8 / 8
all other summary values and route                        unchanged
```

This is a corrected statistics/reporting error, not an experiment-semantic
change. Both preliminary and final compact artifacts are preserved.

## Validation and scope

The initial complete package passed local and empty-directory 735-test
suites and server staging/installed 735-test suites. The hotfix added a
rank-regression test; local and both server packages passed 736 tests, with
one expected server/empty-package skip. Checksums, compile/import, strict
JSON, and source closure passed.

T13S11 ran no new TSC, Ray, `gotsc`, controller, optimizer, plant step,
snapshot, or raw trajectory. It validates neither calibration interaction on
one physical trajectory nor a controller. New histories, targets,
continuous parameters, noise, disturbance recovery, and long hold remain
unvalidated. Probe raw remains forbidden from expert data, and BC, DAgger,
and bounded residual RL remain blocked.
