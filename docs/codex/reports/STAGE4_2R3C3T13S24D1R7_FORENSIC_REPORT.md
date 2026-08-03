# Stage4.2R3c3T13S24D1R7 final forensic report

## Result

D1R7 is a clean zero-new-TSC preflight PASS after one reporting/authentication
hotfix. It authenticates the fixed temporal-basis substitution and freezes 108
D1R8 safety-sentinel specifications. It does not execute a controller, plant,
Ray, `gotsc`, or TSC and does not establish a real sequence or control result.

The final route is:

```text
TEMPORAL_BASIS_SUBSTITUTION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

This route authorizes only prospective D1R8 design. It does not authorize
D1R8 execution by itself, a replacement identification campaign, MPC, expert
data, BC, DAgger, or RL.

## Code, package, and server identity

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition

original implementation checkpoint
  143f9ba
initial package checkpoint
  1ca3c11
authentication hotfix checkpoint
  da578de
final package checkpoint
  0c2311a

scientific config revision
  r42r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1
deployment package revision
  r42r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1h1

final PACKAGE_MANIFEST.json sha256
  e0f50ff41f53555d3e91f74ffae5d2e98cb3a2d301710629cabe61de186948d5
final SHA256SUMS sha256
  23b8f7d40d78eca096211349783c7208eaabca7e157e684611860760d2264dbf

remote package
  /home/yangshen0711/tsc_software/
  stage4_2r3c3t13s24d1r7_package_0c2311a_v1

official output 1
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r7_audits/
  stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_20260803_212200_0c2311a_v1

official output 2
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r7_audits/
  stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_20260803_212200_0c2311a_v2
```

The downloaded compact evidence is under
`docs/codex/audits/stage4_2r3c3t13s24d1r7_20260803_0c2311a/server_compact`.
The authoritative large candidate table, detailed output, and all raw inputs
remain on the server.

## Initial stopped attempt and hotfix classification

The initial package `1ca3c11` stopped before producing any accepted output.
Its primary auditor incorrectly required every authentic S24 structured
cancellation failure to be slot 3 at task step 18. Direct server-side parsing
of all 600 S24 raw files showed the immutable 54 failures were all genuine
`sequential_cancel`, `passed=false`, and strictly above the 0.25 incremental
cap, distributed as:

```text
slot 0 / task step 11    12
slot 1 / task step 14    16
slot 2 / task step 16     4
slot 3 / task step 18    22
```

Their per-sequence counts remained exactly `6:12, 10:14, 14:6, 18:16,
22:6`; the raw inventory digest did not change. The bad assertion had copied
the narrower D1R2 failure location into the broader S24 authentication. This
was an offline authentication/reporting-code bug, not a source change,
runtime error, controller failure, plant failure, or experimental-design
change. No Ray, `gotsc`, TSC, controller, or plant step ran in the stopped
attempt. Its log is 1,223 bytes with SHA-256
`5a4e74ffe4d950acb84a4a858a68ed74e48f3295338bc0cb5114314614cb9145`.

Hotfix `da578de` changed both primary and independent readers to require the
correct frozen slot-to-cancel-step mapping `(0,11),(1,14),(2,16),(3,18)`, the
same failure type and `passed=false`, and the unchanged strict `>0.25`
classification. It also emits the observed distribution. The requested
matrix, thresholds, static gates, source fingerprints, candidate selection,
108-spec digest, formal timing, and all physical semantics were unchanged.

## Validation

The local project virtual environment was used for every Python command.
After the hotfix:

```text
py_compile                         pass
focused D1R7 tests                 8/8
complete local tests             989/989
empty-directory package files     718
empty-directory hashes/compile     pass
empty-directory complete tests   989/989, skipped 1
```

