# ID-2S2 exact sequence replay design

## Purpose

ID-2S1 measured four source-local f03 two-arm sequences and found both useful
time-resolved two-dimensional geometry and large non-additive interaction in
two branches. ID-2S2 repeats exactly those four complete action streams once,
under fresh canonical resets, to determine whether the full physical traces,
paired responses, measured geometry, and interaction residuals reproduce.

ID-2S2 introduces no new action, timing, history, or sequence cell. It fits no
model and gives every trajectory zero fit/calibration/holdout/expert/RL
weight. Two deterministic digital-twin observations are not a probabilistic
transition tube and may not be used to shrink a future uncertainty floor to
zero.

## Frozen campaign and budget

The four ID-2S1 streams are replayed in their original order with fresh
rollout IDs. Each has one reset, 34 issue attempts/TSC calls/verified advances,
and 35 retained states. The campaign maximum is therefore four resets, 136
attempts/calls/verified advances, 140 states, and 700 required artifacts.
Retry, resume, cleanup actions, compression, and model fitting are forbidden.

Every generated stream must be byte/field identical to its hash-bound ID-2S1
compact action stream. The same exact Card15, current, slew, paired-boundary,
Ip, inner-clearance, outer-envelope, and empirical successor-trip gates remain
in force. Current same-step R_geo/Z_geo/Ip are exact observations before each
issue; a future successor remains unknown until the TSC advance completes.

## Replay and scientific gates

The primary and structurally separate raw audit must establish:

1. complete execution and exact raw inventory;
2. exact physical prefix agreement with the matched ID-2R1 baseline through
   state 24/action 23;
3. original-to-fresh full-trajectory equality within `1e-12 m` geometry,
   `1e-9 A` Ip/coil/wire tolerances, excluding `sprsina` byte identity;
4. original-to-fresh paired-response equality at states 25--34 under the same
   tolerances;
5. exact recomputation of the ID-2S1 measured direction-progress, angular-gap,
   Ip, and actual-minus-additive interaction metrics.

A mismatch is retained as finite sequence-history nondeterminism or evidence
identity failure and triggers deep review. A complete PASS establishes only
finite exact replayability of these four sequences and may authorize a
separately frozen canonical-prefix sequence-shooting/control-utility design.
It does not establish authority, a stochastic tube, recourse, recovery, a
controller, MPC, transport, crossing, adaptation, or reachability.
