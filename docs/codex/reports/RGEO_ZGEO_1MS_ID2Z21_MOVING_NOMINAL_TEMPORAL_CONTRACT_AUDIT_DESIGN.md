# ID-2Z21 moving-nominal temporal-control contract audit design

Date: 2026-08-20

## Identity and scope

ID-2Z21 is a server-executed, read-only analysis of tracked ID-2Z18 and
ID-2Z20 evidence. It performs zero TSC calls, zero plant advances, zero model
fits and zero calibration/blind-holdout reads. It does not modify or reinterpret
either frozen predecessor verdict.

The audit decides only whether the existing development evidence is sufficient
to freeze one materially different fresh sustained-allocation campaign around
a moving nominal. It cannot claim Authority-L0, capture, Recourse-L1, a model,
feedback or control qualification.

## Authenticated inputs

The machine config binds exact SHA-256 identities for:

- the ID-2Z18 config, result, corrected independent audit and all fourteen
  fit-weight development compact trajectories;
- the ID-2Z20 config, final compact evidence and result report; and
- the post-ID-2Z20 route review.

Only files inside the repository are accepted. The script rejects missing,
extra or hash-mismatched development trajectories and rejects any attempt to
read the declared unexecuted c00--c03/v00--v03 schedules.

## Lineage audit

The ID-2Z18 `baseline_full_f` trajectory is recomputed from its state rows.
The audit records source-relative distance, causal one-ms R/Z speed and Ip at
states 32, 40, 48, 60 and 65, plus the terminal 60--65 maxima. Those metrics
are checked against frozen values in the config.

The ID-2Z20 held-center numbers are report-bound facts, not independently
reparsed raw evidence because the completed raw subtree was removed after its
independent audit and compact recovery. The audit verifies the exact report
hash and the frozen reported values, then records the held versus continuing-
full-F differences with that provenance. It may not describe those values as
a fresh raw recomputation.

## Exact action allocation

For every development trajectory, issues 16--47 are matched to its declared
32-token sequence. Exact issued-target increments are reconstructed from
successive 14-coil targets. Each occurrence of F/A/a/E/e/H must reproduce one
token vector within the frozen tolerance, each vector must respect 0.3 A per
coil, and H must be zero.

The audit reports numerical rank/condition for the actually executed nonzero
token set without assuming odd symmetry. It separately evaluates hypothetical
`F + token` sums. This is a static impossibility diagnostic only: any sum that
exceeds 0.3 A proves that unconditional additive residual semantics are
inadmissible. It does not authorize projection or clipping. The new route must
choose, replace or time-share exact increments inside the per-issue feasible
set.

## Sustained response audit

For each declared signed pair d00--d05, the audit uses only that pair's first
common-prefix token divergence as its causal segment origin. Later differing
issues are part of the prospectively declared segment but are not counted as
new independent events because their histories have already diverged. At
horizons 2, 4 and 8 ms it computes:

- plus-minus R/Z separation;
- plus-minus causal terminal one-ms R/Z velocity separation;
- three-state median R/Z separation ending at the horizon; and
- whether the response is a multi-state effect rather than an isolated peak.

Every segment/horizon is counted once by `(pair_id, first_divergence_issue,
horizon)`. No later divergence, rollout sibling or repeated common prefix is
allowed to create extra statistical weight.

A prospectively useful segment event must satisfy all of:

- 4 ms R/Z separation at least 0.10 mm or 8 ms separation at least 0.20 mm;
- terminal velocity separation at least 0.05 m/s at one admitted horizon;
- the corresponding three-state median R/Z separation at least 0.05 mm;
- peak-to-three-state-median ratio no greater than 5; and
- exact non-clipped token execution.

The readiness gate additionally requires useful events from at least two
distinct signed pair families. Their R/Z segment vectors must contain a
best-conditioned two-vector set with condition no greater than 20 and an
acute line angle at least 10 degrees. These are D0 campaign-design thresholds,
not controller-grade authority thresholds.

## Terminal and claim boundary

All fourteen development trajectories are recomputed against the unchanged
six-state stationary capture gate: source distance at most 25 mm, causal speed
at most 0.1 m/s and absolute source-Ip offset at most 5% for states 60--65.
ID-2Z21 expects and preserves zero predecessor capture. A nonzero count would
be an evidence mismatch, not a newly discovered PASS.

The audit also records which state/action/history fields a later augmented
moving-terminal viability object must contain. It does not fit or qualify
such an object.

## Routes

Input, identity, action or metric inconsistency produces:

`ONE_MS_ID2Z21_INPUT_OR_EVIDENCE_FAIL_NO_TSC`

Insufficient persistent segment signal, exact allocation or task-plane
diversity produces:

`ONE_MS_ID2Z21_SUSTAINED_ALLOCATION_NOT_READY_REDESIGN_ACTION_BASIS_OR_NOMINAL`

Readiness produces:

`ONE_MS_ID2Z21_MOVING_NOMINAL_TEMPORAL_CONTRACT_READY_FRESH_D0_DESIGN_ONLY`

The readiness route authorizes only a separately frozen fresh campaign design.
It does not authorize TSC under the ID-2Z21 identity.

## Stop rule after readiness

The successor campaign is limited to one small, whole-root, fit-eligible
sustained-allocation matrix. It must compare against continuing moving nominal,
include complete switch/braking/post-tail semantics and freeze all data roles
before TSC. If its sustained D0 gate fails, the temporal grammar closes and the
project changes action basis or nominal. It may not add adjacent duration,
phase or amplitude micro-stages.
