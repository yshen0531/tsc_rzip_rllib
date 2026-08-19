# ID-2Z4R1 earlier-switch capture frontier result

Date: 2026-08-19

## Evidence identity

- physical implementation: `3834a952fceb8f96aec625e73ac082733842839f`
- reporting-only correction: `32ef0a76`
- stage config SHA-256:
  `1e0be886b8787966549d7925cf37d4eeac22379bf9770e9ba28ccf3b1ae63cbd`
- accepted server run:
  `artifacts/server_runs/rgeo_zgeo_1ms_id2z4r1_20260819_3834a952_v3`
- tracked compact evidence:
  `docs/codex/audits/rgeo_zgeo_1ms_id2z4r1_20260819_3834a952_v3`

The earlier `c2b730dc` and `2a8207f8_v2` server directories are preserved
zero-advance diagnostics. They are not part of this scientific result.

## Execution and raw integrity

The final server preflight admitted all twelve frozen candidates with the
within-stage frozen 100 A target-headroom floor and used zero reset/TSC calls. The
accepted campaign then produced:

```text
reset calls / classified rollouts             12 / 12
advance attempts / gotsc / verified advances  1290 / 1290 / 1290
retained states                                1302
guarded safe stops                             12
required artifacts                            6510
required artifact bytes                       76,678,587,048
inventory SHA-256                             1883a7a926ebeb2b6698c410a986b0e87418c1e121d395e0c73d5344440eaf4f
models fit or updated                         0
calibration/holdout records read              0
```

All twelve complete causal prefixes passed. Every branch stopped before its
next issue on the prospectively allowed `PULSE_CLEARANCE_R` gate. No branch
had a runtime, boundary, Card15, readback, current, Ip, prefix, raw or
inventory failure. Server focused tests passed `9/9`; the full one-ms suite
passed `425/425` in `189.829 s`.

The first independent audit omitted the derived `side` string from its raw
state representation and therefore compared `None` against `HFS` at every
checkpoint. It is preserved as a reporting failure. The separately frozen
reporting-only correction derived `side` from independently parsed
`R_geo < R_mid`, changed no physical or scientific semantics, and reran zero
TSC. The corrected audit passed with no failures and exactly reproduced all
counters, prefixes, inventory, scientific metrics and route.

```text
result.json                              8781643403a4e4c0d056097089aa78d1ca45fd171603d4af9c0cc32c504284fc
independent_raw_audit_reporting_r1.json  9572f84e270345380b02ef7d0688c79bc099532cb71765694dd86b51d5d22892
```

## Scientific result

No branch reached all six terminal states `112..117`; therefore none could
pass the unchanged 25 mm / 0.1 m/s / 5%-Ip capture gate. The official route
is:

```text
ONE_MS_ID2Z4R1_EARLIER_SWITCH_FRONTIER_FAIL_ACTION_BASIS_REVIEW_REQUIRED
```

This closes only the frozen twelve-sequence, state-93, B/U switch-time
frontier. It is not plant unreachability, controller failure, or evidence
against feedback, a richer action basis, or a redesigned nominal path.

Descriptive compact-trajectory recomputation explains why another manual
depth ladder is not justified:

- source-relative state 93 is approximately `R=-22.9855 mm`,
  `Z=+8.4939 mm`, distance `24.5047 mm` and one-step speed `0.1887 m/s`;
- the actual R-axis distance to the 25 mm development boundary is about
  `2.0145 mm`; subtracting the separately frozen 2 mm empirical
  post-successor trip value leaves a conservative remainder of about
  `0.0145 mm`. The runtime pre-issue gate used the former boundary and did
  not implement the latter subtraction as a plant bound;
- pure `B12` gave the best observed distance, `24.445 mm` at state 105, but
  speed was still about `0.195 m/s`; its best speed was `0.1717 m/s` at
  state 102, followed by renewed drift;
- `B4-U4-B4` gave the lowest observed speed, about `0.1484 m/s` at state
  104, but its distance was already about `25.80 mm`;
- all terminal attempts were limited by R clearance, not Ip. Last-state Ip
  offsets were roughly `+959` to `+1051 A`, below the 5% source cap of about
  `1564 A`.

The same selected prefix also exposes a route-level conflict. Exact active
target headroom at states `77/81/85/89/93` is respectively
`95.2/96.4/97.6/98.8/100.0 A`. Thus state 93 is the first listed checkpoint
that satisfies the Z4/Z4R1 100 A engineering design reserve, but it is already at the
R-axis exploration boundary. Starting the same late-capture search earlier
would silently weaken the reserve gate; starting at state 93 leaves no useful
capture runway. The transport nominal and capture allocation must be
co-designed rather than patched sequentially.

## Required route review

Do not rerun ID-2Z4R1, relax its gates, or append another hand-selected B/U
depth. The recommended successor is a prospectively frozen, zero-new-TSC
reserve-aware nominal/capture co-design stage:

1. audit the complete existing nominal path for geometry, velocity, Ip and
   exact Card15 headroom together, rather than selecting transport first and
   braking later;
2. use the prospective ID-2Z4R1 compact trajectories only as development
   evidence for a small truth-recentered short-horizon response model and
   action-sequence nominator; it is not a safety model or calibration set;
3. search a richer, exact-Card15 low-dimensional action allocation with an
   explicit reserve constraint and capture/terminal objective, not another
   B/U token ladder;
4. submit only a small, fixed shortlist to canonical-source TSC replay, with
   the model used to amortize nomination and TSC used for finite verification;
5. retain fresh whole-prefix calibration, blind holdout, repeatability and
   Recourse-L1 identities before any feedback controller or waypoint claim.

The earlier Z1/Z2/Z3 stages used a 95 A action-selection floor; 100 A was
introduced for the unrun Z4 design and then frozen in Z4R1. It is not a
physical current limit or a qualified recovery reserve. Whether it should be
prospectively changed remains a separate new-stage design decision. This
result does not authorize changing the completed Z4R1 gate.

## Server cleanup

After the corrected raw audit, compact evidence, logs and this result were
tracked and pushed, the exact accepted v3 `rollouts/` subtree was removed
under an absolute-path guard. The irreversible deletion removed
`77,859,319,851` bytes and restored server free space to
`144,295,432,192` bytes. All top-level compact JSON, both independent
audits, preflight and logs remain on the server and in the tracked evidence
directory; neither zero-advance diagnostic directory was touched.
