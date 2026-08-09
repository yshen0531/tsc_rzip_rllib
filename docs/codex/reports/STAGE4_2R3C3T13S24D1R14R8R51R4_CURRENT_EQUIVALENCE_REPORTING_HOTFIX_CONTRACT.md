# Stage4.2R3c3T13S24D1R14R8R51R4 current-equivalence reporting hotfix contract

Status: frozen on 2026-08-10 after the immutable 100-trajectory R51R4
campaign and both original raw audits reported the execution-failure route,
and after read-only raw forensics localized that route to binary64 nominal
current reconstruction, but before any corrected hotfix or formal-response
artifact was produced.

## 1. Preserved evidence and authorization boundary

This is a zero-new-TSC reporting repair. It must not rerun Ray, `gotsc`, TSC,
a controller, a plant step, or any R8/R8R1/R51/R51R1/R51R3/R51R4 trajectory.
It must not overwrite the original R51R4 primary raw audit, independent raw
audit, stage state, manifest, offline construction, raw files, or logs. Every
R51R4 trajectory remains a probe forbidden from expert, BC, DAgger, residual
RL, or any other learning data.

The repair is fail-closed against the following immutable server evidence:

```text
executed config
  6fb1c69b473a79d3889fe1dc725a564aeb256e45331f98b1834ccc4debeb4802
executed controller / primary raw-audit module
  32a433addb3890e17dec2888cfc2840c634490f105c1b56ad179f8ece404cdaf
executed original independent module
  10df4afe6bdf373f7aa47f5b5c8661ae9e1f805a818418fa64ddc50cfbae3314
stage manifest
  ff0f57ea940f9909b03121428f32534ce16cff5944c3c110e7841d239a0b666d
original stage state
  59c914a6e772c5b8333a62060ca2fec862736949c15077ee925fe200b90617d9
offline construction / primary / independent
  612ed4fc9e1be64450ad894f49eecb467828f50afe3562b07ed585d55f80bca8
  76244364667c3b453f7066417a098e2d06288fe300f60815ae69f4d221069b15
  ef7ff791424a2f2cf7d53864326159f73fda295369821c37b5a676ec24990f21
original raw primary / independent
  9611590b0627ba0598fcbd7ce1aa14ee8072e4f0ad8a3a8912b251a7bb247c19
  c3f76ce90fba1578b87fc78d5051511809ba090c0848e73af0a5c0e90c14cc70
executed package digest
  d1d8aa2acde5b7013b2e87a0cdee1a05bde209e3f6435d2970aba377170b46ae
raw inventory
  count 100 / bytes 3,255,079
  9227c93aae7a1819949bee9a57f9294c9b0f01620bcbbe193e32ca6823a15f3a
plant steps / new raw / real TSC
  3,620 / 100 / true
formal response opened
  false
```

## 2. Exact original failure and read-only diagnosis

Both original audits agree exactly on the real-event digest
`11fa9bcaa7b8b6941c729094925caf1ecbe7234c921e87a0ebf5d33eaab2e384`
and on `passed_count=0`. The original primary nevertheless proves:

```text
strict parse / runtime success / full horizon                 100/100
authentic restart / source state / source trace               100/100
calibration / q0 / candidate / candidate first effect         100/100
stored-center return / event sequence / event gates           100/100
finite / forbidden-input / within-context causal prefix       100/100
runtime failures / safety stops / forbidden traces              0/0/0
maximum current utilization                                     0.3924
```

Only three reporting predicates failed:

```text
q0 first-effect binary-exact nominal current                   20/100
dwell binary-exact nominal current                              4/100
full real/offline event-detail byte digest parity               0/100
```

The controller issued an exact zero increment at every dwell event
(`400/400`). The physical candidate-effect current then remained byte-exact
through every dwell transition (`400/400`), the stored-center return action
had its exact issue-plus-one effect (`100/100`), the physical returned current
equaled the physical q0 center exactly (`100/100`), and every later physical
center state remained exact (`1,820/1,820`). All event actions had their exact
next-state action effect (`2,620/2,620`).

The failed comparisons instead used binary equality against currents
reconstructed through nominal binary64 arithmetic. Their maximum differences
were:

```text
q0 nominal readback                                  1.4210854715202004e-14 A
candidate/dwell nominal readback                     2.8421709430404010e-14 A
return/refresh nominal readback                      1.4210854715202004e-14 A
```

All `2,620/2,620` event-to-next-state nominal-current comparisons pass the
already frozen formal metric-equivalence contract at `rtol=0` and
`atol=1e-12 A`. The threshold therefore predates the real result and is not
selected from the observed discrepancy.

## 3. Only authorized correction

The corrected raw audit must independently parse all 100 gzip JSON files and
retain exact equality for:

```text
raw identity, immutable spec, event names and order
Card15 fields, requested coordinate, candidate identity
trace actions, next-state applied actions, zero dwell increments
physical candidate-current preservation, physical stored-center return
post-return physical center preservation, forbidden inputs and row coverage
```

Only comparisons between a real TSC current and the corresponding
binary64-reconstructed nominal event current change from `array_equal` to:

```text
finite values required
relative tolerance 0
absolute tolerance 1e-12 A
```

The corrected semantic event replay replaces the invalid full JSON byte
digest parity only by the conjunction of the unchanged exact discrete/action/
physical-state gates above and the frozen numerical current equivalence. It
does not relax action, Card15, current-utilization, causality, restart,
formal-timing, or scientific authority gates.

Primary must use NumPy vector comparisons. Independent must use scalar Python
and `math.isclose` without calling the primary measurement implementation.
They must agree exactly on inventory, row identities, old binary counts,
corrected counts, maximum error, semantic row digest, route, and outcome.

## 4. New artifacts and formal opening order

The original artifacts remain authoritative evidence of the reporting bug.
Only new files with the `current_equivalence_reporting_hotfix_` prefix may
carry its correction. The order is:

```text
1. raw primary hotfix
2. raw independent hotfix
3. dual-raw compact bridge and formal primary
4. structurally independent formal recomputation
5. compact/final hotfix report
```

Formal R/Z/Ip outcomes must remain unopened until steps 1 and 2 both pass and
agree. The original `stage_state.json` remains byte-identical; the final
hotfix report records the corrected completion state.

If and only if corrected raw integrity passes, its procedural route is:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_RAW_INTEGRITY_REPORTING_HOTFIX_COMPLETE_FORMAL_REQUIRED
```

After formal opening, the original preregistered scientific routes and gates
remain unchanged:

```text
repairs >= 1 and measured oracle >= 7/16
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_PRESENT_R51R5_MODEL_PREFLIGHT_REQUIRED

otherwise
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_INSUFFICIENT_LONGER_SEQUENTIAL_REDESIGN_REQUIRED
```

## 5. Scientific boundary

This correction can establish only R51R4 raw integrity and then expose its
already completed finite development-envelope response. It cannot convert an
integrity correction into a controller, MPC, formal-control, qualification,
long-hold, robustness, independent-holdout, plant-reachability, or Gate A
claim. R51R5 remains conditional on an exact final R51R4 scientific PASS.
Gate A, expert data, BC, DAgger, residual RL, and Gate B remain blocked.
