# R_geo/Z_geo NR1 safety and fixed-prefix replay qualification

Status: prospectively frozen before any NR1 TSC plant advance on 2026-08-13.

## 1. Scope and claim boundary

NR1 may establish only:

1. a fail-closed hold/abort/recovery interface around the existing direct
   TSC Card15 runner;
2. authentic availability of paired same-step plasma-boundary and limiter
   fields from the fixed 1100 ms start and every generated successor;
3. deterministic replay, from that same fixed start, of one frozen hold
   prefix and one small nonzero reversible prefix; and
4. the measured wall-clock cost of those prefix replays.

NR1 does not implement a plant model, observer, optimizer, MPC, RL, expert,
teacher dataset, trajectory tracker, or deployable controller. It does not
qualify arbitrary-state snapshots or extrapolation beyond the exact prefixes
below. All generated records have `intended_use=interface_validation` and are
forbidden from later expert or learning data.

## 2. Fixed source and controlled signal

Every rollout starts from the existing source directory `1100ms`. The signal
is computed independently at every state from one paired boundary:

```text
R_geo = (min(gfile.boundary_R) + max(gfile.boundary_R)) / 2
Z_geo = (min(gfile.boundary_Z) + max(gfile.boundary_Z)) / 2
```

The paired limiter trace supplies the inner and outer intersections with
`Z=0`, and `R_mid` is their midpoint. `R_geo < R_mid` is HFS; otherwise it is
LFS. No directory name or legacy `R/Z` state field may override this result.
Missing, unequal-length, non-finite, or degenerate boundary/limiter data,
an abnormal state, or disagreement between same-state `Ip` fields aborts the
rollout before another plant advance.

A read-only pre-design interface check found the fixed source fields present
and computed `R_geo=0.708635102 m`, `Z_geo=0.035241343 m`,
`R_mid=0.7919 m`, and `Ip=31286.4059 A`. Thus the fixed source is HFS under
the accepted geometry contract even though its historical directory name
contains `LOW-FIELD-SIDE`.

## 3. Frozen action construction

The existing TSC order, turn counts, Card15 `.3E` serialization, absolute
current limits, 0.3 A/ms slew, 10 ms sample time, and direct runner effect
semantics are unchanged. NR1 calls `TSCStepRunner.step_current_a` and adds no
software delay queue.

At reset, each source readback current is converted to kA-turn, serialized to
the existing exact `.3E` Card15 field, parsed back, and converted to A. This
14-vector is the frozen representable center `q0`. Offline preflight must
prove that constructing `q0` requires no clipping and that the initial
readback-to-`q0` increment respects the unchanged per-step slew.

The nonzero candidate starts from `q0` and requests an alternating-sign
TSC-order increment of `0.05 * max_delta_current_a_per_step` per component.
It too is quantized through the same `.3E` representation before use and must
pass absolute-current and slew preflight. The immediately following command
returns to exact `q0`; all later commands remain at `q0`.

## 4. Frozen real-TSC matrix

Only an accepted offline gate may authorize these four independent rollouts:

| rollout | eight issued targets at 1100--1170 ms |
|---|---|
| `hold_primary` | `q0` repeated eight times |
| `hold_replay` | exact replay of `hold_primary` |
| `pulse_primary` | one small nonzero target, then `q0` seven times |
| `pulse_replay` | exact replay of `pulse_primary` |

Each rollout therefore has eight 10 ms plant advances and ends at 1180 ms.
There are exactly 32 authorized NR1 plant advances. No adaptive action,
optimization, target motion, branch search, or extra diagnostic rollout is
authorized under this identity.

## 5. Fail-closed safety sentinel

The following are prospective campaign stop limits, not certified machine or
deployment limits:

1. the exact boundary/limiter/Ip signal contract passes at every state;
2. TSC reports no abnormal state, nonzero return, solver error, or saturation;
3. all 14 readback and target currents remain inside the existing configured
   absolute limits;
4. every requested current increment is at most the existing configured
   per-step slew plus `1e-9 A`;
5. `R_geo` remains between the same-state inner and outer limiter midplane
   radii and within `0.05 m` of the source `R_geo`;
6. `Z_geo` remains within `0.05 m` of the source `Z_geo`;
7. `Ip` retains its source sign and remains within 10% of source magnitude.

The sentinel validates the current state before issuing each target and the
successor immediately after the step. A violation after a step records that
state and performs no later plant advance. `abort` means exactly this stop;
it does not issue a speculative emergency action. The return to frozen `q0`
after the one-step pulse is the only NR1 recovery candidate. Passing it shows
only finite small-signal return behavior over this prefix.

## 6. Replay and cost gates

For each primary/replay pair:

1. source revision, resolved TSC configuration, start identity, target
   sequence, serialized Card15 target fields, and issue times must match;
2. state times, paired-boundary geometry, Ip, 14 coil readbacks, and the full
   parsed `wire_currents.csv` current vector must agree at every state within
   respectively `0 ms`, `1e-12 m`, `1e-9 A`, `1e-9 A`, and `1e-9 A`;
3. physical-state artifact SHA-256 values (`geqdsk`, `coil_currents.csv`,
   `wire_currents.csv`, and `sprsina`) are recorded, with byte identity a
   diagnostic rather than a substitute for parsed equality; and
4. per-step and per-rollout wall time are recorded without a retrospective
   speed threshold.

All safety gates and both parsed replay comparisons must pass to return
`FIXED_1100MS_PREFIX_REPLAY_QUALIFIED`. A safety failure stops NR1. A replay
failure returns `PREFIX_REPLAY_NOT_QUALIFIED`; it must not be relabeled an
Oracle, but it does not by itself prove that a learned main model is
impossible. Even a pass does not qualify arbitrary-state branch replay,
closed-loop control, or a TSC teacher dataset.

## 7. Evidence and execution rules

The exact implementation commit and package hashes must be recorded before
real TSC. Local synthetic tests and server offline preflight run first using
the existing project/server virtual environments. Server execution uses the
existing project, simulation tree, and TSC virtual environment; it does not
use Git, install packages, modify the simulation source, or read historical
raw as fixtures. Outputs go only to a new NR1-specific project run directory.
Primary and independent postprocessing must read only the newly generated
NR1 evidence.

NR1 PASS authorizes neither NR2 nor any additional TSC by itself. The user's
present instruction authorizes continued staged development, but each later
stage still requires a new prospective design, implementation checkpoint,
and accepted offline gate before its own plant advances.
