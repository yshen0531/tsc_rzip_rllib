# ID-2J0 post-holdout attribution and diagnostic re-observation design

## 1. Purpose and evidence status

ID-2I1 is final as
`ONE_MS_ID2I1_BLIND_WHOLE_HISTORY_HOLDOUT_FAIL_ROUTE_REVIEW`.  This stage
does not reopen that verdict, recalibrate its widths, or create another blind
holdout.  Its sole purpose is to determine why the frozen ID-2G1R1 TCN failed:
one-step local response, free-recursion drift, history support, ensemble
confidence, or actuator/effect timing.

The originally preferred zero-new-TSC audit became impossible after the
server cleanup removed the ID-2H1 and ID-2I1 raw directories.  Their tracked
compact results remain valid but do not contain per-state member predictions.
ID-2J0 therefore uses a new, explicitly post-holdout identity to re-observe
each of the sixteen unique ID-2I1 baseline/probe cells once.  These trajectories
are diagnostic replications, not blind evidence.

## 2. Frozen plant campaign

- fixed authentic 1100 ms source, 1 ms control period;
- the eight already-consumed ID-2I1 history groups are copied byte-for-byte;
- one baseline and one probe per group, one fresh replay per cell;
- 16 rollouts, 34 advances each, at most 544 plant advances and 560 states;
- issue `k` affects state `k+1`; the common history must match through state 25;
- every requested/serialized/applied/readback Card15 action remains audited;
- each turn remains at or below 0.3 A absolute change per coil;
- invalid paired boundary, limiter, Ip, current, runtime, raw, or prefix evidence
  fails closed before any later issue.

This is a TSC-only empirical diagnostic.  It makes no pre-action transition
tube, controller-safety, recovery, authority, or real-device claim.

## 3. Observability and prediction modes

At every decision boundary the same-state paired-boundary `R_geo/Z_geo` and
same-state `Ip` are exact, noiseless observables.  The full causal observation
and controller-owned action history since 1100 ms is available.  The future
successor remains unknown before issue.

The frozen three-member TCN is evaluated without updating any byte or width:

1. teacher-forced one-step prediction at every issue;
2. truth-recentered recursion with reset periods 1, 2, and 4 ms;
3. the original free recursion from state 16 through state 34;
4. absolute and matched baseline/probe errors at every state and axis;
5. action-effect and return-effect ages around issue 25;
6. member disagreement for every prediction mode;
7. future-current propagation versus the observed next-current diagnostic.

The period-1 result is the deployed-information idealization: after every
physical step the next decision receives exact current `R_geo/Z_geo/Ip`.
It is not a claim that an MPC prediction horizon may be reduced to one step.

## 4. Causal support audit

For every post-origin prefix, flatten the last sixteen frozen causal input
frames.  Standardize each feature using development-only rows, with zero-scale
features fixed to scale one.  Report nearest development-prefix distance for:

- the full actual TCN feature vector;
- the same vector with absolute-time coordinates omitted;
- action/history coordinates alone.

No response, future state, group label, sign label, or holdout outcome enters
the support embedding.  Distances are descriptive; they do not become a
transition tube or a post-hoc pass gate.

## 5. Frozen attribution routing

The audit first verifies raw identity, clocks, exact common prefix, Card15 and
current propagation.  An interface mismatch stops model attribution.

Otherwise it reports, without changing the old holdout:

- `MEASUREMENT_RECENTERED_SHORT_HORIZON_REQUIRED` when period-1 local response
  is directionally sound and materially better than free recursion;
- `FACTORIZED_HISTORY_SUPPORT_DATA_REQUIRED` when failures concentrate at
  causal prefixes farther than every development reference while near-support
  period-1 response remains sound;
- `STRUCTURED_NOMINAL_MEMORY_MODEL_REQUIRED` when near-support period-1
  response is confidently wrong or inaccurate;
- `MIXED_DATA_AND_STRUCTURED_MODEL_REQUIRED` when both support and model
  structure contribute;
- `ACTUATOR_OR_EFFECT_SEMANTICS_REVIEW_REQUIRED` for an execution-coordinate
  mismatch;
- `HIGHER_LEVEL_REVIEW_REQUIRED` if the evidence does not discriminate.

These are route diagnoses, not model PASS tokens.  The expected successor
architecture is exact actuator/queue plus an explicit time-indexed nominal,
a stable low-order action-memory state, and only then a small contextual neural
residual.  A larger pure TCN is not an automatic successor.

## 6. Data use and stopping rules

ID-2J0 raw may be used only for post-holdout attribution and for designing a
fresh, separately split development campaign.  It is forbidden for fitting,
training, calibration, model selection, uncertainty-width shrinking, fixtures,
expert/Oracle/BC/DAgger/RL data, controller qualification, or safety proof.

The stage runs no controller, MPC, optimizer, authority search, transport,
R-mid crossing, or online adaptation.  Any route after ID-2J0 requires a new
prospective identity.  ID-2C2 remains unread.

