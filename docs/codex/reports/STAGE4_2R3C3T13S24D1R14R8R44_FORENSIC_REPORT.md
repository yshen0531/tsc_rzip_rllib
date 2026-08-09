# Stage4.2R3c3T13S24D1R14R8R44 forensic report

Date: 2026-08-09 Asia/Shanghai

## 1. Final classification

R8R44 completed its fixed zero-new-TSC controller preflight with exact
primary/independent agreement. The final route is:

```text
FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_AUTHORITY_INSUFFICIENT_NO_TSC
```

The source/model/safety/search/fault/integrity gates passed, but the frozen
authority gate failed. All 16 contexts completed a safe search, yet the
unchanged full R8R43 tube admitted no robust-formal suffix. The fail-closed
policy therefore selected exact current-target hold in all 16 contexts. It
preserved the six baseline formal passes, repaired none of the ten baseline
formal failures, and selected no nonzero deployable first action.

This is a finite controller-preflight authority/design failure. It is not a
runtime, deployment, source, model-fit, raw, restart, causality, Card15,
current, reporting, real-controller, real-MPC, formal plant-control, global
plant-reachability, or Gate A conclusion.

## 2. Frozen identity and checkpoints

```text
R8R44 design                              5af9163
R8R44 implementation                     f95e428
R8R44 original package                   509b7b4
conditional R8R45 design                 c5cd07f
independent metric-view audit hotfix     0e0685c
hotfix package                           6f0df5d
```

The R8R44 design SHA-256 is
`8151ee6f9cf086b134f83f4b4ab8cb84d065a204cd5bef928843ae5d41befad6`.
Conditional R8R45 was frozen before any R8R44 numerical or discrete result
was opened. Its exact source gate requires the R8R44 PASS route, so the final
R8R44 authority-FAIL permanently blocks R8R45 without implementation,
controller execution, or TSC.

The hotfix changed only the independent comparison view: it exposed the
already generated `combined_tube_cap_passed`, `model_gate_passed`, and
`scientific_gate_passed` fields to the inherited R8R43 metric comparator. It
did not change the bank, model, weights, tube, support, candidate order,
planner, action semantics, safety gate, authority gate, route, or any primary
file.

## 3. Package and validation evidence

The final package declares 1,216 files. Its load-bearing fingerprints are:

```text
PACKAGE_MANIFEST.json
  0959ab5b1a3e6f0f00307ab85566bbb0595579f214c5d503c21b63a149a054d0
SHA256SUMS
  67055fb88a3563f3c47be9178df27e2b2382e444daaa66130a3bc8e164ff7c19
R8R44 config
  b186a5395a604a4957240153264465276966407a5baaef343d798a013e01aabb
```

The source tree passed project-virtual-environment compilation, focused
`13/13`, and full Windows-shimmed `1511/1511` tests with zero skips. A first
focused invocation omitted the required Windows `tests/conftest.py` shim and
stopped during import on the unavailable Linux `resource` module; no test
body ran. The corrected shim-first invocation and full suite passed. This was
a local validation-command error, not a code regression.

A fresh empty direct-copy tree inside the repository passed:

```text
declared hashes                              1216/1216
strict JSON parses                                  144
Python compilation                                  476
focused unittest                                  13/13
full unittest                                  1511/1511
expected isolated-package skip                         1
```

The clean transfer tree contained exactly 1,218 physical files (the 1,216
declared files plus manifest and sums) and zero cache files. It was copied
directly with `scp -r`; no archive was created or extracted. Server staging
and installed-tree validation independently repeated 1,216 hashes, 144 JSON,
476 compilations, 451 `bash -n`, focused `13/13`, and full `1511/1511` with
one expected skip, using only the existing server virtual environment.

## 4. Exact server run and audit repair

