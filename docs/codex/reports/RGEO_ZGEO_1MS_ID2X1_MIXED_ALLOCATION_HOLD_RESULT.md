# ID-2X1 mixed-allocation hold result

## Identity and evidence boundary

- Primary implementation revision: `4fa6596bd57480deba7711398a4d83c1f550b94e`.
- Reporting-only independent-auditor repair: `7cf8b2e4`.
- Frozen config SHA-256:
  `53eab001330b3d3610cc66c3280a5cbcbec899fd6302938a89a3780024861622`.
- Four fresh canonical-source TSC resets were executed on the server.  There
  were 275 attempted, `gotsc`, and verified plant advances, 279 retained
  states, and 1,395 required raw files totalling 16,431,125,796 bytes.
- No model was fit or updated and no calibration, blind holdout, expert,
  controller, RL, or fixture data were read or produced.

The first launcher invocation failed before the launcher contract because a
remote shell quoting error did not pass `ID2X1_SOURCE_REVISION`.  It created
zero rollout and zero plant advance.  The preserved
`id2x1_4fa6596b_real.log` records that deployment-launch error.  The corrected
launcher invocation then consumed the one real campaign identity.

## Execution and raw integrity

Server validation passed 7/7 focused tests and 371/371 complete one-ms tests
at the implementation revision.  After the audit repair it passed 8/8 and
372/372 respectively.  The primary result reports exact action/current,
common-prefix, counter, inventory, and fail-closed execution gates.

The initial independent audit incorrectly compared retained raw state-k
`inputa` (which the runner has rewritten with outgoing issue-k) to the
primary compact's preissue state-k `inputa`; it also treated issue-0 q0 as
the canonical source-active command.  That produced a reporting-only prefix
failure.  Commit `7cf8b2e4` repairs only this lifecycle reconstruction:

- every outgoing raw Card15 action is still independently parsed and checked;
- state 0 uses the canonical source `inputa` as its arrival-active command;
- later arrival-active commands use the preceding outgoing issue;
- physical R/Z/Ip, 14 coil currents, 48 wire currents and the non-rewritten
  semantic artifacts are still compared; and
- no threshold, action, controller, raw file or TSC result changed.

The corrected independent audit passes with zero failures and exactly
reproduces all four stops, 275 counters, 279 raw states, 1,395 files,
16,431,125,796 bytes, inventory digest
`bcb5db0d7bced4ed58ee11ee6293a38d36c022a5ededec7b8cb1892b4d95d3a7`,
scientific metrics and final route.  The original failed audit remains
preserved and must not be mistaken for a plant or prefix failure.

## Finite result

All four branches stopped before issuing the next action at a frozen
preissue clearance.  These are guarded candidate failures, not runtime or
interface errors:

| branch | retained states | stop | final source-relative R / Z | final Ip offset | RZ distance |
|---|---:|---|---:|---:|---:|
| p03 level32 hold | 66 | Z clearance | -24.4815 / +25.0517 mm | +173.88 A | 35.0276 mm |
| p04-minus depth18 | 72 | Z clearance | -24.9218 / +25.0312 mm | +895.69 A | 35.3222 mm |
| p04m18 + p07p6 | 70 | R clearance | -25.5066 / +24.2314 mm | +808.98 A | 35.1816 mm |
| p04m24 + p07p8 | 71 | R clearance | -25.1000 / +24.1856 mm | +1,027.35 A | 34.8562 mm |

No branch reached the frozen states 88--96 terminal window.  Therefore no
terminal hold statistic is eligible, zero mixed branches pass, and the exact
route is:

`ONE_MS_ID2X1_MIXED_ALLOCATION_HOLD_FAIL_BROADER_SEQUENCE_SEARCH_REQUIRED`

At common state 65, the strongest mixed branches did improve both coordinates
relative to the p03-level32 baseline by roughly 1--2 mm, but their velocity
and accumulated Ip remained material and the benefit was insufficient to
enter a hold corridor.  This rejects these three fixed late allocations; it
does not prove the actuator directions useless, the plant unreachable, or a
feedback/optimized sequence impossible.

## Route decision

The next and final hand-designed discriminator should preserve the stronger
p03 transport through level64, then use the freed per-step slew after issue64
for bounded p04-minus braking and a small optional p07-plus correction.  This
tests a materially different allocation: X1 abandoned p03 at level32 and
spent the remaining interval on residual ramps, whereas the best measured
p03 path retained much stronger Z correction through level64.

If no such branch reaches its terminal window, stop increasing manually
chosen ramp depths.  The successor must become a finite sequence/control-
utility search or feedback design with explicit current/Ip/clearance cost,
not another capacity or micro-probe ladder.

## Compact tracked evidence

The directory `docs/codex/audits/rgeo_zgeo_1ms_id2x1_20260819_4fa6596b`
contains the primary result, four compact trajectories, offline record,
original failed audit, corrected passing audit, validation logs, launch log
and real-run log.  Server raw remains the primary evidence and was not copied
locally.

