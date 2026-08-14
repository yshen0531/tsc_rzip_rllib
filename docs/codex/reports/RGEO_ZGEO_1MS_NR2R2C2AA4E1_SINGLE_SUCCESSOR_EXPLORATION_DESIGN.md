# R_geo/Z_geo 1 ms NR2R2C2aA4E1 single-successor exploration design

Date: 2026-08-14 Asia/Shanghai

Prospective identity:

```text
rgeo-zgeo-1ms-nr2r2c2aa4e1-single-successor-exploration-v1
```

## Purpose and separation from A4

The frozen A4 late-state support gate remains final as
`ONE_MS_NR2R2C2AA4_LATE_STATE_CAUSAL_SUPPORT_FAIL_NO_TSC`. A4 is not renamed,
resumed, implemented or run. Its strict pre-action support rule remains the
qualification rule for any safety/control claim.

That rule cannot also govern every first digital-twin observation: requiring
each new successor to have already been observed creates a closed bootstrap
loop. E1 therefore introduces a separate, simulator-only development channel
for exactly one previously unseen successor. It deliberately accepts that this
one realized future response has no qualified pre-action transition bound.
This is not a relaxation of A4 and cannot produce an A4, hold, tube, recovery,
model or controller qualification.

## Exact observation and timing contract

From the fixed 1100 ms takeover onward, before issue `k`, current same-state
paired-boundary `R_geo[k]/Z_geo[k]` and same-state `Ip[k]` are true, noiseless
observables. Missing, invalid, unpaired or non-finite boundary data fails
closed. Complete causal observations and controller-owned issued/serialized/
quantized/applied/readback/queue history accumulated since takeover are
available. This does not claim pre-1100 ms history.

Exact current observation does not reveal `state[k+1]` before issue `k`. E1's
only unknown is therefore a future transition, not its pre-issue state.

## Frozen action, budget and unconditional stop

One fresh authentic canonical-source reset makes at most 17 plant-advance
attempts and at most 17 corresponding `gotsc` calls. No failed, stale or
uncertain attempt may be retried under this identity.
A completed execution retains exactly 18 states, 1100 through 1117 ms; any
early interface/runtime/prefix stop must preserve its partial raw and still
write a classified result:

```text
issue 0       q0
issue 1       p03 level1
issues 2..16  p03 level2
```

Issues 0..15 and states 0..16 reproduce the two independently audited A3
replays. The only empirical bootstrap exception is
`issue16 -> state17`, p03 level2 effect-age 15. Issue16 repeats the same exact
Card15 level2 target and has exactly zero requested change from issue15.

After reading and recording state17 the runner must stop unconditionally. It
must not issue step17, return toward q0, clean up with a plant action, or create
state18. This applies on success, scientific rejection, interface failure and
abnormal successor alike. The implementation must prove this stop behavior by
test and the independent raw audit must reject any 1118 ms state directory.

## Frozen evidence identity and known-prefix gate

Before TSC, the implementation must hash-authenticate the base 1 ms config,
A3 config, A3 primary result, A3 independent audit, both A3 compact replays,
the A4 config/design and the A4 support result. It must confirm:

- A3 primary and independent routes passed their exact finite identities;
- the two A3 replays agree exactly over actions 0..15 and states 0..16 on
  time, R_geo/Z_geo/R_mid, Ip, 14 exact coil currents, 48 wire currents and
  the four semantic artifacts;
- their differing `sprsina` hashes remain diagnostic and are not treated as a
  semantic-equality requirement; and
- the A4 support result records 16/32 direct transitions and first unsupported
  issue16/effect17/effect-age15.

During the fresh E1 rollout, before every issue 0..16 the complete live prefix
must continue to match the frozen A3 reference on those same checked
coordinates. A mismatch before issue16 stops without exposing the unknown
successor. Requested Card15, issue/effect timing, actual readback, absolute
current, per-turn per-coil `<=0.3 A/step`, limiter, boundary and Ip checks all
remain fail closed. Legacy runner clipping must neither be needed nor relied
on.

## Exploration clearance, not a safety theorem

State16 must be inside the frozen inner envelope. Before issue16 it must retain
at least `20 mm R / 20 mm Z / 1000 A Ip` to the outer envelope. These are ten
times the post-result acceptance caps and are only an empirical exploration
clearance. They are not a transition tube, a worst-case plant bound or a
guarantee that state17 cannot cross the outer envelope.

