# Fixed-1000-ms NR1 source and one-ms interface qualification

## Purpose

This is the first scientific identity after the user replaced the fixed
1100-ms takeover with the authentic 1000-ms source.  It qualifies only the
source files, exact one-ms command/effect boundary, finite return behavior and
fresh replay.  It does not fit a model or claim Authority, capture, recovery,
Recourse or path control.

All 1100-ms trajectories and verdicts remain immutable historical evidence
with zero fit and qualification weight in this identity.  They are not
retimed, spliced or used as a missing 1000-to-1100 causal prefix.

## Frozen source

The source is
`/home/yangshen0711/tsc_all/tsc_simulation/HH70-PCS-ENV-LOW-FIELD-SIDE-118/1000ms`.
The config binds SHA-256 and byte count for `inputa`, `geqdsk`,
`coil_currents.csv`, `wire_currents.csv`, `sprsina` and `outputa`, plus:

- time: 1000 ms;
- paired boundary points: 278;
- R_geo/Z_geo: `0.7316591665/0 m`;
- Ip: `29779.7241 A`;
- wire-current entries: 48.

Any mismatch stops before TSC.

## Campaign

The first preflight identity stopped with zero TSC because the authentic PF4
readback is `-62 A` while the active Card15 command is `-70 A`; centering a
new command on readback would require an illegal 8 A issue.  Revision 2 keeps
the active Card15 command as the exact command center and treats the readback
difference as real causal plant memory.  It executes six fresh resets:

1. center hold primary/replay;
2. alternating signed pattern A primary/replay;
3. opposite alternating signed pattern B primary/replay.

Each rollout has exactly four one-ms action issues and five retained states
(`1000..1004 ms`).  The first non-hold issue must produce the requested
differential sign in all 14 observed coil-current components relative to its
matched hold successor.  Issues one through three return to and remain at the
exact source Card15 command center.  Readback tail dynamics are retained
rather than mislabeled as instantaneous state return.  The issued and
observed slew limits are both exactly `<=0.3 A/step`.

Maximum budget is six reset calls, 24 plant advances and 30 states.  No retry
is allowed after a plant advance.  An execution failure stops the remaining
campaign rather than changing the action or gate.

## Safety and evidence gates

Before every issue and after every successor:

- the same-step paired-boundary R_geo/Z_geo and same-step Ip must parse;
- R_geo remains inside the limiter and within 50 mm of the 1000-ms source;
- Z_geo remains within 50 mm of the source;
- Ip retains sign and remains within 10% of the source;
- all 14 actual currents remain inside absolute limits;
- exact Card15 target, issue time and `issue k -> state k+1` are preserved.

Primary/replay R_geo, Z_geo, R_mid, Ip, 14 coil currents and all 48 wire
currents must be exact under the frozen tolerances.  A structurally separate
raw-directory audit reparses every retained state.

## Routes and authorization

- `ONE_MS_NR1000S1R1_OFFLINE_FAIL_NO_TSC`: source, config or static action gate
  failed; no TSC may run.
- `ONE_MS_NR1000S1R1_EFFECT_CONTRACT_FAIL_STOP`: first-effect or exact-return
  semantics failed.
- `ONE_MS_NR1000S1R1_SAFETY_FAIL_STOP`: execution or finite source envelope
  failed.
- `ONE_MS_NR1000S1R1_REPLAY_NOT_QUALIFIED`: execution completed but exact fresh
  replay failed.
- `ONE_MS_NR1000S1R1_INTERFACE_QUALIFIED`: this finite source/interface stage
  passed.

A PASS authorizes only a separately frozen 1000-ms long-baseline/continuation
campaign.  It does not authorize reuse of any 1100-ms action basis, model,
event map, calibration, blind result or controller.

## Next dependency

The next identity must observe a 1000-ms-origin nominal/abort continuation for
long enough to expose pre-instability drift and establish the usable
intervention horizon.  It must not target or preserve the old 1100-ms state.
Only after that evidence may 1000-specific signed
primitives, sequential TSC teacher labels, a candidate-value model,
Authority-L0 and Recourse-L1 be developed.
