# Stage4.2R3c3T13S24D1R14R8R51R4D1 forensic report

Date: 2026-08-10 Asia/Shanghai

Final route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_TWO_TRANSPORT_SCHEDULE_GEOMETRY_INSUFFICIENT_NO_REAL_TSC
```

## 1. Scope and conclusion

R51R4D1 was a zero-new-TSC action-geometry preflight over the complete
ordered product of five frozen transport targets in each of the ten failed
R51R4 contexts:

```text
10 contexts x 5 first targets x 5 second targets = 250 specifications
```

The corrected primary and structurally independent scalar implementations
authenticated the final R51R4 source, constructed and retained all 250
schedules, preserved the frozen action-stream digest, and agreed on every
eligibility and coverage decision. Only 68/250 schedules were eligible, and
no context met the prospectively frozen coverage gate. R51R4D1 is therefore
a finite direct-target-to-target action-geometry/support design FAIL.

It is not a runtime, deployment, source-authentication, Card15, binary64
current-equivalence, raw, restart, causality, controller, MPC, formal-control,
plant, or global-reachability failure. It ran no TSC and observed no response.

## 2. Frozen design and implementation checkpoints

```text
original design checkpoint                         e1ddc9e
original implementation checkpoint                 371275b
original package checkpoint                        ba89426
reporting-fix contract checkpoint                  ebf96e9
reporting-fix implementation checkpoint            238e9e2
accepted reporting-fix package checkpoint          b98f9c8
```

Frozen design:

```text
docs/codex/reports/
  STAGE4_2R3C3T13S24D1R14R8R51R4D1_TWO_TRANSPORT_EXACT_RETURN_SCHEDULE_PREFLIGHT_DESIGN.md
SHA-256 ccc279be94ac230b86ebea80b07572fe057aab2110657989a261d37cd6988645
```

Reporting-fix contract:

```text
docs/codex/reports/
  STAGE4_2R3C3T13S24D1R14R8R51R4D1_POST_RETURN_REFRESH_REPORTING_FIX_CONTRACT.md
SHA-256 1a42fb9eea15397c442a3253295d2bb779e52af23e2a7674165868683366e362
```

Accepted package fingerprints:

```text
PACKAGE_MANIFEST.json  84864e076f69fb20cf21af34e0b41bd5204471642e301466565f107e18fdfc77
SHA256SUMS             d80f0c86340c376c1d3f6b5040eb52d2f9f88eae752baa65324e115cda141965
```

## 3. Validation and deployment

Only project/server existing virtual environments were used. Local Windows
unittest discovery loaded the repository's existing `tests/conftest.py`
`resource` compatibility shim. Transfer was direct `scp -r`; no archive was
created or extracted.

Accepted reporting-fix package validation:

```text
declared hashes                                      1292 / 1292
fresh empty-copy physical files                      1294
strict JSON                                           154
Python compilation                                    509
server bash -n                                        460 / 460
focused tests                                          10 / 10
full source tests                                    1618 / 1618
full empty-copy/server tests                         1618 / 1618
expected isolated-package/server skip                    1
```

Server staging and installed validation reproduced the same counts. The
original failed-attempt final artifact and the R51R4 source state/final hashes
were rechecked after installation and remained unchanged.

## 4. Original false-stop attempt

The original dual run is preserved at:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r51r4d1_runs/
  stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight_20260810_ba89426_v1/
  stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight/
```

Primary and independent agreed, but both implementations had added an
undeclared eligibility predicate requiring every post-return refresh command
representation to be componentwise binary64 zero. It failed 250/250 even
though exact stored-center current, exact later q0 Card15/current, return
event, fixed clock, and q0 gate all passed 250/250.

The false-stop hashes are frozen in the reporting-fix contract. Its published
`0/250` eligibility and geometry route are invalid reporting/eligibility
results. No action, response, raw file, TSC trajectory, or plant conclusion
was invalidated because none was produced by D1.

