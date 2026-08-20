# Post-ID-2Z18 model and authority route review

Date: 2026-08-20

## Decision

The overall new-round architecture remains:

```text
exact same-step R_geo/Z_geo/Ip observation
+ exact Card15/action/readback history
+ bounded causal history model and calibrated uncertainty
+ independent hard interface and qualified recovery
-> truth-recentered rolling two-axis control
```

The committed ID-2Z19 v1 implementation must not be trained unchanged. It is
frozen as a pre-fit design stop, not as a model, TSC, plant, authority or
controller failure. No ID-2Z19 model output exists and calibration/holdout
remain unopened.

The next model identity is ID-2Z19R1. It contains one pre-fit readiness gate
and exactly two fixed development candidates. In parallel, one bounded
source-local authority/recovery identity must be designed. A model can rank
candidates but cannot prove authority, safety or recourse; an exact-TSC
branch result cannot replace model calibration or unseen-history validation.

## Why v1 is stopped before fitting

The full signed ID-2Z18 Card15 issue set is numerical rank four. Its first
four singular values are approximately
`17.1171654, 10.7507430, 5.19886186, 0.44272750`; the remaining values are
numerical zero. Projecting the full signed set onto the positive-only F/A/E
rank-three subspace loses as much as `0.08921197 A` in 14-coil L2,
`0.07958776 A` in one coil and `8.2457%` of one issued action norm. This
removes an observed signed Card15 non-odd component despite the frozen
`odd_symmetry_assumed=false` contract.

The v1 future-action summary also derives deltas from future compact
`active_command` rows. Those rows happen to equal the preceding known target
in all checked development transitions, but a deployable causal predictor
must derive the same stream from current active command plus the proposed
future target sequence. Future RZI, future measured current and future
recorded active command must be mutation-invariant forbidden inputs.

The v1 evaluator is also insufficient:

- paired response and action ranking are evaluated only at each pair's first
  divergence;
- d00/d04/d05 repeat the same early response through 4 ms;
- all 24 frozen better-sign comparisons prefer plus and `argmin` ties also
  choose plus, so an always-plus rule can pass the ranking count;
- the d03 1 ms R/Z response is only about `0.0011 mm`, making an unconditional
  cosine sign gate unstable;
- value uses origin-to-endpoint average speed rather than terminal 1 ms
  speed;
- the recurrent regression check takes a maximum across metres and amperes;
- no held-history support/OOD diagnostic, cross-horizon consistency ledger or
  structurally independent scalar evaluator is retained.

These are prospective implementation/evaluator defects discovered before a
fit result. They do not consume the ID-2Z18 development evidence and must not
be rewritten as a failed model experiment.

## ID-2Z19R1 frozen direction

The readiness preflight is part of ID-2Z19R1, not another open-ended science
stage. It must pass before any fit and must establish:

1. an exact rank-four executed-action coordinate, derived from Card15 inputs
   without RZI outcomes, with an explicit reconstruction-residual gate;
2. causal future target reconstruction and counterfactual mutation tests for
   future active/current/RZI fields;
3. fold-local numerical rank, conditioning and cross-family support metrics;
4. all informative event origins and 1--8 ms auxiliary horizons, with
   qualification reported at 1/2/4/8 ms;
5. persistence, constant-velocity and a genuinely refit action-blind
   backbone baseline;
6. a row-level out-of-fold prediction ledger for an independent evaluator.

Exactly two candidates are allowed:

- A: exact rank-four actuator/current coordinates, fixed stable action-memory
  poles and one regularized multi-horizon multitask map. It is a structured
  stable-memory predictor, not a claim that the entire plant is LPV or that
  the direct map is a stable learned state-space model.
- B: the unchanged A plus one very small persistent causal TCN residual with
  fixed width, receptive field and three seeds. It is the only neural
  residual candidate; there is no architecture or hyperparameter sweep.

Both predict RZI displacement and terminal 1 ms RZI increment. The evaluator
reports endpoint error, terminal R/Z velocity error, Ip error, exact candidate
current/slew excursion, response direction only above a frozen signal floor,
paired response, support/OOD, action-value tie structure and cross-horizon
consistency. Physical quantities are compared componentwise or after frozen
normalization; raw metres and amperes are never maximized together.

Candidate B must independently pass every gate, improve the frozen paired
criterion relative to A and regress no componentwise critical metric by more
than the frozen allowance. A failing A does not automatically select B.
All out-of-fold rows are persisted and the independent audit recomputes truth,
metrics, gates, selection and route without refitting.

## Model and authority are independent AND gates

The model route is bounded to one chain:

```text
ID-2Z19R1 development
-> freeze one artifact
-> c00--c03 fresh calibration
-> v00--v03 unopened whole-history holdout
```

If neither candidate passes development, calibration and holdout remain
closed. No third model, larger network, grid search or gate change is
allowed. One zero-fit attribution may distinguish support, target and model
class failure. Only a demonstrated support deficit may authorize one
targeted new-data identity.

Independently, the control route receives one bounded source-local
capture/authority/recovery closure. It must use exact-TSC candidate
evaluation under the pre-existing hard interface, terminal 1 ms speed,
sustained capture, fresh exact replay and a prospectively qualified fallback
for every admitted prefix/pending-action state. A model PASS may shortlist
candidates but cannot authorize the action. An authority FAIL changes the
action/terminal/recovery design rather than triggering more model capacity.

The first real feedback sentinel opens only after both axes pass:

```text
whole-history model calibration/holdout PASS
AND finite authority PASS
AND recovery closure PASS
AND independent hard-interface PASS
```

It uses a frozen model, no online adaptation, exact 1 ms RZI recentering and
one source-local same-side two-axis target. Domain expansion then proceeds
through multiple same-side anchors, different arrival histories, two-axis
waypoints and paths, one R_mid crossing, return crossing and finally repeated
bidirectional crossing with continuous belief. Online adaptation, BC,
DAgger and RL remain later optional layers.

## Claim boundary

ID-2Z18 proves a finite source-local development data set with measurable
history-conditioned responses. It does not prove a qualified predictor,
uncertainty tube, capture, recovery, controller, waypoint, path, R_mid
crossing or deployment. ID-2Z19R1 is allowed to produce only a development
shadow artifact and, on PASS, authorize a separately frozen calibration
identity.
