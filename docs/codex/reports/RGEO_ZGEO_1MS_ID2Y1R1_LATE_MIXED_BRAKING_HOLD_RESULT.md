# ID-2Y1R1 late mixed-braking hold result

## Identity and execution

- implementation revision:
  `3881eb16a6aad1e0f372d1e7c626f19d1ef3e616`;
- historical Y1 regression-alignment revision: `005ac9c2`;
- frozen config SHA-256:
  `0904428058e9ca806e80f47e4b0a40442cf6fbf79218ed264d400e2d7b7679e8`;
- server validation: Y1R1 focused `6/6`, Y1+Y1R1 `13/13`, and complete
  one-ms suite `385/385`;
- real execution: four canonical-source resets, `350/350` attempted,
  `gotsc`, and verified one-ms advances, and 354 retained states;
- raw inventory: 1,770 required artifacts, 20,848,095,096 bytes, digest
  `0f3c7f8cad2a2a73205beada9f6f8df0f13662f7d9f54db5226b60ec4a7343e9`.

The first complete-suite run exposed only a stale historical Y1 test which
still expected the already-frozen Y1 preflight to pass. Commit `005ac9c2`
changed that test to require the actual 92.8 A headroom failure and zero
plant work. It did not change an action, gate, runtime file, or Y1R1
implementation. The repeated server suite then passed 385/385 before real
TSC execution.

## Independent evidence

All four states0--65/actions0--64 prefixes match the independently audited
ID-2W3R1 prefix. Exact Card15, per-coil slew, current, paired-boundary, Ip,
time, solver, counter, storage, and raw-integrity gates pass. The independent
full-raw audit has zero failures and exactly reproduces the primary counters,
inventory, four branch metrics, scientific failure, and final route.

The runner's retained state-k `inputa` contains outgoing issue-k. The
independent audit therefore parses and checks every outgoing Card15 action,
reconstructs the arrival-active command from the canonical source or the
preceding issue, and does not compare the rewritten `inputa` byte hash with
the primary preissue hash. Physical R/Z/Ip, 14 coil currents, 48 wire
currents, and non-rewritten semantic artifacts remain independently checked.

## Finite result

All four branches stopped before the next issue on the frozen negative-R
preissue clearance. None reached the states96--104 hold window:

| branch | retained states | final source R / Z | final Ip offset | R/Z distance |
|---|---:|---:|---:|---:|
| p03L64 + p04m6 | 89 | -25.2101 / +12.8664 mm | +985.44 A | 28.3036 mm |
| p03L64 + p04m12 | 92 | -25.3952 / +12.2211 mm | +1,212.05 A | 28.1828 mm |
| p03L64 + p04m6 + p07p4 | 86 | -25.0107 / +13.0117 mm | +971.70 A | 28.1929 mm |
| p03L64 + p04m8 + p07p4 | 87 | -25.0166 / +12.8317 mm | +1,046.86 A | 28.1155 mm |

The exact final route is:

`ONE_MS_ID2Y1R1_LATE_MIXED_HOLD_FAIL_SEQUENCE_OPTIMIZATION_REQUIRED`

This is a clean finite schedule/control-allocation failure. It is not a
runtime, deployment, interface, raw, actuator, controller, recovery,
closed-loop, global reachability, or plant-unreachability result. No model
was fit or updated; calibration, blind holdout, controller, expert, BC,
DAgger, RL, and fixture records read remain zero.

## Route decision

The hand-selected ramp-depth ladder is closed. A successor may not repair
this result by adding another p04/p07 depth or by enlarging a neural model.
The next discriminator must evaluate a prospectively frozen, finite set of
exact Card15 macro-actions at one common causal prefix and rank their
time-resolved absolute progress, persistence, Ip/current cost, and hard
margin. This is action/control-utility branch search, not model fitting.

Only a useful late macro may enter a later rolling sequence optimizer. A
macro failure redirects the search to an earlier decision point or a broader
action allocation; it cannot be promoted to a hold or recovery conclusion.

## Evidence location

Tracked compact evidence is under
`docs/codex/audits/rgeo_zgeo_1ms_id2y1r1_20260819_3881eb16`. The 20.85 GB
server raw tree remains the primary evidence and was not downloaded.
