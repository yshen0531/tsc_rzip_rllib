# Current status

## R3c4 four-basis design vetoed before execution; R3c3T1 is active

Status timestamp: 2026-07-31 Asia/Shanghai

Current local branch:

```text
codex/stage4_2r3c3t1-transport-response
```

Frozen checkpoints:

```text
8623bcf  final R3c3 runtime and package
83e78e4  independent R3c3 raw response forensics
b0b9ece  final R3c3 certification
fbcbb16  final compact response-bank builder
84483f6  compact bank and R3c4 feasibility veto
```

## Authenticated R3c3 response bank

Remote bank directory:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c4_response_bank
```

Coverage:

```text
R3c3 raw parsed/authenticated                    256/256
R3c1 exact baselines                              32/32
signed response groups                           128/128
matched-hidden-history comparisons                64/64
rank/condition contexts                           32/32
controller-facing forbidden-key count                 0
```

Fingerprints:

```text
R3c3 raw inventory
  88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563

audit response bank
  51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32

controller response bank
  6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0

bank manifest
  a17322dcfc1d019de0455950c95e45b0b7d0f8f29fc3c68a22211481f261a066

provenance digest
  5ec49166e59df915105d4411df36a9901db56f365594b83ff08bbc6abf3751f6

R3c1 baseline inventory
  3e82504dde79215ed34626531e4f926f5bd65404832790cba6a2eb2f2cc3a97e
```

Local compact evidence:

```text
docs/codex/audits/stage4_2r3c4_response_bank_20260730/

6 transferred files / 3,847,978 bytes
inventory digest
  222eabf8089e52d0e18fddafc9f038b28ceae66a3e510e8e5e09e65877f96397
```

The audit bank retains provenance and exact R3c1 trajectories for offline
forensics. The controller-facing bank strips source/result/pair/history/wire
identity and contains only allowed numeric visible state, coil currents,
target, actuator values, selected phase, and bounded response arrays.

## R3c4 pre-execution result

Candidate:

```text
restart_integrated_bounded_response_deadline_mpc_v42r3c4_candidate
```

The prospective oracle was deliberately optimistic:

```text
exact audit-only R3c1 outcome
+ four authenticated odd responses with coefficients in [-1,1]
```

The formal evaluator reproduced all 32 R3c1 PASS values and minimum margins
exactly. Exhaustive-grid and independent per-endpoint convex epigraph checks
found:

```text
R3c1 baseline formal pass                      16/32
bounded four-basis oracle formal pass          16/32
failed contexts repaired                        0/16
baseline pass regression                        0/16
best remaining failed margin              -0.0603147
worst remaining failed margin             -0.3585158
```

Classification:

- runtime/environment error: no;
- deployment/package error: no;
- raw/snapshot corruption: no;
- statistics/reporting error: no;
- plant-restart failure: no;
- real R3c4 control result: not run;
- pre-execution design flaw: yes.

The four short zero-net bases produce at most `0.3659 mm` single-basis R/Z
displacement and lack the transport authority needed to satisfy the full
hold horizon. Even unvalidated linear bounds 2, 4, and 6 repaired no failed
context; those extrapolations are not controller authority.

No R3c4 controller module, offline launch, real TSC run, or raw was created.
The design stop is frozen in:

```text
docs/codex/reports/STAGE4_2R3C4_PREREGISTERED_DESIGN.md
```

## Active next step

Stage4.2R3c3T1 is now preregistered:

```text
docs/codex/reports/STAGE4_2R3C3T1_PREREGISTERED_DESIGN.md
```

It adds two bounded long-separation transport bases:

```text
modes                        0 and 1
per-step amplitude           0.0075
positive effect states       3..8
negative effect states       15..20
requested net                exactly zero
rollouts                     32 × 2 × 2 = 128
```

R3c3T1 must complete the full local/server/offline/real/postprocess/forensic
loop. R3c4 remains blocked unless the combined six-basis bank makes all
32 development contexts feasible under the unchanged formal contract.

## Still unvalidated

A reliable restart MPC expert, independent new histories and initial states,
unseen targets, continuous actuator/plant variation, noise, disturbance
recovery, and independent long hold remain unvalidated.

BC, DAgger, and bounded residual RL remain prohibited.