The accepted state16 evidence currently has descriptive outer margins of
`40.956549 mm R / 38.755202 mm Z / 3036.044690 A Ip`. A3's observed maxima and
the `2 mm / 2 mm / 100 A` values remain empirical evidence, not a pre-action
proof.

## State17 development acceptance

Immediately after the one unknown advance, state17 must be recorded before any
route decision. The primary and independent audits then require valid paired
boundary, finite R_geo/Z_geo/Ip, time 1117 ms, exact active level2 Card15,
readback slew `<=0.3 A`, absolute-current/limiter/Ip validity, no runtime,
solver, abnormal or saturation failure, and no outer-envelope breach.

For the narrow development route to be accepted, state17 must also remain in
the inner envelope and satisfy:

```text
abs(R_geo[17] - R_geo[16]) <= 2 mm
abs(Z_geo[17] - Z_geo[16]) <= 2 mm
abs(Ip[17]    - Ip[16])    <= 100 A
```

These are post-action empirical acceptance gates. Passing them does not turn
them into a prospective tube.

## Evidence and data-use boundary

The final audit is structurally separate. For a completed successor it reparses
18 raw state directories and exactly 90 required files: four semantic artifacts
plus diagnostic `sprsina` for each state. A valid early stop has a smaller
partial inventory that must still be preserved and audited rather than causing
a reporting exception. The result records reset calls, advance attempts and
verified successful plant advances separately. The audit verifies all actions,
clocks, currents, paired boundaries, known-prefix equality, the state17
transition and absence of state18. Final raw `inputa` is an outgoing issue
record, so the independent audit reconstructs pre-issue active command from
the preceding effect/action history rather than comparing a post-run rewritten
file hash to the in-memory A3 pre-issue hash. Server raw remains on the server;
only compact evidence and logs are transferred directly without archives.

E1 raw and trajectory data are development-only causal-support exploration.
They are forbidden from model fitting or calibration, controller/optimizer
development, expert/Oracle data, fixtures, formal hold qualification, BC,
DAgger, RL and blind validation. The one realized successor cannot estimate
repeatability, a probability or a tube.

## Frozen routes and identity consumption

Pre-TSC failures:

```text
ONE_MS_NR2R2C2AA4E1_INPUT_INTEGRITY_FAIL_NO_TSC
ONE_MS_NR2R2C2AA4E1_OFFLINE_PREFLIGHT_FAIL_NO_TSC
ONE_MS_NR2R2C2AA4E1_PACKAGE_OR_DEPLOYMENT_FAIL_NO_TSC
```

Execution/result routes:

```text
ONE_MS_NR2R2C2AA4E1_KNOWN_PREFIX_REPLAY_FAIL_STOP
ONE_MS_NR2R2C2AA4E1_PREISSUE_EXPLORATION_CLEARANCE_FAIL_STOP_BEFORE_ISSUE16
ONE_MS_NR2R2C2AA4E1_NOVEL_SUCCESSOR_EXECUTION_FAIL_STOP
ONE_MS_NR2R2C2AA4E1_HARD_SAFETY_FAIL_STOP
ONE_MS_NR2R2C2AA4E1_SUCCESSOR_ACCEPTANCE_FAIL_REDESIGN
ONE_MS_NR2R2C2AA4E1_RAW_OR_REPORTING_INTEGRITY_FAIL_PRESERVE_RAW
ONE_MS_NR2R2C2AA4E1_SINGLE_SUCCESSOR_OBSERVED_WITHIN_EMPIRICAL_ENVELOPE_DEVELOPMENT_ONLY
```

Once any E1 plant-advance attempt occurs, the one-reset identity is consumed.
It may not retry, add a reset, resume, change a threshold or rerun after a
prefix/runtime/successor result. A zero-attempt packaging failure may be
repaired only if the
physical identity is unchanged. A reporting-only repair preserves completed
raw and runs no new TSC.

An accepted successor authorizes only a global route review and, if still
worthwhile, a separately frozen E2 design or fresh repeat qualification. It
does not automatically authorize an age-by-age p03 ladder. The final project
goal remains safe causal two-axis relative/path/waypoint tracking; source hold
is only one bootstrap dependency.

## Authorization boundary

This design checkpoint authorizes implementation, local/offline validation,
server package validation and, only after every zero-plant gate passes, the
exact one-reset/17-advance E1 campaign. It authorizes no other TSC, A4, model,
controller, MPC, recovery, atlas, adaptation or learning work.
