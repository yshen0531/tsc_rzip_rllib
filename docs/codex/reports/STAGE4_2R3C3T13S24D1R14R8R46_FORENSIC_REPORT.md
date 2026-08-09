# Stage4.2R3c3T13S24D1R14R8R46 forensic report

## Verdict

R8R46 completed its fixed q0-calibration causal-innovation zero-new-TSC
preflight with exact primary/independent agreement. Its final route is:

```text
Q0_CALIBRATION_CAUSAL_INNOVATION_MODEL_INSUFFICIENT_NO_TSC
```

The fixed 0.5/0.5 bounded EWMA innovation was useful under whole-pair
exclusion but not under whole-schedule exclusion. This is a finite
model/adapter and validation-architecture failure. It is not a runtime,
deployment, source-authentication, raw-corruption, reporting, restart,
controller, real-MPC, formal-control, plant-reachability, or Gate A result.

Conditional R8R47 requires an exact R8R46 PASS. It is therefore permanently
blocked and was not implemented or run.

## Frozen identity and validation

```text
design checkpoint                         9cb7580
implementation checkpoint                 75b0ba1
original package checkpoint               7d53cc1
independent serialization hotfix           c6b04ea
final hotfix package checkpoint            561dcb4
R8R46 design SHA-256
  f12206844c181d9610d96588c8f44e3a47cc6661120b208b2ab9c04b57f66e1e
conditional R8R47 design checkpoint        51637b5
conditional R8R47 design SHA-256
  544eb5a9054693e2e0696853bd803ba4a9f72f221b4f60315420c3095683a2d8
final package manifest SHA-256
  9aa13c893743daadccb2b3cd5d2acee4930186eb91a8b6cdc03d7c33207be175
final SHA256SUMS SHA-256
  479f86cf37491b66b3a360d56ed9bcf29a97d9a202b824eaf709be1c0a83030b
```

Local source and fresh empty-directory direct-copy validation passed:

```text
declared hashes                                  1224/1224
initial physical package files                         1226
strict JSON including manifest                           145
Python compilation                                       479
focused tests, original / hotfix               12/12 / 13/13
full shim-first tests, original / hotfix     1523/1523 / 1524/1524
```

Server staging and installed validation reproduced 1,224 hashes, 144 JSON
files from the declared inventory, 479 Python compilations, 452 `bash -n`,
focused `12/12` then `13/13`, and full `1523/1523` then `1524/1524`, with one
expected isolated-package skip. Transfer was direct `scp -r`; no archive was
created or extracted. Local execution used only the project virtual
environment and server execution used only:

```text
/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python
```

## Server execution and audit-only hotfix

Accepted run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r46_runs/
stage4_2r3c3t13s24d1r14r8r46_q0_calibration_causal_innovation_controller_preflight_20260809_7d53cc1_v1
```

Primary completed normally. The first independent attempt completed its
model work but stopped before comparisons and before writing an independent
result because `combined_execution_tube` still contained `numpy.ndarray`
objects when the independent artifact digest was serialized:

```text
TypeError: Object of type ndarray is not JSON serializable
```

This was an independent-audit serialization/reporting implementation error.
The hotfix only applied the repository's existing JSON-safe conversion to
that independent artifact and added a regression test. It changed no bank,
cold model, innovation, residual, tube, support, usefulness metric, planner,
action, gate, route, primary result, or scientific semantics. Primary was not
rerun. Independent was rerun with a new log in the same zero-TSC result
directory, then the finalizer completed.

## Authenticated bank and cold source

Both paths authenticated final R8R44 and independently reconstructed:

```text
trajectories                                      560
physical pairs / history contexts              8 / 16
schedules                                          35
interval records                                 3360
bank digest
  a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest
  80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest
  0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

The recomputed R8R43 primary detailed and model artifacts matched their
authenticated sources exactly. No weight, gain, feature, ridge, neighbor,
outcome, or route search occurred.

## Frozen post-calibration result

Whole-pair exclusion passed every absolute model and usefulness gate:

```text
adapted/cold normalized squared-error ratio       0.42640699597516946
strictly improved folds                                      8/8
maximum fold ratio                            0.8117445903495492
maximum point error
  [0.00759718, 0.0115286, 69.2823, 0.0416461, 0.0466063]
maximum reserved tube
  [0.015, 0.015, 3000, 0.05, 0.0582578950]
containment / support                                  100% / 8/8
innovation clipping components                                  0
```