The correction removed only that undeclared predicate from eligibility and
retained it as a diagnostic. It did not alter any event, action, Card15 field,
current, threshold, source, schedule, coverage gate, or route.

## 5. Corrected accepted run

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r51r4d1_runs/
  stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight_20260810_b98f9c8_v2_refresh_fix/
  stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight/
```

Core integrity result:

```text
source authentication                                  PASS
specifications constructed/reported                    250 / 250
primary/independent discrete agreement                 exact
primary/independent coverage agreement                 exact
primary/independent numerical agreement                PASS
maximum numerical difference                           3.3306690738754696e-16
frozen action-stream digest                            d1607012ca5e39cca3b3113c269c569c754603c49704cef419b239d810ea7ccb
action-stream digest preserved                         yes
history-pair eligible-set equality                     5 / 5
new TSC/raw/plant/controller/model/optimization         0 / 0 / 0 / 0 / 0 / 0
```

Corrected artifact hashes:

```text
offline_primary.json                 0dfb4757ce2eb783885fe0a9912ce859bb7be8ae4f103079058782501d43611b
offline_construction_primary.json    43ddef18075266b2f8c3287e468fa31656f71acd16ca9900cabf776061f74982
offline_independent.json             0d58a9bbb8f0ce2742dc12ee21eef8bbc5c53754bd52b323b6674e544ddd5bc0
final_report.json                    af9501585d67da77973a7d14a642a8ae15a69f04ac70e1c454ba1fe45db6a0f5
stage_state.json                     6dd09da7faea09580cc9b50835572c3f625971a8dd3d403543c3ea82b46c1bec
stage_manifest.json                  ce9a9d3da885fbdd787b05d64c1687343fa3eac2d2e1ab32c6dda9f1f5c88ce7
specs/all_specs.json                 548922d11ec27d56dd7fd259be1339acc1210b6b17adfa00c405e182d3a824af
source_authentication.json           f7521af965e160691aae7c5e3b8ba84e56658a65459e9b00c20229c7d131ef09
compact forensics                    07ffddc23b1428d53c1496f66309ad0b9cc122ef87e45df3427a6e8f64695338
server evidence                      2b9fbf5353a6ddd0f2d17b051a944430a9999510b84d5f13072139d950f975a9
```

## 6. Frozen scientific gate result

```text
eligible schedules                                    68 / 250
context coverage PASS                                  0 / 10
contexts 0--3 eligible pairs                           8 each
contexts 4--9 eligible pairs                           6 each
required eligible pairs                                >= 10 each
all-event-gate rows                                    68 / 250
incremental-limit rows                                178 / 250
off-basis-limit rows                                  190 / 250
equal-pair zero-increment rows                        200 / 250
maximum incremental normalized action                  0.3518518518518519
maximum current utilization                            0.3912
minimum second-transition cosine                       0.9999999999999998
maximum second-transition relative off-basis residual  0.2885170771363397
```

Contexts 0--3 retained all five candidates in both positions and at least one
distinct successor for each first target, but had only eight eligible pairs.
Contexts 4--9 had only six; candidate `d2m` lacked a distinct eligible
successor, so first/second candidate support and successor coverage also
failed. No threshold was weakened after these results were seen.

## 7. Scientific interpretation and next boundary

The fixed direct target-to-target transition at task step 16 is not broadly
representable under the unchanged incremental and off-basis gates. This
rejects R51R4D1's direct two-transport schedule family. It does not reject
sequential actions that return through the exact q0 center, split a transition
into multiple safe Card15 steps, or use a separately designed causal online
controller.

The conditional R51R4D2 real sentinel required a D1 PASS and is therefore
blocked and unrun. Before any new construction or response, the next route
must be prospectively frozen as a new zero-TSC action-geometry redesign. No
R51R4/R51R4D1 evidence may enter expert data. Gate A, expert data, BC, DAgger,
residual RL, and Gate B remain blocked.
