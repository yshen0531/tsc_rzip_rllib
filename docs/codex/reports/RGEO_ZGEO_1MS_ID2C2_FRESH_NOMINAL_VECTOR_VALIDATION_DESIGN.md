# R_geo/Z_geo 1 ms ID-2C2 fresh nominal/vector validation design

Date: 2026-08-17 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2c2-fresh-nominal-vector-validation-v1`

## Purpose

ID-2C1 selected the exact Card15 `p03_minus_stride1` schedule and measured a
complete p04/p07/p09 signed residual family around its issue-15 level. That
campaign contained one realization per cell and used the same identity for
selection and response measurement. ID-2C2 therefore performs no search and
changes no action. It repeats the frozen nominal and residual cells under a
fresh identity to decide whether the finite source-local authority is
repeatable and geometrically useful enough to justify a separate structured
model-development stage.

This remains a TSC-only empirical validation contract. It is not a
controller-safety, tube, recourse or closed-loop contract.

## Frozen campaign

There are nine fixed cell families and two fresh canonical resets per family:

1. fresh q0 baseline;
2. exact `p03_minus_stride1` nominal through issue 31;
3. the selected nominal prefix through issue 15 followed by its held level;
4. the same prefix with one p04-plus issue at issue 16 and exact return at 17;
5. p04-minus in the same form;
6. p07-plus;
7. p07-minus;
8. exact-centred half-p09-plus;
9. exact-centred half-p09-minus.

Every rollout has 32 one-millisecond issues. The maximum is therefore 18
resets, 576 advance attempts/gotsc calls and 594 states. Sibling replay pairs
remain atomic. There is no selection, adaptation, retry, cleanup plant action
or continuation beyond state 32.

The phase-B response of each signed arm is always computed against the
same-replay-index held-nominal baseline. The whole response from state 17
through state 32 is retained. The peak-vector gate describes the complete
one-issue-plus-return primitive, including its causal tail; it is not called
an instantaneous Jacobian.

## Frozen execution and repeatability gates

Before every issue, the implementation must use the current true, noiseless
same-step paired-boundary `R_geo/Z_geo` and same-step `Ip`; validate exact
Card15 representation, actual issued/readback current, absolute current and
the `<=0.3 A` adjacent per-turn slew; and refuse before plant advance on any
invalid boundary or interface condition. Future successor truth remains
unknown before issue.

Every successor must remain inside the unchanged 50 mm/50 mm/10% outer
envelope and the empirical 2 mm/2 mm/100 A per-step cap before another issue.
These empirical TSC stop rules are not pre-action tubes.

All 18 rollouts and 576 verified advances are required. Each replay pair must
match over every state in time, paired-boundary R/Z/Rmid, Ip, all 14 coil
currents and all 48 wire currents at the frozen tolerances. Issued action
records and the four semantic artifacts must also match. `sprsina` remains a
diagnostic artifact and is not promoted to semantic byte identity.

## Frozen scientific gates

For both nominal replays, compared with the same-index q0 replay:

- terminal source-relative R/Z norm reduction must be at least 30%;
- maximum absolute Ip departure from source must be at most 1000 A.

For both phase-B replay sets:

- every one of the six signed arms must have peak R/Z response norm at least
  25 micrometres over states 17--32;
- every arm's maximum absolute Ip response to its paired held-nominal baseline
  must be at most 50 A;
- its terminal R/Z response norm divided by peak norm must be at most 0.50;
- each direction's plus/minus peak vectors must oppose with cosine at most
  `-0.95`, and their norm ratio must lie in `[0.5, 2.0]`;
- the six peak vectors must have numerical R/Z rank two;
- at least one two-column pair must have condition number at most 5;
- the circular maximum angular gap of all six rays must be at most 150
  degrees, establishing positive spanning for this finite primitive family.

These gates use the full actual 14-dimensional Card15 actions. Passing rank,
condition and angular gap does not prove superposition, a smooth Jacobian or
recovery. P09 remains separately labelled as a hybrid/event primitive.

## Data and authorization boundary

ID-2C2 records are validation-only. They may not be fit, calibrated, turned
into fixtures, treated as a blind holdout, or used for expert/Oracle/BC/
DAgger/RL data. A complete PASS may authorize only a separately frozen
source-local structured-model development design using ID-2C1 as development
data and ID-2C2 only as immutable evaluation. That model must start with
exact actuator/queue semantics, a time-indexed active nominal continuation
and stable low-order action/history memory. A neural residual is still
blocked until a simpler causal candidate is evaluated.

A scientific FAIL stops the source-local nominal/vector route for review. An
interface, runtime, safety or raw-integrity failure remains a failure of its
own layer and cannot be reinterpreted as a plant-authority conclusion.

Regardless of outcome, ID-2C2 does not authorize a controller, MPC,
uncertainty contraction, recovery, transport, `R_mid` crossing, online
adaptation or RL. The final goal remains safe causal approximate two-axis
relative/path/waypoint tracking from fixed 1100 ms with continuous history
through HFS/LFS crossings and Ip retained as a coupled safety quantity.
