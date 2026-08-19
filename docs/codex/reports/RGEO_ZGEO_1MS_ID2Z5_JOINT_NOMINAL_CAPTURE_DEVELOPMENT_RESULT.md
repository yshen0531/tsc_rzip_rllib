# R_geo/Z_geo 1 ms ID-2Z5 joint nominal/capture development result

Date: 2026-08-19

## 1. Frozen identity and final route

ID-2Z5 ran from implementation revision
`bcab87f0e5a328b9a2b3f7496328c756bb7b0d53` with stage-config SHA-256
`244e7ebdca7675f61cc8bb83b1816c54bfe7a47ecee48ecbdd5c229dba9bddf5`.
The accepted server run is
`rgeo_zgeo_1ms_id2z5_runs/20260819_bcab87f0_v1`.

The immutable final route is:

```text
ONE_MS_ID2Z5_DEVELOPMENT_DATA_INSUFFICIENT_ACTION_SUPPORT_REVIEW_REQUIRED
```

This is an execution-clean development-data/action-grammar failure. It is
not a runtime, package, raw-integrity, TSC, model-training, controller,
recovery, waypoint, reachability or global plant failure. No predictive
model was fit or updated.

## 2. Execution and independent evidence

- 13/13 canonical-source rollouts were classified.
- 13/13 exact state-61 prefix checks passed.
- 13/13 paths ended in a prospective `PULSE_CLEARANCE_R` safe stop.
- 1,243/1,243 attempted plant advances called `gotsc` and produced verified
  successors; there was no retry.
- 1,256 states and 6,280 required raw artifacts were independently parsed.
- Required raw size was 73,969,512,544 bytes and inventory SHA-256 was
  `8b247193c1e599155843a6ad54f0d4fdadcabdb75213acd0d8d87aa8d46072bc`.
- The structurally separate server audit returned `audit_passed=true` with
  no failures and reproduced the counters, prefix checks, raw inventory,
  scientific metrics and route exactly.
- Calibration/holdout records read: 0. Models fit or updated: 0.

The server-focused suite passed 6/6 and the complete one-ms suite passed
431/431 before the plant run. Offline admission passed all 13 schedules with
maximum exact issued slew 0.3 A, target headroom at least 100 A, and zero
plant calls.

## 3. Frozen scientific result

The data-readiness gate required at least eight complete non-replay families,
ten classified non-replay families with at least sixteen novel successors,
six distinct complete schedules and one complete zero-weight critical replay.
The run obtained twelve classified non-replay families with at least sixteen
novel successors, but zero complete families, zero complete schedules and an
incomplete critical replay. Therefore no model comparison was authorized.

| candidate | retained states | novel successors | stop state | last source distance (mm) |
|---|---:|---:|---:|---:|
| hold24 | 84 | 22 | 83 | 29.3368 |
| b4_h20 | 88 | 26 | 87 | 29.6038 |
| b8_h16 | 91 | 29 | 90 | 29.5032 |
| b12_h12 | 95 | 33 | 94 | 29.6182 |
| bf_alt | 103 | 41 | 102 | 26.9008 |
| bbff_repeat | 103 | 41 | 102 | 26.8970 |
| bbbfff_repeat | 103 | 41 | 102 | 26.8934 |
| bbbbffff_repeat | 104 | 42 | 103 | 27.0648 |
| b4_f4_h16 | 90 | 28 | 89 | 28.6110 |
| b8_f8_h8 | 97 | 35 | 96 | 27.9331 |
| b12_f12 | 105 | 43 | 104 | 27.2197 |
| b4_h4_f4_h12 | 90 | 28 | 89 | 28.7235 |
| bf_alt_replay | 103 | 41 | 102 | 26.9008 |

Every final retained state had just crossed the frozen source-relative
R-axis development boundary: last R offsets were -25.0268 to -25.2864 mm.
Ip was not limiting: final source-relative offsets were 666.3--866.6 A,
inside the unchanged 5% descriptive capture cap of 1,564.3 A. Across all
retained trajectories, maximum absolute one-step changes were 0.667701 mm R,
0.787286 mm Z and 35.3942 A Ip, below the frozen empirical trips. No hard
50-mm/10%-Ip outer-envelope failure occurred.

## 4. What the trajectories do and do not show

State 61 was already 24.554601 mm from source at approximately 0.213045 m/s,
with offsets (-18.840125, +15.747322) mm and +1,205.301 A Ip. The best
observed speed among all post-decision states was 0.112947 m/s in `b12_f12`
at state 75. That state was already 25.665515 mm from source, so it failed the
capture position and speed gates simultaneously; later states accelerated
again. The B/F allocations therefore show finite velocity-shaping effects,
but none of the frozen open-loop schedules produced a capturable held tail.

The `bf_alt` and zero-weight `bf_alt_replay` native continuations are exactly
equal through their common safe stop for R_geo, Z_geo, R_mid, Ip, all 14 coil
currents, all 48 wire currents and all 102 actions. The four checked semantic
artifact hashes are also exact. `sprsina` byte hashes differ, as in earlier
finite native-continuation evidence; this is not a fresh-restart or hidden-
state identity claim. The formal critical-replay gate remains FAIL because
both paths were incomplete, and this descriptive equality does not change
the frozen route.

The evidence rejects the particular state-61, 24-slot B/F/H open-loop family
under the 25-mm development corridor. It does not prove that B/F actions have
no useful local authority, that a measurement-recentered feedback policy
cannot capture, that continuation inside a separately designed wider
simulator-development envelope is unsafe, or that the final two-axis goal is
unreachable. Conversely, the 50-mm hard margin and small realized steps do
not authorize post-hoc widening or continuation beyond the observed stops.

## 5. Route decision

The planned short-horizon model comparison is cancelled because its
prospective data-readiness AND gate failed. Reusing the partial paths for a
fit would violate the frozen role and would train on a corridor-truncation
mechanism rather than qualified sequence outcomes.

The next route requires a deliberate architecture/safety decision, not an
automatic new model or another hand-written depth ladder:

1. Prospectively separate the simulator-only development envelope from the
   terminal capture set and the physical hard envelope, with an explicit
   state-dependent stop/recourse rule. ID-2Z5 itself remains unchanged.
2. Replace long fixed open-loop schedules with exact-observation,
   truth-recentered short-horizon allocation. The observed near-braking point
   around `b12_f12` state 75 is design evidence only, not a ready policy.
3. Decide whether B/F/H remains a bounded candidate basis or whether an
   independently supported additional Card15 direction is required. A
   surrogate may nominate a small set only after prospectively fit-eligible
   data exist; canonical-source TSC may verify shortlisted branches.
4. Preserve fresh whole-history calibration, blind holdout, repeatability,
   Recourse-L1 and eventual waypoint/path qualification as separate AND
   gates. Do not interpret a wider simulator exploration contract as a
   controller safety certificate.

The project pauses at this route-review boundary. The final goal remains the
fixed-1100-ms, exact-observation, one-ms, slew-limited, safe two-axis
waypoint/path controller and later repeated bidirectional R_mid crossing with
continuous belief; ID-2Z5 neither achieves nor falsifies that goal.

## 6. Accepted-raw cleanup

After the compact evidence, hashes, result, independent audit and log were
committed and pushed, the exact accepted run's `rollouts/` subtree was
irreversibly removed under fixed-path, stopped-process, result-hash,
audit-hash and raw-inventory guards. The removed tree contained
75,108,986,121 bytes. Top-level compact evidence and logs remain on the
server and in the tracked audit directory. Server free space after deletion
was 144,288,649,216 bytes.
