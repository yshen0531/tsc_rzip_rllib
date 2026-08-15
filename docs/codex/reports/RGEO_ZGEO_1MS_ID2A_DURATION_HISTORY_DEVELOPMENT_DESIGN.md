# R_geo/Z_geo 1 ms ID-2A duration/history development design

Date: 2026-08-15 Asia/Shanghai

Frozen identity: `rgeo-zgeo-1ms-id2a-duration-history-development-v1`

## Why this stage exists

ID-1C rejected the last static persistent-mean basis candidate.  Its p09-minus
trajectory contained a deterministic, exactly repeated state-12 boundary
excursion which disappeared again at state 13.  Averaging effect ages one
through four therefore destroys information that a causal model must retain.
The failure does not reject p01 or p09 as time-resolved primitives and does
not justify a larger recurrent model without a fit-eligible dataset.

ID-2A is the first dataset in the new round that may be used for development
model fitting, but only if every execution, raw, replay, input-support,
response-support and Ip gate passes.  Older ID-0/ID-1 records remain consumed
design evidence and are not mixed into the fit.

## Prospective matrix

Every rollout restarts from the canonical 1100 ms source, advances at 1 ms,
retains state 0 through state 32 and never retries.  Three complete causal
prefix families are used:

1. `late_q0`: the unmodified q0 history;
2. `history_p04_plus`: a one-issue p04-plus prefix at issue 6 followed by the
   exact q0 return, previously shown to give a useful near-visible-state
   history contrast;
3. `anchor_p03_minus`: the bounded cumulative p03-minus prefix, stepped back
   through its adjacent level and returned to exact q0 before the probe,
   previously shown to give a useful displaced-anchor contrast.

At issue 10 each context receives the exact q0-centred half-amplitude p01 or
p09 Card15 primitive, plus or minus, for one, two or four consecutive issues.
The following issue returns exactly to q0.  Each context has its own no-probe
matched baseline.  The critical p09-minus four-issue trajectory is repeated
once in every context.  This gives 42 rollouts, 1,344 maximum plant advances,
1,386 complete states and 6,930 required raw artifacts.

The matrix deliberately varies duration while retaining every individual
effect and tail state.  No four-state mean, sign label, odd response, static
Jacobian, superposition or finite-memory cutoff is assumed.

## Causal and hard-interface contract

Before each issue, the current same-step paired-boundary R_geo/Z_geo and Ip
are exact noiseless observations.  Complete controller-owned observation,
issued/serialized/applied/readback and queue history since the 1100 ms
takeover is available.  The future successor remains unknown before issue;
latent belief is only for unobserved memory, future response and model
mismatch.  Pre-1100 ms history is not claimed.

Exact Card15 serialization, issue+1 effect timing, 14-coil order, absolute
current, limiter, Ip, paired boundary and per-coil `<=0.3 A` adjacent slew
remain fail-closed.  The generic runner R/Z and silent clipping paths are not
accepted as control semantics.  Novel successors are finite TSC-only
identification exposures and create no controller transition tube or
recovery claim.

## Identifiability and data role

The model input is the exact two-coordinate p01/p09 primitive command plus
the exact actuator/readback history, not an arbitrary 14-by-lag free map.
Before scientific use, the prospective 16-step virtual-input lag block must
have rank 32 and condition no greater than 100.  Each context/direction/sign
family must have at least `0.01 mm` peak R/Z response over its three durations,
the duration trajectories must separate by at least `0.005 mm`, and absolute
Ip response must stay below 150 A.  Context response differences are measured
but are not forced to be nonzero: a null contrast supports a simpler model.
Tail extinction is not a gate.

Each complete prefix context is an atomic group.  Development comparison is
leave-one-context-family-out; steps and sibling durations may never be split
randomly.  Only an overall PASS makes these records development-fit eligible.
Calibration remains a separately frozen fresh grouped stage, and holdout is
an unopened fresh whole-prefix stage after the model and calibration
identities are frozen.

The first comparison after a PASS is exact actuator/queue plus time-indexed
q0 continuation and a stable low-order latent/state-space response model.
A small GRU/TCN may learn only the residual and must win on every held-out
development family before it survives.  Wire currents and sprsina remain
audit-only and cannot become silent deployment features.

## Storage and route boundaries

The server currently has ample space, but the stage still fails before TSC
unless at least 150 GB is free.  Its preregistered raw estimate is capped at
90 GB and at least 50 GB must remain after that estimate.  Raw compression,
overwrite and retry are forbidden.

ID-2A PASS authorizes only development model fitting and a separately frozen
calibration design.  It does not authorize calibration, holdout opening,
controller/MPC execution, recovery, transport, active adaptation, expert
data or any global controllability claim.
