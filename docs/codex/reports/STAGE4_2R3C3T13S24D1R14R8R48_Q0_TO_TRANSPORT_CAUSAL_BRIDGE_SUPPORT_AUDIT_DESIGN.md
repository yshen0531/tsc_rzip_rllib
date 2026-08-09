# Stage4.2R3c3T13S24D1R14R8R48 q0-to-transport causal-bridge support audit design

Status: prospectively frozen on 2026-08-09 after final R8R46 was opened, but
before any R8R48 config, result-bearing bank reconstruction, bridge count,
prefix comparison, candidate coverage, route, package, deployment, Ray,
`gotsc`, TSC, controller, plant step, raw, or snapshot.

## 1. Scientific question

R8R46 forced an exact q0 interval before transport planning, but its held-bank
validation teacher-forced innovations inside immutable trajectories generated
under earlier schedules. R8R48 asks only:

```text
Does the authenticated 560-trajectory development bank contain authentic
physical trajectories that share the exact q0 calibration prefix through
task step 12 and then execute every fixed nonzero transport candidate?
```

This is a support and experiment-design audit. It fits no model, changes no
gain, evaluates no controller outcome, and cannot repair or relabel R8R46.
Feature-space proximity or membership in a global transition hull is reported
separately and may not substitute for an actually executed physical bridge.

## 2. Exact source identity

Require final R8R46 route:

```text
Q0_CALIBRATION_CAUSAL_INNOVATION_MODEL_INSUFFICIENT_NO_TSC
```

Authenticate these eight final server files byte-for-byte:

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

Rebuild the exact source bank and require:

```text
trajectories / contexts / schedules / intervals       560 / 16 / 35 / 3360
bank digest       a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest    80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest     0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

No other raw tree or historical result may enter the audit.

## 3. Frozen q0 prefix and bridge definitions

The six decisions are exactly `[10,12,14,16,18,22]`. For each of the 16
`(pair_id, history_member)` contexts, identify the one `schedule_id=q0`
trajectory and require its interval-zero metadata to be exact binary64 zeros:

```text
previous_q = [0,0,0,0]
q          = [0,0,0,0]
decision   = 10
```

The reference q0 prefix includes every visible normalized R/Z/Ip sample,
every raw trajectory entry, every 14-coil current, and every available issued
action/current-target field from restart through completed task step 12.
Preserve both a canonical prefix digest and exact array equality checks.

An authentic bridge for context `c` and nonzero candidate `a` exists only if
one immutable trajectory simultaneously satisfies:

1. interval zero has exact `previous_q=q0` and `q=q0`;
2. its complete physical prefix through task step 12 is exactly equal to the
   context's q0 reference prefix;
3. at interval one, decision step 12, `previous_q=q0` and `q` equals candidate
   `a` exactly; and
4. the trajectory contains all physical samples for that interval.

A later nonzero action at intervals 2--5 is recorded diagnostically, but does
not satisfy the primary interval-one bridge matrix. Duplicate schedule labels
do not increase coverage. Metadata-only q equality without physical-prefix
identity is not an authentic bridge.

## 4. Fixed candidate matrix

Use the exact R8R31/R8R46 canonical 17-candidate order and canonical-matrix
digest
`c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c`.
Exclude only candidate index zero (`q0`) from the bridge targets. The frozen
matrix is therefore:

```text
16 contexts x 16 nonzero candidates = 256 required authentic bridges
```

Record per-context and per-candidate counts, source identity, schedule
identity, trajectory identity, exact q0-prefix status, first nonzero interval,
and all missing cells. The PASS condition is full `256/256` coverage with one
or more unique authentic source trajectories in every cell. No candidate or
context may be dropped after inspection.

## 5. Geometric diagnostics kept separate

Recompute the inherited interval-one 8D transition hull and 44D planning-
feature support from the same bank. For every context/candidate cell, record:

- exact 8D `(previous_q=q0, q=candidate)` hull membership;
- nearest interval-one feature distance from the context's measured q0 row;
- inherited training-only support threshold and pass/fail; and
- whether the corresponding physical bridge exists.

These fields diagnose whether earlier planning used interpolation in its
declared coordinate geometry. They do not change the physical-bridge gate,
and no R8R46 error, formal result, or schedule ratio enters selection.

## 6. Independent audit and routes

Primary and a structurally independent implementation must independently
authenticate sources, rebuild the bank, construct prefix digests, enumerate
the 256 cells, and agree exactly on all identities/counts/booleans/digests and
to scaled `1e-12` on geometric distances. Independent may reuse immutable raw
loaders and actuator definitions, but not the primary bridge-enumeration or
comparison function.

Frozen routes:

```text
source authentication or bank identity fails
  Q0_TO_TRANSPORT_CAUSAL_BRIDGE_AUDIT_BLOCKED_BY_SOURCE

audit implementation, prefix parsing, or primary/independent agreement fails
  Q0_TO_TRANSPORT_CAUSAL_BRIDGE_AUDIT_EXECUTION_FAIL_STOP

any of 256 authentic physical bridge cells is absent
  Q0_CALIBRATION_TO_TRANSPORT_CAUSAL_BRIDGE_SUPPORT_ABSENT_FRESH_SENTINEL_REQUIRED

all 256 authentic physical bridge cells are present
  Q0_CALIBRATION_TO_TRANSPORT_CAUSAL_BRIDGE_SUPPORT_PRESENT_REANALYSIS_REQUIRED
```

Both scientific routes are valid completed audit outcomes. “Present” does not
make R8R46 pass and “absent” does not prove a plant limitation.

## 7. Execution, packaging, and scope

R8R48 executes zero Ray, `gotsc`, TSC, controller, plant step, raw, snapshot,
optimizer, fit, or learned update. Before execution require project-venv
compilation, focused and complete Windows-shimmed tests, exact package
manifest/checksums, fresh empty direct-copy validation, direct uncompressed
SSH transfer, server preflight, existing server venv, staging/installed
hashes, `bash -n`, compilation, focused/full tests, and dual audit/finalizer.
Large detailed evidence stays on the server; only compact evidence is copied
back.

A support-absent result may authorize only the separately frozen conditional
R8R49 bridge-identification sentinel. A support-present result may authorize
only a new zero-TSC analysis under a new prospective validation boundary.
R8R48 is not a model, controller, MPC, formal-control, plant-reachability, or
Gate A result. Every old and new R8-family trajectory remains forbidden from
expert data, BC, DAgger, residual RL, and all other learning datasets.
