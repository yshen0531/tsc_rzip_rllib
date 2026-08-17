# R_geo/Z_geo 1 ms ID-2F1 repeated-context development design

Date: 2026-08-17 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2f1-repeated-context-development-v1`

## Purpose

ID-2F1 produces fit-eligible source-local data for a genuinely
history-conditioned model. It does not require the valid state19/state27
excursions to be assigned a physical mechanism before fitting. It requires
only exact causal timing, valid paired-boundary R_geo/Z_geo, complete raw,
repeatability and sufficient action-history support.

ID-2E1 remains a grouped model FAIL and ID-2C2 remains unopened. ID-2F1
does not alter or reuse ID-2C2 trajectories.

## Frozen campaign

Every rollout starts from the canonical 1100 ms source and executes the
exact p03-minus stride-one nominal increments at issues 1 through 15. The
resulting exact Card15 target is held except for the declared conditioner
and probe.

Three whole causal contexts are frozen:

1. `none`: no conditioning action;
2. `p04_plus_i18_d1`: issue p04-plus at issue 18, return exactly to the held
   nominal at issue 19, then hold;
3. `p07_plus_i18_d1`: issue p07-plus at issue 18, return exactly to the held
   nominal at issue 19, then hold.

Each context contains:

- one matched no-probe baseline cell;
- p04 and p07 residual directions;
- plus and minus signs;
- issue-22 durations 1, 2 and 4.

Thus each context contains 13 unique cells. Every cell has two fresh replay
members, for 39 unique whole-history cells and 78 rollouts. Every rollout
issues exactly 32 one-ms actions and retains states 0 through 32. Maximum
budgets are 78 reset calls, 2,496 advance attempts, 2,496 `gotsc` calls,
2,496 verified plant advances and 2,574 retained states. Retry after any
advance attempt is forbidden.

The issue-18 conditioning cells are deliberately distinct from ID-2C2's
issue-16 one-issue evaluator cells.

## Causal and actuator contract

Before each issue, same-step paired-boundary R_geo/Z_geo and same-step Ip are
exact noiseless observations. The complete post-takeover observation,
issued/serialized/applied/readback and queue history is available. The next
state and future actual/readback current remain unknown before issue.

Every target is an exact translated 14-dimensional Card15 action. Adjacent
single-turn coil change is at most 0.3 A and may equal 0.3 A. Absolute
current, limiter, paired-boundary and Ip gates are fail closed before the
next issue. Legacy runner clipping must neither be triggered nor relied on.
The physical effect remains issue `k` to state `k+1`; no software queue is
added.

Novel successors are explicitly TSC-only empirical identification
exposures, not controller-grade pre-action tubes. A failed successor stops
before the next issue. No return/cleanup plant action is issued after a stop
or after state 32.

## Fit-eligibility gates

The campaign becomes development-fit eligible only if all of the following
pass:

1. all 78 rollouts complete every declared issue with exact Card15,
   readback, slew, absolute-current, Ip, boundary and timing semantics;
2. all 2,574 states retain all four semantic artifacts (`inputa`, `geqdsk`,
   `coil_currents.csv`, `wire_currents.csv`) and diagnostic `sprsina`, with
   no missing required file;
3. each of the 39 replay pairs is exact in checked R_geo/Z_geo/R_mid/Ip,
   14-coil current, 48-wire current, action history and semantic-artifact
   identity under the frozen deterministic tolerances; `sprsina` remains
   diagnostic and is not required byte-identical;
4. the p04/p07 signed virtual-action lag-16 block has rank 32 and its
   condition number and minimum singular value are reported;
5. every direction/sign family has at least one context-duration arm with a
   peak R/Z response of at least 25 micrometres; zero-response individual
   arms remain valid learning records and are not forced to fail;
6. every nonbaseline arm stays within 150 A absolute baseline-relative Ip
   response and retains the complete available tail through state 32;
7. bounded integrity diagnostics reparse the same paired boundary and
   reproduce R_geo/Z_geo without any xmag/zmag, rc/zc or other fallback.

No event occurrence, symmetry, linearity, superposition, duration
separation or mechanistic explanation is forced. Continuous, zero and jump
responses are all legitimate targets.

## Data roles and next stage

After a complete PASS:

- ID-2F1 may be used only for development fit and whole-history grouped
  model selection together with separately declared prior development data;
- both replay members stay in the same split and are weighted as one unique
  statistical cell for selection summaries;
- calibration, blind holdout, expert/Oracle/BC/DAgger/RL, fixture and
  controller-safety use remain forbidden;
- ID-2C2 remains evaluator-only and unopened until a later model identity
  has frozen its architecture, features and selection result.

The next model stage must compare the same whole-history folds for a stable
structured/LPV baseline, small GRU, causal TCN and probabilistic mixture or
ensemble output. It must use current exact R_geo/Z_geo/Ip and causal
current/action history, and separately report rolling one-step, recursive
rollout, response, jump coverage, Ip and uncertainty metrics.

A model PASS still does not authorize controller TSC. Finite hold,
two-sided authority, reverse, calibrated tube and qualified recourse remain
separate gates before constrained rolling control.

## Storage and evidence

The run is server-only and uncompressed. It requires at least 400 GB free
before launch, reserves at most 180 GB for new raw and requires at least
200 GB estimated free afterward. The output path must not exist.

Primary and structurally independent raw audits must authenticate every
state and recompute all load-bearing metrics before any model-fit flag is
true. A failure preserves raw and is classified separately as input,
storage, execution/interface, raw-integrity, repeatability, action-support,
signal/Ip or scientific-design failure.

This design changes no controller, reward, termination, queue, TSC-state or
existing experiment identity.
