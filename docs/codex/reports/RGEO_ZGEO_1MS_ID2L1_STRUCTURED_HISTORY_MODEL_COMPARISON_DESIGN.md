# R_geo/Z_geo 1 ms ID-2L1 structured history model comparison design

Date: 2026-08-17 Asia/Shanghai

## Purpose

ID-2K1 qualified 40 unique development cells over eight complete causal
history families and four matched signed probes per history. ID-2L1 uses
only those development cells to compare a small sequence of structured
causal models. It runs no TSC and opens no calibration or holdout.

The comparison corrects the two earlier model-design failures:

1. a monolithic sequence model must not spend most of its capacity learning
   the deterministic absolute-time drift while losing the much smaller action
   response;
2. plus/minus Card15 responses are not assumed to be odd. The exact four
   translated primitive vectors define a finite actuator subspace, and
   signed/even memory terms compete explicitly.

## Data and split identity

- source: the tracked ID-2K1 compact trajectories and independently audited
  primary result only;
- uniquely weighted samples: 40 trajectories, five cells in each of eight
  history families;
- the three extra ID-2K1 replays remain integrity-only and receive zero fit
  weight;
- no ID-2I1, ID-2J0, ID-2C2, calibration or holdout trajectory may be read;
- all siblings in a history family remain together;
- four leave-family-pair-out folds:
  `h00+h01`, `h02+h03`, `h04+h05`, and `h06+h07`;
- each fold trains on 30 trajectories from six histories and evaluates ten
  trajectories from two unseen histories.

The full exact Card15 action is retained at the interface. A deterministic
rank-three orthonormal coordinate basis is derived from the four actual
p04/p07 plus/minus target offsets, without response labels. The rank-three
fact is an actuator-coordinate property found by the zero-fit server input
pretest; it is not an output-response rank or authority claim. Every issued deviation
used by the model must reconstruct in that basis within `1e-9 A`; otherwise
the stage fails input integrity.

## Shared causal backbone

Every candidate predicts one-ms R_geo/Z_geo/Ip increments as:

`time-indexed nominal increment + bounded causal action-memory response`.

The nominal term is one shared coefficient per issue step. It is fitted
jointly rather than copied from any held baseline. The response term uses
only exact issued Card15/current history available at the decision boundary:

- the exact issue-to-effect offset is one state;
- future issued candidate Card15 is allowed;
- future actual/readback current and future R_geo/Z_geo/Ip are forbidden;
- fixed poles `0.0, 0.5, 0.8, 0.95` filter both target level and target edge;
- no fitted autoregressive state matrix is allowed, so the explicit backbone
  cannot acquire an unstable recursive eigenvalue;
- current exact/noiseless R_geo/Z_geo/Ip is injected as the rollout origin at
  each truth-recenter boundary. It is not reconstructed by an observer.

Paired baseline/probe transition differences over states 26--34 are included
in the development loss with frozen extra weight. This prevents the much
larger nominal drift from hiding an action-blind model.

## Candidate ladder

Candidates are considered in this fixed simplicity order:

1. `stable_signed`: time nominal plus signed fixed-pole level/edge memory;
2. `stable_signed_even`: add absolute/even fixed-pole memory;
3. `stable_contextual`: add bounded quadratic cross-memory features that can
   condition a new probe on earlier p04/p07 history without using a history
   label;
4. `structured_gru_residual`: a width-10 single-layer GRU learns only the
   residual of `stable_signed_even`. Its inputs are causal time/action/current
   coordinates; three frozen seeds are averaged. Its output is bounded before
   being added to the structured backbone.

`action_blind` is fitted and reported but is not selectable. No candidate may
use group, direction, sign or conditioner labels as model inputs. The labels
exist only in the evaluator.

The first candidate in the simplicity order passing all gates is selected;
small metric improvements do not automatically justify a neural residual.
For the GRU to remain eligible it must also improve mean held-family paired
NRMSE by at least 10% over `stable_signed_even` and may not regress any fold by
more than 5%.

## Evaluation

Every fold reports:

- teacher-forced one-step p95 absolute R/Z/Ip error;
- truth-recentered rolling error at periods 1, 2 and 4 ms from state 16;
- free nine-step absolute rollout from the exact state-25 pre-probe origin;
- matched baseline/probe response NRMSE over states 26--34;
- peak R/Z response cosine at the truth peak for all eight held probes;
- improvement over the action-blind response comparator;
- catastrophic finite bounds and all non-finite values.

The frozen eligibility gates are:

- per-fold teacher one-step p95 at most
  `0.30 mm / 0.30 mm / 30 A`;
- per-fold truth-recentered p95 at most
  `0.30/0.30/30` for 1 ms,
  `0.55/0.55/50` for 2 ms, and
  `0.90/0.90/75` for 4 ms;
- per-fold state-25 free-rollout p95 at most
  `1.50 mm / 1.50 mm / 100 A`;
- every fold paired-response NRMSE strictly below `0.90`, with mean at most
  `0.75`;
- at least seven of eight positive peak cosines in every fold and 30/32 in
  total;
- at least 25% mean NRMSE improvement over action-blind;
- no prediction may exceed the catastrophic error cap
  `3 mm / 3 mm / 150 A`.

These are development selection gates, not calibrated uncertainty bounds.

## Output and route

The selected model is refit on all 40 unique development cells and serialized
with its exact feature definition, normalization, action basis, poles,
coefficients or neural weights, training seeds and source hashes. A second
server process performs a deterministic full refit and metric comparison.

A complete PASS authorizes only a separately frozen fresh calibration-data
design. It does not authorize opening an old holdout, shrinking a tube,
running authority shooting, recovery, controller/MPC, transport, crossing,
online adaptation, expert learning or RL.

If no candidate passes, the route stops for model/data review rather than
enlarging the network or generating more TSC automatically.
