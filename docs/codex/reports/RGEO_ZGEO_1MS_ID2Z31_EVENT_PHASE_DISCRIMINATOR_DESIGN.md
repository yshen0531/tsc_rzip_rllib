# ID2Z31 qZ event-phase discriminator design

Date frozen: 2026-08-21

## Purpose

ID2Z30 failed fresh blind validation because `q_Z+` at issue 44 advanced an
otherwise matched one-frame R event from state 50 to state 49.  ID2Z31 is one
bounded simulator-development campaign that maps this exact event over three
adjacent issue times and checks a fresh exact replay.  It fits or updates no
model and does not qualify feedback.

This is not a rescue or rerun of ID2Z30.  Its blind FAIL and gates remain
immutable.  ID2Z31 rows have zero fit weight and may only design an explicit
event-phase action guard or a set-valued successor.

## Frozen campaign

All rows use a canonical 1100 ms reset, the same 73-issue full-F-to-slack
transition centre and a common state-73 endpoint:

1. fresh matched transition-centre baseline;
2. `q_Z+` sustained-eight/exact-return-eight at issue 43;
3. the same at issue 44;
4. an exact replay of item 3;
5. the same at issue 45;
6. `q_Z-` at issue 44 as the signed matched control.

Maximum budget: six resets, 438 advance attempts/gotsc calls/verified plant
advances, 444 retained states and 2,220 required semantic/diagnostic raw
artifacts.  Retry after any plant-advance attempt is forbidden.  No arm,
phase, duration, amplitude or replay may be added after execution begins.

## Gates and outputs

Before TSC, all six complete Card15 streams must be constructed exactly,
remain within `0.3 A` per-coil slew and absolute-current limits, close through
the frozen bridge, match the certified prefix, pass storage clearance and
bind the immutable ID2Z30 result/audit.

At runtime, any interface, prefix, paired-boundary, current, Ip, empirical
outer-corridor or raw-integrity failure stops the campaign and is not a
scientific event result.  The new successor remains simulator-only empirical
exposure; post-action stop does not constitute a pre-action plant bound.

The event detector is fixed before execution: within effect states 47--52,
record every one-step R increment greater than `+0.20 mm`.  A map is
scientifically complete only if the baseline, all four unique branch cells
and the replay complete safely, every row has exactly one such event in the
window, and the two issue-44 qZ+ replays agree exactly on checked state/action
semantics.  The measured event state is an output, not a PASS target.

PASS authorizes only one zero-TSC guard decision:

- if event state is deterministic but action/phase dependent, freeze a
  conservative no-nonnominal-action horizon that covers every measured event
  state plus the full eight-state response horizon;
- if replay or mapping is not deterministic, use a set-valued/abstaining
  model across the whole affected interval;
- if signal is absent, duplicated or integrity is incomplete, stop and audit;
  do not widen the phase sweep.

Any subsequent model identity must use fresh calibration and fresh
whole-family validation.  ID2Z31 does not authorize ID2Z31 rows for fitting,
a feedback sentinel, Authority-L0, Recourse-L1, source capture, arbitrary
waypoints, paths or R_mid crossing.