The final server package used only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`:

```text
staging checksums/shell/compile/JSON/scientific guards    pass
staging focused tests                                      8/8
installed checksums/shell/compile/JSON/scientific guards  pass
installed focused tests                                    8/8
installed complete tests                                 989/989, skipped 1
```

The staging and installed package-validation logs are byte-identical with
SHA-256 `0d61101ae3a6597161d3c8d10b61b27ce719e7a091e1181390fd7917ed8d014a`.
The installed complete-test log SHA-256 is
`3761f2aab679ebe878fde5e25308cbe3b617f47a25f199508e9de29bd7143241`.

## Raw/source authentication

Primary and independent implementations strictly parsed and authenticated:

```text
source    raw count    total bytes    inventory digest
S24             600       34003877    fae5f62671296c837e00158fe204a1630fc70aace87be650ad13d75928f20c70
D1R2             54        3078383    eb4ac8c0e606ce0d8899f0a512b594877f59cc9424c0f6a87e3450bcd036cc83
D1R6              9         422133    351f7484bd3ec2f68f76cc2f17ea6bc93a6227e2078b8be2f0cdf9e84055fd89
```

The exact D1R1 static replay, D1R2/D1R6 specs, manifests, states, independent
audits, and D1R6 physical-state reporting correction also matched their frozen
hashes. There were zero raw parse, identity, spec, corruption, snapshot, or
source-fingerprint errors.

## Official double result

Each official run wrote exactly five primary/independent artifacts totaling
1,575,823 bytes. Their ordered name/size/hash inventory digest was
`218706afc01d0f02a3c8ae605eb876b0d4f446e5ef412734849afd55862ce6a3`
in both runs. All five corresponding files were byte-identical.

The static recomputation passed every frozen gate:

```text
finite constructions                              7680/7680
issue gates                                       3840/3840
cancellation gates                                3840/3840
Decimal central-sign gates                        1280/1280
global rank/condition contexts                       40/40
slot rank/condition blocks                          160/160
late-column novelty contexts                          40/40

requested global rank                                    16
requested normalized condition                   2.0364675298172568
maximum actual global condition                  2.032765476489212
maximum actual slot condition                    1.3944510812235305
minimum actual late residual                     0.9593473942068252
```

The requested 24-by-16 matrix digest remained
`c4430a13b679ad8dcceb72c259051a5eebad03da47d86816d46c4385cd811d77`.

The candidate table passed exact coverage:

```text
specs / unique experiment IDs                     108 / 108
pairs / pair-history contexts / snapshots          9 / 18 / 18
horizon 35 / 37                                     48 / 60
candidate rows 2,6,10,14,22,23                    18 each
ordered spec digest
  62869a4a028ff177b9eb83e509e7436a5937882081739cc3e548901989f05619
candidate file sha256
  76075e12a411dbd4b0c210cc2e91a8978cb4de908b6f88a2c1ecd9cc44b279f7
```

Across all 108 specs, source action/current/result, hidden wire current,
pair/history/partition label availability, future action count, and future
measurement count were all zero/false. No JSON.GZ or source raw was copied or
modified. The two official logs contain no traceback or error token and each
ends with `zero plant steps`.

## Scientific classification

- Runtime/environment/deployment errors in the accepted result: none.
- Raw/snapshot/source corruption: none.
- Statistics/reporting error: the stopped pre-hotfix S24 slot assertion only;
  fixed without changing experimental semantics and fully retested.
- Design conclusion: the fixed temporal basis is prospectively finite,
  conditioned, cancellation-safe in static replay, and yields the intended
  108-spec real sentinel table.
- Real control/restart conclusion: none; D1R7 executed no plant or controller.
- Formal tracking conclusion: not run and not evaluable.

D1R7 freezes only the preflight matrix and D1R8 candidate table. Restart,
hidden-history robustness, unseen targets, continuous actuator variation,
model error, sensing noise, disturbance recovery, independent long hold, MPC,
expert data, BC, DAgger, and bounded residual RL remain unvalidated by D1R7.