Whole-schedule exclusion passed point, tube, containment, support, finite,
forbidden-input, and clipping gates, but failed the prospectively frozen
usefulness gate:

```text
adapted/cold normalized squared-error ratio        1.2383400549755048
required ratio                                                <=0.95
strictly improved folds                                     26/35
maximum fold ratio                             2.1935323358398033
maximum point error
  [0.00112991, 0.00183543, 56.4268, 0.0127459, 0.0288459]
maximum reserved tube
  [0.015, 0.015, 3000, 0.05, 0.05]
containment / support                                 100% / 35/35
innovation clipping components                                  0
```

The largest held-schedule ratios were:

```text
R8R28_g2_VVVV       2.1935323358398033
R8R28_g2_UUUU       1.4579102011218403
R8R14_d1_p          1.2431109452977964
a1p50_w0p75         1.1349835315643082
UVUV                 1.1176265580853213
UVUU                 1.1153906583748474
q0                   1.1075542506216510
UVVV                 1.0097309601540340
UVVU                 1.0051886148992013
```

By source family, mean fold ratios were `1.82572` for the two front-loaded
R8R28 schedules, `1.10755` for q0, `0.94062` for the Boolean schedules,
`0.88030` for the amplitude/weight grid, and `0.83372` for the R8R14 static
directions. The failure is therefore not just one numerical outlier and may
not be repaired by deleting R8R28, weakening 0.95, or selecting a gain after
seeing held outcomes.

The combined post-calibration tube remained within the frozen caps:

```text
[0.015, 0.015, 3000, 0.05, 0.058257895035251604]
```

Because the model/usefulness gate failed, controller planning was correctly
skipped before calibration/search. The six injected model/support/Card15
faults still selected exact hold. Reported `0` calibration/search/repair/
oracle/nonzero-action counts mean "not run after model rejection", not failed
real controller trajectories.

## Independent agreement and final inventory

```text
maximum bank absolute difference          0.0
maximum scaled model difference           0.0
maximum scaled innovation difference      0.0
maximum scaled tube difference            0.0
maximum scaled metric difference          0.0
maximum scaled planning difference        0.0
all ten source/bank/model/innovation/tube/metric/
planning/discrete/route/outcome agreements true
```

Final server hashes:

```text
primary summary   05f4d646012501ddae9a2c4f7792ece5828d1feab29f2fb4d630bdbdd4eb25fd
primary detailed  efff1666f3b58b9b4f9923342da42f970486f050474677c695758254e79d11c6
model artifact    3e0ad214d98faec1c41ec97521a30fc5643c4793690c03d86377cd9b6bcebdc7
independent       f94c973e6e2fc19bfee83ae1d70a2c67d101df832a75cbbcbe7bb4e96819091f
compact audit     bdc3e835c1c95ebb88a8894045e683195d66cdfb36714c802a3180440e455cce
final report      ee6adc45ee9ccda171a4d0d0ab3e80fb6509fa3582a2ac64cf45f8dfc9acb139
stage state       3c5ec8f7fcb8a71ee2fe5ea1d1df98a431fb3fa8725b95c584fa5a38138099ea
stage manifest    c0558aaa707a21a366167e1cc37a5bb34ebe9e9a1c6f248bcc13503aabb7c984
```

The stage has exactly eight files totaling 123,559,216 bytes, with zero raw,
JSON.GZ, snapshot, or spec files and zero Ray, `gotsc`, TSC, controller, or
plant steps. Large detailed/model evidence remains on the server. Local
compact evidence is:

```text
artifacts/server_validation/r8r46_compact_evidence_561dcb4_v2.json
SHA-256 23f36e5f4c5cd1fb1ec1dd04d8c00e7050c171d165e0643a0007f7372946083a
```

## Scientific boundary and next question

R8R46 rejects this fixed EWMA adapter without testing control authority. It
does not reject all causal adaptation, real q0-calibrated feedback, or the
plant's ability to track. It also does not authorize R8R47.

The next zero-TSC question is whether the authenticated 560-trajectory bank
actually contains prospective causal bridges from the exact q0 calibration
prefix through a later nonzero transport action in every context. This must
be established before fitting another q0-conditioned adapter or authorizing
a real controller. If that bridge evidence is absent, another outcome-tuned
gain on the same rows would not create it; a separately frozen minimal fresh
bridge-identification sentinel is required.

Gate A, expert data, BC, DAgger, residual RL, and Gate B remain blocked. Every
R8-family trajectory remains forbidden from learning data.