Run root:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r44_runs/
stage4_2r3c3t13s24d1r14r8r44_fixed_affine_dominant_global_local_affine_cold_ensemble_receding_controller_preflight_20260809_509b7b4_v1
```

Stage child:

```text
stage4_2r3c3t13s24d1r14r8r44_fixed_affine_dominant_global_local_affine_cold_ensemble_receding_controller_preflight
```

Primary completed normally. The first independent attempt then rebuilt its
evidence but stopped before writing an accepted audit with:

```text
KeyError: 'combined_tube_cap_passed'
```

The cause was the audit-view interface mismatch described above. The failed
launch log was preserved. After the separately tested, committed, packaged,
and server-validated audit hotfix, the independent path was rerun under a new
launch log in the same unchanged zero-TSC run. Primary was not rerun. The
finalizer then accepted the independent result.

## 5. Primary scientific result

```text
authenticated trajectories                         560
schedule identities                                 35
interval records                                  3360
bank digest
  a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
source/model binding                               PASS
safe completed searches                           16/16
fault-injection exact holds                         6/6
predicted repairs among failed baselines           0/10
predicted regressions among baseline passes         0/6
fallback-plus-plan predicted oracle                 6/16
nonzero deployable first actions                    0/16
safety gate                                         PASS
authority/scientific gate                           FAIL
```

The carried physical tube maximum was:

```text
[0.015, 0.018564651219681465, 3000.0, 0.05, 0.05924497047316829]
```

Every context produced a complete safe beam search. Every best suffix was
still non-robust under the full tube. The best failing suffixes began with a
nonzero candidate in all 16 contexts and had maximum predicted current
utilization from about `0.36495` through `0.3904`; they were correctly
forbidden from deployment. Their worst formal-margin violations ranged from
`0.2373889664` to `1.4074872271`. Thus the result is not an empty-action or
current-authority failure: it is the absence of a robust-formal deployable
plan under the frozen whole-suffix uncertainty contract.

The primary `passed=true` field records successful pipeline completion. It
does not override `scientific_gate_passed=false` or the authority-FAIL route.

## 6. Independent and sealed evidence

All ten independent agreement flags are true:

```text
source / bank / model / prediction / tube / metric / planning /
discrete selection / route / outcome
```

All six maximum differences are exactly `0.0`:

```text
bank / scaled model / scaled prediction / scaled tube /
scaled metric / scaled planning
```

The eight final files are:

```text
primary_summary  539691abbd779d6c56711cbbd489ed7f47bc9297472d1bbd9b358ef881bb409b
primary_detailed dabff158160e77d82207c95d0d38093c91aca3a97b06287216b3d83164877aa2
model            7a7b35b6189765653a1c4d16b4a80fc6096ea35fe135542cd5049f65b6ad16a5
independent      d757515ba0e6e3d1de895f2cc5c08f9423d48d56f4a9b8c916239d5cdf7a1a01
compact_audit    b0496ed69c8ba3a45ff611b086df955fc53fe8ed34b9def30706cae3361ea764
final_report     7bd1b8e31c81e82e4559f78acf0b2b37bd6705e178e64d4a53d03575aaf2b713
stage_state      7bbd2a69faaa9de560979120ff6651d65d85141cb7a79e47c8c869ffc346a794
stage_manifest   2a576650f3e540959ffc5f13ef5e10a035a49447d25959291ccb137476e0059a
```

The compact downloaded evidence SHA-256 is
`44ffb8fc75c88e5b3121bbdf1f2d96e70c0bb8851f0e5640b57021b6b8776368`.
The compact planning-forensics SHA-256 is
`22cfab3dad0af3e7a08146d372436c6264ed7a352ad4a3aba7b6f449c9502d26`.
The stage contains exactly eight files totaling 106,854,338 bytes and zero
raw, snapshot, or spec files.

## 7. Scientific boundary and handoff

R8R44 ran zero Ray, `gotsc`, TSC, controller, plant step, raw, or snapshot.
No old R8-family TSC trajectory was rerun. Every R8-family trajectory remains
forbidden from expert data, BC, DAgger, residual RL, or any other learning
dataset.

R8R45 is blocked by its exact source gate. Before any new fit, prediction, or
plan is computed, the next identity must freeze a causal online-innovation
architecture with a genuinely new validation boundary. The justified next
boundary is an exact q0 calibration hold through the first completed
decision interval, followed only then by bounded same-rollout innovation and
control; interval zero remains authenticated by the cold R8R43 model, while
all post-calibration prediction/tube/usefulness gates are evaluated on
whole-pair and whole-schedule held data. A later PASS may authorize only a
separately frozen real safety sentinel. Gate A and all learning remain
blocked.
