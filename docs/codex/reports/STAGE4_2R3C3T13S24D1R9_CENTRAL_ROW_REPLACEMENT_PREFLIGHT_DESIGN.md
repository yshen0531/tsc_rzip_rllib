# Stage4.2R3c3T13S24D1R9 central-row replacement preflight design

## Status and question

This design is frozen on 2026-08-03 after the final D1R8 raw forensics and a
read-only exhaustive development search, but before D1R9 implementation,
accepted output, or any D1R10 controller/TSC execution.

D1R9 is a zero-new-TSC discriminator. It asks whether the 24-row D1R7 matrix
can remove the single D1R8-authenticated unsafe exact row by changing exactly
one central-sign row while preserving every static Card15, action, current,
central-symmetry, rank, condition, late-novelty, blindness, and formal-timing
gate. It also identifies every exact matrix row that still lacks authentic
sequential raw and freezes only those rows for a later safety sentinel.

D1R9 does not fit a model, execute a controller, start Ray or `gotsc`, run TSC,
advance the plant, implement MPC, or produce expert data.

## Frozen identity

```text
stage
  Stage4.2R3c3T13S24D1R9
identity
  central_row_replacement_preflight_v1
package revision
  r42r3c3t13s24d1r9_central_row_replacement_preflight_v1
prospective next stage
  Stage4.2R3c3T13S24D1R10
prospective next controller
  exact_row_completion_safety_sentinel_v1
```

## Immutable sources

D1R9 must authenticate, by exact path, hash, raw inventory, spec equality, and
route, all evidence used by D1R7 plus the immutable D1R8 result. At minimum:

```text
S24 raw                                             600
D1R2 raw                                             54
D1R6 raw                                              9
D1R7 accepted zero-TSC output                         1
D1R8 raw                                            108
D1R8 raw bytes                                  6468042
D1R8 raw inventory digest
  8fd08fd0e8c6c216f4a98c3a6a113f0f6c29aea16dfae92f52cc857e2a801ec2
D1R8 stage manifest sha256
  be36beea24709c00591b0301544b79d87f358d3796322f6514311ab73a0eb279
D1R8 original independent audit sha256
  f196375bc1d07f5a1e8c87f3f1b088b03235a423c9a35c2c459f63d3fed62b8a
D1R8 reporting-hotfix audit sha256
  5eb46eff8affb08969c437ebc56becb70318090e557ab063dbd7b0375d995687
```

Schedules are identified only by the SHA-256 of the exact 16-value requested
matrix row. A sequence index is not cross-matrix identity. This is mandatory
because D1R7 deliberately reassigned central row indices.

## Frozen evidence classification

The D1R7 primary 16 rows classify by exact real sequential action vector as:

```text
exact successful raw
  0,1,2,4,5,6,8,9,10,12,13,14
no exact real sequential raw
  3,7,11,15
exact contradicted raw
  none
```

The 16 possible exact central negatives classify as:

```text
exact successful raw
  negative primary 0,1,4,5,8
exact contradicted raw
  negative primary 2,6,10,14
no exact real sequential raw
  negative primary 3,7,9,11,12,13,15
```

The four contradicted negative rows are bound to authentic D1R2/D1R8 raw and
may not appear in a candidate matrix. In particular, D1R8 proved negative
primary 6 fails 3/18 at its final cancellation.

## Exhaustive selection rule

D1R9 must enumerate all `C(16,8)=12,870` central-index sets. A set is eligible
only if:

1. none of its exact rows is contradicted by authentic raw;
2. the requested 24-by-16 matrix has rank 16 and normalized condition at most
   3.0;
3. every 24-by-4 slot matrix has rank 4 and normalized condition at most 3.0;
4. minimum late-column residual outside the slot-0 span is at least 0.5.

Eligible sets are ordered prospectively by:

```text
1  minimum number of central rows without exact real raw
2  minimum replacements from the D1R7 central-index set
3  minimum maximum requested slot condition number
4  maximum requested late-column residual
5  lexicographically smallest sorted central-index set
```

The frozen expected enumeration has 495 eligible sets. The unique selected
sorted set and ordered row mapping are:

```text
sorted central primary indices
  0,1,3,4,5,7,8,9
ordered central primary indices for rows 16--23
  0,4,1,5,3,7,9,8
```

Only row 22 changes. It becomes exact negative primary 9:

```text
[-0.25,+0.25,-0.25,+0.25,
 -0.25,+0.25,-0.25,+0.25,
 +0.25,-0.25,+0.25,-0.25,
 +0.25,-0.25,+0.25,-0.25]
```

The requested matrix digest must be:

```text
106dfed384febb16019e4d39ce1da03762ad9dbb5e8e69120a4a9d9acdebc30b
```

## Complete static replay

After selection, both implementations must independently replay all 24 rows,
four issue/cancel slots, and 40 D1R1 authentic contexts. The frozen gates are:

```text
finite issue plus cancellation constructions        7680 / 7680
issue gates                                          3840 / 3840
cancellation gates                                   3840 / 3840
exact Decimal central-sign gates                     1280 / 1280
global rank/condition contexts                          40 / 40
slot rank/condition blocks                            160 / 160
late-novelty contexts                                   40 / 40
```

No threshold may be relaxed after the result. The preregistered requested
metrics are:

```text
global rank                                         16
global normalized condition                         2.036467529817257
maximum slot normalized condition                   1.5203729437964553
minimum late residual                               0.9734388197613807
```

## Exact dynamic coverage and D1R10 table

After replacement, exactly 17 matrix rows have exact successful authentic
sequential raw and none has exact contradictory raw. The seven exact rows
without real sequential raw are frozen before D1R9 implementation as:

```text
3,7,11,15,20,21,22
```

D1R9 must generate exactly seven rows across the same 18 authentic hard
contexts and snapshots used by D1R8:

```text
D1R10 specs / unique IDs                            126 / 126
contexts / snapshots                                  18 / 18
row count                                                7
specs per row                                           18
horizon 35 / 37                                    56 / 70
```

Every spec must have a fresh D1R10 identity and exact new matrix digest. It
must preserve snapshot, target, horizon, calibration, baseline controller,
formal timing, action/current gates, and all source/future/hidden-label
prohibitions. Probe trajectories remain forbidden from expert datasets.

## Independent replay and accepted output

A separate implementation must recompute source authentication, exact-vector
evidence classes, all 12,870 combinations, the selection ordering, the full
40-context static replay, and the 126-spec table. Two fresh accepted D1R9
outputs must be byte-identical file by file. D1R9 may write only compact JSON
and logs; raw source remains in place on the server.

## Frozen routes

```text
source/hash/raw/evidence/enumeration/static/candidate mismatch
  CENTRAL_ROW_REPLACEMENT_PREFLIGHT_FAIL_NO_TSC

all primary and independent gates pass twice byte-identically
  CENTRAL_ROW_REPLACEMENT_PREFLIGHT_PASS_EXACT_ROW_SENTINEL_DESIGN_REQUIRED
```

Even a pass authorizes only a separately frozen D1R10 real-TSC safety-sentinel
design. It does not authorize D1R10 execution by itself, the full replacement
identification campaign, transition MPC, expert data, BC, DAgger, or bounded
residual RL.

